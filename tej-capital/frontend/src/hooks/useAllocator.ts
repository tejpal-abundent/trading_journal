import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type Metric } from "../lib/api";
import type { DrawdownEntry, Verdict } from "./useMetrics";

export type AllocatorToken = {
  id: string; token: string; label: string; expires_at: string; revoked_at: string | null; created_at: string;
};

/** POST /api/allocator/tokens — creates a fresh share token. There is no
 * GET list endpoint on the backend yet, so token management (revoke /
 * browse issued links) is out of scope here; Tearsheet only needs create. */
export function useCreateToken() {
  return useMutation({
    mutationFn: (body: { label: string; expires_at: string }) => api.post<AllocatorToken>("/allocator/tokens", body),
  });
}

export type AllocatorViewPayload = {
  label: string;
  generated_at: string;
  returns: Record<string, Metric>;
  risk: Record<string, Metric> & { top_5_drawdowns: DrawdownEntry[] };
  risk_adjusted: Record<string, Metric>;
  statistical_validity: Record<string, Metric> & { sharpe_ci: [number, number] | null };
  trades: Record<string, unknown>;
  verdict: Verdict;
};

/** GET /api/allocator/view?token=... — public, read-only. The API already
 * redacts journal/emotional-state/balance fields; the frontend simply
 * never reaches for keys that aren't in this payload. */
export function useAllocatorView(token: string | undefined) {
  return useQuery({
    queryKey: ["allocator-view", token ?? null],
    queryFn: () => api.get<AllocatorViewPayload>(`/allocator/view?token=${encodeURIComponent(token as string)}`),
    enabled: !!token,
    retry: false,
  });
}
