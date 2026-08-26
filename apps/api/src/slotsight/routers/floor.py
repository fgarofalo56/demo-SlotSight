"""Floor-level endpoints: summary KPIs, trend, and the teaching signals view."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.analytics.floor import daily_trend, floor_summary
from slotsight.config import Settings, get_settings
from slotsight.db import get_session
from slotsight.routers.common import to_trend_point, to_zone_summary, window_days
from slotsight.schemas import (
    FloorSummaryResponse,
    PlantedSignalItem,
    SignalsResponse,
    TrendResponse,
)
from slotsight.seed.scenarios import PLANTED_SIGNALS

router = APIRouter(prefix="/floor", tags=["floor"])


@router.get("/summary", response_model=FloorSummaryResponse, summary="Floor KPIs")
async def get_summary(
    days: int = Depends(window_days),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> FloorSummaryResponse:
    """Headline KPIs plus a per-zone breakdown.

    Both ``peer_index`` and ``floor_index`` are returned for every zone. The
    gap between them is the point: High Limit reads far above average on a
    floor-wide index purely because of denomination, and roughly at par
    against its actual peers. Only one of those is actionable.
    """
    s = await floor_summary(session, days=days, property_name=settings.property_name)
    return FloorSummaryResponse(
        property_name=s.property_name,
        window_days=s.window_days,
        start_date=s.start_date,
        end_date=s.end_date,
        machine_count=s.machine_count,
        active_machine_count=s.active_machine_count,
        coin_in_dollars=round(s.total_coin_in_cents / 100, 2),
        win_dollars=round(s.total_actual_win_cents / 100, 2),
        theo_win_dollars=round(s.total_theo_win_cents / 100, 2),
        floor_wpupd=s.floor_wpupd,
        floor_hold_pct=s.floor_hold_pct,
        wpupd_change_pct=s.wpupd_change_pct,
        zones=[to_zone_summary(z) for z in s.zones],
    )


@router.get("/trend", response_model=TrendResponse, summary="Daily floor trend")
async def get_trend(
    days: int = 90,
    session: AsyncSession = Depends(get_session),
) -> TrendResponse:
    """Floor-wide daily totals, for charting."""
    days = max(1, min(days, 365))
    points = await daily_trend(session, days=days)
    return TrendResponse(window_days=days, points=[to_trend_point(p) for p in points])


@router.get("/signals", response_model=SignalsResponse, summary="Planted demo signals")
async def get_signals() -> SignalsResponse:
    """The narrative signals deliberately planted in the synthetic dataset.

    A teaching endpoint with no production analogue. It exists so a reader can
    check SlotSight's conclusions against a ground truth we control - which is
    exactly what the golden tests do programmatically.
    """
    return SignalsResponse(
        explanation=(
            "This dataset is generated, not random. Four signals are planted so the "
            "analytics have something correct to find and every demo tells the same "
            "story. The golden tests in tests/test_scenarios.py assert that the "
            "pipeline actually surfaces each one."
        ),
        signals=[
            PlantedSignalItem(
                key=s.key,
                headline=s.headline,
                detail=s.detail,
                expected_outcome=s.expected_outcome,
            )
            for s in PLANTED_SIGNALS
        ],
    )
