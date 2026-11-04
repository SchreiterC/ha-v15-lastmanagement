"""Measurement and explanation entities."""
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import UnitOfPower, UnitOfEnergy
from .const import DOMAIN
from .device import v15_device_info

FIELDS = {
    "grid_kw": ("V15 Netzleistung", "kW", "power"),
    "measured_kw": ("V15 Durchschnitt bisher", "kW", "power"),
    "projected_kw": ("V15 Prognose", "kW", "power"),
    "budget_kw": ("V15 Restbudget", "kW", "power"),
    "energy_kwh": ("V15 Netzbezug Viertelstunde", "kWh", "energy"),
    "coverage_percent": ("V15 Messabdeckung", "%", None),
}

async def async_setup_entry(hass, entry, async_add_entities):
    m = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([V15Sensor(m, key, *metadata) for key, metadata in FIELDS.items()] + [V15Explanation(m)])


class V15Sensor(SensorEntity):
    _attr_has_entity_name = False

    def __init__(self, monitor, key, label, unit, device_class):
        self.monitor = monitor
        self.key = key
        self._attr_name = label
        self._attr_unique_id = f"{monitor.entry.entry_id}_{key}"
        self._attr_device_info = v15_device_info(monitor)
        self._attr_native_unit_of_measurement = unit
        if device_class:
            self._attr_device_class = device_class
        # The quarter-hour energy resets every 15 minutes and must NOT be
        # presented as a monotonic lifetime energy counter.
        if key not in ("energy_kwh",):
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if self.key != "coverage_percent" and not self.monitor.data.get("valid"):
            return None
        return self.monitor.data.get(self.key)

    @property
    def extra_state_attributes(self):
        return {"slot_start": self.monitor.data.get("slot"),
                "estimate_only": True}

    async def async_added_to_hass(self):
        self.async_on_remove(self.monitor.subscribe(self.async_write_ha_state))


class V15Explanation(SensorEntity):
    _attr_name = "V15 Diagnose"
    _attr_icon = "mdi:information-outline"
    _attr_has_entity_name = False

    def __init__(self, monitor):
        self.monitor = monitor
        self._attr_unique_id = f"{monitor.entry.entry_id}_diagnosis"
        self._attr_device_info = v15_device_info(monitor)

    @property
    def native_value(self):
        return self.monitor.data.get("reason", "Warte auf Messwerte")

    @property
    def extra_state_attributes(self):
        return {"next_switch": self.monitor.data.get("next_switch"),
                "last_action": self.monitor.last_action,
                "slot_start": self.monitor.data.get("slot"),
                "measurement_coverage_percent": self.monitor.data.get("coverage_percent"),
                "live_control_enabled": self.monitor.enabled,
                "simulation_enabled": self.monitor.simulation,
                "synthetic_demo_active": self.monitor.demo_data}

    async def async_added_to_hass(self):
        self.async_on_remove(self.monitor.subscribe(self.async_write_ha_state))
