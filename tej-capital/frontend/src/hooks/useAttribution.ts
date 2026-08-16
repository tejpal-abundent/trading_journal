import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useTrades } from "./useTrades";

export type AttributionBy = "setup" | "asset" | "session" | "htf" | "dow";
export type AttributionVerdict = "not_enough" | "retire" | "marginal" | "working";

export type AttributionRow = {
  group: string;
  trade_count: number;
  win_rate: number | null;
  avg_win_r: number | null;
  avg_loss_r: number | null;
  expectancy_r: number | null;
  total_r: number | null;
  profit_factor: number | null;
  share_of_total_profit: number | null;
  verdict: AttributionVerdict;
};

/** GET /api/attribution?by=setup|asset|session|htf|dow */
export function useAttribution(by: AttributionBy) {
  return useQuery({
    queryKey: ["attribution", by],
    queryFn: () => api.get<AttributionRow[]>(`/attribution?by=${by}`),
  });
}

export type Concentration = { top_n_share: number | null; top_n_ids: string[] };

export function useConcentration() {
  return useQuery({
    queryKey: ["attribution-concentration"],
    queryFn: () => api.get<Concentration>("/attribution/concentration"),
  });
}

export type ComplianceGap = {
  compliant_expectancy: number | null;
  noncompliant_expectancy: number | null;
  p_value: number | null;
};

/**
 * GET /api/attribution/compliance-gap returns expectancy + significance
 * only — the Brief §4.6 copy also needs the raw trade count on each side
 * ("168 trades" / "19 trades"), which we derive client-side from the
 * already-fetched trade list's rule_compliant flag.
 */
export function useComplianceGap() {
  const gap = useQuery({
    queryKey: ["attribution-compliance-gap"],
    queryFn: () => api.get<ComplianceGap>("/attribution/compliance-gap"),
  });
  const trades = useTrades();

  const counts = useMemo(() => {
    const rows = trades.data ?? [];
    return {
      compliant: rows.filter((t) => t.rule_compliant === true).length,
      noncompliant: rows.filter((t) => t.rule_compliant === false).length,
    };
  }, [trades.data]);

  return { ...gap, counts };
}
