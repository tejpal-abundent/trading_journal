import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type Direction = "long" | "short";
export type Session = "asia" | "london" | "london_ny" | "new_york" | "late_ny";
export type ExecGrade = "A" | "B" | "C" | "D";
export type MindState = "calm" | "rushed" | "frustrated" | "overconfident" | "tilted";
export type Timeframe = "1m" | "5m" | "15m" | "30m" | "1h" | "4h" | "1d" | "1w";

export const TIMEFRAME_OPTIONS: Timeframe[] = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"];

export const SESSION_OPTIONS: { value: Session; label: string }[] = [
  { value: "asia", label: "Asia" },
  { value: "london", label: "London" },
  { value: "london_ny", label: "London-NY" },
  { value: "new_york", label: "NY" },
  { value: "late_ny", label: "Late-NY" },
];

export const EXEC_GRADE_OPTIONS: ExecGrade[] = ["A", "B", "C", "D"];

export const MIND_STATE_OPTIONS: { value: MindState; label: string }[] = [
  { value: "calm", label: "Calm" },
  { value: "rushed", label: "Rushed" },
  { value: "frustrated", label: "Frustrated" },
  { value: "overconfident", label: "Overconfident" },
  { value: "tilted", label: "Tilted" },
];

export type Trade = {
  id: string;
  account_id: string;
  setup_id: string | null;
  instrument: string;
  direction: Direction;
  /** Decimal fields are serialized as strings by the API to preserve precision. */
  entry_price: string;
  exit_price: string | null;
  initial_stop: string | null;
  target_price: string | null;
  position_size: string;
  risk_amount: string | null;
  gross_pnl: string | null;
  costs: string;
  session: Session | null;
  htf_aligned: boolean | null;
  timeframe: Timeframe | null;
  thesis: string | null;
  review: string | null;
  execution_grade: ExecGrade | null;
  state_of_mind: MindState | null;
  rule_compliant: boolean | null;
  breach_note: string | null;
  mae_r: string | null;
  mfe_r: string | null;
  opened_at: string;
  closed_at: string | null;
  one_sentence_takeaway: string | null;
  external_id: string | null;
  superseded_by: string | null;
  superseded_reason: string | null;
  entered_at: string;
  r_multiple: number | null;
  enrichment_needed: boolean;
};

export type TradeCreatePayload = {
  account_id: string;
  setup_id?: string | null;
  instrument: string;
  direction: Direction;
  entry_price: string;
  exit_price?: string | null;
  initial_stop?: string | null;
  target_price?: string | null;
  position_size: string;
  risk_amount?: string | null;
  gross_pnl?: string | null;
  costs?: string;
  session?: Session | null;
  htf_aligned?: boolean | null;
  timeframe?: Timeframe | null;
  thesis?: string | null;
  review?: string | null;
  execution_grade?: ExecGrade | null;
  state_of_mind?: MindState | null;
  rule_compliant?: boolean | null;
  breach_note?: string | null;
  mae_r?: string | null;
  mfe_r?: string | null;
  opened_at: string;
  closed_at?: string | null;
  one_sentence_takeaway?: string | null;
};

export type TradeEnrichPayload = {
  setup_id?: string | null;
  risk_amount?: string | null;
  execution_grade?: ExecGrade | null;
  state_of_mind?: MindState | null;
  mae_r?: string | null;
  mfe_r?: string | null;
  rule_compliant?: boolean | null;
  breach_note?: string | null;
  one_sentence_takeaway?: string | null;
  review?: string | null;
  timeframe?: Timeframe | null;
};

export type RiskExceedsTimeframeLimit = {
  error: "risk_exceeds_timeframe_limit";
  timeframe: string;
  risk_pct: number;
  threshold: number;
  hint: string;
};

export function isRiskExceedsTimeframeLimit(body: unknown): body is { detail: RiskExceedsTimeframeLimit } {
  const detail = (body as { detail?: unknown } | undefined)?.detail;
  return !!detail && typeof detail === "object" && (detail as { error?: string }).error === "risk_exceeds_timeframe_limit";
}

/**
 * Pulls the server's per-timeframe-risk hint out of an api.ts error, if
 * that's what failed. Lets callers (Trade Entry's before-section, the
 * enrichment form) surface it as a field-level error under the risk input
 * instead of the generic submit-error banner used for everything else.
 */
export function riskLimitHintFrom(err: unknown): string | null {
  const body = (err as { body?: unknown } | undefined)?.body;
  return isRiskExceedsTimeframeLimit(body) ? body.detail.hint : null;
}

export function useTrades(accountId?: string, since?: string) {
  const params = new URLSearchParams();
  if (since) params.set("since", since);
  if (accountId) params.set("account_id", accountId);
  const qs = params.toString();
  return useQuery({
    queryKey: ["trades", accountId ?? null, since ?? null],
    queryFn: () => api.get<Trade[]>(`/trades${qs ? `?${qs}` : ""}`),
  });
}

/** GET /api/trades/enrichment — trades with risk_amount IS NULL, most recent first. */
export function useEnrichmentQueue() {
  return useQuery({
    queryKey: ["trades", "enrichment"],
    queryFn: () => api.get<Trade[]>("/trades/enrichment"),
  });
}

/** GET /api/trades/open — trades where closed_at IS NULL AND not superseded.
 * Feeds the Open Positions panel at the top of Trade Entry so multi-day and
 * multi-week holds are discoverable a day or a week or a month later. */
export function useOpenTrades() {
  return useQuery({
    queryKey: ["trades", "open"],
    queryFn: () => api.get<Trade[]>("/trades/open"),
  });
}

export type TradeClosePayload = {
  exit_price: string;
  closed_at: string;
  gross_pnl: string;
  costs?: string;
  mae_r?: string | null;
  mfe_r?: string | null;
  rule_compliant?: boolean | null;
  breach_note?: string | null;
  execution_grade?: ExecGrade | null;
  state_of_mind?: MindState | null;
  review?: string | null;
  one_sentence_takeaway?: string | null;
};

/** POST /api/trades/{id}/close — finalise an open trade. NOT a correction:
 * the trade wasn't wrong, it just wasn't over. No reason required. Refuses
 * if the trade is already closed (409) or if closed_at < opened_at (400). */
export function useCloseTrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: TradeClosePayload }) =>
      api.post<Trade>(`/trades/${id}/close`, body),
    onSuccess: () => invalidateTrades(qc),
  });
}

function invalidateTrades(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["trades"], exact: false });
}

export function useCreateTrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TradeCreatePayload) => api.post<Trade>("/trades", body),
    onSuccess: () => invalidateTrades(qc),
  });
}

/** PATCH /api/trades/{id} — enrichment-only fields, no correction/reason required
 * (Brief §4.2: these were never asserted before, so nothing to correct). */
export function useEnrichTrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: TradeEnrichPayload }) =>
      api.patch<Trade>(`/trades/${id}`, body),
    onSuccess: () => invalidateTrades(qc),
  });
}

export type PlaybookSetup = {
  id: string;
  tag: string;
  name: string;
  description: string;
  is_active: boolean;
  retired_at: string | null;
};

/** GET /api/playbook — active setups feed the Trade Entry "Setup" dropdown. */
export function usePlaybookSetups() {
  return useQuery({
    queryKey: ["playbook"],
    queryFn: () => api.get<PlaybookSetup[]>("/playbook"),
  });
}
