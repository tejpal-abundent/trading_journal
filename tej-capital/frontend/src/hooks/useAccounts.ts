import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type AccountType = "live" | "prop_funded" | "prop_evaluation" | "demo" | "verified_mirror";

export type Account = {
  id: string;
  name: string;
  broker: string;
  currency: string;
  account_type: AccountType;
  in_composite: boolean;
  exclusion_reason: string | null;
  created_at: string;
  archived_at: string | null;
};

export type AccountCreatePayload = {
  name: string;
  broker: string;
  currency: string;
  account_type: AccountType;
  in_composite?: boolean;
  exclusion_reason?: string | null;
};

export function useAccounts() {
  return useQuery({
    queryKey: ["accounts"],
    queryFn: () => api.get<Account[]>("/accounts"),
  });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AccountCreatePayload) => api.post<Account>("/accounts", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  });
}
