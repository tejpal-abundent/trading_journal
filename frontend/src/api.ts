const BASE = import.meta.env.VITE_API_URL || '/api'

export interface Trade {
  id: number
  pair: string
  direction: string
  timeframe: string
  setup_score: number
  verdict: string
  criteria_checked: string[]
  notes: string
  status: string
  entry_price: number | null
  exit_price: number | null
  stop_loss: number | null
  take_profit: number | null
  pnl: number | null
  pnl_percent: number | null
  rr_achieved: number | null
  lessons: string | null
  created_at: string
  closed_at: string | null
}

export interface AnalyticsData {
  period_days: number
  total_trades: number
  closed_trades: number
  open_trades: number
  wins: number
  losses: number
  win_rate: number
  total_pnl: number
  avg_score: number
  avg_rr: number
  score_analysis: Record<string, { count: number; win_rate: number; avg_pnl: number }>
  pair_breakdown: Record<string, { wins: number; losses: number; pnl: number }>
  direction_stats: Record<string, { count: number; win_rate: number; pnl: number }>
  trades: Trade[]
}

async function request<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  createTrade: (data: Omit<Trade, 'id' | 'status' | 'entry_price' | 'exit_price' | 'stop_loss' | 'take_profit' | 'pnl' | 'pnl_percent' | 'rr_achieved' | 'lessons' | 'created_at' | 'closed_at'>) =>
    request<Trade>('/trades', { method: 'POST', body: JSON.stringify(data) }),

  listTrades: (status?: string) =>
    request<Trade[]>(`/trades${status ? `?status=${status}` : ''}`),

  getTrade: (id: number) =>
    request<Trade>(`/trades/${id}`),

  updateTrade: (id: number, data: Partial<Trade>) =>
    request<Trade>(`/trades/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  deleteTrade: (id: number) =>
    request<{ ok: boolean }>(`/trades/${id}`, { method: 'DELETE' }),

  getAnalytics: (days = 14) =>
    request<AnalyticsData>(`/analytics?days=${days}`),
}
