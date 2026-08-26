"""Shared router dependencies and domain -> schema converters.

Converters live in one place so the REST API, the MCP server, and the chat
agent all render a machine the same way. Three renderings of the same object
is how a UI and an assistant start quoting different numbers for the same
question.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from slotsight.analytics.floor import DailyPoint, MachineMetrics, ZoneMetrics
from slotsight.analytics.outliers import DataQualityFlag, TopPerformer, Underperformer
from slotsight.analytics.recommend import Recommendation
from slotsight.config import Settings, get_settings
from slotsight.db import get_session
from slotsight.market import CompetitorSighting, MarketIntelProvider, TitleBenchmark
from slotsight.market.synthetic import SyntheticMarketProvider
from slotsight.schemas import (
    CompetitorItem,
    DataQualityItem,
    MachineSummary,
    MarketTitleItem,
    RecommendationItem,
    TopPerformerItem,
    TrendPoint,
    UnderperformerItem,
    ZoneSummary,
)

SYNTHETIC_DISCLAIMER = (
    "All market intelligence in this demo is SYNTHETIC. It is generated from a fixed "
    "seed and is not sourced from, affiliated with, or endorsed by any real market-data "
    "provider. See NOTICE.md."
)

DENOM_LABELS: dict[int, str] = {
    1: "Penny",
    5: "Nickel",
    25: "Quarter",
    100: "$1",
    500: "$5",
    2500: "$25",
}

GAME_TYPE_LABELS: dict[str, str] = {
    "video_reel": "Video Reel",
    "mechanical_reel": "Mechanical Reel",
    "video_poker": "Video Poker",
    "keno_multigame": "Multigame",
}


def denom_label(cents: int) -> str:
    return DENOM_LABELS.get(cents, f"{cents}¢")


# ═══════════════════════════════════════════════════════════════════════════
# Dependencies
# ═══════════════════════════════════════════════════════════════════════════
async def get_market_provider(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[MarketIntelProvider, None]:
    """The market-intel provider.

    Swap the concrete class here to plug in a real feed - nothing above this
    line knows which implementation it is talking to. See slotsight.market.
    """
    yield SyntheticMarketProvider(session)


def window_days(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Trailing window in gaming days, ending at the most recent day in the data.",
    ),
) -> int:
    return days


SettingsDep = Depends(get_settings)
SessionDep = Depends(get_session)
MarketDep = Depends(get_market_provider)
WindowDep = Depends(window_days)

__all__ = [
    "DENOM_LABELS",
    "GAME_TYPE_LABELS",
    "SYNTHETIC_DISCLAIMER",
    "MarketDep",
    "SessionDep",
    "Settings",
    "SettingsDep",
    "WindowDep",
    "denom_label",
    "get_market_provider",
    "to_competitor_item",
    "to_data_quality_item",
    "to_machine_summary",
    "to_market_title_item",
    "to_recommendation_item",
    "to_top_performer_item",
    "to_trend_point",
    "to_underperformer_item",
    "to_zone_summary",
    "window_days",
]


# ═══════════════════════════════════════════════════════════════════════════
# Converters
# ═══════════════════════════════════════════════════════════════════════════
def to_machine_summary(m: MachineMetrics) -> MachineSummary:
    return MachineSummary(
        asset_number=m.asset_number,
        bank_id=m.bank_id,
        zone_code=m.zone_code,
        zone_name=m.zone_name,
        title=m.title,
        manufacturer=m.manufacturer,
        cabinet=m.cabinet,
        game_type=m.game_type,
        denomination_cents=m.denomination_cents,
        denomination_label=denom_label(m.denomination_cents),
        par_hold_pct=m.par_hold_pct,
        days=m.days,
        coin_in_dollars=m.coin_in_dollars,
        win_dollars=m.win_dollars,
        wpupd=m.wpupd,
        hold_pct=m.hold_pct,
        hold_deviation=m.hold_deviation,
        peer_cohort=m.peer_cohort,
        peer_cohort_size=m.peer_cohort_size,
        peer_index=m.peer_index,
        floor_index=m.floor_index,
    )


def to_zone_summary(z: ZoneMetrics) -> ZoneSummary:
    return ZoneSummary(
        zone_code=z.zone_code,
        zone_name=z.zone_name,
        is_high_limit=z.is_high_limit,
        machine_count=z.machine_count,
        coin_in_dollars=round(z.coin_in_cents / 100, 2),
        win_dollars=round(z.actual_win_cents / 100, 2),
        wpupd=z.wpupd,
        hold_pct=z.hold_pct,
        peer_index=z.peer_index,
        floor_index=z.floor_index,
    )


def to_trend_point(p: DailyPoint) -> TrendPoint:
    return TrendPoint(
        business_date=p.business_date,
        coin_in_dollars=p.coin_in_dollars,
        win_dollars=p.win_dollars,
        theo_win_dollars=round(p.theo_win_cents / 100, 2),
        active_machines=p.active_machines,
    )


def to_data_quality_item(f: DataQualityFlag) -> DataQualityItem:
    return DataQualityItem(
        asset_number=f.asset_number,
        title=f.title,
        zone_code=f.zone_code,
        issue=f.issue,
        observed_hold_pct=f.observed_hold_pct,
        par_hold_pct=f.par_hold_pct,
        deviation_ratio=f.deviation_ratio,
        detail=f.detail,
    )


def to_underperformer_item(u: Underperformer) -> UnderperformerItem:
    return UnderperformerItem(
        machine=to_machine_summary(u.machine),
        peer_index=u.peer_index,
        prior_peer_index=u.prior_peer_index,
        index_change=u.index_change,
        sustained=u.sustained,
        severity=u.severity,
        evidence=u.evidence,
    )


def to_top_performer_item(t: TopPerformer) -> TopPerformerItem:
    return TopPerformerItem(
        machine=to_machine_summary(t.machine),
        peer_index=t.peer_index,
        prior_peer_index=t.prior_peer_index,
        index_change=t.index_change,
    )


def to_recommendation_item(r: Recommendation) -> RecommendationItem:
    return RecommendationItem(
        id=r.id,
        action=r.action,
        priority=r.priority,
        subject_type=r.subject_type,
        subject_id=r.subject_id,
        headline=r.headline,
        rationale=r.rationale,
        evidence=r.evidence,
        suggested_title=r.suggested_title,
        suggested_title_market_index=r.suggested_title_market_index,
        estimated_annual_impact_dollars=r.estimated_annual_impact_dollars,
        confidence=r.confidence,
        uses_synthetic_market_data=r.uses_synthetic_market_data,
        data_sources=r.data_sources,
        monitoring_instruction=r.monitoring_instruction,
    )


def to_market_title_item(b: TitleBenchmark, *, on_our_floor: bool) -> MarketTitleItem:
    return MarketTitleItem(
        title=b.title,
        manufacturer=b.manufacturer,
        segment=b.segment,
        provider=b.provider,
        market_index=b.market_index,
        trend_30d_pct=b.trend_30d_pct,
        install_base=b.install_base,
        as_of_date=b.as_of_date,
        outperformance_pct=round(b.outperformance_pct, 1),
        is_rising=b.is_rising,
        on_our_floor=on_our_floor,
    )


def to_competitor_item(c: CompetitorSighting) -> CompetitorItem:
    return CompetitorItem(
        property_name=c.property_name,
        market=c.market,
        title=c.title,
        unit_count=c.unit_count,
        promo_note=c.promo_note,
        observed_date=c.observed_date,
    )
