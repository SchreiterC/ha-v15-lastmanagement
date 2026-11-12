#!/usr/bin/env python3
"""Run V15/evcc deterministic 15-minute simulations without real Home Assistant.

Uses production calculation/controller code from the adjoining custom_component.
No network, no real services, no Home Assistant credentials.
"""
import argparse
import asyncio
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_evcc_scenarios import VirtualTestCase  # noqa: E402


SCENARIOS = {
    "pv_drop_and_recovery": [
        (120, -9000, True), (290, 2500, True), (900, -9000, True),
    ],
    "meter_outage": [
        (120, -9000, True), (260, 2500, True), (440, -9000, False),
        (900, -9000, True),
    ],
    "high_background": [
        (900, 3000, True), (1800, 3000, True),
    ],
    "sunny_30min": [
        (1800, -9500, True),
    ],
}


async def simulate(scenario, output):
    # Isolated HA model and actual V15Monitor/V15EvccController.
    test = VirtualTestCase("test_pv_loss_causes_pause_and_pv_return_allows_resume")
    test.setUp()
    await test.run_scenario(SCENARIOS[scenario])
    path = Path(output)
    path.mkdir(parents=True, exist_ok=True)
    trace = path / f"{scenario}_trace.csv"
    with trace.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(test.log[0].keys()))
        writer.writeheader()
        writer.writerows(test.log)
    commands = path / f"{scenario}_commands.csv"
    with commands.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_utc", "entity_id", "value"])
        for stamp, entity, value in test.hass.calls:
            writer.writerow([stamp.isoformat(), entity, value])
    print(f"Szenario: {scenario}")
    print(f"Simulierte Messpunkte: {len(test.log)}")
    print(f"Simulierte Stellbefehle: {len(test.hass.calls)}")
    for t, entity, value in test.hass.calls:
        print(f"  {t.isoformat()}  {entity} -> {value}")
    print(f"Messwerte: {trace}")
    print(f"Befehle: {commands}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS.keys(), default="pv_drop_and_recovery")
    parser.add_argument("--output", default=str(ROOT / "simulator-output"))
    args = parser.parse_args()
    asyncio.run(simulate(args.scenario, args.output))


if __name__ == "__main__":
    main()
