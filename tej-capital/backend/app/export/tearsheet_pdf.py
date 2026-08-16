"""Tearsheet PDF and HTML rendering with Playwright support for PDF export."""


def render_html(tearsheet: dict) -> str:
    """Render a tearsheet as styled HTML using design tokens.

    Args:
        tearsheet: A tearsheet metrics dictionary from compute_tearsheet()

    Returns:
        A complete HTML document string with inline styles
    """
    # Extract key metrics from tearsheet
    returns = tearsheet.get("returns", {})
    risk = tearsheet.get("risk", {})
    risk_adjusted = tearsheet.get("risk_adjusted", {})
    verdict = tearsheet.get("verdict", {})

    cumulative_twr = returns.get("cumulative_twr", {}).get("value")
    cagr = returns.get("cagr", {}).get("value")
    sharpe = risk_adjusted.get("sharpe", {}).get("value")
    max_drawdown = risk.get("max_drawdown", {}).get("value")
    verdict_band = verdict.get("band", "neutral")

    # Design tokens (can be replaced with brand-specific values)
    colors = {
        "bg_primary": "#ffffff",
        "bg_secondary": "#f8f9fa",
        "text_primary": "#1a1a1a",
        "text_secondary": "#666666",
        "border": "#e0e0e0",
        "accent_positive": "#2ecc71",
        "accent_negative": "#e74c3c",
        "accent_neutral": "#3498db",
    }

    verdict_colors = {
        "excellent": colors["accent_positive"],
        "strong": colors["accent_positive"],
        "acceptable": colors["accent_neutral"],
        "weak": colors["accent_negative"],
        "poor": colors["accent_negative"],
        "neutral": colors["text_secondary"],
    }

    verdict_color = verdict_colors.get(verdict_band, colors["text_secondary"])

    # Format numbers
    def fmt_pct(val, decimals=2):
        if val is None:
            return "N/A"
        return f"{val*100:.{decimals}f}%"

    def fmt_num(val, decimals=2):
        if val is None:
            return "N/A"
        return f"{val:.{decimals}f}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Tearsheet</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: {colors['bg_primary']};
            color: {colors['text_primary']};
            padding: 40px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        header {{
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid {colors['border']};
        }}
        h1 {{
            font-size: 32px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: {colors['text_secondary']};
            font-size: 14px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 40px;
        }}
        @media (max-width: 600px) {{
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        .metric-card {{
            background-color: {colors['bg_secondary']};
            border: 1px solid {colors['border']};
            border-radius: 8px;
            padding: 20px;
        }}
        .metric-label {{
            color: {colors['text_secondary']};
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            display: block;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: 600;
        }}
        .metric-value.neutral {{
            color: {colors['text_primary']};
        }}
        .metric-value.positive {{
            color: {colors['accent_positive']};
        }}
        .metric-value.negative {{
            color: {colors['accent_negative']};
        }}
        .verdict {{
            background-color: {verdict_color};
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 40px;
        }}
        .verdict h2 {{
            font-size: 20px;
            margin-bottom: 8px;
            text-transform: capitalize;
        }}
        .detail-section {{
            margin-bottom: 40px;
        }}
        .detail-section h3 {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid {colors['border']};
        }}
        .detail-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }}
        @media (max-width: 600px) {{
            .detail-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        .detail-item {{
            padding: 10px;
            background-color: {colors['bg_secondary']};
            border-radius: 4px;
        }}
        .detail-label {{
            color: {colors['text_secondary']};
            font-size: 11px;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        .detail-value {{
            font-size: 14px;
            font-weight: 500;
        }}
        footer {{
            text-align: center;
            color: {colors['text_secondary']};
            font-size: 12px;
            padding-top: 20px;
            border-top: 1px solid {colors['border']};
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Trading Performance Tearsheet</h1>
            <p class="subtitle">Generated from live metrics</p>
        </header>

        <div class="verdict">
            <h2>{verdict_band}</h2>
            <p>Performance verdict band</p>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <span class="metric-label">Cumulative Return</span>
                <div class="metric-value {"positive" if (cumulative_twr or 0) >= 0 else "negative"}">
                    {fmt_pct(cumulative_twr)}
                </div>
            </div>
            <div class="metric-card">
                <span class="metric-label">CAGR</span>
                <div class="metric-value {"positive" if (cagr or 0) >= 0 else "negative"}">
                    {fmt_pct(cagr)}
                </div>
            </div>
            <div class="metric-card">
                <span class="metric-label">Sharpe Ratio</span>
                <div class="metric-value neutral">
                    {fmt_num(sharpe)}
                </div>
            </div>
            <div class="metric-card">
                <span class="metric-label">Max Drawdown</span>
                <div class="metric-value {"negative" if (max_drawdown or 0) < 0 else "neutral"}">
                    {fmt_pct(max_drawdown)}
                </div>
            </div>
        </div>

        <div class="detail-section">
            <h3>Returns Metrics</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Annualized Return</div>
                    <div class="detail-value">{fmt_pct(returns.get("annualised_return", {}).get("value"))}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Avg Daily Return</div>
                    <div class="detail-value">{fmt_pct(returns.get("avg_daily_return", {}).get("value"), 4)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Positive Days %</div>
                    <div class="detail-value">{fmt_pct(returns.get("pct_positive_days", {}).get("value"))}</div>
                </div>
            </div>
        </div>

        <div class="detail-section">
            <h3>Risk Metrics</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Volatility</div>
                    <div class="detail-value">{fmt_pct(risk.get("annualised_volatility", {}).get("value"))}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Downside Deviation</div>
                    <div class="detail-value">{fmt_pct(risk.get("downside_deviation", {}).get("value"))}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Longest DD Days</div>
                    <div class="detail-value">{risk.get("longest_drawdown_days", {}).get("value") or "N/A"}</div>
                </div>
            </div>
        </div>

        <div class="detail-section">
            <h3>Risk-Adjusted Metrics</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Sortino Ratio</div>
                    <div class="detail-value">{fmt_num(risk_adjusted.get("sortino", {}).get("value"))}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Calmar Ratio</div>
                    <div class="detail-value">{fmt_num(risk_adjusted.get("calmar", {}).get("value"))}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Recovery Factor</div>
                    <div class="detail-value">{fmt_num(risk_adjusted.get("recovery_factor", {}).get("value"))}</div>
                </div>
            </div>
        </div>

        <footer>
            <p>This tearsheet was automatically generated from your trading journal data.</p>
        </footer>
    </div>
</body>
</html>
"""
    return html


async def render_pdf(tearsheet: dict) -> bytes | None:
    """Render a tearsheet as a PDF using Playwright if available.

    Args:
        tearsheet: A tearsheet metrics dictionary from compute_tearsheet()

    Returns:
        PDF bytes if Playwright is installed and importable, else None
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None

    html_content = render_html(tearsheet)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(html_content)
            pdf_bytes = await page.pdf()
            await browser.close()
            return pdf_bytes
    except Exception:
        # If PDF rendering fails for any reason, return None
        return None
