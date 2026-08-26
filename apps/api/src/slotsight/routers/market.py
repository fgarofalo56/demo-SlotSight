"""Market intelligence endpoints.

Every response carries ``is_synthetic: true`` and a disclaimer. That is not
decoration - a recommendation grounded in invented benchmarks must never reach
a screen looking like one grounded in real market data. See NOTICE.md.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.db import get_session
from slotsight.market import MarketIntelProvider
from slotsight.models import Machine
from slotsight.routers.common import (
    SYNTHETIC_DISCLAIMER,
    get_market_provider,
    to_competitor_item,
    to_market_title_item,
)
from slotsight.schemas import CompetitorsResponse, MarketResponse

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/titles", response_model=MarketResponse, summary="Title benchmarks")
async def get_market_titles(
    segment: str | None = Query(default=None, description="e.g. 'Penny Video Reel'"),
    rising_only: bool = Query(default=False, description="Only titles trending up"),
    exclude_owned: bool = Query(
        default=False, description="Only titles we do NOT currently operate"
    ),
    session: AsyncSession = Depends(get_session),
    market: MarketIntelProvider = Depends(get_market_provider),
) -> MarketResponse:
    """Benchmark performance for game titles in comparable markets.

    ``on_our_floor`` is the field that makes this actionable: a high-indexing
    title we already operate is confirmation, while a high-indexing title we
    do *not* operate is an opportunity.
    """
    benchmarks = await market.title_benchmarks(segment=segment)
    owned = {t for (t,) in (await session.execute(select(Machine.title).distinct())).all()}

    if rising_only:
        benchmarks = [b for b in benchmarks if b.is_rising]
    if exclude_owned:
        benchmarks = [b for b in benchmarks if b.title not in owned]

    return MarketResponse(
        provider_name=market.name,
        is_synthetic=market.is_synthetic,
        disclaimer=SYNTHETIC_DISCLAIMER,
        titles=[to_market_title_item(b, on_our_floor=b.title in owned) for b in benchmarks],
    )


@router.get("/competitors", response_model=CompetitorsResponse, summary="Competitor sightings")
async def get_competitors(
    title: str | None = Query(default=None, description="Filter to one title"),
    market: MarketIntelProvider = Depends(get_market_provider),
) -> CompetitorsResponse:
    """What nearby (fictional) properties are running."""
    sightings = await market.competitor_offerings(title=title)
    return CompetitorsResponse(
        provider_name=market.name,
        is_synthetic=market.is_synthetic,
        disclaimer=SYNTHETIC_DISCLAIMER,
        sightings=[to_competitor_item(c) for c in sightings],
    )
