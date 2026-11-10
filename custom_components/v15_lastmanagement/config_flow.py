"""User-facing V15 setup and options, including per-load restore estimates."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import (
    DOMAIN, CONF_GRID, CONF_LIMIT, CONF_RESERVE, CONF_REVERSED, CONF_LOADS,
    CONF_STALE, DEFAULT_LIMIT, DEFAULT_RESERVE, DEFAULT_STALE,
    CONF_RESTORE, CONF_RESTORE_POWERS, CONF_RESTORE_STABLE,
    CONF_RESTORE_MIN_OFF, CONF_RESTORE_MARGIN,
    DEFAULT_RESTORE, DEFAULT_RESTORE_STABLE,
    DEFAULT_RESTORE_MIN_OFF, DEFAULT_RESTORE_MARGIN,
)


def schema(values=None):
    """Keep old config fields and IDs; add opt-in restoration settings."""
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
        vol.Required(CONF_RESTORE, default=values.get(CONF_RESTORE, DEFAULT_RESTORE)): bool,
        vol.Required(CONF_RESTORE_STABLE,
                     default=values.get(CONF_RESTORE_STABLE, DEFAULT_RESTORE_STABLE)):
            vol.All(vol.Coerce(int), vol.Range(min=30, max=1800)),
        vol.Required(CONF_RESTORE_MIN_OFF,
                     default=values.get(CONF_RESTORE_MIN_OFF, DEFAULT_RESTORE_MIN_OFF)):
            vol.All(vol.Coerce(int), vol.Range(min=60, max=7200)),
        vol.Required(CONF_RESTORE_MARGIN,
                     default=values.get(CONF_RESTORE_MARGIN, DEFAULT_RESTORE_MARGIN)):
            vol.All(vol.Coerce(float), vol.Range(min=0, max=5000)),
    })


def restore_schema(loads, previous=None):
    """One required rated power in watts for every selected load.

    Field names are the actual switch entity_ids, avoiding ambiguous numbering.
    """
    previous = previous or {}
    return vol.Schema({
        vol.Required(entity_id, default=previous.get(entity_id, vol.UNDEFINED)):
            vol.All(vol.Coerce(float), vol.Range(min=10, max=25000))
        for entity_id in loads
    })


def restore_description_placeholders(loads):
    """Show exactly which switches need an estimated power, in selection order."""
    return {"switches": "\n".join(f"- `{entity_id}`" for entity_id in loads)}


def validation_error(data):
    if data[CONF_RESERVE] >= data[CONF_LIMIT]:
        return "reserve_too_high"
    if data.get(CONF_RESTORE, False) and not data.get(CONF_LOADS):
        return "restore_requires_loads"
    return None


class V15ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            error = validation_error(user_input)
            if error is None:
                self._pending_data = dict(user_input)
                if user_input.get(CONF_RESTORE):
                    return await self.async_step_restore()
                await self.async_set_unique_id("v15_main")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="V15 Lastmanagement", data=user_input)
            errors["base"] = error
        return self.async_show_form(step_id="user", data_schema=schema(user_input), errors=errors)

    async def async_step_restore(self, user_input=None):
        if user_input is not None:
            self._pending_data[CONF_RESTORE_POWERS] = {
                entity_id: float(user_input[entity_id])
                for entity_id in self._pending_data[CONF_LOADS]
            }
            await self.async_set_unique_id("v15_main")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="V15 Lastmanagement", data=self._pending_data)
        return self.async_show_form(
            step_id="restore",
            data_schema=restore_schema(self._pending_data[CONF_LOADS]),
            description_placeholders=restore_description_placeholders(
                self._pending_data[CONF_LOADS]
            ),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return V15OptionsFlow()


class V15OptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            error = validation_error(user_input)
            if error is None:
                self._pending_data = dict(user_input)
                if user_input.get(CONF_RESTORE):
                    self._previous_powers = current.get(CONF_RESTORE_POWERS, {})
                    return await self.async_step_restore()
                self._pending_data[CONF_RESTORE_POWERS] = {}
                return self.async_create_entry(title="", data=self._pending_data)
            errors["base"] = error
        return self.async_show_form(
            step_id="init", data_schema=schema(user_input or current), errors=errors
        )

    async def async_step_restore(self, user_input=None):
        if user_input is not None:
            self._pending_data[CONF_RESTORE_POWERS] = {
                entity_id: float(user_input[entity_id])
                for entity_id in self._pending_data[CONF_LOADS]
            }
            return self.async_create_entry(title="", data=self._pending_data)
        return self.async_show_form(
            step_id="restore",
            data_schema=restore_schema(
                self._pending_data[CONF_LOADS], self._previous_powers
            ),
            description_placeholders=restore_description_placeholders(
                self._pending_data[CONF_LOADS]
            ),
        )
