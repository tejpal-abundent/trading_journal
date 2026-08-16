"""Behavioural pattern detection. Statistical tests run always; LLM only phrases the survivors."""
from __future__ import annotations
import pandas as pd
import numpy as np
from scipy import stats


def _slices(trades: pd.DataFrame) -> dict:
    """Return {slice_name: (pd.Series, pd.Series) of r_multiples}. Each slice is a binary split."""
    out: dict[str, tuple[pd.Series, pd.Series]] = {}
    if "closed_at" in trades.columns:
        dow = pd.to_datetime(trades["closed_at"]).dt.dayofweek
        out["monday_vs_rest"] = (trades[dow == 0]["r_multiple"].dropna(),
                                  trades[dow != 0]["r_multiple"].dropna())
        out["friday_vs_rest"] = (trades[dow == 4]["r_multiple"].dropna(),
                                  trades[dow != 4]["r_multiple"].dropna())
    if "session" in trades.columns:
        for sess in ("asia", "london", "new_york"):
            a = trades[trades["session"] == sess]["r_multiple"].dropna()
            b = trades[trades["session"] != sess]["r_multiple"].dropna()
            if len(a) >= 5 and len(b) >= 5:
                out[f"session_{sess}_vs_rest"] = (a, b)
    return out


def _bh_fdr(pvalues: list[float], q: float = 0.10) -> list[bool]:
    """Benjamini-Hochberg: return mask of hypotheses that pass at FDR q."""
    n = len(pvalues)
    order = np.argsort(pvalues)
    sorted_p = np.array(pvalues)[order]
    thresholds = (np.arange(1, n + 1) / n) * q
    passes = sorted_p <= thresholds
    if not passes.any():
        return [False] * n
    max_i = np.max(np.where(passes))
    mask = np.zeros(n, dtype=bool)
    mask[order[: max_i + 1]] = True
    return mask.tolist()


def find_patterns(trades: pd.DataFrame, q: float = 0.10) -> list[dict]:
    """Run deterministic statistical tests on binary slices of trades.

    Args:
        trades: DataFrame with columns like 'r_multiple', 'closed_at', 'session'
        q: FDR threshold (default 0.10, i.e., 10% false discovery rate allowed)

    Returns:
        List of dicts with keys: name, expectancy_a, expectancy_b, p_value
        Only returns slices that survive Benjamini-Hochberg FDR correction.
    """
    slices = _slices(trades)
    if not slices:
        return []
    names = list(slices.keys())
    results = []
    for name in names:
        a, b = slices[name]
        t = stats.ttest_ind(a, b, equal_var=False)
        results.append({"name": name, "expectancy_a": float(a.mean()),
                        "expectancy_b": float(b.mean()), "p_value": float(t.pvalue)})
    survivors_mask = _bh_fdr([r["p_value"] for r in results], q=q)
    return [r for r, keep in zip(results, survivors_mask) if keep]
