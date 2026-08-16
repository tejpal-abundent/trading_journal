import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export type AuditType = "correction" | "amendment";

export type AuditFeedItem = {
  id: string;
  type: AuditType;
  occurred_at: string;
  reason: string;
  details: Record<string, unknown>;
};

/** GET /api/audit?since=&type= — unified corrections + policy amendments feed. */
export function useAudit(filters?: { since?: string; type?: AuditType }) {
  const qs = new URLSearchParams();
  if (filters?.since) qs.set("since", filters.since);
  if (filters?.type) qs.set("type", filters.type);
  const q = qs.toString();
  return useQuery({
    queryKey: ["audit", filters?.since ?? null, filters?.type ?? null],
    queryFn: () => api.get<AuditFeedItem[]>(`/audit${q ? `?${q}` : ""}`),
  });
}
