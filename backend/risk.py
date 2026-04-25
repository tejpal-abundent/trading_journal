"""Pure risk calculation. No DB, no I/O."""
from typing import Optional


def compute_risk(
    entry: Optional[float],
    stop: Optional[float],
    position_size: Optional[float],
    account_size: Optional[float],
) -> dict:
    """Returns {risk_dollars, risk_percent}, both None if any required input is missing."""
    if entry is None or stop is None or position_size is None or account_size is None:
        return {"risk_dollars": None, "risk_percent": None}

    risk_per_unit = abs(entry - stop)
    risk_dollars = round(risk_per_unit * position_size, 4)

    if account_size == 0:
        return {"risk_dollars": risk_dollars, "risk_percent": None}

    risk_percent = round((risk_dollars / account_size) * 100, 4)
    return {"risk_dollars": risk_dollars, "risk_percent": risk_percent}
