"""Standalone restoration arithmetic tests."""
import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "custom_components" / "v15_lastmanagement" / "restore_logic.py"
spec = importlib.util.spec_from_file_location("v15_restore", module_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestRestoreLogic(unittest.TestCase):
    def test_sufficient_budget(self):
        self.assertTrue(mod.power_headroom_ok(450, 0.8, 200, 100))

    def test_insufficient_budget(self):
        self.assertFalse(mod.power_headroom_ok(600, 0.8, 200, 100))

    def test_no_budget(self):
        self.assertFalse(mod.power_headroom_ok(100, None, 200, 100))
        self.assertFalse(mod.power_headroom_ok(100, 0, 200, 100))

    def test_invalid_power(self):
        self.assertFalse(mod.power_headroom_ok(100, 4.5, 0, 100))
        self.assertFalse(mod.power_headroom_ok(float("nan"), 4.5, 100, 100))
        self.assertFalse(mod.power_headroom_ok(100, 4.5, 100, -50))

    def test_export_not_counted_as_headroom(self):
        # -5 kW export must not be treated as +5 kW restorative headroom.
        self.assertFalse(mod.power_headroom_ok(-5000, 0.8, 900, 100))

    def test_both_periods_required(self):
        now = datetime(2026, 11, 5, tzinfo=timezone.utc)
        self.assertFalse(mod.periods_satisfied(now, now-timedelta(seconds=200), now-timedelta(seconds=30), 180, 90))
        self.assertFalse(mod.periods_satisfied(now, now-timedelta(seconds=100), now-timedelta(seconds=120), 180, 90))
        self.assertTrue(mod.periods_satisfied(now, now-timedelta(seconds=200), now-timedelta(seconds=120), 180, 90))


if __name__ == "__main__":
    unittest.main()
