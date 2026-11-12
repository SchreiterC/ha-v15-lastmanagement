"""Beta 6 go-e runtime tests with real HA fixtures and mocked local HTTP I/O.

These tests never communicate with any LAN device or cloud endpoint.
"""
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant.common import MockConfigEntry

from custom_components.v15_lastmanagement.const import (
    DOMAIN, CONF_GRID, CONF_LIMIT, CONF_RESERVE, CONF_REVERSED, CONF_LOADS,
    CONF_STALE, CONF_EVCC_CONFIGURED, CONF_GOE_CONFIGURED, CONF_GOE_HOST,
    CONF_GOE_EXCLUSIVE, CONF_GOE_PHASES, CONF_GOE_MIN_A, CONF_GOE_MAX_A,
    CONF_GOE_MARGIN_W, CONF_GOE_STABLE_S, CONF_GOE_STEP_S, CONF_GOE_ALLOW_PAUSE,
)

GRID = "sensor.beta6_grid"
BASE = {
    CONF_GRID: GRID, CONF_LIMIT: 5.0, CONF_RESERVE: 0.5,
    CONF_REVERSED: False, CONF_LOADS: [], CONF_STALE: 120,
}
GOE = {
    CONF_EVCC_CONFIGURED: False,
    CONF_GOE_CONFIGURED: True,
    CONF_GOE_HOST: "192.168.1.50",
    CONF_GOE_EXCLUSIVE: True,
    CONF_GOE_PHASES: 3,
    CONF_GOE_MIN_A: 6,
    CONF_GOE_MAX_A: 16,
    CONF_GOE_MARGIN_W: 300,
    CONF_GOE_STABLE_S: 90,
    CONF_GOE_STEP_S: 30,
    CONF_GOE_ALLOW_PAUSE: True,
}


def goe_status():
    nrg = [0] * 16
    nrg[11] = 11040
    return {"amp": 16, "frc": 0, "nrg": nrg, "pnp": 3}


def entity_id(hass, entry, platform, key):
    registry = er.async_get(hass)
    result = registry.async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{key}"
    )
    assert result, f"Missing {platform} entity {key}"
    return result


@pytest.fixture
async def goe_entry(hass: HomeAssistant):
    state = goe_status()
    calls = []

    async def fake_status(_self):
        return {**state, "nrg": list(state["nrg"])}

    async def fake_set(_self, key, value):
        calls.append((key, value))
        state[key] = value

    hass.states.async_set(GRID, "5040", {"unit_of_measurement": "W"})
    entry = MockConfigEntry(
        domain=DOMAIN, title="V15 Beta 6 Go-e Test",
        unique_id="v15_main", data=BASE, options=GOE,
    )
    with (
        patch(
            "custom_components.v15_lastmanagement.goe_control.GoeLocalAPI.status",
            new=fake_status,
        ),
        patch(
            "custom_components.v15_lastmanagement.goe_control.GoeLocalAPI.set_value",
            new=fake_set,
        ),
    ):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield entry, state, calls
        if entry.entry_id in hass.data.get(DOMAIN, {}):
            await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()


async def test_goe_entities_disabled_until_explicit_opt_in(
    hass: HomeAssistant, goe_entry
):
    entry, state, calls = goe_entry
    assert state["amp"] == 16
    assert entity_id(hass, entry, "sensor", "goe_target_current")
    goe_switch = entity_id(hass, entry, "switch", "goe_live_control")
    assert hass.states.get(goe_switch).state == "off"
    assert er.async_get(hass).async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_evcc_live_control"
    ) is None
    diag = entity_id(hass, entry, "sensor", "diagnosis")
    assert hass.states.get(diag).attributes["charging_backend"] == "goe"
    assert calls == []


async def test_goe_enabling_requires_safety_confirmation(
    hass: HomeAssistant, goe_entry
):
    entry, state, calls = goe_entry
    monitor = hass.data[DOMAIN][entry.entry_id]
    monitor.config[CONF_GOE_EXCLUSIVE] = False
    with pytest.raises(ValueError):
        monitor.goe.activate()
    assert calls == []
    assert not monitor.goe.enabled


async def test_goe_explicit_enable_then_reload_is_off(
    hass: HomeAssistant, goe_entry
):
    entry, _, calls = goe_entry
    switch_id = entity_id(hass, entry, "switch", "goe_live_control")
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": switch_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(switch_id).state == "on"
    assert calls == []
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(switch_id).state == "off"
    assert calls == []


async def test_goe_options_are_a_separate_step(hass: HomeAssistant):
    hass.states.async_set(GRID, "5040", {"unit_of_measurement": "W"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {**BASE, CONF_EVCC_CONFIGURED: False, CONF_GOE_CONFIGURED: True},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "goe"
    fields = {key.schema for key in result["data_schema"].schema}
    assert {CONF_GOE_HOST, CONF_GOE_EXCLUSIVE, CONF_GOE_PHASES} <= fields


async def test_choosing_goe_and_evcc_simultaneously_fails(hass: HomeAssistant):
    hass.states.async_set(GRID, "5040", {"unit_of_measurement": "W"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {**BASE, CONF_EVCC_CONFIGURED: True, CONF_GOE_CONFIGURED: True},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "charger_conflict"
