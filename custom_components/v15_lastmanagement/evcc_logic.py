"""Pure, conservative helpers for optional evcc charging-current management.

No I/O or Home Assistant imports: these rules can be tested independently.
"""
from dataclasses import dataclass
import math
import re

_AMP_RE = re.compile(r"^\s*(\d{1,2}(?:[.,]\d+)?)\s*(?:a|ampere|amps)?\s*$", re.I)


def parse_amperes(value):
    """Accept HA number state or common select labels such as '6' or '6 A'."""
    if isinstance(value, (float, int)):
        return float(value) if math.isfinite(float(value)) else None
    match = _AMP_RE.fullmatch(str(value or ""))
    if match is None:
        return None
    result = float(match.group(1).replace(",", "."))
    return result if math.isfinite(result) else None


def select_option_for_amperes(options, amperes):
    """Return exact HA select option, never guess an unsupported string."""
    for option in options or []:
        parsed = parse_amperes(option)
        if parsed is not None and abs(parsed - amperes) < 0.01:
            return option
    return None


@dataclass(frozen=True)
class ChargeBudget:
    base_import_w: float
    available_charge_w: float
    target_current_a: int | None
    min_charge_w: float


def charging_budget(*, grid_w, charging_w, budget_kw, phases, voltage,
                    minimum_a, maximum_a, margin_w):
    """Conservative EV charge cap based on current non-EV net consumption.

    The quarter-hour budget already includes the V15 safety reserve. The
    additional margin here covers measurement/actuation error. Negative base
    grid import (e.g. PV export) is allowed; it provides genuine headroom.
    """
    vals = (grid_w, charging_w, budget_kw, phases, voltage,
            minimum_a, maximum_a, margin_w)
    if not all(math.isfinite(float(x)) for x in vals):
        raise ValueError("Non-finite evcc input")
    if not (phases in (1, 3) and 200 <= voltage <= 250 and
            6 <= minimum_a <= maximum_a <= 32 and margin_w >= 0 and
            charging_w >= 0 and budget_kw >= 0):
        raise ValueError("Invalid evcc configuration or measurement")
    base_w = float(grid_w) - float(charging_w)
    available_w = max(0.0, budget_kw * 1000.0 - base_w - margin_w)
    min_w = phases * voltage * minimum_a
    max_amp = math.floor(available_w / (phases * voltage))
    target = None if max_amp < minimum_a else int(min(maximum_a, max_amp))
    return ChargeBudget(base_w, available_w, target, min_w)
