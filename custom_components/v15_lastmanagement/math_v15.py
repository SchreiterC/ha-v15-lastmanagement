"""Pure functions: V15 never substitutes for a certified utility meter."""
from datetime import datetime
import math


def quarter_start(now: datetime) -> datetime:
    """Align to quarter hours in the datetime's timezone."""
    return now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)


def calculate(energy_wh: float, elapsed_s: float, import_w: float, limit_kw: float, reserve_kw: float) -> dict:
    """Assume the current import power remains unchanged to the slot end.

    Integration uses positive import only; exported power never cancels import.
    This is an intentionally conservative simplification, not billing precision.
    """
    values = (energy_wh, elapsed_s, import_w, limit_kw, reserve_kw)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("non-finite input")
    if energy_wh < 0 or limit_kw <= 0 or reserve_kw < 0 or reserve_kw >= limit_kw:
        raise ValueError("invalid energy or limits")
    elapsed_s = max(0.0, min(900.0, elapsed_s))
    import_w = max(0.0, import_w)
    allowed_wh = (limit_kw - reserve_kw) * 250.0
    remaining_s = max(0.0, 900.0 - elapsed_s)
    projected_wh = energy_wh + import_w * remaining_s / 3600.0
    measured_kw = (energy_wh * 3.6 / elapsed_s) if elapsed_s > 0 else 0.0
    projected_kw = projected_wh / 250.0
    # Raw headroom can become arbitrarily large as the remaining time tends
    # to zero. That is mathematical catch-up power, NOT a usable load target.
    # Never advise a controller to exceed the configured target (net of reserve).
    theoretical_budget_kw = (max(0.0, (allowed_wh - energy_wh) * 3.6 / remaining_s)
                             if remaining_s > 0 else 0.0)
    budget_kw = min(limit_kw - reserve_kw, theoretical_budget_kw)
    return {
        "measured_kw": round(measured_kw, 3),
        "projected_kw": round(projected_kw, 3),
        "budget_kw": round(budget_kw, 3),
        "at_risk": projected_wh > allowed_wh,
    }
