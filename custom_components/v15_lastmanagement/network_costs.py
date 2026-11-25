"""Illustrative Austrian grid-capacity charges; no billing data is fetched.

The regional values are *DRAFT ONLY*: E-Control SNE-T-V 2027, consultation
version 29 October 2026, section 5(1), grid level 7. They MUST NOT be
presented as legally effective tariffs. Network areas are not identical to
federal states. The phased introduction date differs by network area.

Sources:
https://www.wko.at/oe/news/0339-hue-snt-v-2027-begutachtungsentwurf.pdf
https://www.ris.bka.gv.at/eli/bgbl/ii/2026/299/P6/NOR40281083
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math


DRAFT_DATE = "2026-10-29"
DRAFT_SOURCE = "E-Control SNE-T-V 2027 (§ 5 Abs. 1), Entwurf 29.10.2026"
# (Cents per kW per month for first 10 kW, cents for every further kW).
# Not the 2027 transition rates from § 5 Abs. 2.
DRAFT_2027_NE7 = {
    "Burgenland": (340, 510),
    "Kärnten": (351, 527),
    "Klagenfurt": (250, 375),
    "Niederösterreich": (261, 392),
    "Oberösterreich": (241, 362),
    "Linz": (257, 386),
    "Salzburg": (210, 315),
    "Steiermark": (321, 482),
    "Graz": (228, 342),
    "Tirol": (245, 368),
    "Innsbruck": (326, 489),
    "Vorarlberg": (200, 300),
    "Wien": (246, 369),
    "Kleinwalsertal": (583, 875),
}


def _decimal(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as err:
        raise ValueError("Not a numeric tariff or peak") from err
    if not number.is_finite() or number < 0:
        raise ValueError("Tariff and grid peaks must be finite and nonnegative")
    return number


def monthly_capacity_charge(peak_kw, first_tier_cents, higher_tier_cents,
                            minimum_kw=2.0):
    """Monthly EUR net, progressive split at 10 kW, half-up cents.

    Tariff applies to max(observed 15-min peak, applicable minimum). Grid
    level 7 normally has a 2 kW minimum under SNE-G-V § 6(3). Small
    connections, legacy agreements and the transition need separate review.
    """
    measured = _decimal(peak_kw)
    first = _decimal(first_tier_cents)
    higher = _decimal(higher_tier_cents)
    floor = _decimal(minimum_kw)
    billable = max(measured, floor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    first_kw = min(billable, Decimal("10"))
    additional = max(Decimal("0"), billable - Decimal("10"))
    cents = first_kw * first + additional * higher
    return float((cents / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def estimate_difference(peak_kw, target_kw, first_tier_cents, higher_tier_cents,
                        minimum_kw=2.0):
    """Hypothetical difference, NOT savings claim or refundable current charge."""
    peak = _decimal(peak_kw)
    target = _decimal(target_kw)
    actual = monthly_capacity_charge(peak, first_tier_cents, higher_tier_cents, minimum_kw)
    at_target = monthly_capacity_charge(min(peak, target), first_tier_cents,
                                        higher_tier_cents, minimum_kw)
    return max(0.0, round(actual - at_target, 2))


@dataclass
class MonthlyPeak:
    """Max of *fully observed* completed V15 15-minute grid-import periods."""

    month: str | None = None
    kw: float | None = None
    count: int = 0
    last_slot: str | None = None

    def ensure_month(self, local_dt):
        key = local_dt.strftime("%Y-%m")
        if self.month != key:
            self.month = key
            self.kw = None
            self.count = 0
            self.last_slot = None

    def restore(self, month, kw, count, last_slot, now):
        self.ensure_month(now)
        if month != self.month:
            return False
        try:
            value = _decimal(kw)
            n = int(count)
        except (ValueError, TypeError):
            return False
        if n < 1 or not last_slot:
            return False
        self.kw = float(value)
        self.count = n
        self.last_slot = str(last_slot)
        return True

    def record_slot(self, start, end, energy_wh, coverage_seconds):
        """Accept a quarter only if it ends at its fixed 15-min boundary.

        Missing samples or a delayed Home Assistant restart cannot be
        silently reconstructed. For any missing month data, this observed
        maximum can be *lower* than the network operator's billed maximum.
        """
        self.ensure_month(end)
        if end != start + timedelta(minutes=15) or start.minute % 15:
            return False
        if self.month != start.strftime("%Y-%m"):
            return False
        try:
            wh = _decimal(energy_wh)
            coverage = _decimal(coverage_seconds)
        except ValueError:
            return False
        if coverage < Decimal("855") or coverage > Decimal("900"):
            return False
        slot_id = start.isoformat()
        if slot_id == self.last_slot:
            return False
        kw = float((wh / Decimal("250")).quantize(Decimal("0.01"),
                   rounding=ROUND_HALF_UP))
        self.kw = max(kw, self.kw) if self.kw is not None else kw
        self.count += 1
        self.last_slot = slot_id
        return True
