"""Stateless, conservative conditions for restoring a V15-controlled load."""
from datetime import datetime
import math


def power_headroom_ok(grid_w: float, budget_kw: float | None,
                      load_w: float, margin_w: float) -> bool:
    """Only restore if anticipated grid import fits into the *capped* budget.

    A switch does not expose actual power draw. ``load_w`` must be a user-entered
    conservative estimate including startup demand. Export is never counted as
    additional headroom, since a battery or PV output can change at any time.
    """
    if budget_kw is None:
        return False
    values = (grid_w, budget_kw, load_w, margin_w)
    if not all(math.isfinite(x) for x in values):
        return False
    if budget_kw <= 0 or load_w <= 0 or margin_w < 0:
        return False
    return max(0, grid_w) + load_w + margin_w <= budget_kw * 1000


def periods_satisfied(now: datetime, off_at: datetime,
                      eligible_since: datetime | None,
                      min_off_s: int, stable_s: int) -> bool:
    """Require both a minimum off period and sustained power headroom."""
    if eligible_since is None:
        return False
    off_duration = (now - off_at).total_seconds()
    stable_duration = (now - eligible_since).total_seconds()
    return off_duration >= min_off_s and stable_duration >= stable_s
