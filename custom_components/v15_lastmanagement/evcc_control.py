"""Optional evcc controller via existing Home Assistant evcc entities.

User opt-in is required *every runtime*. No network credentials are stored.
This regulator never enables the evcc 'now' mode or changes phase wiring.
It may only switch from 'smart' to 'off' and back after an owned pause.
"""
from datetime import timedelta
import logging
import math

from homeassistant.util import dt as dt_util
from .const import (
    CONF_STALE, DEFAULT_STALE, CONF_EVCC_CONFIGURED, CONF_EVCC_CURRENT,
    CONF_EVCC_MODE, CONF_EVCC_POWER, CONF_EVCC_PHASES,
    CONF_EVCC_FIXED_PHASES, CONF_EVCC_MIN_A, CONF_EVCC_MAX_A,
    CONF_EVCC_VOLTAGE, CONF_EVCC_MARGIN_W, CONF_EVCC_STABLE_S,
    CONF_EVCC_STEP_S, CONF_EVCC_ALLOW_PAUSE,
    DEFAULT_EVCC_PHASES, DEFAULT_EVCC_MIN_A, DEFAULT_EVCC_MAX_A,
    DEFAULT_EVCC_VOLTAGE, DEFAULT_EVCC_MARGIN_W, DEFAULT_EVCC_STABLE_S,
    DEFAULT_EVCC_STEP_S,
)
from .evcc_logic import charging_budget, parse_amperes, select_option_for_amperes

_LOGGER = logging.getLogger(__name__)


class V15EvccController:
    """Regulate charger maximum current, optionally pause in smart mode."""

    def __init__(self, monitor):
        self.monitor = monitor
        self.hass = monitor.hass
        self.config = monitor.config
        self.configured = bool(self.config.get(CONF_EVCC_CONFIGURED))
        self.enabled = False  # Never restored across HA restarts or options reload.
        self.owned_pause = False
        self.original_current = None
        self.last_command = None
        self.last_action = "Noch keine evcc-Aktion"
        self.stop_reason = None  # Keep safety-stop reason visible until next opt-in.
        self.status = "evcc nicht konfiguriert" if not self.configured else "evcc-Regelung ausgeschaltet"
        self.target = None
        self.base_w = None
        self.available_w = None
        self.busy = False
        self.action_pending = False
        self.last_change_at = None
        self.increase_ready_since = None
        self.resume_ready_since = None
        self.expected_current = None
        self.expected_mode = None
        self.ack_deadline = None
        self.last_phases = None
        self.last_confirmed_current = None
        self.last_confirmed_mode = None

    @property
    def observed_entities(self):
        if not self.configured:
            return []
        keys = (CONF_EVCC_CURRENT, CONF_EVCC_MODE, CONF_EVCC_POWER, CONF_EVCC_PHASES)
        return [self.config[key] for key in keys if self.config.get(key)]

    def _state(self, key):
        entity = self.config.get(key)
        return self.hass.states.get(entity) if entity else None

    def _power(self):
        state = self._state(CONF_EVCC_POWER)
        if state is None or state.state in ("unknown", "unavailable", ""):
            return None
        age = (dt_util.utcnow() - state.last_updated).total_seconds()
        if age < -5 or age > self.config.get(CONF_STALE, DEFAULT_STALE):
            return None
        try:
            number = float(state.state)
            unit = str(state.attributes.get("unit_of_measurement", "")).lower().strip()
            if unit == "kw":
                number *= 1000.0
            elif unit != "w":
                return None
            return number if math.isfinite(number) and 0 <= number <= 100000 else None
        except (TypeError, ValueError):
            return None

    def _phases(self):
        if self.config.get(CONF_EVCC_PHASES):
            state = self._state(CONF_EVCC_PHASES)
            if state is None:
                return None
            try:
                phases = int(float(state.state))
            except (TypeError, ValueError):
                return None
            # 0 while not charging is normal on some integrations. Treat as
            # unknown rather than assuming a potentially unsafe phase count.
            if phases in (1, 3):
                self.last_phases = phases
                return phases
            if self.owned_pause and self.last_phases in (1, 3):
                # Prefer 3 phases for conservative resumption planning.
                return max(self.last_phases, int(self.config.get(
                    CONF_EVCC_FIXED_PHASES, DEFAULT_EVCC_PHASES)))
            return None
        return int(self.config.get(CONF_EVCC_FIXED_PHASES, DEFAULT_EVCC_PHASES))

    def _snapshot(self):
        current = self._state(CONF_EVCC_CURRENT)
        mode = self._state(CONF_EVCC_MODE)
        charge_w = self._power()
        phases = self._phases()
        if not current or not mode or charge_w is None or phases is None:
            return None
        if current.state in ("unknown", "unavailable") or mode.state in ("unknown", "unavailable"):
            return None
        current_a = parse_amperes(current.state)
        if current_a is None or not (6 <= current_a <= 32):
            return None
        return {"current": current, "current_a": current_a,
                "mode": mode, "mode_name": mode.state,
                "charge_w": charge_w, "phases": phases}

    def activate(self):
        if not self.configured:
            raise ValueError("evcc ist nicht konfiguriert")
        if self.monitor.demo_data:
            raise ValueError("V15 Demo mit künstlichen Messwerten deaktivieren")
        snap = self._snapshot()
        if snap is None:
            raise ValueError("evcc-Messwerte, Phasen oder Entitäten sind ungültig")
        if snap["mode_name"] != "smart":
            raise ValueError("evcc muss vor der Aktivierung im Modus smart sein")
        if self.config[CONF_EVCC_CURRENT].split(".")[0] not in ("select", "number"):
            raise ValueError("Maximalstrom muss eine select- oder number-Entität sein")
        self.enabled = True
        self.stop_reason = None
        self.owned_pause = False
        self.original_current = snap["current_a"]
        self.last_confirmed_current = snap["current_a"]
        self.last_confirmed_mode = "smart"
        self.expected_current = None
        self.expected_mode = None
        self.ack_deadline = None
        self.increase_ready_since = None
        self.resume_ready_since = None
        self.status = "evcc-Steuerung aktiv; prüfe Leistungsbudget"

    def deactivate(self, reason="evcc-Steuerung ausgeschaltet"):
        # Never automatically boost charging after a failure or a manual OFF.
        # If V15 had paused the loadpoint, user must explicitly resume in evcc.
        self.enabled = False
        self.stop_reason = reason
        self.status = reason
        self.increase_ready_since = None
        self.resume_ready_since = None
        self.owned_pause = False
        self.expected_current = None
        self.expected_mode = None
        self.ack_deadline = None

    def _acknowledged(self, snap, now):
        """Abandon ownership on missing or unexpected command confirmation."""
        if self.ack_deadline is not None:
            pending_current = self.expected_current
            pending_mode = self.expected_mode
            ok_current = pending_current is None or abs(snap["current_a"] - pending_current) < 0.1
            ok_mode = pending_mode is None or snap["mode_name"] == pending_mode
            if ok_current and ok_mode:
                self.ack_deadline = None
                self.last_confirmed_current = snap["current_a"]
                self.last_confirmed_mode = snap["mode_name"]
                self.expected_current = None
                self.expected_mode = None
            elif now > self.ack_deadline:
                self.deactivate("evcc-Rückmeldung nach Stellbefehl fehlt; manuell prüfen")
                _LOGGER.warning("V15 evcc command not confirmed; control stopped")
                return False
            else:
                self.status = "Warte auf evcc-Rückmeldung"
                return False
        if (self.last_confirmed_current is not None and
                abs(snap["current_a"] - self.last_confirmed_current) > 0.1):
            self.deactivate("evcc-Maximalstrom extern verändert; V15 stoppt zur Konfliktvermeidung")
            return False
        if (self.last_confirmed_mode is not None and
                snap["mode_name"] != self.last_confirmed_mode):
            self.deactivate("evcc-Lademodus extern verändert; V15 stoppt zur Konfliktvermeidung")
            return False
        return True

    def _preview(self, trusted, cal, grid_w):
        """Always calculate a dry-run target when evcc readings are valid."""
        self.target = None
        self.available_w = None
        self.base_w = None
        if not self.configured or not trusted or grid_w is None:
            return None
        snap = self._snapshot()
        if snap is None:
            return None
        try:
            budget = charging_budget(
                grid_w=grid_w, charging_w=snap["charge_w"],
                budget_kw=cal["budget_kw"], phases=snap["phases"],
                voltage=float(self.config.get(CONF_EVCC_VOLTAGE, DEFAULT_EVCC_VOLTAGE)),
                minimum_a=float(self.config.get(CONF_EVCC_MIN_A, DEFAULT_EVCC_MIN_A)),
                maximum_a=min(float(self.config.get(CONF_EVCC_MAX_A, DEFAULT_EVCC_MAX_A)),
                              self.original_current or DEFAULT_EVCC_MAX_A),
                margin_w=float(self.config.get(CONF_EVCC_MARGIN_W, DEFAULT_EVCC_MARGIN_W)),
            )
        except (ValueError, TypeError):
            return None
        self.target = budget.target_current_a
        self.available_w = round(budget.available_charge_w)
        self.base_w = round(budget.base_import_w)
        return snap, budget

    def decide(self, now, trusted, cal, grid_w):
        """Return (service, value) or None; preview remains usable in dry-run."""
        preview = self._preview(trusted, cal, grid_w)
        if not self.configured:
            self.status = "evcc nicht konfiguriert"
            return None
        if not self.enabled:
            self.status = self.stop_reason or (
                "evcc-Regelung aus; Zielstrom nur berechnet"
                if preview else "evcc-Regelung ausgeschaltet"
            )
            return None
        if self.monitor.demo_data or self.monitor.simulation:
            self.status = "Demo/Probelauf: keine evcc-Stellbefehle"
            return None
        if not trusted or grid_w is None:
            self.status = "Warte auf gültige Netzwerte und ausreichende Messabdeckung"
            self.increase_ready_since = None
            self.resume_ready_since = None
            return None
        if preview is None:
            self.status = "evcc-Sensor oder Ladeparameter fehlen/ungültig"
            self.increase_ready_since = None
            self.resume_ready_since = None
            return None
        snap, budget = preview
        if not self._acknowledged(snap, now):
            return None
        if self.last_change_at:
            if (now - self.last_change_at).total_seconds() < int(
                self.config.get(CONF_EVCC_STEP_S, DEFAULT_EVCC_STEP_S)
            ):
                self.status = "Warte auf Messwert-Stabilisierung nach evcc-Stellbefehl"
                return None
        mode = snap["mode_name"]
        current = snap["current_a"]
        minimum = float(self.config.get(CONF_EVCC_MIN_A, DEFAULT_EVCC_MIN_A))
        if self.owned_pause:
            if (now - self.monitor.slot).total_seconds() > 810:
                self.resume_ready_since = None
                self.status = "Warte auf neue Viertelstunde vor Wiederfreigabe"
                return None
            if mode != "off":
                self.deactivate("evcc-Modus nach V15-Pause extern geändert; Steuerung gestoppt")
                return None
            if budget.target_current_a is None or cal["at_risk"]:
                self.resume_ready_since = None
                self.status = "Ladepause: Budget reicht noch nicht für Mindeststrom"
                return None
            if self.resume_ready_since is None:
                self.resume_ready_since = now
            seconds = (now - self.resume_ready_since).total_seconds()
            stable = int(self.config.get(CONF_EVCC_STABLE_S, DEFAULT_EVCC_STABLE_S))
            if seconds < stable:
                self.status = f"Ladepause: stabile Reserve {int(seconds)}/{stable} s"
                return None
            if current > minimum:
                self.status = "Setze Mindeststrom vor Wiederfreigabe"
                return ("current", int(minimum))
            if "smart" not in snap["mode"].attributes.get("options", []):
                self.status = "evcc-Modus smart nicht verfügbar"
                return None
            self.status = "Wiederfreigabe im evcc-Modus smart"
            return ("mode", "smart")
        if mode != "smart":
            self.deactivate("evcc nicht mehr im Modus smart; V15-Steuerung gestoppt")
            return None
        if budget.target_current_a is None:
            self.increase_ready_since = None
            if self.config.get(CONF_EVCC_ALLOW_PAUSE, False) and snap["charge_w"] >= 200:
                if "off" not in snap["mode"].attributes.get("options", []):
                    self.status = "evcc-Modus off nicht verfügbar; Ladepause unmöglich"
                    return None
                self.status = "EV-Mindestladeleistung über Restbudget: Ladepause erforderlich"
                return ("mode", "off")
            if current > minimum:
                self.status = "Ladebudget unter 6 A: begrenze zuerst auf Mindeststrom"
                return ("current", int(minimum))
            self.status = "Budget unter Mindestleistung; Ladepause nicht freigegeben oder evcc lädt nicht"
            return None
        target = min(budget.target_current_a, int(self.original_current or budget.target_current_a))
        if current > target + 0.1:
            self.increase_ready_since = None
            self.status = f"Strombegrenzung nötig: {current:g} A → {target} A"
            return ("current", int(target))
        if target > current + 0.1 and not cal["at_risk"]:
            if (now - self.monitor.slot).total_seconds() > 810:
                self.increase_ready_since = None
                self.status = "Keine Stromerhöhung kurz vor Viertelstundenende"
                return None
            if self.increase_ready_since is None:
                self.increase_ready_since = now
            seconds = (now - self.increase_ready_since).total_seconds()
            stable = int(self.config.get(CONF_EVCC_STABLE_S, DEFAULT_EVCC_STABLE_S))
            if seconds < stable:
                self.status = f"Warte auf stabile Leistungsreserve {int(seconds)}/{stable} s"
                return None
            new_current = min(target, round(current) + 1)
            self.status = f"Stabile Reserve: erhöhe auf {new_current} A"
            return ("current", new_current)
        self.increase_ready_since = None
        self.status = "evcc innerhalb des Leistungsbudgets; keine Änderung"
        return None

    def evaluate(self, now, trusted, cal, grid_w):
        action = self.decide(now, trusted, cal, grid_w)
        if action is None or self.busy or self.action_pending:
            return
        self.action_pending = True
        self.hass.async_create_task(self.apply(action))

    async def apply(self, planned):
        if not self.enabled or self.busy:
            self.action_pending = False
            return
        self.busy = True
        try:
            # Recompute using the latest sensor values immediately before I/O.
            if not self.monitor.data.get("trusted_for_control"):
                return
            now = dt_util.now()
            fresh_grid = self.monitor.read_power()
            if fresh_grid is None:
                return
            fresh_cal = self.monitor.calculate_current(now, fresh_grid)
            if fresh_cal is None:
                return
            action = self.decide(now, True, fresh_cal, fresh_grid)
            if action is None or action != planned or not self.enabled:
                return
            kind, value = action
            entity = self.config[CONF_EVCC_CURRENT if kind == "current" else CONF_EVCC_MODE]
            if kind == "current":
                state = self._state(CONF_EVCC_CURRENT)
                if entity.split(".")[0] == "select":
                    option = select_option_for_amperes(state.attributes.get("options"), value)
                    if option is None:
                        self.status = f"Maximalstromoption {value} A fehlt in evcc"
                        return
                    service, data = "select_option", {"entity_id": entity, "option": option}
                else:
                    if entity.split(".")[0] != "number":
                        return
                    step_min = float(state.attributes.get("min", 0))
                    step_max = float(state.attributes.get("max", 32))
                    if not step_min <= value <= step_max:
                        self.status = "Gewünschter Ladestrom außerhalb der Entitätsgrenzen"
                        return
                    service, data = "set_value", {"entity_id": entity, "value": value}
                domain = entity.split(".")[0]
            else:
                domain, service, data = "select", "select_option", {"entity_id": entity, "option": value}
            self.last_change_at = now
            self.expected_current = value if kind == "current" else None
            self.expected_mode = value if kind == "mode" else None
            self.ack_deadline = now + timedelta(seconds=20)
            await self.hass.services.async_call(domain, service, data, blocking=True)
            if kind == "mode" and value == "off":
                self.owned_pause = True
                self.resume_ready_since = None
                self.last_action = "evcc durch V15 pausiert (Modus off)"
            elif kind == "mode" and value == "smart":
                self.owned_pause = False
                self.last_action = "evcc durch V15 wieder freigegeben (Modus smart)"
            else:
                self.last_action = f"evcc-Maximalstrom durch V15 auf {value} A gesetzt"
            _LOGGER.info(self.last_action)
        except Exception:
            _LOGGER.exception("V15 evcc action failed")
            self.deactivate("Fehler bei evcc-Schaltbefehl; V15-Steuerung gestoppt")
            self.last_action = "evcc-Stellbefehl fehlgeschlagen (siehe Protokoll)"
        finally:
            self.busy = False
            self.action_pending = False
            self.monitor.notify()
