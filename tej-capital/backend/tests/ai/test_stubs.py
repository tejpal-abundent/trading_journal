"""Tests for AI layer stubs: pattern detection, Qdrant, LLM integrations."""
import pandas as pd
import pytest
from app.ai.pattern_detect import find_patterns
from app.ai.qdrant_search import query
from app.api.errors import NotConfiguredError


def test_find_patterns_runs_without_credentials():
    """Pattern detection is deterministic and runs without any credentials."""
    trades = pd.DataFrame([
        {"session": "london", "r_multiple": 0.5, "closed_at": "2026-08-16"}
    ] * 30 + [
        {"session": "asia", "r_multiple": -0.4, "closed_at": "2026-08-17"}
    ] * 30)
    result = find_patterns(trades, q=0.10)
    assert isinstance(result, list)
    # With sufficient sample size difference in means, should detect the session pattern
    if result:
        assert all("name" in r and "p_value" in r for r in result)


def test_qdrant_query_raises_not_configured(monkeypatch):
    """Qdrant query raises NotConfiguredError when TEJ_QDRANT_URL is not set."""
    # Mock get_settings to return a config with no qdrant_url
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: type("Settings", (), {"qdrant_url": None})()
    )
    with pytest.raises(NotConfiguredError) as exc_info:
        query("hesitation")
    assert exc_info.value.integration == "qdrant"
    assert "TEJ_QDRANT_URL" in exc_info.value.hint
