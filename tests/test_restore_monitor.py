"""Runtime decisions with minimal HA stubs (NOT a full HA integration test)."""
import asyncio
from datetime import datetime, timedelta, timezone
import importlib
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "v15_lastmanagement"


def module(name, **attributes):
    result = types.ModuleType(name)
    result.__dict__.update(attributes)
    sys.modules[name] = result
    return result


# Minimal HA API stubs for testing the coordinator in ordinary CI Python.
module("homeassistant")
module("homeassistant.const", STATE_ON="on", STATE_OFF="off")
module("homeassistant.core", callback=lambda func: func)
module("homeassistant.helpers")
module("homeassistant.helpers.event",
       async_track_state_change_event=lambda *args: lambda: None,
       async_track_time_interval=lambda *args: lambda: None)
module("homeassistant.util")
clock = types.SimpleNamespace(now=datetime(2026, 11, 5, 13, 7, 30, tzinfo=timezone.utc))
module("homeassistant.util.dt", now=lambda: clock.now, utcnow=lambda: clock.now)
package = module("v15_test_package")
package.__path__ = [str(ROOT)]
coordinator = importlib.import_module("v15_test_package.coordinator")
const = importlib.import_module("v15_test_package.const")


class FakeState:
    def __init__(self, value, attrs=None, age=0):
        self.state = value
        self.attributes = attrs or {}
        self.last_updated = clock.now - timedelta(seconds=age)


class FakeServices:
    def __init__(self, hass):
        self.hass = hass
        self.calls = []
        self.device_responds = True

    async def async_call(self, domain, action, data, blocking=False):
        self.calls.append((domain, action, data["entity_id"], blocking))
        if self.device_responds:
            entity_id = data["entity_id"]
            self.hass.states[entity_id] = FakeState("off" if action == "turn_off" else "on")
            if self.hass.monitor:
                self.hass.monitor._on_load_change(types.SimpleNamespace(data={
                    "entity_id": entity_id,
                    "new_state": self.hass.states[entity_id],
                }))


class FakeHass:
    def __init__(self):
        self.states = {
            "sensor.grid": FakeState("450", {"unit_of_measurement": "W"}),
            "switch.lamp": FakeState("on"),
        }
        self.services = FakeServices(self)
        self.monitor = None
        self.tasks = []

    def async_create_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.append(task)
        return task


class FakeEntry:
    entry_id = "sample_entry"
    data = {const.CONF_GRID: "sensor.grid", const.CONF_LIMIT: 1.0,
            const.CONF_RESERVE: 0.2, const.CONF_REVERSED: False,
            const.CONF_LOADS: ["switch.lamp"]}

    def __init__(self, auto=True):
        self.options = {
            const.CONF_RESTORE: auto,
            const.CONF_RESTORE_POWERS: {"switch.lamp": 200},
            const.CONF_RESTORE_MARGIN: 100,
            const.CONF_RESTORE_MIN_OFF: 180,
            const.CONF_RESTORE_STABLE: 90,
        }


class TestMonitorRestoration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        clock.now = datetime(2026, 11, 5, 13, 7, 30, tzinfo=timezone.utc)
        self.hass = FakeHass()
        self.monitor = coordinator.V15Monitor(self.hass, FakeEntry())
        self.hass.monitor = self.monitor
        m = self.monitor
        m.enabled = True
        m.simulation = False
        m.slot = datetime(2026, 11, 5, 13, 0, tzinfo=timezone.utc)
        m.energy_wh = 50.0
        m.coverage_s = 450.0
        m.data = {"trusted_for_control": True, "restore_ready": True}

    def prepare_owned_off(self):
        m = self.monitor
        self.hass.states["switch.lamp"] = FakeState("off")
        m.managed_off["switch.lamp"] = clock.now - timedelta(seconds=200)
        m.restore_candidate = "switch.lamp"
        m.restore_since = clock.now - timedelta(seconds=120)
        m.last_shed_time = clock.now - timedelta(seconds=200)

    async def test_live_shedding_marks_only_confirmed_off(self):
        m = self.monitor
        m.data = {"trusted_for_control": True, "at_risk": True}
        await m.async_shed()
        self.assertEqual(self.hass.states["switch.lamp"].state, "off")
        self.assertIn("switch.lamp", m.managed_off)
        self.assertEqual(self.hass.services.calls[0][1], "turn_off")

    async def test_no_ownership_when_off_not_confirmed(self):
        m = self.monitor
        self.hass.services.device_responds = False
        m.data = {"trusted_for_control": True, "at_risk": True}
        await m.async_shed()
        self.assertNotIn("switch.lamp", m.managed_off)
        self.assertIn("switch.lamp", m.pending_off)

    async def test_one_restore_of_own_load(self):
        self.prepare_owned_off()
        await self.monitor.async_restore()
        self.assertEqual(self.hass.services.calls[-1][1], "turn_on")
        self.assertEqual(self.hass.states["switch.lamp"].state, "on")
        self.assertFalse(self.monitor.managed_off)
        self.assertIn("bestätigt", self.monitor.last_action)
        await self.monitor.async_restore()
        self.assertEqual(len(self.hass.services.calls), 1)

    async def test_no_restore_when_live_off(self):
        self.prepare_owned_off()
        self.monitor.enabled = False
        await self.monitor.async_restore()
        self.assertEqual(self.hass.services.calls, [])

    async def test_no_restore_when_not_opted_in(self):
        self.prepare_owned_off()
        self.monitor.config[const.CONF_RESTORE] = False
        await self.monitor.async_restore()
        self.assertEqual(self.hass.services.calls, [])

    async def test_no_restore_when_untrusted(self):
        self.prepare_owned_off()
        self.monitor.data["trusted_for_control"] = False
        await self.monitor.async_restore()
        self.assertEqual(self.hass.services.calls, [])

    async def test_no_restore_when_power_invalid(self):
        self.prepare_owned_off()
        self.hass.states["sensor.grid"] = FakeState("unknown")
        await self.monitor.async_restore()
        self.assertEqual(self.hass.services.calls, [])

    async def test_no_restore_when_budget_insufficient(self):
        self.prepare_owned_off()
        self.hass.states["sensor.grid"] = FakeState("750", {"unit_of_measurement": "W"})
        await self.monitor.async_restore()
        self.assertEqual(self.hass.services.calls, [])

    async def test_no_restore_when_min_off_not_reached(self):
        self.prepare_owned_off()
        self.monitor.managed_off["switch.lamp"] = clock.now - timedelta(seconds=100)
        await self.monitor.async_restore()
        self.assertEqual(self.hass.services.calls, [])

    async def test_manual_on_clears_ownership(self):
        self.prepare_owned_off()
        self.hass.states["switch.lamp"] = FakeState("on")
        self.monitor._on_load_change(types.SimpleNamespace(data={
            "entity_id": "switch.lamp", "new_state": self.hass.states["switch.lamp"]
        }))
        self.assertFalse(self.monitor.managed_off)

    async def test_untracked_manual_off_never_restored(self):
        self.hass.states["switch.lamp"] = FakeState("off")
        self.assertEqual(self.monitor._last_managed_off(), None)
        await self.monitor.async_restore()
        self.assertEqual(self.hass.services.calls, [])

    async def test_restart_does_not_claim_old_switches(self):
        self.prepare_owned_off()
        new_monitor = coordinator.V15Monitor(self.hass, FakeEntry())
        self.assertFalse(new_monitor.managed_off)
        self.assertFalse(new_monitor.enabled)

    async def test_update_automatically_queues_restore_when_ready(self):
        self.prepare_owned_off()
        self.monitor.coverage_s = 450.0
        self.monitor.last_time = None
        self.monitor.update()
        await asyncio.sleep(0)
        self.assertTrue(any(call[1] == "turn_on" for call in self.hass.services.calls))

    async def test_update_rejects_low_coverage(self):
        self.prepare_owned_off()
        self.monitor.coverage_s = 100.0
        self.monitor.update()
        await asyncio.sleep(0)
        self.assertFalse(self.hass.services.calls)
        self.assertFalse(self.monitor.data["trusted_for_control"])

    async def test_quarter_rollover_restarts_coverage_and_stability(self):
        self.prepare_owned_off()
        clock.now = datetime(2026, 11, 5, 13, 15, 2, tzinfo=timezone.utc)
        self.monitor.update()
        await asyncio.sleep(0)
        self.assertFalse(self.hass.services.calls)
        self.assertIsNone(self.monitor.restore_since)
        self.assertFalse(self.monitor.data["trusted_for_control"])

    async def test_unconfirmed_on_is_not_retried(self):
        self.prepare_owned_off()
        self.hass.services.device_responds = False
        await self.monitor.async_restore()
        self.assertEqual(len(self.hass.services.calls), 1)
        self.assertFalse(self.monitor.managed_off)
        self.assertIn("switch.lamp", self.monitor.pending_on)
        await self.monitor.async_restore()
        self.assertEqual(len(self.hass.services.calls), 1)

    async def test_forecast_above_target_blocks_restoration(self):
        self.prepare_owned_off()
        self.monitor.energy_wh = 210.0  # allowed: 200 Wh
        await self.monitor.async_restore()
        self.assertFalse(self.hass.services.calls)

    async def test_no_restore_near_quarter_boundary(self):
        self.prepare_owned_off()
        clock.now = datetime(2026, 11, 5, 13, 14, 0, tzinfo=timezone.utc)
        self.monitor.restore_since = clock.now - timedelta(seconds=120)
        self.monitor.managed_off["switch.lamp"] = clock.now - timedelta(seconds=200)
        self.monitor.last_shed_time = clock.now - timedelta(seconds=200)
        await self.monitor.async_restore()
        self.assertEqual(self.hass.services.calls, [])

    async def test_demo_never_restores_hardware(self):
        self.prepare_owned_off()
        self.monitor.demo_data = True
        await self.monitor.async_restore()
        self.assertEqual(self.hass.services.calls, [])


if __name__ == "__main__":
    unittest.main()
