"""A store older than 14.2 has its weather-buffer stamps moved onto HA's clock, once.

Up to minor version 1 the five stamps the weather-buffer paths compare -- three on each
zone, two on each sensor group -- were written by a bare ``datetime.now()``, the
PROCESS's clock. From 14.2 on they are naive on HA's clock, and loading an older store
rewrites what the release before left behind.

The process zone is substituted rather than set, because ``time.tzset()`` does not exist
on Windows.
"""

import copy
import datetime
import zoneinfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.irrigation_plus import const, helpers
from custom_components.irrigation_plus.store import (
    STORAGE_KEY,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
    MigratableStore,
    SmartIrrigationStorage,
)

UTC = datetime.UTC
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")
ZONE_STAMPS = (
    const.ZONE_LAST_CALCULATED,
    const.ZONE_LAST_CONSUMED,
    const.ZONE_LAST_UPDATED,
)


@pytest.fixture
def utc_container_berlin_user(monkeypatch):
    """The process at UTC, Home Assistant at Europe/Berlin: +2 h in July."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    before = dt_util.get_default_time_zone()
    dt_util.set_default_time_zone(BERLIN)
    yield
    dt_util.set_default_time_zone(before)


@pytest.fixture
def berlin_container_utc_user(monkeypatch):
    """The process at Europe/Berlin, Home Assistant at UTC: +1 h in January, +2 h in July."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: BERLIN)
    before = dt_util.get_default_time_zone()
    dt_util.set_default_time_zone(UTC)
    yield
    dt_util.set_default_time_zone(before)


def _data(*rows, stamp="2026-07-15T10:00:00"):
    """A store's data block: one zone and one sensor group, every stamp at ``stamp``."""
    return {
        "config": {},
        "zones": [{const.ZONE_ID: 1, **dict.fromkeys(ZONE_STAMPS, stamp)}],
        "mappings": [
            {
                const.MAPPING_ID: 1,
                const.MAPPING_DATA: [
                    {const.RETRIEVED_AT: row, const.MAPPING_TEMPERATURE: 20.0}
                    for row in (rows or (stamp,))
                ],
                const.MAPPING_DATA_LAST_UPDATED: stamp,
            }
        ],
    }


def _stamps(data):
    """Every stamp of a data block: the zone's three, each row's, the group's."""
    zone = data["zones"][0]
    mapping = data["mappings"][0]
    return (
        [zone[key] for key in ZONE_STAMPS]
        + [row[const.RETRIEVED_AT] for row in mapping[const.MAPPING_DATA]]
        + [mapping[const.MAPPING_DATA_LAST_UPDATED]]
    )


async def _migrate(hass, major, minor, data):
    store = MigratableStore(
        hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_MINOR_VERSION
    )
    return await store._async_migrate_func(major, minor, data)


async def _file_as_an_older_release_left_it(hass, hass_storage, *, minor=1):
    """A whole store document with process-local stamps, as setup will find it.

    Written through this code's API and save, so it hydrates; then given the minor
    version and the stamps a release before 14.2 wrote. ``minor=None`` drops the key,
    which is how releases older than HA's minor versions left it.
    """
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    mapping = await store.async_create_mapping(
        {const.MAPPING_NAME: "GW", const.MAPPING_MAPPINGS: {}, const.MAPPING_DATA: []}
    )
    await store.async_create_zone(
        {
            const.ZONE_NAME: "Front",
            const.ZONE_MAPPING: mapping[const.MAPPING_ID],
            const.ZONE_SIZE: 10.0,
            const.ZONE_THROUGHPUT: 10.0,
        }
    )
    await store.async_save()
    document = hass_storage[STORAGE_KEY]
    if minor is None:
        del document["minor_version"]
    else:
        document["minor_version"] = minor
    for zone in document["data"]["zones"]:
        zone.update(dict.fromkeys(ZONE_STAMPS, "2026-07-15T10:00:00"))
    for group in document["data"]["mappings"]:
        group[const.MAPPING_DATA] = [
            {const.RETRIEVED_AT: "2026-07-15T09:55:00", const.MAPPING_TEMPERATURE: 20.0}
        ]
        group[const.MAPPING_DATA_LAST_UPDATED] = "2026-07-15T10:00:00"
    return document


class TestTheFiveStampsMoveOntoHAsClock:
    async def test_every_stamp_moves_by_the_offset_in_one_pass(
        self, hass, utc_container_berlin_user
    ):
        """The watermark and the buffer it is compared with move together."""
        out = await _migrate(hass, 14, 1, _data())

        assert _stamps(out) == ["2026-07-15T12:00:00"] * 5

    async def test_each_stamp_is_read_at_its_own_dates_offset(
        self, hass, berlin_container_utc_user
    ):
        """The buffer keeps a week, enough to straddle a DST change.

        Today's offset for every stamp would read the January one an hour off.
        """
        out = await _migrate(
            hass, 14, 1, _data("2026-01-15T12:00:00", "2026-07-15T12:00:00")
        )

        rows = [row[const.RETRIEVED_AT] for row in out["mappings"][0][const.MAPPING_DATA]]
        assert rows == ["2026-01-15T11:00:00", "2026-07-15T10:00:00"]

    async def test_an_aware_stamp_is_read_as_the_instant_it_names(
        self, hass, utc_container_berlin_user
    ):
        out = await _migrate(hass, 14, 1, _data(stamp="2026-07-15T10:00:00+00:00"))

        assert _stamps(out) == ["2026-07-15T12:00:00"] * 5

    async def test_what_it_cannot_read_is_left_exactly_as_found(
        self, hass, utc_container_berlin_user
    ):
        data = {
            "config": {},
            "zones": [
                {
                    const.ZONE_ID: 1,
                    const.ZONE_LAST_CALCULATED: None,
                    const.ZONE_LAST_CONSUMED: "not a date",
                    const.ZONE_LAST_UPDATED: 12345,
                },
                {const.ZONE_ID: 2},
                "not a zone",
            ],
            "mappings": [
                # The field's legacy attrs default was the string "[]".
                {const.MAPPING_ID: 1, const.MAPPING_DATA: "[]"},
                {
                    const.MAPPING_ID: 2,
                    const.MAPPING_DATA: [
                        {const.MAPPING_TEMPERATURE: 20.0},
                        {const.RETRIEVED_AT: None},
                        "not a row",
                    ],
                    const.MAPPING_DATA_LAST_UPDATED: None,
                },
            ],
        }
        before = copy.deepcopy(data)

        out = await _migrate(hass, 14, 1, data)

        assert out["zones"] == before["zones"]
        assert out["mappings"] == before["mappings"]

    async def test_a_store_at_14_2_or_later_is_left_alone(
        self, hass, utc_container_berlin_user
    ):
        """The rewrite is not idempotent: run on an HA-local store it moves it again."""
        for minor in (2, 3):
            out = await _migrate(hass, 14, minor, _data(stamp="2026-07-15T12:00:00"))

            assert _stamps(out) == ["2026-07-15T12:00:00"] * 5

    async def test_an_older_major_is_moved_as_well(self, hass, utc_container_berlin_user):
        out = await _migrate(hass, 13, 1, _data())

        assert _stamps(out) == ["2026-07-15T12:00:00"] * 5


class TestThroughHomeAssistantsLoad:
    """The way setup meets it: Home Assistant's own Store decides to migrate."""

    async def test_a_14_1_file_is_moved_and_saved_as_14_2(
        self, hass, hass_storage, utc_container_berlin_user
    ):
        await _file_as_an_older_release_left_it(hass, hass_storage, minor=1)

        store = SmartIrrigationStorage(hass)
        await store.async_load()

        (zone,) = store.zones.values()
        assert (zone.last_calculated, zone.last_consumed_at, zone.last_updated) == (
            "2026-07-15T12:00:00",
        ) * 3
        (mapping,) = store.mappings.values()
        assert mapping.data_last_updated == "2026-07-15T12:00:00"
        assert [row[const.RETRIEVED_AT] for row in store.buffers[mapping.id]] == [
            "2026-07-15T11:55:00"
        ]
        saved = hass_storage[STORAGE_KEY]
        assert (saved["version"], saved["minor_version"]) == (14, 2)

    async def test_a_file_without_a_minor_version_counts_as_14_1(
        self, hass, hass_storage, utc_container_berlin_user
    ):
        await _file_as_an_older_release_left_it(hass, hass_storage, minor=None)

        store = SmartIrrigationStorage(hass)
        await store.async_load()

        (zone,) = store.zones.values()
        assert zone.last_consumed_at == "2026-07-15T12:00:00"


class TestARolledBackReleaseOpensTheFile:
    """What v2026.09.17 does with a file this release saved.

    Home Assistant refuses a stored MAJOR version above the one a Store reads
    (``UnsupportedStorageVersionError``, since HA 2026.3), which is why the stamps moved
    on the MINOR version. A release that knows only 14.1 opens a 14.2 file, runs its own
    two-argument migrate function on it and saves it back as 14.1. That is harmless only
    if the function leaves zones and buffers alone.

    The store below opens the file the way v2026.09.17 does: major 14, minor 1 (HA's
    default) and a migrate function with TWO parameters, so Home Assistant's own dispatch,
    not this test, decides to call it without the minor. Its body is this release's major
    steps. Against v2026.09.17's function they differ by one config default
    (``forecast_weather_entity``) and in nothing that touches zones or mappings -- read on
    2026-09-30; vendoring that release's function here would still hydrate against
    today's constants.
    """

    async def test_a_14_2_file_comes_back_untouched_and_is_saved_as_14_1(
        self, hass, hass_storage, utc_container_berlin_user
    ):
        await _file_as_an_older_release_left_it(hass, hass_storage, minor=1)
        await SmartIrrigationStorage(hass).async_load()  # the migration; saved as 14.2
        written = copy.deepcopy(hass_storage[STORAGE_KEY])
        assert (written["version"], written["minor_version"]) == (14, 2)

        seen = []

        class AsReleasedIn0917(MigratableStore):
            async def _async_migrate_func(self, old_version, data):
                seen.append(old_version)
                return await self._async_migrate_major(old_version, data)

        loaded = await AsReleasedIn0917(hass, 14, STORAGE_KEY).async_load()

        assert seen == [14]
        assert loaded["zones"] == written["data"]["zones"]
        assert loaded["mappings"] == written["data"]["mappings"]
        assert loaded["zones"][0][const.ZONE_LAST_CONSUMED] == "2026-07-15T12:00:00"
        saved = hass_storage[STORAGE_KEY]
        assert (saved["version"], saved["minor_version"]) == (14, 1)
