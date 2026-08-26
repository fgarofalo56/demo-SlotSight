"""The synthetic market-intelligence provider.

Reads the generated ``market_titles`` and ``competitor_offerings`` tables. All
of it is invented — see NOTICE.md. ``is_synthetic`` is hardcoded ``True`` and
is surfaced through the API into the UI so a recommendation built on this data
is never mistaken for one built on real market intelligence.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.market import CompetitorSighting, TitleBenchmark
from slotsight.models import CompetitorOffering, MarketTitle


class SyntheticMarketProvider:
    """Market intel backed by generated data."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def name(self) -> str:
        return "SlotSight Synthetic Market Feed"

    @property
    def is_synthetic(self) -> bool:
        return True

    async def title_benchmarks(self, segment: str | None = None) -> list[TitleBenchmark]:
        stmt = select(MarketTitle)
        if segment:
            stmt = stmt.where(MarketTitle.segment == segment)
        stmt = stmt.order_by(MarketTitle.market_index.desc())

        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            TitleBenchmark(
                title=r.title,
                manufacturer=r.manufacturer,
                segment=r.segment,
                provider=r.provider,
                market_index=r.market_index,
                trend_30d_pct=r.trend_30d_pct,
                install_base=r.install_base,
                as_of_date=r.as_of_date,
            )
            for r in rows
        ]

    async def competitor_offerings(self, title: str | None = None) -> list[CompetitorSighting]:
        stmt = select(CompetitorOffering)
        if title:
            stmt = stmt.where(CompetitorOffering.title == title)
        stmt = stmt.order_by(CompetitorOffering.unit_count.desc())

        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            CompetitorSighting(
                property_name=r.property_name,
                market=r.market,
                title=r.title,
                unit_count=r.unit_count,
                promo_note=r.promo_note,
                observed_date=r.observed_date,
            )
            for r in rows
        ]


__all__ = ["SyntheticMarketProvider"]
