# Statistical Honesty Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add statistical honesty (Wilson CIs, expected variance, sample integrity, process scorecard, frequency/regime warnings, don't-bail banner) on top of the existing analytics dashboard.

**Architecture:** Pure additive layer. New `backend/stats.py` (Wilson CI + Schilling streak math + label). `backend/analytics.py` extended with four new top-level blocks and CI decorations on every existing win-rate. Four new React cards on the Review tab + a conditional banner. No schema changes, no API URL changes, no migration.

**Tech Stack:** Python 3 + pytest (backend), React 18 + TypeScript + Tailwind (frontend).

**Related spec:** `docs/superpowers/specs/2026-04-29-statistical-honesty-design.md`

---

## File map

| Path | Action | Purpose |
|---|---|---|
| `backend/stats.py` | CREATE | `wilson_ci`, `confidence_label`, `expected_max_loss_streak`, `current_streak` |
| `backend/tests/test_stats.py` | CREATE | Unit tests for stats helpers |
| `backend/analytics.py` | MODIFY | Decorate existing blocks with `_ci`/`confidence`; add 4 new blocks; extend `strategy_breakdown` |
| `backend/tests/test_analytics.py` | MODIFY | Assertions on the new blocks |
| `frontend/src/api.ts` | MODIFY | Extend `AnalyticsData` type with new optional fields |
| `frontend/src/lib/confidence.ts` | CREATE | `formatRateWithCI`, `confidenceColor` |
| `frontend/src/components/SampleIntegrityCard.tsx` | CREATE | Renders `sample_integrity` |
| `frontend/src/components/VarianceExpectationsCard.tsx` | CREATE | Renders `streak_expectations` |
| `frontend/src/components/ProcessScorecardCard.tsx` | CREATE | Renders `process_score` |
| `frontend/src/components/DontBailBanner.tsx` | CREATE | Conditional banner above the dashboard |
| `frontend/src/components/Review.tsx` | MODIFY | Mount the four new components; decorate existing rate cells with confidence badges |

---

## Conventions

**Run tests from inside `backend/`:**

```bash
cd backend && pytest tests/ -v
```

**Tests file path** in steps below is shown relative to repo root (`backend/tests/...`); run from `backend/` and use `tests/...`.

**Commits:** Each task ends with one commit. Conventional-commits style (`feat:`, `test:`, etc.). All commits include the standard `Co-Authored-By` trailer.

---

## Task 1: `wilson_ci` helper

**Files:**
- Create: `backend/stats.py`
- Create: `backend/tests/test_stats.py`

- [ ] **Step 1.1: Write the failing test for Wilson CI**

Create `backend/tests/test_stats.py`:

```python
from stats import wilson_ci


def test_wilson_ci_zero_n_returns_none():
    assert wilson_ci(0, 0) is None


def test_wilson_ci_50_of_100_brackets_50_percent():
    lo, hi = wilson_ci(50, 100)
    assert 39.0 < lo < 41.0
    assert 59.0 < hi < 61.0


def test_wilson_ci_1_of_1_does_not_return_100_100():
    lo, hi = wilson_ci(1, 1)
    assert lo < 100.0
    assert hi == 100.0  # upper bound *can* hit 100 at p=1
    assert lo < 50.0    # lower bound must be well below 100


def test_wilson_ci_returns_tuple_rounded_to_one_decimal():
    lo, hi = wilson_ci(7, 18)
    # Both values should have at most 1 decimal place
    assert lo == round(lo, 1)
    assert hi == round(hi, 1)


def test_wilson_ci_ordering():
    lo, hi = wilson_ci(11, 18)
    assert lo < hi
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_stats.py -v
```

Expected: ImportError or ModuleNotFoundError on `from stats import wilson_ci`.

- [ ] **Step 1.3: Implement `wilson_ci` in `backend/stats.py`**

```python
"""Pure statistical helpers for the analytics layer.

No I/O, no globals, no scipy dependency — closed-form Wilson interval
and Schilling expected-streak approximation are sufficient for the
sample sizes this journal sees.
"""
import math


def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% Wilson interval for a proportion.

    Returns (lo, hi) on the 0-100 scale, rounded to 1 decimal.
    Returns None if n == 0.
    """
    if n <= 0:
        return None
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lo = (centre - margin) / denom
    hi = (centre + margin) / denom
    return (round(lo * 100, 1), round(hi * 100, 1))
```

- [ ] **Step 1.4: Run tests to verify pass**

```bash
cd backend && pytest tests/test_stats.py -v
```

Expected: 5 passed.

- [ ] **Step 1.5: Commit**

```bash
git add backend/stats.py backend/tests/test_stats.py
git commit -m "$(cat <<'EOF'
feat(stats): add Wilson confidence interval helper

Closed-form 95% Wilson interval, no scipy dependency. Returns None for
empty sample. First building block of the statistical honesty layer.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `confidence_label` helper

**Files:**
- Modify: `backend/stats.py`
- Modify: `backend/tests/test_stats.py`

- [ ] **Step 2.1: Add failing tests**

Append to `backend/tests/test_stats.py`:

```python
from stats import confidence_label


def test_confidence_label_boundaries():
    # Per the video: <30 noise, <100 noisy, <500 reasonable, <1000 strong, >=1000 conviction
    assert confidence_label(0) == "Noise"
    assert confidence_label(29) == "Noise"
    assert confidence_label(30) == "Noisy"
    assert confidence_label(99) == "Noisy"
    assert confidence_label(100) == "Reasonable"
    assert confidence_label(499) == "Reasonable"
    assert confidence_label(500) == "Strong"
    assert confidence_label(999) == "Strong"
    assert confidence_label(1000) == "Conviction"
    assert confidence_label(10_000) == "Conviction"
```

- [ ] **Step 2.2: Run to verify failure**

```bash
cd backend && pytest tests/test_stats.py::test_confidence_label_boundaries -v
```

Expected: ImportError on `confidence_label`.

- [ ] **Step 2.3: Implement `confidence_label`**

Append to `backend/stats.py`:

```python
CONFIDENCE_THRESHOLDS = [
    (30,   "Noise"),       # under 30 trades = pure noise (per video)
    (100,  "Noisy"),
    (500,  "Reasonable"),
    (1000, "Strong"),
]


def confidence_label(n: int) -> str:
    for threshold, label in CONFIDENCE_THRESHOLDS:
        if n < threshold:
            return label
    return "Conviction"
```

- [ ] **Step 2.4: Run tests**

```bash
cd backend && pytest tests/test_stats.py -v
```

Expected: 6 passed (5 from Task 1 + 1 new).

- [ ] **Step 2.5: Commit**

```bash
git add backend/stats.py backend/tests/test_stats.py
git commit -m "$(cat <<'EOF'
feat(stats): add confidence_label with video thresholds

Labels: Noise <30, Noisy <100, Reasonable <500, Strong <1000, Conviction >=1000.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `expected_max_loss_streak` helper

**Files:**
- Modify: `backend/stats.py`
- Modify: `backend/tests/test_stats.py`

- [ ] **Step 3.1: Add failing tests**

Append to `backend/tests/test_stats.py`:

```python
from stats import expected_max_loss_streak


def test_expected_streak_zero_n():
    assert expected_max_loss_streak(0.5, 0) == 0


def test_expected_streak_p_loss_zero():
    assert expected_max_loss_streak(0.0, 100) == 0


def test_expected_streak_p_loss_one():
    assert expected_max_loss_streak(1.0, 100) == 0  # degenerate, return 0


def test_expected_streak_50_50_100_trades():
    # Schilling: log(100*0.5)/log(2) = log(50)/log(2) ≈ 5.64 → 6
    result = expected_max_loss_streak(0.5, 100)
    assert 5 <= result <= 7


def test_expected_streak_returns_at_least_one():
    # Even tiny n should give >=1 if math is degenerate-ish
    assert expected_max_loss_streak(0.5, 2) >= 1
```

- [ ] **Step 3.2: Run to verify failure**

```bash
cd backend && pytest tests/test_stats.py -v -k expected_streak
```

Expected: ImportError.

- [ ] **Step 3.3: Implement**

Append to `backend/stats.py`:

```python
def expected_max_loss_streak(p_loss: float, n: int) -> int:
    """Schilling approximation for the longest run of losses in n trials.

    E[longest run] ≈ log_(1/p_loss)( n * (1 - p_loss) )

    Returns 0 if inputs are degenerate (n==0, p_loss<=0, p_loss>=1).
    """
    if n <= 0 or p_loss <= 0 or p_loss >= 1:
        return 0
    expected = math.log(n * (1 - p_loss)) / math.log(1 / p_loss)
    return max(1, round(expected))
```

- [ ] **Step 3.4: Run tests**

```bash
cd backend && pytest tests/test_stats.py -v
```

Expected: 11 passed.

- [ ] **Step 3.5: Commit**

```bash
git add backend/stats.py backend/tests/test_stats.py
git commit -m "$(cat <<'EOF'
feat(stats): add Schilling expected-max-loss-streak

Closed-form approximation for the longest run of losses in n IID trials.
Used by the variance expectations card to set "this is normal" thresholds.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `current_streak` helper

**Files:**
- Modify: `backend/stats.py`
- Modify: `backend/tests/test_stats.py`

- [ ] **Step 4.1: Add failing tests**

Append to `backend/tests/test_stats.py`:

```python
from stats import current_streak


def test_current_streak_empty():
    s = current_streak([])
    assert s == {"kind": "none", "length": 0, "longest_loss": 0}


def test_current_streak_all_wins():
    trades = [{"status": "win"}] * 5
    s = current_streak(trades)
    assert s == {"kind": "win", "length": 5, "longest_loss": 0}


def test_current_streak_all_losses():
    trades = [{"status": "loss"}] * 4
    s = current_streak(trades)
    assert s == {"kind": "loss", "length": 4, "longest_loss": 4}


def test_current_streak_mixed_tail_loss():
    # win, loss, loss, win, loss, loss, loss → tail is 3 losses; longest_loss is 3
    trades = [
        {"status": "win"}, {"status": "loss"}, {"status": "loss"},
        {"status": "win"}, {"status": "loss"}, {"status": "loss"}, {"status": "loss"},
    ]
    s = current_streak(trades)
    assert s == {"kind": "loss", "length": 3, "longest_loss": 3}


def test_current_streak_breakeven_breaks_streak():
    # loss, loss, breakeven → tail is broken, kind=none, length=0; longest_loss=2
    trades = [{"status": "loss"}, {"status": "loss"}, {"status": "breakeven"}]
    s = current_streak(trades)
    assert s == {"kind": "none", "length": 0, "longest_loss": 2}


def test_current_streak_longest_loss_in_middle():
    # loss×4 in the middle, then a win at the end
    trades = [
        {"status": "win"},
        {"status": "loss"}, {"status": "loss"}, {"status": "loss"}, {"status": "loss"},
        {"status": "win"},
    ]
    s = current_streak(trades)
    assert s == {"kind": "win", "length": 1, "longest_loss": 4}
```

- [ ] **Step 4.2: Run to verify failure**

```bash
cd backend && pytest tests/test_stats.py -v -k current_streak
```

Expected: ImportError.

- [ ] **Step 4.3: Implement**

Append to `backend/stats.py`:

```python
def current_streak(closed_trades_in_order: list[dict]) -> dict:
    """closed_trades_in_order must be sorted by closed_at ascending.

    Returns {kind, length, longest_loss}.
    - longest_loss: the longest loss run anywhere in the input.
    - kind/length: the *current* trailing streak (breakeven breaks it).
    """
    longest_loss = 0
    run = 0
    for t in closed_trades_in_order:
        if t["status"] == "loss":
            run += 1
            longest_loss = max(longest_loss, run)
        else:
            run = 0

    kind, length = "none", 0
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

- [ ] **Step 4.4: Run tests**

```bash
cd backend && pytest tests/test_stats.py -v
```

Expected: 17 passed.

- [ ] **Step 4.5: Commit**

```bash
git add backend/stats.py backend/tests/test_stats.py
git commit -m "$(cat <<'EOF'
feat(stats): add current_streak helper

Tracks current win/loss streak from the tail, plus the longest historical
loss streak. Breakeven breaks the current streak.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Decorate top-level win_rate with CI + confidence

**Files:**
- Modify: `backend/analytics.py`
- Modify: `backend/tests/test_analytics.py`

- [ ] **Step 5.1: Add failing test**

Append to `backend/tests/test_analytics.py` (do not remove existing tests):

```python
def test_top_level_win_rate_decorated_with_ci():
    trades = [_trade(status="win", pnl=20), _trade(status="loss", pnl=-10)]
    a = compute_analytics(trades, days=14)
    assert a["win_rate"] == 50.0
    assert a["n"] == 2
    assert isinstance(a["win_rate_ci"], (list, tuple))
    assert len(a["win_rate_ci"]) == 2
    assert a["confidence"] == "Noise"


def test_top_level_win_rate_no_closed_trades():
    trades = [_trade(status="planned")]
    a = compute_analytics(trades, days=14)
    assert a["n"] == 0
    assert a["win_rate_ci"] is None
    assert a["confidence"] == "Noise"
```

- [ ] **Step 5.2: Run to verify failure**

```bash
cd backend && pytest tests/test_analytics.py::test_top_level_win_rate_decorated_with_ci -v
```

Expected: KeyError on `n`.

- [ ] **Step 5.3: Modify `backend/analytics.py`**

Add an import at the top:

```python
from stats import wilson_ci, confidence_label, expected_max_loss_streak, current_streak
```

In `compute_analytics()`, after the existing `closed = [...]` line, before the `return {...}`, add a top-level `n` and decorate win_rate. Update the returned dict to include `n`, `win_rate_ci`, and `confidence`:

Existing return shape (relevant excerpt):
```python
return {
    ...
    "win_rate": round(win_rate, 1),
    ...
}
```

Replace with:
```python
n_closed = len(closed)
return {
    ...
    "win_rate": round(win_rate, 1),
    "n": n_closed,
    "win_rate_ci": wilson_ci(len(wins), n_closed),
    "confidence": confidence_label(n_closed),
    ...
}
```

(Keep all other existing keys exactly as they are — additive only.)

- [ ] **Step 5.4: Run tests**

```bash
cd backend && pytest tests/test_analytics.py -v
```

Expected: all existing tests still pass + 2 new pass.

- [ ] **Step 5.5: Commit**

```bash
git add backend/analytics.py backend/tests/test_analytics.py
git commit -m "$(cat <<'EOF'
feat(analytics): decorate top-level win_rate with Wilson CI and confidence label

Adds n / win_rate_ci / confidence siblings to the headline win rate.
Existing fields are preserved unchanged.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `_decorate` helper + decorate sub-blocks

**Files:**
- Modify: `backend/analytics.py`
- Modify: `backend/tests/test_analytics.py`

- [ ] **Step 6.1: Add failing tests**

Append to `backend/tests/test_analytics.py`:

```python
def test_score_analysis_rows_have_ci_and_confidence():
    trades = [
        _trade(status="win", setup_score=90, pnl=20),
        _trade(status="loss", setup_score=88, pnl=-10),
        _trade(status="win", setup_score=75, pnl=15),
    ]
    a = compute_analytics(trades, days=14)["score_analysis"]
    assert "A (85-100)" in a
    assert "n" in a["A (85-100)"]
    assert "win_rate_ci" in a["A (85-100)"]
    assert "confidence" in a["A (85-100)"]


def test_pair_breakdown_has_ci():
    trades = [
        _trade(status="win", pair="XAU/USD", pnl=10),
        _trade(status="loss", pair="XAU/USD", pnl=-5),
        _trade(status="win", pair="EUR/USD", pnl=20),
    ]
    a = compute_analytics(trades, days=14)["pair_breakdown"]
    assert "win_rate_ci" in a["XAU/USD"]
    assert "confidence" in a["XAU/USD"]


def test_direction_stats_has_ci():
    trades = [
        _trade(status="win", direction="LONG", pnl=10),
        _trade(status="loss", direction="LONG", pnl=-5),
    ]
    a = compute_analytics(trades, days=14)["direction_stats"]
    assert "win_rate_ci" in a["LONG"]
    assert a["LONG"]["confidence"] == "Noise"


def test_mistake_impact_rows_have_ci():
    trades = [
        _trade(status="win", pnl=10, mistake_tags=["moved_sl"]),
        _trade(status="loss", pnl=-5, mistake_tags=["moved_sl"]),
    ]
    rows = compute_analytics(trades, days=14)["mistake_impact"]
    for r in rows:
        assert "win_rate_ci" in r
        assert "confidence" in r


def test_timing_impact_buckets_have_ci():
    trades = [
        _trade(status="win", entry_timing="on_time", pnl=10),
        _trade(status="loss", entry_timing="late", pnl=-5),
    ]
    a = compute_analytics(trades, days=14)["timing_impact"]
    assert "win_rate_ci" in a["on_time"]
    assert "confidence" in a["on_time"]
```

- [ ] **Step 6.2: Run tests to verify failure**

```bash
cd backend && pytest tests/test_analytics.py -v
```

Expected: 5 new tests fail with KeyError on `win_rate_ci`.

- [ ] **Step 6.3: Add `_decorate` helper to `backend/analytics.py`**

Just after the `RISK_THRESHOLD_PCT = 2.0` line, add:

```python
def _decorate(wins: int, n: int) -> dict:
    """Returns the standard CI-decoration dict to merge into a row."""
    return {
        "n": n,
        "win_rate_ci": wilson_ci(wins, n),
        "confidence": confidence_label(n),
    }
```

- [ ] **Step 6.4: Decorate `_score_analysis`**

Replace the body of `_score_analysis` so each bucket also includes `**_decorate(...)`. Locate the existing block:

```python
def _score_analysis(closed):
    buckets = {"A (85-100)": [], "B (70-84)": [], "C (55-69)": [], "D (<55)": []}
    for t in closed:
        s = t["setup_score"]
        if s >= 85: buckets["A (85-100)"].append(t)
        elif s >= 70: buckets["B (70-84)"].append(t)
        elif s >= 55: buckets["C (55-69)"].append(t)
        else: buckets["D (<55)"].append(t)
    out = {}
    for bucket, bt in buckets.items():
        if bt:
            bw = [t for t in bt if t["status"] == "win"]
            out[bucket] = {
                "count": len(bt),
                "win_rate": round(len(bw) / len(bt) * 100, 1),
                "avg_pnl": round(sum(t["pnl"] or 0 for t in bt) / len(bt), 2),
            }
    return out
```

Replace the inner dict construction with:

```python
            out[bucket] = {
                "count": len(bt),
                "win_rate": round(len(bw) / len(bt) * 100, 1),
                "avg_pnl": round(sum(t["pnl"] or 0 for t in bt) / len(bt), 2),
                **_decorate(len(bw), len(bt)),
            }
```

- [ ] **Step 6.5: Decorate `_pair_breakdown`**

The existing function only counts wins / losses / pnl. Extend the row to also carry `n` and decorate. Replace:

```python
def _pair_breakdown(closed):
    pairs = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0})
    for t in closed:
        p = t["pair"]
        if t["status"] == "win": pairs[p]["wins"] += 1
        elif t["status"] == "loss": pairs[p]["losses"] += 1
        pairs[p]["pnl"] = round(pairs[p]["pnl"] + (t["pnl"] or 0), 2)
    return dict(pairs)
```

With:

```python
def _pair_breakdown(closed):
    pairs = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0, "_n": 0})
    for t in closed:
        p = t["pair"]
        pairs[p]["_n"] += 1
        if t["status"] == "win": pairs[p]["wins"] += 1
        elif t["status"] == "loss": pairs[p]["losses"] += 1
        pairs[p]["pnl"] = round(pairs[p]["pnl"] + (t["pnl"] or 0), 2)
    out = {}
    for p, agg in pairs.items():
        out[p] = {
            "wins": agg["wins"], "losses": agg["losses"], "pnl": agg["pnl"],
            "win_rate": round(agg["wins"] / agg["_n"] * 100, 1) if agg["_n"] else 0,
            **_decorate(agg["wins"], agg["_n"]),
        }
    return out
```

- [ ] **Step 6.6: Decorate `_direction_stats`**

Replace existing body's inner dict:

```python
        out[d] = {
            "count": len(rows),
            "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
            "pnl": round(sum(t["pnl"] or 0 for t in rows), 2),
        }
```

With:

```python
        out[d] = {
            "count": len(rows),
            "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
            "pnl": round(sum(t["pnl"] or 0 for t in rows), 2),
            **_decorate(len(wins), len(rows)),
        }
```

- [ ] **Step 6.7: Decorate `_tag_impact`**

In `_tag_impact`, the rows currently look like:

```python
        rows.append({
            "tag": tag,
            "count": agg["count"],
            "win_rate": round(agg["wins"] / agg["count"] * 100, 1) if agg["count"] else 0,
            "avg_pnl": round(agg["pnl_sum"] / agg["count"], 2) if agg["count"] else 0,
            "total_pnl": round(agg["pnl_sum"], 2),
        })
```

Replace with:

```python
        rows.append({
            "tag": tag,
            "count": agg["count"],
            "win_rate": round(agg["wins"] / agg["count"] * 100, 1) if agg["count"] else 0,
            "avg_pnl": round(agg["pnl_sum"] / agg["count"], 2) if agg["count"] else 0,
            "total_pnl": round(agg["pnl_sum"], 2),
            **_decorate(agg["wins"], agg["count"]),
        })
```

(This single change covers `mistake_impact`, `emotion_impact.entry`, `emotion_impact.exit`, and `confluence_impact` since they all use this helper.)

- [ ] **Step 6.8: Decorate `_timing_impact`**

Replace the inner dict:

```python
        out[bucket] = {
            "count": len(rows),
            "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
        }
```

With:

```python
        out[bucket] = {
            "count": len(rows),
            "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
            **_decorate(len(wins), len(rows)),
        }
```

- [ ] **Step 6.9: Decorate `_plan_adherence`**

Update `_plan_adherence` to add `_ci`/`_confidence` siblings on the two win-rate fields. Find the return dict and replace:

```python
    return {
        "rules_followed_pct": round(len(followed) / len(rules_known) * 100, 1) if rules_known else 0,
        "rules_followed_win_rate": round(len(fwins) / len(followed) * 100, 1) if followed else 0,
        "rules_broken_win_rate": round(len(bwins) / len(broken) * 100, 1) if broken else 0,
        "skip_rate": round(len(skipped) / len(planned_lifecycle) * 100, 1) if planned_lifecycle else 0,
        "retroactive_rate": round(
            len([t for t in trades if t["retroactive"]]) / len(trades) * 100, 1
        ) if trades else 0,
    }
```

With:

```python
    fci  = wilson_ci(len(fwins), len(followed)) if followed else None
    bci  = wilson_ci(len(bwins), len(broken)) if broken else None
    return {
        "rules_followed_pct": round(len(followed) / len(rules_known) * 100, 1) if rules_known else 0,
        "rules_followed_win_rate": round(len(fwins) / len(followed) * 100, 1) if followed else 0,
        "rules_followed_win_rate_ci": fci,
        "rules_followed_confidence": confidence_label(len(followed)),
        "rules_broken_win_rate": round(len(bwins) / len(broken) * 100, 1) if broken else 0,
        "rules_broken_win_rate_ci": bci,
        "rules_broken_confidence": confidence_label(len(broken)),
        "skip_rate": round(len(skipped) / len(planned_lifecycle) * 100, 1) if planned_lifecycle else 0,
        "retroactive_rate": round(
            len([t for t in trades if t["retroactive"]]) / len(trades) * 100, 1
        ) if trades else 0,
    }
```

- [ ] **Step 6.10: Run all analytics tests**

```bash
cd backend && pytest tests/test_analytics.py -v
```

Expected: all pre-existing tests still pass + 5 new tests pass.

- [ ] **Step 6.11: Commit**

```bash
git add backend/analytics.py backend/tests/test_analytics.py
git commit -m "$(cat <<'EOF'
feat(analytics): decorate sub-blocks with Wilson CI and confidence labels

Adds n / win_rate_ci / confidence to score_analysis, pair_breakdown,
direction_stats, mistake_impact, emotion_impact, confluence_impact,
timing_impact, and plan_adherence's two win-rate fields.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `sample_integrity` block

**Files:**
- Modify: `backend/analytics.py`
- Modify: `backend/tests/test_analytics.py`

- [ ] **Step 7.1: Add failing test**

Append to `backend/tests/test_analytics.py`:

```python
def test_sample_integrity_clean_predicate():
    # 5 closed trades; 3 are clean (rules_followed=True, no mistakes,
    # not retroactive, on_time entry); 2 are not clean.
    trades = [
        _trade(status="win", pnl=20, rules_followed=True, mistake_tags=[],
               retroactive=False, entry_timing="on_time"),
        _trade(status="win", pnl=15, rules_followed=True, mistake_tags=[],
               retroactive=False, entry_timing="on_time"),
        _trade(status="loss", pnl=-10, rules_followed=True, mistake_tags=[],
               retroactive=False, entry_timing="on_time"),
        # not clean: late entry
        _trade(status="loss", pnl=-15, rules_followed=True, mistake_tags=[],
               retroactive=False, entry_timing="late"),
        # not clean: has mistake
        _trade(status="loss", pnl=-5, rules_followed=True,
               mistake_tags=["moved_sl"], retroactive=False, entry_timing="on_time"),
    ]
    s = compute_analytics(trades, days=14)["sample_integrity"]
    assert s["clean_count"] == 3
    assert s["total_count"] == 5
    assert s["clean_pct"] == 60.0
    assert s["clean_win_rate"] == round(2 / 3 * 100, 1)
    assert s["all_win_rate"] == 40.0
    assert s["integrity_delta"] == round(s["clean_win_rate"] - s["all_win_rate"], 1)


def test_sample_integrity_no_clean_trades():
    trades = [_trade(status="loss", pnl=-10, rules_followed=False, mistake_tags=["moved_sl"])]
    s = compute_analytics(trades, days=14)["sample_integrity"]
    assert s["clean_count"] == 0
    assert s["clean_win_rate"] == 0
    assert s["clean_win_rate_ci"] is None


def test_sample_integrity_excludes_null_rules_followed():
    # rules_followed is None → not clean (per spec)
    trades = [
        _trade(status="win", pnl=10, rules_followed=None, mistake_tags=[],
               retroactive=False, entry_timing="on_time"),
    ]
    s = compute_analytics(trades, days=14)["sample_integrity"]
    assert s["clean_count"] == 0
```

- [ ] **Step 7.2: Run to verify failure**

```bash
cd backend && pytest tests/test_analytics.py -v -k sample_integrity
```

Expected: KeyError on `sample_integrity`.

- [ ] **Step 7.3: Implement `_sample_integrity`**

In `backend/analytics.py`, add the helper just before `_edge_composite`:

```python
def _is_clean(t: dict) -> bool:
    """Strict clean-trade predicate from the spec.

    A closed trade is clean iff:
      - retroactive == 0  (planned in advance)
      - rules_followed == True  (explicit yes, not None)
      - mistake_tags is empty
      - entry_timing == 'on_time'
    """
    return (
        not t["retroactive"]
        and t["rules_followed"] is True
        and not t["mistake_tags"]
        and t["entry_timing"] == "on_time"
    )


def _sample_integrity(closed):
    total = len(closed)
    clean = [t for t in closed if _is_clean(t)]
    clean_n = len(clean)
    clean_wins = [t for t in clean if t["status"] == "win"]
    all_wins = [t for t in closed if t["status"] == "win"]

    clean_wr = round(len(clean_wins) / clean_n * 100, 1) if clean_n else 0
    all_wr = round(len(all_wins) / total * 100, 1) if total else 0

    return {
        "definition": (
            "rules_followed=True AND no mistake_tags AND retroactive=False "
            "AND entry_timing='on_time'"
        ),
        "clean_count": clean_n,
        "total_count": total,
        "clean_pct": round(clean_n / total * 100, 1) if total else 0,
        "clean_win_rate": clean_wr,
        "clean_win_rate_ci": wilson_ci(len(clean_wins), clean_n),
        "clean_confidence": confidence_label(clean_n),
        "all_win_rate": all_wr,
        "all_win_rate_ci": wilson_ci(len(all_wins), total),
        "all_confidence": confidence_label(total),
        "integrity_delta": round(clean_wr - all_wr, 1),
    }
```

In `compute_analytics()` return dict, add the new key:

```python
        "sample_integrity": _sample_integrity(closed),
```

(Place it after `"mfe_mae_analysis": ...,` for readability.)

- [ ] **Step 7.4: Run tests**

```bash
cd backend && pytest tests/test_analytics.py -v
```

Expected: all pass.

- [ ] **Step 7.5: Commit**

```bash
git add backend/analytics.py backend/tests/test_analytics.py
git commit -m "$(cat <<'EOF'
feat(analytics): add sample_integrity block

Computes clean-trade subset (rules followed + no mistakes + planned in
advance + on-time entry) and exposes the win-rate delta as the cost
of indiscipline.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: `streak_expectations` block

**Files:**
- Modify: `backend/analytics.py`
- Modify: `backend/tests/test_analytics.py`

- [ ] **Step 8.1: Add failing tests**

Append to `backend/tests/test_analytics.py`:

```python
def test_streak_expectations_basic():
    # 18 closed trades, 11 wins, 7 losses → p_loss ≈ 0.389
    trades = [_trade(status="win", pnl=10) for _ in range(11)] + \
             [_trade(status="loss", pnl=-5) for _ in range(7)]
    s = compute_analytics(trades, days=14)["streak_expectations"]
    assert "p_loss" in s
    assert 0.38 < s["p_loss"] < 0.40
    assert s["expected_max_loss_streak"] >= 1
    assert s["five_loss_streak_every_n_trades"] is not None


def test_streak_expectations_actual_max_loss_streak():
    # Build a sequence with a known longest losing run.
    # Order matters: closed_at ascending. Use distinct timestamps.
    seq = ["win", "loss", "loss", "loss", "win", "loss", "loss", "win"]
    trades = []
    for i, st in enumerate(seq):
        trades.append(_trade(
            status=st,
            pnl=10 if st == "win" else -5,
            closed_at=f"2026-04-{20 + i:02d}T10:00:00",
        ))
    s = compute_analytics(trades, days=14)["streak_expectations"]
    assert s["actual_max_loss_streak"] == 3


def test_streak_expectations_current_streak_kind():
    seq = ["win", "loss", "loss"]
    trades = [_trade(status=st, pnl=(10 if st == "win" else -5),
                     closed_at=f"2026-04-{20 + i:02d}T10:00:00") for i, st in enumerate(seq)]
    s = compute_analytics(trades, days=14)["streak_expectations"]
    assert s["current_streak"]["kind"] == "loss"
    assert s["current_streak"]["length"] == 2


def test_streak_expectations_insufficient_data():
    trades = [_trade(status="planned")]
    s = compute_analytics(trades, days=14)["streak_expectations"]
    assert s == {"insufficient_data": True}


def test_streak_expectations_all_wins_no_losses():
    # p_loss = 0, expected_max_loss_streak should be 0
    trades = [_trade(status="win", pnl=10) for _ in range(5)]
    s = compute_analytics(trades, days=14)["streak_expectations"]
    assert s["p_loss"] == 0.0
    assert s["expected_max_loss_streak"] == 0
    assert s["five_loss_streak_every_n_trades"] is None
```

- [ ] **Step 8.2: Run to verify failure**

```bash
cd backend && pytest tests/test_analytics.py -v -k streak_expectations
```

Expected: KeyError on `streak_expectations`.

- [ ] **Step 8.3: Implement `_streak_expectations`**

Add to `backend/analytics.py` just below `_sample_integrity`:

```python
def _streak_expectations(closed):
    """Variance expectations from p_loss and sample size.

    closed must be list of closed trades (status in win/loss/breakeven).
    """
    if not closed:
        return {"insufficient_data": True}

    losses = [t for t in closed if t["status"] == "loss"]
    wins = [t for t in closed if t["status"] == "win"]
    decisive = len(losses) + len(wins)
    if decisive == 0:
        return {"insufficient_data": True}

    p_loss = len(losses) / decisive

    # Sort by closed_at ascending for streak math
    ordered = sorted(closed, key=lambda t: t.get("closed_at") or "")
    streak = current_streak(ordered)

    five_loss_every_n = (
        round(1 / (p_loss ** 5)) if p_loss > 0 else None
    )

    return {
        "p_loss": round(p_loss, 3),
        "expected_max_loss_streak": expected_max_loss_streak(p_loss, len(closed)),
        "actual_max_loss_streak": streak["longest_loss"],
        "current_streak": {"kind": streak["kind"], "length": streak["length"]},
        "five_loss_streak_every_n_trades": five_loss_every_n,
        "fat_tail_caveat": (
            "Markets have fat tails — expected streaks can underestimate "
            "real-world variance."
        ),
    }
```

In `compute_analytics()` return dict, add:

```python
        "streak_expectations": _streak_expectations(closed),
```

- [ ] **Step 8.4: Run tests**

```bash
cd backend && pytest tests/test_analytics.py -v
```

Expected: all pass.

- [ ] **Step 8.5: Commit**

```bash
git add backend/analytics.py backend/tests/test_analytics.py
git commit -m "$(cat <<'EOF'
feat(analytics): add streak_expectations block

Exposes p_loss, Schilling expected max loss streak, actual max loss streak,
current trailing streak, and the "5-loss streak every N trades" headline.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: `process_score` block

**Files:**
- Modify: `backend/analytics.py`
- Modify: `backend/tests/test_analytics.py`

- [ ] **Step 9.1: Add failing tests**

Append to `backend/tests/test_analytics.py`:

```python
def test_process_score_composite_equals_sample_integrity_clean_pct():
    trades = [
        _trade(status="win", rules_followed=True, mistake_tags=[],
               retroactive=False, entry_timing="on_time", pnl=10),
        _trade(status="loss", rules_followed=False, mistake_tags=["moved_sl"],
               retroactive=False, entry_timing="late", pnl=-5),
        _trade(status="win", rules_followed=True, mistake_tags=[],
               retroactive=False, entry_timing="on_time", pnl=15),
    ]
    a = compute_analytics(trades, days=14)
    assert a["process_score"]["composite"] == a["sample_integrity"]["clean_pct"]


def test_process_score_sub_scores():
    # 4 closed: 3 with rules_followed=True (1 of which is None), 1 false
    # 3 with no mistakes; 1 with mistake_tags
    trades = [
        _trade(status="win",  rules_followed=True,  mistake_tags=[], pnl=10),
        _trade(status="win",  rules_followed=True,  mistake_tags=[], pnl=10),
        _trade(status="loss", rules_followed=False, mistake_tags=["moved_sl"], pnl=-5),
        _trade(status="win",  rules_followed=None,  mistake_tags=[], pnl=10),
    ]
    p = compute_analytics(trades, days=14)["process_score"]
    # rules_followed_pct denominator = trades with rules_followed not None = 3
    # 2 of 3 followed → 66.7%
    assert p["rules_followed_pct"] == round(2 / 3 * 100, 1)
    # no_mistakes denominator = all closed (4); 3 have no mistakes
    assert p["no_mistakes_pct"] == 75.0


def test_process_score_winrate_delta():
    trades = [
        _trade(status="win",  rules_followed=True, mistake_tags=[],
               retroactive=False, entry_timing="on_time", pnl=10),
        _trade(status="loss", rules_followed=False, mistake_tags=["moved_sl"],
               retroactive=False, entry_timing="late", pnl=-5),
    ]
    a = compute_analytics(trades, days=14)
    delta = a["process_score"]["process_winrate_minus_outcome_winrate"]
    assert delta == a["sample_integrity"]["integrity_delta"]
```

- [ ] **Step 9.2: Run to verify failure**

```bash
cd backend && pytest tests/test_analytics.py -v -k process_score
```

Expected: KeyError on `process_score`.

- [ ] **Step 9.3: Implement `_process_score`**

Add to `backend/analytics.py`, just below `_streak_expectations`:

```python
def _process_score(closed, sample_integrity):
    """Process scorecard: judge process, not outcomes.

    composite = strict; same as sample_integrity.clean_pct.
    Sub-scores are diagnostic so the user can see which leg drags it down.
    """
    rules_known = [t for t in closed if t["rules_followed"] is not None]
    followed = [t for t in rules_known if t["rules_followed"]]
    no_mistakes = [t for t in closed if not t["mistake_tags"]]

    return {
        "definition": (
            "Strict: % of closed trades that satisfy ALL of "
            "rules_followed AND no mistake_tags AND retroactive=False "
            "AND entry_timing='on_time'"
        ),
        "rules_followed_pct": (
            round(len(followed) / len(rules_known) * 100, 1) if rules_known else 0
        ),
        "no_mistakes_pct": (
            round(len(no_mistakes) / len(closed) * 100, 1) if closed else 0
        ),
        "clean_pct": sample_integrity["clean_pct"],
        "composite": sample_integrity["clean_pct"],
        "process_winrate_minus_outcome_winrate": sample_integrity["integrity_delta"],
    }
```

In `compute_analytics()`, restructure so `_sample_integrity` is computed once and reused. Replace the two new lines added in earlier tasks:

```python
        "sample_integrity": _sample_integrity(closed),
        "streak_expectations": _streak_expectations(closed),
```

with:

```python
        # NOTE: sample_integrity computed first; process_score reuses it
        "sample_integrity": (si := _sample_integrity(closed)),
        "streak_expectations": _streak_expectations(closed),
        "process_score": _process_score(closed, si),
```

(The walrus operator `(si := ...)` is fine on Python 3.8+; backend tests run on 3.11+.)

- [ ] **Step 9.4: Run tests**

```bash
cd backend && pytest tests/test_analytics.py -v
```

Expected: all pass.

- [ ] **Step 9.5: Commit**

```bash
git add backend/analytics.py backend/tests/test_analytics.py
git commit -m "$(cat <<'EOF'
feat(analytics): add process_score block

Strict composite (matches sample_integrity.clean_pct) plus diagnostic
sub-scores (rules_followed_pct, no_mistakes_pct) and the WR delta when
the sample is clean.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: `regime_coverage` block

**Files:**
- Modify: `backend/analytics.py`
- Modify: `backend/tests/test_analytics.py`

- [ ] **Step 10.1: Add failing tests**

Append to `backend/tests/test_analytics.py`:

```python
def test_regime_coverage_warning_for_short_span():
    trades = [_trade(status="win", pnl=10) for _ in range(5)]
    a = compute_analytics(trades, days=14, period_start="2026-04-15", period_end="2026-04-29")
    rc = a["regime_coverage"]
    assert rc["span_days"] >= 14
    assert rc["n_trades"] == 5
    assert rc["warning"] is not None
    assert "fat_tail_caveat" in rc


def test_regime_coverage_no_warning_for_long_high_n():
    # 200+ days span and 100+ trades → no warning
    trades = [_trade(status="win", pnl=1) for _ in range(120)]
    a = compute_analytics(trades, days=200, period_start="2025-09-01", period_end="2026-04-29")
    rc = a["regime_coverage"]
    assert rc["warning"] is None
```

- [ ] **Step 10.2: Run to verify failure**

```bash
cd backend && pytest tests/test_analytics.py -v -k regime_coverage
```

Expected: KeyError.

- [ ] **Step 10.3: Implement `_regime_coverage`**

Add to `backend/analytics.py`:

```python
from datetime import datetime


def _regime_coverage(trades, period_start, period_end):
    """Span / sample-size warning + fat-tail caveat.

    span_days = max(period span, actual trade-data span). The warning fires
    when EITHER span < 180 days OR n_trades < 100.
    """
    n_trades = len(trades)

    closed_dates = [t.get("closed_at") for t in trades if t.get("closed_at")]
    data_span_days = 0
    if closed_dates:
        try:
            parsed = sorted(
                datetime.fromisoformat(d.replace("Z", "+00:00")) for d in closed_dates
            )
            data_span_days = (parsed[-1] - parsed[0]).days
        except (ValueError, TypeError):
            data_span_days = 0

    period_span_days = 0
    if period_start and period_end:
        try:
            ps = datetime.fromisoformat(period_start)
            pe = datetime.fromisoformat(period_end)
            period_span_days = (pe - ps).days
        except (ValueError, TypeError):
            period_span_days = 0

    span_days = max(data_span_days, period_span_days)

    warning = None
    if span_days < 180 or n_trades < 100:
        warning = (
            f"Sample spans {span_days} days with {n_trades} trades. "
            "Markets need 6+ months across multiple regimes for confidence."
        )

    return {
        "span_days": span_days,
        "n_trades": n_trades,
        "warning": warning,
        "fat_tail_caveat": (
            "Markets have fat tails — true confidence may need 10x more "
            "trades than the math suggests (Taleb)."
        ),
    }
```

In `compute_analytics()` return dict, add:

```python
        "regime_coverage": _regime_coverage(trades, period_start, period_end),
```

- [ ] **Step 10.4: Run tests**

```bash
cd backend && pytest tests/test_analytics.py -v
```

Expected: all pass.

- [ ] **Step 10.5: Commit**

```bash
git add backend/analytics.py backend/tests/test_analytics.py
git commit -m "$(cat <<'EOF'
feat(analytics): add regime_coverage block

Span and sample-size warning when the dataset is too short or too small,
plus the Taleb fat-tail caveat for the dashboard footnote.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: `strategy_breakdown` decoration + frequency_warning

**Files:**
- Modify: `backend/analytics.py`
- Modify: `backend/tests/test_analytics.py`

- [ ] **Step 11.1: Add failing tests**

Append to `backend/tests/test_analytics.py`:

```python
def test_strategy_breakdown_under_30_has_frequency_warning():
    trades = [_trade(status="win", strategy="Zone Failure", pnl=10) for _ in range(10)]
    rows = compute_analytics(trades, days=14)["strategy_breakdown"]
    s = next(r for r in rows if r["strategy"] == "Zone Failure")
    assert s["frequency_warning"] == "Under 30 trades — insufficient sample"
    assert s["confidence"] == "Noise"
    assert s["win_rate_ci"] is not None


def test_strategy_breakdown_30_or_more_no_frequency_warning():
    trades = [_trade(status="win", strategy="Zone Failure", pnl=10) for _ in range(35)]
    rows = compute_analytics(trades, days=14)["strategy_breakdown"]
    s = next(r for r in rows if r["strategy"] == "Zone Failure")
    assert s["frequency_warning"] is None
    assert s["confidence"] == "Noisy"
```

- [ ] **Step 11.2: Run to verify failure**

```bash
cd backend && pytest tests/test_analytics.py -v -k strategy_breakdown
```

Expected: KeyError on `frequency_warning` or `confidence`.

- [ ] **Step 11.3: Modify `_strategy_breakdown`**

Replace the existing function body's row construction:

```python
        out.append({
            "strategy": s,
            "count": len(rows),
            "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
            "expectancy": round(sum(t["pnl"] or 0 for t in rows) / len(rows), 2) if rows else 0,
        })
```

With:

```python
        out.append({
            "strategy": s,
            "count": len(rows),
            "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
            "expectancy": round(sum(t["pnl"] or 0 for t in rows) / len(rows), 2) if rows else 0,
            **_decorate(len(wins), len(rows)),
            "frequency_warning": (
                "Under 30 trades — insufficient sample" if len(rows) < 30 else None
            ),
        })
```

- [ ] **Step 11.4: Run tests**

```bash
cd backend && pytest tests/test_analytics.py -v
```

Expected: all pass.

- [ ] **Step 11.5: Commit**

```bash
git add backend/analytics.py backend/tests/test_analytics.py
git commit -m "$(cat <<'EOF'
feat(analytics): decorate strategy_breakdown with CI + frequency warning

Each strategy row now carries n, win_rate_ci, confidence, and a
frequency_warning that flags strategies under 30 trades.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Frontend type extensions

**Files:**
- Modify: `frontend/src/api.ts`

- [ ] **Step 12.1: Extend the `AnalyticsData` interface**

Open `frontend/src/api.ts`. The interface starts at line 83. Replace it (in place) with the version below — every change is **additive**; do not remove existing fields.

```ts
export interface CIDecoration {
  n?: number
  win_rate_ci?: [number, number] | null
  confidence?: string
}

export interface SampleIntegrity {
  definition: string
  clean_count: number
  total_count: number
  clean_pct: number
  clean_win_rate: number
  clean_win_rate_ci: [number, number] | null
  clean_confidence: string
  all_win_rate: number
  all_win_rate_ci: [number, number] | null
  all_confidence: string
  integrity_delta: number
}

export type StreakExpectations =
  | { insufficient_data: true }
  | {
      p_loss: number
      expected_max_loss_streak: number
      actual_max_loss_streak: number
      current_streak: { kind: 'win' | 'loss' | 'none'; length: number }
      five_loss_streak_every_n_trades: number | null
      fat_tail_caveat: string
    }

export interface ProcessScore {
  definition: string
  rules_followed_pct: number
  no_mistakes_pct: number
  clean_pct: number
  composite: number
  process_winrate_minus_outcome_winrate: number
}

export interface RegimeCoverage {
  span_days: number
  n_trades: number
  warning: string | null
  fat_tail_caveat: string
}

export interface AnalyticsData {
  period_days: number | null
  period_start: string | null
  period_end: string | null
  total_trades: number
  closed_trades: number
  open_trades: number
  planned_trades: number
  skipped_trades: number
  wins: number
  losses: number
  breakeven: number
  win_rate: number
  // NEW — top-level CI decoration
  n?: number
  win_rate_ci?: [number, number] | null
  confidence?: string
  total_pnl: number
  avg_score: number
  avg_rr: number
  score_analysis: Record<string, { count: number; win_rate: number; avg_pnl: number } & CIDecoration>
  pair_breakdown: Record<string, { wins: number; losses: number; pnl: number; win_rate?: number } & CIDecoration>
  direction_stats: Record<string, { count: number; win_rate: number; pnl: number } & CIDecoration>
  plan_adherence: {
    rules_followed_pct: number
    rules_followed_win_rate: number
    rules_followed_win_rate_ci?: [number, number] | null
    rules_followed_confidence?: string
    rules_broken_win_rate: number
    rules_broken_win_rate_ci?: [number, number] | null
    rules_broken_confidence?: string
    skip_rate: number
    retroactive_rate: number
  }
  risk_discipline: {
    avg_risk_pct: number
    max_risk_pct: number
    over_threshold_count: number
    histogram: { bucket: string; count: number }[]
  }
  mistake_impact: ({ tag: string; count: number; win_rate: number; avg_pnl: number; total_pnl: number } & CIDecoration)[]
  emotion_impact: {
    entry: ({ tag: string; count: number; win_rate: number; avg_pnl: number; total_pnl: number } & CIDecoration)[]
    exit:  ({ tag: string; count: number; win_rate: number; avg_pnl: number; total_pnl: number } & CIDecoration)[]
  }
  timing_impact: Record<string, { count: number; win_rate: number } & CIDecoration>
  strategy_breakdown: ({
    strategy: string
    count: number
    win_rate: number
    expectancy: number
    frequency_warning?: string | null
  } & CIDecoration)[]
  edge_composite: {
    headline: string
    count: number
    win_rate?: number
    avg_rr?: number
    total_pnl?: number
    filter?: Record<string, unknown>
  }
  confluence_impact: ({ tag: string; count: number; win_rate: number; avg_pnl: number; total_pnl: number } & CIDecoration)[]
  mfe_mae_analysis: {
    count: number
    avg_mfe_all?: number | null
    avg_mfe_winners?: number | null
    avg_mfe_losers?: number | null
    avg_mae_winners?: number | null
    avg_mae_losers?: number | null
    max_mfe_all?: number | null
  }
  // NEW blocks
  sample_integrity?: SampleIntegrity
  streak_expectations?: StreakExpectations
  process_score?: ProcessScore
  regime_coverage?: RegimeCoverage
  confluence_filter: string[]
  trades: Trade[]
}
```

- [ ] **Step 12.2: Verify frontend type-checks**

```bash
cd frontend && npm run typecheck
```

Expected: zero errors.

- [ ] **Step 12.3: Commit**

```bash
git add frontend/src/api.ts
git commit -m "$(cat <<'EOF'
feat(types): extend AnalyticsData with CI decorations and four new blocks

Adds optional fields so the frontend can ship before the backend deploys
without breaking. CIDecoration mixin keeps the additive shape DRY across
existing rows.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Frontend confidence formatter

**Files:**
- Create: `frontend/src/lib/confidence.ts`

- [ ] **Step 13.1: Create the formatter file**

Create `frontend/src/lib/confidence.ts`:

```ts
import { CIDecoration } from '../api'

/**
 * Format a percentage with its 95% Wilson CI half-width and confidence
 * label. Example output: "61.1% +/-9 (n=18, Noisy)".
 */
export function formatRateWithCI(rate: number, deco: CIDecoration | undefined): string {
  if (!deco) return `${rate}%`
  const n = deco.n ?? 0
  const ci = deco.win_rate_ci
  const label = deco.confidence ?? confidenceLabel(n)
  if (!ci) return `${rate}% (n=${n})`
  const halfWidth = Math.round((ci[1] - ci[0]) / 2)
  return `${rate}% +/-${halfWidth} (n=${n}, ${label})`
}

export function confidenceLabel(n: number): string {
  if (n < 30) return 'Noise'
  if (n < 100) return 'Noisy'
  if (n < 500) return 'Reasonable'
  if (n < 1000) return 'Strong'
  return 'Conviction'
}

export function confidenceBadgeClass(label: string | undefined): string {
  switch (label) {
    case 'Noise':      return 'bg-red-100 text-red-700'
    case 'Noisy':      return 'bg-orange-100 text-orange-700'
    case 'Reasonable': return 'bg-yellow-100 text-yellow-700'
    case 'Strong':     return 'bg-green-100 text-green-700'
    case 'Conviction': return 'bg-emerald-100 text-emerald-700'
    default:           return 'bg-gray-100 text-gray-700'
  }
}
```

- [ ] **Step 13.2: Verify type-check**

```bash
cd frontend && npm run typecheck
```

Expected: zero errors.

- [ ] **Step 13.3: Commit**

```bash
git add frontend/src/lib/confidence.ts
git commit -m "$(cat <<'EOF'
feat(frontend): add confidence formatter helper

formatRateWithCI renders "61.1% +/-9 (n=18, Noisy)". confidenceBadgeClass
maps the label to a Tailwind utility class. Pure functions, no React.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: SampleIntegrityCard component

**Files:**
- Create: `frontend/src/components/SampleIntegrityCard.tsx`

- [ ] **Step 14.1: Create the component**

```tsx
import { SampleIntegrity } from '../api'
import { confidenceBadgeClass } from '../lib/confidence'

interface Props { data: SampleIntegrity | undefined }

export default function SampleIntegrityCard({ data }: Props) {
  if (!data) return null

  if (data.clean_count === 0) {
    return (
      <div className="card">
        <h3>⚖️ Sample Integrity</h3>
        <p className="muted">
          No clean trades yet — log a trade with rules_followed=yes,
          no mistake tags, on-time entry, planned in advance.
        </p>
      </div>
    )
  }

  const ciHalfWidth = (ci: [number, number] | null) =>
    ci ? Math.round((ci[1] - ci[0]) / 2) : 0

  return (
    <div className="card">
      <h3>⚖️ Sample Integrity</h3>
      <div className="muted small">{data.definition}</div>
      <div style={{ marginTop: 8 }}>
        Clean trades: <b>{data.clean_count}</b> of {data.total_count}{' '}
        ({data.clean_pct}%)
      </div>
      <table style={{ marginTop: 8, width: '100%' }}>
        <tbody>
          <tr>
            <td>Clean win rate</td>
            <td align="right">
              <b>{data.clean_win_rate}%</b>
              {data.clean_win_rate_ci && (
                <> +/-{ciHalfWidth(data.clean_win_rate_ci)}</>
              )}{' '}
              <span className={`badge ${confidenceBadgeClass(data.clean_confidence)}`}>
                n={data.clean_count}, {data.clean_confidence}
              </span>
            </td>
          </tr>
          <tr>
            <td>All trades WR</td>
            <td align="right">
              {data.all_win_rate}%
              {data.all_win_rate_ci && (
                <> +/-{ciHalfWidth(data.all_win_rate_ci)}</>
              )}{' '}
              <span className={`badge ${confidenceBadgeClass(data.all_confidence)}`}>
                n={data.total_count}, {data.all_confidence}
              </span>
            </td>
          </tr>
          <tr>
            <td>Discipline edge</td>
            <td align="right">
              <b style={{ color: data.integrity_delta >= 0 ? 'var(--green)' : 'var(--red)' }}>
                {data.integrity_delta >= 0 ? '+' : ''}{data.integrity_delta} pp
              </b>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 14.2: Verify type-check**

```bash
cd frontend && npm run typecheck
```

Expected: zero errors.

- [ ] **Step 14.3: Commit**

```bash
git add frontend/src/components/SampleIntegrityCard.tsx
git commit -m "$(cat <<'EOF'
feat(ui): add SampleIntegrityCard component

Displays clean-vs-all win rates with the discipline-edge delta. Empty state
prompts the user to log a clean trade when none exist yet.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: VarianceExpectationsCard component

**Files:**
- Create: `frontend/src/components/VarianceExpectationsCard.tsx`

- [ ] **Step 15.1: Create the component**

```tsx
import { StreakExpectations } from '../api'

interface Props { data: StreakExpectations | undefined }

export default function VarianceExpectationsCard({ data }: Props) {
  if (!data) return null
  if ('insufficient_data' in data) {
    return (
      <div className="card">
        <h3>📉 Variance Expectations</h3>
        <p className="muted">No closed trades yet.</p>
      </div>
    )
  }

  const lossPct = Math.round(data.p_loss * 100)
  return (
    <div className="card">
      <h3>📉 Variance Expectations</h3>
      <table style={{ width: '100%' }}>
        <tbody>
          <tr><td>Loss probability</td><td align="right"><b>{lossPct}%</b></td></tr>
          <tr><td>Expected max loss streak</td><td align="right"><b>{data.expected_max_loss_streak}</b></td></tr>
          <tr><td>Your actual max</td><td align="right"><b>{data.actual_max_loss_streak}</b></td></tr>
          <tr>
            <td>Current streak</td>
            <td align="right">
              <b>{data.current_streak.length}</b>{' '}
              {data.current_streak.kind !== 'none' ? data.current_streak.kind + (data.current_streak.length === 1 ? '' : 'es') : ''}
            </td>
          </tr>
        </tbody>
      </table>
      {data.five_loss_streak_every_n_trades !== null && (
        <p className="muted small" style={{ marginTop: 8 }}>
          At your loss rate, a 5-loss streak starts roughly once every{' '}
          <b>{data.five_loss_streak_every_n_trades}</b> trades.
          Don't quit at normal variance.
        </p>
      )}
      <p className="muted small" style={{ marginTop: 4, fontStyle: 'italic' }}>
        {data.fat_tail_caveat}
      </p>
    </div>
  )
}
```

- [ ] **Step 15.2: Verify type-check**

```bash
cd frontend && npm run typecheck
```

Expected: zero errors.

- [ ] **Step 15.3: Commit**

```bash
git add frontend/src/components/VarianceExpectationsCard.tsx
git commit -m "$(cat <<'EOF'
feat(ui): add VarianceExpectationsCard component

Renders Schilling's expected max loss streak vs. actual, current streak,
the "5-loss every N trades" headline, and the fat-tail caveat.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: ProcessScorecardCard component

**Files:**
- Create: `frontend/src/components/ProcessScorecardCard.tsx`

- [ ] **Step 16.1: Create the component**

```tsx
import { ProcessScore } from '../api'

interface Props { data: ProcessScore | undefined }

export default function ProcessScorecardCard({ data }: Props) {
  if (!data) return null
  return (
    <div className="card">
      <h3>🎯 Process Scorecard</h3>
      <p className="muted small">Judge the process, not individual outcomes.</p>
      <div style={{ marginTop: 12, fontSize: '1.5em' }}>
        Composite (strict): <b>{data.composite}</b>
        <span className="muted small" style={{ marginLeft: 8 }}>← optimize this</span>
      </div>
      <table style={{ width: '100%', marginTop: 12 }}>
        <tbody>
          <tr><td>Rules followed</td><td align="right">{data.rules_followed_pct}%</td></tr>
          <tr><td>No mistakes</td><td align="right">{data.no_mistakes_pct}%</td></tr>
          <tr><td>Clean entries (all 4 conditions)</td><td align="right">{data.clean_pct}%</td></tr>
        </tbody>
      </table>
      <p className="muted small" style={{ marginTop: 8 }}>
        Process bonus:{' '}
        <b style={{ color: data.process_winrate_minus_outcome_winrate >= 0 ? 'var(--green)' : 'var(--red)' }}>
          {data.process_winrate_minus_outcome_winrate >= 0 ? '+' : ''}
          {data.process_winrate_minus_outcome_winrate} pp
        </b>{' '}
        WR when sample is clean.
      </p>
    </div>
  )
}
```

- [ ] **Step 16.2: Verify type-check**

```bash
cd frontend && npm run typecheck
```

Expected: zero errors.

- [ ] **Step 16.3: Commit**

```bash
git add frontend/src/components/ProcessScorecardCard.tsx
git commit -m "$(cat <<'EOF'
feat(ui): add ProcessScorecardCard component

Headlines the strict composite (% of trades that satisfy all four
clean conditions). Diagnostic sub-scores below help the user see which
leg drags the composite down.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 17: DontBailBanner component

**Files:**
- Create: `frontend/src/components/DontBailBanner.tsx`

- [ ] **Step 17.1: Create the component**

```tsx
import { StreakExpectations } from '../api'

interface Props { data: StreakExpectations | undefined }

export default function DontBailBanner({ data }: Props) {
  if (!data || 'insufficient_data' in data) return null
  if (data.current_streak.kind !== 'loss') return null
  if (data.current_streak.length < 2) return null

  const lossPct = Math.round(data.p_loss * 100)
  const expected = data.expected_max_loss_streak
  const actual = data.current_streak.length

  if (actual <= expected) {
    return (
      <div className="banner banner-info" style={{
        padding: 12, borderRadius: 6, marginBottom: 12,
        background: '#e0f2fe', color: '#075985',
      }}>
        ℹ {actual} losses in a row is normal at your {lossPct}% loss rate.
        Expected max streak in this sample is {expected}. Don't tilt — keep the system.
      </div>
    )
  }

  return (
    <div className="banner banner-warn" style={{
      padding: 12, borderRadius: 6, marginBottom: 12,
      background: '#fef3c7', color: '#854d0e',
    }}>
      ⚠ {actual}-loss streak exceeds the {expected} expected for this sample.
      Could be variance, could be a regime shift. Review before next trade.
    </div>
  )
}
```

- [ ] **Step 17.2: Verify type-check**

```bash
cd frontend && npm run typecheck
```

Expected: zero errors.

- [ ] **Step 17.3: Commit**

```bash
git add frontend/src/components/DontBailBanner.tsx
git commit -m "$(cat <<'EOF'
feat(ui): add DontBailBanner component

Shows a calming "this is normal" banner when the current loss streak is
within the expected envelope, and a softer warning variant when it
exceeds the expected max.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 18: Mount cards + decorate existing rates in Review.tsx

**Files:**
- Modify: `frontend/src/components/Review.tsx`

- [ ] **Step 18.1: Add imports**

At the top of `frontend/src/components/Review.tsx`, alongside the existing imports, add:

```tsx
import SampleIntegrityCard from "./SampleIntegrityCard";
import VarianceExpectationsCard from "./VarianceExpectationsCard";
import ProcessScorecardCard from "./ProcessScorecardCard";
import DontBailBanner from "./DontBailBanner";
import { confidenceBadgeClass } from "../lib/confidence";
```

- [ ] **Step 18.2: Mount the banner + three cards near the top of the dashboard**

Locate the existing line that renders the headline:
```tsx
          Win rate {d.win_rate}% · Avg score {d.avg_score} · Avg R {d.avg_rr}
```

(Around line 185.) Just **above** the headline section's enclosing `<div>`, mount the banner. Then add the three cards in a grid below the headline. Concretely, find the headline block:

```tsx
        <div className="kpis">
          Win rate {d.win_rate}% · Avg score {d.avg_score} · Avg R {d.avg_rr}
        </div>
```

Replace with:

```tsx
        <DontBailBanner data={d.streak_expectations} />
        <div className="kpis">
          Win rate <b>{d.win_rate}%</b>
          {d.win_rate_ci && (
            <span className={`badge ${confidenceBadgeClass(d.confidence)}`} style={{ marginLeft: 6 }}>
              n={d.n ?? d.closed_trades}, {d.confidence ?? ''}
            </span>
          )}
          {' · '}Avg score {d.avg_score} · Avg R {d.avg_rr}
        </div>

        <div className="cards-grid" style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 12, marginTop: 12,
        }}>
          <SampleIntegrityCard data={d.sample_integrity} />
          <VarianceExpectationsCard data={d.streak_expectations} />
          <ProcessScorecardCard data={d.process_score} />
        </div>
```

- [ ] **Step 18.3: Add fat-tail footnote at the bottom of the dashboard**

At the end of the main analytics render block (just before the closing `</div>` of the dashboard but after the strategy_breakdown render), add:

```tsx
        {d.regime_coverage && (
          <div className="muted small" style={{ marginTop: 16, fontStyle: 'italic' }}>
            {d.regime_coverage.warning && <p>⚠ {d.regime_coverage.warning}</p>}
            <p>{d.regime_coverage.fat_tail_caveat}</p>
          </div>
        )}
```

- [ ] **Step 18.4: Verify type-check + dev server smoke**

```bash
cd frontend && npm run typecheck
```

Expected: zero errors.

```bash
cd frontend && npm run dev
```

Open `http://localhost:9000`, log in, navigate to the Review tab. Verify (manually):
- Headline win rate shows a confidence badge.
- The three new cards render in a grid.
- If you have a 2+ loss streak in the data, the banner shows.
- The fat-tail caveat shows at the bottom.

Stop the dev server when done.

- [ ] **Step 18.5: Commit**

```bash
git add frontend/src/components/Review.tsx
git commit -m "$(cat <<'EOF'
feat(ui): mount statistical-honesty layer on the Review tab

Adds the don't-bail banner above the headline, three new cards
(sample integrity, variance expectations, process scorecard) in a
responsive grid, a confidence badge on the headline win rate, and the
regime/fat-tail footnote at the bottom of the dashboard.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 19: End-to-end smoke

**Files:**
- (no file changes — verification only)

- [ ] **Step 19.1: Run the full backend test suite**

```bash
cd backend && pytest tests/ -v
```

Expected: all tests pass (existing + new).

- [ ] **Step 19.2: Run frontend type-check + lint**

```bash
cd frontend && npm run typecheck && npm run lint
```

Expected: zero errors.

- [ ] **Step 19.3: Manual smoke against deployed/local backend**

Start backend + frontend:

```bash
cd backend && uvicorn main:app --reload &
cd ../frontend && npm run dev
```

Walk through:
1. Plan a trade, enter it, close it (win or loss).
2. Open Review → verify headline shows confidence badge.
3. Verify Sample Integrity card shows clean count + delta.
4. Verify Variance Expectations card shows expected vs. actual streak.
5. Verify Process Scorecard composite is sensible (matches `sample_integrity.clean_pct`).
6. If you have ≥2 losses in a row, verify the don't-bail banner appears.
7. Verify regime warning + fat-tail caveat render at the bottom.

If anything looks wrong, file the bug and fix in a follow-up commit on the same branch.

- [ ] **Step 19.4: Final tag commit (no changes)**

```bash
git log --oneline -25
```

Confirm the chain of commits matches the task numbering. No new commit unless a fix landed in 19.3.

---

## Self-review checklist (run after writing this plan)

- [x] Every spec section in 2026-04-29-statistical-honesty-design.md is covered by a task above.
- [x] No "TBD" / "TODO" / placeholder strings.
- [x] Function names referenced across tasks (`_decorate`, `_sample_integrity`, `_streak_expectations`, `_process_score`, `_regime_coverage`, `wilson_ci`, `confidence_label`, `expected_max_loss_streak`, `current_streak`) are consistent.
- [x] Type names referenced across tasks (`CIDecoration`, `SampleIntegrity`, `StreakExpectations`, `ProcessScore`, `RegimeCoverage`) are consistent between Task 12 and tasks 14–18.
- [x] Each task ends with a commit step.
- [x] Each implementation step has the actual code, not a description of code.
