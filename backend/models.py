from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pair = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)
    timeframe = Column(String(10), nullable=False)
    strategy = Column(String(100), nullable=False, default="Zone Failure")
    setup_score = Column(Integer, nullable=False)
    verdict = Column(String(100), nullable=False)
    criteria_checked = Column(JSON, nullable=False)
    notes = Column(String(2000), default="")

    planned_entry = Column(Float, nullable=True)
    planned_stop = Column(Float, nullable=True)
    planned_target = Column(Float, nullable=True)
    planned_rr = Column(Float, nullable=True)

    status = Column(String(20), default="planned")
    retroactive = Column(Integer, default=0)
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    position_size = Column(Float, nullable=True)
    account_size = Column(Float, nullable=True)
    risk_dollars = Column(Float, nullable=True)
    risk_percent = Column(Float, nullable=True)
    entry_timing = Column(String(20), nullable=True)
    emotions_entry = Column(String(500), default=",")
    feelings_entry = Column(String(2000), default="")
    skip_reason = Column(String(500), default="")

    partial_exits = Column(String(2000), default="[]")
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    rr_achieved = Column(Float, nullable=True)
    rules_followed = Column(Integer, nullable=True)
    mistake_tags = Column(String(500), default=",")
    emotions_exit = Column(String(500), default=",")
    feelings_exit = Column(String(2000), default="")
    lessons = Column(String(2000), default="")
    chart_url = Column(String(500), default="")
    confluences = Column(String(2000), default=",")
    mfe_r = Column(Float, nullable=True)
    mae_r = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=True)
