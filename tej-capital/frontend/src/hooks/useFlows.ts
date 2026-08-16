import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type FlowType =
  | "deposit"
  | "withdrawal"
  | "prop_payout"
  | "platform_fee"
  | "transfer_in"
  | "transfer_out";

export type CashFlow = {
  id: string;
  account_id: string;
  as_of_date: string;
  /** Decimal — serialized as a string by the API to preserve precision. */
  amount: string;
  flow_type: FlowType;
  flow_timing: "start_of_day" | "end_of_day";
  note: string | null;
  superseded_by: string | null;
  superseded_reason: string | null;
};

export function useFlows(accountId: string | undefined, since?: string) {
  return useQuery({
    queryKey: ["flows", accountId, since ?? null],
    queryFn: () => api.get<CashFlow[]>(`/accounts/${accountId}/flows${since ? `?since=${since}` : ""}`),
    enabled: !!accountId,
  });
}

/** POST /api/accounts/{id}/flows — "money in or out today" (deposit, withdrawal, prop payout, ...). */
export function useCreateFlow(accountId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { as_of_date: string; amount: string; flow_type: FlowType; note?: string | null }) =>
      api.post<CashFlow>(`/accounts/${accountId}/flows`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["flows", accountId], exact: false }),
  });
}
