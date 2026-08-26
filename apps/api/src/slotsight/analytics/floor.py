"""Floor-level aggregation.

This module owns the one query everything else is built on: per-machine
totals over a date window, enriched with peer-relative indices. Outlier
detection and recommendations both consume its output rather than issuing
their own SQL, so there is exactly one definition of "how a machine is doing".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.analytics import metrics as mx
from slotsight.models import DailyPerformance, Machine, Zone

DEFAULT_WINDOW_DAYS = 30

# A cohort smaller than this is not a meaningful benchmark - one unlucky
# machine would swing the average it is being judged against.
MIN_COHORT_SIZE = 6


# ═══════════════════════════════════════════════════════════════════════════
# Result types
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class MachineMetrics:
    """Everything known about one machine's performance over a window."""

    asset_number: str
    bank_id: str
    zone_code: str
    zone_name: str
    title: str
    manufacturer: str
    cabinet: str
    game_type: str
    denomination_cents: int
    par_hold_pct: float

    days: int
    coin_in_cents: int
    theo_win_cents: int
    actual_win_cents: int

    wpupd: float
    coin_in_per_day: float
    hold_pct: float
    hold_deviation: float

    peer_cohort: str
    peer_cohort_size: int
    peer_index: float
    floor_index: float

    @property
    def win_dollars(self) -> float:
        return mx.to_dollars(self.actual_win_cents)

    @property
    def coin_in_dollars(self) -> float:
        return mx.to_dollars(self.coin_in_cents)


@dataclass(frozen=True)
class ZoneMetrics:
    zone_code: str
    zone_name: str
    is_high_limit: bool
    machine_count: int
    coin_in_cents: int
    actual_win_cents: int
    wpupd: float
    hold_pct: float
    peer_index: float
    floor_index: float


@dataclass(frozen=True)
class DailyPoint:
    business_date: date
    coin_in_cents: int
    actual_win_cents: int
    theo_win_cents: int
    active_machines: int

    @property
    def win_dollars(self) -> float:
        return mx.to_dollars(self.actual_win_cents)

    @property
    def coin_in_dollars(self) -> float:
        return mx.to_dollars(self.coin_in_cents)


@dataclass(frozen=True)
class FloorSummary:
    property_name: str
    window_days: int
    start_date: date
    end_date: date
    machine_count: int
    active_machine_count: int
    total_coin_in_cents: int
    total_actual_win_cents: int
    total_theo_win_cents: int
    floor_wpupd: float
    floor_hold_pct: float
    wpupd_change_pct: float
    zones: list[ZoneMetrics] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Window helpers
# ═══════════════════════════════════════════════════════════════════════════
async def latest_business_date(session: AsyncSession) -> date | None:
    """The most recent gaming day present in the data.

    Windows anchor here rather than on ``date.today()`` so that analysis stays
    correct when the dataset is a day or two stale - which is the normal state
    of a warehouse fed by an overnight job.
    """
    result = await session.execute(select(func.max(DailyPerformance.business_date)))
    return result.scalar_one_or_none()


async def resolve_window(
    session: AsyncSession, days: int, end: date | None = None
) -> tuple[date, date]:
    """Resolve a trailing window to concrete inclusive (start, end) dates."""
    end_date = end or await latest_business_date(session) or date.today()
    start_date = end_date - timedelta(days=days - 1)
    return start_date, end_date


# ═══════════════════════════════════════════════════════════════════════════
# The core query
# ═══════════════════════════════════════════════════════════════════════════
def _machine_totals_stmt(start: date, end: date) -> Select[Any]:
    return (
        select(
            Machine.asset_number,
            Machine.bank_id,
            Zone.code.label("zone_code"),
            Zone.name.label("zone_name"),
            Machine.title,
            Machine.manufacturer,
            Machine.cabinet,
            Machine.game_type,
            Machine.denomination_cents,
            Machine.par_hold_pct,
            func.count(DailyPerformance.id).label("days"),
            func.coalesce(func.sum(DailyPerformance.coin_in_cents), 0).label("coin_in"),
            func.coalesce(func.sum(DailyPerformance.theo_win_cents), 0).label("theo_win"),
            func.coalesce(func.sum(DailyPerformance.actual_win_cents), 0).label("actual_win"),
        )
        .join(Zone, Zone.id == Machine.zone_id)
        .join(DailyPerformance, DailyPerformance.asset_number == Machine.asset_number)
        .where(
            DailyPerformance.business_date >= start,
            DailyPerformance.business_date <= end,
            Machine.status == "active",
        )
        .group_by(
            Machine.asset_number,
            Machine.bank_id,
            Zone.code,
            Zone.name,
            Machine.title,
            Machine.manufacturer,
            Machine.cabinet,
            Machine.game_type,
            Machine.denomination_cents,
            Machine.par_hold_pct,
        )
    )


async def machine_metrics(
    session: AsyncSession,
    days: int = DEFAULT_WINDOW_DAYS,
    end: date | None = None,
) -> list[MachineMetrics]:
    """Per-machine metrics over a trailing window, with peer indices.

    Aggregation happens in SQL; indexing happens in Python. That split is
    intentional - computing cohort averages requires two passes over the same
    result set, and at ~840 machines the round trip costs more than the
    arithmetic.
    """
    start, end_date = await resolve_window(session, days, end)
    rows = (await session.execute(_machine_totals_stmt(start, end_date))).all()
    if not rows:
        return []

    # Pass 1 - raw per-machine figures.
    #
    # Postgres SUM() over BIGINT returns NUMERIC, which asyncpg hands back as
    # decimal.Decimal. Coerce at this boundary rather than downstream: Decimal
    # and float do not mix, and letting a Decimal leak into the pure metric
    # functions would make them fail only against a real database and not in
    # unit tests. Money stays exact through the SQL sum; it becomes an int
    # here, and only becomes a float at the ratio.
    raw: list[dict[str, Any]] = []
    for r in rows:
        window_days = max(int(r.days), 1)
        coin_in = int(r.coin_in)
        theo_win = int(r.theo_win)
        actual_win = int(r.actual_win)
        par_hold = float(r.par_hold_pct)

        raw.append(
            {
                "row": r,
                "coin_in": coin_in,
                "theo_win": theo_win,
                "actual_win": actual_win,
                "par_hold": par_hold,
                "days": window_days,
                "wpupd": mx.wpupd(actual_win, window_days),
                "coin_in_per_day": mx.coin_in_per_day(coin_in, window_days),
                "hold_pct": mx.hold_pct(actual_win, coin_in),
                "cohort": mx.peer_cohort_key(int(r.denomination_cents), r.game_type),
            }
        )

    # Pass 2 - cohort and floor averages.
    cohort_totals: dict[str, list[float]] = {}
    for item in raw:
        cohort_totals.setdefault(item["cohort"], []).append(item["wpupd"])

    cohort_avg = {k: sum(v) / len(v) for k, v in cohort_totals.items() if v}
    cohort_size = {k: len(v) for k, v in cohort_totals.items()}
    floor_avg = sum(i["wpupd"] for i in raw) / len(raw)

    # Pass 3 - assemble.
    out: list[MachineMetrics] = []
    for item in raw:
        r = item["row"]
        cohort = item["cohort"]
        size = cohort_size[cohort]

        # Undersized cohort: fall back to the floor average and let the caller
        # see the small size rather than silently trusting a noisy benchmark.
        reference = cohort_avg[cohort] if size >= MIN_COHORT_SIZE else floor_avg

        out.append(
            MachineMetrics(
                asset_number=r.asset_number,
                bank_id=r.bank_id,
                zone_code=r.zone_code,
                zone_name=r.zone_name,
                title=r.title,
                manufacturer=r.manufacturer,
                cabinet=r.cabinet,
                game_type=r.game_type,
                denomination_cents=int(r.denomination_cents),
                par_hold_pct=item["par_hold"],
                days=item["days"],
                coin_in_cents=item["coin_in"],
                theo_win_cents=item["theo_win"],
                actual_win_cents=item["actual_win"],
                wpupd=round(item["wpupd"], 2),
                coin_in_per_day=round(item["coin_in_per_day"], 2),
                hold_pct=round(item["hold_pct"], 5),
                hold_deviation=round(
                    mx.hold_deviation_ratio(item["hold_pct"], item["par_hold"]), 3
                ),
                peer_cohort=cohort,
                peer_cohort_size=size,
                peer_index=round(mx.index_to_average(item["wpupd"], reference), 3),
                floor_index=round(mx.index_to_average(item["wpupd"], floor_avg), 3),
            )
        )

    return out


# ═══════════════════════════════════════════════════════════════════════════
# Rollups
# ═══════════════════════════════════════════════════════════════════════════
def rollup_zones(machines: list[MachineMetrics], high_limit_codes: set[str]) -> list[ZoneMetrics]:
    """Aggregate machine metrics up to zones.

    Note that a zone's ``peer_index`` is the mean of its machines' peer
    indices, not a ratio of sums. That is the honest version: it answers "how
    is a typical machine in this zone doing against its own peers", which is
    what a floor manager is actually asking. A ratio of sums would be
    dominated by whichever denomination happened to have the most units.
    """
    grouped: dict[str, list[MachineMetrics]] = {}
    for m in machines:
        grouped.setdefault(m.zone_code, []).append(m)

    zones: list[ZoneMetrics] = []
    for code, items in grouped.items():
        coin_in = sum(i.coin_in_cents for i in items)
        actual = sum(i.actual_win_cents for i in items)
        days = max((i.days for i in items), default=1)
        zones.append(
            ZoneMetrics(
                zone_code=code,
                zone_name=items[0].zone_name,
                is_high_limit=code in high_limit_codes,
                machine_count=len(items),
                coin_in_cents=coin_in,
                actual_win_cents=actual,
                wpupd=round(mx.wpupd(actual, days) / len(items), 2),
                hold_pct=round(mx.hold_pct(actual, coin_in), 5),
                peer_index=round(sum(i.peer_index for i in items) / len(items), 3),
                floor_index=round(sum(i.floor_index for i in items) / len(items), 3),
            )
        )

    return sorted(zones, key=lambda z: z.peer_index, reverse=True)


async def daily_trend(
    session: AsyncSession, days: int = 90, end: date | None = None
) -> list[DailyPoint]:
    """Floor-wide totals per gaming day, for charting."""
    start, end_date = await resolve_window(session, days, end)
    stmt = (
        select(
            DailyPerformance.business_date,
            func.coalesce(func.sum(DailyPerformance.coin_in_cents), 0).label("coin_in"),
            func.coalesce(func.sum(DailyPerformance.actual_win_cents), 0).label("actual_win"),
            func.coalesce(func.sum(DailyPerformance.theo_win_cents), 0).label("theo_win"),
            func.count(DailyPerformance.id).label("active"),
        )
        .where(
            DailyPerformance.business_date >= start,
            DailyPerformance.business_date <= end_date,
        )
        .group_by(DailyPerformance.business_date)
        .order_by(DailyPerformance.business_date)
    )
    rows = (await session.execute(stmt)).all()
    return [
        DailyPoint(
            business_date=r.business_date,
            coin_in_cents=int(r.coin_in),
            actual_win_cents=int(r.actual_win),
            theo_win_cents=int(r.theo_win),
            active_machines=int(r.active),
        )
        for r in rows
    ]


async def floor_summary(
    session: AsyncSession,
    days: int = DEFAULT_WINDOW_DAYS,
    property_name: str = "Neon Palms Casino Resort",
    end: date | None = None,
) -> FloorSummary:
    """Headline KPIs plus zone breakdown, with period-over-period change."""
    start, end_date = await resolve_window(session, days, end)
    machines = await machine_metrics(session, days=days, end=end_date)

    high_limit_codes = {
        c for (c,) in (await session.execute(select(Zone.code).where(Zone.is_high_limit))).all()
    }

    total_machines = (await session.execute(select(func.count()).select_from(Machine))).scalar_one()

    coin_in = sum(m.coin_in_cents for m in machines)
    actual = sum(m.actual_win_cents for m in machines)
    theo = sum(m.theo_win_cents for m in machines)
    floor_wpupd = sum(m.wpupd for m in machines) / len(machines) if machines else 0.0

    # Same-length immediately-preceding window, for the trend arrow.
    prior_end = start - timedelta(days=1)
    prior = await machine_metrics(session, days=days, end=prior_end)
    prior_wpupd = sum(m.wpupd for m in prior) / len(prior) if prior else 0.0

    return FloorSummary(
        property_name=property_name,
        window_days=days,
        start_date=start,
        end_date=end_date,
        machine_count=int(total_machines),
        active_machine_count=len(machines),
        total_coin_in_cents=coin_in,
        total_actual_win_cents=actual,
        total_theo_win_cents=theo,
        floor_wpupd=round(floor_wpupd, 2),
        floor_hold_pct=round(mx.hold_pct(actual, coin_in), 5),
        wpupd_change_pct=round(mx.pct_change(floor_wpupd, prior_wpupd), 2),
        zones=rollup_zones(machines, high_limit_codes),
    )


async def machine_daily_series(
    session: AsyncSession, asset_number: str, days: int = 90, end: date | None = None
) -> list[DailyPoint]:
    """Daily series for one machine - the trend view behind a detail page."""
    start, end_date = await resolve_window(session, days, end)
    stmt = (
        select(
            DailyPerformance.business_date,
            DailyPerformance.coin_in_cents,
            DailyPerformance.actual_win_cents,
            DailyPerformance.theo_win_cents,
        )
        .where(
            DailyPerformance.asset_number == asset_number,
            DailyPerformance.business_date >= start,
            DailyPerformance.business_date <= end_date,
        )
        .order_by(DailyPerformance.business_date)
    )
    rows = (await session.execute(stmt)).all()
    return [
        DailyPoint(
            business_date=r.business_date,
            coin_in_cents=int(r.coin_in_cents),
            actual_win_cents=int(r.actual_win_cents),
            theo_win_cents=int(r.theo_win_cents),
            active_machines=1,
        )
        for r in rows
    ]


__all__ = [
    "DEFAULT_WINDOW_DAYS",
    "MIN_COHORT_SIZE",
    "DailyPoint",
    "FloorSummary",
    "MachineMetrics",
    "ZoneMetrics",
    "daily_trend",
    "floor_summary",
    "latest_business_date",
    "machine_daily_series",
    "machine_metrics",
    "resolve_window",
    "rollup_zones",
]
