"""End-to-end V15/evcc integration tests against an in-process Home Assistant.

No connection to real HA, evcc, go-e or Victron. Test entities are local HA
states; a mock evcc service records commands, instead of forwarding them.
"""

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant.common import MockConfigEntry

from custom_components.v15_lastmanagement.const import (
    DOMAIN, CONF_GRID, CONF_LIMIT, CONF_RESERVE, CONF_REVERSED, CONF_LOADS,
    CONF_STALE, CONF_EVCC_CONFIGURED, CONF_EVCC_CURRENT, CONF_EVCC_MODE,
    CONF_EVCC_POWER, CONF_EVCC_PHASES, CONF_EVCC_FIXED_PHASES,
    CONF_EVCC_MIN_A, CONF_EVCC_MAX_A, CONF_EVCC_VOLTAGE, CONF_EVCC_MARGIN_W,
    CONF_EVCC_STABLE_S, CONF_EVCC_STEP_S, CONF_EVCC_ALLOW_PAUSE,
    CONF_RESTART_LIVE,
    CONF_RESTART_PV, CONF_PV_ENABLED, CONF_PV_SELECTED, CONF_PV_ARM,
    CONF_COST_CONFIGURED, CONF_COST_REGION, CONF_COST_MODE,
    CONF_PV_FORECAST, CONF_PV_EARLIEST, CONF_PV_DEADLINE,
    CONF_PV_DURATION, CONF_PV_MIN_WH, CONF_PV_WATTS, CONF_PV_MARGIN,
    CONF_PV_STABLE,
)

GRID = "sensor.v15_lab_grid"
CURRENT = "select.v15_lab_max_current"
MODE = "select.v15_lab_mode"
CHARGING = "sensor.v15_lab_charge_power"
PHASES = "sensor.v15_lab_phases"

BASE = {
    CONF_GRID: GRID,
    CONF_LIMIT: 5.0,
    CONF_RESERVE: 0.5,
    CONF_REVERSED: False,
    CONF_LOADS: [],
    CONF_STALE: 120,
}
EVCC = {
    CONF_EVCC_CONFIGURED: True,
    CONF_EVCC_CURRENT: CURRENT,
    CONF_EVCC_MODE: MODE,
    CONF_EVCC_POWER: CHARGING,
    CONF_EVCC_PHASES: PHASES,
    CONF_EVCC_FIXED_PHASES: 3,
    CONF_EVCC_MIN_A: 6,
    CONF_EVCC_MAX_A: 16,
    CONF_EVCC_VOLTAGE: 230,
    CONF_EVCC_MARGIN_W: 300,
    CONF_EVCC_STABLE_S: 90,
    CONF_EVCC_STEP_S: 30,
    CONF_EVCC_ALLOW_PAUSE: False,
}


def set_virtual_states(hass: HomeAssistant):
    """Set up synthetic evcc entities inside the disposable HA instance."""
    hass.states.async_set(GRID, "1100", {"unit_of_measurement": "W"})
    hass.states.async_set(CURRENT, "16", {"options": [str(n) for n in range(6, 17)]})
    hass.states.async_set(MODE, "smart", {"options": ["off", "smart", "now"]})
    hass.states.async_set(CHARGING, "6.9", {"unit_of_measurement": "kW"})
    hass.states.async_set(PHASES, "3")


@pytest.fixture
async def v15(hass: HomeAssistant):
    set_virtual_states(hass)
    entry = MockConfigEntry(
        domain=DOMAIN, title="V15 Lab", unique_id="v15_main",
        data=BASE, options=EVCC,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield entry
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


def entity_id(hass, entry, platform, key):
    registry = er.async_get(hass)
    result = registry.async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{key}"
    )
    assert result is not None, f"Missing {platform} entity for {key}"
    return result


async def test_runtime_entities_and_disabled_by_default(hass: HomeAssistant, v15):
    """Real HA entity registry + actual integration entry setup."""
    diagnostic = entity_id(hass, v15, "sensor", "diagnosis")
    evcc_switch = entity_id(hass, v15, "switch", "evcc_live_control")
    target = entity_id(hass, v15, "sensor", "evcc_target_current")

    assert hass.states.get(diagnostic) is not None
    assert hass.states.get(target) is not None
    assert hass.states.get(evcc_switch).state == "off"
    assert hass.states.get(entity_id(hass, v15, "switch", "live_control")).state == "off"
    diag_attrs = hass.states.get(diagnostic).attributes
    assert diag_attrs["evcc_configured"] is True
    assert diag_attrs["evcc_live_control"] is False


async def test_explicit_service_enable_then_reload_disables(hass: HomeAssistant, v15):
    """HA switch service allows opt-in; reloading must not restore consent."""
    switch_id = entity_id(hass, v15, "switch", "evcc_live_control")
    await hass.services.async_call("switch", "turn_on", {"entity_id": switch_id}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(switch_id).state == "on"
    assert await hass.config_entries.async_reload(v15.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(switch_id).state == "off"


async def test_opt_in_live_shedding_restored_after_reload(hass: HomeAssistant):
    """Real HA RestoreEntity must preserve only explicit consented mode."""
    set_virtual_states(hass)
    load = "switch.v15_dummy_load"
    hass.states.async_set(load, "on")
    entry = MockConfigEntry(
        domain=DOMAIN, title="V15 Restore Lab", unique_id="v15_main",
        data={**BASE, CONF_LOADS: [load]},
        options={CONF_RESTART_LIVE: True},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    live = entity_id(hass, entry, "switch", "live_control")
    simulation = entity_id(hass, entry, "switch", "simulation")
    assert hass.states.get(live).state == "off"
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": live}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(live).state == "on"
    assert hass.states.get(simulation).state == "off"
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(live).state == "on"
    assert hass.states.get(simulation).state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_opt_in_pv_live_restores_without_reusing_old_arm(
    hass: HomeAssistant, monkeypatch
):
    """PV live switch restored, but ON arm from previous session invalid."""
    from custom_components.v15_lastmanagement.pv_start import V15PvStartController
    from datetime import datetime, timedelta, timezone

    arm = "input_boolean.v15_test_arm"
    selected = "select.v15_test_dishwasher"
    op = "sensor.v15_test_operation"
    door = "sensor.v15_test_door"
    remote = "binary_sensor.v15_test_remote"
    remote_start = "binary_sensor.v15_test_remote_start"
    online = "binary_sensor.v15_test_online"
    forecast = "sensor.v15_test_pv"

    def fake_resolve(self):
        self.selected = selected
        self.operation = op
        self.door = door
        self.remote = remote
        self.remote_start = remote_start
        self.connectivity = online
        self.device_id = "virtual-home-connect-device"
        self.missing_entities = []

    monkeypatch.setattr(V15PvStartController, "resolve", fake_resolve)
    set_virtual_states(hass)
    hass.states.async_set(arm, "on")
    hass.states.async_set(selected, "dishcare_dishwasher_program_eco_50")
    hass.states.async_set(op, "ready")
    hass.states.async_set(door, "closed")
    hass.states.async_set(remote, "on")
    hass.states.async_set(remote_start, "on")
    hass.states.async_set(online, "on")
    hass.states.async_set(forecast, "0", {"wh_period_15m": {}})

    entry = MockConfigEntry(
        domain=DOMAIN, title="PV Restart Lab", unique_id="v15_main",
        data={**BASE,
              CONF_PV_ENABLED: True,
              CONF_PV_SELECTED: selected,
              CONF_PV_ARM: arm,
              CONF_PV_FORECAST: forecast,
              CONF_PV_EARLIEST: "09:00",
              CONF_PV_DEADLINE: "15:00",
              CONF_PV_DURATION: 240,
              CONF_PV_MIN_WH: 1500,
              CONF_PV_WATTS: 2500,
              CONF_PV_MARGIN: 300,
              CONF_PV_STABLE: 90},
        options={CONF_RESTART_PV: True},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    pv = entity_id(hass, entry, "switch", "pv_start_live")
    assert hass.states.get(pv).state == "off"
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": pv}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(pv).state == "on"
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(pv).state == "on"
    monitor = hass.data[DOMAIN][entry.entry_id]
    assert monitor.pv.require_fresh_arm is True
    assert monitor.pv.arm_seen_off is False
    assert monitor.pv._fresh_arm_ready() is False
    assert monitor.pv.require_fresh_arm is True
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_default_live_shedding_remains_off_after_reload(hass: HomeAssistant):
    """Existing users are not changed by new optional recovery settings."""
    set_virtual_states(hass)
    load = "switch.v15_dummy_load"
    hass.states.async_set(load, "on")
    entry = MockConfigEntry(
        domain=DOMAIN, title="V15 Default Lab", unique_id="v15_main",
        data={**BASE, CONF_LOADS: [load]}, options={},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    live = entity_id(hass, entry, "switch", "live_control")
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": live}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(live).state == "on"
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(live).state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_no_evcc_commands_without_opt_in(hass: HomeAssistant, v15):
    """Sensor events alone must never issue charger commands."""
    calls = []
    async def record(call):
        calls.append(dict(call.data))
    hass.services.async_register("select", "select_option", record)
    # Move the virtual grid sensor: updates run through Home Assistant events.
    hass.states.async_set(GRID, "4000", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    hass.states.async_set(GRID, "500", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    assert calls == []
    switch_id = entity_id(hass, v15, "switch", "evcc_live_control")
    assert hass.states.get(switch_id).state == "off"


async def test_integration_user_flow_shows_evcc_settings(hass: HomeAssistant):
    """The actual configuration flow must expose an optional evcc page."""
    set_virtual_states(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**BASE, CONF_EVCC_CONFIGURED: True}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "evcc"
    fields = {key.schema for key in result["data_schema"].schema}
    assert CONF_EVCC_CURRENT in fields
    assert CONF_EVCC_MODE in fields
    assert CONF_EVCC_POWER in fields


async def test_network_tariff_sensors_are_opt_in_and_informational(hass: HomeAssistant):
    """An actual HA config entry exposes three cost-preview entities."""
    from datetime import timedelta
    from homeassistant.util import dt as dt_util
    set_virtual_states(hass)
    entry = MockConfigEntry(
        domain=DOMAIN, title="V15 Tariff Lab", unique_id="v15_main",
        data=BASE,
        options={
            CONF_COST_CONFIGURED: True,
            CONF_COST_MODE: "draft2027",
            CONF_COST_REGION: "Burgenland",
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    peak = entity_id(hass, entry, "sensor", "network_peak")
    charge = entity_id(hass, entry, "sensor", "network_charge")
    target = entity_id(hass, entry, "sensor", "network_potential")
    assert hass.states.get(peak).state == "unknown"
    monitor = hass.data[DOMAIN][entry.entry_id]
    now = dt_util.now().replace(minute=0, second=0, microsecond=0)
    monitor.costs.complete_slot(
        now, now + timedelta(minutes=15), 1250, 900
    )
    monitor.notify()
    await hass.async_block_till_done()
    assert float(hass.states.get(peak).state) == 5.0
    assert float(hass.states.get(charge).state) == 17.0
    assert float(hass.states.get(target).state) == 0.0
    attributes = hass.states.get(charge).attributes
    assert attributes["not_an_invoice"] is True
    assert "Entwurf" in attributes["legal_status"]
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_no_hardware_connection_after_unload(hass: HomeAssistant, v15):
    """After a real HA unload, no active V15 runtime remains."""
    from custom_components.v15_lastmanagement.const import DOMAIN
    assert v15.entry_id in hass.data[DOMAIN]
    assert await hass.config_entries.async_unload(v15.entry_id)
    await hass.async_block_till_done()
    assert v15.entry_id not in hass.data[DOMAIN]


async def test_real_ha_service_path_reduces_virtual_evcc_current(
    hass: HomeAssistant, v15, freezer
):
    """Drive actual state events and the real HA service bus, never a device."""
    from datetime import datetime, timedelta, timezone

    calls = []

    async def virtual_select_service(call):
        calls.append((call.data["entity_id"], call.data["option"]))
        entity = call.data["entity_id"]
        if entity == CURRENT:
            hass.states.async_set(
                CURRENT, str(call.data["option"]),
                {"options": [str(n) for n in range(6, 17)]},
            )
        elif entity == MODE:
            hass.states.async_set(
                MODE, str(call.data["option"]),
                {"options": ["off", "smart", "now"]},
            )
        else:
            raise AssertionError(f"Unexpected select entity: {entity}")

    # The intercepted select service is the *only* charger endpoint.
    hass.services.async_register("select", "select_option", virtual_select_service)
    start = datetime(2026, 11, 10, 13, 0, tzinfo=timezone.utc)
    freezer.move_to(start)
    # HA preserves last_updated when only reporting the same state. Recreate
    # the virtual states under the frozen test clock so freshness is genuine.
    for lab_entity in (GRID, CURRENT, MODE, CHARGING, PHASES):
        hass.states.async_remove(lab_entity)
    set_virtual_states(hass)
    await hass.async_block_till_done()
    from homeassistant.util import dt as dt_util
    assert abs((dt_util.utcnow() - hass.states.get(CHARGING).last_updated).total_seconds()) < 5
    evcc_switch = entity_id(hass, v15, "switch", "evcc_live_control")
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": evcc_switch}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(evcc_switch).state == "on"

    # More than two simulated minutes, sampled every five seconds, are needed
    # to satisfy the 95% quarter-hour coverage requirement.
    for second in range(0, 146, 5):
        freezer.move_to(start + timedelta(seconds=second))
        hass.states.async_set(
            GRID, "9000", {"unit_of_measurement": "W"}, force_update=True
        )
        hass.states.async_set(
            CHARGING, "6.9", {"unit_of_measurement": "kW"}, force_update=True
        )
        await hass.async_block_till_done()

    assert (CURRENT, "6") in calls
    assert all(option != "now" for _, option in calls)
