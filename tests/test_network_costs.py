"""Tariff correctness, safe gaps, month boundaries and draft provenance."""
import importlib.util
from pathlib import Path
from datetime import datetime, timedelta, timezone
import sys
import unittest

MODULE = (Path(__file__).resolve().parents[1] /
          "custom_components/v15_lastmanagement/network_costs.py")
spec = importlib.util.spec_from_file_location("network_costs", MODULE)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class TestAustrianTariffs(unittest.TestCase):
    def test_all_14_distinct_network_areas(self):
        self.assertEqual(len(mod.DRAFT_2027_NE7), 14)
        self.assertEqual(mod.DRAFT_2027_NE7["Burgenland"], (340, 510))
        self.assertEqual(mod.DRAFT_2027_NE7["Graz"], (228, 342))
        self.assertEqual(mod.DRAFT_2027_NE7["Steiermark"], (321, 482))
        self.assertEqual(mod.DRAFT_2027_NE7["Kleinwalsertal"], (583, 875))

    def test_minimum_two_kw_and_progressive_tier(self):
        # Austrian §6(2): 10 kW at first rate, remainder at second.
        self.assertEqual(mod.monthly_capacity_charge(0.5, 340, 510), 6.80)
        self.assertEqual(mod.monthly_capacity_charge(5, 340, 510), 17.00)
        self.assertEqual(mod.monthly_capacity_charge(10, 340, 510), 34.00)
        self.assertEqual(mod.monthly_capacity_charge(11, 340, 510), 39.10)

    def test_target_only_hypothetical_and_floor(self):
        self.assertEqual(mod.estimate_difference(8, 5, 340, 510), 10.20)
        self.assertEqual(mod.estimate_difference(4, 5, 340, 510), 0.00)
        self.assertEqual(mod.estimate_difference(3, 1, 340, 510), 3.40)

    def test_invalid_tariffs_refused(self):
        for bad in (float("nan"), -1, "unknown", float("inf")):
            with self.assertRaises(ValueError):
                mod.monthly_capacity_charge(5, bad, 500)


class TestPeakTracking(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2027, 1, 5, 14, 0,
                              tzinfo=timezone(timedelta(hours=1)))
        self.peak = mod.MonthlyPeak()

    def test_completed_slot_contributes_kw(self):
        end = self.start + timedelta(minutes=15)
        self.assertTrue(self.peak.record_slot(self.start, end, 1250, 899))
        self.assertEqual(self.peak.kw, 5.0)
        self.assertEqual(self.peak.count, 1)
        self.assertFalse(self.peak.record_slot(self.start, end, 1250, 899))
        self.assertEqual(self.peak.count, 1)

    def test_rejects_incomplete_measurements_and_demo(self):
        self.assertFalse(self.peak.record_slot(
            self.start, self.start+timedelta(minutes=15), 2500, 800))
        self.assertIsNone(self.peak.kw)
        self.assertFalse(self.peak.record_slot(
            self.start, self.start+timedelta(minutes=30), 2500, 899))

    def test_does_not_lose_higher_prior_peak(self):
        for i, energy in enumerate((1500, 500, 1000)):
            start = self.start + timedelta(minutes=15*i)
            self.assertTrue(self.peak.record_slot(
                start, start+timedelta(minutes=15), energy, 900))
        self.assertEqual(self.peak.kw, 6.0)
        self.assertEqual(self.peak.count, 3)

    def test_restore_only_same_month(self):
        end = self.start+timedelta(minutes=15)
        self.assertTrue(self.peak.record_slot(self.start, end, 1250, 900))
        restored = mod.MonthlyPeak()
        self.assertTrue(restored.restore(
            self.peak.month, self.peak.kw, self.peak.count,
            self.peak.last_slot, end))
        self.assertEqual(restored.kw, 5.0)
        future = datetime(2027, 2, 1, 12, 0, tzinfo=end.tzinfo)
        self.assertFalse(restored.restore(
            self.peak.month, self.peak.kw, self.peak.count,
            self.peak.last_slot, future))
        self.assertIsNone(restored.kw)


if __name__ == "__main__":
    unittest.main()
