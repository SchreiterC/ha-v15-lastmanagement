"""Pure calculation and format tests for HA evcc entity control."""
import importlib.util
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'custom_components/v15_lastmanagement/evcc_logic.py'
spec=importlib.util.spec_from_file_location('v15_evcc_logic_test', SOURCE)
import sys
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)

class TestEvccLogic(unittest.TestCase):
    def test_3ph_minimum_is_4140_w(self):
        r=module.charging_budget(grid_w=5000,charging_w=4000,budget_kw=4.5,
             phases=3, voltage=230, minimum_a=6,maximum_a=16,margin_w=300)
        self.assertEqual(r.min_charge_w,4140)
        self.assertIsNone(r.target_current_a)
        self.assertEqual(r.available_charge_w, 3200)
    def test_1ph_budget(self):
        r=module.charging_budget(grid_w=3000, charging_w=1500,budget_kw=4.5,
             phases=1,voltage=230,minimum_a=6,maximum_a=16,margin_w=300)
        self.assertEqual(r.target_current_a, 11)  # 2700 / 230 = 11.7
    def test_never_exceeds_original_cap(self):
        r=module.charging_budget(grid_w=-3000,charging_w=4000,budget_kw=4.5,
             phases=3,voltage=230,minimum_a=6,maximum_a=11,margin_w=300)
        self.assertEqual(r.target_current_a,11)
    def test_high_background_consumption_blocks_current(self):
        r=module.charging_budget(grid_w=8500,charging_w=3500,budget_kw=4.5,
             phases=3,voltage=230,minimum_a=6,maximum_a=16,margin_w=300)
        self.assertIsNone(r.target_current_a)
    def test_current_select_options_exact(self):
        self.assertEqual(module.select_option_for_amperes(['6 A','7 A','16 A'],7),'7 A')
        self.assertIsNone(module.select_option_for_amperes(['6 A','8 A'],7))
        self.assertEqual(module.parse_amperes('16 A'),16)
        self.assertIsNone(module.parse_amperes('auto'))
    def test_invalid_phase_and_power(self):
        with self.assertRaises(ValueError):
            module.charging_budget(grid_w=1000,charging_w=500,budget_kw=5,
                phases=2,voltage=230,minimum_a=6,maximum_a=16,margin_w=300)
        with self.assertRaises(ValueError):
            module.charging_budget(grid_w=1000,charging_w=-50,budget_kw=5,
                phases=3,voltage=230,minimum_a=6,maximum_a=16,margin_w=300)

if __name__=='__main__':unittest.main()
