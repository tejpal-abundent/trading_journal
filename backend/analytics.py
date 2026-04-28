"""Analytics computations over a list of parsed trade dicts."""
from collections import defaultdict
from stats import wilson_ci, confidence_label, expected_max_loss_streak, current_streak

RISK_THRESHOLD_PCT = 2.0


def _decorate(wins: int, n: int) -> dict:
    """Returns the standard CI-decoration dict to merge into a row."""
    return {
        "n": n,
        "win_rate_ci": wilson_ci(wins, n),
        "confidence": confidence_label(n),
    }


def compute_analytics(trades: list[dict], days: int | None = None,
                      period_start: str | None = None, period_end: str | None = None,
                      confluence_filter: list[str] | None = None) -> dict:
    closed = [t for t in trades if t["status"] in ("win", "loss", "breakeven")]
    wins = [t for t in closed if t["status"] == "win"]
    losses = [t for t in closed if t["status"] == "loss"]
    breakevens = [t for t in closed if t["status"] == "breakeven"]
    skipped = [t for t in trades if t["status"] == "skipped"]
    entered_open = [t for t in trades if t["status"] == "entered"]
    planned = [t for t in trades if t["status"] == "planned"]

    total_pnl = sum(t["pnl"] or 0 for t in closed)
    avg_score = sum(t["setup_score"] for t in trades) / len(trades) if trades else 0
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    avg_rr = sum(t["rr_achieved"] or 0 for t in closed) / len(closed) if closed else 0

    n_closed = len(closed)
    return {
        "period_days": days,
        "period_start": period_start, "period_end": period_end,
        "confluence_filter": confluence_filter or [],
        "total_trades": len(trades),
        "closed_trades": len(closed),
        "open_trades": len(entered_open),
        "planned_trades": len(planned),
        "skipped_trades": len(skipped),
        "wins": len(wins), "losses": len(losses), "breakeven": len(breakevens),
        "win_rate": round(win_rate, 1),
        "n": n_closed,
        "win_rate_ci": wilson_ci(len(wins), n_closed),
        "confidence": confidence_label(n_closed),
        "total_pnl": round(total_pnl, 2),
        "avg_score": round(avg_score, 1),
        "avg_rr": round(avg_rr, 2),
        "score_analysis": _score_analysis(closed),
        "pair_breakdown": _pair_breakdown(closed),
        "direction_stats": _direction_stats(closed),
        "plan_adherence": _plan_adherence(trades),
        "risk_discipline": _risk_discipline(trades),
        "mistake_impact": _tag_impact([t for t in closed if not t["retroactive"]], "mistake_tags"),
        "emotion_impact": {
            "entry": _tag_impact(closed, "emotions_entry"),
            "exit":  _tag_impact(closed, "emotions_exit"),
        },
        "timing_impact": _timing_impact(closed),
        "strategy_breakdown": _strategy_breakdown(closed),
        "edge_composite": _edge_composite(closed),
        "confluence_impact": _tag_impact(closed, "confluences"),
        "mfe_mae_analysis": _mfe_mae_analysis(closed),
        "sample_integrity": _sample_integrity(closed),
        "trades": trades,
    }


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
                **_decorate(len(bw), len(bt)),
            }
    return out


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


def _direction_stats(closed):
    out = {}
    for d in ("LONG", "SHORT"):
        rows = [t for t in closed if t["direction"] == d]
        wins = [t for t in rows if t["status"] == "win"]
        out[d] = {
            "count": len(rows),
            "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
            "pnl": round(sum(t["pnl"] or 0 for t in rows), 2),
            **_decorate(len(wins), len(rows)),
        }
    return out


def _plan_adherence(trades):
    planned_lifecycle = [
        t for t in trades
        if not t["retroactive"]
        and t["status"] in ("entered", "win", "loss", "breakeven", "skipped")
    ]
    closed = [t for t in planned_lifecycle if t["status"] in ("win", "loss", "breakeven")]
    skipped = [t for t in planned_lifecycle if t["status"] == "skipped"]
    rules_known = [t for t in closed if t["rules_followed"] is not None]
    followed = [t for t in rules_known if t["rules_followed"]]
    broken = [t for t in rules_known if not t["rules_followed"]]
    fwins = [t for t in followed if t["status"] == "win"]
    bwins = [t for t in broken if t["status"] == "win"]
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


def _risk_discipline(trades):
    rows = [t for t in trades if t["risk_percent"] is not None]
    if not rows:
        return {"avg_risk_pct": 0, "max_risk_pct": 0, "over_threshold_count": 0, "histogram": []}
    avg = sum(t["risk_percent"] for t in rows) / len(rows)
    mx = max(t["risk_percent"] for t in rows)
    over = len([t for t in rows if t["risk_percent"] > RISK_THRESHOLD_PCT])

    bucket_defs = [("<0.5%", 0, 0.5), ("0.5-1%", 0.5, 1.0), ("1-2%", 1.0, 2.0),
                   ("2-3%", 2.0, 3.0), (">3%", 3.0, float("inf"))]
    hist = []
    for name, lo, hi in bucket_defs:
        count = len([t for t in rows if lo <= t["risk_percent"] < hi])
        hist.append({"bucket": name, "count": count})

    return {
        "avg_risk_pct": round(avg, 2),
        "max_risk_pct": round(mx, 2),
        "over_threshold_count": over,
        "histogram": hist,
    }


def _tag_impact(closed, key):
    by_tag = defaultdict(lambda: {"count": 0, "wins": 0, "pnl_sum": 0.0})
    for t in closed:
        tags = t.get(key) or []
        if not tags:
            if key == "mistake_tags":
                by_tag["(none)"]["count"] += 1
                if t["status"] == "win": by_tag["(none)"]["wins"] += 1
                by_tag["(none)"]["pnl_sum"] += t["pnl"] or 0
            continue
        for tag in tags:
            by_tag[tag]["count"] += 1
            if t["status"] == "win": by_tag[tag]["wins"] += 1
            by_tag[tag]["pnl_sum"] += t["pnl"] or 0
    rows = []
    for tag, agg in by_tag.items():
        rows.append({
            "tag": tag,
            "count": agg["count"],
            "win_rate": round(agg["wins"] / agg["count"] * 100, 1) if agg["count"] else 0,
            "avg_pnl": round(agg["pnl_sum"] / agg["count"], 2) if agg["count"] else 0,
            "total_pnl": round(agg["pnl_sum"], 2),
            **_decorate(agg["wins"], agg["count"]),
        })
    rows.sort(key=lambda r: abs(r["total_pnl"]), reverse=True)
    return rows


def _timing_impact(closed):
    out = {}
    for bucket in ("on_time", "late", "early"):
        rows = [t for t in closed if t["entry_timing"] == bucket]
        wins = [t for t in rows if t["status"] == "win"]
        out[bucket] = {
            "count": len(rows),
            "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
            **_decorate(len(wins), len(rows)),
        }
    return out


def _strategy_breakdown(closed):
    by_strat = defaultdict(list)
    for t in closed:
        by_strat[t["strategy"]].append(t)
    out = []
    for s, rows in by_strat.items():
        wins = [t for t in rows if t["status"] == "win"]
        out.append({
            "strategy": s,
            "count": len(rows),
            "win_rate": round(len(wins) / len(rows) * 100, 1) if rows else 0,
            "expectancy": round(sum(t["pnl"] or 0 for t in rows) / len(rows), 2) if rows else 0,
        })
    return out


def _score_bucket_label(score):
    if score >= 85: return "A+"
    if score >= 70: return "B"
    if score >= 55: return "C"
    return "D"


def _mfe_mae_analysis(closed):
    with_mfe = [t for t in closed if t.get("mfe_r") is not None]
    with_mae = [t for t in closed if t.get("mae_r") is not None]
    if not with_mfe and not with_mae:
        return {"count": 0}

    wins = [t for t in closed if t["status"] == "win"]
    losses = [t for t in closed if t["status"] == "loss"]

    def _avg(rows, key):
        vals = [t[key] for t in rows if t.get(key) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    return {
        "count": len(with_mfe) + len(with_mae),
        "avg_mfe_all": _avg(closed, "mfe_r"),
        "avg_mfe_winners": _avg(wins, "mfe_r"),
        "avg_mfe_losers":  _avg(losses, "mfe_r"),
        "avg_mae_winners": _avg(wins, "mae_r"),
        "avg_mae_losers":  _avg(losses, "mae_r"),
        "max_mfe_all": max((t["mfe_r"] for t in with_mfe), default=None),
    }


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


def _edge_composite(closed):
    eligible = [t for t in closed if not t["retroactive"]]
    by_slice = defaultdict(list)
    for t in eligible:
        if t["rules_followed"] is None: continue
        no_mistakes = not t["mistake_tags"]
        key = (t["strategy"], _score_bucket_label(t["setup_score"]),
               bool(t["rules_followed"]), no_mistakes)
        by_slice[key].append(t)

    candidates = [(k, v) for k, v in by_slice.items() if len(v) >= 5]
    if not candidates:
        return {"headline": "Not enough data yet", "count": 0}

    candidates.sort(key=lambda kv: sum(t["pnl"] or 0 for t in kv[1]), reverse=True)
    (strategy, score_bucket, rules_ok, no_mistakes), rows = candidates[0]
    wins = [t for t in rows if t["status"] == "win"]
    rr_vals = [t["rr_achieved"] for t in rows if t["rr_achieved"] is not None]
    headline_parts = [f"{strategy} {score_bucket} setups"]
    if rules_ok: headline_parts.append("plan followed")
    if no_mistakes: headline_parts.append("no mistakes")
    return {
        "headline": ", ".join(headline_parts),
        "filter": {
            "strategy": strategy, "score_bucket": score_bucket,
            "rules_followed": rules_ok, "no_mistakes": no_mistakes,
        },
        "count": len(rows),
        "win_rate": round(len(wins) / len(rows) * 100, 1),
        "avg_rr": round(sum(rr_vals) / len(rr_vals), 2) if rr_vals else 0,
        "total_pnl": round(sum(t["pnl"] or 0 for t in rows), 2),
    }
