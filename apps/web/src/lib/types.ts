/**
 * API response types.
 *
 * These mirror the Pydantic schemas in
 * `apps/api/src/slotsight/schemas/__init__.py`. If you change one, change both.
 *
 * Money crosses the API boundary as **dollars**, already converted from the
 * integer cents used for storage and arithmetic. See the money rule in
 * `.github/copilot-instructions.md`.
 */

export interface DependencyStatus {
  name: string
  status: 'ok' | 'degraded' | 'unavailable' | 'not_configured'
  detail: string
}

export interface HealthResponse {
  status: string
  version: string
  property_name: string
  dependencies: DependencyStatus[]
}

export interface ZoneSummary {
  zone_code: string
  zone_name: string
  is_high_limit: boolean
  machine_count: number
  coin_in_dollars: number
  win_dollars: number
  wpupd: number
  hold_pct: number
  /** Against the same denomination + game type. The actionable one. */
  peer_index: number
  /** Against the whole floor. Misleading — shown only to explain the trap. */
  floor_index: number
}

export interface FloorSummaryResponse {
  property_name: string
  window_days: number
  start_date: string
  end_date: string
  machine_count: number
  active_machine_count: number
  coin_in_dollars: number
  win_dollars: number
  theo_win_dollars: number
  floor_wpupd: number
  floor_hold_pct: number
  wpupd_change_pct: number
  zones: ZoneSummary[]
}

export interface TrendPoint {
  business_date: string
  coin_in_dollars: number
  win_dollars: number
  theo_win_dollars: number
  active_machines: number
}

export interface TrendResponse {
  window_days: number
  points: TrendPoint[]
}

export interface MachineSummary {
  asset_number: string
  bank_id: string
  zone_code: string
  zone_name: string
  title: string
  manufacturer: string
  cabinet: string
  game_type: string
  denomination_cents: number
  denomination_label: string
  par_hold_pct: number
  days: number
  coin_in_dollars: number
  win_dollars: number
  wpupd: number
  hold_pct: number
  hold_deviation: number
  peer_cohort: string
  peer_cohort_size: number
  peer_index: number
  floor_index: number
}

export interface MachineListResponse {
  window_days: number
  total: number
  returned: number
  machines: MachineSummary[]
}

export interface DataQualityItem {
  asset_number: string
  title: string
  zone_code: string
  issue: string
  observed_hold_pct: number
  par_hold_pct: number
  deviation_ratio: number
  detail: string
}

export interface UnderperformerItem {
  machine: MachineSummary
  peer_index: number
  prior_peer_index: number
  index_change: number
  sustained: boolean
  severity: 'critical' | 'warning' | 'watch'
  evidence: string[]
}

export interface TopPerformerItem {
  machine: MachineSummary
  peer_index: number
  prior_peer_index: number
  index_change: number
}

export interface OutliersResponse {
  window_days: number
  underperformers: UnderperformerItem[]
  top_performers: TopPerformerItem[]
  data_quality_flags: DataQualityItem[]
}

export type RecommendationAction =
  | 'convert'
  | 'remove'
  | 'monitor'
  | 'investigate'
  | 'no_action'

export type Priority = 'critical' | 'high' | 'medium' | 'low'

export interface RecommendationItem {
  id: string
  action: RecommendationAction
  priority: Priority
  subject_type: string
  subject_id: string
  headline: string
  rationale: string
  evidence: string[]
  suggested_title: string | null
  suggested_title_market_index: number | null
  estimated_annual_impact_dollars: number | null
  confidence: string
  uses_synthetic_market_data: boolean
  data_sources: string[]
  monitoring_instruction: string | null
}

export interface RecommendationsResponse {
  window_days: number
  generated_for: string
  total: number
  recommendations: RecommendationItem[]
}

export interface MarketTitleItem {
  title: string
  manufacturer: string
  segment: string
  provider: string
  market_index: number
  trend_30d_pct: number
  install_base: number
  as_of_date: string
  outperformance_pct: number
  is_rising: boolean
  on_our_floor: boolean
}

export interface MarketResponse {
  provider_name: string
  is_synthetic: boolean
  disclaimer: string
  titles: MarketTitleItem[]
}

export interface ToolCallRecord {
  tool: string
  arguments: Record<string, unknown>
  result_summary: string
}

export interface ChatResponse {
  answer: string
  tool_calls: ToolCallRecord[]
  window_days: number
  model_deployment: string
  grounded: boolean
}

export interface PlantedSignalItem {
  key: string
  headline: string
  detail: string
  expected_outcome: string
}

export interface SignalsResponse {
  explanation: string
  signals: PlantedSignalItem[]
}
