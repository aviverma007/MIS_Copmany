"""Numeric helpers to keep NaN/inf out of JSON responses.

`pandas.Series.mean()` on an empty/all-NaN slice returns NaN, and
`NaN or 0` does NOT fall back to 0 (NaN is truthy in Python) -- it silently
returns NaN, which then crashes FastAPI's default JSON encoder. Use
`safe_float` everywhere a mean/ratio might be NaN.
"""
from __future__ import annotations

import math


def safe_float(value, default: float = 0.0) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(f) or math.isinf(f):
        return default
    return f
