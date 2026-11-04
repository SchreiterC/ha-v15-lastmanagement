"""Shared logical device descriptor for the V15 config entry."""
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from .const import DOMAIN

def v15_device_info(monitor):
    """Associate all V15 entities with one logical HA service device."""
    return DeviceInfo(
        identifiers={(DOMAIN, monitor.entry.entry_id)},
        name="V15 Lastmanagement",
        manufacturer="V15 Lastmanagement",
        model="Viertelstunden-Lastmanagement",
        sw_version="0.3.5b1",
        entry_type=DeviceEntryType.SERVICE,
    )
