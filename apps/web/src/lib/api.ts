/**
 * Typed API client.
 *
 * All fetching lives here, never in components. A component that knows a URL
 * is a component you cannot test.
 */

import type {
  ChatResponse,
  FloorSummaryResponse,
  HealthResponse,
  MachineListResponse,
  MarketResponse,
  OutliersResponse,
  RecommendationsResponse,
  SignalsResponse,
  TrendResponse,
} from './types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

/** An API failure carrying enough context to show the user something useful. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }

  /** True when the chat endpoint is unavailable purely for lack of config. */
  get isNotConfigured(): boolean {
    return this.status === 503
  }
}

async function get<T>(path: string, params?: Record<string, string | number | boolean>) {
  const url = new URL(`${BASE}/api${path}`, window.location.origin)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v))
    }
  }

  const response = await fetch(url.toString(), {
    headers: { accept: 'application/json' },
  })

  if (!response.ok) {
    let detail: unknown
    try {
      detail = (await response.json())?.detail
    } catch {
      detail = await response.text().catch(() => undefined)
    }
    throw new ApiError(
      `GET ${path} failed (${response.status})`,
      response.status,
      detail,
    )
  }

  return (await response.json()) as T
}

export const api = {
  health: () => get<HealthResponse>('/health'),

  floorSummary: (days = 30) => get<FloorSummaryResponse>('/floor/summary', { days }),

  trend: (days = 90) => get<TrendResponse>('/floor/trend', { days }),

  signals: () => get<SignalsResponse>('/floor/signals'),

  machines: (params: {
    days?: number
    zone?: string
    denomination_cents?: number
    game_type?: string
    bank_id?: string
    sort?: string
    descending?: boolean
    limit?: number
  }) => get<MachineListResponse>('/machines', params as Record<string, string | number | boolean>),

  recommendations: (params: { days?: number; action?: string; limit?: number }) =>
    get<RecommendationsResponse>(
      '/recommendations',
      params as Record<string, string | number | boolean>,
    ),

  outliers: (days = 30, limit = 25) => get<OutliersResponse>('/outliers', { days, limit }),

  marketTitles: (params: { exclude_owned?: boolean; rising_only?: boolean } = {}) =>
    get<MarketResponse>('/market/titles', params as Record<string, string | number | boolean>),

  async chat(message: string, windowDays = 30): Promise<ChatResponse> {
    const response = await fetch(`${BASE}/api/chat`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ message, window_days: windowDays }),
    })

    if (!response.ok) {
      let detail: unknown
      try {
        detail = (await response.json())?.detail
      } catch {
        detail = undefined
      }
      throw new ApiError(`Chat failed (${response.status})`, response.status, detail)
    }

    return (await response.json()) as ChatResponse
  },
}
