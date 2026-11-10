"""Safety-focused evcc state-machine tests, not a live-HA integration test."""
import asyncio
from datetime import datetime, timedelta, timezone
import types
import unittest
import importlib

# test_restore_monitor installs lightweight Home Assistant stubs.
from test_restore_monitor import clock, coordinator, const
from v15_test_package.evcc_control import V15EvccController


class State:
    def __init__(self, value, attrs=None):
        self.state=str(value)
        self.attributes=attrs or {}
        self.last_updated=clock.now


class Services:
    def __init__(self, hass):
        self.hass=hass
        self.calls=[]
    async def async_call(self, domain, method, data, blocking=False):
        self.calls.append((domain,method,dict(data)))
        entity=data['entity_id']
        self.hass.states[entity]=State(data.get('value',data.get('option')),
            self.hass.states[entity].attributes)


class Hass:
    def __init__(self):
        self.states={
            'sensor.grid':State(4500,{'unit_of_measurement':'W'}),
            'sensor.evcc_power':State(3500,{'unit_of_measurement':'W'}),
            'sensor.phases':State(3),
            'select.evcc_max':State(16,{'options':[str(i) for i in range(6,17)]}),
            'select.evcc_mode':State('smart',{'options':['smart','off','now']}),
        }
        self.services=Services(self)
        self.tasks=[]
    def async_create_task(self, co):
        task=asyncio.create_task(co)
        self.tasks.append(task)
        return task


class Monitor:
    def __init__(self, h):
        self.hass=h
        self.config={
            const.CONF_EVCC_CONFIGURED:True,
            const.CONF_EVCC_CURRENT:'select.evcc_max',
            const.CONF_EVCC_MODE:'select.evcc_mode',
            const.CONF_EVCC_POWER:'sensor.evcc_power',
            const.CONF_EVCC_PHASES:'sensor.phases',
            const.CONF_EVCC_FIXED_PHASES:3,
            const.CONF_EVCC_MIN_A:6,
            const.CONF_EVCC_MAX_A:16,
            const.CONF_EVCC_MARGIN_W:300,
            const.CONF_EVCC_VOLTAGE:230,
            const.CONF_EVCC_ALLOW_PAUSE:True,
            const.CONF_EVCC_STABLE_S:90,
            const.CONF_EVCC_STEP_S:30,
            const.CONF_STALE:120,
        }
        self.slot=datetime(2026,11,5,13,0,0,tzinfo=timezone.utc)
        self.simulation=False
        self.demo_data=False
        self.data={'trusted_for_control':True}
        self.cal={'budget_kw':4.5,'at_risk':False}
    def read_power(self):
        return float(self.hass.states['sensor.grid'].state)
    def calculate_current(self, now, watts):
        return self.cal
    def notify(self):
        pass

class TestEvccController(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        clock.now=datetime(2026,11,5,13,7,30,tzinfo=timezone.utc)
        self.h=Hass(); self.m=Monitor(self.h)
        self.ev=V15EvccController(self.m)
    def time(self, seconds):
        clock.now += timedelta(seconds=seconds)
        self.h.states['sensor.evcc_power'].last_updated=clock.now
    def test_disabled_by_default(self):
        self.assertFalse(self.ev.enabled)
        self.assertIsNone(self.ev.decide(clock.now,True,self.m.cal,4500))
    def test_non_smart_never_claimed(self):
        self.h.states['select.evcc_mode']=State('now',{'options':['off','smart','now']})
        with self.assertRaises(ValueError):self.ev.activate()
    def test_not_operating_in_simulation(self):
        self.ev.activate(); self.m.simulation=True
        self.assertIsNone(self.ev.decide(clock.now,True,self.m.cal,4500))
    def test_stale_charge_sensor_blocks_control(self):
        self.ev.activate()
        self.h.states['sensor.evcc_power'].last_updated -= timedelta(seconds=3600)
        self.assertIsNone(self.ev.decide(clock.now,True,self.m.cal,4500))
    def test_missing_phase_sensor_blocks_control(self):
        self.ev.activate()
        self.h.states['sensor.phases']=State(0)
        self.assertIsNone(self.ev.decide(clock.now,True,self.m.cal,4500))
    async def test_pauses_only_when_opted_in(self):
        self.ev.activate()
        self.m.config[const.CONF_EVCC_ALLOW_PAUSE]=False
        self.assertEqual(self.ev.decide(clock.now,True,self.m.cal,4500),('current',6))
        self.assertEqual(self.h.services.calls,[])
        self.m.config[const.CONF_EVCC_ALLOW_PAUSE]=True
        self.assertEqual(self.ev.decide(clock.now,True,self.m.cal,4500),('mode','off'))
        await self.ev.apply(('mode','off'))
        self.assertTrue(self.ev.owned_pause)
        self.assertEqual(self.h.states['select.evcc_mode'].state,'off')
    async def test_pause_and_resume_with_stability(self):
        self.ev.activate()
        await self.ev.apply(('mode','off'))
        self.h.states['sensor.grid']=State(0,{'unit_of_measurement':'W'})
        self.h.states['sensor.evcc_power']=State(0,{'unit_of_measurement':'W'})
        self.time(31)
        self.assertIsNone(self.ev.decide(clock.now,True,self.m.cal,0))
        self.time(91)
        self.assertEqual(self.ev.decide(clock.now,True,self.m.cal,0),('current',6))
        await self.ev.apply(('current',6))
        self.time(31)
        self.assertEqual(self.ev.decide(clock.now,True,self.m.cal,0),('mode','smart'))
        await self.ev.apply(('mode','smart'))
        self.assertFalse(self.ev.owned_pause)
        self.assertEqual(self.h.states['select.evcc_mode'].state,'smart')
    def test_untrusted_grid_never_actuates(self):
        self.ev.activate()
        self.assertIsNone(self.ev.decide(clock.now,False,self.m.cal,4500))
    def test_external_current_change_disables_control(self):
        self.ev.activate()
        self.h.states['select.evcc_max']=State(12,{'options':[str(i) for i in range(6,17)]})
        self.assertIsNone(self.ev.decide(clock.now,True,self.m.cal,4500))
        self.assertFalse(self.ev.enabled)
    def test_dry_run_calculates_target_without_control(self):
        # With 6 A three-phase charging the budget needs at least 4140 W.
        self.h.states['sensor.grid']=State(0,{'unit_of_measurement':'W'})
        self.h.states['sensor.evcc_power']=State(0,{'unit_of_measurement':'W'})
        self.m.simulation=True
        self.assertIsNone(self.ev.decide(clock.now, True, self.m.cal, 0))
        self.assertEqual(self.ev.target, 6)
        self.assertFalse(self.ev.enabled)

    async def test_number_current_entity(self):
        self.m.config[const.CONF_EVCC_CURRENT]='number.evcc_max'
        self.h.states['number.evcc_max']=State(16,{'min':6,'max':16})
        self.m.config[const.CONF_EVCC_ALLOW_PAUSE]=False
        self.ev.activate()
        await self.ev.apply(('current',6))
        self.assertEqual(self.h.services.calls[-1][0:2],('number','set_value'))
        self.assertEqual(self.h.states['number.evcc_max'].state,'6')

    def test_off_mode_not_owned_will_never_be_resumed(self):
        self.ev.activate()
        self.ev.last_confirmed_mode='off'  # another integration changed mode
        self.h.states['select.evcc_mode']=State('off',{'options':['smart','off','now']})
        self.assertIsNone(self.ev.decide(clock.now,True,self.m.cal,0))
        self.assertFalse(self.ev.owned_pause)

    def test_no_current_increase_before_stability(self):
        self.h.states['select.evcc_max']=State(6,{'options':[str(i) for i in range(6,17)]})
        self.h.states['sensor.grid']=State(0,{'unit_of_measurement':'W'})
        self.h.states['sensor.evcc_power']=State(0,{'unit_of_measurement':'W'})
        self.ev.activate()
        # For this test, original current is a permitted 16A snapshot.
        self.ev.original_current=16
        self.m.cal['budget_kw']=6.0
        self.assertIsNone(self.ev.decide(clock.now,True,self.m.cal,0))
        self.time(89)
        self.assertIsNone(self.ev.decide(clock.now,True,self.m.cal,0))
        self.time(2)
        self.assertEqual(self.ev.decide(clock.now,True,self.m.cal,0),('current',7))

    def test_external_mode_change_stops_control(self):
        self.ev.activate()
        self.h.states['select.evcc_mode']=State('now',{'options':['smart','off','now']})
        self.assertIsNone(self.ev.decide(clock.now,True,self.m.cal,4500))
        self.assertFalse(self.ev.enabled)

    def test_restart_starts_in_disabled_state(self):
        self.ev.activate()
        self.assertFalse(V15EvccController(self.m).enabled)

if __name__=='__main__':unittest.main()
