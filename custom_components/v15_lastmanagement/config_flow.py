"""UI setup and Options for V15, optional load restoration and evcc controls."""
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
    CONF_EVCC_CONFIGURED, CONF_EVCC_CURRENT, CONF_EVCC_MODE, CONF_EVCC_POWER,
    CONF_EVCC_PHASES, CONF_EVCC_FIXED_PHASES, CONF_EVCC_MIN_A,
    CONF_EVCC_MAX_A, CONF_EVCC_VOLTAGE, CONF_EVCC_MARGIN_W,
    CONF_EVCC_STABLE_S, CONF_EVCC_STEP_S, CONF_EVCC_ALLOW_PAUSE,
    DEFAULT_EVCC_PHASES, DEFAULT_EVCC_MIN_A, DEFAULT_EVCC_MAX_A,
    DEFAULT_EVCC_VOLTAGE, DEFAULT_EVCC_MARGIN_W, DEFAULT_EVCC_STABLE_S,
    DEFAULT_EVCC_STEP_S,
    CONF_GOE_CONFIGURED, CONF_GOE_HOST, CONF_GOE_EXCLUSIVE,
    CONF_GOE_PHASES, CONF_GOE_MIN_A, CONF_GOE_MAX_A,
    CONF_GOE_MARGIN_W, CONF_GOE_STABLE_S, CONF_GOE_STEP_S,
    CONF_GOE_ALLOW_PAUSE,
)
from .goe_logic import validated_local_ipv4

GOE_OPTION_KEYS = (
    CONF_GOE_HOST, CONF_GOE_EXCLUSIVE, CONF_GOE_PHASES,
    CONF_GOE_MIN_A, CONF_GOE_MAX_A, CONF_GOE_MARGIN_W,
    CONF_GOE_STABLE_S, CONF_GOE_STEP_S, CONF_GOE_ALLOW_PAUSE,
)

EVCC_OPTION_KEYS = (
    CONF_EVCC_CURRENT, CONF_EVCC_MODE, CONF_EVCC_POWER, CONF_EVCC_PHASES,
    CONF_EVCC_FIXED_PHASES, CONF_EVCC_MIN_A, CONF_EVCC_MAX_A,
    CONF_EVCC_VOLTAGE, CONF_EVCC_MARGIN_W, CONF_EVCC_STABLE_S,
    CONF_EVCC_STEP_S, CONF_EVCC_ALLOW_PAUSE,
)


def schema(values=None):
    """Keep existing config field IDs and opt-in defaults."""
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
        vol.Required(CONF_EVCC_CONFIGURED,
                     default=values.get(CONF_EVCC_CONFIGURED, False)): bool,
        vol.Required(CONF_GOE_CONFIGURED,
                     default=values.get(CONF_GOE_CONFIGURED, False)): bool,
    })


def restore_schema(loads, previous=None):
    previous = previous or {}
    return vol.Schema({
        vol.Required(entity_id, default=previous.get(entity_id, vol.UNDEFINED)):
            vol.All(vol.Coerce(float), vol.Range(min=10, max=25000))
        for entity_id in loads
    })


def restore_description_placeholders(loads):
    return {"switches": "\n".join(f"- `{entity_id}`" for entity_id in loads)}


def evcc_schema(previous=None):
    """evcc is optional; entity IDs are selected rather than hard-coded."""
    v = previous or {}
    return vol.Schema({
        vol.Required(CONF_EVCC_CURRENT,
                     default=v.get(CONF_EVCC_CURRENT, vol.UNDEFINED)):
            EntitySelector(EntitySelectorConfig(domain=["select", "number"])),
        vol.Required(CONF_EVCC_MODE,
                     default=v.get(CONF_EVCC_MODE, vol.UNDEFINED)):
            EntitySelector(EntitySelectorConfig(domain="select")),
        vol.Required(CONF_EVCC_POWER,
                     default=v.get(CONF_EVCC_POWER, vol.UNDEFINED)):
            EntitySelector(EntitySelectorConfig(domain="sensor")),
        vol.Optional(CONF_EVCC_PHASES,
                     default=v.get(CONF_EVCC_PHASES, vol.UNDEFINED)):
            EntitySelector(EntitySelectorConfig(domain="sensor")),
        vol.Required(CONF_EVCC_FIXED_PHASES,
                     default=v.get(CONF_EVCC_FIXED_PHASES, DEFAULT_EVCC_PHASES)):
            vol.In([1, 3]),
        vol.Required(CONF_EVCC_MIN_A,
                     default=v.get(CONF_EVCC_MIN_A, DEFAULT_EVCC_MIN_A)):
            vol.All(vol.Coerce(int), vol.Range(min=6, max=32)),
        vol.Required(CONF_EVCC_MAX_A,
                     default=v.get(CONF_EVCC_MAX_A, DEFAULT_EVCC_MAX_A)):
            vol.All(vol.Coerce(int), vol.Range(min=6, max=32)),
        vol.Required(CONF_EVCC_VOLTAGE,
                     default=v.get(CONF_EVCC_VOLTAGE, DEFAULT_EVCC_VOLTAGE)):
            vol.All(vol.Coerce(int), vol.Range(min=200, max=250)),
        vol.Required(CONF_EVCC_MARGIN_W,
                     default=v.get(CONF_EVCC_MARGIN_W, DEFAULT_EVCC_MARGIN_W)):
            vol.All(vol.Coerce(int), vol.Range(min=0, max=3000)),
        vol.Required(CONF_EVCC_STABLE_S,
                     default=v.get(CONF_EVCC_STABLE_S, DEFAULT_EVCC_STABLE_S)):
            vol.All(vol.Coerce(int), vol.Range(min=30, max=900)),
        vol.Required(CONF_EVCC_STEP_S,
                     default=v.get(CONF_EVCC_STEP_S, DEFAULT_EVCC_STEP_S)):
            vol.All(vol.Coerce(int), vol.Range(min=30, max=300)),
        vol.Required(CONF_EVCC_ALLOW_PAUSE,
                     default=v.get(CONF_EVCC_ALLOW_PAUSE, False)): bool,
    })




def goe_schema(previous=None):
    """Direct go-e API v2: a private IPv4 host and deliberately bounded current."""
    v = previous or {}
    return vol.Schema({
        vol.Required(CONF_GOE_HOST, default=v.get(CONF_GOE_HOST, vol.UNDEFINED)):
            vol.All(str, vol.Length(min=7, max=15)),
        vol.Required(CONF_GOE_EXCLUSIVE,
                     default=v.get(CONF_GOE_EXCLUSIVE, False)): bool,
        vol.Required(CONF_GOE_PHASES,
                     default=v.get(CONF_GOE_PHASES, 3)): vol.In([1, 3]),
        vol.Required(CONF_GOE_MIN_A,
                     default=v.get(CONF_GOE_MIN_A, DEFAULT_EVCC_MIN_A)):
            vol.All(vol.Coerce(int), vol.Range(min=6, max=32)),
        vol.Required(CONF_GOE_MAX_A,
                     default=v.get(CONF_GOE_MAX_A, DEFAULT_EVCC_MAX_A)):
            vol.All(vol.Coerce(int), vol.Range(min=6, max=32)),
        vol.Required(CONF_GOE_MARGIN_W,
                     default=v.get(CONF_GOE_MARGIN_W, DEFAULT_EVCC_MARGIN_W)):
            vol.All(vol.Coerce(int), vol.Range(min=0, max=3000)),
        vol.Required(CONF_GOE_STABLE_S,
                     default=v.get(CONF_GOE_STABLE_S, DEFAULT_EVCC_STABLE_S)):
            vol.All(vol.Coerce(int), vol.Range(min=30, max=900)),
        vol.Required(CONF_GOE_STEP_S,
                     default=v.get(CONF_GOE_STEP_S, DEFAULT_EVCC_STEP_S)):
            vol.All(vol.Coerce(int), vol.Range(min=30, max=300)),
        vol.Required(CONF_GOE_ALLOW_PAUSE,
                     default=v.get(CONF_GOE_ALLOW_PAUSE, False)): bool,
    })


def goe_error(data):
    try:
        validated_local_ipv4(data[CONF_GOE_HOST])
    except (ValueError, KeyError, TypeError):
        return "goe_local_address"
    if data[CONF_GOE_MIN_A] > data[CONF_GOE_MAX_A]:
        return "goe_current_limits"
    return None

def validation_error(data):
    if data.get(CONF_EVCC_CONFIGURED, False) and data.get(CONF_GOE_CONFIGURED, False):
        return "charger_conflict"
    if data[CONF_RESERVE] >= data[CONF_LIMIT]:
        return "reserve_too_high"
    if data.get(CONF_RESTORE, False) and not data.get(CONF_LOADS):
        return "restore_requires_loads"
    return None


def evcc_error(data):
    if data[CONF_EVCC_MIN_A] > data[CONF_EVCC_MAX_A]:
        return "evcc_current_limits"
    if data[CONF_EVCC_CURRENT] == data[CONF_EVCC_MODE]:
        return "evcc_separate_entities"
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
                return await self._continue_setup()
            errors["base"] = error
        return self.async_show_form(step_id="user", data_schema=schema(user_input), errors=errors)

    async def _continue_setup(self):
        if self._pending_data.get(CONF_EVCC_CONFIGURED):
            return await self.async_step_evcc()
        if self._pending_data.get(CONF_GOE_CONFIGURED):
            return await self.async_step_goe()
        await self.async_set_unique_id("v15_main")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="V15 Lastmanagement", data=self._pending_data)

    async def async_step_restore(self, user_input=None):
        if user_input is not None:
            self._pending_data[CONF_RESTORE_POWERS] = {
                entity_id: float(user_input[entity_id])
                for entity_id in self._pending_data[CONF_LOADS]
            }
            return await self._continue_setup()
        return self.async_show_form(
            step_id="restore", data_schema=restore_schema(self._pending_data[CONF_LOADS]),
            description_placeholders=restore_description_placeholders(self._pending_data[CONF_LOADS]),
        )

    async def async_step_evcc(self, user_input=None):
        errors = {}
        if user_input is not None:
            error = evcc_error(user_input)
            if error is None:
                self._pending_data.update(user_input)
                await self.async_set_unique_id("v15_main")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="V15 Lastmanagement", data=self._pending_data)
            errors["base"] = error
        return self.async_show_form(step_id="evcc", data_schema=evcc_schema(user_input), errors=errors)

    async def async_step_goe(self, user_input=None):
        errors = {}
        if user_input is not None:
            error = goe_error(user_input)
            if error is None:
                self._pending_data.update(user_input)
                await self.async_set_unique_id("v15_main")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="V15 Lastmanagement", data=self._pending_data)
            errors["base"] = error
        return self.async_show_form(step_id="goe", data_schema=goe_schema(user_input), errors=errors)

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
                self._previous = current
                if user_input.get(CONF_RESTORE):
                    return await self.async_step_restore()
                self._pending_data[CONF_RESTORE_POWERS] = {}
                return await self._continue_options()
            errors["base"] = error
        return self.async_show_form(
            step_id="init", data_schema=schema(user_input or current), errors=errors
        )

    async def _continue_options(self):
        if self._pending_data.get(CONF_EVCC_CONFIGURED):
            return await self.async_step_evcc()
        if self._pending_data.get(CONF_GOE_CONFIGURED):
            return await self.async_step_goe()
        return self.async_create_entry(title="", data=self._pending_data)

    async def async_step_restore(self, user_input=None):
        if user_input is not None:
            self._pending_data[CONF_RESTORE_POWERS] = {
                entity_id: float(user_input[entity_id])
                for entity_id in self._pending_data[CONF_LOADS]
            }
            return await self._continue_options()
        return self.async_show_form(
            step_id="restore", data_schema=restore_schema(
                self._pending_data[CONF_LOADS], self._previous.get(CONF_RESTORE_POWERS, {})
            ),
            description_placeholders=restore_description_placeholders(self._pending_data[CONF_LOADS]),
        )

    async def async_step_evcc(self, user_input=None):
        errors = {}
        if user_input is not None:
            error = evcc_error(user_input)
            if error is None:
                self._pending_data.update(user_input)
                return self.async_create_entry(title="", data=self._pending_data)
            errors["base"] = error
        return self.async_show_form(
            step_id="evcc", data_schema=evcc_schema(user_input or self._previous),
            errors=errors,
        )

    async def async_step_goe(self, user_input=None):
        errors = {}
        if user_input is not None:
            error = goe_error(user_input)
            if error is None:
                self._pending_data.update(user_input)
                return self.async_create_entry(title="", data=self._pending_data)
            errors["base"] = error
        return self.async_show_form(
            step_id="goe", data_schema=goe_schema(user_input or self._previous),
            errors=errors,
        )
