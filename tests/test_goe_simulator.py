"""Standalone fake go-e server unit tests (no HTTP listener is opened)."""
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "lab_goe/goe_simulator.py"
spec = importlib.util.spec_from_file_location("v15_fake_goe_server", SOURCE)
fake = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fake
spec.loader.exec_module(fake)


class TestFakeGoEServer(unittest.TestCase):
    def setUp(self):
        with fake.LOCK:
            fake.STATE.clear()
            fake.STATE.update(fake.DEFAULT)

    def test_initial_charge_power_and_phase_count(self):
        state = fake.snapshot()
        self.assertEqual(state["amp"], 16)
        self.assertEqual(state["frc"], 0)
        self.assertEqual(state["pnp"], 3)
        self.assertEqual(state["nrg"][11], 11040)

    def test_current_limiting_changes_power(self):
        self.assertEqual(fake.update_values({"amp": ["14"]}), {"amp": True})
        self.assertEqual(fake.snapshot()["nrg"][11], 9660)

    def test_pause_and_restore_neutral(self):
        fake.update_values({"frc": ["1"]})
        self.assertEqual(fake.snapshot()["nrg"][11], 0)
        fake.update_values({"amp": ["6"]})
        self.assertEqual(fake.snapshot()["nrg"][11], 0)
        fake.update_values({"frc": ["0"]})
        self.assertEqual(fake.snapshot()["nrg"][11], 4140)

    def test_beta6_never_sets_force_on(self):
        self.assertNotEqual(fake.update_values({"frc": ["2"]})["frc"], True)
        self.assertEqual(fake.snapshot()["frc"], 0)
        self.assertEqual(fake.update_values({"frc": ["2"]}, allow_force_on=True),
                         {"frc": True})
        self.assertEqual(fake.snapshot()["frc"], 2)

    def test_invalid_payload_cannot_change_current(self):
        for payload in ({"amp": ["0"]}, {"amp": ["true"]}, {"amp": ["64"]},
                        {"amp": ["\"NaN\""]}):
            fake.update_values(payload)
            self.assertEqual(fake.snapshot()["amp"], 16)

    def test_disconnect_stops_charging(self):
        fake.update_values({"plugged": ["false"]}, allow_force_on=True)
        self.assertEqual(fake.snapshot()["nrg"][11], 0)
        self.assertEqual(fake.snapshot()["pnp"], 0)


if __name__ == "__main__":
    unittest.main()
