"""5-second sample-based monitoring and optional one-way load shedding.

Actions NEVER occur after an unknown sample or with insufficient slot coverage.
No automatic load restoration; user explicitly opts into live actuation.
"""
from datetime import timedelta
import logging
import math

from homeassistant.core import callback
from homeassistant.const import STATE_ON
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import CONF_GRID, CONF_LIMIT, CONF_RESERVE, CONF_REVERSED, CONF_LOADS, CONF_STALE, DEFAULT_STALE
from .math_v15 import quarter_start, calculate

_LOGGER = logging.getLogger(__name__)


class V15Monitor:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.config = {**entry.data, **entry.options}
        self.grid_entity = self.config[CONF_GRID]
        self.load_entities = list(self.config.get(CONF_LOADS, []))
        self.listeners = []
        self.subscribers = []
        self.enabled = False  # Live control is disabled every startup/reload.
        self.simulation = True
        self.demo_data = False  # Synthetic readings; never operate hardware.
        self.demo_started = None
        self.last_time = None
        self.last_w = None
        self.slot = None
        self.energy_wh = 0.0
        self.coverage_s = 0.0
        self.last_shed_time = None
        self.data = {}
        self.last_action = "Noch keine Schalthandlung"
        self.control_busy = False
        self.action_pending = False
        self.last_candidate = None

    def subscribe(self, callback_fn):
        self.subscribers.append(callback_fn)
        def unsubscribe():
            if callback_fn in self.subscribers:
                self.subscribers.remove(callback_fn)
        return unsubscribe

    @callback
    def notify(self):
        for fn in tuple(self.subscribers):
            fn()

    def read_power(self):
        state = self.hass.states.get(self.grid_entity)
        if state is None or state.state in ("unavailable", "unknown", "none", ""):
            return None
        age = (dt_util.utcnow() - state.last_updated).total_seconds()
        if age < -5 or age > int(self.config.get(CONF_STALE, DEFAULT_STALE)):
            return None
        try:
            raw = float(state.state)
            unit = str(state.attributes.get("unit_of_measurement", "")).strip().lower()
            if unit in ("w", "watt", "watts"):
                watts = raw
            elif unit in ("kw", "kilowatt"):
                watts = raw * 1000
            else:
                return None
            if self.config.get(CONF_REVERSED, False):
                watts = -watts
            return watts if math.isfinite(watts) else None
        except (ValueError, TypeError):
            return None

    def _first_on_switch(self):
        for entity_id in self.load_entities:
            state = self.hass.states.get(entity_id)
            if state is not None and state.state == STATE_ON:
                return entity_id
        return None

    @callback
    def update(self, _event=None):
        now = dt_util.now()
        slot = quarter_start(now)
        if self.demo_data:
            # Repeat an illustrative 180-second 2 -> 8 kW profile.
            # It uses the same integrator and coverage logic as a real sensor.
            elapsed_demo = (now - self.demo_started).total_seconds() if self.demo_started else 0
            phase = elapsed_demo % 180
            watts = 2000.0 if phase < 70 else (8000.0 if phase < 140 else 2000.0)
        else:
            watts = self.read_power()
        if self.slot != slot:
            # Never reconstruct any undocumented history or assume continuity.
            self.slot = slot
            self.energy_wh = 0.0
            self.coverage_s = 0.0
            self.last_time = None
            self.last_w = None
        if watts is None:
            self.last_time = None
            self.last_w = None
        else:
            if self.last_time is not None and self.last_w is not None:
                dt = (now - self.last_time).total_seconds()
                if 0 < dt <= 30:
                    self.energy_wh += max(0.0, self.last_w) * dt / 3600.0
                    self.coverage_s += dt
            self.last_time = now
            self.last_w = watts
        elapsed = max(0.0, min(900.0, (now - slot).total_seconds()))
        cal = calculate(self.energy_wh, elapsed, max(0.0, watts or 0.0),
                        float(self.config[CONF_LIMIT]), float(self.config[CONF_RESERVE]))
        coverage = self.coverage_s / elapsed if elapsed else 0
        trusted = watts is not None and elapsed >= 60 and coverage >= 0.95 and not self.demo_data
        candidate = self._first_on_switch()
        risky = watts is not None and cal["at_risk"]
        if self.demo_data:
            reason = f"DEMO (synthetische Daten): {candidate or 'kein Schalter'} wäre Kandidat; es wird nie geschaltet" if risky else "DEMO (synthetische Daten): innerhalb des Zielwerts; keine Hardwaresteuerung"
        elif watts is None:
            reason = "Messwert fehlt, ist veraltet oder Einheit nicht W/kW"
        elif not trusted:
            reason = "Messabdeckung noch unzureichend (mind. 60 s und 95 %)"
        elif not risky:
            reason = "Prognose innerhalb des Zielwerts"
        elif not candidate:
            reason = "Grenzwert gefährdet, kein konfigurierter Schalter eingeschaltet"
        elif self.enabled:
            reason = "Aktive Abschaltung freigegeben"
        elif self.simulation:
            reason = f"SIMULATION: {candidate} würde abgeschaltet"
        else:
            reason = "Aktive Abschaltung ausgeschaltet"
        self.last_candidate = candidate
        self.data = {
            **cal,
            # Suppress a misleading budget until a continuous, sufficiently
            # covered slot has actually been observed.
            "budget_kw": cal["budget_kw"] if trusted else None,
            "trusted_for_control": trusted,
            "coverage_percent": round(100 * coverage, 1),
            "grid_kw": round(watts / 1000.0, 3) if watts is not None else None,
            "energy_kwh": round(self.energy_wh / 1000.0, 4),
            "elapsed_s": round(elapsed),
            "slot": slot.isoformat(),
            "valid": watts is not None,
            "demo_data": self.demo_data,
            "reason": reason,
            "next_switch": candidate,
            "last_action": self.last_action,
        }
        self.notify()
        cooldown_ok = self.last_shed_time is None or (now - self.last_shed_time).total_seconds() >= 30
        if (self.enabled and not self.demo_data and trusted and risky and candidate and cooldown_ok
                and not self.control_busy and not self.action_pending):
            self.action_pending = True
            self.hass.async_create_task(self.async_shed())

    async def async_shed(self):
        if not self.enabled or self.control_busy:
            self.action_pending = False
            return
        self.control_busy = True
        try:
            # Recheck before executing: control could have been disabled.
            if not self.enabled or self.demo_data or not self.data.get("trusted_for_control") or not self.data.get("at_risk"):
                return
            # Revalidate fresh sensor and selected loads at the actual moment of service call.
            if self.read_power() is None:
                return
            entity_id = self._first_on_switch()
            if entity_id is None:
                return
            await self.hass.services.async_call("switch", "turn_off", {"entity_id": entity_id}, blocking=True)
            self.last_action = f"Abgeschaltet: {entity_id}"
            self.last_shed_time = dt_util.now()
            _LOGGER.warning("V15 load shedding: %s", entity_id)
        except Exception:
            _LOGGER.exception("V15 failed to turn off discretionary load")
            self.last_action = "Fehler bei der Abschaltung (siehe Protokoll)"
            self.last_shed_time = dt_util.now()
        finally:
            self.control_busy = False
            self.action_pending = False
            self.notify()

    async def async_start(self):
        self.listeners.append(async_track_state_change_event(self.hass, [self.grid_entity], self.update))
        self.listeners.append(async_track_time_interval(self.hass, self.update, timedelta(seconds=5)))
        self.update()

    async def async_stop(self):
        self.enabled = False
        self.demo_data = False
        for unsubscribe in self.listeners:
            unsubscribe()
        self.listeners.clear()
