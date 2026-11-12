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
    "managed_off_count": ("V15 Verwaltete Abschaltungen", None, None),
}

async def async_setup_entry(hass, entry, async_add_entities):
    m = hass.data[DOMAIN][entry.entry_id]
    entities = [V15Sensor(m, key, *metadata) for key, metadata in FIELDS.items()] + [V15Explanation(m)]
    if m.evcc.configured:
        entities.append(V15EvccTargetSensor(m))
    async_add_entities(entities)


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
        if self.key not in ("coverage_percent", "managed_off_count") and not self.monitor.data.get("valid"):
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
                "synthetic_demo_active": self.monitor.demo_data,
                "automatic_restore_configured": self.monitor.auto_restore_enabled,
                "managed_off_switches": list(self.monitor.managed_off),
                "restore_candidate": self.monitor.data.get("restore_candidate"),
                "restore_ready": self.monitor.data.get("restore_ready", False),
                "restore_status": self.monitor.data.get("restore_status"),
                "pending_restore_confirmation": list(self.monitor.pending_on),
                "evcc_configured": self.monitor.evcc.configured,
                "evcc_live_control": self.monitor.evcc.enabled,
                "evcc_status": self.monitor.evcc.status,
                "evcc_last_action": self.monitor.evcc.last_action,
                "evcc_paused_by_v15": self.monitor.evcc.owned_pause,
                "evcc_target_current_a": self.monitor.evcc.target,
                "evcc_available_charge_w": self.monitor.evcc.available_w,
                "evcc_base_load_w": self.monitor.evcc.base_w}

    async def async_added_to_hass(self):
        self.async_on_remove(self.monitor.subscribe(self.async_write_ha_state))


class V15EvccTargetSensor(SensorEntity):
    """Recommendation in amperes, without implying physical current has changed."""
    _attr_name = "V15 evcc Zielstrom"
    _attr_has_entity_name = False
    _attr_icon = "mdi:current-ac"
    _attr_native_unit_of_measurement = "A"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, monitor):
        self.monitor = monitor
        self._attr_unique_id = f"{monitor.entry.entry_id}_evcc_target_current"
        self._attr_device_info = v15_device_info(monitor)

    @property
    def native_value(self):
        return self.monitor.evcc.target

    @property
    def extra_state_attributes(self):
        return {
            "status": self.monitor.evcc.status,
            "available_charge_w": self.monitor.evcc.available_w,
            "base_load_w": self.monitor.evcc.base_w,
            "last_action": self.monitor.evcc.last_action,
        }

    async def async_added_to_hass(self):
        self.async_on_remove(self.monitor.subscribe(self.async_write_ha_state))
