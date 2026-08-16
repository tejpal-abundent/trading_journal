import pytest
from app.api.errors import NotConfiguredError
from app.ingest.mt5_adapter import Mt5Adapter
from app.ingest.bybit_adapter import BybitAdapter
from app.ingest.darwinex_adapter import DarwinexAdapter


def test_mt5_stub_raises_not_configured():
    """Mt5Adapter raises NotConfiguredError when TEJ_MT5_LOGIN is not set."""
    with pytest.raises(NotConfiguredError) as exc_info:
        Mt5Adapter()
    assert exc_info.value.integration == "mt5"
    assert "TEJ_MT5_LOGIN" in exc_info.value.hint


def test_bybit_stub_raises_not_configured():
    """BybitAdapter raises NotConfiguredError when TEJ_BYBIT_API_KEY is not set."""
    with pytest.raises(NotConfiguredError) as exc_info:
        BybitAdapter()
    assert exc_info.value.integration == "bybit"
    assert "TEJ_BYBIT_API_KEY" in exc_info.value.hint


def test_darwinex_stub_raises_not_configured():
    """DarwinexAdapter raises NotConfiguredError when TEJ_DARWINEX_API_KEY is not set."""
    with pytest.raises(NotConfiguredError) as exc_info:
        DarwinexAdapter()
    assert exc_info.value.integration == "darwinex"
    assert "TEJ_DARWINEX_API_KEY" in exc_info.value.hint
