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


def compute_rr(
    entry: Optional[float],
    exit_price: Optional[float],
    stop_loss: Optional[float],
    direction: Optional[str],
    status: Optional[str],
    trailed_stops: Optional[list],
) -> dict:
    """Compute classic R achieved + R locked at penultimate trail.

    Returns both as None if any required input is missing.
    Raises ValueError if entry_price == stop_loss (R distance would be zero).
    """
    if entry is None or exit_price is None or stop_loss is None or direction is None:
        return {"rr_achieved": None, "r_locked_at_penultimate_trail": None}

    if entry == stop_loss:
        raise ValueError("entry_price equals stop_loss; R distance is zero")

    dir_sign = 1 if direction.upper() == "LONG" else -1
    r_distance = abs(entry - stop_loss)

    rr_achieved = round((exit_price - entry) * dir_sign / r_distance, 2)

    r_locked = None
    if status == "win" and trailed_stops and len(trailed_stops) >= 2:
        penultimate = trailed_stops[-2].get("price")
        if penultimate is not None:
            r_locked = round((exit_price - penultimate) * dir_sign / r_distance, 2)

    return {"rr_achieved": rr_achieved, "r_locked_at_penultimate_trail": r_locked}
