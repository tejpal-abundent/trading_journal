"""Pure statistical helpers for the analytics layer.

No I/O, no globals, no scipy dependency — closed-form Wilson interval
and Schilling expected-streak approximation are sufficient for the
sample sizes this journal sees.
"""
import math


def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% Wilson interval for a proportion.

    Returns (lo, hi) on the 0-100 scale, rounded to 1 decimal.
    Returns None if n == 0.
    """
    if n <= 0:
        return None
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lo = (centre - margin) / denom
    hi = (centre + margin) / denom
    return (round(lo * 100, 1), round(hi * 100, 1))


CONFIDENCE_THRESHOLDS = [
    (30,   "Noise"),       # under 30 trades = pure noise (per video)
    (100,  "Noisy"),
    (500,  "Reasonable"),
    (1000, "Strong"),
]


def confidence_label(n: int) -> str:
    for threshold, label in CONFIDENCE_THRESHOLDS:
        if n < threshold:
            return label
    return "Conviction"
