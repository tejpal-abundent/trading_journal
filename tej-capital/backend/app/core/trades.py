"""Trade-level statistics. Pure. Consumes a trades DataFrame."""
from __future__ import annotations
import pandas as pd
from scipy import stats


def _rr(trades: pd.DataFrame) -> pd.Series:
    return trades["r_multiple"].dropna()


def expectancy_r(trades: pd.DataFrame) -> float | None:
    r = _rr(trades)
    if len(r) == 0:
        return None
    return float(r.mean())


def payoff_ratio(trades: pd.DataFrame) -> float | None:
    r = _rr(trades)
    wins = r[r > 0]
    losses = r[r < 0]
    if len(wins) == 0 or len(losses) == 0:
        return None
    return float(wins.mean() / abs(losses.mean()))


def profit_factor(trades: pd.DataFrame) -> float | None:
    r = _rr(trades)
    gains = r[r > 0].sum()
    losses = -r[r < 0].sum()
    if losses == 0:
        return None
    return float(gains / losses)


def top_n_concentration(trades: pd.DataFrame, n: int = 3) -> dict:
    r = _rr(trades)
    if len(r) == 0:
        return {"top_n_share": None, "top_n_ids": []}
    positive = r[r > 0]
    if positive.sum() == 0:
        return {"top_n_share": None, "top_n_ids": []}
    sorted_positive = positive.sort_values(ascending=False)
    top = sorted_positive.head(n)
    share = float(top.sum() / positive.sum())
    ids = trades.loc[top.index, "id"].tolist() if "id" in trades.columns else top.index.tolist()
    return {"top_n_share": share, "top_n_ids": ids}


def compliance_gap_significance(trades: pd.DataFrame) -> dict:
    if "rule_compliant" not in trades.columns:
        return {"compliant_expectancy": None, "noncompliant_expectancy": None, "p_value": None}
    compliant = trades[trades["rule_compliant"] == True]["r_multiple"].dropna()
    noncompliant = trades[trades["rule_compliant"] == False]["r_multiple"].dropna()
    if len(compliant) < 5 or len(noncompliant) < 5:
        return {
            "compliant_expectancy": float(compliant.mean()) if len(compliant) else None,
            "noncompliant_expectancy": float(noncompliant.mean()) if len(noncompliant) else None,
            "p_value": None,
        }
    t = stats.ttest_ind(compliant, noncompliant, equal_var=False)
    return {
        "compliant_expectancy": float(compliant.mean()),
        "noncompliant_expectancy": float(noncompliant.mean()),
        "p_value": float(t.pvalue),
    }


def streaks(trades: pd.DataFrame) -> dict:
    r = _rr(trades)
    longest_win = current_win = longest_loss = current_loss = 0
    for v in r:
        if v > 0:
            current_win += 1
            current_loss = 0
            longest_win = max(longest_win, current_win)
        elif v < 0:
            current_loss += 1
            current_win = 0
            longest_loss = max(longest_loss, current_loss)
        else:
            current_win = current_loss = 0
    return {"longest_win_streak": longest_win, "longest_loss_streak": longest_loss}


def mae_mfe_stats(trades: pd.DataFrame) -> dict:
    if "mae_r" not in trades.columns or "mfe_r" not in trades.columns:
        return {"avg_mae_r_winners": None, "avg_mfe_r_losers": None}
    winners = trades[trades["r_multiple"] > 0]
    losers = trades[trades["r_multiple"] < 0]
    mae_w = winners["mae_r"].dropna().mean() if len(winners) else None
    mfe_l = losers["mfe_r"].dropna().mean() if len(losers) else None
    return {
        "avg_mae_r_winners": float(mae_w) if mae_w is not None else None,
        "avg_mfe_r_losers": float(mfe_l) if mfe_l is not None else None,
    }
