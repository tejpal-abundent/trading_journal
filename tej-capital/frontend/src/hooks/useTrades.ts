import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type Direction = "long" | "short";
export type Session = "asia" | "london" | "london_ny" | "new_york" | "late_ny";
export type ExecGrade = "A" | "B" | "C" | "D";
export type MindState = "calm" | "rushed" | "frustrated" | "overconfident" | "tilted";

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
};

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
