"""Home Assistant UI configuration, including editable Options."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import (
    DOMAIN, CONF_GRID, CONF_LIMIT, CONF_RESERVE, CONF_REVERSED, CONF_LOADS,
    CONF_STALE, DEFAULT_LIMIT, DEFAULT_RESERVE, DEFAULT_STALE,
)


def schema(values=None):
    values = values or {}
    grid = EntitySelector(EntitySelectorConfig(domain="sensor"))
    loads = EntitySelector(EntitySelectorConfig(domain="switch", multiple=True))
    return vol.Schema({
        vol.Required(CONF_GRID, default=values.get(CONF_GRID, vol.UNDEFINED)): grid,
        vol.Required(CONF_LIMIT, default=values.get(CONF_LIMIT, DEFAULT_LIMIT)):
            vol.All(vol.Coerce(float), vol.Range(min=0.2, max=100)),
        vol.Required(CONF_RESERVE, default=values.get(CONF_RESERVE, DEFAULT_RESERVE)):
            vol.All(vol.Coerce(float), vol.Range(min=0, max=20)),
        vol.Required(CONF_REVERSED, default=values.get(CONF_REVERSED, False)): bool,
        vol.Required(CONF_STALE, default=values.get(CONF_STALE, DEFAULT_STALE)):
            vol.All(vol.Coerce(int), vol.Range(min=15, max=3600)),
        vol.Optional(CONF_LOADS, default=values.get(CONF_LOADS, [])): loads,
    })


def validate(data):
    return data[CONF_RESERVE] < data[CONF_LIMIT]


class V15ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            if validate(user_input):
                await self.async_set_unique_id("v15_main")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="V15 Lastmanagement", data=user_input)
            errors["base"] = "reserve_too_high"
        return self.async_show_form(step_id="user", data_schema=schema(user_input), errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return V15OptionsFlow()


class V15OptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            if validate(user_input):
                return self.async_create_entry(title="", data=user_input)
            errors["base"] = "reserve_too_high"
        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=schema(current), errors=errors)
