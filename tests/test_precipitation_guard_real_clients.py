"""The reported skip case through each REAL weather client, not a hand-built series.

Berlin, 2.15 mm forecast for 11:00-14:00 local on the 13th, threshold 2 mm,
look-ahead 1. Dispatch on the 12th morning: covered, dry, no skip. Dispatch on
the 13th morning: 2.15 mm, skip. Every other guard test feeds the window a
series written by the test itself; here each client parses a document shaped
like its own API, so a client that reads its own product wrongly is caught here
rather than in the field. The nine client cases are the maintainer's, offered
in review on the pull request.

The Pirate Weather document is not a model of a response but a real one:
``tests/fixtures/pirate_weather_berlin.json``, recorded from the live API on
2026-09-16 for Berlin (52.52/13.41) and trimmed to the keys the client reads.
Its stamps are moved onto this test's dates and the reported rain is placed in
the hour each case needs; the shape -- 168 hourly entries an hour apart, eight
daily blocks at local midnight -- is the recording's.

The last case is the one the nine structurally cannot reach: each of their
documents is built at ``now`` and so is freshly fetched, while the window's
coverage rule bites on a document the client has been serving from its cache
for most of a day.

The zone is set by the ``berlin`` fixture, which each test requests by name.
The repo's autouse fixtures hand every test a ``hass`` that sets US/Pacific,
and a fixture running before it would be overwritten. That is why this file
defines its own rather than importing the identical one next door: a plain
helper crosses test modules freely in this suite, a pytest fixture does not.
"""

import datetime
import json
import pathlib
from unittest.mock import MagicMock, patch

import homeassistant.util.dt as dt_util
import pytest
from freezegun import freeze_time

from custom_components.irrigation_plus.weathermodules.MetOfficeClient import (
    MetOfficeClient,
)
from custom_components.irrigation_plus.weathermodules.OpenMeteoClient import (
    OpenMeteoClient,
)
from custom_components.irrigation_plus.weathermodules.OWMClient import OWMClient
from custom_components.irrigation_plus.weathermodules.PirateWeatherClient import (
    PirateWeatherClient,
)
from tests.test_precipitation_guard import BERLIN, _config, _coordinator, _local
from tests.test_weather_modules import _openmeteo_doc

UTC = datetime.timezone.utc
# Rain 11:00-14:00 local on the 13th = 09:00-12:00Z. Every client's series is
# asked to carry it as the rate over the hour ENDING at 12:00Z.
RAIN_END = datetime.datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
RAIN_DATE = datetime.date(2026, 9, 13)
CASES = [
    ((2026, 9, 12, 6, 19), 0.0, False),
    ((2026, 9, 13, 6, 20), 2.15, True),
]

_FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "pirate_weather_berlin.json"
_PIRATE_SESSION = (
    "custom_components.irrigation_plus.weathermodules.PirateWeatherClient._SESSION.get"
)


@pytest.fixture
def berlin():
    original = dt_util.DEFAULT_TIME_ZONE
    dt_util.set_default_time_zone(BERLIN)
    try:
        yield
    finally:
        dt_util.set_default_time_zone(original)


def _response(doc):
    r = MagicMock()
    r.status_code = 200
    r.text = json.dumps(doc)
    return r


def _floor(dt, hours):
    dt = dt.replace(minute=0, second=0, microsecond=0)
    return dt - datetime.timedelta(hours=dt.hour % hours)


def _utc(stamp):
    return datetime.datetime.fromtimestamp(stamp, UTC)


def _owm_doc(now):
    first = _floor(now, 3) + datetime.timedelta(hours=3)
    entries = []
    for k in range(40):
        dt = first + datetime.timedelta(hours=3 * k)
        e = {
            "dt": int(dt.timestamp()),
            "main": {
                "temp": 15.0,
                "humidity": 70,
                "pressure": 1013,
                "temp_min": 12.0,
                "temp_max": 18.0,
            },
            "wind": {"speed": 3.0},
        }
        if dt == RAIN_END:
            e["rain"] = {"3h": 2.15}
        entries.append(e)
    return {"cod": "200", "list": entries}


def _pirate_doc(fetched_at, entries=None):
    """The recorded Berlin response, moved onto this test's dates.

    Wurzel: a hand-built Pirate Weather document can only show that the client
      reads back what the test wrote into it. The recorded one carries the block
      lengths, the one-hour spacing and the local-midnight daily boundaries the
      API really serves, so those are evidence here rather than assumption.
    Fix-Logik: the hourly stamps move by ONE offset, which keeps the block where
      the recording had it -- anchored on the hour the fetch began in -- and the
      daily stamps move by whole days, which keeps them on local midnight. Both
      the recorded and the test's dates lie in September CEST, so the day shift
      is exact. Only the precipitation values are the case's: the hour ending at
      ``RAIN_END`` carries the reported 2.15 mm/h, the local day it falls on the
      same total (0.215 cm, since the client reads SI centimetres), the rest dry.
      ``entries`` truncates the hourly block to the short one Pirate Weather
      serves without ``extend=hourly``.
    NOT-TO-DO: do not shift the daily blocks by the hourly offset. It is not a
      whole number of days, and their spans would stop being local days -- which
      is exactly what ``forecast_window.day_span`` prices a fill-in entry over.
    siehe tests/test_pirateweather_daily.py for the fixture's own checks
    """
    doc = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    hourly = doc["hourly"]["data"]
    if entries is not None:
        hourly = hourly[:entries]
    offset = _floor(fetched_at, 1) - _utc(hourly[0]["time"])
    for entry in hourly:
        stamp = _utc(entry["time"]) + offset
        entry["time"] = int(stamp.timestamp())
        entry["precipIntensity"] = 2.15 if stamp == RAIN_END else 0.0
    doc["hourly"]["data"] = hourly
    daily = doc["daily"]["data"]
    shift = datetime.timedelta(
        days=(
            fetched_at.astimezone(BERLIN).date()
            - _utc(daily[0]["time"]).astimezone(BERLIN).date()
        ).days
    )
    for block in daily:
        stamp = _utc(block["time"]) + shift
        block["time"] = int(stamp.timestamp())
        block["precipAccumulation"] = (
            0.215 if stamp.astimezone(BERLIN).date() == RAIN_DATE else 0.0
        )
    return doc


def _met_doc(now):
    first = _floor(now, 3)
    steps = []
    for k in range(7 * 8):
        t = first + datetime.timedelta(hours=3 * k)
        steps.append(
            {
                "time": t.strftime("%Y-%m-%dT%H:%MZ"),
                "maxScreenAirTemp": 18.0,
                "minScreenAirTemp": 12.0,
                "windSpeed10m": 3.0,
                "mslp": 101300,
                "screenRelativeHumidity": 70.0,
                # Accumulation over the three hours FOLLOWING the step.
                "totalPrecipAmount": (
                    2.15 if t == RAIN_END - datetime.timedelta(hours=3) else 0.0
                ),
            }
        )
    return {"features": [{"properties": {"timeSeries": steps}}]}


def _meteo_doc(now, extra_daily_mm=None):
    site_today = now.astimezone(BERLIN).date()
    doc = _openmeteo_doc(site_today, 7200)
    doc["hourly"]["precipitation"] = [
        2.15 if t == "2026-09-13T14:00" else 0.0 for t in doc["hourly"]["time"]
    ]
    doc["daily"]["precipitation_sum"] = [
        (
            2.15
            if d == "2026-09-13"
            else (extra_daily_mm if extra_daily_mm and d == "2026-09-14" else 0.0)
        )
        for d in doc["daily"]["time"]
    ]
    return doc


async def _run(client, patcher, config):
    with patcher:
        return await _coordinator(client)._eval_precipitation(config)


@pytest.mark.parametrize(("when", "observed", "skip"), CASES)
async def test_owm(berlin, when, observed, skip):
    now = _local(*when)
    with freeze_time(now):
        client = OWMClient(api_key="k", latitude=52.5, longitude=13.4)
        p = patch(
            "custom_components.irrigation_plus.weathermodules.OWMClient._SESSION.get",
            return_value=_response(_owm_doc(now)),
        )
        r = await _run(client, p, _config())
    assert (r["available"], r["observed"], r["would_skip"]) == (True, observed, skip)


@pytest.mark.parametrize(("when", "observed", "skip"), CASES)
async def test_pirate(berlin, when, observed, skip):
    now = _local(*when)
    with freeze_time(now):
        client = PirateWeatherClient("key", "1", 52.52, 13.41, 0)
        p = patch(_PIRATE_SESSION, return_value=_response(_pirate_doc(now)))
        r = await _run(client, p, _config())
    assert (r["available"], r["observed"], r["would_skip"]) == (True, observed, skip)


@pytest.mark.parametrize(("when", "observed", "skip"), CASES)
async def test_met_office_three_hourly_only(berlin, when, observed, skip):
    now = _local(*when)
    with freeze_time(now):
        client = MetOfficeClient(
            api_key="k", latitude=51.5, longitude=-0.1, elevation=10
        )
        p = patch.object(MetOfficeClient, "_request", return_value=_met_doc(now))
        r = await _run(client, p, _config())
    assert (r["available"], r["observed"], r["would_skip"]) == (True, observed, skip)


@pytest.mark.parametrize(("when", "observed", "skip"), CASES)
async def test_open_meteo(berlin, when, observed, skip):
    now = _local(*when)
    with freeze_time(now):
        client = OpenMeteoClient(latitude=52.52, longitude=13.41)
        p = patch(
            "custom_components.irrigation_plus.weathermodules.OpenMeteoClient._SESSION.get",
            return_value=_response(_meteo_doc(now)),
        )
        r = await _run(client, p, _config())
    assert (r["available"], r["observed"], r["would_skip"]) == (True, observed, skip)


async def test_open_meteo_daily_totals_do_not_add_to_the_series(berlin):
    # The daily entry for the 14th says 14 mm while the hourly series (which
    # covers the 14th) says dry: the series wins, nothing is counted twice.
    now = _local(2026, 9, 13, 6, 20)
    with freeze_time(now):
        client = OpenMeteoClient(latitude=52.52, longitude=13.41)
        p = patch(
            "custom_components.irrigation_plus.weathermodules.OpenMeteoClient._SESSION.get",
            return_value=_response(_meteo_doc(now, extra_daily_mm=14.0)),
        )
        r = await _run(client, p, _config(days=2))
    assert (r["available"], r["observed"], r["would_skip"]) == (True, 2.15, True)


# A run at 06:50 local on the 13th, with the client still serving the document
# it fetched 23 hours earlier at 07:50 local on the 12th -- one daily
# auto-update cycle, the interval that lets a cached document reach this age.
STALE_DISPATCH = _local(2026, 9, 13, 6, 50)
STALE_FETCH = STALE_DISPATCH - datetime.timedelta(hours=23)
# What a daily auto-update hands the client. Anything at least the document's
# age would do; the point is only that nothing refetches.
DAILY_UPDATE_CACHE_SECONDS = 86399


@pytest.mark.parametrize(
    ("entries", "available", "skip"), [(48, False, False), (168, True, True)]
)
async def test_a_cached_pirate_document_covers_the_window_only_with_the_long_block(
    berlin, entries, available, skip
):
    """A document old enough that the short hourly block stops inside the window.

    Wurzel: the guard measures its window as look-ahead x 24 h from the RUN's
      start and refuses to decide unless the first 24 of those hours are covered.
      Pirate Weather's hourly block without ``extend=hourly`` is 48 entries
      anchored on the hour the fetch began in, so it reaches floor(fetch) + 47 h,
      and ``get_forecast_data`` keeps serving one document for the whole
      configured update interval. Coverage therefore needs
      floor(fetch) + 47 h >= dispatch + 24 h. Writing the fetch as dispatch minus
      an age, and m for the minutes it sat into its own hour, that is
      age + m <= 23 h: the block stops short once the document is older than
      23 hours MINUS those minutes. Nothing fills the gap, because
      ``forecast_window._entries_behind`` admits a daily entry only where its
      span begins after the series' last stamp, and the day the series ends in
      began before it.
    Fix-Logik: the fetch above is 23 h before dispatch at 50 minutes past the
      hour, so m = 50 min and the short block misses the window's end by exactly
      those 50 minutes (series to the 14th 04:00Z, window to the 14th 04:50Z).
      It is the fetch MINUTE that decides at this age, and 50 of a possible 60
      sits far enough from the m = 0 edge -- where a document exactly 23 hours
      old would still just cover -- that no drift moves the case onto the
      passing side unnoticed. The long block this branch now asks for reaches
      floor(fetch) + 167 h and covers the window with days to spare.
    NOT-TO-DO: do not let this case fetch at dispatch. A refetch would hand the
      guard a document anchored at the run, the short block would cover the
      window too and the case would prove nothing -- hence the cache seconds and
      the assertion that no request is made. And do not read the short block's
      silence as "no rain in the series": both halves carry the 2.15 mm hour,
      which is asserted below.
    siehe custom_components/irrigation_plus/weathermodules/PirateWeatherClient.py
      (PirateWeather_URL) und tests/test_pirateweather_daily.py::
      test_the_request_asks_for_the_long_hourly_block
    """
    doc = _pirate_doc(STALE_FETCH, entries=entries)
    client = PirateWeatherClient(
        "key", "1", 52.52, 13.41, 0, cache_seconds=DAILY_UPDATE_CACHE_SECONDS
    )
    with freeze_time(STALE_FETCH), patch(_PIRATE_SESSION, return_value=_response(doc)):
        assert client.get_forecast_data(), "the fetch has to fill the client's cache"

    with freeze_time(STALE_DISPATCH), patch(_PIRATE_SESSION) as no_request:
        result = await _coordinator(client)._eval_precipitation(_config())

    no_request.assert_not_called()
    assert any(rate for _, rate in client.get_hourly_precipitation_forecast())
    assert (result["available"], result["would_skip"]) == (available, skip)
    assert result["observed"] == (2.15 if available else None)
