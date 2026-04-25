const BASE = import.meta.env.VITE_API_URL || 'https://trading-journal-1-8ork.onrender.com/api'

export type TradeStatus = 'planned' | 'entered' | 'win' | 'loss' | 'breakeven' | 'skipped'
export type EntryTiming = 'on_time' | 'late' | 'early'
export type CloseStatus = 'win' | 'loss' | 'breakeven'

export interface PartialExit {
  price: number
  size_pct: number
  reason: 'took_profit' | 'cut_loss' | 'scaled_out' | 'sl_adjusted'
}

export interface Trade {
  id: number
  pair: string
  direction: 'LONG' | 'SHORT'
  timeframe: string
  strategy: string
  setup_score: number
  verdict: string
  criteria_checked: string[]
  notes: string
  planned_entry: number | null
  planned_stop: number | null
  planned_target: number | null
  planned_rr: number | null
  status: TradeStatus
  retroactive: boolean
  entry_price: number | null
  exit_price: number | null
  stop_loss: number | null
  take_profit: number | null
  position_size: number | null
  account_size: number | null
  risk_dollars: number | null
  risk_percent: number | null
  entry_timing: EntryTiming | null
  emotions_entry: string[]
  feelings_entry: string
  skip_reason: string
  partial_exits: PartialExit[]
  pnl: number | null
  pnl_percent: number | null
  rr_achieved: number | null
  rules_followed: boolean | null
  mistake_tags: string[]
  emotions_exit: string[]
  feelings_exit: string
  lessons: string
  chart_url: string
  created_at: string
  closed_at: string | null
}

export interface Strategy {
  id: number
  name: string
  criteria: { id: string; label: string; points: number; category: string; description: string }[]
  is_core_required: string[]
  created_at: string
}

export interface AccountSnapshot {
  id: number
  balance: number
  recorded_at: string
  note: string
}

export interface Review {
  id: number
  period_type: 'week' | 'month' | 'custom'
  period_start: string
  period_end: string
  notes: string
  stats_snapshot?: AnalyticsData
  created_at: string
}

export interface AnalyticsData {
  period_days: number | null
  period_start: string | null
  period_end: string | null
  total_trades: number
  closed_trades: number
  open_trades: number
  planned_trades: number
  skipped_trades: number
  wins: number
  losses: number
  breakeven: number
  win_rate: number
  total_pnl: number
  avg_score: number
  avg_rr: number
  score_analysis: Record<string, { count: number; win_rate: number; avg_pnl: number }>
  pair_breakdown: Record<string, { wins: number; losses: number; pnl: number }>
  direction_stats: Record<string, { count: number; win_rate: number; pnl: number }>
  plan_adherence: {
    rules_followed_pct: number
    rules_followed_win_rate: number
    rules_broken_win_rate: number
    skip_rate: number
    retroactive_rate: number
  }
  risk_discipline: {
    avg_risk_pct: number
    max_risk_pct: number
    over_threshold_count: number
    histogram: { bucket: string; count: number }[]
  }
  mistake_impact: { tag: string; count: number; win_rate: number; avg_pnl: number; total_pnl: number }[]
  emotion_impact: {
    entry: { tag: string; count: number; win_rate: number; avg_pnl: number; total_pnl: number }[]
    exit:  { tag: string; count: number; win_rate: number; avg_pnl: number; total_pnl: number }[]
  }
  timing_impact: Record<string, { count: number; win_rate: number }>
  strategy_breakdown: { strategy: string; count: number; win_rate: number; expectancy: number }[]
  edge_composite: {
    headline: string
    count: number
    win_rate?: number
    avg_rr?: number
    total_pnl?: number
    filter?: Record<string, unknown>
  }
  trades: Trade[]
}

async function request<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    let msg = `API error: ${res.status}`
    try { const j = await res.json(); if (j.detail) msg = j.detail } catch {}
    throw new Error(msg)
  }
  return res.json()
}

export const api = {
  createPlan: (data: {
    pair: string; direction: string; timeframe: string; strategy: string;
    setup_score: number; verdict: string; criteria_checked: string[]; notes?: string;
    planned_entry?: number | null; planned_stop?: number | null;
    planned_target?: number | null; planned_rr?: number | null;
  }) => request<Trade>('/trades', { method: 'POST', body: JSON.stringify(data) }),

  enterTrade: (id: number, data: {
    entry_price: number; stop_loss: number; take_profit?: number | null;
    position_size: number; account_size: number;
    entry_timing?: EntryTiming | null;
    emotions_entry?: string[]; feelings_entry?: string;
  }) => request<Trade>(`/trades/${id}/enter`, { method: 'POST', body: JSON.stringify(data) }),

  skipTrade: (id: number, data: { skip_reason: string; emotions_entry?: string[] }) =>
    request<Trade>(`/trades/${id}/skip`, { method: 'POST', body: JSON.stringify(data) }),

  closeTrade: (id: number, data: {
    status: CloseStatus; exit_price: number;
    pnl?: number | null; pnl_percent?: number | null; rr_achieved?: number | null;
    rules_followed?: boolean | null;
    mistake_tags?: string[]; emotions_exit?: string[];
    feelings_exit?: string; lessons?: string; chart_url?: string;
    partial_exits?: PartialExit[];
  }) => request<Trade>(`/trades/${id}/close`, { method: 'POST', body: JSON.stringify(data) }),

  createRetroactiveTrade: (data: Record<string, unknown>) =>
    request<Trade>('/trades/retroactive', { method: 'POST', body: JSON.stringify(data) }),

  listTrades: (status?: string) =>
    request<Trade[]>(`/trades${status ? `?status=${status}` : ''}`),

  getTrade: (id: number) => request<Trade>(`/trades/${id}`),

  updateTrade: (id: number, data: Partial<Trade>) =>
    request<Trade>(`/trades/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  deleteTrade: (id: number) =>
    request<{ ok: boolean }>(`/trades/${id}`, { method: 'DELETE' }),

  listStrategies: () => request<Strategy[]>('/strategies'),
  createStrategy: (data: Omit<Strategy, 'id' | 'created_at'>) =>
    request<Strategy>('/strategies', { method: 'POST', body: JSON.stringify(data) }),
  updateStrategy: (id: number, data: Partial<Strategy>) =>
    request<Strategy>(`/strategies/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteStrategy: (id: number) =>
    request<{ ok: boolean }>(`/strategies/${id}`, { method: 'DELETE' }),

  listSnapshots: () => request<AccountSnapshot[]>('/account-snapshots'),
  createSnapshot: (data: { balance: number; note?: string }) =>
    request<AccountSnapshot>('/account-snapshots', { method: 'POST', body: JSON.stringify(data) }),
  latestSnapshot: () =>
    request<{ balance: number | null }>('/account-snapshots/latest'),

  listReviews: () => request<Review[]>('/reviews'),
  getReview: (id: number) => request<Review>(`/reviews/${id}`),
  createReview: (data: { period_type: string; period_start: string; period_end: string; notes: string }) =>
    request<Review>('/reviews', { method: 'POST', body: JSON.stringify(data) }),
  deleteReview: (id: number) =>
    request<{ ok: boolean }>(`/reviews/${id}`, { method: 'DELETE' }),

  getAnalytics: (params: { days?: number; from?: string; to?: string } = {}) => {
    const q = new URLSearchParams()
    if (params.days) q.set('days', String(params.days))
    if (params.from) q.set('start_from', params.from)
    if (params.to) q.set('end_to', params.to)
    return request<AnalyticsData>(`/analytics${q.toString() ? `?${q.toString()}` : ''}`)
  },
}
