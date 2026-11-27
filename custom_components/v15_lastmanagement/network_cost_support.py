"""Optional preview of Austrian monthly grid-capacity charge.

No network billing data is retrieved. Only a *completed*, sufficiently covered
local V15 15-minute period enters the observed-month peak. The calculation is
not an invoice and cannot recover earlier peaks or HA measurement gaps.
"""
from .const import (
    CONF_COST_CONFIGURED, CONF_COST_REGION, CONF_COST_MODE,
    CONF_COST_FIRST, CONF_COST_HIGHER, CONF_COST_MINIMUM,
    CONF_LIMIT,
)
from .network_costs import (
    DRAFT_2027_NE7, DRAFT_SOURCE, MonthlyPeak, monthly_capacity_charge,
    estimate_difference,
)


class V15NetworkCostMonitor:
    def __init__(self, monitor):
        self.monitor = monitor
        self.enabled = bool(monitor.config.get(CONF_COST_CONFIGURED, False))
        self.mode = monitor.config.get(CONF_COST_MODE, "draft2027")
        self.region = monitor.config.get(CONF_COST_REGION, "")
        self.peak = MonthlyPeak()
        self.storage = None
        self.history_completeness_warning = True
        self.last_status = "Keine abgeschlossenen Viertelstunden verfügbar"

    def rates(self):
        if not self.enabled:
            return None
        if self.mode == "draft2027":
            return DRAFT_2027_NE7.get(self.region)
        if self.mode == "manual":
            try:
                return (float(self.monitor.config[CONF_COST_FIRST]),
                        float(self.monitor.config[CONF_COST_HIGHER]))
            except (KeyError, ValueError, TypeError):
                return None
        return None

    async def async_load(self):
        if not self.enabled:
            return
        from homeassistant.helpers.storage import Store
        from homeassistant.util import dt as dt_util
        self.storage = Store(
            self.monitor.hass, 1,
            f"v15_lastmanagement_monthly_capacity_{self.monitor.entry.entry_id}",
        )
        old = await self.storage.async_load()
        if isinstance(old, dict):
            self.peak.restore(old.get("month"), old.get("kw"),
                              old.get("count", 0), old.get("last_slot"),
                              dt_util.now())

    def _snapshot(self):
        return {
            "month": self.peak.month,
            "kw": self.peak.kw,
            "count": self.peak.count,
            "last_slot": self.peak.last_slot,
        }

    def complete_slot(self, start, end, wh, coverage_s, demo=False):
        if not self.enabled or demo:
            return
        if self.peak.record_slot(start, end, wh, coverage_s):
            self.last_status = "Lokale Viertelstundenspitze fortgeschrieben"
            if self.storage is not None:
                self.storage.async_delay_save(self._snapshot, 1.0)

    def snapshot(self, now):
        self.peak.ensure_month(now)
        rates = self.rates()
        peak_kw = self.peak.kw
        minimum = float(self.monitor.config.get(CONF_COST_MINIMUM, 2.0))
        if not self.enabled or rates is None or peak_kw is None:
            return {
                "month": self.peak.month, "peak_kw": peak_kw,
                "estimated_eur": None, "hypothetical_reduction_eur": None,
                "period_count": self.peak.count, "complete": False,
            }
        charge = monthly_capacity_charge(peak_kw, *rates, minimum_kw=minimum)
        hypothetical = estimate_difference(
            peak_kw, float(self.monitor.config[CONF_LIMIT]),
            *rates, minimum_kw=minimum,
        )
        return {
            "month": self.peak.month,
            "peak_kw": peak_kw,
            "estimated_eur": charge,
            "hypothetical_reduction_eur": hypothetical,
            "period_count": self.peak.count,
            "complete": False,
        }

    def metadata(self):
        return {
            "tariff_mode": self.mode,
            "net_area": self.region if self.mode == "draft2027" else None,
            "source": DRAFT_SOURCE if self.mode == "draft2027"
                      else "Benutzerdefinierter Tarif, nicht extern geprüft",
            "legal_status": "Entwurf – keine gültige Abrechnung"
                            if self.mode == "draft2027"
                            else "Benutzereingabe – Gültigkeit nicht geprüft",
            "network_level": 7 if self.mode == "draft2027" else None,
            "rates_cents_per_kw_month": self.rates(),
            "assumed_minimum_kw": float(
                self.monitor.config.get(CONF_COST_MINIMUM, 2.0)),
            "excludes": [
                "Arbeitspreis", "Netzverlustentgelt", "Netzbereitstellung",
                "Steuern", "Umsatzsteuer", "sonstige Entgelte",
            ],
            "warning": (
                "Nur vollständig erfasste Viertelstunden seit Aktivierung "
                "werden berücksichtigt. Der Wert kann unter der tatsächlich "
                "verrechneten Monatsspitze liegen. Keine Rechnungsprognose."
            ),
        }
