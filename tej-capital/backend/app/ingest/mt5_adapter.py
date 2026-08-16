from datetime import date
import pandas as pd
from app.api.errors import NotConfiguredError
from app.ingest.base import CanonicalTrade, CanonicalFlow
from app.config import get_settings


class Mt5Adapter:
    """BrokerAdapter for MetaTrader 5.

    Requires Windows runtime with MetaTrader5 python package.
    Credentials: TEJ_MT5_LOGIN, TEJ_MT5_PASSWORD, TEJ_MT5_SERVER
    """

    name = "mt5"

    def __init__(self):
        s = get_settings()
        if not s.mt5_login:
            raise NotConfiguredError(
                "mt5",
                "set TEJ_MT5_LOGIN + TEJ_MT5_PASSWORD + TEJ_MT5_SERVER; requires Windows VM with MetaTrader5 python package"
            )

    def fetch_equity(self, since: date) -> pd.Series:
        raise NotConfiguredError(
            "mt5",
            "MT5 execution requires Windows runtime"
        )

    def fetch_closed_trades(self, since: date) -> list[CanonicalTrade]:
        raise NotConfiguredError(
            "mt5",
            "set TEJ_MT5_LOGIN + TEJ_MT5_PASSWORD + TEJ_MT5_SERVER; requires Windows VM with MetaTrader5 python package"
        )

    def fetch_flows(self, since: date) -> list[CanonicalFlow]:
        raise NotConfiguredError(
            "mt5",
            "set TEJ_MT5_LOGIN + TEJ_MT5_PASSWORD + TEJ_MT5_SERVER; requires Windows VM with MetaTrader5 python package"
        )
