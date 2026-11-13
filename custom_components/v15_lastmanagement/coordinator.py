"""V15 monitor with opt-in prioritized shedding and conservative restoration.

No hardware action without explicit live control. Restoration is separately
opted into via the options flow and is possible only for confirmed loads that
V15 itself turned off during this integration runtime. The ownership record is
intentionally not restored across Home Assistant restarts or config reloads.
"""
from datetime import timedelta
import logging
import math

from homeassistant.core import callback
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    CONF_GRID, CONF_LIMIT, CONF_RESERVE, CONF_REVERSED, CONF_LOADS,
    CONF_STALE, DEFAULT_STALE, CONF_RESTORE, CONF_RESTORE_POWERS,
    CONF_RESTORE_STABLE, CONF_RESTORE_MIN_OFF, CONF_RESTORE_MARGIN,
    DEFAULT_RESTORE, DEFAULT_RESTORE_STABLE, DEFAULT_RESTORE_MIN_OFF,
    DEFAULT_RESTORE_MARGIN,
)
from .math_v15 import quarter_start, calculate
from .restore_logic import power_headroom_ok, periods_satisfied
from .evcc_control import V15EvccController
from .goe_control import V15GoeController

_LOGGER = logging.getLogger(__name__)

# A successful service call is not proof that the physical switch changed
# state. Only record switches that report 'off' within this interval.
SHED_CONFIRMATION_SECONDS = 20
# After restoring one load, observe the total grid load before another restore.
RESTORE_SPACING_SECONDS = 60
# Avoid turning on a load right before the meter's quarter-hour reset.
RESTORE_MIN_REMAINING_SECONDS = 90


class V15Monitor:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.config = {**entry.data, **entry.options}
        self.grid_entity = self.config[CONF_GRID]
        self.load_entities = list(dict.fromkeys(self.config.get(CONF_LOADS, [])))
        self.listeners = []
        self.subscribers = []
        self.enabled = False  # No actuation on restart or reload.
        self.simulation = True
        self.demo_data = False  # Synthetic readings never operate hardware.
        self.demo_started = None
        self.last_time = None
        self.last_w = None
        self.slot = None
        self.energy_wh = 0.0
        self.coverage_s = 0.0
        self.last_shed_time = None
        self.last_restore_time = None
        self.data = {}
        self.last_action = "Noch keine Schalthandlung"
        self.control_busy = False
        self.action_pending = False
        self.last_candidate = None
        # A switch must be confirmed OFF after a V15 request before we own it.
        self.pending_off = {}  # switch -> timestamp of V15 off request
        self.pending_on = {}   # switch -> timestamp of unconfirmed ON request
        self.managed_off = {}  # switch -> timestamp of confirmed off state
        self.restore_candidate = None
        self.restore_since = None
        self.restore_status = "Wiedereinschaltung nicht geprüft"
        self.evcc = V15EvccController(self)
        self.goe = V15GoeController(self)
        if self.evcc.configured and self.goe.configured:
            raise ValueError('evcc and direct go-e control are mutually exclusive')
        self.charger = self.goe if self.goe.configured else self.evcc

    def calculate_current(self, now, watts):
        """Fresh quarter-hour budget for a late asynchronous evcc action."""
        if self.slot != quarter_start(now):
            return None
        elapsed = max(0.0, min(900.0, (now - self.slot).total_seconds()))
        return calculate(self.energy_wh, elapsed, max(0.0, watts),
                         float(self.config[CONF_LIMIT]), float(self.config[CONF_RESERVE]))

    @property
    def auto_restore_enabled(self):
        return bool(self.config.get(CONF_RESTORE, DEFAULT_RESTORE))

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

    def _last_managed_off(self):
        """Restore in reverse shedding order (last shed, first restored)."""
        for entity_id in reversed(tuple(self.managed_off)):
            state = self.hass.states.get(entity_id)
            if state is not None and state.state == STATE_OFF:
                return entity_id
        return None

    def _mark_our_off(self, entity_id):
        self.pending_off.pop(entity_id, None)
        if entity_id not in self.managed_off:
            self.managed_off[entity_id] = dt_util.now()
            _LOGGER.info("V15 confirmed managed switch off: %s", entity_id)
        self.last_action = f"Abgeschaltet: {entity_id}"
        self.notify()

    @callback
    def _on_load_change(self, event):
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        if not entity_id or new_state is None:
            return
        if new_state.state == STATE_OFF and entity_id in self.pending_off:
            started = self.pending_off[entity_id]
            if 0 <= (dt_util.now() - started).total_seconds() <= SHED_CONFIRMATION_SECONDS:
                self._mark_our_off(entity_id)
        elif new_state.state == STATE_ON:
            if entity_id in self.pending_on:
                self.pending_on.pop(entity_id, None)
                self.last_action = f"Wiedereingeschaltet (bestätigt): {entity_id}"
            # Manual/external ON revokes our right to restore this load.
            self.pending_off.pop(entity_id, None)
            if entity_id in self.managed_off:
                self.managed_off.pop(entity_id, None)
                self.restore_candidate = None
                self.restore_since = None
                _LOGGER.info("V15 released managed switch after ON: %s", entity_id)
        self.update()

    def _cleanup_pending(self, now):
        for entity_id, requested in tuple(self.pending_off.items()):
            if (now - requested).total_seconds() > SHED_CONFIRMATION_SECONDS:
                self.pending_off.pop(entity_id, None)
                _LOGGER.warning("V15 did not confirm switch OFF: %s", entity_id)
        for entity_id, requested in tuple(self.pending_on.items()):
            if (now - requested).total_seconds() > SHED_CONFIRMATION_SECONDS:
                self.pending_on.pop(entity_id, None)
                self.last_action = f"Wiedereinschaltung nicht bestätigt: {entity_id}"
                _LOGGER.warning("V15 did not confirm switch ON: %s", entity_id)

    def _restore_power(self, entity_id):
        try:
            power = float(self.config.get(CONF_RESTORE_POWERS, {}).get(entity_id, 0))
        except (ValueError, TypeError):
            return None
        return power if math.isfinite(power) and 10 <= power <= 25000 else None

    def _restore_eligible(self, now, watts, cal, trusted):
        """Return (candidate, reason) for conservative one-at-a-time restore."""
        if not self.auto_restore_enabled:
            return None, "Automatische Wiedereinschaltung in den Optionen deaktiviert"
        if not self.enabled or self.demo_data or self.simulation:
            return None, "Aktive Laststeuerung nicht eingeschaltet"
        if not self.managed_off:
            return None, "Keine von V15 bestätigten Abschaltungen vorhanden"
        if not trusted or watts is None:
            return None, "Warte auf gültige Messwerte (mind. 60 s und 95 % Abdeckung)"
        if cal["at_risk"]:
            return None, "Viertelstundenprognose gefährdet die Leistungsgrenze"
        remaining_s = 900 - (now - quarter_start(now)).total_seconds()
        if remaining_s < RESTORE_MIN_REMAINING_SECONDS:
            return None, "Warte auf neue Viertelstunde (weniger als 90 s verbleiben)"
        if self.pending_off or self.pending_on:
            return None, "Warte auf Rückmeldung der letzten Schalthandlung"
        if self.last_shed_time and (now - self.last_shed_time).total_seconds() < RESTORE_SPACING_SECONDS:
            return None, "Warte nach der letzten Abschaltung"
        if self.last_restore_time and (now - self.last_restore_time).total_seconds() < RESTORE_SPACING_SECONDS:
            return None, "Warte auf Stabilisierung nach Wiedereinschaltung"
        candidate = self._last_managed_off()
        if candidate is None:
            return None, "V15-Last ist derzeit nicht eindeutig ausgeschaltet"
        load_w = self._restore_power(candidate)
        if load_w is None:
            return None, f"Leistungsangabe für {candidate} fehlt oder ist ungültig"
        margin_w = float(self.config.get(CONF_RESTORE_MARGIN, DEFAULT_RESTORE_MARGIN))
        if not power_headroom_ok(watts, cal["budget_kw"], load_w, margin_w):
            return None, f"Nicht genug Restbudget für {candidate} ({load_w:g} W + {margin_w:g} W Puffer)"
        return candidate, "Ausreichendes Restbudget vorhanden"

    @callback
    def update(self, _event=None):
        now = dt_util.now()
        slot = quarter_start(now)
        self._cleanup_pending(now)
        if self.demo_data:
            elapsed_demo = (now - self.demo_started).total_seconds() if self.demo_started else 0
            phase = elapsed_demo % 180
            watts = 2000.0 if phase < 70 else (8000.0 if phase < 140 else 2000.0)
        else:
            watts = self.read_power()

        if self.slot != slot:
            # Every fixed quarter-hour starts with fresh coverage and energy.
            self.slot = slot
            self.energy_wh = 0.0
            self.coverage_s = 0.0
            self.last_time = None
            self.last_w = None
            self.restore_candidate = None
            self.restore_since = None
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

        restore_candidate, restore_status = self._restore_eligible(now, watts, cal, trusted)
        restore_ready = False
        if restore_candidate is None:
            self.restore_candidate = None
            self.restore_since = None
        else:
            if restore_candidate != self.restore_candidate:
                self.restore_candidate = restore_candidate
                self.restore_since = now
            off_at = self.managed_off[restore_candidate]
            min_off_s = int(self.config.get(CONF_RESTORE_MIN_OFF, DEFAULT_RESTORE_MIN_OFF))
            stable_s = int(self.config.get(CONF_RESTORE_STABLE, DEFAULT_RESTORE_STABLE))
            restore_ready = periods_satisfied(
                now, off_at, self.restore_since, min_off_s, stable_s
            )
            if not restore_ready:
                off_elapsed = max(0, round((now - off_at).total_seconds()))
                stable_elapsed = max(0, round((now - self.restore_since).total_seconds()))
                restore_status = (
                    f"Wartezeit {off_elapsed}/{min_off_s} s, "
                    f"stabile Reserve {stable_elapsed}/{stable_s} s für {restore_candidate}"
                )
            else:
                restore_status = f"Wiedereinschaltung möglich: {restore_candidate}"
        self.restore_status = restore_status

        if self.demo_data:
            reason = (f"DEMO: {candidate or 'kein Schalter'} wäre Kandidat; keine echte Steuerung"
                      if risky else "DEMO: innerhalb des Zielwerts; keine Hardwaresteuerung")
        elif watts is None:
            reason = "Messwert fehlt, ist veraltet oder Einheit nicht W/kW"
        elif not trusted:
            reason = "Messabdeckung noch unzureichend (mind. 60 s und 95 %)"
        elif risky and not candidate:
            reason = "Grenzwert gefährdet, kein konfigurierter Schalter eingeschaltet"
        elif risky and self.enabled:
            reason = "Aktive Abschaltung freigegeben"
        elif risky and self.simulation:
            reason = f"SIMULATION: {candidate} würde abgeschaltet"
        elif risky:
            reason = "Aktive Abschaltung ausgeschaltet"
        else:
            reason = "Prognose innerhalb des Zielwerts"

        self.last_candidate = candidate
        self.data = {
            **cal,
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
            "managed_off_count": len(self.managed_off),
            "restore_candidate": restore_candidate,
            "restore_ready": restore_ready,
            "restore_status": restore_status,
        }
        if (self.enabled and trusted and risky and candidate) or (
            self.enabled and self.last_shed_time and
            (now - self.last_shed_time).total_seconds() < 30
        ):
            # A configured switch is shed first; do not adjust evcc and a
            # switch simultaneously based on the same pre-action grid reading.
            self.charger._preview(trusted, cal, watts)
            if self.charger.enabled:
                self.charger.status = "Warte auf vorrangige Lastabschaltung"
        else:
            self.charger.evaluate(now, trusted, cal, watts)
        self.notify()

        cooldown_ok = self.last_shed_time is None or (now - self.last_shed_time).total_seconds() >= 30
        if (self.enabled and not self.demo_data and trusted and risky and candidate and cooldown_ok
                and not self.control_busy and not self.action_pending):
            self.action_pending = True
            self.hass.async_create_task(self.async_shed())
        elif (restore_ready and not self.control_busy and not self.action_pending):
            self.action_pending = True
            self.hass.async_create_task(self.async_restore())

    async def async_shed(self):
        if not self.enabled or self.control_busy:
            self.action_pending = False
            return
        self.control_busy = True
        entity_id = None
        try:
            if (not self.enabled or self.demo_data or
                    not self.data.get("trusted_for_control") or
                    not self.data.get("at_risk")):
                return
            if self.read_power() is None:
                return
            entity_id = self._first_on_switch()
            if entity_id is None:
                return
            requested_at = dt_util.now()
            self.pending_off[entity_id] = requested_at
            self.last_shed_time = requested_at
            await self.hass.services.async_call(
                "switch", "turn_off", {"entity_id": entity_id}, blocking=True
            )
            current = self.hass.states.get(entity_id)
            if current is not None and current.state == STATE_OFF:
                self._mark_our_off(entity_id)
            else:
                self.last_action = f"Abschaltung angefordert, Status noch nicht bestätigt: {entity_id}"
            _LOGGER.info("V15 requested discretionary switch OFF: %s", entity_id)
        except Exception:
            if entity_id is not None:
                self.pending_off.pop(entity_id, None)
            _LOGGER.exception("V15 failed to turn off discretionary load")
            self.last_action = "Fehler bei der Abschaltung (siehe Protokoll)"
        finally:
            self.control_busy = False
            self.action_pending = False
            self.notify()

    async def async_restore(self):
        if not self.enabled or self.control_busy:
            self.action_pending = False
            return
        self.control_busy = True
        try:
            if (not self.enabled or not self.auto_restore_enabled or
                    self.demo_data or self.simulation or
                    not self.data.get("trusted_for_control") or
                    not self.data.get("restore_ready")):
                return
            watts = self.read_power()
            if watts is None:
                return
            now = dt_util.now()
            cal = calculate(
                self.energy_wh,
                max(0.0, (now - self.slot).total_seconds()),
                max(0.0, watts),
                float(self.config[CONF_LIMIT]), float(self.config[CONF_RESERVE]),
            )
            entity_id, _reason = self._restore_eligible(now, watts, cal, True)
            if entity_id is None or entity_id != self.restore_candidate:
                return
            if not periods_satisfied(
                now, self.managed_off[entity_id], self.restore_since,
                int(self.config.get(CONF_RESTORE_MIN_OFF, DEFAULT_RESTORE_MIN_OFF)),
                int(self.config.get(CONF_RESTORE_STABLE, DEFAULT_RESTORE_STABLE))
            ):
                return
            state = self.hass.states.get(entity_id)
            if state is None or state.state != STATE_OFF:
                return
            # The pending flag separates command delivery from device feedback.
            self.pending_on[entity_id] = now
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": entity_id}, blocking=True
            )
            self.last_restore_time = dt_util.now()
            # Never retry automatically for the same OFF incident. A device
            # that fails to report ON stays off for manual inspection.
            self.managed_off.pop(entity_id, None)
            self.restore_candidate = None
            self.restore_since = None
            current = self.hass.states.get(entity_id)
            if current is not None and current.state == STATE_ON:
                self.pending_on.pop(entity_id, None)
                self.last_action = f"Wiedereingeschaltet (bestätigt): {entity_id}"
            else:
                self.last_action = f"Wiedereinschaltung angefordert, Rückmeldung offen: {entity_id}"
            _LOGGER.info("V15 restored managed switch: %s", entity_id)
        except Exception:
            if self.restore_candidate is not None:
                self.pending_on.pop(self.restore_candidate, None)
            _LOGGER.exception("V15 failed to restore discretionary load")
            self.last_action = "Fehler bei Wiedereinschaltung (siehe Protokoll)"
            self.last_restore_time = dt_util.now()  # avoid immediate retry loop
        finally:
            self.control_busy = False
            self.action_pending = False
            self.notify()

    async def async_start(self):
        self.listeners.append(async_track_state_change_event(
            self.hass, [self.grid_entity], self.update
        ))
        if self.evcc.observed_entities:
            self.listeners.append(async_track_state_change_event(
                self.hass, self.evcc.observed_entities, self.update
            ))
        if self.load_entities:
            self.listeners.append(async_track_state_change_event(
                self.hass, self.load_entities, self._on_load_change
            ))
        self.listeners.append(async_track_time_interval(
            self.hass, self.update, timedelta(seconds=5)
        ))
        await self.goe.async_start()
        self.update()

    async def async_stop(self):
        await self.goe.async_stop()
        self.evcc.deactivate("HA-Neustart oder Konfigurationswechsel; keine automatische evcc-Freigabe")
        self.enabled = False
        self.demo_data = False
        for unsubscribe in self.listeners:
            unsubscribe()
        self.listeners.clear()
        # Never restore loads at unload. They remain OFF for manual review.
        self.pending_off.clear()
        self.pending_on.clear()
        self.managed_off.clear()
        self.restore_candidate = None
        self.restore_since = None
