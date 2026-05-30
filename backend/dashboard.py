"""Pure dashboard aggregation. No DB, no I/O."""
from datetime import datetime, date, timedelta
from calendar import monthrange
from typing import Optional


CLOSED_STATUSES = ("win", "loss", "breakeven")


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    s2 = s.replace("Z", "").split(".")[0]
    try:
        return datetime.fromisoformat(s2).date()
    except Exception:
        return None


def _label_month(d: date) -> str:
    return d.strftime("%b %Y")


def _label_week(d: date) -> str:
    return f"Week of {d.strftime('%Y-%m-%d')}"


def _week_start(d: date) -> date:
    """Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


def _months_back(today: date, n: int) -> list[date]:
    """List the first-of-month dates for the past n months (oldest first), inclusive of current."""
    out = []
    y, m = today.year, today.month
    for _ in range(n):
        out.append(date(y, m, 1))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


def _days_in_month(d: date) -> int:
    return monthrange(d.year, d.month)[1]


def _split_trade_across_months(opened: date, closed: date, pnl: float) -> dict[tuple[int, int], float]:
    """Return {(year, month): pnl_share} for the trade, weighted by days held."""
    if opened > closed:
        opened, closed = closed, opened
    days_held = (closed - opened).days + 1
    out: dict[tuple[int, int], float] = {}
    cur = opened
    while cur <= closed:
        month_end = date(cur.year, cur.month, _days_in_month(cur))
        slice_end = min(month_end, closed)
        days_in_slice = (slice_end - cur).days + 1
        key = (cur.year, cur.month)
        out[key] = out.get(key, 0) + pnl * days_in_slice / days_held
        cur = slice_end + timedelta(days=1)
    return {k: round(v, 2) for k, v in out.items()}


def compute_dashboard(
    trades: list[dict],
    latest_snapshot_balance: Optional[float] = None,
    today: Optional[date] = None,
) -> dict:
    """Return the dashboard payload (see spec §4.1)."""
    if today is None:
        today = date.today()

    closed = [t for t in trades if t.get("status") in CLOSED_STATUSES]
    open_count = sum(1 for t in trades if t.get("status") == "entered")

    # --- monthly ---
    month_starts = _months_back(today, 12)
    monthly_close: dict[tuple[int, int], dict] = {
        (d.year, d.month): {"label": _label_month(d), "year": d.year, "month": d.month,
                            "pnl_close_date": 0, "pnl_split": 0,
                            "trades": 0, "wins": 0}
        for d in month_starts
    }
    for t in closed:
        cd = _parse_date(t.get("closed_at"))
        if cd is None:
            continue
        key = (cd.year, cd.month)
        if key in monthly_close:
            monthly_close[key]["pnl_close_date"] += t.get("pnl") or 0
            monthly_close[key]["trades"] += 1
            if t.get("status") == "win":
                monthly_close[key]["wins"] += 1
        # split attribution
        od = _parse_date(t.get("created_at"))
        if od is not None and (t.get("pnl") or 0) != 0:
            for (yr, mn), share in _split_trade_across_months(od, cd, t["pnl"]).items():
                if (yr, mn) in monthly_close:
                    monthly_close[(yr, mn)]["pnl_split"] += share

    monthly_list = []
    for d in month_starts:
        m = monthly_close[(d.year, d.month)]
        win_rate = round(m["wins"] / m["trades"], 2) if m["trades"] > 0 else 0
        monthly_list.append({
            "label": m["label"], "year": m["year"], "month": m["month"],
            "pnl_close_date": round(m["pnl_close_date"], 2),
            "pnl_split": round(m["pnl_split"], 2),
            "trades": m["trades"], "win_rate": win_rate,
        })

    # --- weekly (4 most recent ISO weeks) ---
    weekly_buckets: dict[date, dict] = {}
    for i in range(4):
        start = _week_start(today) - timedelta(weeks=i)
        iso_year, iso_week, _ = start.isocalendar()
        weekly_buckets[start] = {"label": _label_week(start), "iso_year": iso_year,
                                  "iso_week": iso_week, "pnl": 0, "trades": 0, "wins": 0}
    for t in closed:
        cd = _parse_date(t.get("closed_at"))
        if cd is None:
            continue
        ws = _week_start(cd)
        if ws in weekly_buckets:
            weekly_buckets[ws]["pnl"] += t.get("pnl") or 0
            weekly_buckets[ws]["trades"] += 1
            if t.get("status") == "win":
                weekly_buckets[ws]["wins"] += 1

    weekly_list = []
    for ws in sorted(weekly_buckets.keys()):
        w = weekly_buckets[ws]
        win_rate = round(w["wins"] / w["trades"], 2) if w["trades"] > 0 else 0
        weekly_list.append({
            "label": w["label"], "iso_year": w["iso_year"], "iso_week": w["iso_week"],
            "pnl": round(w["pnl"], 2), "trades": w["trades"], "win_rate": win_rate,
        })

    # --- daily_heatmap (trailing 90 days) ---
    heat: dict[str, dict] = {}
    for i in range(90):
        d = today - timedelta(days=89 - i)
        heat[d.isoformat()] = {"date": d.isoformat(), "pnl": 0, "trades": 0}
    for t in closed:
        cd = _parse_date(t.get("closed_at"))
        if cd is None:
            continue
        key = cd.isoformat()
        if key in heat:
            heat[key]["pnl"] += t.get("pnl") or 0
            heat[key]["trades"] += 1
    daily_heatmap = [{"date": k, "pnl": round(v["pnl"], 2), "trades": v["trades"]}
                     for k, v in sorted(heat.items())]

    # --- equity_curve (one point per closed trade, ordered) ---
    baseline = latest_snapshot_balance if latest_snapshot_balance is not None else 0
    closed_sorted = sorted(
        [t for t in closed if t.get("closed_at")],
        key=lambda t: t["closed_at"],
    )
    equity_curve = []
    running = baseline
    for t in closed_sorted:
        running += t.get("pnl") or 0
        equity_curve.append({
            "date": (_parse_date(t["closed_at"]) or date.today()).isoformat(),
            "cumulative_pnl": round(running, 2),
            "trade_id": t["id"],
        })

    # --- this_week / this_month / ytd ---
    this_week_start = _week_start(today)
    this_week = {"label": _label_week(this_week_start), "pnl": 0, "trades": 0, "wins": 0}
    this_month = {"label": _label_month(today), "pnl": 0, "trades": 0, "wins": 0}
    ytd = {"label": f"YTD {today.year}", "pnl": 0, "trades": 0, "wins": 0}

    for t in closed:
        cd = _parse_date(t.get("closed_at"))
        if cd is None:
            continue
        pnl = t.get("pnl") or 0
        is_win = t.get("status") == "win"
        if cd >= this_week_start and cd <= today:
            this_week["pnl"] += pnl; this_week["trades"] += 1; this_week["wins"] += int(is_win)
        if cd.year == today.year and cd.month == today.month:
            this_month["pnl"] += pnl; this_month["trades"] += 1; this_month["wins"] += int(is_win)
        if cd.year == today.year:
            ytd["pnl"] += pnl; ytd["trades"] += 1; ytd["wins"] += int(is_win)

    def _finalize(b):
        return {"label": b["label"], "pnl": round(b["pnl"], 2), "trades": b["trades"],
                "win_rate": round(b["wins"] / b["trades"], 2) if b["trades"] > 0 else 0}

    return {
        "this_week":  _finalize(this_week),
        "this_month": _finalize(this_month),
        "ytd":        _finalize(ytd),
        "open_trades": {"count": open_count},
        "monthly": monthly_list,
        "weekly": weekly_list,
        "daily_heatmap": daily_heatmap,
        "equity_curve": equity_curve,
    }
