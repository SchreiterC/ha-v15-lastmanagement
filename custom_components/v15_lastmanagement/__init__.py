"""V15 Lastmanagement custom integration."""
from homeassistant.const import Platform
from .const import DOMAIN
from .coordinator import V15Monitor

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]


async def async_setup_entry(hass, entry):
    monitor = V15Monitor(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = monitor
    await monitor.async_start()
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        await monitor.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await hass.data[DOMAIN][entry.entry_id].async_stop()
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
