from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime, timedelta
from database import get_db, init_db
from models import Trade

app = FastAPI(title="Trading Journal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()


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


class TradeOut(BaseModel):
    id: int
    pair: str
    direction: str
    timeframe: str
    setup_score: int
    verdict: str
    criteria_checked: list[str]
    notes: str
    status: str
    entry_price: Optional[float]
    exit_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    pnl: Optional[float]
    pnl_percent: Optional[float]
    rr_achieved: Optional[float]
    lessons: Optional[str]
    created_at: datetime
    closed_at: Optional[datetime]

    class Config:
        from_attributes = True


# --- Routes ---

@app.post("/api/trades", response_model=TradeOut)
async def create_trade(trade: TradeCreate, db: AsyncSession = Depends(get_db)):
    db_trade = Trade(**trade.model_dump())
    db.add(db_trade)
    await db.commit()
    await db.refresh(db_trade)
    return db_trade


@app.get("/api/trades", response_model=list[TradeOut])
async def list_trades(
    status: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(Trade).order_by(Trade.created_at.desc()).limit(limit)
    if status:
        q = q.where(Trade.status == status)
    result = await db.execute(q)
    return result.scalars().all()


@app.get("/api/trades/{trade_id}", response_model=TradeOut)
async def get_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(404, "Trade not found")
    return trade


@app.patch("/api/trades/{trade_id}", response_model=TradeOut)
async def update_trade(trade_id: int, data: TradeUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(404, "Trade not found")

    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] in ("win", "loss", "breakeven"):
        trade.closed_at = datetime.utcnow()

    for k, v in update_data.items():
        setattr(trade, k, v)

    await db.commit()
    await db.refresh(trade)
    return trade


@app.delete("/api/trades/{trade_id}")
async def delete_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(404, "Trade not found")
    await db.delete(trade)
    await db.commit()
    return {"ok": True}


@app.get("/api/analytics")
async def get_analytics(days: int = 14, db: AsyncSession = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=days)
    q = select(Trade).where(Trade.created_at >= cutoff).order_by(Trade.created_at.desc())
    result = await db.execute(q)
    trades = result.scalars().all()

    closed = [t for t in trades if t.status in ("win", "loss", "breakeven")]
    wins = [t for t in closed if t.status == "win"]
    losses = [t for t in closed if t.status == "loss"]

    total_pnl = sum(t.pnl or 0 for t in closed)
    avg_score = sum(t.setup_score for t in trades) / len(trades) if trades else 0
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    avg_rr = sum(t.rr_achieved or 0 for t in closed) / len(closed) if closed else 0

    # Score vs outcome correlation
    score_buckets = {"A (85-100)": [], "B (70-84)": [], "C (55-69)": [], "D (<55)": []}
    for t in closed:
        if t.setup_score >= 85:
            score_buckets["A (85-100)"].append(t)
        elif t.setup_score >= 70:
            score_buckets["B (70-84)"].append(t)
        elif t.setup_score >= 55:
            score_buckets["C (55-69)"].append(t)
        else:
            score_buckets["D (<55)"].append(t)

    score_analysis = {}
    for bucket, bucket_trades in score_buckets.items():
        if bucket_trades:
            bucket_wins = [t for t in bucket_trades if t.status == "win"]
            score_analysis[bucket] = {
                "count": len(bucket_trades),
                "win_rate": round(len(bucket_wins) / len(bucket_trades) * 100, 1),
                "avg_pnl": round(sum(t.pnl or 0 for t in bucket_trades) / len(bucket_trades), 2),
            }

    # Per-pair breakdown
    pairs = {}
    for t in closed:
        if t.pair not in pairs:
            pairs[t.pair] = {"wins": 0, "losses": 0, "pnl": 0}
        if t.status == "win":
            pairs[t.pair]["wins"] += 1
        elif t.status == "loss":
            pairs[t.pair]["losses"] += 1
        pairs[t.pair]["pnl"] += t.pnl or 0

    # Direction breakdown
    long_trades = [t for t in closed if t.direction == "LONG"]
    short_trades = [t for t in closed if t.direction == "SHORT"]
    direction_stats = {
        "LONG": {
            "count": len(long_trades),
            "win_rate": round(len([t for t in long_trades if t.status == "win"]) / len(long_trades) * 100, 1) if long_trades else 0,
            "pnl": round(sum(t.pnl or 0 for t in long_trades), 2),
        },
        "SHORT": {
            "count": len(short_trades),
            "win_rate": round(len([t for t in short_trades if t.status == "win"]) / len(short_trades) * 100, 1) if short_trades else 0,
            "pnl": round(sum(t.pnl or 0 for t in short_trades), 2),
        },
    }

    return {
        "period_days": days,
        "total_trades": len(trades),
        "closed_trades": len(closed),
        "open_trades": len([t for t in trades if t.status == "open"]),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "avg_score": round(avg_score, 1),
        "avg_rr": round(avg_rr, 2),
        "score_analysis": score_analysis,
        "pair_breakdown": pairs,
        "direction_stats": direction_stats,
        "trades": [TradeOut.model_validate(t) for t in trades],
    }
