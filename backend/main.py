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
        execute(
            "INSERT INTO trades (pair, direction, timeframe, setup_score, verdict, criteria_checked, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [data["pair"], data["direction"], data["timeframe"], data["setup_score"], data["verdict"], json.dumps(data["criteria_checked"]), data.get("notes", "")]
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
            if v is not None:
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
            "setup_score": t.setup_score, "verdict": t.verdict,
            "criteria_checked": t.criteria_checked if isinstance(t.criteria_checked, list) else json.loads(t.criteria_checked or "[]"),
            "notes": t.notes or "", "status": t.status or "open",
            "entry_price": t.entry_price, "exit_price": t.exit_price,
            "stop_loss": t.stop_loss, "take_profit": t.take_profit,
            "pnl": t.pnl, "pnl_percent": t.pnl_percent, "rr_achieved": t.rr_achieved,
            "lessons": t.lessons or "",
            "created_at": str(t.created_at) if t.created_at else None,
            "closed_at": str(t.closed_at) if t.closed_at else None,
        }

    def db_create_trade(data: dict) -> dict:
        db = _get_db()
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
            if v is not None:
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
    """Normalize a trade row from Turso (strings) to proper types."""
    if not row:
        return row
    cc = row.get("criteria_checked", "[]")
    if isinstance(cc, str):
        try:
            cc = json.loads(cc)
        except:
            cc = []
    return {
        "id": int(row["id"]),
        "pair": row["pair"],
        "direction": row["direction"],
        "timeframe": row["timeframe"],
        "setup_score": int(row["setup_score"]),
        "verdict": row["verdict"],
        "criteria_checked": cc,
        "notes": row.get("notes") or "",
        "status": row.get("status") or "open",
        "entry_price": float(row["entry_price"]) if row.get("entry_price") else None,
        "exit_price": float(row["exit_price"]) if row.get("exit_price") else None,
        "stop_loss": float(row["stop_loss"]) if row.get("stop_loss") else None,
        "take_profit": float(row["take_profit"]) if row.get("take_profit") else None,
        "pnl": float(row["pnl"]) if row.get("pnl") else None,
        "pnl_percent": float(row["pnl_percent"]) if row.get("pnl_percent") else None,
        "rr_achieved": float(row["rr_achieved"]) if row.get("rr_achieved") else None,
        "lessons": row.get("lessons") or "",
        "created_at": row.get("created_at"),
        "closed_at": row.get("closed_at"),
    }


# --- Schemas ---

class TradeCreate(BaseModel):
    pair: str
    direction: str
    timeframe: str
    setup_score: int
    verdict: str
    criteria_checked: list[str]
    notes: str = ""


class TradeUpdate(BaseModel):
    status: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    rr_achieved: Optional[float] = None
    lessons: Optional[str] = None


# --- Routes ---

@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/api/trades")
def create_trade(trade: TradeCreate):
    row = db_create_trade(trade.model_dump())
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
    try:
        existing = db_get_trade(trade_id)
        if not existing:
            raise HTTPException(404, "Trade not found")

        update_data = data.model_dump(exclude_unset=True)
        if update_data.get("status") in ("win", "loss", "breakeven"):
            update_data["closed_at"] = datetime.utcnow().isoformat()

        row = db_update_trade(trade_id, update_data)
        return _parse_trade(row)
    except HTTPException:
        raise
    except Exception as e:
        print(f"UPDATE ERROR: {e}")
        traceback.print_exc()
        raise HTTPException(500, str(e))


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
