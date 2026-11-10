"""Explicitly opt-in controls. Simulation never calls Home Assistant services."""
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN
from .device import v15_device_info

async def async_setup_entry(hass, entry, async_add_entities):
    m = hass.data[DOMAIN][entry.entry_id]
    entities = [V15Control(m), V15Simulation(m), V15Demo(m)]
    if m.evcc.configured:
        entities.append(V15EvccControl(m))
    async_add_entities(entities)

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
        self.monitor.evcc.deactivate("Probelauf aktiviert; evcc nicht mehr gesteuert")
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
        self.monitor.evcc.deactivate("Künstliche Demo aktiviert; evcc nicht mehr gesteuert")
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


class V15EvccControl(V15BaseSwitch):
    """Separate, explicit opt-in for actual evcc max-current/mode control."""
    key = "evcc_live_control"
    _attr_name = "V15 evcc-Ladestromregelung"
    _attr_icon = "mdi:ev-station"

    @property
    def is_on(self):
        return self.monitor.evcc.enabled

    @property
    def extra_state_attributes(self):
        e = self.monitor.evcc
        return {
            "status": e.status,
            "original_max_current_a": e.original_current,
            "paused_by_v15": e.owned_pause,
            "last_action": e.last_action,
        }

    async def async_turn_on(self, **kwargs):
        self.monitor.evcc.activate()
        self.monitor.simulation = False
        self.monitor.update()

    async def async_turn_off(self, **kwargs):
        self.monitor.evcc.deactivate(
            "V15 evcc-Steuerung deaktiviert; Ladezustand und Stromlimit in evcc prüfen"
        )
        self.monitor.update()
