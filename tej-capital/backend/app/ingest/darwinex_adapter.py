from datetime import date
import pandas as pd
from app.api.errors import NotConfiguredError
from app.ingest.base import CanonicalTrade, CanonicalFlow
from app.config import get_settings


class DarwinexAdapter:
    """BrokerAdapter for Darwinex.

    Credentials: TEJ_DARWINEX_API_KEY
    """

    name = "darwinex"

    def __init__(self):
        s = get_settings()
        if not s.darwinex_api_key:
            raise NotConfiguredError(
                "darwinex",
                "set TEJ_DARWINEX_API_KEY; sign up at https://www.darwinex.com/darwinex-api"
            )

    def fetch_equity(self, since: date) -> pd.Series:
        raise NotConfiguredError(
            "darwinex",
            "set TEJ_DARWINEX_API_KEY; sign up at https://www.darwinex.com/darwinex-api"
        )

    def fetch_closed_trades(self, since: date) -> list[CanonicalTrade]:
        raise NotConfiguredError(
            "darwinex",
            "set TEJ_DARWINEX_API_KEY; sign up at https://www.darwinex.com/darwinex-api"
        )

    def fetch_flows(self, since: date) -> list[CanonicalFlow]:
        raise NotConfiguredError(
            "darwinex",
            "set TEJ_DARWINEX_API_KEY; sign up at https://www.darwinex.com/darwinex-api"
        )
