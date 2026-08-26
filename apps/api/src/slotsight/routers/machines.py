"""Machine listing, filtering, and detail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.analytics.floor import machine_daily_series, machine_metrics
from slotsight.analytics.outliers import detect_data_quality
from slotsight.db import get_session
from slotsight.routers.common import (
    to_data_quality_item,
    to_machine_summary,
    to_trend_point,
    window_days,
)
from slotsight.schemas import (
    MachineDetailResponse,
    MachineListResponse,
)

router = APIRouter(prefix="/machines", tags=["machines"])

SORT_FIELDS = {
    "peer_index": lambda m: m.peer_index,
    "wpupd": lambda m: m.wpupd,
    "coin_in": lambda m: m.coin_in_cents,
    "hold_pct": lambda m: m.hold_pct,
    "asset_number": lambda m: m.asset_number,
}


@router.get("", response_model=MachineListResponse, summary="List machines with metrics")
async def list_machines(
    days: int = Depends(window_days),
    zone: str | None = Query(default=None, description="Zone code, e.g. MFS"),
    denomination_cents: int | None = Query(default=None, description="e.g. 1 for penny"),
    game_type: str | None = Query(default=None, description="e.g. video_reel"),
    title: str | None = Query(default=None, description="Exact game title"),
    bank_id: str | None = Query(default=None, description="e.g. NP-214"),
    max_peer_index: float | None = Query(default=None, description="Only at or below this"),
    min_peer_index: float | None = Query(default=None, description="Only at or above this"),
    sort: str = Query(default="peer_index", description=f"One of: {', '.join(SORT_FIELDS)}"),
    descending: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=1_000),
    session: AsyncSession = Depends(get_session),
) -> MachineListResponse:
    """Filtered, sorted machine metrics for a trailing window.

    This is the single endpoint the chat agent's ``find_underperformers`` and
    ``search_machines`` tools sit on, which is why the filter set is broader
    than the UI strictly needs - a natural-language question can slice the
    floor in ways a fixed screen cannot.
    """
    if sort not in SORT_FIELDS:
        raise HTTPException(422, f"Unknown sort field '{sort}'. Valid: {', '.join(SORT_FIELDS)}")

    machines = await machine_metrics(session, days=days)

    if zone:
        machines = [m for m in machines if m.zone_code.upper() == zone.upper()]
    if denomination_cents is not None:
        machines = [m for m in machines if m.denomination_cents == denomination_cents]
    if game_type:
        machines = [m for m in machines if m.game_type == game_type]
    if title:
        machines = [m for m in machines if m.title.lower() == title.lower()]
    if bank_id:
        machines = [m for m in machines if m.bank_id.upper() == bank_id.upper()]
    if max_peer_index is not None:
        machines = [m for m in machines if m.peer_index <= max_peer_index]
    if min_peer_index is not None:
        machines = [m for m in machines if m.peer_index >= min_peer_index]

    total = len(machines)
    machines.sort(key=SORT_FIELDS[sort], reverse=descending)
    page = machines[:limit]

    return MachineListResponse(
        window_days=days,
        total=total,
        returned=len(page),
        machines=[to_machine_summary(m) for m in page],
    )


@router.get(
    "/{asset_number}",
    response_model=MachineDetailResponse,
    summary="Single machine detail with trend",
)
async def get_machine(
    asset_number: str,
    days: int = Depends(window_days),
    trend_days: int = Query(default=90, ge=7, le=365),
    session: AsyncSession = Depends(get_session),
) -> MachineDetailResponse:
    machines = await machine_metrics(session, days=days)
    target = next((m for m in machines if m.asset_number.upper() == asset_number.upper()), None)
    if target is None:
        raise HTTPException(404, f"Machine '{asset_number}' not found or has no data in window.")

    cohort = [m for m in machines if m.peer_cohort == target.peer_cohort]
    peer_avg = round(sum(m.wpupd for m in cohort) / len(cohort), 2) if cohort else 0.0

    flag = next(
        (f for f in detect_data_quality(machines) if f.asset_number == target.asset_number),
        None,
    )
    series = await machine_daily_series(session, target.asset_number, days=trend_days)

    return MachineDetailResponse(
        machine=to_machine_summary(target),
        trend=[to_trend_point(p) for p in series],
        peer_average_wpupd=peer_avg,
        data_quality_flag=to_data_quality_item(flag) if flag else None,
    )
