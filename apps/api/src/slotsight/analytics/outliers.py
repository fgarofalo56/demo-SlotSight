"""Outlier detection: underperformers, top performers, and untrustworthy data.

Three rules shape this module, and they are the difference between an engine
a floor manager will act on and one they will quietly stop opening.

1. **Data quality is evaluated first, and its findings are removed from every
   other list.** A machine reporting three times its par hold is not a star
   performer to buy more of - it is a broken meter. An engine that cannot say
   "I don't believe this number" is not safe to act on.

2. **One bad window is not evidence.** Slot results are genuinely volatile in
   the short run; a machine can trail its peers for three weeks on variance
   alone. Nothing is flagged unless the prior window agrees or the trend is
   clearly and consistently down.

3. **Comparisons are peer-relative, never floor-wide.** See
   ``metrics.peer_cohort_key`` for why this matters so much.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.analytics import metrics as mx
from slotsight.analytics.floor import (
    DEFAULT_WINDOW_DAYS,
    MachineMetrics,
    machine_metrics,
    resolve_window,
)

# Peer index at or below this is a candidate for intervention.
UNDERPERFORM_THRESHOLD = 0.85

# Peer index at or above this is a standout.
OUTPERFORM_THRESHOLD = 1.15

# Realized hold this many times par (or this fraction of it) is implausible.
HOLD_DEVIATION_HIGH = 2.0
HOLD_DEVIATION_LOW = 0.25

# A machine needs at least this much coin-in per day before its ratios mean
# anything. Below it, hold percentages swing wildly on a handful of spins.
MIN_COIN_IN_PER_DAY_DOLLARS = 150.0

SEVERITY_CRITICAL = "critical"
SEVERITY_WARNING = "warning"
SEVERITY_WATCH = "watch"


# ═══════════════════════════════════════════════════════════════════════════
# Result types
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class DataQualityFlag:
    """A machine whose numbers should not be trusted."""

    asset_number: str
    title: str
    zone_code: str
    issue: str
    observed_hold_pct: float
    par_hold_pct: float
    deviation_ratio: float
    detail: str

    @property
    def verdict(self) -> str:
        return "data_quality"


@dataclass(frozen=True)
class Underperformer:
    machine: MachineMetrics
    peer_index: float
    prior_peer_index: float
    index_change: float
    sustained: bool
    severity: str
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TopPerformer:
    machine: MachineMetrics
    peer_index: float
    prior_peer_index: float
    index_change: float


@dataclass(frozen=True)
class BankRollup:
    """Underperformance aggregated to the bank.

    Conversions are executed at bank granularity - a tech does not swap one
    machine out of an eight-unit bank of the same title. Recommendations are
    therefore only useful at this level.
    """

    bank_id: str
    zone_code: str
    zone_name: str
    title: str
    manufacturer: str
    cabinet: str
    game_type: str
    denomination_cents: int
    unit_count: int
    flagged_units: int
    avg_peer_index: float
    avg_prior_peer_index: float
    total_win_cents: int
    avg_wpupd: float
    severity: str


# ═══════════════════════════════════════════════════════════════════════════
# 1. Data quality - runs first, poisons nothing downstream
# ═══════════════════════════════════════════════════════════════════════════
def detect_data_quality(machines: list[MachineMetrics]) -> list[DataQualityFlag]:
    """Find machines whose realized hold is inconsistent with their paytable."""
    flags: list[DataQualityFlag] = []

    for m in machines:
        # Too quiet to judge - ratios on tiny samples are noise, not signal.
        if m.coin_in_per_day < MIN_COIN_IN_PER_DAY_DOLLARS:
            continue

        dev = m.hold_deviation

        if dev >= HOLD_DEVIATION_HIGH:
            flags.append(
                DataQualityFlag(
                    asset_number=m.asset_number,
                    title=m.title,
                    zone_code=m.zone_code,
                    issue="hold_above_par",
                    observed_hold_pct=m.hold_pct,
                    par_hold_pct=m.par_hold_pct,
                    deviation_ratio=dev,
                    detail=(
                        f"Realized hold {m.hold_pct * 100:.1f}% is {dev:.1f}x the "
                        f"paytable par of {m.par_hold_pct * 100:.1f}%. Sustained hold "
                        f"this far above par is characteristic of a metering or bill "
                        f"validator fault, not genuine performance. Verify the meter "
                        f"before treating this machine's numbers as real."
                    ),
                )
            )
        elif 0 < dev <= HOLD_DEVIATION_LOW:
            flags.append(
                DataQualityFlag(
                    asset_number=m.asset_number,
                    title=m.title,
                    zone_code=m.zone_code,
                    issue="hold_below_par",
                    observed_hold_pct=m.hold_pct,
                    par_hold_pct=m.par_hold_pct,
                    deviation_ratio=dev,
                    detail=(
                        f"Realized hold {m.hold_pct * 100:.1f}% is only {dev:.2f}x par "
                        f"({m.par_hold_pct * 100:.1f}%). Check for an unrecorded jackpot "
                        f"payout or a paytable mismatch."
                    ),
                )
            )

    return sorted(flags, key=lambda f: abs(f.deviation_ratio - 1.0), reverse=True)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Underperformers
# ═══════════════════════════════════════════════════════════════════════════
def _severity_for(peer_index: float, sustained: bool) -> str:
    if peer_index < 0.70 and sustained:
        return SEVERITY_CRITICAL
    if peer_index < UNDERPERFORM_THRESHOLD and sustained:
        return SEVERITY_WARNING
    return SEVERITY_WATCH


async def find_underperformers(
    session: AsyncSession,
    days: int = DEFAULT_WINDOW_DAYS,
    threshold: float = UNDERPERFORM_THRESHOLD,
    end: date | None = None,
) -> list[Underperformer]:
    """Machines trailing their peer cohort, confirmed against a prior window."""
    start, end_date = await resolve_window(session, days, end)
    current = await machine_metrics(session, days=days, end=end_date)
    prior = await machine_metrics(session, days=days, end=start - timedelta(days=1))
    prior_by_asset = {m.asset_number: m for m in prior}

    excluded = {f.asset_number for f in detect_data_quality(current)}

    results: list[Underperformer] = []
    for m in current:
        if m.asset_number in excluded or m.peer_index >= threshold:
            continue

        p = prior_by_asset.get(m.asset_number)
        prior_index = p.peer_index if p else m.peer_index
        change = round(m.peer_index - prior_index, 3)

        # Sustained means either it was already weak, or it is falling fast.
        sustained = prior_index < (threshold + 0.10) or change <= -0.08

        evidence = [
            f"Peer index {m.peer_index:.2f} against {m.peer_cohort_size} comparable "
            f"units ({m.peer_cohort.replace(':', '¢ ')}).",
            f"WPUPD ${m.wpupd:,.2f} over {m.days} days.",
        ]
        if p:
            direction = "down" if change < 0 else "up"
            evidence.append(
                f"Prior {days}-day window indexed {prior_index:.2f} "
                f"({direction} {abs(change):.2f})."
            )
        if not sustained:
            evidence.append(
                "Prior window was healthy - this may be short-run variance. Watch only."
            )

        results.append(
            Underperformer(
                machine=m,
                peer_index=m.peer_index,
                prior_peer_index=round(prior_index, 3),
                index_change=change,
                sustained=sustained,
                severity=_severity_for(m.peer_index, sustained),
                evidence=evidence,
            )
        )

    return sorted(results, key=lambda u: u.peer_index)


async def find_top_performers(
    session: AsyncSession,
    days: int = DEFAULT_WINDOW_DAYS,
    threshold: float = OUTPERFORM_THRESHOLD,
    limit: int = 20,
    end: date | None = None,
) -> list[TopPerformer]:
    """Standouts, with data-quality flags removed.

    That exclusion is the whole point. The single highest-"winning" machine in
    this dataset is a broken meter; a rank-by-win leaderboard would put it at
    the top and invite someone to order eight more.
    """
    start, end_date = await resolve_window(session, days, end)
    current = await machine_metrics(session, days=days, end=end_date)
    prior = await machine_metrics(session, days=days, end=start - timedelta(days=1))
    prior_by_asset = {m.asset_number: m for m in prior}

    excluded = {f.asset_number for f in detect_data_quality(current)}

    results: list[TopPerformer] = []
    for m in current:
        if m.asset_number in excluded or m.peer_index < threshold:
            continue
        p = prior_by_asset.get(m.asset_number)
        prior_index = p.peer_index if p is not None else m.peer_index
        results.append(
            TopPerformer(
                machine=m,
                peer_index=m.peer_index,
                prior_peer_index=round(prior_index, 3),
                index_change=round(m.peer_index - prior_index, 3),
            )
        )

    return sorted(results, key=lambda t: t.peer_index, reverse=True)[:limit]


# ═══════════════════════════════════════════════════════════════════════════
# 3. Bank rollup
# ═══════════════════════════════════════════════════════════════════════════
def rollup_to_banks(
    underperformers: list[Underperformer],
    all_machines: list[MachineMetrics],
    min_flagged_share: float = 0.5,
) -> list[BankRollup]:
    """Aggregate flagged machines into bank-level findings.

    A bank is only reported when a majority of its units are flagged. One weak
    machine in an otherwise healthy bank is a service call, not a conversion -
    and recommending a conversion for it would burn the operator's trust.
    """
    by_bank: dict[str, list[MachineMetrics]] = {}
    for m in all_machines:
        by_bank.setdefault(m.bank_id, []).append(m)

    flagged_by_bank: dict[str, list[Underperformer]] = {}
    for u in underperformers:
        flagged_by_bank.setdefault(u.machine.bank_id, []).append(u)

    rollups: list[BankRollup] = []
    for bank_id, flagged in flagged_by_bank.items():
        units = by_bank.get(bank_id, [])
        if not units or len(flagged) / len(units) < min_flagged_share:
            continue

        head = flagged[0].machine
        severities = {u.severity for u in flagged}
        severity = (
            SEVERITY_CRITICAL
            if SEVERITY_CRITICAL in severities
            else SEVERITY_WARNING
            if SEVERITY_WARNING in severities
            else SEVERITY_WATCH
        )

        rollups.append(
            BankRollup(
                bank_id=bank_id,
                zone_code=head.zone_code,
                zone_name=head.zone_name,
                title=head.title,
                manufacturer=head.manufacturer,
                cabinet=head.cabinet,
                game_type=head.game_type,
                denomination_cents=head.denomination_cents,
                unit_count=len(units),
                flagged_units=len(flagged),
                avg_peer_index=round(sum(u.peer_index for u in flagged) / len(flagged), 3),
                avg_prior_peer_index=round(
                    sum(u.prior_peer_index for u in flagged) / len(flagged), 3
                ),
                total_win_cents=sum(u.machine.actual_win_cents for u in flagged),
                avg_wpupd=round(sum(u.machine.wpupd for u in flagged) / len(flagged), 2),
                severity=severity,
            )
        )

    return sorted(rollups, key=lambda b: b.avg_peer_index)


def trend_direction(series: list[float]) -> tuple[float, str]:
    """Slope of a series plus a human label."""
    slope = mx.linear_trend_slope(series)
    if slope < -0.5:
        return slope, "declining"
    if slope > 0.5:
        return slope, "improving"
    return slope, "flat"


__all__ = [
    "HOLD_DEVIATION_HIGH",
    "HOLD_DEVIATION_LOW",
    "MIN_COIN_IN_PER_DAY_DOLLARS",
    "OUTPERFORM_THRESHOLD",
    "SEVERITY_CRITICAL",
    "SEVERITY_WARNING",
    "SEVERITY_WATCH",
    "UNDERPERFORM_THRESHOLD",
    "BankRollup",
    "DataQualityFlag",
    "TopPerformer",
    "Underperformer",
    "detect_data_quality",
    "find_top_performers",
    "find_underperformers",
    "rollup_to_banks",
    "trend_direction",
]
