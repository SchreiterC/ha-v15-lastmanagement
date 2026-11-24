"""No physical Home Connect devices: fake HA service and time for PV starts."""
from datetime import datetime, timedelta, timezone
import asyncio
import unittest

from test_restore_monitor import FakeEntry, FakeHass, FakeState, clock, coordinator, const

SELECTED = "select.dishwasher_selected_program"
OPERATION = "sensor.dishwasher_operation"
DOOR = "sensor.dishwasher_door"
REMOTE = "binary_sensor.dishwasher_remote"
REMOTE_START = "binary_sensor.dishwasher_remote_start"
ARM = "input_boolean.dishwasher_start"
FORECAST = "sensor.pv_forecast"


class TestPvStartController(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        clock.now = datetime(2026, 11, 24, 12, 7, 30, tzinfo=timezone.utc)
        self.hass = FakeHass()
        self.monitor = coordinator.V15Monitor(self.hass, FakeEntry())
        self.hass.monitor = self.monitor
        self.monitor.config.update({
            const.CONF_PV_ENABLED: True,
            const.CONF_PV_SELECTED: SELECTED,
            const.CONF_PV_ARM: ARM,
            const.CONF_PV_FORECAST: FORECAST,
            const.CONF_PV_EARLIEST: "12:00",
            const.CONF_PV_DEADLINE: "13:00",
            const.CONF_PV_DURATION: 60,
            const.CONF_PV_MIN_WH: 100,
            const.CONF_PV_WATTS: 200,
            const.CONF_PV_MARGIN: 100,
            const.CONF_PV_STABLE: 90,
        })
        self.monitor.pv.configured = True
        p = self.monitor.pv
        p.enabled = True
        p.selected = SELECTED
        p.operation = OPERATION
        p.door = DOOR
        p.remote = REMOTE
        p.remote_start = REMOTE_START
        p.device_id = "virtual-device"
        p.connectivity = None
        self.monitor.simulation = False
        self.monitor.slot = clock.now.replace(minute=0, second=0, microsecond=0)
        self.monitor.energy_wh = 50
        self.monitor.coverage_s = 450
        self.monitor.data = {"trusted_for_control": True}
        values = {
            (clock.now.replace(hour=12, minute=0, second=0, microsecond=0) +
             timedelta(minutes=15*i)).isoformat(): 100
            for i in range(24)
        }
        self.hass.states.update({
            SELECTED: FakeState("dishcare_dishwasher_program_eco_50"),
            OPERATION: FakeState("ready"),
            DOOR: FakeState("closed"),
            REMOTE: FakeState("on"),
            REMOTE_START: FakeState("on"),
            ARM: FakeState("on"),
            FORECAST: FakeState("1", {"wh_period_15m": values}),
        })
        self.calls = []
        self.fail_start = False
        self.hass.services.has_service = lambda domain, action: True
        async def service(domain, action, data, blocking=False):
            self.calls.append((domain, action, dict(data)))
            if domain == "input_boolean":
                self.hass.states[ARM] = FakeState("off")
            if domain == "home_connect":
                if self.fail_start:
                    raise RuntimeError("cloud failure")
                self.hass.states[OPERATION] = FakeState("run")
        self.hass.services.async_call = service

    def calculate(self):
        w = self.monitor.read_power()
        return w, self.monitor.calculate_current(clock.now, w)

    async def test_one_shot_arm_consumed_and_confirmed(self):
        p = self.monitor.pv
        p.stable_since = clock.now - timedelta(seconds=100)
        w, cal = self.calculate()
        p.evaluate(clock.now, w, cal, True)
        await asyncio.gather(*self.hass.tasks)
        self.assertEqual(sum(x[0] == "home_connect" for x in self.calls), 1)
        self.assertEqual(self.hass.states[ARM].state, "off")
        p.evaluate(clock.now, w, cal, True)
        self.assertEqual(p.last_reason, "Programmstart bestätigt")
        self.assertIsNone(p.pending_until)

    async def test_never_start_without_manual_arm(self):
        p = self.monitor.pv
        self.hass.states[ARM] = FakeState("off")
        p.stable_since = clock.now - timedelta(seconds=100)
        w, cal = self.calculate()
        p.evaluate(clock.now, w, cal, True)
        self.assertFalse(self.hass.tasks)

    async def test_missing_door_or_remote_never_start(self):
        for entity, value in [(DOOR, "open"), (REMOTE_START, "off")]:
            p = self.monitor.pv
            self.hass.states[entity] = FakeState(value)
            p.stable_since = clock.now - timedelta(seconds=100)
            w, cal = self.calculate()
            p.evaluate(clock.now, w, cal, True)
            self.assertFalse(self.hass.tasks)
            self.hass.states[entity] = FakeState("closed" if entity == DOOR else "on")

    async def test_oven_program_is_forbidden(self):
        self.hass.states[SELECTED] = FakeState("cooking_oven_program_heating_mode_hot_air")
        p = self.monitor.pv
        p.stable_since = clock.now - timedelta(seconds=100)
        w, cal = self.calculate()
        p.evaluate(clock.now, w, cal, True)
        self.assertFalse(self.hass.tasks)

    async def test_no_start_with_untrusted_or_low_budget(self):
        p = self.monitor.pv
        p.stable_since = clock.now - timedelta(seconds=100)
        w, cal = self.calculate()
        p.evaluate(clock.now, w, cal, False)
        self.assertFalse(self.hass.tasks)
        self.hass.states["sensor.grid"] = FakeState("790", {"unit_of_measurement":"W"})
        w, cal = self.calculate()
        p.evaluate(clock.now, w, cal, True)
        self.assertFalse(self.hass.tasks)

    async def test_disabled_after_new_controller(self):
        from v15_test_package.pv_start import V15PvStartController
        self.monitor.config[const.CONF_PV_ENABLED] = False
        fresh = V15PvStartController(self.monitor)
        self.assertFalse(fresh.enabled)

    async def test_cloud_exception_consumes_authorization_and_does_not_retry(self):
        self.fail_start = True
        p = self.monitor.pv
        p.stable_since = clock.now - timedelta(seconds=100)
        w, cal = self.calculate()
        p.evaluate(clock.now, w, cal, True)
        await asyncio.gather(*self.hass.tasks)
        self.assertEqual(self.hass.states[ARM].state, "off")
        self.assertEqual(sum(x[0] == "home_connect" for x in self.calls), 1)


if __name__ == "__main__":
    unittest.main()
