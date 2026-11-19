"""Home Connect controller safety tests using fake HA entities (no real appliances)."""
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import AsyncMock

from test_restore_monitor import (
    FakeEntry, FakeHass, FakeState, clock, coordinator, const,
)
from v15_test_package.home_connect_support import Load, V15HomeConnectController

PAUSE = "button.washer_pause"
RESUME = "button.washer_resume"
STATE = "sensor.washer_operation_state"
PROGRAM = "select.washer_program"
REMOTE = "binary_sensor.washer_remote"
START = "binary_sensor.washer_remote_start"
LOCAL = "binary_sensor.washer_local"


class TestHomeConnectControl(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        clock.now = datetime(2026, 11, 5, 13, 7, 30, tzinfo=timezone.utc)
        self.hass = FakeHass()
        self.monitor = coordinator.V15Monitor(self.hass, FakeEntry())
        self.hass.monitor = self.monitor
        self.monitor.enabled = True
        self.monitor.simulation = False
        self.monitor.load_entities = []
        self.monitor.slot = clock.now.replace(minute=0, second=0)
        self.monitor.energy_wh = 50
        self.monitor.coverage_s = 450
        self.monitor.data = {"trusted_for_control": True, "at_risk": True}
        self.load = Load(PAUSE, STATE, RESUME, 400.0, REMOTE, START, LOCAL, PROGRAM)
        self.monitor.hc.loads = [self.load]
        self.hass.states.update({
            PAUSE: FakeState("unknown"), RESUME: FakeState("unknown"),
            STATE: FakeState("run"), PROGRAM: FakeState("cotton"),
            REMOTE: FakeState("on"), START: FakeState("on"),
            LOCAL: FakeState("off"),
        })
        self.requests = []
        self.change_state = True

        async def press(domain, service, data, blocking=False):
            self.requests.append((domain, service, data["entity_id"]))
            if self.change_state:
                if data["entity_id"] == PAUSE:
                    self.hass.states[STATE] = FakeState("pause")
                elif data["entity_id"] == RESUME:
                    self.hass.states[STATE] = FakeState("run")
        self.hass.services.async_call = press

    def arm_restore(self):
        m = self.monitor
        m.data["at_risk"] = False
        m.energy_wh = 40
        m.hc.owned[PAUSE] = (clock.now - timedelta(seconds=200), "cotton")
        m.hc_ready_since = clock.now - timedelta(seconds=100)
        m.hc_ready_name = PAUSE
        m.last_shed_time = clock.now - timedelta(seconds=200)
        self.hass.states[STATE] = FakeState("pause")
        self.hass.states["sensor.grid"] = FakeState("100", {"unit_of_measurement": "W"})

    async def test_confirmed_pause_and_resume(self):
        await self.monitor.hc.async_pause(PAUSE)
        self.assertIn(PAUSE, self.monitor.hc.owned)
        self.arm_restore()
        await self.monitor.hc.async_resume(PAUSE)
        self.assertIn(("button", "press", RESUME), self.requests)
        self.assertNotIn(PAUSE, self.monitor.hc.owned)

    async def test_unconfirmed_pause_not_owned(self):
        self.change_state = False
        await self.monitor.hc.async_pause(PAUSE)
        self.assertNotIn(PAUSE, self.monitor.hc.owned)
        clock.now += timedelta(seconds=91)
        self.monitor.hc.reconcile(clock.now)
        self.assertIn(PAUSE, self.monitor.hc.failed)

    async def test_manual_pause_not_owned_or_resumed(self):
        self.hass.states[STATE] = FakeState("pause")
        self.assertIsNone(self.monitor.hc.first_running())
        await self.monitor.hc.async_resume(PAUSE)
        self.assertEqual(self.requests, [])

    async def test_no_pause_without_remote_control(self):
        self.hass.states[REMOTE] = FakeState("off")
        await self.monitor.hc.async_pause(PAUSE)
        self.assertEqual(self.requests, [])

    async def test_no_resume_on_program_change(self):
        self.arm_restore()
        self.hass.states[PROGRAM] = FakeState("eco")
        self.monitor.hc.reconcile(clock.now)
        self.assertNotIn(PAUSE, self.monitor.hc.owned)
        await self.monitor.hc.async_resume(PAUSE)
        self.assertEqual(self.requests, [])

    async def test_no_resume_on_low_budget(self):
        self.arm_restore()
        self.hass.states["sensor.grid"] = FakeState("750", {"unit_of_measurement": "W"})
        await self.monitor.hc.async_resume(PAUSE)
        self.assertEqual(self.requests, [])

    async def test_no_resume_on_invalid_grid_measurement(self):
        self.arm_restore()
        self.hass.states["sensor.grid"] = FakeState("unavailable")
        await self.monitor.hc.async_resume(PAUSE)
        self.assertEqual(self.requests, [])

    async def test_resume_failure_not_retried(self):
        self.arm_restore()
        self.change_state = False
        await self.monitor.hc.async_resume(PAUSE)
        await self.monitor.hc.async_resume(PAUSE)
        self.assertEqual(self.requests.count(("button", "press", RESUME)), 1)

    async def test_live_disabled_blocks_commands(self):
        self.arm_restore()
        self.monitor.enabled = False
        await self.monitor.hc.async_resume(PAUSE)
        await self.monitor.hc.async_pause(PAUSE)
        self.assertEqual(self.requests, [])

    def test_restart_discards_ownership(self):
        self.arm_restore()
        fresh = V15HomeConnectController(self.monitor)
        self.assertEqual(fresh.owned, {})

if __name__ == "__main__":
    unittest.main()
