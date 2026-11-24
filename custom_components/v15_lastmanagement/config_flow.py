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
    CONF_HC_PAUSE, CONF_HC_POWERS,
    CONF_PV_ENABLED, CONF_PV_SELECTED, CONF_PV_ARM, CONF_PV_FORECAST,
    CONF_PV_EARLIEST, CONF_PV_DEADLINE, CONF_PV_DURATION,
    CONF_PV_MIN_WH, CONF_PV_WATTS, CONF_PV_MARGIN, CONF_PV_STABLE,
    CONF_RESTART_LIVE, CONF_RESTART_PV,
)
from .home_connect_support import selectable_pause_buttons, validate_pause_buttons
from .pv_start_logic import parse_clock
from homeassistant.helpers import entity_registry as er

EVCC_OPTION_KEYS = (
    CONF_EVCC_CURRENT, CONF_EVCC_MODE, CONF_EVCC_POWER, CONF_EVCC_PHASES,
    CONF_EVCC_FIXED_PHASES, CONF_EVCC_MIN_A, CONF_EVCC_MAX_A,
    CONF_EVCC_VOLTAGE, CONF_EVCC_MARGIN_W, CONF_EVCC_STABLE_S,
    CONF_EVCC_STEP_S, CONF_EVCC_ALLOW_PAUSE,
)


def schema(values=None, hass=None):
    """Keep existing config field IDs and opt-in defaults."""
    values = values or {}
    grid = EntitySelector(EntitySelectorConfig(domain="sensor"))
    loads = EntitySelector(EntitySelectorConfig(domain="switch", multiple=True))
    hc_buttons = selectable_pause_buttons(hass) if hass is not None else []
    hc = EntitySelector(EntitySelectorConfig(domain="button", multiple=True, include_entities=hc_buttons))
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
        vol.Optional(CONF_HC_PAUSE, default=values.get(CONF_HC_PAUSE, [])): hc,
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
        vol.Required(CONF_PV_ENABLED,
                     default=values.get(CONF_PV_ENABLED, False)): bool,
        vol.Required(CONF_RESTART_LIVE,
                     default=values.get(CONF_RESTART_LIVE, False)): bool,
        vol.Required(CONF_RESTART_PV,
                     default=values.get(CONF_RESTART_PV, False)): bool,
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



def pv_start_schema(previous=None, hass=None):
    """Optional dishwasher-only solar start setup."""
    v = previous or {}
    available = []
    if hass is not None:
        registry = er.async_get(hass)
        available = sorted(
            e.entity_id for e in registry.entities.values()
            if e.platform == "home_connect" and e.disabled_by is None
            and e.entity_id.startswith("select.")
            and e.unique_id.endswith("-BSH.Common.Root.SelectedProgram")
        )
    return vol.Schema({
        vol.Required(CONF_PV_SELECTED, default=v.get(CONF_PV_SELECTED, vol.UNDEFINED)):
            EntitySelector(EntitySelectorConfig(domain="select", include_entities=available)),
        vol.Required(CONF_PV_ARM, default=v.get(CONF_PV_ARM, vol.UNDEFINED)):
            EntitySelector(EntitySelectorConfig(domain="input_boolean")),
        vol.Required(CONF_PV_FORECAST, default=v.get(CONF_PV_FORECAST, vol.UNDEFINED)):
            EntitySelector(EntitySelectorConfig(domain="sensor")),
        vol.Required(CONF_PV_EARLIEST, default=v.get(CONF_PV_EARLIEST, "09:00")): str,
        vol.Required(CONF_PV_DEADLINE, default=v.get(CONF_PV_DEADLINE, "15:00")): str,
        vol.Required(CONF_PV_DURATION, default=v.get(CONF_PV_DURATION, 240)):
            vol.All(vol.Coerce(int), vol.Range(min=15, max=720)),
        vol.Required(CONF_PV_MIN_WH, default=v.get(CONF_PV_MIN_WH, 1500)):
            vol.All(vol.Coerce(float), vol.Range(min=0, max=100000)),
        vol.Required(CONF_PV_WATTS, default=v.get(CONF_PV_WATTS, 2500)):
            vol.All(vol.Coerce(float), vol.Range(min=10, max=25000)),
        vol.Required(CONF_PV_MARGIN, default=v.get(CONF_PV_MARGIN, 300)):
            vol.All(vol.Coerce(float), vol.Range(min=0, max=5000)),
        vol.Required(CONF_PV_STABLE, default=v.get(CONF_PV_STABLE, 90)):
            vol.All(vol.Coerce(int), vol.Range(min=30, max=900)),
    })


def pv_start_error(data, hass):
    try:
        start = parse_clock(data[CONF_PV_EARLIEST])
        deadline = parse_clock(data[CONF_PV_DEADLINE])
    except ValueError:
        return "pv_time_invalid"
    if start >= deadline:
        return "pv_time_order"
    if data[CONF_PV_DURATION] % 15:
        return "pv_duration_invalid"
    registry = er.async_get(hass)
    selected = registry.async_get(data[CONF_PV_SELECTED])
    if (selected is None or selected.platform != "home_connect"
            or selected.disabled_by is not None
            or not selected.unique_id.endswith("-BSH.Common.Root.SelectedProgram")):
        return "pv_selected_invalid"
    options = hass.states.get(data[CONF_PV_SELECTED])
    if options is None or not any(
        str(value).startswith("dishcare_dishwasher_program_")
        for value in options.attributes.get("options", [])
    ):
        return "pv_dishwasher_only"
    return None


def validation_error(data, hass=None):
    if data[CONF_RESERVE] >= data[CONF_LIMIT]:
        return "reserve_too_high"
    if data.get(CONF_RESTORE, False) and not (data.get(CONF_LOADS) or data.get(CONF_HC_PAUSE)):
        return "restore_requires_loads"
    if data.get(CONF_HC_PAUSE) and not data.get(CONF_RESTORE, False):
        return "home_connect_requires_restore"
    if hass is not None and data.get(CONF_HC_PAUSE) and not validate_pause_buttons(hass, data[CONF_HC_PAUSE]):
        return "home_connect_entity_invalid"
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
            error = validation_error(user_input, self.hass)
            if error is None:
                self._pending_data = dict(user_input)
                if user_input.get(CONF_RESTORE):
                    return await self.async_step_restore()
                return await self._continue_setup()
            errors["base"] = error
        return self.async_show_form(step_id="user", data_schema=schema(user_input, self.hass), errors=errors)

    async def _continue_setup(self):
        if self._pending_data.get(CONF_EVCC_CONFIGURED):
            return await self.async_step_evcc()
        return await self._finish_setup()

    async def _finish_setup(self):
        if self._pending_data.get(CONF_PV_ENABLED):
            return await self.async_step_pv_start()
        return await self._create_setup_entry()

    async def _create_setup_entry(self):
        await self.async_set_unique_id("v15_main")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="V15 Lastmanagement", data=self._pending_data)

    async def async_step_restore(self, user_input=None):
        if user_input is not None:
            self._pending_data[CONF_RESTORE_POWERS] = {
                entity_id: float(user_input[entity_id])
                for entity_id in self._pending_data.get(CONF_LOADS, [])
            }
            self._pending_data[CONF_HC_POWERS] = {
                entity_id: float(user_input[entity_id])
                for entity_id in self._pending_data.get(CONF_HC_PAUSE, [])
            }
            return await self._continue_setup()
        return self.async_show_form(
            step_id="restore", data_schema=restore_schema(
                self._pending_data.get(CONF_LOADS, []) + self._pending_data.get(CONF_HC_PAUSE, [])),
            description_placeholders=restore_description_placeholders(
                self._pending_data.get(CONF_LOADS, []) + self._pending_data.get(CONF_HC_PAUSE, [])),
        )

    async def async_step_evcc(self, user_input=None):
        errors = {}
        if user_input is not None:
            error = evcc_error(user_input)
            if error is None:
                self._pending_data.update(user_input)
                return await self._finish_setup()
            errors["base"] = error
        return self.async_show_form(step_id="evcc", data_schema=evcc_schema(user_input), errors=errors)

    async def async_step_pv_start(self, user_input=None):
        errors = {}
        if user_input is not None:
            error = pv_start_error(user_input, self.hass)
            if error is None:
                self._pending_data.update(user_input)
                return await self._create_setup_entry()
            errors["base"] = error
        return self.async_show_form(
            step_id="pv_start", data_schema=pv_start_schema(user_input, self.hass),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return V15OptionsFlow()


class V15OptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            error = validation_error(user_input, self.hass)
            if error is None:
                self._pending_data = dict(user_input)
                self._previous = current
                if user_input.get(CONF_RESTORE):
                    return await self.async_step_restore()
                self._pending_data[CONF_RESTORE_POWERS] = {}
                self._pending_data[CONF_HC_POWERS] = {}
                return await self._continue_options()
            errors["base"] = error
        return self.async_show_form(
            step_id="init", data_schema=schema(user_input or current, self.hass), errors=errors
        )

    async def _continue_options(self):
        if self._pending_data.get(CONF_EVCC_CONFIGURED):
            return await self.async_step_evcc()
        return await self._finish_options()

    async def _finish_options(self):
        if self._pending_data.get(CONF_PV_ENABLED):
            return await self.async_step_pv_start()
        return self.async_create_entry(title="", data=self._pending_data)

    async def async_step_restore(self, user_input=None):
        if user_input is not None:
            self._pending_data[CONF_RESTORE_POWERS] = {
                entity_id: float(user_input[entity_id])
                for entity_id in self._pending_data.get(CONF_LOADS, [])
            }
            self._pending_data[CONF_HC_POWERS] = {
                entity_id: float(user_input[entity_id])
                for entity_id in self._pending_data.get(CONF_HC_PAUSE, [])
            }
            return await self._continue_options()
        return self.async_show_form(
            step_id="restore", data_schema=restore_schema(
                self._pending_data.get(CONF_LOADS, []) + self._pending_data.get(CONF_HC_PAUSE, []),
                {**self._previous.get(CONF_RESTORE_POWERS, {}), **self._previous.get(CONF_HC_POWERS, {})}
            ),
            description_placeholders=restore_description_placeholders(
                self._pending_data.get(CONF_LOADS, []) + self._pending_data.get(CONF_HC_PAUSE, [])),
        )

    async def async_step_evcc(self, user_input=None):
        errors = {}
        if user_input is not None:
            error = evcc_error(user_input)
            if error is None:
                self._pending_data.update(user_input)
                return await self._finish_options()
            errors["base"] = error
        return self.async_show_form(
            step_id="evcc", data_schema=evcc_schema(user_input or self._previous),
            errors=errors,
        )

    async def async_step_pv_start(self, user_input=None):
        errors = {}
        if user_input is not None:
            error = pv_start_error(user_input, self.hass)
            if error is None:
                self._pending_data.update(user_input)
                return self.async_create_entry(title="", data=self._pending_data)
            errors["base"] = error
        return self.async_show_form(
            step_id="pv_start",
            data_schema=pv_start_schema(user_input or self._previous, self.hass),
            errors=errors,
        )
