"""Pure go-e input validation tests. No Home Assistant or network required."""
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/v15_lastmanagement/goe_logic.py"
spec = importlib.util.spec_from_file_location("v15_goe_logic_test", SOURCE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def raw(amp=16, frc=0, power=11040, pnp=3):
    readings = [0] * 16
    readings[11] = power
    return {"amp": amp, "frc": frc, "nrg": readings, "pnp": pnp}


class TestGoeLogic(unittest.TestCase):
    def test_only_private_ipv4_lan_is_allowed(self):
        for host in ("10.0.5.2", "172.16.7.3", "172.31.9.20", "192.168.1.50"):
            self.assertEqual(module.validated_local_ipv4(host), host)

    def test_reject_public_loopback_dns_urls_credentials_and_ports(self):
        for host in (
            "8.8.8.8", "127.0.0.1", "::1", "169.254.2.4",
            "http://192.168.1.50", "192.168.1.50:80",
            "go-e.local", "10.0.0.1@evil.com", "192.169.1.50",
            "172.32.0.2", "0.0.0.0",
        ):
            with self.subTest(host=host), self.assertRaises(ValueError):
                module.validated_local_ipv4(host)

    def test_power_and_mode_mapping(self):
        s = module.parse_goe_status(raw(), 3)
        self.assertEqual(s["charge_w"], 11040)
        self.assertEqual(s["current_a"], 16)
        self.assertEqual(s["phases"], 3)
        self.assertEqual(s["mode_name"], "smart")
        self.assertEqual(module.parse_goe_status(raw(frc=1), 3)["mode_name"], "off")
        self.assertEqual(module.parse_goe_status(raw(frc=2), 3)["mode_name"], "now")

    def test_do_not_underestimate_three_phase_charging(self):
        self.assertEqual(module.parse_goe_status(raw(pnp=1), 3)["phases"], 3)
        self.assertEqual(module.parse_goe_status(raw(pnp=0), 3)["phases"], 3)
        self.assertIsNone(module.parse_goe_status(raw(pnp=3), 1))

    def test_reject_invalid_schema_and_power(self):
        candidates = [
            None, {}, [], {"amp": 16, "frc": 0},
            raw(amp=True), raw(amp=4), raw(amp=33),
            raw(frc=True), raw(frc=-1), raw(frc=3),
            raw(power=-1), raw(power=1e100), raw(power=float("nan")),
            raw(pnp=2), raw(pnp="3"),
        ]
        for candidate in candidates:
            with self.subTest(payload=candidate):
                self.assertIsNone(module.parse_goe_status(candidate, 3))

    def test_reject_invalid_phase_configuration(self):
        self.assertIsNone(module.parse_goe_status(raw(), 2))


if __name__ == "__main__":
    unittest.main()
