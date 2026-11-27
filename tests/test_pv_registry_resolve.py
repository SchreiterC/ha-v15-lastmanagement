"""Registry-resolution regression tests for Home Connect dishwasher PV start."""
import unittest
from types import SimpleNamespace

from test_restore_monitor import FakeEntry, FakeHass, coordinator

KEYS = {
    "select": "BSH.Common.Root.SelectedProgram",
    "operation": "BSH.Common.Status.OperationState",
    "door": "BSH.Common.Status.DoorState",
    "remote": "BSH.Common.Status.RemoteControlActive",
    "remote_start": "BSH.Common.Status.RemoteControlStartAllowed",
    "connected": "BSH.Common.Event.ApplianceConnected",
}


class FakeRegistry:
    def __init__(self, records):
        self.entities = {x.entity_id: x for x in records}
        self.by_key = {
            (x.domain, x.platform, x.unique_id): x.entity_id
            for x in records
        }

    def async_get(self, entity_id):
        return self.entities.get(entity_id)

    def async_get_entity_id(self, domain, platform, unique_id):
        return self.by_key.get((domain, platform, unique_id))


def record(entity_id, unique, device="device-a", translation=None, device_class=None):
    return SimpleNamespace(
        entity_id=entity_id,
        domain=entity_id.split(".")[0],
        platform="home_connect",
        unique_id=unique,
        device_id=device,
        translation_key=translation,
        original_device_class=device_class,
        disabled_by=None,
    )


class TestPvRegistryResolve(unittest.TestCase):
    def setUp(self):
        m = coordinator.V15Monitor(FakeHass(), FakeEntry())
        m.config.update({"pv_start_configured": True, "pv_selected_program": "select.neff_program"})
        self.pv = m.pv
        self.pv.configured = True
        self.entries = [
            record("select.neff_program", "abc-" + KEYS["select"], translation="selected_program"),
            record("sensor.neff_state", "abc-" + KEYS["operation"], translation="operation_state"),
            record("sensor.neff_door", "abc-" + KEYS["door"], translation="door"),
            record("binary_sensor.neff_remote", "abc-" + KEYS["remote"], translation="remote_control"),
            record("binary_sensor.neff_remote_start", "abc-" + KEYS["remote_start"], translation="remote_start"),
            record("binary_sensor.neff_online", "abc-" + KEYS["connected"], device_class="connectivity"),
        ]

    def test_resolves_all_default_entities(self):
        self.pv.resolve(FakeRegistry(self.entries))
        self.assertEqual(self.pv.missing_entities, [])
        self.assertEqual(self.pv.connectivity, "binary_sensor.neff_online")
        self.assertEqual(self.pv.device_id, "device-a")

    def test_registry_translation_fallback_for_known_device(self):
        changed = []
        for e in self.entries:
            if e.translation_key in ("door", "operation_state", "remote_control", "remote_start"):
                e = SimpleNamespace(**{**vars(e), "unique_id": e.unique_id.replace("abc-", "abc-v2-")})
            changed.append(e)
        self.pv.resolve(FakeRegistry(changed))
        self.assertEqual(self.pv.missing_entities, [])

    def test_reports_exact_missing_entity(self):
        remaining = [e for e in self.entries if e.entity_id != "binary_sensor.neff_online"]
        self.pv.resolve(FakeRegistry(remaining))
        self.assertEqual(self.pv.missing_entities, ["connectivity"])

    def test_never_uses_other_device_entity(self):
        changed = []
        for e in self.entries:
            if e.entity_id == "sensor.neff_door":
                e = SimpleNamespace(**{**vars(e), "device_id": "device-b"})
            changed.append(e)
        self.pv.resolve(FakeRegistry(changed))
        self.assertIn("door", self.pv.missing_entities)

    def test_ambiguous_metadata_is_rejected(self):
        changed = [x for x in self.entries if x.entity_id != "sensor.neff_door"]
        changed += [
            record("sensor.neff_door_1", "abc-v2-DoorA", translation="door"),
            record("sensor.neff_door_2", "abc-v2-DoorB", translation="door"),
        ]
        self.pv.resolve(FakeRegistry(changed))
        self.assertIn("door", self.pv.missing_entities)


if __name__ == "__main__":
    unittest.main()
