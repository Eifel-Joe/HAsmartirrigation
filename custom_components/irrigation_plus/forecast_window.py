"""Expected precipitation over a run's calendar days.

Pure arithmetic -- no Home Assistant import -- so the window can be checked
against hand-computed numbers. The precipitation skip guard hands it the
configured client's hourly precipitation series and its dated daily entries,
and Home Assistant's own time zone decides which calendar days a run covers.

The window starts at the run's own local DATE and spans ``days`` calendar days
from there. The guard used to sum whole days out of ``get_forecast_data``,
which by contract starts tomorrow; evaluated at dispatch on the morning of a
run, that put the first day of the window one day AFTER the run, so the day it
rained was never examined (#137). Hours before the evaluation are cut off, so a
run that starts in the evening with a one-day window sees only the rest of its
own day.

Known imprecisions, each bounded:

* Pirate Weather's hourly points are read as ending at their stamp, which its
  client marks as assumed; if they begin there, the run date's total is off by
  one hour of rain at each end.
* Open-Meteo converts its local stamps with the document's single
  ``utc_offset_seconds``, so hours after a daylight-saving change inside the
  document sit an hour off.
* ``day_projection.forecast_rain_mm`` integrates the same series for the
  next-run projection but declines when the series starts after the span. Here
  the first sample reaches back one step, which is what lets a three-hourly
  series cover the hours just after a fetch. The two can disagree on whether a
  span is covered; the difference is deliberate, do not fix one side only.
"""

from __future__ import annotations

import datetime
from typing import NamedTuple

_UTC = datetime.timezone.utc
_SECONDS_PER_HOUR = 3600.0
# A covered span within this many seconds of the requested one counts as whole.
_COVERAGE_TOLERANCE_SECONDS = 1.0


class ExpectedRain(NamedTuple):
    """Forecast rain over a run's window, and how much of the window was covered."""

    mm: float
    # The run's own date was fully covered by the hourly series or daily entries.
    run_date_covered: bool
    # Every day of the window was fully covered.
    complete: bool


def _local_midnight_utc(day: datetime.date, tz) -> datetime.datetime:
    # Built in the zone, then converted: subtracting two datetimes that share one
    # ZoneInfo is wall-clock arithmetic and would give a 25-hour day 24 hours.
    return datetime.datetime(day.year, day.month, day.day, tzinfo=tz).astimezone(_UTC)


def window_intervals(run_start, days, tz, evaluated_at):
    """``[(index, start, end)]`` in UTC for the run's local date and the days after it.

    Each day runs from local midnight to the next, so a daylight-saving change
    gives it 23 or 25 hours. The part before ``evaluated_at`` is cut off, because
    a forecast says nothing about hours that have already passed; a day that is
    entirely past is left out. ``index`` 0 is the run's own date.
    """
    run_date = run_start.astimezone(tz).date()
    evaluated = evaluated_at.astimezone(_UTC)
    out = []
    for index in range(max(1, int(days))):
        day = run_date + datetime.timedelta(days=index)
        start = max(_local_midnight_utc(day, tz), evaluated)
        end = _local_midnight_utc(day + datetime.timedelta(days=1), tz)
        if start < end:
            out.append((index, start, end))
    return out


def _overlap_seconds(a_start, a_end, b_start, b_end) -> float:
    return max(0.0, (min(a_end, b_end) - max(a_start, b_start)).total_seconds())


def _hourly_segments(series):
    """``[(start, end, mm_per_hour)]`` in UTC from a client's ``[(stamp, rate)]``.

    Each rate covers the interval ENDING at its stamp, the convention every client
    hands back. Its length is the gap to the previous stamp; the first sample takes
    the gap to the next one, or one hour when it stands alone. A duplicated stamp
    has no length and is dropped.
    """
    points = sorted(
        (stamp.astimezone(_UTC), float(rate))
        for stamp, rate in (series or [])
        if stamp is not None and rate is not None
    )
    segments = []
    for i, (stamp, rate) in enumerate(points):
        if i > 0:
            span = stamp - points[i - 1][0]
        elif len(points) > 1:
            span = points[1][0] - stamp
        else:
            span = datetime.timedelta(hours=1)
        if span.total_seconds() <= 0:
            continue
        segments.append((stamp - span, stamp, rate))
    return segments


def expected_rain(*, run_start, evaluated_at, days, tz, hourly, daily) -> ExpectedRain:
    """Forecast precipitation on the run's local date and the ``days - 1`` after it.

    The hourly series is integrated wherever it reaches. Coverage is reported per
    day so the caller can refuse to decide on a run date nothing forecast.
    ``daily`` is not read yet.
    """
    intervals = window_intervals(run_start, days, tz, evaluated_at)
    pieces = [
        (start, end, rate / _SECONDS_PER_HOUR)
        for start, end, rate in _hourly_segments(hourly)
    ]
    total = 0.0
    run_date_covered = True
    complete = True
    for index, start, end in intervals:
        covered = 0.0
        for piece_start, piece_end, per_second in pieces:
            seconds = _overlap_seconds(start, end, piece_start, piece_end)
            total += per_second * seconds
            covered += seconds
        if covered < (end - start).total_seconds() - _COVERAGE_TOLERANCE_SECONDS:
            complete = False
            if index == 0:
                run_date_covered = False
    return ExpectedRain(total, run_date_covered, complete)
