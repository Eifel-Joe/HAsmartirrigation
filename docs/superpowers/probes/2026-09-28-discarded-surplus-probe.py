"""Does the cycle's own run discard the surplus an external run created?

Measured on master 6acfc819: zone 1 watering, zone 2 queued, zone 2 watered
externally, then zone 1 finishes and zone 2 is dispatched anyway. The number in
question is the bucket that dispatch WRITES, against the bucket the water it
delivered would imply.
"""

from types import SimpleNamespace

from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.irrigation_plus import const

from tests.test_service_chain import (
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
    z[const.ZONE_IRRIGATION_TARGET_BUCKET] = 0
    return z


async def test_probe_the_surplus_the_second_run_writes(hass):
    c = _coord(hass, SEQUENTIAL)
    c.hass.config = SimpleNamespace(units=METRIC_SYSTEM)
    c._observed_on_since = {}
    c._observed_zone_by_entity = {}
    z1, z2 = _register(c, _observed_zone(1), _observed_zone(2))

    await _dispatch(c, [z1, z2])

    # The external run of zone 2, through the real credit path.
    await c._credit_observed_watering(2, 600)
    credited = c.async_write_watered_bucket.await_args.args[1]
    print(f"\n  external credit writes bucket: {credited:.3f}")

    # async_write_watered_bucket is a mock here, so apply what it was told to
    # write -- that is the store state the cycle's dispatch would read.
    c._zones[2][const.ZONE_BUCKET] = credited
    c.async_write_watered_bucket.reset_mock()

    await _finish(c, 1)

    print(f"  dispatched:                    {c._dispatched}")
    writes = [call.args for call in c.async_write_watered_bucket.await_args_list]
    print(f"  buckets the cycle's run wrote: {writes}")
    ceiling = c._run_ceiling(dict(c._zones[2], **{const.ZONE_BUCKET: credited}))
    print(f"  ceiling for that run:          {ceiling}")
    print(f"  pre + delivered depth:         {credited + 20.0:.3f}")
