import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type NavMark = {
  id: string;
  account_id: string;
  as_of_date: string;
  /** Decimal — serialized as a string by the API to preserve precision. */
  closing_equity: string;
  superseded_by: string | null;
  superseded_reason: string | null;
};

export type MarkExistsConflict = {
  error: "mark_exists";
  existing_id: string | null;
  hint: string;
};

function isMarkExistsConflict(body: unknown): body is { detail: MarkExistsConflict } {
  const detail = (body as { detail?: unknown } | undefined)?.detail;
  return !!detail && typeof detail === "object" && (detail as { error?: string }).error === "mark_exists";
}

/** GET /api/accounts/{id}/nav?since=YYYY-MM-DD — current (non-superseded) marks, oldest first. */
export function useNav(accountId: string | undefined, since?: string) {
  return useQuery({
    queryKey: ["nav", accountId, since ?? null],
    queryFn: () => api.get<NavMark[]>(`/accounts/${accountId}/nav${since ? `?since=${since}` : ""}`),
    enabled: !!accountId,
  });
}

function invalidateNav(qc: ReturnType<typeof useQueryClient>, accountId: string | undefined) {
  qc.invalidateQueries({ queryKey: ["nav", accountId], exact: false });
}

/** POST /api/accounts/{id}/nav — create a mark. 409 mark_exists means the caller should
 * switch to correction mode; the conflict's existing_id is surfaced via error.body. */
export function useSubmitMark(accountId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { as_of_date: string; closing_equity: string }) =>
      api.post<NavMark>(`/accounts/${accountId}/nav`, body),
    onSuccess: () => invalidateNav(qc, accountId),
  });
}

/** POST /api/accounts/{id}/nav/correct — reason must be >= 10 chars (enforced server-side too). */
export function useCorrectMark(accountId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { as_of_date: string; closing_equity: string; reason: string }) =>
      api.post<NavMark>(`/accounts/${accountId}/nav/correct`, body),
    onSuccess: () => invalidateNav(qc, accountId),
  });
}

export { isMarkExistsConflict };
