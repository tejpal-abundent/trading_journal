import { useEffect, useState } from "react";
import { api, Expectancy, DashboardStreak, MindsetPrompt } from "../api";
import { formatCurrency } from "../lib/dashboard";

interface Props {
  expectancy: Expectancy;
  streak: DashboardStreak;
}

type State = "losing-streak" | "winning-streak" | "small-sample" | "calm" | "outcome-vs-execution";

function readState(e: Expectancy, s: DashboardStreak): State {
  if (s.kind === "loss" && s.length >= 2) return "losing-streak";
  if (s.kind === "win"  && s.length >= 3) return "winning-streak";
  if (e.trades < 10) return "small-sample";
  return "calm";
}

/** Pick the mindset prompt that best fits the current state. */
function selectPrompt(prompts: MindsetPrompt[], state: State): MindsetPrompt | null {
  if (prompts.length === 0) return null;

  const match = (substr: string) => prompts.find(p => p.text.toLowerCase().includes(substr));

  // Priority: state → matching prompt
  if (state === "losing-streak")  return match("abandoning") ?? match("variance") ?? prompts[0];
  if (state === "winning-streak") return match("risking too much") ?? match("feel something") ?? prompts[0];
  if (state === "small-sample")   return match("judging") ?? match("few trades") ?? prompts[0];
  if (state === "outcome-vs-execution") return match("good outcomes") ?? prompts[0];

  // Rotate daily through the rest
  const day = Math.floor(Date.now() / (1000 * 60 * 60 * 24));
  return prompts[day % prompts.length];
}

const HEADLINE: Record<State, (e: Expectancy, s: DashboardStreak) => string> = {
  "losing-streak": (e, s) =>
    `${s.length} losses in a row. Your edge is still ${e.value >= 0 ? "+" : ""}${formatCurrency(e.value)}/trade. Variance is normal.`,
  "winning-streak": (e, s) =>
    `${s.length} wins in a row. Your edge is ${e.value >= 0 ? "+" : ""}${formatCurrency(e.value)}/trade.`,
  "small-sample": (e) =>
    `Only ${e.trades} closed trades. Sample is too small to judge.`,
  "calm": (e) =>
    `You're ${e.value >= 0 ? "+" : ""}${formatCurrency(e.value)}/trade across ${e.trades} trades. Edge confirmed.`,
  "outcome-vs-execution": (e) =>
    `${e.trades} trades logged. Stay focused on process, not outcomes.`,
};

export default function VarianceCoach({ expectancy, streak }: Props) {
  const [prompts, setPrompts] = useState<MindsetPrompt[]>([]);
  useEffect(() => { api.listMindsetPrompts().then(setPrompts); }, []);

  const state = readState(expectancy, streak);
  const headline = HEADLINE[state](expectancy, streak);
  const prompt = selectPrompt(prompts, state);

  const accent =
    state === "losing-streak"  ? "var(--yellow)" :
    state === "winning-streak" ? "var(--yellow)" :
    state === "small-sample"   ? "var(--blue)" :
                                  "var(--green)";

  return (
    <div className="card" style={{ borderLeft: `4px solid ${accent}` }}>
      <div className="text-xs text-2" style={{ letterSpacing: 1, textTransform: "uppercase" }}>
        Mindset check
      </div>
      <div className="text-sm" style={{ marginTop: 6 }}>{headline}</div>
      {prompt && (
        <div className="text-sm font-500" style={{ marginTop: 12, color: accent }}>
          ▸ {prompt.text}
        </div>
      )}
    </div>
  );
}
