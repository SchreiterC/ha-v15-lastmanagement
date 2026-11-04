"""Explicitly opt-in controls. Simulation never calls Home Assistant services."""
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN
from .device import v15_device_info

async def async_setup_entry(hass, entry, async_add_entities):
    m = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([V15Control(m), V15Simulation(m), V15Demo(m)])

class V15BaseSwitch(SwitchEntity):
    _attr_has_entity_name = False
    def __init__(self, monitor):
        self.monitor = monitor
        self._attr_unique_id = f"{monitor.entry.entry_id}_{self.key}"
        self._attr_device_info = v15_device_info(monitor)
    async def async_added_to_hass(self):
        self.async_on_remove(self.monitor.subscribe(self.async_write_ha_state))

class V15Control(V15BaseSwitch):
    key = "live_control"
    _attr_name = "V15 Aktive Lastabschaltung"
    _attr_icon = "mdi:transmission-tower-off"
    @property
    def is_on(self):
        return self.monitor.enabled
    @property
    def extra_state_attributes(self):
        return {"last_action": self.monitor.last_action, "configured_switches": self.monitor.load_entities}
    async def async_turn_on(self, **kwargs):
        # Deliberate user action required on every HA restart/reload.
        if not self.monitor.load_entities:
            raise ValueError("No load switches configured for live shedding")
        if self.monitor.demo_data:
            raise ValueError("Synthetic demo is active; disable demo data before live control")
        self.monitor.enabled = True
        self.monitor.simulation = False
        self.monitor.update()
    async def async_turn_off(self, **kwargs):
        self.monitor.enabled = False
        self.monitor.update()

class V15Simulation(V15BaseSwitch):
    key = "simulation"
    _attr_name = "V15 Probelauf ohne Schalten"
    _attr_icon = "mdi:test-tube"
    @property
    def is_on(self):
        return self.monitor.simulation
    async def async_turn_on(self, **kwargs):
        self.monitor.enabled = False
        self.monitor.simulation = True
        self.monitor.update()
    async def async_turn_off(self, **kwargs):
        self.monitor.simulation = False
        self.monitor.update()

class V15Demo(V15BaseSwitch):
    key = "demo_data"
    _attr_name = "V15 Demo mit künstlichen Messwerten"
    _attr_icon = "mdi:chart-bell-curve-cumulative"

    @property
    def is_on(self):
        return self.monitor.demo_data

    async def async_turn_on(self, **kwargs):
        from homeassistant.util import dt as dt_util
        self.monitor.enabled = False
        self.monitor.simulation = True
        self.monitor.demo_data = True
        self.monitor.demo_started = dt_util.now()
        # Drop any historical real-data integration before switching sources.
        self.monitor.last_time = None
        self.monitor.last_w = None
        self.monitor.energy_wh = 0.0
        self.monitor.coverage_s = 0.0
        self.monitor.update()

    async def async_turn_off(self, **kwargs):
        self.monitor.demo_data = False
        self.monitor.demo_started = None
        self.monitor.enabled = False
        self.monitor.last_time = None
        self.monitor.last_w = None
        self.monitor.energy_wh = 0.0
        self.monitor.coverage_s = 0.0
        self.monitor.update()
