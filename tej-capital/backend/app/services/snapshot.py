"""Compute and freeze a metric snapshot with a ledger hash for point-in-time integrity."""
from __future__ import annotations
import hashlib
import math
import uuid
from datetime import date, datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import returns as R, metrics as M, stats as S, trades as T, verdict as V
from app.domain.nav import NavSnapshot
from app.domain.flows import CashFlow
from app.domain.trades import Trade
from app.domain.metrics import MetricSnapshot
from app.domain.settings import Settings


def _wrap(value, n: int) -> dict:
    return {"value": value, "n": int(n)}


def _json_safe(obj):
    """Recursively convert date/datetime/Decimal (and anything else the JSONB
    codec can't natively encode) into JSON-primitive types, so the metrics
    dict is safe both to persist in a JSONB column and to hand straight back
    as an HTTP response body."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        # NaN/Infinity are not valid JSON (RFC 8259) — Postgres' JSONB codec
        # rejects them outright. A NaN here means "no data for this slice"
        # (e.g. every winning trade is missing mae_r), which is exactly R3's
        # "never a zero, use null" rule applied to a non-scalar edge case.
        return None
    return obj


async def _load_series(db: AsyncSession, scope: str, account_id: uuid.UUID | None):
    """Returns (composite return series, trades DataFrame, count of nav rows)."""
    nav_q = select(NavSnapshot).where(NavSnapshot.superseded_by.is_(None))
    flow_q = select(CashFlow).where(CashFlow.superseded_by.is_(None))
    trade_q = select(Trade).where(Trade.superseded_by.is_(None))
    if scope == "per_account" and account_id:
        nav_q = nav_q.where(NavSnapshot.account_id == account_id)
        flow_q = flow_q.where(CashFlow.account_id == account_id)
        trade_q = trade_q.where(Trade.account_id == account_id)

    nav_rows = (await db.execute(nav_q.order_by(NavSnapshot.as_of_date))).scalars().all()
    flow_rows = (await db.execute(flow_q.order_by(CashFlow.as_of_date))).scalars().all()

    per_acct: dict = {}
    for r in nav_rows:
        per_acct.setdefault(r.account_id, {"nav": {}, "flows": {}})["nav"][r.as_of_date] = float(r.closing_equity)
    for f in flow_rows:
        per_acct.setdefault(f.account_id, {"nav": {}, "flows": {}})["flows"][f.as_of_date] = float(f.amount)

    accounts = {
        aid: (pd.Series(d["nav"]).sort_index(), pd.Series(d["flows"]).sort_index() if d["flows"] else pd.Series(dtype="float64"))
        for aid, d in per_acct.items()
    }
    composite = R.composite_twr(accounts) if len(accounts) > 1 else (
        R.daily_twr(*next(iter(accounts.values()))) if accounts else pd.Series(dtype="float64")
    )

    trades_rows = (await db.execute(trade_q)).scalars().all()
    trades_df = pd.DataFrame([{
        "id": str(t.id),
        "setup": str(t.setup_id) if t.setup_id else None,
        "instrument": t.instrument,
        "session": t.session,
        "htf_aligned": t.htf_aligned,
        "r_multiple": t.r_multiple,
        "risk_amount": float(t.risk_amount) if t.risk_amount is not None else None,
        "gross_pnl": float(t.gross_pnl) if t.gross_pnl is not None else None,
        "costs": float(t.costs),
        "rule_compliant": t.rule_compliant,
        "closed_at": t.closed_at,
        "mae_r": float(t.mae_r) if t.mae_r is not None else None,
        "mfe_r": float(t.mfe_r) if t.mfe_r is not None else None,
    } for t in trades_rows])
    return composite, trades_df, len(nav_rows)


async def compute_tearsheet(db: AsyncSession, scope: str = "composite",
                             account_id: uuid.UUID | None = None) -> dict:
    settings = await db.get(Settings, 1)
    tdy = settings.trading_days_per_year if settings else 252
    rfr = float(settings.risk_free_rate) if settings else 0.04
    benchmark = float(settings.benchmark_sharpe) if settings else 0.0
    trials = int(settings.strategy_variants_tested) if settings else 1

    returns, trades, _nav_row_count = await _load_series(db, scope, account_id)
    n_days = len(returns)

    tearsheet = {
        "returns": {
            "cumulative_twr": _wrap(M.cumulative_twr(returns), n_days),
            "cagr": _wrap(M.cagr(returns, tdy), n_days),
            "annualised_return": _wrap(M.annualised_return(returns, tdy), n_days),
            "avg_daily_return": _wrap(M.avg_daily_return(returns), n_days),
            "pct_positive_days": _wrap(M.pct_positive_days(returns), n_days),
            "best_day": _wrap(M.best_day(returns), n_days),
            "worst_day": _wrap(M.worst_day(returns), n_days),
        },
        "risk": {
            "annualised_volatility": _wrap(M.annualised_volatility(returns, tdy), n_days),
            "downside_deviation": _wrap(M.downside_deviation(returns, 0.0, tdy), n_days),
            "max_drawdown": _wrap(M.max_drawdown(returns), n_days),
            "current_drawdown": _wrap(M.current_drawdown(returns), n_days),
            "longest_drawdown_days": _wrap(M.longest_drawdown_days(returns), n_days),
            "ulcer_index": _wrap(M.ulcer_index(returns), n_days),
            "var_95": _wrap(M.var_95(returns), n_days),
            "cvar_95": _wrap(M.cvar_95(returns), n_days),
            "skewness": _wrap(M.skewness(returns), n_days),
            "excess_kurtosis": _wrap(M.excess_kurtosis(returns), n_days),
            "top_5_drawdowns": M.top_n_drawdowns(returns, n=5),
        },
        "risk_adjusted": {
            "sharpe": _wrap(M.sharpe(returns, rfr, tdy), n_days),
            "sortino": _wrap(M.sortino(returns, 0.0, tdy), n_days),
            "calmar": _wrap(M.calmar(returns, tdy), n_days),
            "sterling": _wrap(M.sterling(returns, tdy), n_days),
            "burke": _wrap(M.burke(returns, tdy), n_days),
            "omega": _wrap(M.omega(returns), n_days),
            "gain_to_pain": _wrap(M.gain_to_pain(returns), n_days),
            "tail_ratio": _wrap(M.tail_ratio(returns), n_days),
            "ulcer_performance_index": _wrap(M.ulcer_performance_index(returns, rfr, tdy), n_days),
            "recovery_factor": _wrap(M.recovery_factor(returns), n_days),
        },
        "statistical_validity": {
            "sharpe_t_stat": _wrap(S.sharpe_t_stat(returns), n_days),
            "psr_vs_zero": _wrap(S.probabilistic_sharpe_ratio(returns, 0.0), n_days),
            "psr_vs_benchmark": _wrap(S.probabilistic_sharpe_ratio(returns, benchmark), n_days),
            "deflated_sharpe": _wrap(S.deflated_sharpe(returns, trials, benchmark), n_days),
            "sharpe_ci": S.sharpe_ci(returns),
        },
        "trades": {
            "expectancy_r": _wrap(T.expectancy_r(trades) if len(trades) else None, len(trades)),
            "payoff_ratio": _wrap(T.payoff_ratio(trades) if len(trades) else None, len(trades)),
            "profit_factor": _wrap(T.profit_factor(trades) if len(trades) else None, len(trades)),
            "top_3_concentration": T.top_n_concentration(trades, 3) if len(trades) else {},
            "compliance_gap": T.compliance_gap_significance(trades) if len(trades) else {},
            "streaks": T.streaks(trades) if len(trades) else {},
            "mae_mfe": T.mae_mfe_stats(trades) if len(trades) else {},
        },
        "verdict": V.verdict_band(returns, benchmark_sharpe=benchmark, trading_days_per_year=tdy),
    }
    return _json_safe(tearsheet)


def compute_ledger_hash(nav_rows, flow_rows, trade_rows) -> str:
    h = hashlib.sha256()
    for r in sorted(nav_rows, key=lambda x: (x.account_id, x.as_of_date, x.id)):
        h.update(f"nav|{r.id}|{r.entered_at.isoformat()}|".encode())
    for r in sorted(flow_rows, key=lambda x: (x.account_id, x.as_of_date, x.id)):
        h.update(f"flow|{r.id}|{r.entered_at.isoformat()}|".encode())
    for r in sorted(trade_rows, key=lambda x: (x.account_id, x.opened_at, x.id)):
        h.update(f"trade|{r.id}|{r.entered_at.isoformat()}|".encode())
    return h.hexdigest()


async def freeze_snapshot(db: AsyncSession, *, as_of_date: date, scope: str = "composite",
                          account_id: uuid.UUID | None = None) -> tuple[MetricSnapshot, bool]:
    """Returns (snapshot, was_created). Idempotent per (date, scope, account_id)."""
    existing = (await db.execute(
        select(MetricSnapshot).where(
            MetricSnapshot.as_of_date == as_of_date,
            MetricSnapshot.scope == scope,
            MetricSnapshot.account_id == account_id,
        )
    )).scalar_one_or_none()
    if existing:
        return existing, False

    metrics = await compute_tearsheet(db, scope, account_id)
    nav_rows = (await db.execute(select(NavSnapshot).where(NavSnapshot.superseded_by.is_(None)))).scalars().all()
    flow_rows = (await db.execute(select(CashFlow).where(CashFlow.superseded_by.is_(None)))).scalars().all()
    trade_rows = (await db.execute(select(Trade).where(Trade.superseded_by.is_(None)))).scalars().all()

    snap = MetricSnapshot(
        id=uuid.uuid4(),
        as_of_date=as_of_date,
        scope=scope,
        account_id=account_id,
        metrics=metrics,
        ledger_hash=compute_ledger_hash(nav_rows, flow_rows, trade_rows),
    )
    db.add(snap)
    await db.commit()
    await db.refresh(snap)
    return snap, True
