"""Planted narrative signals in the synthetic dataset.

The generator does not produce *random* data — it produces data with a **story
already in it**. Four signals are deliberately planted so that every demo, on
every machine, tells the same story, and so the analytics have something
correct to find.

The golden tests in ``tests/test_scenarios.py`` import these constants and
assert the pipeline actually surfaces them. If someone refactors the analytics
and breaks the conclusions, CI fails — the dataset is the test oracle.

    SIGNAL 1  A declining bank        → should be flagged for conversion
    SIGNAL 2  A hot market title      → should be recommended as the target
    SIGNAL 3  A metering anomaly      → should be flagged as data quality
    SIGNAL 4  A strong zone           → should be explicitly left alone

Signal 4 matters more than it looks. An engine that flags everything is
useless; proving SlotSight recommends *no action* on a healthy zone is what
makes the other three recommendations credible.
"""

from __future__ import annotations

from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL 1 — The declining bank
# ═══════════════════════════════════════════════════════════════════════════
# An eight-unit bank of "Sunset Serpent" pennies in Main Floor South. It opened
# at roughly floor-average and has bled off over the trailing 60 days, ending
# near 0.78 of its peer group. Slow enough that nobody noticed on a weekly
# report; obvious the moment you plot the trend.

DECLINING_BANK_ID = "NP-214"
DECLINING_BANK_TITLE = "Sunset Serpent"
DECLINING_BANK_ZONE = "MFS"
DECLINING_BANK_DENOM_CENTS = 1
DECLINING_BANK_UNITS = 8
DECLINING_BANK_FIRST_ASSET = "NP-21401"

# Decay runs over this trailing window, ending at this multiple of where it started.
DECLINING_BANK_WINDOW_DAYS = 60
DECLINING_BANK_END_FACTOR = 0.66

# What the analytics should conclude. Tests assert against these.
DECLINING_BANK_EXPECTED_PEER_INDEX_MAX = 0.85
DECLINING_BANK_EXPECTED_VERDICT = "convert"


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL 2 — The hot market title
# ═══════════════════════════════════════════════════════════════════════════
# "Neon Tiki Riches" is running ~19% above segment average in comparable
# markets and trending up. We own zero units. It is denomination- and
# cabinet-compatible with the declining bank, which makes it the obvious
# conversion target rather than merely an interesting data point.

HOT_MARKET_TITLE = "Neon Tiki Riches"
HOT_MARKET_INDEX = 1.19
HOT_MARKET_TREND_30D_PCT = 6.4
HOT_MARKET_SEGMENT = "Penny Video Reel"

HOT_MARKET_EXPECTED_INDEX_MIN = 1.15


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL 3 — The metering anomaly
# ═══════════════════════════════════════════════════════════════════════════
# One machine reports an actual hold far above its paytable par for a
# contiguous stretch. In the real world this is a bill validator fault, a
# meter rollover, or a miskeyed par — not a genuinely lucrative machine.
#
# This is the trap. A naive "rank by win" engine promotes this machine as a
# top performer and recommends buying more of them. SlotSight must instead
# flag it as untrustworthy data. An analytics tool that cannot say "I don't
# believe this number" is not safe to act on.

ANOMALY_ASSET_NUMBER = "NP-10307"
# Long enough to dominate the default 30-day analysis window. At 12 days the
# fault averaged against 18 healthy days lands at ~1.96x par - just under the
# 2.0 threshold - and the detector correctly stays silent. That is the right
# behaviour and the wrong demo, so the planted fault runs longer.
#
# Note the real property this exposes: a fault DILUTES as the window widens.
# Over 90 days this same machine reads ~1.6x and drops below threshold. Data
# quality checks belong on short windows. See docs/slot-analytics-primer.md.
ANOMALY_WINDOW_DAYS = 21
ANOMALY_HOLD_MULTIPLIER = 3.4

# Flag when observed hold deviates from par by more than this ratio.
ANOMALY_HOLD_DEVIATION_THRESHOLD = 2.0
ANOMALY_EXPECTED_VERDICT = "data_quality"


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL 4 — The healthy zone
# ═══════════════════════════════════════════════════════════════════════════
# High Limit is performing well. Nothing here should be recommended for
# conversion or removal.

HEALTHY_ZONE_CODE = "HL"
HEALTHY_ZONE_BOOST = 1.22
HEALTHY_ZONE_EXPECTED_PEER_INDEX_MIN = 1.05


# ═══════════════════════════════════════════════════════════════════════════
# Manifest
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PlantedSignal:
    """One planted signal, for docs and the /api/floor/signals endpoint."""

    key: str
    headline: str
    detail: str
    expected_outcome: str


PLANTED_SIGNALS: tuple[PlantedSignal, ...] = (
    PlantedSignal(
        key="declining_bank",
        headline=f"{DECLINING_BANK_TITLE} bank {DECLINING_BANK_ID} is fading",
        detail=(
            f"{DECLINING_BANK_UNITS} penny units in {DECLINING_BANK_ZONE} have decayed to "
            f"~{DECLINING_BANK_EXPECTED_PEER_INDEX_MAX:.2f} of peer average over the "
            f"trailing {DECLINING_BANK_WINDOW_DAYS} days."
        ),
        expected_outcome="Flagged for conversion.",
    ),
    PlantedSignal(
        key="hot_market_title",
        headline=f"{HOT_MARKET_TITLE} is outperforming in comparable markets",
        detail=(
            f"Market index {HOT_MARKET_INDEX:.2f} "
            f"(+{(HOT_MARKET_INDEX - 1) * 100:.0f}%), trending "
            f"+{HOT_MARKET_TREND_30D_PCT:.1f}% over 30 days. We own zero units."
        ),
        expected_outcome="Recommended as the conversion target.",
    ),
    PlantedSignal(
        key="metering_anomaly",
        headline=f"{ANOMALY_ASSET_NUMBER} is reporting an implausible hold",
        detail=(
            f"Observed hold runs ~{ANOMALY_HOLD_MULTIPLIER:.1f}x par for "
            f"{ANOMALY_WINDOW_DAYS} days. Consistent with a metering fault, not performance."
        ),
        expected_outcome="Flagged as a data-quality issue, NOT as a top performer.",
    ),
    PlantedSignal(
        key="healthy_zone",
        headline=f"{HEALTHY_ZONE_CODE} is healthy",
        detail=("High Limit is running above peer average. No intervention warranted."),
        expected_outcome="Explicitly recommended for no action.",
    ),
)

__all__ = [
    "ANOMALY_ASSET_NUMBER",
    "ANOMALY_EXPECTED_VERDICT",
    "ANOMALY_HOLD_DEVIATION_THRESHOLD",
    "ANOMALY_HOLD_MULTIPLIER",
    "ANOMALY_WINDOW_DAYS",
    "DECLINING_BANK_END_FACTOR",
    "DECLINING_BANK_EXPECTED_PEER_INDEX_MAX",
    "DECLINING_BANK_EXPECTED_VERDICT",
    "DECLINING_BANK_FIRST_ASSET",
    "DECLINING_BANK_ID",
    "DECLINING_BANK_TITLE",
    "DECLINING_BANK_UNITS",
    "DECLINING_BANK_WINDOW_DAYS",
    "DECLINING_BANK_ZONE",
    "HEALTHY_ZONE_CODE",
    "HEALTHY_ZONE_EXPECTED_PEER_INDEX_MIN",
    "HOT_MARKET_EXPECTED_INDEX_MIN",
    "HOT_MARKET_INDEX",
    "HOT_MARKET_TITLE",
    "PLANTED_SIGNALS",
    "PlantedSignal",
]
