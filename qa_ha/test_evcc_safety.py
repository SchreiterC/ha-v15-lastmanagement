"""Safety integration tests for optional evcc control in disposable HA 2026.11.

All charger endpoints are synthetic HA states and a local service handler.
No network, real evcc, go-e or Victron devices are accessed.
"""
from datetime import datetime, timedelta, timezone

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant.common import MockConfigEntry

from custom_components.v15_lastmanagement.const import (
    DOMAIN, CONF_GRID, CONF_LIMIT, CONF_RESERVE, CONF_REVERSED, CONF_LOADS,
    CONF_STALE, CONF_EVCC_CONFIGURED, CONF_EVCC_CURRENT, CONF_EVCC_MODE,
    CONF_EVCC_POWER, CONF_EVCC_PHASES, CONF_EVCC_FIXED_PHASES,
    CONF_EVCC_MIN_A, CONF_EVCC_MAX_A, CONF_EVCC_VOLTAGE, CONF_EVCC_MARGIN_W,
    CONF_EVCC_STABLE_S, CONF_EVCC_STEP_S, CONF_EVCC_ALLOW_PAUSE,
)

GRID = "sensor.evcc_lab_grid"
CURRENT = "select.evcc_lab_current"
MODE = "select.evcc_lab_mode"
CHARGING = "sensor.evcc_lab_charge"
PHASES = "sensor.evcc_lab_phases"
START = datetime(2026, 11, 10, 13, 0, tzinfo=timezone.utc)
OPTIONS_CURRENT = [str(a) for a in range(6, 17)]
OPTIONS_MODE = ["off", "smart", "now"]


def set_lab(hass: HomeAssistant, grid=1100, current=16, mode="smart", charge=6900):
    hass.states.async_set(GRID, str(grid), {"unit_of_measurement": "W"}, force_update=True)
    hass.states.async_set(CURRENT, str(current), {"options": OPTIONS_CURRENT}, force_update=True)
    hass.states.async_set(MODE, mode, {"options": OPTIONS_MODE}, force_update=True)
    hass.states.async_set(CHARGING, str(charge / 1000), {"unit_of_measurement": "kW"}, force_update=True)
    hass.states.async_set(PHASES, "3", force_update=True)


@pytest.fixture
async def evcc_lab(hass: HomeAssistant):
    set_lab(hass)
    entry = MockConfigEntry(
        domain=DOMAIN, title="V15 isolated evcc safety lab", unique_id="evcc_safety",
        data={
            CONF_GRID: GRID, CONF_LIMIT: 5.0, CONF_RESERVE: 0.5,
            CONF_REVERSED: False, CONF_LOADS: [], CONF_STALE: 120,
        },
        options={
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
            CONF_EVCC_ALLOW_PAUSE: True,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield entry
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


def monitor(hass: HomeAssistant, entry):
    return hass.data[DOMAIN][entry.entry_id]


def evcc_switch(hass: HomeAssistant, entry):
    result = er.async_get(hass).async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_evcc_live_control"
    )
    assert result is not None
    return result


async def setup_clock(hass: HomeAssistant, freezer, *, grid=1100, charge=6900):
    freezer.move_to(START)
    # Existing same-value HA states can retain last_updated from before the
    # frozen clock. Recreate them so freshness is checked for real.
    for entity in (GRID, CURRENT, MODE, CHARGING, PHASES):
        hass.states.async_remove(entity)
    set_lab(hass, grid=grid, charge=charge)
    await hass.async_block_till_done()
    assert abs((dt_util.utcnow() - hass.states.get(CHARGING).last_updated).total_seconds()) < 5


async def enable(hass: HomeAssistant, entry):
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": evcc_switch(hass, entry)}, blocking=True
    )
    await hass.async_block_till_done()
    assert monitor(hass, entry).evcc.enabled


async def sample(hass: HomeAssistant, freezer, second: int, grid: int, charge: int):
    freezer.move_to(START + timedelta(seconds=second))
    hass.states.async_set(GRID, str(grid), {"unit_of_measurement": "W"}, force_update=True)
    hass.states.async_set(
        CHARGING, str(charge / 1000), {"unit_of_measurement": "kW"}, force_update=True
    )
    await hass.async_block_till_done()


def charger_service(hass: HomeAssistant, commands, *, recovery_grid=0, confirm=True):
    """A synthetic evcc select service; never forwards anything to a device."""
    async def handle(call):
        entity = call.data["entity_id"]
        option = call.data["option"]
        assert entity in (CURRENT, MODE)
        commands.append((entity, option, dt_util.now()))
        if not confirm:
            return
        if entity == CURRENT:
            hass.states.async_set(CURRENT, option, {"options": OPTIONS_CURRENT})
        else:
            hass.states.async_set(MODE, option, {"options": OPTIONS_MODE})
            if option == "off":
                hass.states.async_set(
                    GRID, str(recovery_grid), {"unit_of_measurement": "W"}
                )
                hass.states.async_set(
                    CHARGING, "0.0", {"unit_of_measurement": "kW"}
                )
            elif option == "smart":
                # Virtual loadpoint resuming at 6A/3 phases. It is not real hardware.
                hass.states.async_set(GRID, "4140", {"unit_of_measurement": "W"})
                hass.states.async_set(
                    CHARGING, "4.14", {"unit_of_measurement": "kW"}
                )
    hass.services.async_register("select", "select_option", handle)


async def pump_until(hass, freezer, *, grid, charge, predicate, last=160):
    for second in range(0, last + 1, 5):
        await sample(hass, freezer, second, grid, charge)
        if predicate():
            return second
    raise AssertionError("Virtual evcc controller did not reach the expected state")


@pytest.mark.parametrize(
    ("recovery_grid", "should_resume"),
    [(0, True), (3000, False)],
)
async def test_owned_pause_requires_stable_budget_before_smart(
    hass: HomeAssistant, evcc_lab, freezer, recovery_grid, should_resume
):
    """An owned pause only resumes after headroom and the stability timer."""
    commands = []
    charger_service(hass, commands, recovery_grid=recovery_grid)
    await setup_clock(hass, freezer, grid=9000)
    await enable(hass, evcc_lab)
    off_at = await pump_until(
        hass, freezer, grid=9000, charge=6900,
        predicate=lambda: (MODE, "off") in [(e, v) for e, v, _ in commands],
    )
    ctrl = monitor(hass, evcc_lab).evcc
    assert ctrl.owned_pause
    assert hass.states.get(MODE).state == "off"
    assert not any(e == MODE and v == "smart" for e, v, _ in commands)

    # 90s of stable reserve are mandatory: no premature resume.
    for s in range(off_at + 5, off_at + 90, 5):
        await sample(hass, freezer, s, recovery_grid, 0)
    assert not any(e == MODE and v == "smart" for e, v, _ in commands)

    # Permit time to set 6A and wait the configured command-spacing interval.
    for s in range(off_at + 90, off_at + 180, 5):
        await sample(hass, freezer, s, recovery_grid, 0)
        if should_resume and any(e == MODE and v == "smart" for e, v, _ in commands):
            break

    saw_resume = any(e == MODE and v == "smart" for e, v, _ in commands)
    assert saw_resume is should_resume
    assert not any(e == MODE and v == "now" for e, v, _ in commands)
    if should_resume:
        assert (CURRENT, "6") in [(e, v) for e, v, _ in commands]
        assert hass.states.get(MODE).state == "smart"
        assert not ctrl.owned_pause
        assert ctrl.enabled
    else:
        assert hass.states.get(MODE).state == "off"
        assert ctrl.owned_pause


async def test_manual_now_while_paused_relinquishes_control(
    hass: HomeAssistant, evcc_lab, freezer
):
    """A user-owned 'now' mode after V15's pause is never overridden."""
    commands = []
    charger_service(hass, commands, recovery_grid=0)
    await setup_clock(hass, freezer, grid=9000)
    await enable(hass, evcc_lab)
    off_at = await pump_until(
        hass, freezer, grid=9000, charge=6900,
        predicate=lambda: monitor(hass, evcc_lab).evcc.owned_pause,
    )
    before_manual = len(commands)
    freezer.move_to(START + timedelta(seconds=off_at + 5))
    hass.states.async_set(MODE, "now", {"options": OPTIONS_MODE})
    await hass.async_block_till_done()
    for sec in range(off_at + 10, off_at + 150, 5):
        await sample(hass, freezer, sec, 0, 0)
    assert hass.states.get(MODE).state == "now"
    assert not monitor(hass, evcc_lab).evcc.enabled
    assert not any(e == MODE and v == "smart" for e, v, _ in commands[before_manual:])


async def test_competing_current_regulator_stops_v15(
    hass: HomeAssistant, evcc_lab, freezer
):
    """An independent HA automation changing max-current revokes ownership."""
    commands = []
    charger_service(hass, commands)
    await setup_clock(hass, freezer, grid=3900)
    await enable(hass, evcc_lab)
    limited_at = await pump_until(
        hass, freezer, grid=3900, charge=6900,
        predicate=lambda: any(e == CURRENT and v == "10" for e, v, _ in commands),
    )
    ctrl = monitor(hass, evcc_lab).evcc
    assert ctrl.enabled
    assert hass.states.get(CURRENT).state == "10"

    # Competing controller overwrites the V15 limit without a V15 service call.
    freezer.move_to(START + timedelta(seconds=limited_at + 5))
    hass.states.async_set(CURRENT, "12", {"options": OPTIONS_CURRENT})
    await hass.async_block_till_done()
    for sec in range(limited_at + 10, limited_at + 80, 5):
        await sample(hass, freezer, sec, 9000, 6900)
    assert not ctrl.enabled
    assert "extern verändert" in ctrl.status
    assert hass.states.get(CURRENT).state == "12"
    assert commands == [(CURRENT, "10", commands[0][2])]


async def test_unconfirmed_current_command_times_out_without_retry(
    hass: HomeAssistant, evcc_lab, freezer
):
    """Failed command acknowledgements stop V15 instead of looping commands."""
    commands = []
    charger_service(hass, commands, confirm=False)
    await setup_clock(hass, freezer, grid=3900)
    await enable(hass, evcc_lab)
    first = await pump_until(
        hass, freezer, grid=3900, charge=6900,
        predicate=lambda: bool(commands),
    )
    assert commands[0][0] == CURRENT
    assert hass.states.get(CURRENT).state == "16"
    for sec in range(first + 5, first + 50, 5):
        await sample(hass, freezer, sec, 3900, 6900)
    ctrl = monitor(hass, evcc_lab).evcc
    assert not ctrl.enabled
    assert "Rückmeldung" in ctrl.status
    assert len(commands) == 1


async def test_reload_does_not_unpause_v15_owned_evcc(
    hass: HomeAssistant, evcc_lab, freezer
):
    """Never auto-resume a V15-paused charger after a config entry reload."""
    commands = []
    charger_service(hass, commands, recovery_grid=0)
    await setup_clock(hass, freezer, grid=9000)
    await enable(hass, evcc_lab)
    off_at = await pump_until(
        hass, freezer, grid=9000, charge=6900,
        predicate=lambda: monitor(hass, evcc_lab).evcc.owned_pause,
    )
    assert hass.states.get(MODE).state == "off"
    assert await hass.config_entries.async_reload(evcc_lab.entry_id)
    await hass.async_block_till_done()
    ctrl = monitor(hass, evcc_lab).evcc
    assert not ctrl.enabled
    assert not ctrl.owned_pause
    count = len(commands)
    for sec in range(off_at + 5, off_at + 155, 5):
        await sample(hass, freezer, sec, 0, 0)
    assert len(commands) == count
    assert hass.states.get(MODE).state == "off"
    assert hass.states.get(evcc_switch(hass, evcc_lab)).state == "off"


async def test_manual_off_without_v15_pause_is_not_reversed(
    hass: HomeAssistant, evcc_lab, freezer
):
    """Manual OFF is not V15-owned, so even surplus power must not resume it."""
    commands = []
    charger_service(hass, commands)
    await setup_clock(hass, freezer, grid=1100)
    await enable(hass, evcc_lab)

    # First establish trusted measurements without any reason to shed current.
    for sec in range(0, 91, 5):
        await sample(hass, freezer, sec, 1100, 6900)
    assert not commands
    assert not monitor(hass, evcc_lab).evcc.owned_pause

    freezer.move_to(START + timedelta(seconds=95))
    hass.states.async_set(MODE, "off", {"options": OPTIONS_MODE})
    hass.states.async_set(CHARGING, "0.0", {"unit_of_measurement": "kW"})
    hass.states.async_set(GRID, "0", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    for sec in range(100, 255, 5):
        await sample(hass, freezer, sec, 0, 0)

    ctrl = monitor(hass, evcc_lab).evcc
    assert not ctrl.enabled
    assert not ctrl.owned_pause
    assert "extern verändert" in ctrl.status
    assert hass.states.get(MODE).state == "off"
    assert not commands


async def test_grid_meter_failure_blocks_resuming_owned_pause(
    hass: HomeAssistant, evcc_lab, freezer
):
    """After an owned pause, missing grid data cannot grant charging power."""
    commands = []
    charger_service(hass, commands, recovery_grid=0)
    await setup_clock(hass, freezer, grid=9000)
    await enable(hass, evcc_lab)
    off_at = await pump_until(
        hass, freezer, grid=9000, charge=6900,
        predicate=lambda: monitor(hass, evcc_lab).evcc.owned_pause,
    )

    freezer.move_to(START + timedelta(seconds=off_at + 5))
    hass.states.async_set(GRID, "unavailable", {"unit_of_measurement": "W"})
    hass.states.async_set(CHARGING, "0.0", {"unit_of_measurement": "kW"})
    await hass.async_block_till_done()
    original_commands = len(commands)
    for sec in range(off_at + 10, off_at + 180, 5):
        freezer.move_to(START + timedelta(seconds=sec))
        hass.states.async_set(
            CHARGING, "0.0", {"unit_of_measurement": "kW"}, force_update=True
        )
        await hass.async_block_till_done()

    ctrl = monitor(hass, evcc_lab).evcc
    assert ctrl.enabled
    assert ctrl.owned_pause
    assert hass.states.get(MODE).state == "off"
    assert len(commands) == original_commands
    assert not any(e == MODE and v == "smart" for e, v, _ in commands)
