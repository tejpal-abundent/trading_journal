import numpy as np
import pandas as pd
from app.core.verdict import verdict_band


def test_verdict_not_yet_meaningful_on_short_sample():
    r = pd.Series(np.random.default_rng(0).normal(0.001, 0.01, size=50))
    v = verdict_band(r, benchmark_sharpe=1.0)
    assert v["level"] == "not_yet_meaningful"
    assert v["n_days"] == 50
    assert "roughly" in v["detail"].lower()


def test_verdict_ok_when_min_trl_met():
    rng = np.random.default_rng(1)
    r = pd.Series(rng.normal(0.002, 0.005, size=3000))  # very high sharpe, huge N
    v = verdict_band(r, benchmark_sharpe=0.0)
    assert v["level"] == "ok"
