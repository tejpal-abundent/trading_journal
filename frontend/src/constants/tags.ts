export const MISTAKE_TAGS = [
  "moved_sl", "exited_early", "oversized",
  "chased_entry", "against_trend", "ignored_news",
  "fomo_entry", "no_plan", "revenge_trade", "held_too_long",
] as const;

export const EMOTION_TAGS = [
  "confident", "patient", "anxious", "fearful", "fomo",
  "greedy", "frustrated", "calm", "hesitant", "excited",
] as const;

export const ENTRY_TIMING = ["on_time", "late", "early"] as const;

export const PARTIAL_EXIT_REASONS = [
  "took_profit", "cut_loss", "scaled_out", "sl_adjusted",
] as const;

export const labelize = (tag: string) =>
  tag.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
