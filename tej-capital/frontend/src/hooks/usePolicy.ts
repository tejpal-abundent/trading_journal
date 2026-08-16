import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type LimitType =
  | "risk_per_trade" | "concurrent_open_risk" | "daily_loss" | "weekly_loss" | "monthly_loss"
  | "drawdown_killswitch" | "asset_class_concentration" | "risk_sizing_consistency"
  | "avg_loser_vs_1r" | "rule_compliance_rate";

export type LimitUnit = "pct" | "r" | "abs";

export type PolicySection =
  | "mandate" | "method" | "time_horizon" | "position_sizing" | "correlation"
  | "stop_discipline" | "news_policy" | "leverage" | "valuation" | "custody"
  | "amendment_procedure" | "review_cadence";

export const LIMIT_TYPES: LimitType[] = [
  "risk_per_trade", "concurrent_open_risk", "daily_loss", "weekly_loss", "monthly_loss",
  "drawdown_killswitch", "asset_class_concentration", "risk_sizing_consistency",
  "avg_loser_vs_1r", "rule_compliance_rate",
];

export const POLICY_SECTIONS: PolicySection[] = [
  "mandate", "method", "time_horizon", "position_sizing", "correlation",
  "stop_discipline", "news_policy", "leverage", "valuation", "custody",
  "amendment_procedure", "review_cadence",
];

export type PolicyLimit = {
  id: string; limit_type: LimitType; threshold: string; unit: LimitUnit;
  effective_from: string; effective_to: string | null; committed_action: string; created_at: string;
};

export function usePolicyLimits() {
  return useQuery({ queryKey: ["policy-limits"], queryFn: () => api.get<PolicyLimit[]>("/policy/limits") });
}

export type LimitBreach = {
  id: string; limit_id: string; breached_on: string; observed_value: string;
  threshold_value: string; note: string | null; resolved_on: string | null;
};

export function usePolicyBreaches() {
  return useQuery({ queryKey: ["policy-breaches"], queryFn: () => api.get<LimitBreach[]>("/policy/breaches") });
}

export type PolicyDocument = { id: string; section: PolicySection; body: string; updated_at: string };

export function usePolicyDocument() {
  return useQuery({ queryKey: ["policy-document"], queryFn: () => api.get<PolicyDocument[]>("/policy/document") });
}

export type AmendmentBlockedConflict = {
  error: "amendment_blocked_during_drawdown";
  hint: string;
  current_drawdown_pct: number;
};

export function isAmendmentBlocked(body: unknown): body is { detail: AmendmentBlockedConflict } {
  const detail = (body as { detail?: unknown } | undefined)?.detail;
  return !!detail && typeof detail === "object" && (detail as { error?: string }).error === "amendment_blocked_during_drawdown";
}

export type SetLimitPayload = {
  threshold: string;
  unit: LimitUnit;
  effective_from: string;
  committed_action: string;
  reason: string;
  override_during_drawdown?: boolean;
};

/** POST /api/policy/limits/{type} — a 409 amendment_blocked_during_drawdown
 * carries { hint, current_drawdown_pct } in error.body.detail; callers
 * should reopen with override_during_drawdown=true + a >=30 char reason
 * (see DrawdownAmendmentModal). */
export function useSetLimit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ limitType, body }: { limitType: LimitType; body: SetLimitPayload }) =>
      api.post(`/policy/limits/${limitType}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["policy-limits"], exact: false }),
  });
}

export function usePatchDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ section, body }: { section: PolicySection; body: string }) =>
      api.patch<PolicyDocument>(`/policy/document/${section}`, { body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["policy-document"] }),
  });
}
