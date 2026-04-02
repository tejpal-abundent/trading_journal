from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pair = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)  # SHORT or LONG
    timeframe = Column(String(10), nullable=False)  # 1H, 2H, 4H
    setup_score = Column(Integer, nullable=False)
    verdict = Column(String(100), nullable=False)
    criteria_checked = Column(JSON, nullable=False)  # list of checked criteria ids
    notes = Column(String(500), default="")

    # Result fields - filled after trade closes
    status = Column(String(20), default="open")  # open, win, loss, breakeven, skipped
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)  # profit/loss amount
    pnl_percent = Column(Float, nullable=True)  # profit/loss %
    rr_achieved = Column(Float, nullable=True)  # actual R:R achieved
    lessons = Column(String(1000), default="")  # post-trade notes

    created_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=True)
