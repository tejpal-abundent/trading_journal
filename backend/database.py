from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os

# Use Turso in production (set TURSO_DB_URL env var), SQLite locally
TURSO_URL = os.environ.get("TURSO_DB_URL")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

if TURSO_URL:
    DATABASE_URL = f"sqlite+{TURSO_URL}/?authToken={TURSO_TOKEN}&secure=true"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "trading_journal.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
