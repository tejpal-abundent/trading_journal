from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import json
from datetime import datetime, timedelta

USE_TURSO = bool(os.environ.get("TURSO_DB_URL"))

app = FastAPI(title="Trading Journal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database layer ---

if USE_TURSO:
    from turso_db import execute, fetch_all, fetch_one, init_tables

    @app.on_event("startup")
    def startup():
        init_tables()

    def db_create_trade(data: dict) -> dict:
        cols = list(data.keys())
        placeholders = ",".join(["?"] * len(cols))
        execute(
            f"INSERT INTO trades ({','.join(cols)}) VALUES ({placeholders})",
            [data[c] for c in cols],
        )
        return fetch_one("SELECT * FROM trades ORDER BY id DESC LIMIT 1")

    def db_list_trades(status=None, limit=100):
        if status:
            return fetch_all("SELECT * FROM trades WHERE status = ? ORDER BY created_at DESC LIMIT ?", [status, limit])
        return fetch_all("SELECT * FROM trades ORDER BY created_at DESC LIMIT ?", [limit])

    def db_get_trade(trade_id: int):
        return fetch_one("SELECT * FROM trades WHERE id = ?", [trade_id])

    def db_update_trade(trade_id: int, data: dict):
        sets = []
        vals = []
        for k, v in data.items():
            sets.append(f"{k} = ?")
            vals.append(v)
        if not sets:
            return db_get_trade(trade_id)
        vals.append(trade_id)
        execute(f"UPDATE trades SET {', '.join(sets)} WHERE id = ?", vals)
        return fetch_one("SELECT * FROM trades WHERE id = ?", [trade_id])

    def db_delete_trade(trade_id: int):
        execute("DELETE FROM trades WHERE id = ?", [trade_id])

    def db_trades_since(cutoff: str):
        return fetch_all("SELECT * FROM trades WHERE created_at >= ? ORDER BY created_at DESC", [cutoff])

else:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import DeclarativeBase, sessionmaker
    from models import Trade

    DB_PATH = os.path.join(os.path.dirname(__file__), "trading_journal.db")
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    class Base(DeclarativeBase):
        pass

    @app.on_event("startup")
    def startup():
        from models import Base as ModelBase
        ModelBase.metadata.create_all(bind=engine)
        # Run shared migrations against raw connection
        from migrations import run_migrations
        from sqlalchemy import text

        def _exec(sql, args=None):
            with engine.begin() as conn:
                if args:
                    out = sql
                    params = {}
                    i = 0
                    while "?" in out:
                        out = out.replace("?", f":p{i}", 1)
                        params[f"p{i}"] = args[i]
                        i += 1
                    conn.execute(text(out), params)
                else:
                    conn.execute(text(sql))

        def _fetch_one(sql, args=None):
            with engine.connect() as conn:
                if args:
                    out = sql
                    params = {}
                    i = 0
                    while "?" in out:
                        out = out.replace("?", f":p{i}", 1)
                        params[f"p{i}"] = args[i]
                        i += 1
                    row = conn.execute(text(out), params).mappings().first()
                else:
                    row = conn.execute(text(sql)).mappings().first()
                return dict(row) if row else None

        run_migrations(_exec, _fetch_one)

    def _get_db():
        db = SessionLocal()
        try:
            return db
        except:
            db.close()
            raise

    def _trade_to_dict(t):
        return {
            "id": t.id, "pair": t.pair, "direction": t.direction, "timeframe": t.timeframe,
            "strategy": t.strategy or "Zone Failure",
            "setup_score": t.setup_score, "verdict": t.verdict,
            "criteria_checked": t.criteria_checked if isinstance(t.criteria_checked, list) else json.loads(t.criteria_checked or "[]"),
            "notes": t.notes or "",
            "planned_entry": t.planned_entry, "planned_stop": t.planned_stop,
            "planned_target": t.planned_target, "planned_rr": t.planned_rr,
            "status": t.status or "planned",
            "retroactive": int(t.retroactive or 0),
            "entry_price": t.entry_price, "exit_price": t.exit_price,
            "stop_loss": t.stop_loss, "take_profit": t.take_profit,
            "position_size": t.position_size, "account_size": t.account_size,
            "risk_dollars": t.risk_dollars, "risk_percent": t.risk_percent,
            "entry_timing": t.entry_timing,
            "emotions_entry": t.emotions_entry or ",",
            "feelings_entry": t.feelings_entry or "",
            "skip_reason": t.skip_reason or "",
            "partial_exits": t.partial_exits or "[]",
            "pnl": t.pnl, "pnl_percent": t.pnl_percent, "rr_achieved": t.rr_achieved,
            "rules_followed": t.rules_followed,
            "mistake_tags": t.mistake_tags or ",",
            "emotions_exit": t.emotions_exit or ",",
            "feelings_exit": t.feelings_exit or "",
            "lessons": t.lessons or "",
            "chart_url": t.chart_url or "",
            "created_at": str(t.created_at) if t.created_at else None,
            "closed_at": str(t.closed_at) if t.closed_at else None,
        }

    def db_create_trade(data: dict) -> dict:
        db = _get_db()
        if isinstance(data.get("criteria_checked"), str):
            try:
                data["criteria_checked"] = json.loads(data["criteria_checked"])
            except: pass
        t = Trade(**data)
        db.add(t); db.commit(); db.refresh(t)
        result = _trade_to_dict(t)
        db.close()
        return result

    def db_list_trades(status=None, limit=100):
        db = _get_db()
        q = select(Trade).order_by(Trade.created_at.desc()).limit(limit)
        if status: q = q.where(Trade.status == status)
        trades = [_trade_to_dict(t) for t in db.execute(q).scalars().all()]
        db.close()
        return trades

    def db_get_trade(trade_id: int):
        db = _get_db()
        t = db.execute(select(Trade).where(Trade.id == trade_id)).scalar_one_or_none()
        result = _trade_to_dict(t) if t else None
        db.close()
        return result

    def db_update_trade(trade_id: int, data: dict):
        db = _get_db()
        t = db.execute(select(Trade).where(Trade.id == trade_id)).scalar_one_or_none()
        if not t:
            db.close()
            return None
        for k, v in data.items():
            setattr(t, k, v)
        db.commit(); db.refresh(t)
        result = _trade_to_dict(t)
        db.close()
        return result

    def db_delete_trade(trade_id: int):
        db = _get_db()
        t = db.execute(select(Trade).where(Trade.id == trade_id)).scalar_one_or_none()
        if t: db.delete(t); db.commit()
        db.close()

    def db_trades_since(cutoff: str):
        db = _get_db()
        trades = [_trade_to_dict(t) for t in db.execute(
            select(Trade).where(Trade.created_at >= cutoff).order_by(Trade.created_at.desc())
        ).scalars().all()]
        db.close()
        return trades


# --- Helpers ---

def _parse_trade(row: dict) -> dict:
    if not row:
        return row
    cc = row.get("criteria_checked", "[]")
    if isinstance(cc, str):
        try: cc = json.loads(cc)
        except: cc = []

    pe = row.get("partial_exits", "[]")
    if isinstance(pe, str):
        try: pe = json.loads(pe)
        except: pe = []

    def _f(key):
        v = row.get(key)
        return float(v) if v not in (None, "") else None

    def _i(key):
        v = row.get(key)
        return int(v) if v not in (None, "") else None

    def _tags(key):
        raw = row.get(key) or ","
        return [t for t in raw.split(",") if t]

    return {
        "id": int(row["id"]),
        "pair": row["pair"], "direction": row["direction"], "timeframe": row["timeframe"],
        "strategy": row.get("strategy") or "Zone Failure",
        "setup_score": int(row["setup_score"]),
        "verdict": row["verdict"],
        "criteria_checked": cc,
        "notes": row.get("notes") or "",
        "planned_entry": _f("planned_entry"), "planned_stop": _f("planned_stop"),
        "planned_target": _f("planned_target"), "planned_rr": _f("planned_rr"),
        "status": row.get("status") or "planned",
        "retroactive": bool(_i("retroactive") or 0),
        "entry_price": _f("entry_price"), "exit_price": _f("exit_price"),
        "stop_loss": _f("stop_loss"), "take_profit": _f("take_profit"),
        "position_size": _f("position_size"), "account_size": _f("account_size"),
        "risk_dollars": _f("risk_dollars"), "risk_percent": _f("risk_percent"),
        "entry_timing": row.get("entry_timing"),
        "emotions_entry": _tags("emotions_entry"),
        "feelings_entry": row.get("feelings_entry") or "",
        "skip_reason": row.get("skip_reason") or "",
        "partial_exits": pe,
        "pnl": _f("pnl"), "pnl_percent": _f("pnl_percent"), "rr_achieved": _f("rr_achieved"),
        "rules_followed": (None if row.get("rules_followed") is None else bool(_i("rules_followed"))),
        "mistake_tags": _tags("mistake_tags"),
        "emotions_exit": _tags("emotions_exit"),
        "feelings_exit": row.get("feelings_exit") or "",
        "lessons": row.get("lessons") or "",
        "chart_url": row.get("chart_url") or "",
        "created_at": row.get("created_at"),
        "closed_at": row.get("closed_at"),
    }


# --- Schemas ---

class TradeCreatePlan(BaseModel):
    pair: str
    direction: str
    timeframe: str
    strategy: str = "Zone Failure"
    setup_score: int
    verdict: str
    criteria_checked: list[str]
    notes: str = ""
    planned_entry: Optional[float] = None
    planned_stop: Optional[float] = None
    planned_target: Optional[float] = None
    planned_rr: Optional[float] = None


class TradeEnter(BaseModel):
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    position_size: float
    account_size: float
    entry_timing: Optional[str] = None
    emotions_entry: list[str] = []
    feelings_entry: str = ""


class TradeSkip(BaseModel):
    skip_reason: str
    emotions_entry: list[str] = []


class TradeClose(BaseModel):
    status: str
    exit_price: float
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    rr_achieved: Optional[float] = None
    rules_followed: Optional[bool] = None
    mistake_tags: list[str] = []
    emotions_exit: list[str] = []
    feelings_exit: str = ""
    lessons: str = ""
    chart_url: str = ""
    partial_exits: list[dict] = []


class TradeRetroactive(BaseModel):
    pair: str
    direction: str
    timeframe: str
    strategy: str = "Zone Failure"
    setup_score: int
    verdict: str
    criteria_checked: list[str]
    notes: str = ""
    planned_entry: Optional[float] = None
    planned_stop: Optional[float] = None
    planned_target: Optional[float] = None
    planned_rr: Optional[float] = None
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    position_size: Optional[float] = None
    account_size: Optional[float] = None
    entry_timing: Optional[str] = None
    emotions_entry: list[str] = []
    feelings_entry: str = ""
    status: str
    exit_price: float
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    rr_achieved: Optional[float] = None
    rules_followed: Optional[bool] = None
    mistake_tags: list[str] = []
    emotions_exit: list[str] = []
    feelings_exit: str = ""
    lessons: str = ""
    chart_url: str = ""
    partial_exits: list[dict] = []


class TradeUpdate(BaseModel):
    notes: Optional[str] = None
    planned_entry: Optional[float] = None
    planned_stop: Optional[float] = None
    planned_target: Optional[float] = None
    planned_rr: Optional[float] = None
    status: Optional[str] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    position_size: Optional[float] = None
    account_size: Optional[float] = None
    entry_timing: Optional[str] = None
    emotions_entry: Optional[list[str]] = None
    feelings_entry: Optional[str] = None
    skip_reason: Optional[str] = None
    partial_exits: Optional[list[dict]] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    rr_achieved: Optional[float] = None
    rules_followed: Optional[bool] = None
    mistake_tags: Optional[list[str]] = None
    emotions_exit: Optional[list[str]] = None
    feelings_exit: Optional[str] = None
    lessons: Optional[str] = None
    chart_url: Optional[str] = None


def _tags_to_db(tags: list[str]) -> str:
    """Encode a tag list as a comma-wrapped string. Empty list -> ','."""
    if not tags:
        return ","
    cleaned = [t.strip() for t in tags if t and t.strip()]
    return "," + ",".join(cleaned) + "," if cleaned else ","


# --- Routes ---

@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/api/trades")
def create_trade(trade: TradeCreatePlan):
    data = trade.model_dump()
    data["criteria_checked"] = json.dumps(data["criteria_checked"])
    data["status"] = "planned"
    row = db_create_trade(data)
    return _parse_trade(row)


@app.get("/api/trades")
def list_trades(status: Optional[str] = None, limit: int = 100):
    rows = db_list_trades(status, limit)
    return [_parse_trade(r) for r in rows]


@app.get("/api/trades/{trade_id}")
def get_trade(trade_id: int):
    row = db_get_trade(trade_id)
    if not row:
        raise HTTPException(404, "Trade not found")
    return _parse_trade(row)


@app.patch("/api/trades/{trade_id}")
def update_trade(trade_id: int, data: TradeUpdate):
    import traceback
    from risk import compute_risk
    try:
        existing = db_get_trade(trade_id)
        if not existing:
            raise HTTPException(404, "Trade not found")

        update_data = data.model_dump(exclude_unset=True)

        for key in ("emotions_entry", "emotions_exit", "mistake_tags"):
            if key in update_data:
                update_data[key] = _tags_to_db(update_data[key] or [])
        if "partial_exits" in update_data:
            update_data["partial_exits"] = json.dumps(update_data["partial_exits"] or [])
        if "rules_followed" in update_data and update_data["rules_followed"] is not None:
            update_data["rules_followed"] = int(update_data["rules_followed"])

        if update_data.get("status") in ("win", "loss", "breakeven", "skipped"):
            update_data["closed_at"] = datetime.utcnow()

        risk_keys = {"entry_price", "stop_loss", "position_size", "account_size"}
        if risk_keys & set(update_data.keys()):
            merged = {**(existing or {}), **update_data}
            risk = compute_risk(merged.get("entry_price"), merged.get("stop_loss"),
                                merged.get("position_size"), merged.get("account_size"))
            update_data["risk_dollars"] = risk["risk_dollars"]
            update_data["risk_percent"] = risk["risk_percent"]

        row = db_update_trade(trade_id, update_data)
        return _parse_trade(row)
    except HTTPException:
        raise
    except Exception as e:
        print(f"UPDATE ERROR: {e}")
        traceback.print_exc()
        raise HTTPException(500, str(e))


@app.post("/api/trades/{trade_id}/enter")
def enter_trade(trade_id: int, data: TradeEnter):
    from risk import compute_risk
    existing = db_get_trade(trade_id)
    if not existing:
        raise HTTPException(404, "Trade not found")
    payload = data.model_dump()
    risk = compute_risk(payload["entry_price"], payload["stop_loss"],
                        payload["position_size"], payload["account_size"])
    update = {
        "status": "entered",
        "entry_price": payload["entry_price"],
        "stop_loss": payload["stop_loss"],
        "take_profit": payload.get("take_profit"),
        "position_size": payload["position_size"],
        "account_size": payload["account_size"],
        "risk_dollars": risk["risk_dollars"],
        "risk_percent": risk["risk_percent"],
        "entry_timing": payload.get("entry_timing"),
        "emotions_entry": _tags_to_db(payload.get("emotions_entry") or []),
        "feelings_entry": payload.get("feelings_entry") or "",
    }
    row = db_update_trade(trade_id, update)
    return _parse_trade(row)


@app.post("/api/trades/{trade_id}/skip")
def skip_trade(trade_id: int, data: TradeSkip):
    existing = db_get_trade(trade_id)
    if not existing:
        raise HTTPException(404, "Trade not found")
    update = {
        "status": "skipped",
        "skip_reason": data.skip_reason,
        "emotions_entry": _tags_to_db(data.emotions_entry or []),
        "closed_at": datetime.utcnow(),
    }
    row = db_update_trade(trade_id, update)
    return _parse_trade(row)


@app.post("/api/trades/{trade_id}/close")
def close_trade(trade_id: int, data: TradeClose):
    if data.status not in ("win", "loss", "breakeven"):
        raise HTTPException(400, "status must be win | loss | breakeven")
    existing = db_get_trade(trade_id)
    if not existing:
        raise HTTPException(404, "Trade not found")
    update = {
        "status": data.status,
        "exit_price": data.exit_price,
        "pnl": data.pnl,
        "pnl_percent": data.pnl_percent,
        "rr_achieved": data.rr_achieved,
        "rules_followed": (None if data.rules_followed is None else int(data.rules_followed)),
        "mistake_tags": _tags_to_db(data.mistake_tags or []),
        "emotions_exit": _tags_to_db(data.emotions_exit or []),
        "feelings_exit": data.feelings_exit or "",
        "lessons": data.lessons or "",
        "chart_url": data.chart_url or "",
        "partial_exits": json.dumps(data.partial_exits or []),
        "closed_at": datetime.utcnow(),
    }
    row = db_update_trade(trade_id, update)
    return _parse_trade(row)


@app.post("/api/trades/retroactive")
def create_retroactive_trade(trade: TradeRetroactive):
    from risk import compute_risk
    if trade.status not in ("win", "loss", "breakeven"):
        raise HTTPException(400, "status must be win | loss | breakeven")
    risk = compute_risk(trade.entry_price, trade.stop_loss,
                        trade.position_size, trade.account_size)
    data = {
        "pair": trade.pair, "direction": trade.direction, "timeframe": trade.timeframe,
        "strategy": trade.strategy, "setup_score": trade.setup_score, "verdict": trade.verdict,
        "criteria_checked": json.dumps(trade.criteria_checked),
        "notes": trade.notes,
        "planned_entry": trade.planned_entry, "planned_stop": trade.planned_stop,
        "planned_target": trade.planned_target, "planned_rr": trade.planned_rr,
        "status": trade.status, "retroactive": 1,
        "entry_price": trade.entry_price, "stop_loss": trade.stop_loss,
        "take_profit": trade.take_profit, "exit_price": trade.exit_price,
        "position_size": trade.position_size, "account_size": trade.account_size,
        "risk_dollars": risk["risk_dollars"], "risk_percent": risk["risk_percent"],
        "entry_timing": trade.entry_timing,
        "emotions_entry": _tags_to_db(trade.emotions_entry or []),
        "feelings_entry": trade.feelings_entry,
        "pnl": trade.pnl, "pnl_percent": trade.pnl_percent, "rr_achieved": trade.rr_achieved,
        "rules_followed": (None if trade.rules_followed is None else int(trade.rules_followed)),
        "mistake_tags": _tags_to_db(trade.mistake_tags or []),
        "emotions_exit": _tags_to_db(trade.emotions_exit or []),
        "feelings_exit": trade.feelings_exit,
        "lessons": trade.lessons, "chart_url": trade.chart_url,
        "partial_exits": json.dumps(trade.partial_exits or []),
        "closed_at": datetime.utcnow(),
    }
    row = db_create_trade(data)
    return _parse_trade(row)


@app.delete("/api/trades/{trade_id}")
def delete_trade(trade_id: int):
    existing = db_get_trade(trade_id)
    if not existing:
        raise HTTPException(404, "Trade not found")
    db_delete_trade(trade_id)
    return {"ok": True}


@app.get("/api/analytics")
def get_analytics(days: int = 14):
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    trades = [_parse_trade(r) for r in db_trades_since(cutoff)]

    closed = [t for t in trades if t["status"] in ("win", "loss", "breakeven")]
    wins = [t for t in closed if t["status"] == "win"]
    losses = [t for t in closed if t["status"] == "loss"]

    total_pnl = sum(t["pnl"] or 0 for t in closed)
    avg_score = sum(t["setup_score"] for t in trades) / len(trades) if trades else 0
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    avg_rr = sum(t["rr_achieved"] or 0 for t in closed) / len(closed) if closed else 0

    score_buckets = {"A (85-100)": [], "B (70-84)": [], "C (55-69)": [], "D (<55)": []}
    for t in closed:
        s = t["setup_score"]
        if s >= 85: score_buckets["A (85-100)"].append(t)
        elif s >= 70: score_buckets["B (70-84)"].append(t)
        elif s >= 55: score_buckets["C (55-69)"].append(t)
        else: score_buckets["D (<55)"].append(t)

    score_analysis = {}
    for bucket, bt in score_buckets.items():
        if bt:
            bw = [t for t in bt if t["status"] == "win"]
            score_analysis[bucket] = {
                "count": len(bt),
                "win_rate": round(len(bw) / len(bt) * 100, 1),
                "avg_pnl": round(sum(t["pnl"] or 0 for t in bt) / len(bt), 2),
            }

    pairs = {}
    for t in closed:
        p = t["pair"]
        if p not in pairs: pairs[p] = {"wins": 0, "losses": 0, "pnl": 0}
        if t["status"] == "win": pairs[p]["wins"] += 1
        elif t["status"] == "loss": pairs[p]["losses"] += 1
        pairs[p]["pnl"] += t["pnl"] or 0

    long_trades = [t for t in closed if t["direction"] == "LONG"]
    short_trades = [t for t in closed if t["direction"] == "SHORT"]
    direction_stats = {
        "LONG": {
            "count": len(long_trades),
            "win_rate": round(len([t for t in long_trades if t["status"] == "win"]) / len(long_trades) * 100, 1) if long_trades else 0,
            "pnl": round(sum(t["pnl"] or 0 for t in long_trades), 2),
        },
        "SHORT": {
            "count": len(short_trades),
            "win_rate": round(len([t for t in short_trades if t["status"] == "win"]) / len(short_trades) * 100, 1) if short_trades else 0,
            "pnl": round(sum(t["pnl"] or 0 for t in short_trades), 2),
        },
    }

    return {
        "period_days": days,
        "total_trades": len(trades),
        "closed_trades": len(closed),
        "open_trades": len([t for t in trades if t["status"] == "open"]),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "avg_score": round(avg_score, 1),
        "avg_rr": round(avg_rr, 2),
        "score_analysis": score_analysis,
        "pair_breakdown": pairs,
        "direction_stats": direction_stats,
        "trades": trades,
    }
