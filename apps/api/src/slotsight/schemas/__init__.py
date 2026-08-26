"""Pydantic response models.

Deliberately separate from the SQLAlchemy models. The ORM describes storage;
these describe the contract. Keeping them apart means a column rename does not
silently become a breaking API change, and it gives the generated OpenAPI
schema (which the frontend's typed client is built from) a stable shape.

Money crosses this boundary as **dollars**, not cents. Cents are a storage and
arithmetic concern; every consumer wants dollars, and converting once here
beats converting in five places in the UI.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base with shared config."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ═══════════════════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════════════════
class DependencyStatus(ApiModel):
    name: str
    status: str = Field(
        description="ok | configured | degraded | unavailable | not_configured. "
        "'configured' means settings are present but NOT verified — it is "
        "deliberately distinct from 'ok'."
    )
    detail: str = ""


class HealthResponse(ApiModel):
    status: str
    version: str
    property_name: str
    dependencies: list[DependencyStatus]


# ═══════════════════════════════════════════════════════════════════════════
# Floor
# ═══════════════════════════════════════════════════════════════════════════
class ZoneSummary(ApiModel):
    zone_code: str
    zone_name: str
    is_high_limit: bool
    machine_count: int
    coin_in_dollars: float
    win_dollars: float
    wpupd: float
    hold_pct: float
    peer_index: float = Field(description="Mean peer index. 1.00 == cohort average.")
    floor_index: float = Field(
        description="Mean floor-wide index. Misleading across denominations - "
        "compare peer_index instead."
    )


class FloorSummaryResponse(ApiModel):
    property_name: str
    window_days: int
    start_date: date
    end_date: date
    machine_count: int
    active_machine_count: int
    coin_in_dollars: float
    win_dollars: float
    theo_win_dollars: float
    floor_wpupd: float
    floor_hold_pct: float
    wpupd_change_pct: float
    zones: list[ZoneSummary]


class TrendPoint(ApiModel):
    business_date: date
    coin_in_dollars: float
    win_dollars: float
    theo_win_dollars: float
    active_machines: int


class TrendResponse(ApiModel):
    window_days: int
    points: list[TrendPoint]


# ═══════════════════════════════════════════════════════════════════════════
# Machines
# ═══════════════════════════════════════════════════════════════════════════
class MachineSummary(ApiModel):
    asset_number: str
    bank_id: str
    zone_code: str
    zone_name: str
    title: str
    manufacturer: str
    cabinet: str
    game_type: str
    denomination_cents: int
    denomination_label: str
    par_hold_pct: float
    days: int
    coin_in_dollars: float
    win_dollars: float
    wpupd: float
    hold_pct: float
    hold_deviation: float
    peer_cohort: str
    peer_cohort_size: int
    peer_index: float
    floor_index: float


class MachineListResponse(ApiModel):
    window_days: int
    total: int
    returned: int
    machines: list[MachineSummary]


class MachineDetailResponse(ApiModel):
    machine: MachineSummary
    trend: list[TrendPoint]
    peer_average_wpupd: float
    data_quality_flag: DataQualityItem | None = None


# ═══════════════════════════════════════════════════════════════════════════
# Outliers
# ═══════════════════════════════════════════════════════════════════════════
class DataQualityItem(ApiModel):
    asset_number: str
    title: str
    zone_code: str
    issue: str
    observed_hold_pct: float
    par_hold_pct: float
    deviation_ratio: float
    detail: str


class UnderperformerItem(ApiModel):
    machine: MachineSummary
    peer_index: float
    prior_peer_index: float
    index_change: float
    sustained: bool
    severity: str
    evidence: list[str]


class TopPerformerItem(ApiModel):
    machine: MachineSummary
    peer_index: float
    prior_peer_index: float
    index_change: float


class OutliersResponse(ApiModel):
    window_days: int
    underperformers: list[UnderperformerItem]
    top_performers: list[TopPerformerItem]
    data_quality_flags: list[DataQualityItem]


# ═══════════════════════════════════════════════════════════════════════════
# Recommendations
# ═══════════════════════════════════════════════════════════════════════════
class RecommendationItem(ApiModel):
    id: str
    action: str = Field(description="convert | remove | monitor | investigate | no_action")
    priority: str = Field(description="critical | high | medium | low")
    subject_type: str
    subject_id: str
    headline: str
    rationale: str
    evidence: list[str]
    suggested_title: str | None = None
    suggested_title_market_index: float | None = None
    estimated_annual_impact_dollars: float | None = None
    confidence: str
    uses_synthetic_market_data: bool
    data_sources: list[str]
    monitoring_instruction: str | None = None


class RecommendationsResponse(ApiModel):
    window_days: int
    generated_for: str
    total: int
    recommendations: list[RecommendationItem]


# ═══════════════════════════════════════════════════════════════════════════
# Market
# ═══════════════════════════════════════════════════════════════════════════
class MarketTitleItem(ApiModel):
    title: str
    manufacturer: str
    segment: str
    provider: str
    market_index: float
    trend_30d_pct: float
    install_base: int
    as_of_date: date
    outperformance_pct: float
    is_rising: bool
    on_our_floor: bool


class MarketResponse(ApiModel):
    provider_name: str
    is_synthetic: bool = Field(
        description="True when benchmarks are generated rather than sourced. "
        "Always True in this demo - see NOTICE.md."
    )
    disclaimer: str
    titles: list[MarketTitleItem]


class CompetitorItem(ApiModel):
    property_name: str
    market: str
    title: str
    unit_count: int
    promo_note: str
    observed_date: date


class CompetitorsResponse(ApiModel):
    provider_name: str
    is_synthetic: bool
    disclaimer: str
    sightings: list[CompetitorItem]


# ═══════════════════════════════════════════════════════════════════════════
# Planted signals (teaching endpoint)
# ═══════════════════════════════════════════════════════════════════════════
class PlantedSignalItem(ApiModel):
    key: str
    headline: str
    detail: str
    expected_outcome: str


class SignalsResponse(ApiModel):
    explanation: str
    signals: list[PlantedSignalItem]


# ═══════════════════════════════════════════════════════════════════════════
# Chat
# ═══════════════════════════════════════════════════════════════════════════
class ChatRequest(ApiModel):
    message: str = Field(min_length=1, max_length=2_000)
    window_days: int = Field(default=30, ge=1, le=365)


class ToolCallRecord(ApiModel):
    """One analytics function the model invoked, with its arguments.

    Returned to the client so every answer is auditable: you can see exactly
    which deterministic function produced the numbers being quoted.
    """

    tool: str
    arguments: dict[str, Any]
    result_summary: str


class ChatResponse(ApiModel):
    answer: str
    tool_calls: list[ToolCallRecord]
    window_days: int
    model_deployment: str
    grounded: bool = Field(
        description="True when the answer was produced from at least one analytics "
        "tool call rather than from the model's own knowledge."
    )


# Resolve the forward reference in MachineDetailResponse.
MachineDetailResponse.model_rebuild()
