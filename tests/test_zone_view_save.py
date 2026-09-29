"""A zone save through the panel's view: what is forwarded, and what lands.

The panel used to post the whole zone it held on every edit. That copy is
re-read only on ``_update_frontend``, which a run's credit does not send, so a
page left open across a run posted its pre-run bucket back, and
``_book_asserted_bucket`` took the stale level for one set by hand. The panel
now sends only what an edit set. Two things stay with the view:

* the strip list, for a panel still cached in a browser that keeps posting
  whole zones: nothing the server writes may come back through it;
* the bucket/maximum clamp, which the store applies only when one payload
  carries both. A panel edit carries one, so the view completes the pair from
  the stored zone -- at this boundary, not in the store, which every other
  bucket writer passes through too.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from freezegun import freeze_time
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const
from custom_components.irrigation_plus.store import SmartIrrigationStorage
from custom_components.irrigation_plus.websockets import SmartIrrigationZoneView

T0 = datetime.datetime(2026, 5, 22, 6, 0, 0)
SAVED_AT = T0 + datetime.timedelta(hours=3)
LEDGER = [{"ts": T0.isoformat(), "mm": 1.0}]


@pytest.fixture
async def coordinator(hass):
    """A real coordinator over a real in-memory store, reachable from the view."""
    hass.data[const.DOMAIN] = {
        const.CONF_USE_WEATHER_SERVICE: False,
        const.CONF_WEATHER_SERVICE: None,
    }
    hass.config.units = METRIC_SYSTEM
    hass.config.language = "en"
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    entry = Mock()
    entry.unique_id = "t"
    entry.data = {}
    entry.options = {}
    c = SmartIrrigationCoordinator(hass, None, entry, store)
    c.store = store
    hass.data[const.DOMAIN]["coordinator"] = c
    yield c, store
    # The constructor arms the midnight counter; left armed, the test ends with
    # a lingering timer.
    c._track_midnight_time_unsub()


async def _zone(store, *, bucket, maximum_bucket):
    zone = await store.async_create_zone(
        {
            const.ZONE_NAME: "Front",
            const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
            const.ZONE_BUCKET: bucket,
            const.ZONE_MAXIMUM_BUCKET: maximum_bucket,
            const.ZONE_THROUGHPUT: 10.0,
            const.ZONE_SIZE: 10.0,
            const.ZONE_LAST_CONSUMED: T0,
            const.ZONE_PENDING_BUCKET_EVENTS: list(LEDGER),
        }
    )
    return zone[const.ZONE_ID]


async def _post(hass, data):
    """POST a zone save through the real view, the way the panel does."""
    request = MagicMock()
    request.app = {"hass": hass}
    request.json = AsyncMock(return_value=data)
    view = SmartIrrigationZoneView()
    view.json = MagicMock(return_value="OK")
    with freeze_time(SAVED_AT):
        await view.post(request)


async def test_a_whole_zone_post_does_not_write_back_what_the_server_writes(
    coordinator,
):
    """A panel still cached in a browser posts the whole zone it holds.

    These six are written by the server alone -- the days-between counter by
    every credit, in the same write, the rest by the calculation -- and none has
    an input on the form. A pre-run copy of the counter would undo the wait the
    run had just restarted.
    """
    c, store = coordinator
    zid = await _zone(store, bucket=0.0, maximum_bucket=30.0)
    fresh = {
        const.ZONE_DAYS_SINCE_IRRIGATION: 0,
        const.ZONE_IRRIGATION_TARGET_BUCKET: 0.0,
        const.ZONE_DELTA: -1.5,
        const.ZONE_EXPLANATION: "fresh",
        const.ZONE_CURRENT_DRAINAGE: 0.4,
        const.ZONE_NUMBER_OF_DATA_POINTS: 24,
    }
    await store.async_update_zone(zid, dict(fresh))
    stale = {
        const.ZONE_DAYS_SINCE_IRRIGATION: 3,
        const.ZONE_IRRIGATION_TARGET_BUCKET: -2.0,
        const.ZONE_DELTA: -4.0,
        const.ZONE_EXPLANATION: "stale",
        const.ZONE_CURRENT_DRAINAGE: 1.2,
        const.ZONE_NUMBER_OF_DATA_POINTS: 7,
    }

    await _post(c.hass, {const.ZONE_ID: zid, const.ZONE_NAME: "renamed", **stale})

    after = store.get_zone(zid)
    assert after[const.ZONE_NAME] == "renamed"
    assert {key: after[key] for key in fresh} == fresh


async def test_an_edit_after_a_credit_keeps_the_credit(coordinator):
    """The backend half of the defect: a run credits, then the panel saves.

    Posting only the edited field, nothing of the credit may move -- not the
    level, the ledger entry it booked, the watermark or the days-between reset.
    """
    c, store = coordinator
    zid = await _zone(store, bucket=-6.2, maximum_bucket=30.0)
    await store.async_update_zone(zid, {const.ZONE_DAYS_SINCE_IRRIGATION: 4})
    with freeze_time(T0 + datetime.timedelta(hours=1)):
        await c.async_write_watered_bucket(zid, 0.0)
    credited = store.get_zone(zid)
    # The credit happened, or what follows proves nothing.
    assert credited[const.ZONE_BUCKET] == 0.0
    assert credited[const.ZONE_DAYS_SINCE_IRRIGATION] == 0
    assert len(credited[const.ZONE_PENDING_BUCKET_EVENTS]) == len(LEDGER) + 1

    await _post(c.hass, {const.ZONE_ID: zid, const.ZONE_NAME: "renamed"})

    after = store.get_zone(zid)
    assert after[const.ZONE_NAME] == "renamed"
    for key in (
        const.ZONE_BUCKET,
        const.ZONE_PENDING_BUCKET_EVENTS,
        const.ZONE_LAST_CONSUMED,
        const.ZONE_DAYS_SINCE_IRRIGATION,
    ):
        assert after[key] == credited[key], key
