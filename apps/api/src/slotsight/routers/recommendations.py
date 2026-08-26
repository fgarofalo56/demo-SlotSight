"""Recommendations and outliers."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.analytics.floor import machine_metrics
from slotsight.analytics.outliers import (
    detect_data_quality,
    find_top_performers,
    find_underperformers,
)
from slotsight.analytics.recommend import build_recommendations
from slotsight.config import Settings, get_settings
from slotsight.db import get_session
from slotsight.market import MarketIntelProvider
from slotsight.routers.common import (
    get_market_provider,
    to_data_quality_item,
    to_recommendation_item,
    to_top_performer_item,
    to_underperformer_item,
    window_days,
)
from slotsight.schemas import OutliersResponse, RecommendationsResponse

router = APIRouter(tags=["recommendations"])


@router.get(
    "/recommendations",
    response_model=RecommendationsResponse,
    summary="Ranked, evidenced recommendations",
)
async def get_recommendations(
    days: int = Depends(window_days),
    action: str | None = Query(
        default=None, description="convert | remove | monitor | investigate | no_action"
    ),
    priority: str | None = Query(default=None, description="critical | high | medium | low"),
    limit: int = Query(default=50, ge=1, le=200),
    include_no_action: bool = Query(
        default=True,
        description="Include explicit all-clear findings for healthy zones. "
        "Turning this off makes silence ambiguous.",
    ),
    session: AsyncSession = Depends(get_session),
    market: MarketIntelProvider = Depends(get_market_provider),
    settings: Settings = Depends(get_settings),
) -> RecommendationsResponse:
    """Every recommendation carries its evidence, its confidence, and its sources.

    Sorted by priority, then by estimated annual impact. Data-quality findings
    outrank performance findings deliberately: a performance conclusion drawn
    from untrustworthy numbers is worse than no conclusion.
    """
    recs = await build_recommendations(
        session, market, days=days, include_no_action=include_no_action
    )

    if action:
        recs = [r for r in recs if r.action == action]
    if priority:
        recs = [r for r in recs if r.priority == priority]

    total = len(recs)
    return RecommendationsResponse(
        window_days=days,
        generated_for=settings.property_name,
        total=total,
        recommendations=[to_recommendation_item(r) for r in recs[:limit]],
    )


@router.get("/outliers", response_model=OutliersResponse, summary="Outliers and data quality")
async def get_outliers(
    days: int = Depends(window_days),
    limit: int = Query(default=25, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> OutliersResponse:
    """Underperformers, top performers, and machines whose data is untrustworthy.

    Machines with a data-quality flag are excluded from *both* performance
    lists. The highest-"winning" machine in this dataset is a metering fault;
    a rank-by-win leaderboard would promote it.
    """
    unders = await find_underperformers(session, days=days)
    tops = await find_top_performers(session, days=days, limit=limit)
    flags = detect_data_quality(await machine_metrics(session, days=days))

    return OutliersResponse(
        window_days=days,
        underperformers=[to_underperformer_item(u) for u in unders[:limit]],
        top_performers=[to_top_performer_item(t) for t in tops],
        data_quality_flags=[to_data_quality_item(f) for f in flags],
    )
