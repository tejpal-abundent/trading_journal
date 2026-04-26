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

    def db_trades_between(start_iso: str, end_iso: str):
        return fetch_all(
            "SELECT * FROM trades WHERE created_at >= ? AND created_at <= ? ORDER BY created_at DESC",
            [start_iso, end_iso],
        )

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
            "confluences": t.confluences or ",",
            "mfe_r": t.mfe_r, "mae_r": t.mae_r,
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

    def db_trades_between(start_iso: str, end_iso: str):
        db = _get_db()
        trades = [_trade_to_dict(t) for t in db.execute(
            select(Trade).where(Trade.created_at >= start_iso, Trade.created_at <= end_iso)
                         .order_by(Trade.created_at.desc())
        ).scalars().all()]
        db.close()
        return trades

    from sqlalchemy import text as _text

    def _sa_list_strategies():
        with engine.connect() as conn:
            rows = conn.execute(_text("SELECT * FROM strategies ORDER BY id ASC")).mappings().all()
            return [dict(r) for r in rows]

    def _sa_create_strategy(data):
        criteria_json = json.dumps([c if isinstance(c, dict) else c.model_dump() for c in data["criteria"]])
        core_json = json.dumps(data["is_core_required"])
        with engine.begin() as conn:
            conn.execute(_text(
                "INSERT INTO strategies (name, criteria, is_core_required) VALUES (:n, :c, :ic)"
            ), {"n": data["name"], "c": criteria_json, "ic": core_json})
            r = conn.execute(_text("SELECT * FROM strategies WHERE name = :n"),
                             {"n": data["name"]}).mappings().first()
            return dict(r)

    def _sa_update_strategy(sid, payload):
        sets = ", ".join(f"{k} = :{k}" for k in payload.keys())
        params = {**payload, "id": sid}
        with engine.begin() as conn:
            conn.execute(_text(f"UPDATE strategies SET {sets} WHERE id = :id"), params)
            r = conn.execute(_text("SELECT * FROM strategies WHERE id = :id"),
                             {"id": sid}).mappings().first()
            return dict(r) if r else None

    def _sa_delete_strategy(sid):
        with engine.begin() as conn:
            r = conn.execute(_text("SELECT * FROM strategies WHERE id = :id"),
                             {"id": sid}).mappings().first()
            if not r:
                from fastapi import HTTPException
                raise HTTPException(404, "Strategy not found")
            in_use = conn.execute(_text("SELECT COUNT(*) AS c FROM trades WHERE strategy = :n"),
                                  {"n": r["name"]}).scalar()
            if int(in_use) > 0:
                from fastapi import HTTPException
                raise HTTPException(409, "Strategy is referenced by existing trades")
            conn.execute(_text("DELETE FROM strategies WHERE id = :id"), {"id": sid})


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
        "confluences": _tags("confluences"),
        "mfe_r": _f("mfe_r"), "mae_r": _f("mae_r"),
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
    confluences: list[str] = []


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
    mfe_r: Optional[float] = None
    mae_r: Optional[float] = None


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
    confluences: list[str] = []
    mfe_r: Optional[float] = None
    mae_r: Optional[float] = None


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
    confluences: Optional[list[str]] = None
    mfe_r: Optional[float] = None
    mae_r: Optional[float] = None


def _tags_to_db(tags: list[str]) -> str:
    """Encode a tag list as a comma-wrapped string. Empty list -> ','."""
    if not tags:
        return ","
    cleaned = [t.strip() for t in tags if t and t.strip()]
    return "," + ",".join(cleaned) + "," if cleaned else ","


class CriterionDef(BaseModel):
    id: str
    label: str
    points: int
    category: str = "Quality"
    description: str = ""


class StrategyCreate(BaseModel):
    name: str
    criteria: list[CriterionDef]
    is_core_required: list[str] = []


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    criteria: Optional[list[CriterionDef]] = None
    is_core_required: Optional[list[str]] = None


class AccountSnapshotCreate(BaseModel):
    balance: float
    note: str = ""


class ReviewCreate(BaseModel):
    period_type: str
    period_start: str
    period_end: str
    notes: str


def _parse_strategy(row):
    if not row:
        return None
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "criteria": json.loads(row["criteria"]) if isinstance(row.get("criteria"), str) else row.get("criteria") or [],
        "is_core_required": json.loads(row.get("is_core_required") or "[]") if isinstance(row.get("is_core_required"), str) else (row.get("is_core_required") or []),
        "created_at": row.get("created_at"),
    }


def _parse_snapshot(row):
    if not row:
        return None
    return {
        "id": int(row["id"]),
        "balance": float(row["balance"]),
        "recorded_at": row.get("recorded_at"),
        "note": row.get("note") or "",
    }


def _parse_review(row):
    if not row:
        return None
    return {
        "id": int(row["id"]),
        "period_type": row["period_type"],
        "period_start": row["period_start"],
        "period_end": row["period_end"],
        "notes": row["notes"],
        "stats_snapshot": json.loads(row["stats_snapshot"]) if isinstance(row.get("stats_snapshot"), str) else row.get("stats_snapshot"),
        "created_at": row.get("created_at"),
    }


# --- Routes ---

@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/api/trades")
def create_trade(trade: TradeCreatePlan):
    data = trade.model_dump()
    data["criteria_checked"] = json.dumps(data["criteria_checked"])
    data["confluences"] = _tags_to_db(data.get("confluences") or [])
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

        for key in ("emotions_entry", "emotions_exit", "mistake_tags", "confluences"):
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
        "mfe_r": data.mfe_r,
        "mae_r": data.mae_r,
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
        "confluences": _tags_to_db(trade.confluences or []),
        "mfe_r": trade.mfe_r, "mae_r": trade.mae_r,
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
def get_analytics(days: int | None = None,
                  start_from: Optional[str] = None,
                  end_to: Optional[str] = None,
                  confluences: Optional[str] = None):
    confluence_filter = [c.strip() for c in confluences.split(",") if c.strip()] if confluences else []
    return _compute_analytics_range(start_from, end_to, days, confluence_filter)


# --- Strategies ---

@app.get("/api/strategies")
def list_strategies():
    rows = fetch_all("SELECT * FROM strategies ORDER BY id ASC") if USE_TURSO else _sa_list_strategies()
    return [_parse_strategy(r) for r in rows]


@app.post("/api/strategies")
def create_strategy(data: StrategyCreate):
    if USE_TURSO:
        execute(
            "INSERT INTO strategies (name, criteria, is_core_required) VALUES (?, ?, ?)",
            [data.name, json.dumps([c.model_dump() for c in data.criteria]),
             json.dumps(data.is_core_required)],
        )
        row = fetch_one("SELECT * FROM strategies WHERE name = ?", [data.name])
    else:
        row = _sa_create_strategy(data.model_dump())
    return _parse_strategy(row)


@app.patch("/api/strategies/{strategy_id}")
def update_strategy(strategy_id: int, data: StrategyUpdate):
    payload = data.model_dump(exclude_unset=True)
    if "criteria" in payload:
        payload["criteria"] = json.dumps(payload["criteria"])
    if "is_core_required" in payload:
        payload["is_core_required"] = json.dumps(payload["is_core_required"])

    if not payload:
        raise HTTPException(400, "no fields to update")
    sets = ", ".join(f"{k} = ?" for k in payload.keys())
    if USE_TURSO:
        execute(f"UPDATE strategies SET {sets} WHERE id = ?", list(payload.values()) + [strategy_id])
        row = fetch_one("SELECT * FROM strategies WHERE id = ?", [strategy_id])
    else:
        row = _sa_update_strategy(strategy_id, payload)
    if not row:
        raise HTTPException(404, "Strategy not found")
    return _parse_strategy(row)


@app.delete("/api/strategies/{strategy_id}")
def delete_strategy(strategy_id: int):
    if USE_TURSO:
        row = fetch_one("SELECT name FROM strategies WHERE id = ?", [strategy_id])
        if not row:
            raise HTTPException(404, "Strategy not found")
        in_use = fetch_one("SELECT COUNT(*) AS c FROM trades WHERE strategy = ?", [row["name"]])
        if int(in_use["c"]) > 0:
            raise HTTPException(409, "Strategy is referenced by existing trades")
        execute("DELETE FROM strategies WHERE id = ?", [strategy_id])
    else:
        _sa_delete_strategy(strategy_id)
    return {"ok": True}


# --- Account snapshots ---

@app.get("/api/account-snapshots")
def list_snapshots():
    if USE_TURSO:
        rows = fetch_all("SELECT * FROM account_snapshots ORDER BY id DESC")
    else:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            rows = [dict(r) for r in conn.execute(_text("SELECT * FROM account_snapshots ORDER BY id DESC")).mappings()]
    return [_parse_snapshot(r) for r in rows]


@app.post("/api/account-snapshots")
def create_snapshot(data: AccountSnapshotCreate):
    if USE_TURSO:
        execute("INSERT INTO account_snapshots (balance, note) VALUES (?, ?)", [data.balance, data.note])
        row = fetch_one("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1")
    else:
        from sqlalchemy import text as _text
        with engine.begin() as conn:
            conn.execute(_text("INSERT INTO account_snapshots (balance, note) VALUES (:b, :n)"),
                         {"b": data.balance, "n": data.note})
            row = dict(conn.execute(_text("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1")).mappings().first())
    return _parse_snapshot(row)


@app.get("/api/account-snapshots/latest")
def latest_snapshot():
    if USE_TURSO:
        row = fetch_one("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1")
    else:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            r = conn.execute(_text("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1")).mappings().first()
            row = dict(r) if r else None
    if not row:
        return {"balance": None}
    return _parse_snapshot(row)


# --- Reviews ---

def _compute_analytics_range(start_from: Optional[str] = None,
                              end_to: Optional[str] = None,
                              days: Optional[int] = None,
                              confluence_filter: Optional[list[str]] = None) -> dict:
    from analytics import compute_analytics
    if start_from and end_to:
        rows = db_trades_between(start_from, end_to)
        period_start, period_end = start_from, end_to
        period_days = None
    else:
        d = days or 14
        cutoff = (datetime.utcnow() - timedelta(days=d)).isoformat()
        rows = db_trades_since(cutoff)
        period_start = cutoff
        period_end = datetime.utcnow().isoformat()
        period_days = d
    trades = [_parse_trade(r) for r in rows]
    if confluence_filter:
        trades = [t for t in trades
                  if all(c in (t.get("confluences") or []) for c in confluence_filter)]
    return compute_analytics(trades, days=period_days,
                              period_start=period_start, period_end=period_end,
                              confluence_filter=confluence_filter or [])


@app.get("/api/reviews")
def list_reviews():
    if USE_TURSO:
        rows = fetch_all("SELECT id, period_type, period_start, period_end, notes, created_at FROM review_notes ORDER BY id DESC")
    else:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            rows = [dict(r) for r in conn.execute(_text("SELECT id, period_type, period_start, period_end, notes, created_at FROM review_notes ORDER BY id DESC")).mappings()]
    return [{
        "id": int(r["id"]), "period_type": r["period_type"],
        "period_start": r["period_start"], "period_end": r["period_end"],
        "notes": r["notes"], "created_at": r.get("created_at"),
    } for r in rows]


@app.get("/api/reviews/{review_id}")
def get_review(review_id: int):
    if USE_TURSO:
        row = fetch_one("SELECT * FROM review_notes WHERE id = ?", [review_id])
    else:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            r = conn.execute(_text("SELECT * FROM review_notes WHERE id = :i"), {"i": review_id}).mappings().first()
            row = dict(r) if r else None
    if not row:
        raise HTTPException(404, "Review not found")
    return _parse_review(row)


@app.post("/api/reviews")
def create_review(data: ReviewCreate):
    snapshot = _compute_analytics_range(data.period_start, data.period_end)
    if USE_TURSO:
        execute(
            "INSERT INTO review_notes (period_type, period_start, period_end, notes, stats_snapshot) VALUES (?, ?, ?, ?, ?)",
            [data.period_type, data.period_start, data.period_end, data.notes, json.dumps(snapshot)],
        )
        row = fetch_one("SELECT * FROM review_notes ORDER BY id DESC LIMIT 1")
    else:
        from sqlalchemy import text as _text
        with engine.begin() as conn:
            conn.execute(_text("""
                INSERT INTO review_notes (period_type, period_start, period_end, notes, stats_snapshot)
                VALUES (:t, :s, :e, :n, :ss)
            """), {"t": data.period_type, "s": data.period_start, "e": data.period_end,
                   "n": data.notes, "ss": json.dumps(snapshot)})
            row = dict(conn.execute(_text("SELECT * FROM review_notes ORDER BY id DESC LIMIT 1")).mappings().first())
    return _parse_review(row)


@app.delete("/api/reviews/{review_id}")
def delete_review(review_id: int):
    if USE_TURSO:
        execute("DELETE FROM review_notes WHERE id = ?", [review_id])
    else:
        from sqlalchemy import text as _text
        with engine.begin() as conn:
            conn.execute(_text("DELETE FROM review_notes WHERE id = :i"), {"i": review_id})
    return {"ok": True}
