# Trading Journal — Statistical Honesty Layer

**Date:** 2026-04-29
**Author:** tejpal@buildfactory.io
**Status:** Approved for planning

## 1. Goal

The journal already captures the four phases of a trade and computes win rates, expectancy, plan adherence, and an edge composite. What it does *not* tell the user is whether any of those numbers are statistically meaningful, what variance to expect, or how much the user's own indiscipline is contaminating the sample.

This layer adds the missing **statistical honesty**: confidence intervals on every rate, expected variance vs. actual, a clean-sample edge, a process-vs-outcome scorecard, and "don't tilt" guardrails during normal losing streaks.

The work is informed by the law-of-large-numbers framing from Renaissance Technologies / Jim Simons / Nassim Taleb: *small edges compound at scale, but only if you don't quit at normal variance and only if your sample isn't contaminated by emotional deviations.*

## 2. Scope

**In scope (all 8 items):**

1. **Wilson confidence interval** on every win rate / proportion in the analytics payload.
2. **Confidence label** (`Noise` / `Noisy` / `Reasonable` / `Strong` / `Conviction`) on every metric, using the video's exact thresholds (30 / 100 / 500 / 1000).
3. **Sample integrity** block — clean trades vs. all trades, with the win-rate delta exposed as the "cost of indiscipline."
4. **Streak expectations** block — Schilling's expected longest losing streak vs. actual vs. current.
5. **Process scorecard** — composite "% of trades that are *both* clean AND rule-followed," shown as a top-line metric on the Review tab.
6. **Frequency flag on `strategy_breakdown`** — strategies with under 30 trades flagged "insufficient sample."
7. **Don't-bail banner** — UI banner when the user is inside the expected-loss-streak envelope.
8. **Regime / fat-tail caveat** — `regime_coverage` block reminding the user the sample needs months across regimes, plus a Taleb-style fat-tail footnote on confidence intervals.

**Out of scope:**

- Schema changes — none. All work is in `analytics.py` + new `stats.py` + frontend.
- Per-trade fields — no new columns. All four new blocks are derived from existing data.
- Multi-user, auth, broker imports — same as the v2 spec.
- Monte Carlo simulators or bootstrapped CIs — Wilson is sufficient at the sample sizes this journal sees.

## 3. Decisions log (from brainstorming)

| Question | Choice | Implication |
|---|---|---|
| Which items to ship? | A — all 8 | Comprehensive layer in one release |
| Confidence thresholds | Video numbers exactly: 30 / 100 / 500 / 1000 | `Noise` / `Noisy` / `Reasonable` / `Strong` / `Conviction` |
| "Clean trade" definition | `retroactive=0 AND rules_followed=1 AND no mistake_tags AND entry_timing='on_time'` | Strictest definition — surfaces the "casino-discipline" trade |
| `process_score.composite` | Strict — % of trades that are *both* clean AND rule-followed (not an average of the two) | Tighter signal; harder to game |
| CI method | Wilson 95% (closed-form, no scipy) | Works at low N where normal approx breaks |
| Streak math | Schilling approximation, closed-form | No simulation; deterministic |
| Where it lives | New `backend/stats.py`, extend `backend/analytics.py`, extend `frontend/src/components/Review.tsx` | Additive; no migration |

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  GET /api/analytics  (unchanged URL, payload grows)          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  backend/analytics.py                                        │
│   ─ existing _score_analysis / _pair_breakdown / etc         │
│   ─ NEW: _sample_integrity, _streak_expectations,            │
│           _process_score, _regime_coverage                   │
│   ─ each existing block decorated with `_ci`, `_confidence`  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  backend/stats.py  (NEW, ~80 lines, pure)                    │
│   ─ wilson_ci(wins, n)                                       │
│   ─ confidence_label(n)                                      │
│   ─ expected_max_loss_streak(p_loss, n)                      │
│   ─ current_streak(closed_trades_in_order)                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  frontend/src/components/Review.tsx                          │
│   ─ existing cards decorated with confidence badges          │
│   ─ NEW SampleIntegrityCard                                  │
│   ─ NEW VarianceExpectationsCard                             │
│   ─ NEW ProcessScorecardCard                                 │
│   ─ NEW DontBailBanner (top of Review tab)                   │
│  frontend/src/lib/confidence.ts  (NEW formatter)             │
└─────────────────────────────────────────────────────────────┘
```

No new endpoints. No schema changes. No migration required. Existing API consumers continue to read the fields they read today; new fields are additive.

## 5. Backend

### 5.1 New module: `backend/stats.py`

Pure functions, no dependencies beyond `math`.

```python
import math

CONFIDENCE_THRESHOLDS = [
    (30,   "Noise"),       # under 30 trades = pure noise (per video)
    (100,  "Noisy"),
    (500,  "Reasonable"),
    (1000, "Strong"),
]
# n >= 1000 -> "Conviction"


def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% Wilson interval for a proportion. Returns (lo, hi) on the 0–100 scale.
    Returns None if n == 0."""
    if n <= 0:
        return None
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lo = (centre - margin) / denom
    hi = (centre + margin) / denom
    return (round(lo * 100, 1), round(hi * 100, 1))


def confidence_label(n: int) -> str:
    for threshold, label in CONFIDENCE_THRESHOLDS:
        if n < threshold:
            return label
    return "Conviction"


def expected_max_loss_streak(p_loss: float, n: int) -> int:
    """Schilling approximation for the longest run of losses in n trials.
    Returns 0 if inputs are degenerate."""
    if n <= 0 or p_loss <= 0 or p_loss >= 1:
        return 0
    # E[longest run] ≈ log_(1/p_loss)( n * (1 - p_loss) )
    return max(1, round(math.log(n * (1 - p_loss)) / math.log(1 / p_loss)))


def current_streak(closed_trades_in_order: list[dict]) -> dict:
    """closed_trades_in_order must be sorted by closed_at ascending.
    Looks at the tail to find the current win/loss streak (breakeven breaks the streak)."""
    kind, length, longest_loss = "none", 0, 0
    # Compute longest_loss across the whole list
    run = 0
    for t in closed_trades_in_order:
        if t["status"] == "loss":
            run += 1
            longest_loss = max(longest_loss, run)
        else:
            run = 0
    # Compute current streak from the tail
    for t in reversed(closed_trades_in_order):
        if t["status"] in ("win", "loss"):
            if length == 0:
                kind = t["status"]
                length = 1
            elif t["status"] == kind:
                length += 1
            else:
                break
        else:
            break  # breakeven breaks the streak
    return {"kind": kind, "length": length, "longest_loss": longest_loss}
```

Pure, no I/O, fully unit-testable.

### 5.2 Decorating existing analytics blocks

Every place that emits a `win_rate: X` field gains two siblings: `win_rate_ci: [lo, hi]` and `confidence: "label"`. The wrapper helper:

```python
def _decorate(wins: int, n: int) -> dict:
    return {
        "n": n,
        "win_rate_ci": wilson_ci(wins, n),
        "confidence": confidence_label(n),
    }
```

Affected existing blocks (each row gets `_decorate(...)` merged in):

- top-level `win_rate` (uses `len(wins)` / `len(closed)`)
- `score_analysis` buckets (A / B / C / D)
- `pair_breakdown` rows
- `direction_stats.LONG` and `.SHORT`
- `plan_adherence.rules_followed_win_rate` and `rules_broken_win_rate` (denominators are `len(followed)` and `len(broken)`)
- `mistake_impact` rows
- `emotion_impact.entry` and `.exit` rows
- `timing_impact` buckets (`on_time` / `late` / `early`)
- `strategy_breakdown` rows (also gets `frequency_warning` — see 5.3.5)
- `confluence_impact` rows
- `edge_composite` (gets `win_rate_ci`, `confidence` next to existing `win_rate`)

These decorations are additive: existing keys keep their existing names and types.

### 5.3 New analytics blocks

Five new top-level keys returned from `compute_analytics()`. Each is implemented as its own `_function` mirroring the style of the existing helpers.

#### 5.3.1 `sample_integrity`

```json
"sample_integrity": {
  "definition": "rules_followed=1 AND no mistake_tags AND retroactive=0 AND entry_timing='on_time'",
  "clean_count": 11,
  "total_count": 18,
  "clean_pct": 61.1,
  "clean_win_rate": 72.7,
  "clean_win_rate_ci": [43.4, 90.3],
  "clean_confidence": "Noise",
  "all_win_rate": 61.1,
  "all_win_rate_ci": [38.5, 79.6],
  "all_confidence": "Noise",
  "integrity_delta": 11.6
}
```

Predicate (a closed trade is **clean** iff all four hold):

- `retroactive == 0` — the user actually planned the trade in advance
- `rules_followed == 1` — explicit yes, not null
- `mistake_tags` is empty (the comma-wrapped representation is exactly `,`)
- `entry_timing == 'on_time'` — not `late`, not `early`, not null

`integrity_delta = clean_win_rate - all_win_rate`. Positive value means discipline pays off; negative means the user's "clean" subset is unlucky or the predicate is too restrictive (early-stage data).

Denominator for `clean_pct` is `total_count` = closed trades only (`status in win/loss/breakeven`). Trades where `rules_followed` is null are *not* clean.

#### 5.3.2 `streak_expectations`

```json
"streak_expectations": {
  "p_loss": 0.39,
  "expected_max_loss_streak": 3,
  "actual_max_loss_streak": 5,
  "current_streak": { "kind": "loss", "length": 2 },
  "five_loss_streak_every_n_trades": 112,
  "fat_tail_caveat": "Markets have fat tails — expected streaks can underestimate real-world variance."
}
```

Computation:

- `p_loss = len(losses) / len(closed)` (breakeven excluded from both numerator and denominator).
- `expected_max_loss_streak = expected_max_loss_streak(p_loss, len(closed))`.
- `actual_max_loss_streak = current_streak(...).longest_loss` (sorted by `closed_at`).
- `current_streak` = `current_streak(...)` returned as `{kind, length}` (drop `longest_loss` here — it's already in `actual_max_loss_streak`).
- `five_loss_streak_every_n_trades` — the headline factoid from the video. Computed as `int(round(1 / p_loss ** 5))` for `p_loss > 0`, else `null`. *(Note: this is "1 in N trades" expected to start a 5-loss run; not the same as expected gap. It's the headline number from the video, kept for educational value, with the caveat noted.)*

If `len(closed) == 0` the entire block is `{"insufficient_data": true}`.

#### 5.3.3 `process_score`

```json
"process_score": {
  "definition": "Strict: % of closed trades that are clean AND rule-followed (same predicate as sample_integrity)",
  "rules_followed_pct": 73.0,
  "no_mistakes_pct": 66.0,
  "clean_pct": 61.1,
  "composite": 61.1,
  "process_winrate_minus_outcome_winrate": 11.6
}
```

Decisions:

- `composite` is the **strict** measure (chosen from brainstorm): trades that satisfy *all* four clean-predicate conditions. This equals `sample_integrity.clean_pct`. It's surfaced separately under a "process" framing because it's the single number the user is asked to optimize.
- `rules_followed_pct` and `no_mistakes_pct` retained as diagnostic sub-scores so the user can see *which* leg drags `composite` down.
- `process_winrate_minus_outcome_winrate = clean_win_rate − all_win_rate` (same as `integrity_delta` — duplicated here under the process lens because Review.tsx renders this card separately).

Denominator for `rules_followed_pct`: `len([t for t in closed if t['rules_followed'] is not None])` (consistent with existing `plan_adherence.rules_followed_pct`).
Denominator for `no_mistakes_pct`: `len(closed)`.

#### 5.3.4 `regime_coverage`

```json
"regime_coverage": {
  "span_days": 14,
  "n_trades": 18,
  "warning": "Sample spans 14 days. Markets need 6+ months across multiple regimes for confidence.",
  "fat_tail_caveat": "Markets have fat tails — true confidence may need 10× more trades than the math suggests (Taleb)."
}
```

- `span_days` = `(max(closed_at) − min(closed_at)).days` over closed trades, or `period_end − period_start` if both are passed in. Pick whichever is larger so the user sees the broader span.
- `warning` is rendered when `span_days < 180` *or* `n_trades < 100`. Otherwise the field is `null`.
- `fat_tail_caveat` is always present (rendered as a footnote next to CIs on the frontend).

#### 5.3.5 `strategy_breakdown` extension

Each row gains:

```json
{
  "strategy": "Zone Failure",
  "count": 18,
  "win_rate": 61.1,
  "expectancy": 24.0,
  "win_rate_ci": [38.5, 79.6],   // NEW
  "confidence": "Noise",          // NEW
  "frequency_warning": "Under 30 trades — insufficient sample"  // NEW (or null)
}
```

`frequency_warning` is `"Under 30 trades — insufficient sample"` when `count < 30`, else `null`.

### 5.4 Field naming convention

To keep the payload predictable:

- Every win-rate field `X` gains siblings `X_ci: [lo, hi] | null` and a sibling `confidence` (or `X_confidence` when there are multiple WRs in the same object — e.g. `clean_confidence` and `all_confidence` on `sample_integrity`).
- All `_ci` values are rounded to 1 decimal, on the 0–100 scale, matching `win_rate`.
- All `_pct` and `_rate` values continue to be rounded to 1 decimal as in the existing code.

### 5.5 Backwards compatibility

- No existing field is renamed, removed, or has its type changed.
- New fields are additions to existing objects. The frontend currently ignores unknown fields (TypeScript types will be relaxed before the new UI consumes them — see 6.4).
- `tests/test_analytics.py` continues to pass on existing assertions; new assertions cover the new blocks.

## 6. Frontend

### 6.1 New formatter: `src/lib/confidence.ts`

```ts
export type CIBlock = { n: number; win_rate_ci: [number, number] | null; confidence: string };

export function formatRateWithCI(rate: number, ci: CIBlock): string {
  // "61.1% ±18 (n=18, Noisy)"
  if (!ci.win_rate_ci) return `${rate}% (n=${ci.n})`;
  const [lo, hi] = ci.win_rate_ci;
  const halfWidth = Math.round((hi - lo) / 2);
  return `${rate}% ±${halfWidth} (n=${ci.n}, ${ci.confidence})`;
}

export function confidenceColor(label: string): string {
  // Tailwind utility class for the badge background
  return {
    "Noise":      "bg-red-100 text-red-700",
    "Noisy":      "bg-orange-100 text-orange-700",
    "Reasonable": "bg-yellow-100 text-yellow-700",
    "Strong":     "bg-green-100 text-green-700",
    "Conviction": "bg-emerald-100 text-emerald-700",
  }[label] ?? "bg-gray-100 text-gray-700";
}
```

### 6.2 Decorated existing UI

Existing tables and stat blocks in `Review.tsx` that show win rates today get a confidence badge appended to each row's win-rate cell. Same for the headline win-rate at the top of the Review tab.

The fat-tail caveat from `regime_coverage.fat_tail_caveat` is rendered once as a footnote at the bottom of the analytics dashboard (small, italicized, next to a tooltip icon).

### 6.3 New cards

#### `SampleIntegrityCard.tsx`

Reads `analytics.sample_integrity`. Layout:

```
┌──────────────────────────────────────────────────────┐
│ ⚖️  Sample Integrity                                 │
│                                                      │
│ Clean trades: 11 of 18 (61%)                         │
│ Definition: rules followed + no mistakes +           │
│             on-time entry + planned in advance       │
│                                                      │
│ Clean win rate    72.7% ±24  (n=11, Noise)           │
│ All trades WR     61.1% ±18  (n=18, Noise)           │
│ Discipline edge   +11.6 pp                           │
└──────────────────────────────────────────────────────┘
```

If `clean_count == 0`, render `"No clean trades yet — log a trade where rules_followed=yes, no mistake tags, on-time entry, planned in advance."` instead of the metrics.

#### `VarianceExpectationsCard.tsx`

Reads `analytics.streak_expectations`. Layout:

```
┌──────────────────────────────────────────────────────┐
│ 📉  Variance Expectations                            │
│                                                      │
│ Loss probability:        39%                         │
│ Expected max loss streak: 3  (in 18 trades)          │
│ Your actual:              5                          │
│ Current streak:           2 losses                   │
│                                                      │
│ At your loss rate, a 5-loss streak starts roughly    │
│ once every 112 trades. Don't quit at normal variance. │
└──────────────────────────────────────────────────────┘
```

If `insufficient_data`, render `"No closed trades yet."` placeholder.

#### `ProcessScorecardCard.tsx`

Reads `analytics.process_score`. Layout:

```
┌──────────────────────────────────────────────────────┐
│ 🎯  Process Scorecard                                │
│ Judge the process, not individual outcomes.          │
│                                                      │
│ Composite (strict)    61.1   ← optimize this         │
│ Rules followed        73%                            │
│ No mistakes           66%                            │
│ Clean entries         61%                            │
│                                                      │
│ Process bonus: +11.6 pp WR when sample is clean.     │
└──────────────────────────────────────────────────────┘
```

The "composite" is the headline; the three sub-scores are diagnostic.

#### `DontBailBanner.tsx`

Conditionally rendered at the top of the Review tab when:

```ts
const s = analytics.streak_expectations;
const showBanner =
  s &&
  s.current_streak.kind === "loss" &&
  s.current_streak.length >= 2 &&
  s.current_streak.length <= s.expected_max_loss_streak;
```

Copy:

```
ℹ {length} losses in a row is normal at your {p_loss*100}% loss rate.
   Expected max streak in {n_trades} trades is {expected_max_loss_streak}.
   Don't tilt — keep the system.
```

When `current_streak.length > expected_max_loss_streak` the banner switches to a softer warning:

```
⚠ {length}-loss streak exceeds the {expected} expected for {n} trades.
   Could be variance, could be a regime shift. Review before next trade.
```

(This second variant addresses the fat-tail caveat in the user's daily flow.)

### 6.4 TypeScript types

Extend `src/api.ts` `Analytics` type with the new fields, all marked optional initially:

```ts
type CIBlock = { win_rate_ci?: [number, number] | null; confidence?: string };

type Analytics = {
  // ... existing fields ...
  win_rate: number;
  win_rate_ci?: [number, number] | null;
  confidence?: string;
  n?: number;

  sample_integrity?: { ... };
  streak_expectations?: { ... } | { insufficient_data: true };
  process_score?: { ... };
  regime_coverage?: { ... };

  strategy_breakdown: Array<{
    strategy: string;
    count: number;
    win_rate: number;
    expectancy: number;
    win_rate_ci?: [number, number] | null;
    confidence?: string;
    frequency_warning?: string | null;
  }>;
};
```

Optional during the rollout window so frontend doesn't break before backend is deployed.

### 6.5 File structure

| File | Action | Purpose |
|---|---|---|
| `frontend/src/lib/confidence.ts` | NEW | `formatRateWithCI`, `confidenceColor` |
| `frontend/src/components/SampleIntegrityCard.tsx` | NEW | Renders `sample_integrity` |
| `frontend/src/components/VarianceExpectationsCard.tsx` | NEW | Renders `streak_expectations` |
| `frontend/src/components/ProcessScorecardCard.tsx` | NEW | Renders `process_score` |
| `frontend/src/components/DontBailBanner.tsx` | NEW | Conditional banner |
| `frontend/src/components/Review.tsx` | EDIT | Mount the four new components; decorate existing rate cells with confidence badges |
| `frontend/src/api.ts` | EDIT | Extend `Analytics` type with new optional fields |
| `backend/stats.py` | NEW | Pure stats helpers |
| `backend/analytics.py` | EDIT | Decorate existing blocks; add four new computations |
| `backend/tests/test_stats.py` | NEW | Wilson, Schilling, label, current_streak unit tests |
| `backend/tests/test_analytics.py` | EDIT | Assertions on the new blocks |

## 7. Testing

### 7.1 `backend/tests/test_stats.py` (new)

- `wilson_ci(0, 0)` → `None`
- `wilson_ci(50, 100)` → CI brackets ~50% with width matching reference value
- `wilson_ci(1, 1)` → does not return `[100, 100]` (Wilson's small-N behavior)
- `confidence_label`: boundary checks at 29 / 30 / 99 / 100 / 499 / 500 / 999 / 1000 / 1001
- `expected_max_loss_streak(0.5, 100)` ≈ ~6, sanity checks at extremes (`p_loss=0`, `p_loss=1`, `n=0`)
- `current_streak`: empty list, all-wins, all-losses, mixed, breakeven-breaks-streak

### 7.2 `backend/tests/test_analytics.py` (extend)

For each new block:

- `sample_integrity`: build 5 closed trades, 3 clean (all four predicates true), assert `clean_count=3`, `clean_pct=60.0`, `integrity_delta = clean_wr - all_wr`.
- `streak_expectations`: build 10 closed trades with a known LLLWLLW...; assert `actual_max_loss_streak` matches; assert `current_streak.length` matches; assert `expected_max_loss_streak` is a positive int.
- `process_score`: assert `composite == sample_integrity.clean_pct`; assert sub-scores compute on correct denominators.
- `regime_coverage`: pass `period_start`/`period_end` 30 days apart, assert `span_days=30` and `warning` is non-null; pass 200 days with `n_trades >= 100`, assert `warning is None`.
- `strategy_breakdown`: 20 trades on one strategy → `frequency_warning` set; 50 trades → `frequency_warning is None`.

### 7.3 No frontend automated tests

Manual checklist (added to the implementation plan):

- Headline win rate shows a confidence badge.
- Each card renders.
- `DontBailBanner` shows during a 2-loss streak when expected max ≥ 2; shifts to warning variant past expected.
- Tooltip on the fat-tail footnote opens.

## 8. Rollout

1. Land `stats.py` + tests first (no payload change).
2. Land analytics decorations + new blocks; deploy backend.
3. Land frontend changes that consume the new fields. Until that ships, the existing UI ignores the additions (TypeScript marks them optional).

No DB migration. No infra change. Single Render redeploy + single Cloudflare deploy.

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Wilson CI is approximate at very low N (n<5) | The label downgrades to `Noise` and the UI surfaces the warning prominently; the CI is still computed and shown — the user is informed, not lied to |
| Schilling approximation for streaks is for IID Bernoulli; markets aren't IID | `fat_tail_caveat` is rendered next to the streak number; `DontBailBanner` warning variant covers exceedance |
| `clean_count=0` could disable the integrity card silently | Card renders an explicit empty-state message instead of nothing |
| Strict process composite may discourage the user (sub-30%) | Diagnostic sub-scores (rules-followed, no-mistakes, clean-entries) are shown alongside the composite so they can see which leg to fix |
| `five_loss_streak_every_n_trades` is a simplification of the video's claim | Caveat included; field documented as "headline approximation" not a precise expectation |

## 10. Open items (to revisit after MVP)

- Bootstrap CIs (less assumption-heavy than Wilson) when the dataset is large enough to support them.
- A proper Monte Carlo "given your edge, here's a 95% drawdown envelope" simulator on the Review tab.
- Multi-regime tagging on trades (manual `regime: bull|bear|chop` tag) so `regime_coverage` can show actual regime breadth, not just elapsed days.
- Per-strategy streak expectations (currently aggregated across all strategies).
