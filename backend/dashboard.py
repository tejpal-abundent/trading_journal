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


def _compute_expectancy(closed_trades: list[dict]) -> dict:
    """Compute trading expectancy from closed trades with non-null pnl.

    Returns:
        {
            "value": float,        # EV per trade in dollars
            "win_rate": float,     # 0..1
            "loss_rate": float,    # 0..1
            "avg_win": float,      # avg pnl across winning trades
            "avg_loss": float,     # avg pnl across losing trades (positive number, the magnitude)
            "wins": int,
            "losses": int,
            "breakevens": int,
            "trades": int,         # total trades counted (wins+losses+breakevens)
            "last_trade_delta": float | None,  # how the most-recent closed trade changed EV
                                                # (EV_now − EV_before_last). null if <2 trades
        }
    """
    relevant = [t for t in closed_trades if t.get("pnl") is not None]
    if not relevant:
        return {
            "value": 0.0, "win_rate": 0.0, "loss_rate": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0,
            "wins": 0, "losses": 0, "breakevens": 0, "trades": 0,
            "last_trade_delta": None,
        }

    def _ev(rows: list[dict]) -> float:
        if not rows:
            return 0.0
        wins = [r["pnl"] for r in rows if r.get("status") == "win"]
        losses = [r["pnl"] for r in rows if r.get("status") == "loss"]
        n = len(rows)
        if n == 0:
            return 0.0
        win_rate = len(wins) / n
        loss_rate = len(losses) / n
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0  # magnitude
        return win_rate * avg_win - loss_rate * avg_loss

    # Sort by closed_at to identify "last trade"
    sorted_rel = sorted(relevant, key=lambda t: t.get("closed_at") or "")
    wins = [r["pnl"] for r in sorted_rel if r.get("status") == "win"]
    losses = [r["pnl"] for r in sorted_rel if r.get("status") == "loss"]
    breakevens = [r for r in sorted_rel if r.get("status") == "breakeven"]
    n = len(sorted_rel)
    win_rate = len(wins) / n if n else 0.0
    loss_rate = len(losses) / n if n else 0.0
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0

    ev_now = win_rate * avg_win - loss_rate * avg_loss
    ev_before = _ev(sorted_rel[:-1]) if n >= 2 else None
    last_delta = round(ev_now - ev_before, 2) if ev_before is not None else None

    return {
        "value": round(ev_now, 2),
        "win_rate": round(win_rate, 4),
        "loss_rate": round(loss_rate, 4),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "wins": len(wins), "losses": len(losses), "breakevens": len(breakevens),
        "trades": n,
        "last_trade_delta": last_delta,
    }


def _loss_discipline_weight(loss_magnitude: float, risk_dollars: float | None) -> float:
    """Weight a loss by how disciplined the exit was, expressed as a fraction
    of planned risk. Aligns with trading rule #1 (cut at 30%/50%/70% of planned
    risk before full stop).

        loss / planned_risk ≤ 30%        → 0.25  (nailed the early cut)
        loss / planned_risk in (30,50%]  → 0.5   (cut decently)
        loss / planned_risk in (50,70%]  → 0.75  (some discipline)
        loss / planned_risk > 70%        → 1.0   (let it run to/near full SL)

    If planned risk is missing or non-positive (legacy/retroactive trades),
    we can't classify the discipline, so treat as a full loss.
    """
    if not risk_dollars or risk_dollars <= 0:
        return 1.0
    ratio = loss_magnitude / risk_dollars
    if ratio <= 0.30:
        return 0.25
    if ratio <= 0.50:
        return 0.5
    if ratio <= 0.70:
        return 0.75
    return 1.0


def _compute_disciplined_expectancy(closed_trades: list[dict]) -> dict:
    """Discipline-weighted EV per trade. Same formula as true expectancy, but
    each losing trade is scaled by `_loss_discipline_weight` (0.25/0.5/0.75/1.0)
    based on the loss size as a fraction of planned risk.

    The headline answers a what-if: "what would my edge be if I always cut
    losses early?" The gap vs. true expectancy is the `discipline_tax` —
    the $/trade I leave on the table by letting losses run past 70% of risk.

    Returns the same shape as `_compute_expectancy` plus:
        "discipline_tax": float,   # disciplined_value − true_value (≥ 0)
    """
    relevant = [t for t in closed_trades if t.get("pnl") is not None]
    if not relevant:
        return {
            "value": 0.0, "win_rate": 0.0, "loss_rate": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0,
            "wins": 0, "losses": 0, "breakevens": 0, "trades": 0,
            "last_trade_delta": None, "discipline_tax": 0.0,
        }

    def _weighted_loss_contrib_per_trade(rows: list[dict]) -> float:
        """sum(|pnl_i| × weight_i) / N  — the disciplined loss term per trade."""
        n = len(rows)
        if n == 0:
            return 0.0
        total = 0.0
        for r in rows:
            if r.get("status") != "loss":
                continue
            mag = abs(r["pnl"])
            w = _loss_discipline_weight(mag, r.get("risk_dollars"))
            total += mag * w
        return total / n

    def _ev_disciplined(rows: list[dict]) -> float:
        n = len(rows)
        if n == 0:
            return 0.0
        wins = [r["pnl"] for r in rows if r.get("status") == "win"]
        avg_win = sum(wins) / len(wins) if wins else 0.0
        win_rate = len(wins) / n
        return win_rate * avg_win - _weighted_loss_contrib_per_trade(rows)

    sorted_rel = sorted(relevant, key=lambda t: t.get("closed_at") or "")
    wins = [r["pnl"] for r in sorted_rel if r.get("status") == "win"]
    losses = [r for r in sorted_rel if r.get("status") == "loss"]
    breakevens = [r for r in sorted_rel if r.get("status") == "breakeven"]
    n = len(sorted_rel)

    win_rate = len(wins) / n if n else 0.0
    loss_rate = len(losses) / n if n else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    # Disciplined avg_loss = mean of weighted loss magnitudes (for the breakdown line)
    weighted_loss_mags = [
        abs(r["pnl"]) * _loss_discipline_weight(abs(r["pnl"]), r.get("risk_dollars"))
        for r in losses
    ]
    avg_loss_disciplined = (sum(weighted_loss_mags) / len(weighted_loss_mags)) if weighted_loss_mags else 0.0

    ev_now = _ev_disciplined(sorted_rel)
    ev_before = _ev_disciplined(sorted_rel[:-1]) if n >= 2 else None
    last_delta = round(ev_now - ev_before, 2) if ev_before is not None else None

    # Tax = how much better the disciplined edge is vs the true edge
    true_avg_loss = abs(sum(r["pnl"] for r in losses) / len(losses)) if losses else 0.0
    true_ev = win_rate * avg_win - loss_rate * true_avg_loss
    discipline_tax = round(ev_now - true_ev, 2)

    return {
        "value": round(ev_now, 2),
        "win_rate": round(win_rate, 4),
        "loss_rate": round(loss_rate, 4),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss_disciplined, 2),
        "wins": len(wins), "losses": len(losses), "breakevens": len(breakevens),
        "trades": n,
        "last_trade_delta": last_delta,
        "discipline_tax": discipline_tax,
    }


def _compute_streak(closed_trades: list[dict]) -> dict:
    """Return current closed-trade streak by status. Breakeven breaks the streak."""
    sorted_rel = sorted(closed_trades, key=lambda t: t.get("closed_at") or "")
    if not sorted_rel:
        return {"kind": "none", "length": 0}
    last = sorted_rel[-1].get("status")
    if last not in ("win", "loss"):
        return {"kind": "none", "length": 0}
    length = 0
    for t in reversed(sorted_rel):
        if t.get("status") == last:
            length += 1
        else:
            break
    return {"kind": last, "length": length}


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
        "expectancy": _compute_expectancy(closed),
        "disciplined_expectancy": _compute_disciplined_expectancy(closed),
        "streak": _compute_streak(closed),
    }
