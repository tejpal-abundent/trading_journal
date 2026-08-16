"""DDQ (Due Diligence Questionnaire) pack ZIP creation."""
import io
import zipfile
import pandas as pd


def build(
    tearsheet: dict,
    corrections: list[dict] | None = None,
    policy_doc: str | None = None,
    attribution: dict | None = None,
) -> bytes:
    """Build a DDQ pack ZIP containing performance and strategy documentation.

    Args:
        tearsheet: A tearsheet metrics dictionary from compute_tearsheet()
        corrections: List of correction records (audit trail)
        policy_doc: Strategy policy document text
        attribution: Attribution analysis dictionary

    Returns:
        ZIP file as bytes ready for download
    """
    corrections = corrections or []
    policy_doc = policy_doc or "No policy document provided."
    attribution = attribution or {}

    # Create in-memory ZIP file
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Strategy document
        strategy_md = _create_strategy_md(tearsheet)
        zf.writestr("strategy.md", strategy_md)

        # Policy document
        zf.writestr("policy.md", policy_doc)

        # Performance CSV
        performance_csv = _create_performance_csv(tearsheet)
        zf.writestr("performance.csv", performance_csv)

        # Attribution CSV
        attribution_csv = _create_attribution_csv(attribution)
        zf.writestr("attribution.csv", attribution_csv)

        # Corrections audit log CSV
        corrections_csv = _create_corrections_csv(corrections)
        zf.writestr("corrections.csv", corrections_csv)

        # README
        readme = _create_readme()
        zf.writestr("README.md", readme)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def _create_readme() -> str:
    """Create README for the DDQ pack."""
    return """# Due Diligence Questionnaire Pack

This archive contains trading performance documentation and strategy files.

## Contents

- **README.md** - This file
- **strategy.md** - Strategy overview and performance summary
- **policy.md** - Risk management and execution policy
- **performance.csv** - Detailed performance metrics
- **attribution.csv** - Attribution analysis by sector/instrument
- **corrections.csv** - Audit trail of data corrections

## Usage

Review each document in order:

1. Start with **strategy.md** for an overview
2. Read **policy.md** for risk framework
3. Analyze **performance.csv** for quantitative metrics
4. Review **attribution.csv** for performance drivers
5. Check **corrections.csv** for data integrity notes

---

Generated from TEJ Capital trading journal
"""


def _create_strategy_md(tearsheet: dict) -> str:
    """Create strategy summary markdown."""
    returns = tearsheet.get("returns", {})
    risk = tearsheet.get("risk", {})
    risk_adjusted = tearsheet.get("risk_adjusted", {})
    trades = tearsheet.get("trades", {})
    verdict = tearsheet.get("verdict", {})

    def fmt_pct(val, decimals=2):
        if val is None:
            return "N/A"
        return f"{val*100:.{decimals}f}%"

    def fmt_num(val, decimals=2):
        if val is None:
            return "N/A"
        return f"{val:.{decimals}f}"

    cumulative_twr = returns.get("cumulative_twr", {}).get("value")
    cagr = returns.get("cagr", {}).get("value")
    sharpe = risk_adjusted.get("sharpe", {}).get("value")
    max_dd = risk.get("max_drawdown", {}).get("value")
    vol = risk.get("annualised_volatility", {}).get("value")
    exp_r = trades.get("expectancy_r", {}).get("value")
    profit_factor = trades.get("profit_factor", {}).get("value")
    verdict_band = verdict.get("band", "neutral")

    return f"""# Strategy Performance Summary

## Verdict: {verdict_band.upper()}

## Key Metrics

### Returns
- **Cumulative TWR**: {fmt_pct(cumulative_twr)}
- **CAGR**: {fmt_pct(cagr)}
- **Best Day**: {fmt_pct(returns.get("best_day", {}).get("value"))}
- **Worst Day**: {fmt_pct(returns.get("worst_day", {}).get("value"))}

### Risk
- **Max Drawdown**: {fmt_pct(max_dd)}
- **Volatility**: {fmt_pct(vol)}
- **Sharpe Ratio**: {fmt_num(sharpe)}
- **Sortino Ratio**: {fmt_num(risk_adjusted.get("sortino", {}).get("value"))}
- **Calmar Ratio**: {fmt_num(risk_adjusted.get("calmar", {}).get("value"))}

### Trade Statistics
- **Total Trades**: {trades.get("expectancy_r", {}).get("n") or 0}
- **Expectancy (R)**: {fmt_num(exp_r)}
- **Profit Factor**: {fmt_num(profit_factor)}
- **Win Rate**: {fmt_pct(returns.get("pct_positive_days", {}).get("value"))}

## Performance Distribution

- **Sharpe CI (95%)**: {_format_sharpe_ci(risk_adjusted.get("sharpe_ci", {}))}
- **Deflated Sharpe**: {fmt_num(risk_adjusted.get("deflated_sharpe", {}).get("value"))}

## Risk Profile

### Tail Risk Metrics
- **VaR (95%)**: {fmt_pct(risk.get("var_95", {}).get("value"))}
- **CVaR (95%)**: {fmt_pct(risk.get("cvar_95", {}).get("value"))}
- **Skewness**: {fmt_num(risk.get("skewness", {}).get("value"))}
- **Excess Kurtosis**: {fmt_num(risk.get("excess_kurtosis", {}).get("value"))}

## Conclusion

The strategy demonstrates {verdict_band} performance characteristics based on quantitative analysis.

---

*Performance metrics computed from trading journal data*
"""


def _format_sharpe_ci(ci_data: dict) -> str:
    """Format Sharpe CI range."""
    lower = ci_data.get("lower")
    upper = ci_data.get("upper")
    if lower is None or upper is None:
        return "N/A"
    return f"[{lower:.2f}, {upper:.2f}]"


def _create_performance_csv(tearsheet: dict) -> str:
    """Create performance metrics CSV."""
    metrics = []

    returns = tearsheet.get("returns", {})
    risk = tearsheet.get("risk", {})
    risk_adjusted = tearsheet.get("risk_adjusted", {})
    trades = tearsheet.get("trades", {})

    for group_name, group_data in [
        ("Returns", returns),
        ("Risk", risk),
        ("Risk-Adjusted", risk_adjusted),
        ("Trades", trades),
    ]:
        for key, value in group_data.items():
            if isinstance(value, dict) and "value" in value:
                metrics.append({
                    "Category": group_name,
                    "Metric": key,
                    "Value": value.get("value"),
                    "N": value.get("n"),
                })

    df = pd.DataFrame(metrics)
    return df.to_csv(index=False)


def _create_attribution_csv(attribution: dict) -> str:
    """Create attribution analysis CSV."""
    if not attribution:
        return "Source,Contribution,Percentage\n# No attribution data\n"

    records = []
    for source, contrib in attribution.items():
        records.append({
            "Source": source,
            "Contribution": contrib.get("value", 0),
            "Percentage": contrib.get("pct", 0),
        })

    df = pd.DataFrame(records)
    return df.to_csv(index=False)


def _create_corrections_csv(corrections: list[dict]) -> str:
    """Create audit trail CSV of corrections."""
    if not corrections:
        return "Timestamp,Field,OldValue,NewValue,Reason\n# No corrections in audit trail\n"

    df = pd.DataFrame(corrections)
    return df.to_csv(index=False)
