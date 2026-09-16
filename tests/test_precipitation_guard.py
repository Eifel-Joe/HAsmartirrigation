"""The precipitation skip guard examines the 24 hours from the run's start.

Rebuilt from the case reported in #137, in Europe/Berlin. Forecast: 2.15 mm on
the 13th, window 1 day, threshold 2 mm. The guard used to read the day AFTER the
run: it skipped the dry 12th for the 13th's rain and let the 13th water, because
by then it was looking at the 14th.

Europe/Berlin is UTC+2 in September, so a local stamp is two hours earlier in
UTC; every expectation below is derived from the UTC block bounds.

The zone is set by the ``berlin`` fixture, which each test requests by name. The
repo's autouse fixtures hand every test a ``hass`` that sets US/Pacific, and a
fixture running before it would be overwritten.
"""

import datetime
import logging
import zoneinfo
from types import SimpleNamespace
from unittest.mock import Mock, patch

import homeassistant.util.dt as dt_util
import pytest
import requests
from freezegun import freeze_time

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const
from custom_components.irrigation_plus.skip_conditions import SKIP_PRECIPITATION
from custom_components.irrigation_plus.weathermodules import OWMClient as owm_module

UTC = datetime.timezone.utc
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")


@pytest.fixture
def berlin():
    original = dt_util.DEFAULT_TIME_ZONE
    dt_util.set_default_time_zone(BERLIN)
    try:
        yield
    finally:
        dt_util.set_default_time_zone(original)


def _local(*args):
    return datetime.datetime(*args, tzinfo=BERLIN).astimezone(UTC)


# The reported forecast's rain on the 13th, in the hour ending 14:00 local.
AFTERNOON = _local(2026, 9, 13, 14, 0)
# The run the guard is asked about below: 06:20 local on the 13th = 04:20Z.
RUN = _local(2026, 9, 13, 6, 20)
# Three rain moments around that run's start, the only thing the three boundary
# tests below vary. The hour ending 06:00 local on the 13th (03:00-04:00Z) falls
# 20 minutes short of it; the hour ending 07:00 local (04:00-05:00Z) straddles
# it; the hour ending 02:00 local on the 14th (13th 23:00-14th 00:00Z) falls
# inside its first 24 hours although the local date has turned over.
BEFORE_THE_RUN = _local(2026, 9, 13, 6, 0)
ACROSS_THE_RUN = _local(2026, 9, 13, 7, 0)
THE_NIGHT_AFTER = _local(2026, 9, 14, 2, 0)
# Rain the evening after a morning run: inside the 24 hours from the RUN
# (13th 04:20Z-14th 04:20Z), outside the 24 hours from an evaluation at 20:00
# local on the 12th (12th 18:00Z-13th 18:00Z).
THE_EVENING_AFTER = _local(2026, 9, 13, 22, 0)
# Every boundary test below evaluates here, the evening before the run, so the
# evaluation never clips the window and the rain moment is the only variable.
THE_EVENING_BEFORE = _local(2026, 9, 12, 20, 0)


def _forecast_days(rain_on):
    """UTC-day entries after today's UTC date, as OWM builds them.

    The list runs past the end of ``_hourly``'s series (16th 22:00Z) so that one
    entry -- the UTC 17th, starting two hours after it -- still lies behind the
    series and reaches the fill-in path in ``_entries_behind``. Stopping at the
    15th, as this did while the series was three days long, would leave that
    function returning nothing in every test using ``_client``.
    """
    today = dt_util.utcnow().date()
    out = []
    for d in (12, 13, 14, 15, 16, 17):
        start = datetime.datetime(2026, 9, d, tzinfo=UTC)
        if start.date() <= today:
            continue
        out.append(
            {
                const.FORECAST_DAY_START: start,
                const.FORECAST_DAY_END: start + datetime.timedelta(days=1),
                const.MAPPING_PRECIPITATION: 2.15 if start.date() == rain_on else 0.0,
            }
        )
    return out


def _hourly(rain_ending_at):
    """Hourly stamps from the local 12th to the local 17th, with one rainy hour.

    Five days, so a two-block window from an evening run on the 13th still ends
    inside the series and the rain a window of 1 must NOT reach has a stamp.
    """
    first = _local(2026, 9, 12, 0, 0)
    out = []
    for h in range(1, 121):
        stamp = first + datetime.timedelta(hours=h)
        out.append((stamp, 2.15 if stamp == rain_ending_at else 0.0))
    return out


def _client(rain_ending_at=AFTERNOON):
    rain_on = (rain_ending_at - datetime.timedelta(hours=1)).date()
    return SimpleNamespace(
        get_forecast_data=lambda: _forecast_days(rain_on),
        get_hourly_precipitation_forecast=lambda: _hourly(rain_ending_at),
    )


def _daily_only_client():
    return SimpleNamespace(get_forecast_data=lambda: _forecast_days(AFTERNOON.date()))


def _coordinator(client):
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    hass = Mock()

    async def run_executor(func, *args):
        return func(*args)

    hass.async_add_executor_job = run_executor
    coord.hass = hass
    coord._WeatherServiceClient = client
    return coord


def _config(enabled=True, days=1):
    return {
        const.CONF_SKIP_IRRIGATION_ON_PRECIPITATION: enabled,
        const.CONF_PRECIPITATION_THRESHOLD_MM: 2,
        const.CONF_PRECIPITATION_FORECAST_DAYS: days,
        const.CONF_USE_WEATHER_SERVICE: True,
    }


async def test_the_dry_day_before_the_rain_is_not_skipped(berlin):
    with freeze_time(_local(2026, 9, 12, 6, 19)):
        result = await _coordinator(_client())._eval_precipitation(_config())
    assert result["id"] == SKIP_PRECIPITATION
    assert result["available"] is True
    assert result["observed"] == 0.0
    assert result["would_skip"] is False


async def test_the_rain_day_itself_is_skipped(berlin):
    with freeze_time(_local(2026, 9, 13, 6, 20)):
        result = await _coordinator(_client())._eval_precipitation(_config())
    assert result["observed"] == 2.15
    assert result["would_skip"] is True


async def test_the_evening_outlook_for_tomorrow_looks_at_tomorrow(berlin):
    # The #137 case as a preview: asked the evening before about tomorrow's run.
    with freeze_time(THE_EVENING_BEFORE):
        result = await _coordinator(_client())._eval_precipitation(_config(), RUN)
    assert result["observed"] == 2.15
    assert result["would_skip"] is True


async def test_the_window_is_anchored_at_the_run_not_at_the_evaluation(berlin):
    # The test above no longer tells the two apart: a rolling window from the
    # evaluation (12th 18:00Z-13th 18:00Z) already reaches the reported afternoon
    # rain, which under a calendar-date window was a whole date away. This rain
    # sits in the 10h20m tail the two windows do not share, so only a window
    # anchored at the run's start sees it. Do not fold this back into the case
    # above as a parameter -- it exists to fail when the anchor slips.
    with freeze_time(THE_EVENING_BEFORE):
        result = await _coordinator(_client(THE_EVENING_AFTER))._eval_precipitation(
            _config(), RUN
        )
    assert result["observed"] == 2.15
    assert result["would_skip"] is True


async def test_rain_before_the_run_starts_does_not_count(berlin):
    # The boundary is the run, not a date: this rain falls on the run's own local
    # date -- and the calendar-date window counted it -- but the hour it falls in
    # ends at 04:00Z, 20 minutes before the run begins.
    with freeze_time(THE_EVENING_BEFORE):
        result = await _coordinator(_client(BEFORE_THE_RUN))._eval_precipitation(
            _config(), RUN
        )
    assert (result["observed"], result["would_skip"]) == (0.0, False)


async def test_rain_in_the_hour_the_run_starts_in_counts_from_the_start(berlin):
    # The boundary itself, and a case NEW with the run anchor: while the window
    # began at local midnight a partial hour at its start could not occur, because
    # every client's hours begin on the hour. The run starts at 04:20Z inside the
    # hour 04:00-05:00Z, so 40 of that hour's 60 minutes lie in the window and
    # 2.15 mm/h contributes 2.15 * 40/60 = 1.4333 mm, shown as 1.43. Below the
    # 2 mm threshold: this user sees 1.43 on the chip and waters.
    with freeze_time(THE_EVENING_BEFORE):
        result = await _coordinator(_client(ACROSS_THE_RUN))._eval_precipitation(
            _config(), RUN
        )
    assert (result["observed"], result["would_skip"]) == (1.43, False)


async def test_rain_in_the_night_after_the_run_starts_counts(berlin):
    # The far side of the same boundary: past local midnight, so the calendar-date
    # window put this rain on the day AFTER the run and missed it, while the block
    # 04:20Z-04:20Z reaches it with 4h20m to spare.
    with freeze_time(THE_EVENING_BEFORE):
        result = await _coordinator(_client(THE_NIGHT_AFTER))._eval_precipitation(
            _config(), RUN
        )
    assert (result["observed"], result["would_skip"]) == (2.15, True)


@pytest.mark.parametrize(
    ("days", "rain_at", "observed", "would_skip"),
    [
        (1, _local(2026, 9, 14, 6, 0), 2.15, True),
        (1, _local(2026, 9, 15, 6, 0), 0.0, False),
        (2, _local(2026, 9, 15, 6, 0), 2.15, True),
    ],
)
async def test_an_evening_run_with_a_one_day_window_sees_the_next_morning(
    berlin, days, rain_at, observed, would_skip
):
    # Asked for on the pull request: a 21:00 run with a look-ahead of 1 skips for
    # rain at 06:00 the next day. The calendar-date window saw only the three
    # hours left of the 13th and needed a look-ahead of 2 for that rain, which on
    # upgrade would silently have turned "tomorrow" into "almost nothing" for
    # every install that waters in the evening. The second case pins what a
    # look-ahead of 1 still does NOT reach: rain 32 hours out is the next block.
    with freeze_time(_local(2026, 9, 13, 21, 0)):
        result = await _coordinator(_client(rain_at))._eval_precipitation(
            _config(days=days)
        )
    assert (result["observed"], result["would_skip"]) == (observed, would_skip)


@pytest.mark.parametrize(
    ("rainy_hours", "rate", "threshold"), [(10, 0.2, 2), (1, 0.49, 0.49)]
)
async def test_rain_adding_up_to_the_threshold_skips_as_the_dashboard_shows_it(
    berlin, rainy_hours, rate, threshold
):
    # Integrated per second, ten hours of 0.2 mm come to 1.9999999999999998 and
    # one hour of 0.49 mm to 0.48999999999999994. The dashboard shows each as the
    # threshold itself, so the run has to skip.
    rainy = {_local(2026, 9, 13, 8 + h, 0) for h in range(rainy_hours)}
    series = [(stamp, rate if stamp in rainy else 0.0) for stamp, _ in _hourly(None)]
    client = SimpleNamespace(
        get_forecast_data=lambda: _forecast_days(None),
        get_hourly_precipitation_forecast=lambda: series,
    )
    config = _config() | {const.CONF_PRECIPITATION_THRESHOLD_MM: threshold}
    with freeze_time(_local(2026, 9, 13, 6, 20)):
        result = await _coordinator(client)._eval_precipitation(config)
    assert (result["observed"], result["would_skip"]) == (threshold, True)


async def test_a_client_without_an_hourly_series_cannot_decide_the_first_24_hours(
    berlin,
):
    with freeze_time(_local(2026, 9, 13, 6, 20)):
        result = await _coordinator(_daily_only_client())._eval_precipitation(_config())
    assert result["available"] is False
    assert result["would_skip"] is False


async def test_a_failed_refresh_does_not_decide_on_the_last_documents_series(berlin):
    # Every client returns no daily forecast when its refresh fails but keeps the
    # document of its last success, and the hourly accessor reads that one.
    # Deciding on it would skip on a forecast of any age.
    client = SimpleNamespace(
        get_forecast_data=lambda: None,
        get_hourly_precipitation_forecast=lambda: _hourly(AFTERNOON),
    )
    with freeze_time(_local(2026, 9, 13, 6, 20)):
        result = await _coordinator(client)._eval_precipitation(_config())
    assert result["available"] is False
    assert result["would_skip"] is False


async def test_a_real_client_whose_refresh_fails_leaves_the_guard_undecided(berlin):
    # The premise of the test above, with OWM itself: the failed request yields no
    # daily forecast, while the hourly accessor still reads the old document,
    # which forecasts 30 mm over the run's late morning.
    client = owm_module.OWMClient(api_key="k", latitude=50.0, longitude=7.0)
    first = datetime.datetime(2026, 9, 12, 0, 0, tzinfo=UTC)
    client._cached_forecast_doc = {
        "cod": "200",
        "list": [
            {"dt": int((first + datetime.timedelta(hours=3 * k)).timestamp())}
            | ({"rain": {"3h": 30.0}} if k == 12 else {})
            for k in range(17)
        ],
    }
    offline = requests.ConnectionError("offline")
    with freeze_time(_local(2026, 9, 13, 6, 20)):
        with patch.object(owm_module._SESSION, "get", side_effect=offline):
            assert client.get_forecast_data() is None
            assert client.get_hourly_precipitation_forecast()
            result = await _coordinator(client)._eval_precipitation(_config())
    assert result["available"] is False
    assert result["would_skip"] is False


async def test_at_dispatch_uncovered_first_24_hours_are_logged_at_info(berlin, caplog):
    # The guard then sits the run out, and nothing in the dashboard shows it.
    caplog.set_level(
        logging.DEBUG, logger="custom_components.irrigation_plus.skip_conditions"
    )
    with freeze_time(RUN):
        await _coordinator(_daily_only_client())._eval_precipitation(_config())
    levels = [
        r.levelno
        for r in caplog.records
        if "does not cover the first 24 hours" in r.getMessage()
    ]
    assert levels == [logging.INFO]


async def test_a_preview_logs_uncovered_first_24_hours_at_debug(berlin, caplog):
    # A preview names its run and repeats on every refresh, so the same gap would
    # fill the log at info.
    caplog.set_level(
        logging.DEBUG, logger="custom_components.irrigation_plus.skip_conditions"
    )
    with freeze_time(RUN):
        await _coordinator(_daily_only_client())._eval_precipitation(_config(), RUN)
    levels = [
        r.levelno
        for r in caplog.records
        if "does not cover the first 24 hours" in r.getMessage()
    ]
    assert levels == [logging.DEBUG]


async def test_a_window_whose_later_days_are_partly_covered_still_decides(
    berlin, caplog
):
    # Only uncovered first 24 hours stop the decision. A window reaching past the
    # forecast decides on the rain it has and says so at debug.
    caplog.set_level(
        logging.DEBUG, logger="custom_components.irrigation_plus.skip_conditions"
    )
    # 36 dry hours from local 13th 00:00 (12th 22:00Z): the 13th and the first
    # twelve hours of the local 14th.
    first = _local(2026, 9, 13, 0, 0)
    series = [(first + datetime.timedelta(hours=h), 0.0) for h in range(1, 37)]
    assert series[-1][0] == datetime.datetime(2026, 9, 14, 10, 0, tzinfo=UTC)

    def utc_day(day, mm):
        start = datetime.datetime(2026, 9, day, tzinfo=UTC)
        return {
            const.FORECAST_DAY_START: start,
            const.FORECAST_DAY_END: start + datetime.timedelta(days=1),
            const.MAPPING_PRECIPITATION: mm,
        }

    # Days filed by UTC date, as OWM files them. The 14th starts at 00:00Z, before
    # the series ends at 10:00Z, and is left out; the 15th starts after it.
    client = SimpleNamespace(
        get_forecast_data=lambda: [utc_day(14, 0.0), utc_day(15, 5.0)],
        get_hourly_precipitation_forecast=lambda: series,
    )
    with freeze_time(_local(2026, 9, 13, 6, 20)):
        result = await _coordinator(client)._eval_precipitation(_config(days=3))
    # Blocks of 24 hours from 04:20Z on the 13th: the 2nd ends 15th 04:20Z and the
    # 3rd runs to 16th 04:20Z, so the UTC 15th (15th 00:00Z-16th 00:00Z) lies
    # wholly inside the window -- 4h20m of it in the 2nd block, the other 19h40m
    # in the 3rd. All 5 mm count. Under calendar dates the same entry was clipped
    # to a 22/24 overlap with the local days; 24-hour blocks from 04:20Z hold it.
    assert result["available"] is True
    assert result["would_skip"] is True
    assert result["observed"] == 5.0
    levels = [
        r.levelno for r in caplog.records if "covers only part of the" in r.getMessage()
    ]
    assert levels == [logging.DEBUG]


async def test_disabled_is_a_noop():
    result = await _coordinator(_client())._eval_precipitation(_config(enabled=False))
    assert result["enabled"] is False
    assert result["available"] is False
    assert result["would_skip"] is False


async def test_no_weather_client_is_unavailable():
    result = await _coordinator(None)._eval_precipitation(_config())
    assert result["available"] is False
    assert result["would_skip"] is False
