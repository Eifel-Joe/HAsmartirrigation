"""Expected precipitation over a run's rolling 24-hour blocks.

Pure arithmetic -- no Home Assistant import and no Home Assistant time zone --
so the window can be checked against hand-computed numbers. The precipitation
skip guard hands it the configured client's hourly precipitation series and its
dated daily entries.

The window starts at the run itself and spans ``days`` blocks of 24 absolute
hours from there. The guard used to sum whole days out of ``get_forecast_data``,
which by contract starts tomorrow; evaluated at dispatch on the morning of a
run, that put the first day of the window one day AFTER the run, so the day it
rained was never examined (#137). Measuring instead in local calendar dates
fixed that but tied the look-ahead to the hour of the run: with a look-ahead of
1 an evening run saw only the rest of its own date, which on upgrade would have
turned "tomorrow" into "almost nothing" for every install that waters in the
evening. Hours before the evaluation are still cut off, because a forecast says
nothing about hours already past.

Known imprecisions, each bounded. All but the last under-count, which errs
towards watering; the last one is the exception and is marked as such:

* Pirate Weather's hourly points are read as ending at their stamp, which its
  client marks as assumed: that reading is taken from the documentation, not
  measured, and if they begin there a block's total is off by one hour of rain
  at each end. Measured against a live response on 2026-09-16, the first stamp
  falls on the hour the fetch began in -- evidence for the documented
  "beginning" convention rather than a resolution of it -- and the daily spans
  run from one block's time to the next at local midnight.
* Open-Meteo converts its local stamps with the document's single
  ``utc_offset_seconds``, so hours after a daylight-saving change inside the
  document sit an hour off.
* Met Office groups its three-hourly product by UTC date, and the entry for
  the product's last date spans the whole day although its total holds only
  the steps up to where the product ends. When the hourly document serves the
  series, that entry lies behind it and counts as covering its whole day, so
  the total is short while the day reports as complete. It under-counts, which
  errs towards watering, and only a window reaching that date sees it.
* Met Office's hourly document reaches 48 hours from the FETCH, not from the
  evaluation, and the accessor reads a document fetched earlier -- up to one
  cache lifetime, at most three hours, old. The daily entry for the day such a
  series ends in starts before that end and is left out, so whatever the
  series does not reach stays uncovered. Evaluated at the run, the series
  covers at most the first two blocks, and the document's age eats into that
  from the far end: even at the run itself the tail of the second block can be
  missing, and a look-ahead of three or more loses its third block whole. A
  preview some hours before the run loses those hours as well. It under-counts,
  which errs towards watering. Pirate Weather used to share this shortfall --
  its default hourly block is also 48 entries from the fetch -- but its client
  now always asks for the long block (``extend=hourly``, measured 2026-09-16
  at 168 entries reaching floor(fetch) + 167 h), so it is affected only past a
  look-ahead of about six days or a document that many days stale. OWM (five
  days, three-hourly) and Open-Meteo (seven days) are not affected either.
* ``day_projection.forecast_rain_mm`` integrates the same series for the
  next-run projection but declines when the series starts after the span. Here
  the first sample reaches back one step, which is what lets a three-hourly
  series cover the hours just after a fetch. The two can disagree on whether a
  span is covered; the difference is deliberate, do not fix one side only.
* THE EXCEPTION, and the only one here that errs towards SKIPPING rather than
  watering: a daily entry admitted by ``_entries_behind`` is charged to a block
  in PROPORTION to its overlap with it, so an entry whose span only pokes into
  the window contributes a share of its total although the forecast places that
  rain across hours the window does not cover. A skip can therefore be built out
  of rain forecast for hours outside the window. Bounded by the total of an
  entry straddling an end of the window times the share of its span that lies
  inside -- one entry per end at most, since no client's daily entries overlap
  each other, and in practice only the far end: an entry meeting the near one
  would have to start behind a series that already ended before the window. Only
  Pirate Weather and Met Office can produce it, because an entry reaches the
  fill-in path only where its span starts strictly AFTER the hourly series ends,
  and OWM and Open-Meteo build their daily list out of the same document their
  hourly series comes from, so no entry of theirs lies behind it. Measured
  2026-09-16 through Pirate Weather itself: 48 hourly entries at 0.0 mm/h
  ending 2026-09-14 03:00Z, dispatch 06:19 local on 2026-09-12 (04:19Z),
  look-ahead 3, and one daily entry for the local 15th carrying 12 mm whose
  span begins after the series ends and overlaps the window by 6 h 19 min of
  its 24 h -- observed 3.16 mm against a 2 mm threshold, the run skipped
  although no hour the forecast covers holds any rain at all. ``complete`` is False in such a case, but that is
  debug-logged only and does not hold the decision back. The pro-rating itself
  is not the fault: it is the same arithmetic that lets a partly covered block
  count at all, the integration model working as designed on an input whose
  resolution is a whole day. Counting an entry only where its span lies wholly
  inside the window would trade this for dropping real rain at every window
  edge, and a share of the total is the expected value when a day's total is
  all the forecast gives.
"""

from __future__ import annotations

import datetime
import math
from typing import NamedTuple

from .const import FORECAST_DAY_END, FORECAST_DAY_START, MAPPING_PRECIPITATION

_UTC = datetime.timezone.utc
_SECONDS_PER_HOUR = 3600.0
_BLOCK = datetime.timedelta(hours=24)
# A covered span within this many seconds of the requested one counts as whole.
# The same number decides that a block with less than that left at the
# evaluation is dropped, and the two MUST stay one value: a block shorter than
# the slack could never report a shortfall, so it would count as covered
# whatever the forecast holds for it.
_COVERAGE_TOLERANCE_SECONDS = 1.0


class ExpectedRain(NamedTuple):
    """Forecast rain over a run's window, and how much of the window was covered."""

    mm: float
    # The first 24 hours from the run's start were fully covered (what is left of
    # them after the evaluation moment, that is).
    first_24h_covered: bool
    # Every 24-hour block of the window was fully covered.
    complete: bool


def day_span(entry):
    """``(start, end)`` in UTC of the day a daily forecast entry covers, or None.

    The one reader of ``FORECAST_DAY_START``/``FORECAST_DAY_END``: the panel
    labels a day from it and the skip guard weighs a day with it, so the two
    cannot disagree about which entries carry a usable span. The rules they apply
    to a span differ on purpose -- the panel names the local date holding its
    middle, the guard counts it by overlap. None unless both ends are present,
    carry a time zone, and the end lies after the start.
    """
    start = entry.get(FORECAST_DAY_START)
    end = entry.get(FORECAST_DAY_END)
    if not isinstance(start, datetime.datetime) or not isinstance(
        end, datetime.datetime
    ):
        return None
    if start.utcoffset() is None or end.utcoffset() is None:
        return None
    start, end = start.astimezone(_UTC), end.astimezone(_UTC)
    if end <= start:
        return None
    return start, end


def window_intervals(run_start, days, evaluated_at):
    """``[(index, start, end)]`` in UTC: rolling 24-hour blocks from the run's start.

    Wurzel: the window used to be the run's LOCAL calendar date and the dates after
      it. That made the setting mean different things at different hours: with a
      look-ahead of 1 an evening run saw only the last hours of its own date, so
      every install watering in the evening would have gone from seeing tomorrow to
      seeing almost nothing, silently, on upgrade.
    Fix-Logik: block ``index`` is ``[run_start + index*24h, run_start + (index+1)*24h)``
      in absolute UTC hours. A daylight-saving night is 24 real hours again and Home
      Assistant's zone draws no boundary. The part before ``evaluated_at`` is cut
      off, because a forecast says nothing about hours already past; a block with
      less than the coverage tolerance left is dropped, so a first block wholly in
      the past disappears and ``index`` 0 is then missing from the list.
    NOT-TO-DO: do not add the offset to a zone-aware ``run_start`` without
      converting to UTC first -- adding a day to a ``ZoneInfo`` datetime is
      wall-clock arithmetic and a 25-hour night would come out as 24 hours of
      window shifted by one. And do not flatten the result to plain ``(start, end)``
      pairs: ``index`` is what tells a shrunken first block from a missing one, and
      with a look-ahead of 2 or more nothing else does.
    siehe tests/test_forecast_window.py::test_a_daylight_saving_night_is_still_twenty_four_real_hours
      und ::test_a_first_block_entirely_in_the_past_is_not_covered
    """
    start_utc = run_start.astimezone(_UTC)
    evaluated = evaluated_at.astimezone(_UTC)
    out = []
    for index in range(max(1, int(days))):
        block_start = start_utc + index * _BLOCK
        start = max(block_start, evaluated)
        end = block_start + _BLOCK
        if (end - start).total_seconds() > _COVERAGE_TOLERANCE_SECONDS:
            out.append((index, start, end))
    return out


def _overlap_seconds(a_start, a_end, b_start, b_end) -> float:
    return max(0.0, (min(a_end, b_end) - max(a_start, b_start)).total_seconds())


def _hourly_segments(series):
    """``[(start, end, mm_per_hour)]`` in UTC from a client's ``[(stamp, rate)]``.

    Wurzel: a sample's length used to be the gap to the previous stamp. Open-Meteo
      and Pirate Weather drop a row without a value, so a missing hour stretched
      the next rate back across the gap: its water multiplied and the gap counted
      as forecast.
    Fix-Logik: each rate covers the interval ENDING at its stamp, the convention
      every client hands back, but never more than one step of the series, its
      smallest spacing. The first sample reaches back one step. A longer spacing
      is a hole the caller sees as uncovered. A duplicated stamp keeps its highest
      rate; a rate that is not a finite number is dropped, a negative one is dry.
    NOT-TO-DO: do not cap at a fixed length such as three hours: an hourly series
      with a two-hour hole would still stretch. Met Office already spreads its
      amounts over its own gaps, so capping under-counts there -- the direction
      that waters rather than skips. And check ``math.isfinite`` before any
      ``max``: ``max(0.0, nan)`` is ``0.0`` and would turn a hole into a dry hour.
    siehe tests/test_forecast_window.py
    """
    rates = {}
    for stamp, rate in series or []:
        if stamp is None or rate is None:
            continue
        try:
            value = float(rate)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        key = stamp.astimezone(_UTC)
        rates[key] = max(rates.get(key, 0.0), value, 0.0)
    stamps = sorted(rates)
    if not stamps:
        return []
    spacings = [
        later - earlier for earlier, later in zip(stamps, stamps[1:], strict=False)
    ]
    step = min(spacings) if spacings else datetime.timedelta(hours=1)
    return [(stamp - step, stamp, rates[stamp]) for stamp in stamps]


def _entries_behind(daily, series_end):
    """``[(start, end, mm)]`` for dated daily entries lying behind the hourly series.

    Wurzel: OWM builds its days from the same three-hourly list its hourly series
      comes from. Its last day holds only the slots up to the series' end while
      its span claims the whole day, and a slot stamped 00Z is filed under the new
      day although its rain fell in the three hours before. Filling from such an
      entry counted rain the series had already counted, and reported the day as
      complete.
    Fix-Logik: an entry fills in only where the series has nothing to say -- its
      span has to start AFTER the series' last stamp. An entry that overlaps the
      series, or starts exactly at its end, is left out whole, so the rest of its
      day is uncovered. That under-counts, which errs towards watering. Daily
      entries are assumed not to overlap each other, as every client builds
      them; overlapping ones would be counted twice.
    NOT-TO-DO: do not shorten the span in the client. The panel labels a day by
      the middle of that span, so the client's span has to stay the whole day.
    siehe tests/test_forecast_window.py::test_daily_entries_fill_in_only_behind_the_hourly_series
      und ::test_owm_s_last_day_starting_at_the_series_end_is_not_counted_again
    """
    out = []
    for entry in daily or []:
        if not isinstance(entry, dict):
            continue
        span = day_span(entry)
        if span is None:
            continue
        try:
            mm = float(entry.get(MAPPING_PRECIPITATION))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(mm):
            continue
        start, end = span
        if series_end is not None and start <= series_end:
            continue
        out.append((start, end, max(0.0, mm)))
    return out


def expected_rain(*, run_start, evaluated_at, days, hourly, daily) -> ExpectedRain:
    """Forecast precipitation over ``days`` 24-hour blocks from the run's start.

    The hourly series is integrated wherever it reaches. Dated daily entries that
    start after it fill in, each counted by the share of its own span that falls
    inside the window -- a UTC-day entry thus contributes to a block in proportion
    to their overlap. Coverage is reported per block so the caller can refuse to
    decide on a first 24 hours nothing forecast; a first block already past at the
    evaluation counts as uncovered.
    """
    intervals = window_intervals(run_start, days, evaluated_at)
    segments = _hourly_segments(hourly)
    series_end = segments[-1][1] if segments else None
    pieces = [(start, end, rate / _SECONDS_PER_HOUR) for start, end, rate in segments]
    # NOT-TO-DO: do not price a daily entry over a fixed 86400 s. Three of the four
    #   clients build their span as a UTC date plus one day, which is always 24 h,
    #   so the constant passes every test built on them -- but Pirate Weather takes
    #   both ends from its own block stamps, and a daylight-saving day is 23 or 25
    #   hours there. day_span converts both ends to UTC before returning them, so
    #   (end - start) is real elapsed time and is the divisor that matches the mm.
    # siehe tests/test_forecast_window.py::test_a_daily_entry_is_priced_over_its_own_span
    pieces += [
        (start, end, mm / (end - start).total_seconds())
        for start, end, mm in _entries_behind(daily, series_end)
    ]
    total = 0.0
    first_24h_covered = any(index == 0 for index, _, _ in intervals)
    complete = first_24h_covered
    for index, start, end in intervals:
        covered = 0.0
        for piece_start, piece_end, per_second in pieces:
            seconds = _overlap_seconds(start, end, piece_start, piece_end)
            total += per_second * seconds
            covered += seconds
        if covered < (end - start).total_seconds() - _COVERAGE_TOLERANCE_SECONDS:
            complete = False
            if index == 0:
                first_24h_covered = False
    return ExpectedRain(total, first_24h_covered, complete)
