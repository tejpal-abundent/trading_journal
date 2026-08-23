import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type Settings = {
  id: number;
  starting_capital: string;
  record_start_date: string;
  base_currency: string;
  risk_free_rate: string;
  trading_days_per_year: number;
  minimum_acceptable_return: string;
  benchmark_sharpe: string;
  confidence_level: string;
  strategy_variants_tested: number;
  daily_target_pct: string;
  weekly_target_pct: string;
  monthly_target_pct: string;
  risk_by_timeframe: Record<string, string>;
};

export function useSettings() {
  return useQuery({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Omit<Settings, "id">>) => api.patch<Settings>("/settings", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });
}

export type Target = { id: string; metric_name: string; target_value: string; unit: string };

/** GET/POST /api/settings/targets — POST upserts by metric_name, so create
 * and edit are the same call. */
export function useTargets() {
  return useQuery({ queryKey: ["targets"], queryFn: () => api.get<Target[]>("/settings/targets") });
}

export function useUpsertTarget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { metric_name: string; target_value: string; unit: string }) =>
      api.post<Target>("/settings/targets", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["targets"] }),
  });
}
