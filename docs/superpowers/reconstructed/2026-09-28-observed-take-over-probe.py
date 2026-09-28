"""Does an observed take-over reach the chain at all? (master 6acfc819)"""

from types import SimpleNamespace

import custom_components.irrigation_plus.observed_watering as ow
from custom_components.irrigation_plus import const

from .test_service_chain import (
    SEQUENTIAL,
    _coord,
    _dispatch,
    _finish,
    _register,
    _zone,
)


def _observed_zone(zone_id, duration=600):
    z = _zone(zone_id, duration=duration)
    z[const.ZONE_OBSERVED_ENTITY] = f"switch.external_{zone_id}"
    z[const.ZONE_SIZE] = 5.0
    z[const.ZONE_THROUGHPUT] = 3.1
    z[const.ZONE_MAXIMUM_DURATION] = 3600
    z[const.ZONE_FLOW_SENSOR] = None
    z[const.ZONE_BUCKET] = -20.0
    return z


async def test_an_observed_take_over_on_a_queued_sequential_zone(hass):
    c = _coord(hass, SEQUENTIAL)
    c.hass.config = SimpleNamespace(units=ow.METRIC_SYSTEM)
    c._observed_on_since = {}
    c._observed_zone_by_entity = {}
    z1, z2 = _register(c, _observed_zone(1), _observed_zone(2))

    await _dispatch(c, [z1, z2])
    state = c._chain_state(const.WATERING_MODE_SERVICE)
    print(f"\n  nach dispatch:        dispatched={c._dispatched}  queue={list(state.zones)}")

    # Zone 2 is watered for 10 minutes by something outside the integration and
    # closes again -- the real observed credit path, not a simulation of it.
    await c._credit_observed_watering(2, 600)
    credited = c.async_write_watered_bucket.await_args
    state = c._chain_state(const.WATERING_MODE_SERVICE)
    print(f"  observed gutgeschrieben: bucket -> {credited.args[1] if credited else None}")
    print(f"  run vermerkt als:        {c._record_run.call_args.kwargs.get('result')}")
    print(f"  queue DANACH:            {list(state.zones)}  <-- entscheidet es")
    print(f"  zone_run_in_flight(2):   {c.zone_run_in_flight(2)}")

    await _finish(c, 1)

    print(f"  nach zone 1s Lauf:    dispatched={c._dispatched}")
    second = [d for d in c._dispatched if d[0] == 2]
    assert not second, f"DEFEKT: Zone 2 erneut dispatcht nach externer Bewaesserung: {second}"
