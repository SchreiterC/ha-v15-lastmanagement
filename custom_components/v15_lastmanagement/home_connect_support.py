"""Experimental Home Connect PauseProgram/ResumeProgram adapter using Home Assistant entities only.

Cloud commands are not reliable real-time demand reduction. V15 never invokes
StopProgram or StartProgram. Ownership is ephemeral and lost on reload.
"""
from dataclasses import dataclass, replace
import logging
from homeassistant.util import dt as dt_util
from .const import (
    CONF_HC_PAUSE, CONF_HC_POWERS, CONF_RESTORE, CONF_RESTORE_MARGIN,
    CONF_RESTORE_MIN_OFF, CONF_RESTORE_STABLE, DEFAULT_RESTORE_MARGIN,
    DEFAULT_RESTORE_MIN_OFF, DEFAULT_RESTORE_STABLE,
)
from .math_v15 import quarter_start
from .restore_logic import power_headroom_ok, periods_satisfied

_LOGGER = logging.getLogger(__name__)
PLATFORM = "home_connect"
PAUSE_KEY = "BSH.Common.Command.PauseProgram"
RESUME_KEY = "BSH.Common.Command.ResumeProgram"
STATE_KEY = "BSH.Common.Status.OperationState"
PROGRAM_KEY = "BSH.Common.Root.ActiveProgram"
REMOTE_KEY = "BSH.Common.Status.RemoteControlActive"
REMOTE_START_KEY = "BSH.Common.Status.RemoteControlStartAllowed"
LOCAL_KEY = "BSH.Common.Status.LocalControlActive"
COMMAND_TIMEOUT = 90
SPACING = 60


@dataclass(frozen=True)
class Load:
    pause: str
    status: str
    resume: str | None
    watts: float
    remote: str | None
    remote_start: str | None
    local: str | None
    program: str | None


def _registry(hass):
    from homeassistant.helpers import entity_registry
    return entity_registry.async_get(hass)


def selectable_pause_buttons(hass):
    if hass is None:
        return []
    return sorted(e.entity_id for e in _registry(hass).entities.values()
                  if e.platform == PLATFORM and e.entity_id.startswith("button.")
                  and e.unique_id.endswith("-" + PAUSE_KEY) and e.disabled_by is None)


def validate_pause_buttons(hass, selected):
    registry = _registry(hass)
    for entity_id in selected:
        e = registry.async_get(entity_id)
        if (e is None or e.platform != PLATFORM or e.disabled_by is not None
                or not e.entity_id.startswith("button.")
                or not e.unique_id.endswith("-" + PAUSE_KEY)):
            return False
        prefix = e.unique_id[:-len(PAUSE_KEY)]
        if registry.async_get_entity_id("sensor", PLATFORM, prefix + STATE_KEY) is None:
            return False
    return True


def resolve_loads(hass, selected, powers):
    registry = _registry(hass)
    loads = []
    for entity_id in dict.fromkeys(selected):
        if not validate_pause_buttons(hass, [entity_id]):
            _LOGGER.warning("V15 Home Connect: invalid PauseProgram or state: %s", entity_id)
            continue
        entry = registry.async_get(entity_id)
        prefix = entry.unique_id[:-len(PAUSE_KEY)]
        def lookup(domain, key):
            return registry.async_get_entity_id(domain, PLATFORM, prefix + key)
        try:
            watts = float(powers.get(entity_id))
        except (ValueError, TypeError):
            continue
        if not 10 <= watts <= 25000:
            continue
        loads.append(Load(entity_id, lookup("sensor", STATE_KEY),
                          lookup("button", RESUME_KEY), watts,
                          lookup("binary_sensor", REMOTE_KEY),
                          lookup("binary_sensor", REMOTE_START_KEY),
                          lookup("binary_sensor", LOCAL_KEY),
                          lookup("select", PROGRAM_KEY)))
    return loads


def _good(state):
    return state is not None and state.state not in ("unavailable", "unknown", "none", "")


class V15HomeConnectController:
    def __init__(self, monitor):
        self.m = monitor
        self.loads = resolve_loads(monitor.hass, monitor.config.get(CONF_HC_PAUSE, []),
                                   monitor.config.get(CONF_HC_POWERS, {}))
        self.owned = {}       # pause button: (confirmed timestamp, active program)
        self.pending_pause = {} # pause button: (requested timestamp, active program)
        self.pending_resume = {} # pause button: requested timestamp
        self.failed = set()    # one pause attempt per incident if unconfirmed
        self.resume_attempted = set()
        self.last_action_at = None
        self.status = "Home Connect test mode" if self.loads else "Nicht konfiguriert"
        self.busy = False

    @property
    def observed_entities(self):
        return list(dict.fromkeys(x for load in self.loads for x in (
            load.status, load.pause, load.resume, load.remote, load.remote_start,
            load.local, load.program) if x))

    def _state(self, entity):
        return self.m.hass.states.get(entity) if entity else None

    def _program(self, load):
        state = self._state(load.program)
        return state.state if _good(state) else None

    def _same_program(self, load, expected):
        current = self._program(load)
        return expected is None or (current is not None and current == expected)

    def _can_control(self, load, resume=False):
        op = self._state(load.status)
        if not _good(op) or op.state != ("pause" if resume else "run"):
            return False
        button = self._state(load.resume if resume else load.pause)
        if button is None or button.state == "unavailable":
            return False
        for entity, wanted in ((load.remote, "on"), (load.local, "off")):
            if entity and (not _good(self._state(entity)) or self._state(entity).state != wanted):
                return False
        if resume and load.remote_start and (
                not _good(self._state(load.remote_start)) or
                self._state(load.remote_start).state != "on"):
            return False
        return True

    def first_running(self):
        for load in self.loads:
            if (load.pause not in self.owned and load.pause not in self.pending_pause
                    and load.pause not in self.failed and self._can_control(load)):
                return load.pause
        return None

    def reconcile(self, now):
        for i, load in enumerate(self.loads):
            name = load.pause
            op = self._state(load.status)
            mode = op.state if op else None
            if mode == "pause" and load.resume is None:
                entry = _registry(self.m.hass).async_get(name)
                if entry is not None:
                    resume = _registry(self.m.hass).async_get_entity_id(
                        "button", PLATFORM, entry.unique_id[:-len(PAUSE_KEY)] + RESUME_KEY)
                    if resume:
                        load = replace(load, resume=resume)
                        self.loads[i] = load
            pending = self.pending_pause.get(name)
            if pending:
                since, program = pending
                age = (now - since).total_seconds()
                if (mode == "pause" and 0 <= age <= COMMAND_TIMEOUT
                        and self._same_program(load, program)):
                    self.owned[name] = (now, program)
                    self.pending_pause.pop(name, None)
                    self.status = "Pause bestätigt: " + name
                elif age > COMMAND_TIMEOUT or mode in ("finished", "ready", "inactive", "error", "aborting") or not self._same_program(load, program):
                    self.pending_pause.pop(name, None)
                    self.failed.add(name)
                    self.status = "Pause nicht bestätigt: " + name
            if name in self.owned:
                if mode == "run" or mode in ("finished", "ready", "inactive", "error", "aborting") or not self._same_program(load, self.owned[name][1]):
                    self.owned.pop(name, None)
                    self.pending_resume.pop(name, None)
                    self.resume_attempted.discard(name)
                    self.status = "Zuständigkeit beendet: " + name
            if name in self.pending_resume and (now - self.pending_resume[name]).total_seconds() > COMMAND_TIMEOUT:
                self.pending_resume.pop(name, None)
                self.status = "Fortsetzung nicht bestätigt: " + name

    def _eligible(self, now, watts, cal, trusted):
        if not self.m.config.get(CONF_RESTORE) or not self.m.enabled or self.m.simulation or self.m.demo_data:
            return None
        if not trusted or watts is None or cal["at_risk"] or self.m.control_busy or self.busy:
            return None
        if self.m.pending_off or self.m.pending_on or self.pending_pause or self.pending_resume:
            return None
        if self.m.managed_off or self.m.restore_candidate:
            return None
        if 900 - (now - quarter_start(now)).total_seconds() < 90:
            return None
        if self.m.last_shed_time and (now-self.m.last_shed_time).total_seconds() < SPACING:
            return None
        if self.last_action_at and (now-self.last_action_at).total_seconds() < SPACING:
            return None
        for load in reversed(self.loads):
            if load.pause not in self.owned or load.pause in self.resume_attempted:
                continue
            if not self._can_control(load, resume=True) or not self._same_program(load, self.owned[load.pause][1]):
                continue
            margin = float(self.m.config.get(CONF_RESTORE_MARGIN, DEFAULT_RESTORE_MARGIN))
            if power_headroom_ok(watts, cal["budget_kw"], load.watts, margin):
                return load
        return None

    def evaluate(self, now, watts, cal, trusted, switch_candidate=None, switch_restore=None):
        if self.busy or self.m.action_pending or not self.m.enabled or self.m.demo_data or self.m.simulation:
            return
        if trusted and cal["at_risk"] and switch_candidate is None and not self.m.control_busy:
            name = self.first_running()
            if name is not None and (
                self.m.last_shed_time is None or
                (now-self.m.last_shed_time).total_seconds() >= 30
            ):
                self.m.action_pending = True
                self.m.hass.async_create_task(self.async_pause(name))
                return
        if switch_restore is not None or not self.owned:
            return
        load = self._eligible(now, watts, cal, trusted)
        if load is None:
            self.m.hc_ready_since = None
            self.m.hc_ready_name = None
            return
        if getattr(self.m, "hc_ready_name", None) != load.pause:
            self.m.hc_ready_name = load.pause
            self.m.hc_ready_since = now
        off_at = self.owned[load.pause][0]
        if periods_satisfied(now, off_at, self.m.hc_ready_since,
                             int(self.m.config.get(CONF_RESTORE_MIN_OFF, DEFAULT_RESTORE_MIN_OFF)),
                             int(self.m.config.get(CONF_RESTORE_STABLE, DEFAULT_RESTORE_STABLE))):
            self.m.action_pending = True
            self.m.hass.async_create_task(self.async_resume(load.pause))

    async def async_pause(self, name):
        if self.busy:
            self.m.action_pending = False
            return
        self.busy = True
        try:
            load = next((x for x in self.loads if x.pause == name), None)
            if (load is None or not self.m.enabled or self.m.simulation or self.m.demo_data
                    or not self._can_control(load) or self.m.read_power() is None):
                return
            self.m.last_shed_time = dt_util.now()
            self.pending_pause[name] = (dt_util.now(), self._program(load))
            await self.m.hass.services.async_call("button", "press", {"entity_id": name}, blocking=True)
            self.reconcile(dt_util.now())
            self.status = "Pause angefordert: " + name
        except Exception:
            self.pending_pause.pop(name, None)
            self.failed.add(name)
            self.status = "Fehler bei Pause: " + name
            _LOGGER.exception("V15 Home Connect PauseProgram failed")
        finally:
            self.busy = False
            self.m.action_pending = False
            self.m.notify()

    async def async_resume(self, name):
        if self.busy:
            self.m.action_pending = False
            return
        self.busy = True
        try:
            now = dt_util.now()
            watts = self.m.read_power()
            cal = self.m.calculate_current(now, watts) if watts is not None else None
            load = self._eligible(now, watts, cal, bool(self.m.data.get('trusted_for_control'))) if cal is not None else None
            if load is None or load.pause != name or not periods_satisfied(
                    now, self.owned[name][0], getattr(self.m, "hc_ready_since", None),
                    int(self.m.config.get(CONF_RESTORE_MIN_OFF, DEFAULT_RESTORE_MIN_OFF)),
                    int(self.m.config.get(CONF_RESTORE_STABLE, DEFAULT_RESTORE_STABLE))):
                return
            self.resume_attempted.add(name)
            self.pending_resume[name] = now
            await self.m.hass.services.async_call(
                "button", "press", {"entity_id": load.resume}, blocking=True)
            self.last_action_at = dt_util.now()
            self.reconcile(dt_util.now())
            self.status = "Fortsetzen angefordert: " + name
        except Exception:
            self.status = "Fehler bei Fortsetzen: " + name
            _LOGGER.exception("V15 Home Connect ResumeProgram failed")
        finally:
            self.busy = False
            self.m.action_pending = False
            self.m.notify()

    def deactivate(self):
        self.owned.clear()
        self.pending_pause.clear()
        self.pending_resume.clear()
        self.failed.clear()
        self.resume_attempted.clear()
