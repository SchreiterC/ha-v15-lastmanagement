"""Deterministic, accelerated 15-minute evcc scenarios, with no real HA/evcc I/O.

Uses the actual V15 monitor and evcc controller, but a fake HA state registry,
service recorder and a simulated grid meter / charging load. It is not a full
Home Assistant integration test and cannot validate real charger latencies.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import unittest

from test_restore_monitor import FakeState, FakeEntry, FakeHass, clock, const, coordinator


START = datetime(2026, 11, 10, 13, 0, 0, tzinfo=timezone.utc)


class VirtualEvcc:
    """Minimal physical model of a 3-phase EV connected to evcc's smart mode."""

    def __init__(self, current=16, phases=3):
        self.current = current
        self.phases = phases
        self.mode = "smart"
        self.plugged = True

    @property
    def charging_w(self):
        if not self.plugged or self.mode != "smart":
            return 0
        return self.current * self.phases * 230


class VirtualHomeAssistant:
    """Record evcc commands; never forward them to a real HA instance."""

    def __init__(self, evcc):
        self.evcc = evcc
        self.states = {
            "sensor.grid": FakeState("0", {"unit_of_measurement": "W"}),
            "sensor.evcc_power": FakeState("0", {"unit_of_measurement": "W"}),
            "sensor.phases": FakeState(str(evcc.phases)),
            "select.evcc_max": FakeState(str(evcc.current), {
                "options": [str(i) for i in range(6, 17)]}),
            "select.evcc_mode": FakeState(evcc.mode, {
                "options": ["off", "smart", "now"]}),
        }
        self.calls = []
        self.tasks = []
        self.services = self

    async def async_call(self, domain, service, data, blocking=False):
        # Accept only the two evcc-related select operations. A wrong service
        # must fail the test rather than silently appearing to succeed.
        if domain != "select" or service != "select_option":
            raise AssertionError(f"Unexpected service call: {domain}.{service}")
        entity, value = data["entity_id"], str(data["option"])
        if entity == "select.evcc_max":
            if value not in self.states[entity].attributes["options"]:
                raise AssertionError(f"Unsupported evcc current: {value}")
            self.evcc.current = int(value)
        elif entity == "select.evcc_mode":
            if value not in ("off", "smart", "now"):
                raise AssertionError(f"Unsupported evcc mode: {value}")
            self.evcc.mode = value
        else:
            raise AssertionError(f"Unexpected entity: {entity}")
        self.states[entity] = FakeState(value, self.states[entity].attributes)
        self.calls.append((clock.now, entity, value))

    def async_create_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.append(task)
        return task


class VirtualTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        clock.now = START
        self.evcc = VirtualEvcc()
        self.hass = VirtualHomeAssistant(self.evcc)
        data = {
            const.CONF_GRID: "sensor.grid", const.CONF_LIMIT: 5.0,
            const.CONF_RESERVE: 0.5, const.CONF_REVERSED: False,
            const.CONF_LOADS: [],
        }
        options = {
            const.CONF_EVCC_CONFIGURED: True,
            const.CONF_EVCC_CURRENT: "select.evcc_max",
            const.CONF_EVCC_MODE: "select.evcc_mode",
            const.CONF_EVCC_POWER: "sensor.evcc_power",
            const.CONF_EVCC_PHASES: "sensor.phases",
            const.CONF_EVCC_FIXED_PHASES: 3,
            const.CONF_EVCC_MIN_A: 6,
            const.CONF_EVCC_MAX_A: 16,
            const.CONF_EVCC_VOLTAGE: 230,
            const.CONF_EVCC_MARGIN_W: 300,
            const.CONF_EVCC_STABLE_S: 90,
            const.CONF_EVCC_STEP_S: 30,
            const.CONF_EVCC_ALLOW_PAUSE: True,
            const.CONF_STALE: 120,
        }
        class Entry:
            entry_id = "simulation-only"
        entry = Entry()
        entry.data = data
        entry.options = options
        self.monitor = coordinator.V15Monitor(self.hass, entry)
        self.monitor.simulation = False
        self.monitor.evcc.activate()
        self.log = []

    async def tick(self, seconds, background_w, sensor_ok=True):
        clock.now = START + timedelta(seconds=seconds)
        charging = self.evcc.charging_w
        grid_w = float(background_w) + charging
        if sensor_ok:
            self.hass.states["sensor.grid"] = FakeState(str(grid_w), {"unit_of_measurement": "W"})
            self.hass.states["sensor.evcc_power"] = FakeState(str(charging), {"unit_of_measurement": "W"})
        else:
            self.hass.states["sensor.grid"] = FakeState("unavailable", {"unit_of_measurement": "W"})
        self.monitor.update()
        await asyncio.sleep(0)
        self.log.append({
            "second": seconds, "grid_w": grid_w, "background_w": background_w,
            "charge_w": charging, "current": self.evcc.current,
            "mode": self.evcc.mode, "trusted": self.monitor.data.get("trusted_for_control"),
            "projected_kw": self.monitor.data.get("projected_kw"),
            "status": self.monitor.evcc.status,
        })

    async def run_scenario(self, schedule, step=5):
        end = max(end for end, _, _ in schedule)
        for second in range(0, end, step):
            current_interval = next((seg for seg in schedule if seg[0] > second), None)
            if current_interval is None:
                raise AssertionError("Incomplete schedule")
            _, background_w, valid = current_interval
            await self.tick(second, background_w, valid)

    async def test_pv_loss_causes_pause_and_pv_return_allows_resume(self):
        # Solar surplus allows 16A at start, then solar disappears and comes
        # back in the SAME 15-minute interval; fast-forward simulated time.
        await self.run_scenario([
            (120, -9000, True),
            (290, 2500, True),
            (900, -9000, True),
        ])
        actions = [(t, ent, value) for t, ent, value in self.hass.calls]
        self.assertTrue(any(ent == "select.evcc_mode" and val == "off"
                            for _, ent, val in actions), actions)
        self.assertTrue(any(ent == "select.evcc_mode" and val == "smart"
                            for _, ent, val in actions), actions)
        self.assertFalse(any(ent == "select.evcc_mode" and val == "now"
                             for _, ent, val in actions))
        self.assertTrue(all(6 <= int(value) <= 16
                            for _, ent, value in actions if ent == "select.evcc_max"))

    async def test_invalid_grid_reading_never_commands_extra_current(self):
        await self.run_scenario([
            (120, -9000, True),
            (260, 2500, True),
            (440, -9000, False),
        ])
        outage_start = START + timedelta(seconds=260)
        self.assertFalse(any(time >= outage_start for time, _, _ in self.hass.calls))

    async def test_restart_does_not_inherit_active_control(self):
        await self.run_scenario([(200, 2500, True)])
        new_monitor = coordinator.V15Monitor(self.hass, self.monitor.entry)
        self.assertFalse(new_monitor.evcc.enabled)
        self.assertFalse(new_monitor.enabled)
        new_monitor.update()
        await asyncio.sleep(0)
        self.assertFalse(new_monitor.evcc.enabled)

    async def test_manually_changed_mode_revokes_controller_control(self):
        await self.run_scenario([(200, -9000, True)])
        self.evcc.mode = "now"
        self.hass.states["select.evcc_mode"] = FakeState("now", {
            "options": ["off", "smart", "now"]})
        await self.tick(200, -9000)
        self.assertFalse(self.monitor.evcc.enabled)
        action_count = len(self.hass.calls)
        await self.tick(210, 2500)
        self.assertEqual(len(self.hass.calls), action_count)


if __name__ == "__main__":
    unittest.main()
