"""go-e controller state-machine tests with a fake HTTP API and HA stubs.

Never connects to a real charger or a Home Assistant instance.
"""
import copy
from datetime import datetime, timedelta, timezone
import unittest

from test_restore_monitor import FakeEntry, FakeHass, FakeState, clock, coordinator, const


def response(amp=16, frc=0, power=11040):
    values = [0] * 16
    values[11] = power
    return {"amp": amp, "frc": frc, "nrg": values, "pnp": 3}


class FakeAPI:
    def __init__(self, status=None):
        self.raw = status or response()
        self.writes = []
        self.fail = False

    async def status(self):
        if self.fail:
            raise OSError("Synthetic local go-e API outage")
        return copy.deepcopy(self.raw)

    async def set_value(self, key, value):
        if self.fail:
            raise OSError("Synthetic go-e command outage")
        assert key in ("amp", "frc")
        assert key != "frc" or value in (0, 1)
        self.writes.append((key, value))
        self.raw[key] = value
        if key == "frc" and value == 1:
            self.raw["nrg"][11] = 0
        if key == "frc" and value == 0:
            self.raw["nrg"][11] = 4140
        if key == "amp" and self.raw["frc"] == 0:
            self.raw["nrg"][11] = value * 3 * 230


class TestGoeController(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        clock.now = datetime(2026, 11, 5, 13, 7, 30, tzinfo=timezone.utc)
        e = FakeEntry()
        e.options.update({
            const.CONF_EVCC_CONFIGURED: False,
            const.CONF_GOE_CONFIGURED: True,
            const.CONF_GOE_HOST: "192.168.1.50",
            const.CONF_GOE_EXCLUSIVE: True,
            const.CONF_GOE_PHASES: 3,
            const.CONF_GOE_MIN_A: 6,
            const.CONF_GOE_MAX_A: 16,
            const.CONF_GOE_MARGIN_W: 300,
            const.CONF_GOE_STABLE_S: 90,
            const.CONF_GOE_STEP_S: 30,
            const.CONF_GOE_ALLOW_PAUSE: True,
        })
        self.hass = FakeHass()
        self.monitor = coordinator.V15Monitor(self.hass, e)
        self.hass.monitor = self.monitor
        self.monitor.simulation = False
        self.monitor.slot = datetime(2026, 11, 5, 13, 0, tzinfo=timezone.utc)
        self.monitor.data = {"trusted_for_control": True}
        self.cal = {"budget_kw": 4.5, "at_risk": False}
        self.monitor.calculate_current = lambda now, watts: self.cal
        self.monitor.read_power = lambda: self.grid
        self.grid = 5040
        self.g = self.monitor.goe
        self.api = FakeAPI()
        self.g.api = self.api
        self.g._latest = copy.deepcopy(self.api.raw)
        self.g._seen_at = clock.now
        self.g._running = True

    def advance(self, seconds):
        clock.now += timedelta(seconds=seconds)
        self.g._latest = copy.deepcopy(self.api.raw)
        self.g._seen_at = clock.now

    def test_safe_start_and_read_only_preview(self):
        self.assertFalse(self.g.enabled)
        self.assertFalse(self.monitor.evcc.configured)
        self.assertIs(self.monitor.charger, self.g)
        self.assertIsNone(self.g.decide(clock.now, True, self.cal, self.grid))
        self.assertEqual(self.g.target, 14)
        self.assertEqual(self.api.writes, [])

    def test_reject_activation_if_other_regulators_not_confirmed_off(self):
        self.monitor.config[const.CONF_GOE_EXCLUSIVE] = False
        with self.assertRaises(ValueError):
            self.g.activate()
        self.assertEqual(self.api.writes, [])

    def test_manual_force_state_never_taken_over(self):
        for frc in (1, 2):
            with self.subTest(frc=frc):
                self.api.raw["frc"] = frc
                self.advance(0)
                with self.assertRaises(ValueError):
                    self.g.activate()
                self.assertFalse(self.g.enabled)
        self.assertEqual(self.api.writes, [])

    def test_stale_or_invalid_goe_status_blocks_activation(self):
        self.g._seen_at -= timedelta(seconds=30)
        with self.assertRaises(ValueError):
            self.g.activate()
        self.g._seen_at = clock.now
        self.api.raw["nrg"][11] = -1
        self.advance(0)
        with self.assertRaises(ValueError):
            self.g.activate()

    async def test_current_reduced_through_fake_goe_api(self):
        self.g.activate()
        self.assertEqual(
            self.g.decide(clock.now, True, self.cal, 5040), ("current", 14)
        )
        await self.g.apply(("current", 14))
        self.assertEqual(self.api.writes, [("amp", 14)])
        self.assertEqual(self.api.raw["amp"], 14)
        self.advance(5)
        self.assertTrue(self.g._acknowledged(self.g._snapshot(), clock.now))
        self.assertEqual(self.g.last_confirmed_current, 14)

    async def test_pause_then_resume_to_neutral_only_after_six_amp(self):
        self.grid = 12540
        self.g.activate()
        self.assertEqual(
            self.g.decide(clock.now, True, self.cal, self.grid),
            ("mode", "off")
        )
        await self.g.apply(("mode", "off"))
        self.assertTrue(self.g.owned_pause)
        self.assertEqual(self.api.raw["frc"], 1)
        self.grid = -9000
        self.advance(31)
        self.assertIsNone(self.g.decide(clock.now, True, self.cal, self.grid))
        self.advance(91)
        self.assertEqual(
            self.g.decide(clock.now, True, self.cal, self.grid), ("current", 6)
        )
        await self.g.apply(("current", 6))
        self.assertEqual(self.api.raw["frc"], 1)
        self.assertEqual(self.api.raw["amp"], 6)
        self.advance(31)
        self.assertEqual(
            self.g.decide(clock.now, True, self.cal, self.grid),
            ("mode", "smart")
        )
        await self.g.apply(("mode", "smart"))
        self.assertEqual(self.api.raw["frc"], 0)
        self.assertEqual(
            self.api.writes, [("frc", 1), ("amp", 6), ("frc", 0)]
        )
        self.assertFalse(self.g.owned_pause)

    def test_manual_amperes_override_disables_controller(self):
        self.g.activate()
        self.api.raw["amp"] = 12
        self.advance(1)
        self.assertIsNone(self.g.decide(clock.now, True, self.cal, self.grid))
        self.assertFalse(self.g.enabled)
        self.assertIn("extern", self.g.status)
        self.assertEqual(self.api.writes, [])

    def test_force_on_by_external_controller_disables_v15(self):
        self.g.activate()
        self.api.raw["frc"] = 2
        self.advance(1)
        self.assertIsNone(self.g.decide(clock.now, True, self.cal, self.grid))
        self.assertFalse(self.g.enabled)

    async def test_api_outage_disables_live_control_without_write(self):
        self.g.activate()
        self.api.fail = True
        await self.g.async_poll()
        self.assertFalse(self.g.enabled)
        self.assertEqual(self.api.writes, [])
        self.assertIsNone(self.g._latest)

    async def test_reload_does_not_restore_pause_or_live_control(self):
        self.g.activate()
        self.grid = 12540
        await self.g.apply(("mode", "off"))
        self.assertEqual(self.api.raw["frc"], 1)
        await self.g.async_stop()
        self.assertFalse(self.g.enabled)
        self.assertEqual(self.api.raw["frc"], 1)
        self.assertEqual(self.api.writes, [("frc", 1)])

    def test_mutual_exclusion_rejects_both_backend_configs(self):
        e = FakeEntry()
        e.options.update({
            const.CONF_EVCC_CONFIGURED: True,
            const.CONF_GOE_CONFIGURED: True,
            const.CONF_GOE_HOST: "192.168.1.50",
        })
        with self.assertRaises(ValueError):
            coordinator.V15Monitor(FakeHass(), e)


if __name__ == "__main__":
    unittest.main()
