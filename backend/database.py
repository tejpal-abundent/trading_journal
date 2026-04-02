from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os

TURSO_URL = os.environ.get("TURSO_DB_URL")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

if TURSO_URL:
    import libsql_client.dbapi2 as libsql_dbapi

    # Convert libsql:// to https:// for HTTP mode (avoids WebSocket issues)
    http_url = TURSO_URL.replace("libsql://", "https://")

    def creator():
        return libsql_dbapi.connect(http_url, auth_token=TURSO_TOKEN)

    engine = create_engine("sqlite://", creator=creator, echo=False)
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "trading_journal.db")
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

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
