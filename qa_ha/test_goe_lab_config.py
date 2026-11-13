"""Static validation of the optional two-container go-e test lab.

No Docker daemon, network connection or go-e wallbox required.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_goe_lab_docker_compose_is_localhost_bound():
    compose = yaml.safe_load((ROOT / "lab_goe/compose.yaml").read_text())
    services = compose["services"]
    assert set(services) == {"goe-simulator", "homeassistant-goe-lab"}
    ha = services["homeassistant-goe-lab"]
    fake = services["goe-simulator"]
    assert "127.0.0.1:8125:8123" in ha["ports"]
    assert "127.0.0.1:8126:80" in fake["ports"]
    assert "../custom_components/v15_lastmanagement:" in " ".join(ha["volumes"])
    assert fake["networks"]["v15_goe"]["ipv4_address"] == "172.28.201.10"
    assert compose["networks"]["v15_goe"]["ipam"]["config"][0]["subnet"] == "172.28.201.0/24"


def test_goe_lab_uses_only_fake_charger_and_synthetic_meter():
    config = yaml.safe_load((ROOT / "lab_goe/config/configuration.yaml").read_text())
    assert config["input_number"]["v15_goe_grundlast_w"]["initial"] == -6000
    rest = config["rest"][0]
    assert rest["resource"].startswith("http://172.28.201.10/api/status")
    assert rest["scan_interval"] == 5
    assert all("test_heartbeat" in row.get("attributes", {})
               for row in config["template"][0]["sensor"])
    assert all("unit_of_measurement" in row for row in config["template"][0]["sensor"])
