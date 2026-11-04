"""Binary status entities for the V15 monitor."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN
from .device import v15_device_info

async def async_setup_entry(hass, entry, async_add_entities):
    m = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([V15Risk(m), V15Data(m), V15Trusted(m)])

class BaseV15Binary(BinarySensorEntity):
    _attr_has_entity_name = False
    def __init__(self, monitor):
        self.monitor = monitor
        self._attr_unique_id = f"{monitor.entry.entry_id}_{self.key}"
        self._attr_device_info = v15_device_info(monitor)
    async def async_added_to_hass(self):
        self.async_on_remove(self.monitor.subscribe(self.async_write_ha_state))

class V15Risk(BaseV15Binary):
    key = "risk"
    _attr_name = "V15 Grenzwert gefährdet"
    @property
    def is_on(self):
        return self.monitor.data.get("at_risk") if self.monitor.data.get("valid") else None

class V15Data(BaseV15Binary):
    key = "valid"
    _attr_name = "V15 Messwert gültig"
    @property
    def is_on(self):
        return self.monitor.data.get("valid", False)

class V15Trusted(BaseV15Binary):
    key = "trusted"
    _attr_name = "V15 Regelung zulässig"
    @property
    def is_on(self):
        return self.monitor.data.get("trusted_for_control", False)
