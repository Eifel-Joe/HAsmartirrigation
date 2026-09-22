"""The sequential chain delivers the run its cycle planned (Eifel-Joe#2).

``Chain.zones`` holds bare ids and ``_chain_advance`` re-reads the stored zone, so
everything the dispatching cycle decided about a queued zone — the live duration and
the live-estimate marker — used to be dropped between the two. A sibling
``Chain.planned`` now carries it, mirroring how ``Rotation.remaining`` already carries
the rotating half's own plan.

The fixtures come from test_service_chain.py, whose ``_coord`` spy records
``(zone_id, duration)`` for every dispatch.
"""

from custom_components.irrigation_plus import const

from .test_service_chain import (
    SEQUENTIAL,
    _coord,
    _dispatch,
    _finish,
    _register,
    _zone,
)


def _live(zone, duration):
    """What irrigation._apply_live_durations hands the dispatcher: a COPY."""
    return {**zone, const.ZONE_DURATION: duration}


class TestTheQueueRemembersWhatTheCycleDecided:
    async def test_a_queued_zone_waters_the_live_duration_not_the_stored_one(
        self, hass
    ):
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [_live(z1, 300), _live(z2, 300)])
        await _finish(c, 1)
        assert c._dispatched == [(1, 300.0), (2, 300.0)]

    async def test_a_zone_stored_at_zero_still_waters_its_live_duration(self, hass):
        """The severe case: the daily calc said 0, the live estimate said 300.

        Reachable because the live gate drops the stored-duration pre-filter
        (irrigation.py:851), so "stored 0, live 300" is an ordinary state. Before
        the plan existed, the re-read saw 0 and the zone was skipped in silence.
        """
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=0))
        await _dispatch(c, [_live(z1, 600), _live(z2, 300)])
        await _finish(c, 1)
        assert c._dispatched == [(1, 600.0), (2, 300.0)]

    async def test_the_plan_records_whether_the_cycle_sized_the_zone_live(
        self, hass
    ):
        c = _coord(hass, SEQUENTIAL)
        z1, z2, z3 = _register(
            c, _zone(1, duration=600), _zone(2, duration=600), _zone(3, duration=600)
        )
        c._live_run_zones = {1, 2}
        await _dispatch(c, [_live(z1, 300), _live(z2, 300), z3])
        planned = c._chain_state(const.WATERING_MODE_SERVICE).planned
        assert planned[2].live is True
        assert planned[3].live is False

    async def test_a_zone_with_no_plan_falls_back_to_the_stored_duration(self, hass):
        """Drift must degrade to today's behaviour, never to a dropped zone.

        Not reachable today — ``async_dispatch_chained_zones`` always builds
        ``planned`` and ``zones`` together — so the drift is built by hand here
        on purpose, as a safety net against a future edit that could separate
        them.
        """
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [z1, z2])
        state = c._chain_state(const.WATERING_MODE_SERVICE)
        state.planned.clear()  # simulate the two structures drifting apart
        await _finish(c, 1)
        assert c._dispatched == [(1, 600.0), (2, 600.0)]

    async def test_a_partial_plan_only_decides_the_zone_that_has_one(self, hass):
        """Partial drift is the realistic form: one entry goes, the others stay."""
        c = _coord(hass, SEQUENTIAL)
        z1, z2, z3 = _register(
            c, _zone(1, duration=600), _zone(2, duration=600), _zone(3, duration=600)
        )
        await _dispatch(c, [_live(z1, 300), _live(z2, 300), _live(z3, 300)])
        c._chain_state(const.WATERING_MODE_SERVICE).planned.pop(3)
        await _finish(c, 1)
        await _finish(c, 2)
        assert c._dispatched == [(1, 300.0), (2, 300.0), (3, 600.0)]

    async def test_the_stored_duration_no_longer_decides_a_planned_zone(self, hass):
        """A calculation landing mid-chain cannot shorten or delete the run."""
        c = _coord(hass, SEQUENTIAL)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [z1, z2])
        c._zones[2] = {**c._zones[2], const.ZONE_DURATION: 0}
        await _finish(c, 1)
        assert c._dispatched == [(1, 600.0), (2, 600.0)]
