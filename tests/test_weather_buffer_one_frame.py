"""One clock for the weather buffer, on the daily and the live path.

The scene is the install where the clock matters: the Home Assistant process runs at
UTC (a container started without ``TZ=``) and the user has set Europe/Berlin. The zone
was last calculated at 10:00 UTC -- 12:00 on the user's clock. Readings came in at
09:55, 11:00, 12:00 and 13:00 UTC, and it is now 13:00 UTC, 15:00 in Berlin. Three real
hours have passed, and the hours they cover are the user's 12:00-15:00.

Whichever path reads the buffer, and whichever release wrote it, it has to show a
window of exactly 3.0 h, hourly rows for the hours that start at 12:00, 13:00 and 14:00,
and the site's own offset, +2.0, on them. The daily path had the window right before
this change and the hours wrong: it measured the window on one clock, the process's, and
then priced the hours as if that clock were the user's. That is the half that moves the
solar radiation, and why the row hours are asserted everywhere, not the window alone.

Three hours, not one: the window length is ``abs(now - watermark)``, and with one hour
and a two-hour offset a process-clock ``now`` against a migrated watermark comes out at
|11:00 - 12:00| = 1 h -- the right answer for the wrong reason.

Two stores: one a release before 14.2 left on disk (process-local stamps, through the
real load and with it the store migration), and one this release's own writers filled,
clock read by clock read.

The process zone is substituted rather than set, because ``time.tzset()`` does not
exist on Windows. Under freezegun a bare ``datetime.now()`` reads the frozen instant as
UTC wall time whatever the machine's zone -- the container this scene needs.
"""

import ast
import datetime
import pathlib
import zoneinfo
from unittest.mock import AsyncMock, Mock

import pytest
from freezegun import freeze_time
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.irrigation_plus import (
    SmartIrrigationCoordinator,
    calculation,
    const,
    helpers,
    live_estimate,
)
from custom_components.irrigation_plus.et_estimate import SiteGeometry
from custom_components.irrigation_plus.store import STORAGE_KEY, SmartIrrigationStorage

UTC = datetime.UTC
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")
LAT, LON, ELEV = 50.0, 6.0, 200.0

# The user's 12:00-15:00, and nothing else: (row hour, row UTC offset) per hour.
EXPECTED_WINDOW_H = 3.0
EXPECTED_ROWS = [(12.5, 2.0), (13.5, 2.0), (14.5, 2.0)]

# A sensor group of fixed values: the poll writes a full row from it with no weather
# service and no entity state, and it carries the four fields the hourly form needs.
STATIC_GROUP = {
    field: {
        const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_STATIC_VALUE,
        const.MAPPING_CONF_STATIC_VALUE: value,
    }
    for field, value in (
        (const.MAPPING_TEMPERATURE, 20.0),
        (const.MAPPING_HUMIDITY, 50.0),
        (const.MAPPING_WINDSPEED, 2.0),
        (const.MAPPING_SOLRAD, 2.5),
    )
}

PACKAGE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "custom_components"
    / "irrigation_plus"
)


@pytest.fixture
def utc_container_berlin_user(monkeypatch):
    """The process at UTC, Home Assistant at Europe/Berlin."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    before = dt_util.get_default_time_zone()
    dt_util.set_default_time_zone(BERLIN)
    yield
    dt_util.set_default_time_zone(before)


@pytest.fixture
async def coordinators(hass):
    """Every coordinator a test builds, released at teardown.

    The constructor arms the midnight counter; left armed, the test ends on a
    lingering timer.
    """
    built = []
    yield built
    for c in built:
        c._track_midnight_time_unsub()


async def _coordinator(hass, store, built):
    """A real coordinator over a real store, on a site with coordinates."""
    hass.data[const.DOMAIN] = {
        const.CONF_USE_WEATHER_SERVICE: False,
        const.CONF_WEATHER_SERVICE: None,
    }
    hass.config.units = METRIC_SYSTEM
    hass.config.language = "en"
    entry = Mock()
    entry.unique_id = "t"
    entry.data = {}
    entry.options = {}
    c = SmartIrrigationCoordinator(hass, None, entry, store)
    built.append(c)
    c.store = store
    c._effective_latitude = LAT
    c._effective_longitude = LON
    c._effective_elevation = ELEV
    # Measured radiation and no forecast days: the configuration the hourly form
    # prices, on both paths.
    module = Mock()
    module.name = "PyETO"
    module._solrad_behavior = "3"
    module.forecast_days = 0
    module.calculate = Mock(return_value=0.0)
    c.getModuleInstanceByID = AsyncMock(return_value=module)
    # The published estimate is not what this file measures.
    c.async_refresh_zone_estimates = AsyncMock()
    c.async_refresh_zone_estimates_throttled = AsyncMock()
    return c


async def _new_store(hass):
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    await store.async_update_config({const.CONF_HOURLY_CALCULATION: True})
    return store


async def _add_zone(store):
    """A sensor group of fixed values, a PyETO module on it, and a zone on both."""
    mapping = await store.async_create_mapping(
        {
            const.MAPPING_NAME: "Static",
            const.MAPPING_MAPPINGS: STATIC_GROUP,
            const.MAPPING_DATA: [],
        }
    )
    module = await store.async_create_module(
        {
            const.MODULE_NAME: "PyETO",
            "description": "",
            "config": {
                const.CONF_PYETO_SOLRAD_BEHAVIOR: "3",
                const.CONF_PYETO_FORECAST_DAYS: 0,
            },
        }
    )
    zone = await store.async_create_zone(
        {
            const.ZONE_NAME: "Front",
            const.ZONE_MAPPING: mapping[const.MAPPING_ID],
            const.ZONE_MODULE: module[const.MODULE_ID],
            const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
            const.ZONE_BUCKET: 0.0,
            const.ZONE_THROUGHPUT: 10.0,
            const.ZONE_SIZE: 10.0,
            const.ZONE_MULTIPLIER: 1.0,
            const.ZONE_MAXIMUM_DURATION: 3600,
            const.ZONE_LEAD_TIME: 0,
        }
    )
    return zone[const.ZONE_ID]


def _row(stamp):
    return {
        const.RETRIEVED_AT: stamp,
        **{
            field: cfg[const.MAPPING_CONF_STATIC_VALUE]
            for field, cfg in STATIC_GROUP.items()
        },
    }


async def _store_from_an_older_release(hass, hass_storage, built):
    """The zone as a release before 14.2 left it on disk, loaded the way setup loads it.

    Written through this code's own API and save, then given what such a release wrote:
    minor version 1 and every one of the five stamps on the process's clock (UTC here).
    """
    first = await _new_store(hass)
    zone_id = await _add_zone(first)
    await first.async_save()
    document = hass_storage[STORAGE_KEY]
    document["minor_version"] = 1
    for zone in document["data"]["zones"]:
        for key in (
            const.ZONE_LAST_CALCULATED,
            const.ZONE_LAST_CONSUMED,
            const.ZONE_LAST_UPDATED,
        ):
            zone[key] = "2026-07-15T10:00:00"
    for mapping in document["data"]["mappings"]:
        mapping[const.MAPPING_DATA] = [
            _row("2026-07-15T09:55:00"),
            _row("2026-07-15T11:00:00"),
            _row("2026-07-15T12:00:00"),
            _row("2026-07-15T13:00:00"),
        ]
        mapping[const.MAPPING_DATA_LAST_UPDATED] = "2026-07-15T13:00:00"
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    return await _coordinator(hass, store, built), store, zone_id


async def _store_this_release_wrote(hass, frozen, built):
    """The zone as this release's writers leave it, each stamp from its own clock read."""
    store = await _new_store(hass)
    c = await _coordinator(hass, store, built)
    frozen.move_to("2026-07-15 09:50:00")
    zone_id = await _add_zone(store)  # anchors last_consumed_at
    frozen.move_to("2026-07-15 09:55:00")
    await c._async_update_all()  # the poll stamps a row
    frozen.move_to("2026-07-15 10:00:00")
    await c._async_calculate_all()  # the calculation stamps the zone
    # It swallows a zone's exception: a calculation that did not run must show here,
    # not later as a plausible window.
    assert store.get_zone(zone_id)[const.ZONE_LAST_CALCULATED] == datetime.datetime(
        2026, 7, 15, 12, 0
    )
    for hour in ("11:00", "12:00", "13:00"):
        frozen.move_to(f"2026-07-15 {hour}:00")
        await c._async_update_all()
    return c, store, zone_id


async def _daily(c, zone_id, monkeypatch):
    """The daily calculation's window and hourly rows, read off its own calls.

    Called without ``now``, so it reads its own clock the way the scheduled
    calculation does.
    """
    windows, rows = [], []
    aggregate_window = calculation.aggregate_window
    hourly_eto_priced = calculation.hourly_eto_priced

    def aggregate_spy(*args, **kwargs):
        out = aggregate_window(*args, **kwargs)
        windows.append(out[const.MAPPING_DATA_MULTIPLIER] * 24 if out else None)
        return out

    def priced_spy(*args, **kwargs):
        out = hourly_eto_priced(*args, **kwargs)
        rows.append([(r["hour"], r["tz_offset_h"]) for r in out[0]] if out else None)
        return out

    monkeypatch.setattr(calculation, "aggregate_window", aggregate_spy)
    monkeypatch.setattr(calculation, "hourly_eto_priced", priced_spy)
    await c.async_calculate_zone(zone_id)
    return windows, rows


def _window_h(aggregated):
    return aggregated[const.MAPPING_DATA_MULTIPLIER] * 24 if aggregated else None


async def _live(c, zone, monkeypatch):
    """The live estimate's windows and hourly rows, through the functions that read the store.

    ``now`` is the live refresh's own clock read (``_fetch_intraday_inputs``), so the
    process clock coming back there shows as well as a wrong anchor from the store. The
    second window is the call without ``now`` that ``_observed_precip_since_mm`` makes,
    which falls back on the aggregation's own default clock.
    """
    rows = []
    hourly_eto_priced = live_estimate.hourly_eto_priced

    def priced_spy(*args, **kwargs):
        out = hourly_eto_priced(*args, **kwargs)
        rows.append([(r["hour"], r["tz_offset_h"]) for r in out[0]] if out else None)
        return out

    monkeypatch.setattr(live_estimate, "hourly_eto_priced", priced_spy)
    anchor = live_estimate._window_anchor(zone)
    now_local = (await c._fetch_intraday_inputs())["now"]
    window = _window_h(c._aggregate_live_window(zone, anchor, now=now_local))
    default_clock_window = _window_h(c._aggregate_live_window(zone, anchor))
    c._buffer_hourly_et(
        zone, anchor, now=now_local, geometry=SiteGeometry(LAT, LON, ELEV, 2.0, BERLIN)
    )
    return window, default_clock_window, rows


class TestTheDailyPath:
    async def test_a_store_an_older_release_left(
        self, hass, hass_storage, coordinators, monkeypatch, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 13:00:00"):
            c, _, zone_id = await _store_from_an_older_release(
                hass, hass_storage, coordinators
            )
            windows, rows = await _daily(c, zone_id, monkeypatch)
        assert windows == [pytest.approx(EXPECTED_WINDOW_H)]
        assert rows == [EXPECTED_ROWS]

    async def test_a_store_this_release_wrote(
        self, hass, coordinators, monkeypatch, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 09:50:00") as frozen:
            c, _, zone_id = await _store_this_release_wrote(hass, frozen, coordinators)
            windows, rows = await _daily(c, zone_id, monkeypatch)
        assert windows == [pytest.approx(EXPECTED_WINDOW_H)]
        assert rows == [EXPECTED_ROWS]


class TestTheLivePath:
    async def test_a_store_an_older_release_left(
        self, hass, hass_storage, coordinators, monkeypatch, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 13:00:00"):
            c, store, zone_id = await _store_from_an_older_release(
                hass, hass_storage, coordinators
            )
            window, default_clock_window, rows = await _live(
                c, store.get_zone(zone_id), monkeypatch
            )
        assert window == pytest.approx(EXPECTED_WINDOW_H)
        assert default_clock_window == pytest.approx(EXPECTED_WINDOW_H)
        assert rows == [EXPECTED_ROWS]

    async def test_a_store_this_release_wrote(
        self, hass, coordinators, monkeypatch, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 09:50:00") as frozen:
            c, store, zone_id = await _store_this_release_wrote(
                hass, frozen, coordinators
            )
            window, default_clock_window, rows = await _live(
                c, store.get_zone(zone_id), monkeypatch
            )
        assert window == pytest.approx(EXPECTED_WINDOW_H)
        assert default_clock_window == pytest.approx(EXPECTED_WINDOW_H)
        assert rows == [EXPECTED_ROWS]


class TestEveryWriterStampsHAsClock:
    """Each writer the matrix does not reach, driven once: its stamp reads HA's wall clock.

    Frozen at 10:00 UTC with the user at Europe/Berlin, every stamp must read 12:00. The
    scene is built an hour earlier, so a writer that did not run cannot pass on the
    zone's creation stamp. The census below catches a bare ``datetime.now()`` coming
    back; these catch any other wrong clock -- ``dt_util.utcnow()`` stripped of its zone
    would pass the census. Three writers are pinned where they are tested already: the
    sensor-event row (``test_continuous_update.py::TestCoalescing``), the bucket
    assertion (``test_zone_view_save.py``) and zone creation
    (``test_store_operations.py::TestZoneOperations::test_new_zone_anchors_last_consumed_at``).
    """

    WALL = datetime.datetime(2026, 7, 15, 12, 0)

    @staticmethod
    async def _scene(hass, built, frozen):
        """The zone and its group at 09:00 UTC; then the clock moves to 10:00."""
        store = await _new_store(hass)
        c = await _coordinator(hass, store, built)
        zone_id = await _add_zone(store)
        frozen.move_to("2026-07-15 10:00:00")
        return c, store, zone_id, store.get_zone(zone_id)[const.ZONE_MAPPING]

    async def test_the_poll_of_every_group(
        self, hass, coordinators, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 09:00:00") as frozen:
            c, store, zone_id, mapping_id = await self._scene(
                hass, coordinators, frozen
            )
            await c._async_update_all()
        (row,) = store.get_mapping_buffer(mapping_id)
        assert row[const.RETRIEVED_AT] == self.WALL
        assert store.get_zone(zone_id)[const.ZONE_LAST_UPDATED] == self.WALL

    async def test_the_poll_of_one_zone(
        self, hass, coordinators, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 09:00:00") as frozen:
            c, store, zone_id, mapping_id = await self._scene(
                hass, coordinators, frozen
            )
            await c._async_update_zone(zone_id)
        (row,) = store.get_mapping_buffer(mapping_id)
        assert row[const.RETRIEVED_AT] == self.WALL
        mapping = store.get_mapping(mapping_id)
        assert mapping[const.MAPPING_DATA_LAST_UPDATED] == self.WALL
        assert store.get_zone(zone_id)[const.ZONE_LAST_UPDATED] == self.WALL

    async def test_clearing_the_weather_data(
        self, hass, coordinators, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 09:00:00") as frozen:
            c, store, zone_id, _ = await self._scene(hass, coordinators, frozen)
            await c._async_clear_all_weatherdata()
        assert store.get_zone(zone_id)[const.ZONE_LAST_CONSUMED] == self.WALL

    async def test_a_sensor_group_switching_its_source(
        self, hass, coordinators, utc_container_berlin_user
    ):
        switched = {
            **STATIC_GROUP,
            const.MAPPING_TEMPERATURE: {
                const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
                const.MAPPING_CONF_SENSOR: "sensor.temperature",
            },
        }
        with freeze_time("2026-07-15 09:00:00") as frozen:
            c, store, zone_id, mapping_id = await self._scene(
                hass, coordinators, frozen
            )
            await c.async_update_mapping_config(
                mapping_id, {const.MAPPING_MAPPINGS: switched}
            )
        assert store.get_zone(zone_id)[const.ZONE_LAST_CONSUMED] == self.WALL

    async def test_a_burst_of_sensor_events(
        self, hass, coordinators, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 09:00:00") as frozen:
            c, store, zone_id, mapping_id = await self._scene(
                hass, coordinators, frozen
            )
            await c._async_continuous_update_for_mapping(mapping_id)
        mapping = store.get_mapping(mapping_id)
        assert mapping[const.MAPPING_DATA_LAST_UPDATED] == self.WALL
        assert store.get_zone(zone_id)[const.ZONE_LAST_UPDATED] == self.WALL

    async def test_the_baseline_a_new_sensor_subscription_seeds(
        self, hass, coordinators, utc_container_berlin_user
    ):
        hass.states.async_set(
            "sensor.temperature", "20.0", {"unit_of_measurement": "°C"}
        )
        with freeze_time("2026-07-15 09:00:00") as frozen:
            c, store, _, mapping_id = await self._scene(hass, coordinators, frozen)
            await store.async_update_mapping(
                mapping_id,
                {
                    const.MAPPING_MAPPINGS: {
                        const.MAPPING_TEMPERATURE: {
                            const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
                            const.MAPPING_CONF_SENSOR: "sensor.temperature",
                        }
                    }
                },
            )
            await store.async_update_config({const.CONF_CONTINUOUS_UPDATES: True})
            await c.async_setup_continuous_updates()
        c.async_teardown_continuous_updates()
        (row,) = store.get_mapping_buffer(mapping_id)
        assert row[const.RETRIEVED_AT] == self.WALL


class TestTheSolarClampReadsTheUsersClock:
    """The ingest clamp pairs its clock with HA's UTC offset, so it needs HA's clock.

    A user at New York, the container at UTC, 13:30 on the user's clock (17:30 UTC). At
    this site clear sky allows 1244.8 W/m2 at 13:30 local and 814.5 W/m2 at 17:30 local, so
    a 1000 W/m2 reading passes at the hour it was taken and is clamped at the process's.
    """

    async def test_a_bright_early_afternoon_is_judged_at_its_own_hour(
        self, hass, coordinators
    ):
        before = dt_util.get_default_time_zone()
        dt_util.set_default_time_zone(zoneinfo.ZoneInfo("America/New_York"))
        try:
            store = await _new_store(hass)
            c = await _coordinator(hass, store, coordinators)
            c._effective_latitude = 39.68987
            c._effective_longitude = -84.07865
            c._effective_elevation = 311.0
            reading = 1000.0 * const.W_TO_MJ_DAY_FACTOR
            with freeze_time("2026-06-21 17:30:00"):
                clamped = c._clamp_solar_reading(reading)
        finally:
            dt_util.set_default_time_zone(before)
        assert clamped == pytest.approx(reading)


class TestNoProcessClockOnTheBufferPaths:
    """The modules that write or compare the buffer's stamps read HA's clock, not the process's.

    A tripwire, not a proof -- the matrix above is the proof. This catches a bare
    ``datetime.now()``, ``utcnow()`` or ``today()`` coming back into one of these modules
    at a place the matrix does not reach. If one is ever needed here for something else,
    list it with its reason.
    """

    MODULES = (
        "__init__.py",
        "auto_calc.py",
        "calculation.py",
        "continuous_update.py",
        "helpers.py",
        "live_estimate.py",
        "store.py",
        "weather_aggregate.py",
    )
    ALLOWED: frozenset = frozenset()

    @staticmethod
    def _is_stdlib_clock(node):
        if isinstance(node, ast.Name):
            return node.id in ("datetime", "dt_datetime", "date")
        return (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "datetime"
            and node.attr in ("datetime", "date")
        )

    def test_none_of_them_reads_the_process_clock(self):
        found = []
        for name in self.MODULES:
            tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("now", "utcnow", "today")
                    and self._is_stdlib_clock(node.func.value)
                ):
                    found.append(f"{name}:{node.lineno}")
        assert sorted(set(found) - self.ALLOWED) == []
