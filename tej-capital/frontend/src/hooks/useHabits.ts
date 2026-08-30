import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type HabitCategory = "trading" | "personal" | "body" | "sleep";

export type HabitDefinition = {
  id: string;
  key: string;
  label: string;
  category: HabitCategory;
  sort_order: number;
  is_active: boolean;
};

export type HabitStat = {
  current_streak: number;
  longest_streak: number;
  completion_pct_this_month: number;
};

export type HabitMonthLog = {
  days: string[];
  /** habit_id -> { "YYYY-MM-DD": status } — sparse, only answered days. */
  entries: Record<string, Record<string, boolean>>;
  definitions: HabitDefinition[];
  /** habit_id -> streak/completion stats. */
  stats: Record<string, HabitStat>;
};

const DEFINITIONS_KEY = ["habit-definitions"];
const monthKey = (year: number, month: number) => ["habit-month", year, month];

/** GET /api/habits/definitions — the editable list of tracked behaviours. */
export function useHabitDefinitions() {
  return useQuery({
    queryKey: DEFINITIONS_KEY,
    queryFn: () => api.get<HabitDefinition[]>("/habits/definitions"),
  });
}

/** GET /api/habits/log?year=&month= — one month's grid, sparse entries + streak stats. */
export function useHabitMonth(year: number, month: number) {
  return useQuery({
    queryKey: monthKey(year, month),
    queryFn: () => api.get<HabitMonthLog>(`/habits/log?year=${year}&month=${month}`),
  });
}

function useInvalidateHabits() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["habit-month"], exact: false });
    qc.invalidateQueries({ queryKey: DEFINITIONS_KEY });
  };
}

/** PUT /api/habits/log/{date}/{habit_id} — upsert today's (or any day's) answer. */
export function useToggleHabit() {
  const invalidate = useInvalidateHabits();
  return useMutation({
    mutationFn: ({ date, habitId, status }: { date: string; habitId: string; status: boolean }) =>
      api.put(`/habits/log/${date}/${habitId}`, { status }),
    onSuccess: invalidate,
  });
}

/** DELETE /api/habits/log/{date}/{habit_id} — back to "unanswered". */
export function useDeleteHabitLog() {
  const invalidate = useInvalidateHabits();
  return useMutation({
    mutationFn: ({ date, habitId }: { date: string; habitId: string }) =>
      api.del(`/habits/log/${date}/${habitId}`),
    onSuccess: invalidate,
  });
}

/** POST /api/habits/definitions — add a habit to the list. */
export function useCreateDefinition() {
  const invalidate = useInvalidateHabits();
  return useMutation({
    mutationFn: (body: { key: string; label: string; category: HabitCategory; sort_order?: number }) =>
      api.post<HabitDefinition>("/habits/definitions", body),
    onSuccess: invalidate,
  });
}

/** PATCH /api/habits/definitions/{id} — rename/reorder/retire (key + category are immutable). */
export function useUpdateDefinition() {
  const invalidate = useInvalidateHabits();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; label?: string; sort_order?: number; is_active?: boolean }) =>
      api.patch<HabitDefinition>(`/habits/definitions/${id}`, body),
    onSuccess: invalidate,
  });
}

/** DELETE /api/habits/definitions/{id} — hard delete, cascades its log entries. */
export function useDeleteDefinition() {
  const invalidate = useInvalidateHabits();
  return useMutation({
    mutationFn: (id: string) => api.del(`/habits/definitions/${id}`),
    onSuccess: invalidate,
  });
}
