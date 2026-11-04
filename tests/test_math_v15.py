"""Tests for standalone arithmetic; no Home Assistant imports needed."""
import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / 'custom_components' / 'v15_lastmanagement' / 'math_v15.py'
spec = importlib.util.spec_from_file_location('v15_math', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestV15Math(unittest.TestCase):
    def test_quarter_alignment(self):
        for minute, expected in [(0, 0), (14, 0), (15, 15), (29, 15), (30, 30), (44, 30), (45, 45), (59, 45)]:
            t = datetime(2026, 11, 4, 13, minute, 31, tzinfo=timezone.utc)
            self.assertEqual(module.quarter_start(t).minute, expected)
            self.assertEqual(module.quarter_start(t).second, 0)

    def test_uniform_five_kw(self):
        d = module.calculate(625, 450, 5000, 5, .5)
        self.assertAlmostEqual(d['measured_kw'], 5)
        self.assertAlmostEqual(d['projected_kw'], 5)
        self.assertTrue(d['at_risk'])
        self.assertLessEqual(d['budget_kw'], 4.5)

    def test_capped_budget(self):
        d = module.calculate(10, 899, 720, 5, .5)
        self.assertLessEqual(d['budget_kw'], 4.5)
        self.assertGreaterEqual(d['budget_kw'], 0)

    def test_no_budget_if_energy_exhausted(self):
        d = module.calculate(1500, 700, 500, 5, .5)
        self.assertEqual(d['budget_kw'], 0)
        self.assertTrue(d['at_risk'])

    def test_negative_import_clamped(self):
        d = module.calculate(0, 300, -1000, 5, .5)
        self.assertEqual(d['projected_kw'], 0)

    def test_invalid_reserve(self):
        with self.assertRaises(ValueError):
            module.calculate(0, 300, 1000, 5, 5)

if __name__ == '__main__':
    unittest.main()
