"""Experimental, independently armed PV start of a Home Connect dishwasher.

No StartProgram is issued without a one-shot input_boolean, a selected
dishwasher program, positive V15 headroom, current metering and an explicit
runtime switch enable. Never attempts to start an oven or a washer.
"""
from datetime import timedelta
import logging

from homeassistant.util import dt as dt_util

from .const import (
    CONF_PV_ENABLED, CONF_PV_SELECTED, CONF_PV_ARM, CONF_PV_FORECAST,
    CONF_PV_EARLIEST, CONF_PV_DEADLINE, CONF_PV_DURATION,
    CONF_PV_MIN_WH, CONF_PV_WATTS, CONF_PV_MARGIN, CONF_PV_STABLE,
)
from .pv_start_logic import plan_window, start_allowed
from .restore_logic import power_headroom_ok

_LOGGER = logging.getLogger(__name__)

# Home Connect registry unique IDs are '<haId>-<BSH key>'.
SELECTED = "BSH.Common.Root.SelectedProgram"
OPERATION = "BSH.Common.Status.OperationState"
DOOR = "BSH.Common.Status.DoorState"
REMOTE = "BSH.Common.Status.RemoteControlActive"
REMOTE_START = "BSH.Common.Status.RemoteControlStartAllowed"
CONNECTED = "BSH.Common.Event.ApplianceConnected"


class V15PvStartController:
    def __init__(self, monitor):
        self.m = monitor
        self.configured = bool(monitor.config.get(CONF_PV_ENABLED, False))
        self.enabled = False  # Intentionally never restored after HA restart.
        self.busy = False
        # A restored live switch must never use authorization left ON
        # from the previous Home Assistant runtime.
        self.require_fresh_arm = False
        self.arm_seen_off = False
        self.last_attempt = None
        self.pending_until = None
        self.stable_since = None
        self.last_reason = "Nicht konfiguriert" if not self.configured else "PV-Start deaktiviert"
        self.planned_start = None
        self.planned_wh = None
        self.selected = None
        self.operation = None
        self.door = None
        self.remote = None
        self.remote_start = None
        self.connectivity = None
        self.device_id = None
        if self.configured:
            self.resolve()

    def resolve(self, registry=None):
        """Resolve only enabled entities belonging to the selected HA device.

        Home Connect exposes its status and connectivity entities under distinct
        BSH keys. The registry's translation keys/device class provide a safe
        fallback if an upstream release changes a BSH key. Ambiguous matches
        are refused, and entities from other appliances are never accepted.
        """
        if registry is None:
            from homeassistant.helpers import entity_registry as er
            registry = er.async_get(self.m.hass)
        selected = self.m.config.get(CONF_PV_SELECTED)
        entry = registry.async_get(selected) if selected else None
        self.selected = None
        self.operation = None
        self.door = None
        self.remote = None
        self.remote_start = None
        self.connectivity = None
        self.device_id = None
        self.missing_entities = []
        if entry is None or entry.platform != "home_connect" or entry.disabled_by is not None:
            self.last_reason = "Ausgewähltes Home-Connect-Programm nicht verfügbar"
            self.missing_entities = ["selected_program"]
            return
        if (entry.domain != "select" or not entry.unique_id.endswith("-" + SELECTED)
                or entry.device_id is None):
            self.last_reason = "Nur Home-Connect-Programmauswahl zulässig"
            self.missing_entities = ["selected_program"]
            return
        prefix = entry.unique_id[:-len(SELECTED)]
        device_id = entry.device_id
        peers = [
            entity for entity in registry.entities.values()
            if entity.platform == "home_connect" and entity.device_id == device_id
            and entity.disabled_by is None
        ]

        def lookup(domain, key, translation_key=None, device_class=None):
            candidate_id = registry.async_get_entity_id(domain, "home_connect", prefix + key)
            if candidate_id:
                candidate = registry.async_get(candidate_id)
                if (candidate is not None and candidate.device_id == device_id
                        and candidate.platform == "home_connect"
                        and candidate.disabled_by is None):
                    return candidate_id
            # Never fall back to fuzzy, localized names or another device.
            matches = [
                entity.entity_id for entity in peers
                if entity.domain == domain
                and ((translation_key is not None
                      and entity.translation_key == translation_key)
                     or (device_class is not None
                         and entity.original_device_class == device_class))
            ]
            return matches[0] if len(matches) == 1 else None

        self.selected = selected
        self.device_id = device_id
        self.operation = lookup("sensor", OPERATION, "operation_state")
        self.door = lookup("sensor", DOOR, "door")
        self.remote = lookup("binary_sensor", REMOTE, "remote_control")
        self.remote_start = lookup("binary_sensor", REMOTE_START, "remote_start")
        self.connectivity = lookup(
            "binary_sensor", CONNECTED, device_class="connectivity"
        )
        self.missing_entities = [
            name for name, value in (
                ("operation_state", self.operation),
                ("door", self.door),
                ("remote_control", self.remote),
                ("remote_start", self.remote_start),
                ("connectivity", self.connectivity),
            ) if value is None
        ]
        if self.missing_entities:
            self.last_reason = "Home-Connect-Zuordnung unvollständig: " + ", ".join(
                self.missing_entities
            )
        else:
            self.last_reason = "Home-Connect-Entitäten erfolgreich zugeordnet"

    @property
    def observed_entities(self):
        return list(dict.fromkeys(e for e in (
            self.selected, self.operation, self.door, self.remote, self.remote_start,
            self.connectivity, self.m.config.get(CONF_PV_ARM),
            self.m.config.get(CONF_PV_FORECAST)) if e))

    def deactivate(self, reason="PV-Start deaktiviert"):
        self.enabled = False
        self.stable_since = None
        self.require_fresh_arm = False
        self.arm_seen_off = False
        self.last_reason = reason

    def restore_live_enable(self):
        """Resume monitoring, but require new OFF -> ON authorization."""
        self.enabled = True
        self.require_fresh_arm = True
        self.arm_seen_off = False
        self.stable_since = None
        self.last_reason = "Warte nach Neustart auf neue Startfreigabe"

    def _fresh_arm_ready(self):
        """An old ON after restart cannot grant consent to start."""
        if not self.require_fresh_arm:
            return True
        arm = self._state(self.m.config.get(CONF_PV_ARM))
        if arm is not None and arm.state == "off":
            self.arm_seen_off = True
        if not self.arm_seen_off or arm is None or arm.state != "on":
            self.last_reason = "Nach Neustart: Startfreigabe AUS und erneut EIN schalten"
            return False
        self.require_fresh_arm = False
        return True

    def _state(self, entity):
        return self.m.hass.states.get(entity) if entity else None

    def _is(self, entity, expected):
        state = self._state(entity)
        return state is not None and state.state == expected

    def _ready(self):
        if not all((self.selected, self.operation, self.door, self.remote,
                    self.remote_start, self.connectivity, self.device_id)):
            return False
        selected = self._state(self.selected)
        # Deliberately restrict first release to dishwashers.
        if (selected is None or not selected.state.startswith("dishcare_dishwasher_program_")):
            return False
        door = self._state(self.door)
        return (self._is(self.operation, "ready")
                and door is not None and door.state in ("closed", "locked")
                and self._is(self.remote, "on")
                and self._is(self.remote_start, "on")
                and self._is(self.connectivity, "on"))

    def _plan(self, now):
        state = self._state(self.m.config.get(CONF_PV_FORECAST))
        forecast = state.attributes.get("wh_period_15m") if state else None
        result = plan_window(
            forecast, now, self.m.config[CONF_PV_EARLIEST],
            self.m.config[CONF_PV_DEADLINE],
            int(self.m.config[CONF_PV_DURATION]),
        )
        self.planned_start = result.start.isoformat() if result.start else None
        self.planned_wh = round(result.energy_wh) if result.valid_windows else None
        return result

    def evaluate(self, now, watts, cal, trusted):
        """Read-only evaluation; schedule only after all safety checks hold."""
        if not self.configured or self.busy:
            return
        if self.pending_until is not None:
            if self._is(self.operation, "run"):
                self.last_reason = "Programmstart bestätigt"
                self.pending_until = None
            elif now >= self.pending_until:
                self.last_reason = "Start nicht bestätigt; manuelle Prüfung erforderlich"
                self.pending_until = None
                self.m.hass.async_create_task(self._notify_failure())
            return
        plan = self._plan(now)
        if not self.enabled or self.m.simulation or self.m.demo_data:
            self.stable_since = None
            return
        if not self._is(self.m.config.get(CONF_PV_ARM), "on"):
            self.last_reason = "Warte auf einmalige Startfreigabe"
            self.stable_since = None
            return
        if not self._fresh_arm_ready():
            self.stable_since = None
            return
        if not self._ready():
            self.last_reason = "Gerät ist nicht fernstartbereit"
            self.stable_since = None
            return
        if not start_allowed(
            now, plan, self.m.config[CONF_PV_EARLIEST],
            self.m.config[CONF_PV_DEADLINE], float(self.m.config[CONF_PV_MIN_WH]),
        ):
            self.last_reason = "Warte auf PV-Zeitfenster oder spätesten Start"
            self.stable_since = None
            return
        if not trusted or watts is None or cal is None or cal["at_risk"]:
            self.last_reason = "V15-Messung oder Viertelstundenprognose nicht freigegeben"
            self.stable_since = None
            return
        if (self.m.action_pending or self.m.control_busy or self.m.pending_off
                or self.m.pending_on or self.m.hc.busy or self.m.hc.pending_pause
                or self.m.hc.pending_resume):
            self.last_reason = "Eine andere V15-Schalthandlung läuft"
            self.stable_since = None
            return
        if self.m.last_shed_time and (now - self.m.last_shed_time).total_seconds() < 60:
            self.last_reason = "Warte nach einer Lastabschaltung"
            self.stable_since = None
            return
        expected = float(self.m.config[CONF_PV_WATTS])
        margin = float(self.m.config[CONF_PV_MARGIN])
        if not power_headroom_ok(watts, cal["budget_kw"], expected, margin):
            self.last_reason = "Zu wenig V15-Restbudget für Programmstart"
            self.stable_since = None
            return
        if self.stable_since is None:
            self.stable_since = now
        if (now - self.stable_since).total_seconds() < int(self.m.config[CONF_PV_STABLE]):
            self.last_reason = "Warte auf stabile Leistungsreserve"
            return
        if not self.m.hass.services.has_service("home_connect", "start_selected_program"):
            self.last_reason = "Home-Connect-Startdienst nicht verfügbar"
            return
        self.last_reason = "Einmaliger Programmstart wird angefordert"
        self.busy = True
        self.m.hass.async_create_task(self.async_start())

    async def async_start(self):
        """Consume consent BEFORE the remote command. No automatic retries."""
        try:
            now = dt_util.now()
            watts = self.m.read_power()
            cal = self.m.calculate_current(now, watts) if watts is not None else None
            if (not self.enabled or self.m.simulation or self.m.demo_data
                    or not self.m.data.get("trusted_for_control")
                    or watts is None or cal is None or cal["at_risk"]
                    or not self._is(self.m.config.get(CONF_PV_ARM), "on")
                    or self.require_fresh_arm
                    or not self._ready()):
                return
            plan = self._plan(now)
            if not start_allowed(now, plan, self.m.config[CONF_PV_EARLIEST],
                                 self.m.config[CONF_PV_DEADLINE],
                                 float(self.m.config[CONF_PV_MIN_WH])):
                return
            if not power_headroom_ok(
                watts, cal["budget_kw"], float(self.m.config[CONF_PV_WATTS]),
                float(self.m.config[CONF_PV_MARGIN]),
            ):
                return
            if self.stable_since is None or (now - self.stable_since).total_seconds() < int(self.m.config[CONF_PV_STABLE]):
                return
            self.last_attempt = now.isoformat()
            await self.m.hass.services.async_call(
                "input_boolean", "turn_off",
                {"entity_id": self.m.config[CONF_PV_ARM]}, blocking=True)
            if self._is(self.m.config.get(CONF_PV_ARM), "on"):
                self.last_reason = "Startfreigabe konnte nicht zurückgesetzt werden"
                return
            if not self.enabled or self.m.simulation or self.m.demo_data or not self._ready():
                self.last_reason = "PV-Start nach Freigabeprüfung deaktiviert"
                return
            self.pending_until = dt_util.now() + timedelta(minutes=3)
            await self.m.hass.services.async_call(
                "home_connect", "start_selected_program",
                {"device_id": self.device_id}, blocking=True)
            self.last_reason = "Start angefordert; warte auf Gerätebestätigung"
        except Exception:
            _LOGGER.exception("V15 PV start failed; no automatic retry")
            self.pending_until = None
            self.last_reason = "Home-Connect-Start fehlgeschlagen; keine Wiederholung"
            await self._notify_failure()
        finally:
            self.busy = False
            self.stable_since = None
            self.m.notify()

    async def _notify_failure(self):
        await self.m.hass.services.async_call(
            "persistent_notification", "create",
            {"title": "V15 PV-Start nicht bestätigt",
             "message": "Der Home-Connect-Programmstart wurde nicht bestätigt. "
                        "Bitte das Gerät und die Startfreigabe manuell prüfen."},
            blocking=False,
        )
