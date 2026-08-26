"""The recommendation engine.

Joins three inputs into actions a floor manager can actually take:

    underperforming banks  (analytics.outliers)
  + market opportunities   (market.MarketIntelProvider)
  + compatibility rules    (here)
  ─────────────────────────────────────────────────
  = ranked, evidenced recommendations

Design commitments, in order of importance:

**Every recommendation carries its evidence.** No card says "convert this"
without the numbers, the comparison group, and the window that produced it.
A recommendation a manager cannot audit is a recommendation they will not act
on - and should not.

**Confidence is stated, not implied.** Recommendations built on synthetic
market data say so, in the payload, all the way to the UI.

**Doing nothing is a valid output.** The engine explicitly emits ``no_action``
for healthy areas. An engine that only ever flags problems trains people to
ignore it.

**Impact estimates are conservative and show their assumptions.** See
``TRANSFER_COEFFICIENT``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.analytics.floor import (
    DEFAULT_WINDOW_DAYS,
    MachineMetrics,
    machine_metrics,
    rollup_zones,
)
from slotsight.analytics.outliers import (
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    BankRollup,
    DataQualityFlag,
    detect_data_quality,
    find_underperformers,
    rollup_to_banks,
)
from slotsight.market import MarketIntelProvider, TitleBenchmark

# ═══════════════════════════════════════════════════════════════════════════
# Tuning
# ═══════════════════════════════════════════════════════════════════════════

# A title running 19% above average in comparable markets will NOT reproduce
# that lift here. Different demographic, different floor position, different
# competitive set. We assume roughly half the observed market edge transfers.
#
# This number is a judgement call, not a measurement, and it is exposed in
# every impact estimate rather than buried. Post-install measurement is what
# replaces it - which is exactly why every conversion recommendation carries a
# 30-day monitoring instruction.
TRANSFER_COEFFICIENT = 0.5

# A conversion target must beat what it replaces by at least this much to be
# worth the cost and downtime of a conversion.
MIN_UPLIFT_TO_RECOMMEND = 0.12

# Below this peer index, replacing the title is unlikely to save the position -
# the problem is probably the floor location, not the game.
REMOVAL_THRESHOLD = 0.62

HEALTHY_ZONE_INDEX = 1.02

ACTION_CONVERT = "convert"
ACTION_REMOVE = "remove"
ACTION_MONITOR = "monitor"
ACTION_INVESTIGATE = "investigate"
ACTION_NO_ACTION = "no_action"

PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"


# ═══════════════════════════════════════════════════════════════════════════
# Result type
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class Recommendation:
    id: str
    action: str
    priority: str
    subject_type: str
    subject_id: str
    headline: str
    rationale: str
    evidence: list[str] = field(default_factory=list)
    suggested_title: str | None = None
    suggested_title_market_index: float | None = None
    estimated_annual_impact_dollars: float | None = None
    confidence: str = CONFIDENCE_MEDIUM
    uses_synthetic_market_data: bool = False
    data_sources: list[str] = field(default_factory=list)
    monitoring_instruction: str | None = None


# ═══════════════════════════════════════════════════════════════════════════
# Compatibility
# ═══════════════════════════════════════════════════════════════════════════
_SEGMENT_DENOM = {
    "penny": 1,
    "nickel": 5,
    "quarter": 25,
    "dollar": 100,
    "high limit": 500,
}

_SEGMENT_TYPE = {
    "video reel": "video_reel",
    "mechanical reel": "mechanical_reel",
    "video poker": "video_poker",
    "multigame": "keno_multigame",
}


def _parse_segment(segment: str) -> tuple[int | None, str | None]:
    """Map a market segment label back to (denomination_cents, game_type)."""
    low = segment.lower()
    denom = next((v for k, v in _SEGMENT_DENOM.items() if k in low), None)
    gtype = next((v for k, v in _SEGMENT_TYPE.items() if k in low), None)
    return denom, gtype


def is_compatible(bank: BankRollup, benchmark: TitleBenchmark) -> bool:
    """Can this title physically replace this bank?

    A conversion swaps the game, not the cabinet. Denomination and game type
    have to match, or it is a purchase, not a conversion - a different
    conversation with a different budget line.
    """
    denom, gtype = _parse_segment(benchmark.segment)
    if denom is not None and denom != bank.denomination_cents:
        return False
    return not (gtype is not None and gtype != bank.game_type)


def _estimate_annual_impact(
    bank: BankRollup, benchmark: TitleBenchmark, peer_avg_wpupd: float
) -> float:
    """Conservative annual win uplift, in dollars, if the conversion lands.

    uplift_index = (market_index - current_index) x TRANSFER_COEFFICIENT
    dollars      = uplift_index x peer_avg_wpupd x units x 365
    """
    uplift_index = (benchmark.market_index - bank.avg_peer_index) * TRANSFER_COEFFICIENT
    if uplift_index <= 0:
        return 0.0
    return round(uplift_index * peer_avg_wpupd * bank.unit_count * 365, 2)


# ═══════════════════════════════════════════════════════════════════════════
# Builders
# ═══════════════════════════════════════════════════════════════════════════
def _conversion_recommendation(
    bank: BankRollup,
    candidates: list[TitleBenchmark],
    owned_titles: set[str],
    peer_avg_wpupd: float,
    provider_name: str,
    is_synthetic: bool,
    window_days: int,
) -> Recommendation | None:
    """Pick the best compatible, rising, not-already-owned title for a bank."""
    viable = [
        b
        for b in candidates
        if is_compatible(bank, b)
        and b.title not in owned_titles
        and (b.market_index - bank.avg_peer_index) >= MIN_UPLIFT_TO_RECOMMEND
    ]
    if not viable:
        return None

    # Rank on market index, but let a strong upward trend break ties - a title
    # on the way up is a better bet than an equal one that has plateaued.
    best = max(viable, key=lambda b: b.market_index + (b.trend_30d_pct / 100.0))
    impact = _estimate_annual_impact(bank, best, peer_avg_wpupd)

    priority = (
        PRIORITY_CRITICAL
        if bank.severity == SEVERITY_CRITICAL
        else PRIORITY_HIGH
        if bank.severity == SEVERITY_WARNING
        else PRIORITY_MEDIUM
    )

    drop = bank.avg_prior_peer_index - bank.avg_peer_index
    evidence = [
        f"{bank.flagged_units} of {bank.unit_count} units in bank {bank.bank_id} "
        f"are below peer average.",
        f"Bank peer index {bank.avg_peer_index:.2f} over the trailing {window_days} days "
        f"(prior window {bank.avg_prior_peer_index:.2f}, "
        f"{'down' if drop > 0 else 'up'} {abs(drop):.2f}).",
        f"Average WPUPD ${bank.avg_wpupd:,.2f} against a peer average of ${peer_avg_wpupd:,.2f}.",
        f"{best.title} indexes {best.market_index:.2f} in comparable markets "
        f"({best.outperformance_pct:+.0f}%), trending {best.trend_30d_pct:+.1f}% "
        f"over 30 days.",
        f"{best.title} is compatible: same denomination "
        f"({bank.denomination_cents}¢) and game type ({bank.game_type}).",
        f"We currently operate zero units of {best.title}.",
    ]

    return Recommendation(
        id=f"convert-{bank.bank_id}",
        action=ACTION_CONVERT,
        priority=priority,
        subject_type="bank",
        subject_id=bank.bank_id,
        headline=(f"Convert bank {bank.bank_id} ({bank.title}) to {best.title}"),
        rationale=(
            f"Bank {bank.bank_id} in {bank.zone_name} has fallen to "
            f"{bank.avg_peer_index:.2f} of its peer group and the decline is sustained "
            f"across two consecutive {window_days}-day windows. {best.title} is "
            f"outperforming by {best.outperformance_pct:.0f}% in comparable markets and "
            f"is a drop-in fit for the existing cabinets."
        ),
        evidence=evidence,
        suggested_title=best.title,
        suggested_title_market_index=best.market_index,
        estimated_annual_impact_dollars=impact,
        confidence=CONFIDENCE_MEDIUM if is_synthetic else CONFIDENCE_HIGH,
        uses_synthetic_market_data=is_synthetic,
        data_sources=["Internal daily meter data", provider_name],
        monitoring_instruction=(
            f"Measure for 30 days post-install against the same peer cohort. The "
            f"${impact:,.0f} estimate assumes only {TRANSFER_COEFFICIENT:.0%} of the "
            f"observed market edge transfers to this floor - post-install measurement "
            f"replaces that assumption with a real number."
        ),
    )


def _removal_recommendation(
    bank: BankRollup, peer_avg_wpupd: float, window_days: int
) -> Recommendation:
    return Recommendation(
        id=f"remove-{bank.bank_id}",
        action=ACTION_REMOVE,
        priority=PRIORITY_CRITICAL,
        subject_type="bank",
        subject_id=bank.bank_id,
        headline=f"Reclaim floor space from bank {bank.bank_id} ({bank.title})",
        rationale=(
            f"At {bank.avg_peer_index:.2f} of peer average, bank {bank.bank_id} is far "
            f"enough below its cohort that a title swap is unlikely to recover the "
            f"position. This pattern usually indicates the floor location rather than "
            f"the game. Consider reclaiming the space or relocating the bank."
        ),
        evidence=[
            f"Peer index {bank.avg_peer_index:.2f} - below the {REMOVAL_THRESHOLD:.2f} "
            f"threshold where conversions stop paying back.",
            f"{bank.flagged_units} of {bank.unit_count} units flagged over {window_days} days.",
            f"Average WPUPD ${bank.avg_wpupd:,.2f} vs peer ${peer_avg_wpupd:,.2f}.",
            f"Located in {bank.zone_name}.",
        ],
        confidence=CONFIDENCE_MEDIUM,
        data_sources=["Internal daily meter data"],
        monitoring_instruction=(
            "Before removing, verify the position itself - check adjacent banks in the "
            "same row. If neighbours are also weak, the problem is the location."
        ),
    )


def _data_quality_recommendation(flag: DataQualityFlag) -> Recommendation:
    return Recommendation(
        id=f"investigate-{flag.asset_number}",
        action=ACTION_INVESTIGATE,
        priority=PRIORITY_HIGH,
        subject_type="machine",
        subject_id=flag.asset_number,
        headline=f"Verify metering on {flag.asset_number} ({flag.title})",
        rationale=(
            f"{flag.asset_number} is reporting a realized hold of "
            f"{flag.observed_hold_pct * 100:.1f}%, which is {flag.deviation_ratio:.1f}x "
            f"its paytable par of {flag.par_hold_pct * 100:.1f}%. This machine's numbers "
            f"are excluded from performance rankings until the meter is verified - "
            f"treating them as real would distort the floor average and could prompt "
            f"buying more of a broken unit."
        ),
        evidence=[flag.detail, f"Located in zone {flag.zone_code}."],
        confidence=CONFIDENCE_HIGH,
        data_sources=["Internal daily meter data"],
        monitoring_instruction=(
            "Have a technician verify the bill validator and meter readings. Re-run "
            "this analysis once corrected data is available."
        ),
    )


def _no_action_recommendation(
    zone_code: str, zone_name: str, peer_index: float, units: int
) -> Recommendation:
    return Recommendation(
        id=f"no-action-{zone_code}",
        action=ACTION_NO_ACTION,
        priority=PRIORITY_LOW,
        subject_type="zone",
        subject_id=zone_code,
        headline=f"{zone_name} is healthy - no action recommended",
        rationale=(
            f"{zone_name} is running at {peer_index:.2f} of peer average across "
            f"{units} units. Nothing here warrants conversion or removal. Reported "
            f"explicitly so the absence of a flag reads as a checked result rather "
            f"than an oversight."
        ),
        evidence=[
            f"Zone peer index {peer_index:.2f} across {units} machines.",
            "No sustained underperformers detected in this zone.",
        ],
        confidence=CONFIDENCE_HIGH,
        data_sources=["Internal daily meter data"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════
_PRIORITY_ORDER = {
    PRIORITY_CRITICAL: 0,
    PRIORITY_HIGH: 1,
    PRIORITY_MEDIUM: 2,
    PRIORITY_LOW: 3,
}


async def build_recommendations(
    session: AsyncSession,
    market: MarketIntelProvider,
    days: int = DEFAULT_WINDOW_DAYS,
    end: date | None = None,
    include_no_action: bool = True,
) -> list[Recommendation]:
    """Produce the full ranked recommendation set for a window."""
    machines: list[MachineMetrics] = await machine_metrics(session, days=days, end=end)
    if not machines:
        return []

    underperformers = await find_underperformers(session, days=days, end=end)
    banks = rollup_to_banks(underperformers, machines)
    quality_flags = detect_data_quality(machines)
    benchmarks = await market.title_benchmarks()
    owned_titles = {m.title for m in machines}

    recommendations: list[Recommendation] = []

    # ── 1. Data quality first. These outrank performance findings, because a
    #       performance finding built on bad data is worse than none. ────────
    recommendations.extend(_data_quality_recommendation(f) for f in quality_flags)

    # ── 2. Bank-level conversions and removals ─────────────────────────────
    for bank in banks:
        cohort = [
            m
            for m in machines
            if m.denomination_cents == bank.denomination_cents and m.game_type == bank.game_type
        ]
        peer_avg_wpupd = sum(m.wpupd for m in cohort) / len(cohort) if cohort else bank.avg_wpupd

        if bank.avg_peer_index < REMOVAL_THRESHOLD:
            recommendations.append(_removal_recommendation(bank, peer_avg_wpupd, days))
            continue

        rec = _conversion_recommendation(
            bank,
            benchmarks,
            owned_titles,
            peer_avg_wpupd,
            market.name,
            market.is_synthetic,
            days,
        )
        if rec is not None:
            recommendations.append(rec)
        else:
            recommendations.append(
                Recommendation(
                    id=f"monitor-{bank.bank_id}",
                    action=ACTION_MONITOR,
                    priority=PRIORITY_MEDIUM,
                    subject_type="bank",
                    subject_id=bank.bank_id,
                    headline=f"Monitor bank {bank.bank_id} ({bank.title})",
                    rationale=(
                        f"Bank {bank.bank_id} is underperforming at "
                        f"{bank.avg_peer_index:.2f} of peer average, but no compatible "
                        f"replacement title currently clears the "
                        f"{MIN_UPLIFT_TO_RECOMMEND:.0%} uplift bar. Converting to a "
                        f"marginally better title would not repay the downtime."
                    ),
                    evidence=[
                        f"Peer index {bank.avg_peer_index:.2f} across "
                        f"{bank.flagged_units}/{bank.unit_count} flagged units.",
                        f"No compatible title in the market feed beats it by "
                        f"{MIN_UPLIFT_TO_RECOMMEND:.0%} or more.",
                    ],
                    confidence=CONFIDENCE_MEDIUM,
                    uses_synthetic_market_data=market.is_synthetic,
                    data_sources=["Internal daily meter data", market.name],
                )
            )

    # ── 3. Explicit all-clear for healthy zones ────────────────────────────
    if include_no_action:
        # A zone is disqualified only by a *serious* finding. A single
        # watch-level bank should not suppress the all-clear for an otherwise
        # healthy zone - if it did, no zone would ever be reported healthy on
        # a floor of this size, and the all-clear would be dead code that
        # never fires. Silence would then be ambiguous: the manager could not
        # tell "checked and fine" from "not checked".
        serious_zones = {
            b.zone_code for b in banks if b.severity in (SEVERITY_CRITICAL, SEVERITY_WARNING)
        }
        for zone in rollup_zones(machines, high_limit_codes=set()):
            if zone.zone_code in serious_zones or zone.peer_index < HEALTHY_ZONE_INDEX:
                continue
            recommendations.append(
                _no_action_recommendation(
                    zone.zone_code, zone.zone_name, zone.peer_index, zone.machine_count
                )
            )

    recommendations.sort(
        key=lambda r: (
            _PRIORITY_ORDER.get(r.priority, 9),
            -(r.estimated_annual_impact_dollars or 0.0),
        )
    )
    return recommendations


__all__ = [
    "ACTION_CONVERT",
    "ACTION_INVESTIGATE",
    "ACTION_MONITOR",
    "ACTION_NO_ACTION",
    "ACTION_REMOVE",
    "MIN_UPLIFT_TO_RECOMMEND",
    "REMOVAL_THRESHOLD",
    "TRANSFER_COEFFICIENT",
    "Recommendation",
    "build_recommendations",
    "is_compatible",
]
