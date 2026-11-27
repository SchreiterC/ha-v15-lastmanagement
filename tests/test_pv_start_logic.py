"""Unit tests for PV window math and start-time policy (no Home Assistant runtime)."""
import importlib.util
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone

MODULE = Path(__file__).resolve().parents[1] / "custom_components" / "v15_lastmanagement" / "pv_start_logic.py"
spec = importlib.util.spec_from_file_location("pv_start_logic", MODULE)
# Dataclasses require a registered module, as in a regular import.
import sys
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
plan_window = mod.plan_window
start_allowed = mod.start_allowed


class TestPvWindow(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 24, 12, 2, tzinfo=timezone(timedelta(hours=1)))
        begin = self.now.replace(hour=12, minute=0, second=0, microsecond=0)
        self.forecast = {
            (begin + timedelta(minutes=15 * i)).isoformat(): 100
            for i in range(40)
        }

    def test_selects_full_valid_window_and_is_ready_now(self):
        plan = plan_window(self.forecast, self.now, "12:00", "13:00", 60)
        self.assertEqual(plan.start.hour, 12)
        self.assertEqual(plan.energy_wh, 400)
        self.assertTrue(start_allowed(self.now, plan, "12:00", "13:00", 350))

    def test_future_peak_is_preferred(self):
        key = (self.now.replace(hour=12, minute=45, second=0, microsecond=0)).isoformat()
        self.forecast[key] = 900
        plan = plan_window(self.forecast, self.now, "12:00", "13:00", 30)
        self.assertEqual((plan.start.hour, plan.start.minute), (12, 30))
        self.assertFalse(start_allowed(self.now, plan, "12:00", "13:00", 200))

    def test_missing_and_negative_intervals_are_rejected(self):
        self.forecast.pop(self.now.replace(hour=12, minute=0, second=0, microsecond=0).isoformat())
        self.forecast[self.now.replace(hour=12, minute=15, second=0, microsecond=0).isoformat()] = -1
        plan = plan_window(self.forecast, self.now, "12:00", "12:15", 60)
        self.assertEqual(plan.valid_windows, 0)
        self.assertIsNone(plan.start)

    def test_deadline_waives_pv_but_never_time_guard(self):
        now = self.now.replace(hour=13, minute=1)
        missing = plan_window(None, now, "12:00", "13:00", 60)
        self.assertTrue(start_allowed(now, missing, "12:00", "13:00", 1500))
        self.assertFalse(start_allowed(now.replace(minute=15), missing, "12:00", "13:00", 1500))
        self.assertFalse(start_allowed(self.now.replace(hour=11), missing, "12:00", "13:00", 1500))

    def test_invalid_time_and_duration(self):
        with self.assertRaises(ValueError):
            mod.parse_clock("25:00")
        self.assertIsNone(plan_window(self.forecast, self.now, "12:00", "13:00", 37).start)

    def test_nonfinite_forecast_refused(self):
        self.forecast[self.now.replace(hour=12, minute=0, second=0, microsecond=0).isoformat()] = float("nan")
        result = plan_window(self.forecast, self.now, "12:00", "12:00", 60)
        self.assertIsNone(result.start)


if __name__ == "__main__":
    unittest.main()
