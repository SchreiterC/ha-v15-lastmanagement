"""Pure planning functions for an optional photovoltaic dishwasher start.

Only forecast energy is used to rank candidate windows. Actual grid import and
V15 headroom are evaluated separately immediately before any appliance command.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
from typing import Mapping


@dataclass(frozen=True)
class PvWindow:
    start: datetime | None
    energy_wh: float
    valid_windows: int


def parse_clock(value: str) -> tuple[int, int]:
    """Parse a local clock time, not an absolute instant."""
    try:
        hh, mm = str(value).split(":")
        if len(hh) != 2 or len(mm) != 2:
            raise ValueError("use HH:MM")
        hour, minute = int(hh), int(mm)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("invalid time")
        return hour, minute
    except (ValueError, TypeError) as err:
        raise ValueError("Time must be HH:MM between 00:00 and 23:59") from err


def plan_window(
    values: Mapping[str, object] | None,
    now: datetime,
    earliest: str,
    deadline: str,
    duration_minutes: int,
) -> PvWindow:
    """Best full-duration 15-minute window today, using Wh per 15 minutes.

    Missing, nonfinite and negative entries invalidate the affected candidate.
    The current quarter may be chosen after its exact start time; deadlines
    are enforced by start_allowed(), including a short late-start grace.
    """
    if not isinstance(values, Mapping) or not 15 <= duration_minutes <= 720:
        return PvWindow(None, 0.0, 0)
    if duration_minutes % 15:
        return PvWindow(None, 0.0, 0)
    start_h, start_m = parse_clock(earliest)
    end_h, end_m = parse_clock(deadline)
    first = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    last = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    if first > last:
        return PvWindow(None, 0.0, 0)
    slot = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    slots = duration_minutes // 15
    best_start = None
    best_wh = -1.0
    count = 0
    candidate = first
    while candidate <= last:
        if candidate >= slot:
            total = 0.0
            valid = True
            for j in range(slots):
                key = (candidate + timedelta(minutes=15 * j)).isoformat()
                try:
                    wh = float(values[key])
                except (KeyError, TypeError, ValueError):
                    valid = False
                    break
                if not math.isfinite(wh) or wh < 0:
                    valid = False
                    break
                total += wh
            if valid:
                count += 1
                if total > best_wh:
                    best_wh = total
                    best_start = candidate
        candidate += timedelta(minutes=15)
    return PvWindow(best_start, max(0.0, best_wh), count)


def start_allowed(
    now: datetime,
    plan: PvWindow,
    earliest: str,
    deadline: str,
    minimum_wh: float,
) -> bool:
    """The forecast requirement is waived at the configured deadline.

    The 15-minute grace accommodates V15 measurement coverage and stable
    headroom checks. There is never a start on the next calendar day.
    """
    sh, sm = parse_clock(earliest)
    dh, dm = parse_clock(deadline)
    first = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
    last = now.replace(hour=dh, minute=dm, second=0, microsecond=0)
    if now < first or now >= last + timedelta(minutes=15):
        return False
    if now >= last:
        return True
    return (plan.start is not None and plan.start <= now
            and plan.energy_wh >= minimum_wh)
