"""Experimental go-e Charger API v2 backend, reusing V15's evcc safety logic.

Only local RFC1918 IPv4 hosts are supported. No cloud API, direct device
discovery, OCPP, phase switching, 'force on', or automatic enable on reload.
Controlling the same charger through evcc and go-e simultaneously is unsafe.
"""
from datetime import timedelta
import ipaddress
import json
import logging
import math
from types import SimpleNamespace

from aiohttp import ClientTimeout
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    CONF_GOE_CONFIGURED, CONF_GOE_HOST, CONF_GOE_EXCLUSIVE,
    CONF_GOE_PHASES, CONF_GOE_MIN_A, CONF_GOE_MAX_A,
    CONF_GOE_MARGIN_W, CONF_GOE_STABLE_S, CONF_GOE_STEP_S,
    CONF_GOE_ALLOW_PAUSE, CONF_EVCC_CONFIGURED, CONF_EVCC_MIN_A,
    CONF_EVCC_MAX_A, CONF_EVCC_FIXED_PHASES, CONF_EVCC_VOLTAGE,
    CONF_EVCC_MARGIN_W, CONF_EVCC_STABLE_S, CONF_EVCC_STEP_S,
    CONF_EVCC_ALLOW_PAUSE,
    DEFAULT_EVCC_MIN_A, DEFAULT_EVCC_MAX_A, DEFAULT_EVCC_VOLTAGE,
    DEFAULT_EVCC_MARGIN_W, DEFAULT_EVCC_STABLE_S, DEFAULT_EVCC_STEP_S,
)
from .evcc_control import V15EvccController

_LOGGER = logging.getLogger(__name__)
_RFC1918 = tuple(ipaddress.ip_network(n) for n in
                 ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
_STATUS_FILTER = "amp,frc,nrg,pnp"
_POLL_INTERVAL = 5
_MAX_STATUS_AGE = 15


def validated_local_ipv4(host):
    """Reject remote hosts, URLs, credentials and unexpected ports.

    The go-e HTTP API v2 is plaintext on the local network. This preliminary
    backend therefore supports RFC1918 IPv4 only, without authentication.
    """
    try:
        addr = ipaddress.ip_address(str(host).strip())
    except ValueError as exc:
        raise ValueError("go-e requires a local IPv4 address, not a URL") from exc
    if not isinstance(addr, ipaddress.IPv4Address) or not any(
        addr in subnet for subnet in _RFC1918
    ):
        raise ValueError("go-e address must be in a private RFC1918 IPv4 network")
    return str(addr)


def parse_goe_status(raw, configured_phases):
    """Parse documented API v2 keys; reject incomplete and unsafe readings.

    nrg: U(L1,L2,L3,N), I(L1,L2,L3), P(L1,L2,L3,N,total), pf(...).
    The total charging power is nrg[11], in watts.
    """
    if not isinstance(raw, dict):
        return None
    amp = raw.get("amp")
    frc = raw.get("frc")
    nrg = raw.get("nrg")
    pnp = raw.get("pnp")
    if (type(amp) is not int or not 6 <= amp <= 32 or
            type(frc) is not int or frc not in (0, 1, 2) or
            not isinstance(nrg, list) or len(nrg) < 12):
        return None
    try:
        power = float(nrg[11])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(power) or not 0 <= power <= 30000:
        return None
    if configured_phases not in (1, 3):
        return None
    if pnp is not None and (type(pnp) is not int or pnp not in (0, 1, 3)):
        return None
    # 3 phases are always assumed for a three-phase-capable installation;
    # this cannot underestimate the required charging power.
    if configured_phases == 1 and pnp == 3:
        return None
    phases = max(configured_phases, pnp or configured_phases)
    name = {0: "smart", 1: "off", 2: "now"}[frc]
    return {
        "current_a": amp, "charge_w": power, "phases": phases,
        "mode_name": name,
        "mode": SimpleNamespace(attributes={"options": ["smart", "off", "now"]}),
    }


class GoeLocalAPI:
    """Narrow, unauthenticated local HTTP API v2 client; write allowlist."""

    def __init__(self, hass, host):
        self.hass = hass
        self.host = validated_local_ipv4(host)
        self.base = f"http://{self.host}"

    async def _get(self, path, params):
        session = async_get_clientsession(self.hass)
        async with session.get(
            f"{self.base}{path}", params=params,
            timeout=ClientTimeout(total=3),
        ) as response:
            response.raise_for_status()
            data = await response.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid go-e response")
        return data

    async def status(self):
        return await self._get("/api/status", {"filter": _STATUS_FILTER})

    async def set_value(self, key, value):
        if key not in ("amp", "frc") or type(value) is not int:
            raise ValueError("Only go-e amp/frc integer updates are allowed")
        if key == "amp" and not 6 <= value <= 32:
            raise ValueError("go-e current outside 6..32 A")
        if key == "frc" and value not in (0, 1):
            raise ValueError("V15 never forces charging on")
        result = await self._get("/api/set", {key: json.dumps(value)})
        if result.get(key) is not True:
            raise ValueError(f"go-e refused {key} command")


class V15GoeController(V15EvccController):
    """Direct go-e backend using the same budget/ramp/ack engine as evcc.

    V15 controls either an evcc backend OR this go-e backend per config entry.
    An explicit external-regulator warning must be acknowledged before go-e
    live control can be activated.
    """

    def __init__(self, monitor):
        super().__init__(monitor)
        base = monitor.config
        self.configured = bool(base.get(CONF_GOE_CONFIGURED, False))
        self.config = {
            **base,
            CONF_EVCC_CONFIGURED: self.configured,
            CONF_EVCC_MIN_A: base.get(CONF_GOE_MIN_A, DEFAULT_EVCC_MIN_A),
            CONF_EVCC_MAX_A: base.get(CONF_GOE_MAX_A, DEFAULT_EVCC_MAX_A),
            CONF_EVCC_FIXED_PHASES: base.get(CONF_GOE_PHASES, 3),
            CONF_EVCC_VOLTAGE: DEFAULT_EVCC_VOLTAGE,
            CONF_EVCC_MARGIN_W: base.get(CONF_GOE_MARGIN_W, DEFAULT_EVCC_MARGIN_W),
            CONF_EVCC_STABLE_S: base.get(CONF_GOE_STABLE_S, DEFAULT_EVCC_STABLE_S),
            CONF_EVCC_STEP_S: base.get(CONF_GOE_STEP_S, DEFAULT_EVCC_STEP_S),
            CONF_EVCC_ALLOW_PAUSE: base.get(CONF_GOE_ALLOW_PAUSE, False),
        }
        self.api = GoeLocalAPI(self.hass, base[CONF_GOE_HOST]) if self.configured else None
        self.status = "go-e-Regelung ausgeschaltet" if self.configured else "go-e nicht konfiguriert"
        self.last_action = "Noch keine go-e-Aktion"
        self._latest = None
        self._seen_at = None
        self._poll_busy = False
        self._unsub_poll = None
        self._running = False

    @property
    def observed_entities(self):
        return []  # Direct HTTP API v2, not HA entity updates.

    def _snapshot(self):
        if self._latest is None or self._seen_at is None:
            return None
        age = (dt_util.utcnow() - self._seen_at).total_seconds()
        if age < -5 or age > _MAX_STATUS_AGE:
            return None
        return parse_goe_status(
            self._latest, int(self.config.get(CONF_EVCC_FIXED_PHASES, 3))
        )

    async def async_start(self):
        if not self.configured:
            return
        self._running = True
        self._unsub_poll = async_track_time_interval(
            self.hass, self._schedule_poll, timedelta(seconds=_POLL_INTERVAL)
        )
        await self.async_poll()

    @callback
    def _schedule_poll(self, _now):
        if self._running and not self._poll_busy:
            self.hass.async_create_task(self.async_poll())

    async def async_poll(self):
        if not self._running or self._poll_busy:
            return
        self._poll_busy = True
        try:
            raw = await self.api.status()
            parsed = parse_goe_status(
                raw, int(self.config.get(CONF_EVCC_FIXED_PHASES, 3))
            )
            if parsed is None:
                raise ValueError("go-e status missing amp/frc/nrg/pnp or invalid phases")
            self._latest = raw
            self._seen_at = dt_util.utcnow()
        except Exception as exc:
            self._latest = None
            self._seen_at = None
            if self.enabled:
                self.deactivate("go-e-Messwerte/API nicht erreichbar; Steuerung gestoppt")
            else:
                self.status = "go-e-Messwerte/API nicht erreichbar"
            _LOGGER.warning("V15 go-e local API read failed: %s", exc)
        finally:
            self._poll_busy = False
            if self._running:
                self.monitor.update()

    async def async_stop(self):
        self._running = False
        if self._unsub_poll:
            self._unsub_poll()
            self._unsub_poll = None
        self.deactivate("go-e nach HA-Neustart/Reload ausgeschaltet; Gerät manuell prüfen")

    def activate(self):
        if not self.configured or not self._running:
            raise ValueError("go-e ist nicht konfiguriert oder nicht erreichbar")
        if not self.monitor.config.get(CONF_GOE_EXCLUSIVE, False):
            raise ValueError("Zuerst andere Wallbox-Regler deaktivieren und dies in den Optionen bestätigen")
        if self.monitor.demo_data:
            raise ValueError("Künstliche V15-Demo vor Aktivierung deaktivieren")
        if self.monitor.evcc.enabled:
            raise ValueError("evcc-Steuerung bereits aktiv: go-e darf nicht gleichzeitig regeln")
        snap = self._snapshot()
        if snap is None:
            raise ValueError("go-e-Livedaten fehlen oder sind veraltet")
        if snap["mode_name"] != "smart":
            raise ValueError("go-e muss vor Aktivierung im Neutralzustand (frc=0) sein")
        self.enabled = True
        self.owned_pause = False
        self.original_current = snap["current_a"]
        self.last_confirmed_current = snap["current_a"]
        self.last_confirmed_mode = "smart"
        self.expected_current = None
        self.expected_mode = None
        self.ack_deadline = None
        self.increase_ready_since = None
        self.resume_ready_since = None
        self.status = "go-e-Steuerung aktiv"

    def decide(self, now, trusted, cal, grid_w):
        result = super().decide(now, trusted, cal, grid_w)
        self.status = self.status.replace("evcc", "go-e")
        return result

    async def apply(self, planned):
        if not self.enabled or self.busy or not self._running:
            self.action_pending = False
            return
        self.busy = True
        try:
            if not self.monitor.data.get("trusted_for_control"):
                return
            now = dt_util.now()
            grid = self.monitor.read_power()
            if grid is None:
                return
            cal = self.monitor.calculate_current(now, grid)
            if cal is None:
                return
            # Read back the charger's latest state BEFORE committing a write.
            raw = await self.api.status()
            if parse_goe_status(raw, int(self.config[CONF_EVCC_FIXED_PHASES])) is None:
                self.deactivate("go-e-Status vor Stellbefehl ungültig")
                return
            self._latest = raw
            self._seen_at = dt_util.utcnow()
            action = self.decide(now, True, cal, grid)
            if action is None or action != planned or not self.enabled:
                return
            kind, value = action
            if kind == "current":
                key, target = "amp", int(value)
            else:
                key, target = "frc", {"smart": 0, "off": 1}[value]
            self.last_change_at = now
            self.expected_current = value if kind == "current" else None
            self.expected_mode = value if kind == "mode" else None
            self.ack_deadline = now + timedelta(seconds=20)
            await self.api.set_value(key, target)
            if kind == "mode" and value == "off":
                self.owned_pause = True
                self.resume_ready_since = None
                self.last_action = "go-e durch V15 pausiert (frc=1)"
            elif kind == "mode" and value == "smart":
                self.owned_pause = False
                self.last_action = "go-e durch V15 wieder neutral freigegeben (frc=0)"
            else:
                self.last_action = f"go-e-Ladestrom durch V15 auf {value} A gesetzt"
            _LOGGER.info(self.last_action)
        except Exception:
            _LOGGER.exception("V15 go-e write failed")
            self.deactivate("go-e-Schaltbefehl/API fehlgeschlagen; Steuerung gestoppt")
            self.last_action = "go-e-Stellbefehl fehlgeschlagen; Gerät manuell prüfen"
        finally:
            self.busy = False
            self.action_pending = False
            self.monitor.notify()
