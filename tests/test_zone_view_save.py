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
import pathlib
import re
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from freezegun import freeze_time
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const
from custom_components.irrigation_plus.store import SmartIrrigationStorage
from custom_components.irrigation_plus.websockets import SmartIrrigationZoneView

T0 = datetime.datetime(2026, 5, 22, 6, 0, 0)
SAVED_AT = T0 + datetime.timedelta(hours=3)
LEDGER = [{"ts": T0.isoformat(), "mm": 1.0}]
PANEL = (
    pathlib.Path(__file__).parent.parent
    / "custom_components"
    / "irrigation_plus"
    / "frontend"
    / "src"
    / "views"
    / "zones"
    / "view-zone-settings.ts"
)


def test_the_panel_names_what_each_zone_edit_sets():
    """A tripwire on the panel's source, kept here because CI runs pytest only.

    Every settings input calls ``handleEditZone``. Handed ``{ ...zone, [FIELD]: v }``
    it posted the page's copy of the zone -- a pre-run bucket included, which the
    backend then booked as a level set by hand. Each call site now passes only
    what it sets. A tripwire, not a proof: a call site that copies the zone some
    other way walks straight past it.
    """
    src = PANEL.read_text(encoding="utf-8")
    calls = re.findall(r"this\.handleEditZone\(\s*\w+\s*,", src)
    # No length limit between the brace and the spread: in the deeper template
    # blocks the indentation alone is longer than a fixed window would allow.
    spreading = [
        src.count("\n", 0, m.start()) + 1
        for m in re.finditer(
            r"this\.handleEditZone\(\s*\w+\s*,\s*\{\s*\.\.\.zone\b", src
        )
    ]
    assert calls, "no handleEditZone call found: this pin no longer reads the panel"
    assert spreading == [], f"page copy of the zone spread at lines {spreading}"


def test_a_confirmed_zone_edit_finds_its_zone_by_id():
    """A confirm dialog runs its edit only when the user confirms.

    By then the page may have re-read its zones with one added or removed, and
    the index the dialog was opened with can hold another zone. With only the
    change posted, that zone's id decides which zone is written, so the reset
    dialog finds its zone again by the id it kept, and no confirmed action may
    reach handleEditZone with an index. A tripwire, not a proof.
    """
    src = PANEL.read_text(encoding="utf-8")
    by_id = re.findall(
        r"onConfirm:\s*\(\)\s*=>\s*this\._editZoneById\(\s*zone\.id\b", src
    )
    by_index = [
        src.count("\n", 0, m.start()) + 1
        for m in re.finditer(r"onConfirm:[^}]*?\bhandleEditZone\b", src)
    ]
    assert len(by_id) == 1, "the reset dialog no longer finds its zone by id"
    assert by_index == [], f"confirmed edit by index at lines {by_index}"


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


def _when_ha_reads(naive):
    """The instant at which HA's clock reads ``naive``.

    T0, SAVED_AT and the ledger are stamps on HA's clock, the frame the weather
    window is measured in, and a save stamps HA's clock too. Frozen at the bare
    naive time instead -- UTC wall time under freezegun -- the save would land
    hours before T0, with HA on US/Pacific as every test here has it.
    """
    return naive.replace(tzinfo=dt_util.get_default_time_zone())


async def _post(hass, data):
    """POST a zone save through the real view, the way the panel does."""
    request = MagicMock()
    request.app = {"hass": hass}
    request.json = AsyncMock(return_value=data)
    view = SmartIrrigationZoneView()
    view.json = MagicMock(return_value="OK")
    with freeze_time(_when_ha_reads(SAVED_AT)):
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


async def test_a_lone_bucket_is_clamped_to_the_stored_maximum(coordinator):
    """The form's bucket input posts the bucket alone; the cap still holds."""
    c, store = coordinator
    zid = await _zone(store, bucket=0.0, maximum_bucket=30.0)

    await _post(c.hass, {const.ZONE_ID: zid, const.ZONE_BUCKET: 50.0})

    assert store.get_zone(zid)[const.ZONE_BUCKET] == 30.0


async def test_a_lowered_maximum_clamps_the_stored_level_as_a_statement(
    coordinator,
):
    """Lowering the cap below the level clamps the level, as a whole-zone save
    did: the level moved because someone said where it can be, so the weather
    window restarts there (``_book_asserted_bucket``).
    """
    c, store = coordinator
    zid = await _zone(store, bucket=20.0, maximum_bucket=30.0)

    await _post(c.hass, {const.ZONE_ID: zid, const.ZONE_MAXIMUM_BUCKET: 10.0})

    after = store.get_zone(zid)
    assert after[const.ZONE_BUCKET] == 10.0
    assert after[const.ZONE_MAXIMUM_BUCKET] == 10.0
    # The moment of the save, on HA's clock -- the frame the window is measured in.
    assert after[const.ZONE_LAST_CONSUMED] == SAVED_AT
    assert after[const.ZONE_PENDING_BUCKET_EVENTS] == []


async def test_a_raised_maximum_leaves_the_level_and_the_window_alone(coordinator):
    """Completing the pair must not turn every maximum edit into a statement."""
    c, store = coordinator
    zid = await _zone(store, bucket=20.0, maximum_bucket=30.0)

    await _post(c.hass, {const.ZONE_ID: zid, const.ZONE_MAXIMUM_BUCKET: 40.0})

    after = store.get_zone(zid)
    assert after[const.ZONE_BUCKET] == 20.0
    assert after[const.ZONE_MAXIMUM_BUCKET] == 40.0
    assert after[const.ZONE_LAST_CONSUMED] == T0
    assert after[const.ZONE_PENDING_BUCKET_EVENTS] == LEDGER


async def test_a_new_zone_posted_with_a_bucket_and_no_maximum_is_created(
    coordinator,
):
    """Creating a zone has no stored zone to complete the pair from.

    The setup wizard and the panel's "add zone" both post a bucket without a
    maximum and without an id. Looking the missing value up would ask the store
    for zone ``None``, which it cannot answer.
    """
    c, store = coordinator

    await _post(
        c.hass,
        {
            const.ZONE_NAME: "New",
            const.ZONE_SIZE: 10.0,
            const.ZONE_THROUGHPUT: 5.0,
            const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
            const.ZONE_BUCKET: 0,
        },
    )

    assert [z[const.ZONE_NAME] for z in await store.async_get_zones()] == ["New"]


async def test_a_bucket_set_through_the_store_funnel_is_not_clamped(coordinator):
    """The pair is completed at the panel's boundary only.

    ``set_all_buckets`` posts a level without a maximum and has never been
    clamped. Completing the pair inside the store would change that for it and
    for every other writer the store serves.
    """
    c, store = coordinator
    zid = await _zone(store, bucket=0.0, maximum_bucket=30.0)

    with freeze_time(_when_ha_reads(SAVED_AT)):
        await c._async_set_all_buckets(50.0)

    assert store.get_zone(zid)[const.ZONE_BUCKET] == 50.0


async def test_a_post_that_carries_both_is_saved_as_it_was_posted(coordinator):
    """A whole-zone save, or two edits in one debounce window, carry both.

    Nothing is completed then: the stored value must not replace one the
    post names, or a cap raised together with the level would be lost.
    """
    c, store = coordinator
    zid = await _zone(store, bucket=0.0, maximum_bucket=30.0)

    await _post(
        c.hass,
        {
            const.ZONE_ID: zid,
            const.ZONE_BUCKET: 35.0,
            const.ZONE_MAXIMUM_BUCKET: 40.0,
        },
    )

    after = store.get_zone(zid)
    assert after[const.ZONE_BUCKET] == 35.0
    assert after[const.ZONE_MAXIMUM_BUCKET] == 40.0


async def test_a_lone_bucket_for_an_id_the_store_does_not_know_creates_the_zone(
    coordinator,
):
    """An unknown id is a create, so there is no stored zone to complete from."""
    c, store = coordinator

    await _post(
        c.hass,
        {
            const.ZONE_ID: 7,
            const.ZONE_NAME: "Imported",
            const.ZONE_SIZE: 10.0,
            const.ZONE_THROUGHPUT: 5.0,
            const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
            const.ZONE_BUCKET: 0,
        },
    )

    assert [z[const.ZONE_ID] for z in await store.async_get_zones()] == [7]
