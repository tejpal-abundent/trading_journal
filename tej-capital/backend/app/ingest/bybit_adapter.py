from datetime import date
import pandas as pd
from app.api.errors import NotConfiguredError
from app.ingest.base import CanonicalTrade, CanonicalFlow
from app.config import get_settings


class BybitAdapter:
    """BrokerAdapter for Bybit.

    Credentials: TEJ_BYBIT_API_KEY, TEJ_BYBIT_SECRET
    """

    name = "bybit"

    def __init__(self):
        s = get_settings()
        if not s.bybit_api_key:
            raise NotConfiguredError(
                "bybit",
                "set TEJ_BYBIT_API_KEY + TEJ_BYBIT_SECRET; read-only key + IP allowlist required"
            )

    def fetch_equity(self, since: date) -> pd.Series:
        raise NotConfiguredError(
            "bybit",
            "set TEJ_BYBIT_API_KEY + TEJ_BYBIT_SECRET; read-only key + IP allowlist required"
        )

    def fetch_closed_trades(self, since: date) -> list[CanonicalTrade]:
        raise NotConfiguredError(
            "bybit",
            "set TEJ_BYBIT_API_KEY + TEJ_BYBIT_SECRET; read-only key + IP allowlist required"
        )

    def fetch_flows(self, since: date) -> list[CanonicalFlow]:
        raise NotConfiguredError(
            "bybit",
            "set TEJ_BYBIT_API_KEY + TEJ_BYBIT_SECRET; read-only key + IP allowlist required"
        )
