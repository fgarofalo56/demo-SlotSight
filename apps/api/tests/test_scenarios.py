"""Golden tests: does the pipeline reach the right conclusions?

These are the tests that matter most in this repository, and they are a
different kind of test from the rest.

An ordinary unit test asserts a function returns the right number. These assert
that **the system reaches the right conclusion about a floor whose truth we
control.** The synthetic dataset has four signals deliberately planted in it
(see ``slotsight.seed.scenarios``); these tests assert the analytics actually
surface each one, with the right severity and the right recommended action.

That makes the dataset the test oracle. Refactor the analytics, change a
threshold, or "optimize" a query in a way that breaks the conclusions, and
these fail - even when every unit test still passes.

    SIGNAL 1  declining bank NP-214    -> flagged, recommended for conversion
    SIGNAL 2  hot title Neon Tiki      -> chosen as the conversion target
    SIGNAL 3  metering fault NP-10307  -> flagged as data quality, NOT a star
    SIGNAL 4  healthy zone             -> explicitly recommended no action
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.analytics.floor import machine_metrics
from slotsight.analytics.outliers import (
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    detect_data_quality,
    find_top_performers,
    find_underperformers,
    rollup_to_banks,
)
from slotsight.analytics.recommend import (
    ACTION_CONVERT,
    ACTION_INVESTIGATE,
    ACTION_NO_ACTION,
    build_recommendations,
)
from slotsight.seed import scenarios as sig

pytestmark = pytest.mark.golden

WINDOW = 30


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL 1 — the declining bank
# ═══════════════════════════════════════════════════════════════════════════
class TestSignal1DecliningBank:
    async def test_bank_exists_with_expected_shape(
        self, session: AsyncSession, analysis_end_date
    ) -> None:
        machines = await machine_metrics(session, days=WINDOW, end=analysis_end_date)
        bank = [m for m in machines if m.bank_id == sig.DECLINING_BANK_ID]

        assert len(bank) == sig.DECLINING_BANK_UNITS
        assert all(m.title == sig.DECLINING_BANK_TITLE for m in bank)
        assert all(m.zone_code == sig.DECLINING_BANK_ZONE for m in bank)
        assert all(m.denomination_cents == sig.DECLINING_BANK_DENOM_CENTS for m in bank)

    async def test_bank_is_below_peer_threshold(
        self, session: AsyncSession, analysis_end_date
    ) -> None:
        machines = await machine_metrics(session, days=WINDOW, end=analysis_end_date)
        bank = [m for m in machines if m.bank_id == sig.DECLINING_BANK_ID]
        avg_index = sum(m.peer_index for m in bank) / len(bank)

        assert avg_index <= sig.DECLINING_BANK_EXPECTED_PEER_INDEX_MAX, (
            f"Declining bank indexed {avg_index:.3f}, expected "
            f"<= {sig.DECLINING_BANK_EXPECTED_PEER_INDEX_MAX}"
        )

    async def test_decline_is_detected_as_sustained(
        self, session: AsyncSession, analysis_end_date
    ) -> None:
        """Not variance. The prior window must agree, or the trend must be steep."""
        unders = await find_underperformers(session, days=WINDOW, end=analysis_end_date)
        flagged = [u for u in unders if u.machine.bank_id == sig.DECLINING_BANK_ID]

        assert flagged, "Declining bank produced no underperformers"
        assert all(u.sustained for u in flagged)
        assert any(u.severity in (SEVERITY_CRITICAL, SEVERITY_WARNING) for u in flagged)

    async def test_decline_shows_up_as_a_drop_not_a_baseline(
        self, session: AsyncSession, analysis_end_date
    ) -> None:
        """The bank must be *falling*, not merely low.

        This is what separates the planted signal from a title that was always
        weak. If a refactor made the detector fire on low absolute performance
        alone, this assertion catches it.
        """
        unders = await find_underperformers(session, days=WINDOW, end=analysis_end_date)
        flagged = [u for u in unders if u.machine.bank_id == sig.DECLINING_BANK_ID]
        avg_change = sum(u.index_change for u in flagged) / len(flagged)

        assert avg_change < 0, f"Expected a declining index, got {avg_change:+.3f}"

    async def test_bank_rolls_up_as_a_unit(self, session: AsyncSession, analysis_end_date) -> None:
        """Conversions happen per bank, so the finding must reach bank level."""
        machines = await machine_metrics(session, days=WINDOW, end=analysis_end_date)
        unders = await find_underperformers(session, days=WINDOW, end=analysis_end_date)
        banks = rollup_to_banks(unders, machines)

        target = next((b for b in banks if b.bank_id == sig.DECLINING_BANK_ID), None)
        assert target is not None, "Declining bank did not roll up"
        assert target.flagged_units >= target.unit_count * 0.5

    async def test_recommendation_is_to_convert(
        self, session: AsyncSession, market, analysis_end_date
    ) -> None:
        recs = await build_recommendations(session, market, days=WINDOW, end=analysis_end_date)
        rec = next((r for r in recs if r.subject_id == sig.DECLINING_BANK_ID), None)

        assert rec is not None, "No recommendation produced for the declining bank"
        assert rec.action == ACTION_CONVERT
        assert rec.evidence, "Recommendation carried no evidence"
        assert rec.monitoring_instruction, "Conversion must come with a measurement plan"


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL 2 — the hot market title
# ═══════════════════════════════════════════════════════════════════════════
class TestSignal2HotMarketTitle:
    async def test_title_is_in_the_market_feed_and_outperforming(self, market) -> None:
        benchmarks = await market.title_benchmarks()
        hot = next((b for b in benchmarks if b.title == sig.HOT_MARKET_TITLE), None)

        assert hot is not None
        assert hot.market_index >= sig.HOT_MARKET_EXPECTED_INDEX_MIN
        assert hot.is_rising

    async def test_we_do_not_already_own_it(self, session: AsyncSession, analysis_end_date) -> None:
        """An opportunity we already own is confirmation, not an opportunity."""
        machines = await machine_metrics(session, days=WINDOW, end=analysis_end_date)
        assert all(m.title != sig.HOT_MARKET_TITLE for m in machines)

    async def test_it_is_chosen_as_the_conversion_target(
        self, session: AsyncSession, market, analysis_end_date
    ) -> None:
        recs = await build_recommendations(session, market, days=WINDOW, end=analysis_end_date)
        rec = next((r for r in recs if r.subject_id == sig.DECLINING_BANK_ID), None)

        assert rec is not None
        assert rec.suggested_title == sig.HOT_MARKET_TITLE

    async def test_synthetic_provenance_is_disclosed(
        self, session: AsyncSession, market, analysis_end_date
    ) -> None:
        """A recommendation built on invented data must say so, in the payload."""
        recs = await build_recommendations(session, market, days=WINDOW, end=analysis_end_date)
        conversions = [r for r in recs if r.action == ACTION_CONVERT]

        assert conversions
        assert all(r.uses_synthetic_market_data for r in conversions)
        assert all(market.name in r.data_sources for r in conversions)


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL 3 — the metering fault
# ═══════════════════════════════════════════════════════════════════════════
class TestSignal3MeteringAnomaly:
    async def test_anomaly_is_flagged(self, session: AsyncSession, analysis_end_date) -> None:
        machines = await machine_metrics(session, days=WINDOW, end=analysis_end_date)
        flags = detect_data_quality(machines)

        flag = next((f for f in flags if f.asset_number == sig.ANOMALY_ASSET_NUMBER), None)
        assert flag is not None, "Metering fault was not detected"
        assert flag.issue == "hold_above_par"
        assert flag.deviation_ratio >= sig.ANOMALY_HOLD_DEVIATION_THRESHOLD

    async def test_anomaly_is_excluded_from_top_performers(
        self, session: AsyncSession, analysis_end_date
    ) -> None:
        """**The most important assertion in this file.**

        A naive rank-by-win leaderboard puts this machine at the top and
        invites someone to order eight more of a broken unit. An analytics
        tool that cannot say "I don't believe this number" is not safe to act
        on.
        """
        tops = await find_top_performers(session, days=WINDOW, limit=50, end=analysis_end_date)
        assert all(t.machine.asset_number != sig.ANOMALY_ASSET_NUMBER for t in tops), (
            "Metering fault leaked into the top-performers list"
        )

    async def test_anomaly_is_excluded_from_underperformers(
        self, session: AsyncSession, analysis_end_date
    ) -> None:
        """Untrustworthy data is excluded from *both* directions, not just one."""
        unders = await find_underperformers(session, days=WINDOW, end=analysis_end_date)
        assert all(u.machine.asset_number != sig.ANOMALY_ASSET_NUMBER for u in unders)

    async def test_recommendation_is_to_investigate(
        self, session: AsyncSession, market, analysis_end_date
    ) -> None:
        recs = await build_recommendations(session, market, days=WINDOW, end=analysis_end_date)
        rec = next((r for r in recs if r.subject_id == sig.ANOMALY_ASSET_NUMBER), None)

        assert rec is not None
        assert rec.action == ACTION_INVESTIGATE
        assert "meter" in rec.rationale.lower()


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL 4 — the healthy zone
# ═══════════════════════════════════════════════════════════════════════════
class TestSignal4HealthyZone:
    async def test_at_least_one_zone_is_reported_healthy(
        self, session: AsyncSession, market, analysis_end_date
    ) -> None:
        """An engine that only ever flags problems trains people to ignore it.

        Silence must be unambiguous: the manager has to be able to tell
        "checked and fine" from "not checked".
        """
        recs = await build_recommendations(session, market, days=WINDOW, end=analysis_end_date)
        all_clear = [r for r in recs if r.action == ACTION_NO_ACTION]

        assert all_clear, "No zone was reported healthy - the all-clear path is dead code"
        assert all(r.evidence for r in all_clear)

    async def test_no_action_findings_rank_last(
        self, session: AsyncSession, market, analysis_end_date
    ) -> None:
        recs = await build_recommendations(session, market, days=WINDOW, end=analysis_end_date)
        actions = [r.action for r in recs]
        if ACTION_NO_ACTION in actions and len(set(actions)) > 1:
            first_no_action = actions.index(ACTION_NO_ACTION)
            assert all(a == ACTION_NO_ACTION for a in actions[first_no_action:]), (
                "All-clear findings must sort below actionable ones"
            )


# ═══════════════════════════════════════════════════════════════════════════
# Cross-cutting invariants
# ═══════════════════════════════════════════════════════════════════════════
class TestRecommendationInvariants:
    async def test_every_recommendation_carries_evidence(
        self, session: AsyncSession, market, analysis_end_date
    ) -> None:
        """A recommendation a manager cannot audit is one they should not act on."""
        recs = await build_recommendations(session, market, days=WINDOW, end=analysis_end_date)
        assert recs
        for r in recs:
            assert r.evidence, f"{r.id} has no evidence"
            assert r.rationale, f"{r.id} has no rationale"
            assert r.data_sources, f"{r.id} cites no sources"

    async def test_data_quality_outranks_performance(
        self, session: AsyncSession, market, analysis_end_date
    ) -> None:
        """A performance conclusion drawn from bad data is worse than none."""
        recs = await build_recommendations(session, market, days=WINDOW, end=analysis_end_date)
        investigate = [i for i, r in enumerate(recs) if r.action == ACTION_INVESTIGATE]
        assert investigate, "Expected at least one data-quality investigation"

        # It must outrank every 'monitor' finding, which is the lowest tier of
        # actionable performance work.
        monitors = [i for i, r in enumerate(recs) if r.action == "monitor"]
        if monitors:
            assert min(investigate) < min(monitors)

    async def test_impact_estimates_are_conservative(
        self, session: AsyncSession, market, analysis_end_date
    ) -> None:
        """No conversion may claim an implausible windfall."""
        recs = await build_recommendations(session, market, days=WINDOW, end=analysis_end_date)
        for r in recs:
            if r.estimated_annual_impact_dollars is not None:
                assert r.estimated_annual_impact_dollars >= 0
                assert r.estimated_annual_impact_dollars < 5_000_000
