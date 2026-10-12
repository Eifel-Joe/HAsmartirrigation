"""A pausing group's window: each blocked field reduced over its valid time only."""

from datetime import datetime, timedelta

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.weather_aggregate import aggregate_window

W = datetime(2026, 7, 1, 0, 0, 0)  # the zone's watermark: the window starts here
NOW = W + timedelta(hours=24)
H = timedelta(hours=1)
T = const.MAPPING_TEMPERATURE
WIND = const.MAPPING_WINDSPEED
PRECIP = const.MAPPING_PRECIPITATION


def _hourly(field=T, values=None):
    """One row per hour; the row AT the watermark becomes the boundary reading."""
    return [
        {const.RETRIEVED_AT: W + h * H, field: values[h] if values else float(h)}
        for h in range(24)
    ]


def _span(a, b):
    return (W + a * H, W + b * H)


def _config(aggregate, field=WIND):
    return {
        field: {
            const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
            const.MAPPING_CONF_AGGREGATE: aggregate,
        }
    }


def _agg(readings, blocked=None, config=None, **kw):
    return aggregate_window(readings, W, config or {}, now=NOW, blocked=blocked, **kw)


class TestUnblockedFieldsAreUntouched:
    def test_no_spans_empty_spans_and_foreign_spans_change_nothing(self):
        rows = _hourly() + _hourly(const.MAPPING_DEWPOINT)
        base = _agg(rows)
        assert _agg(rows, blocked={}) == base
        assert _agg(rows, blocked={WIND: (_span(3, 9),)}) == base

    def test_a_field_without_spans_is_reduced_as_before(self):
        rows = [
            {
                const.RETRIEVED_AT: W + h * H,
                T: float(h),
                const.MAPPING_DEWPOINT: 2.0 * h,
            }
            for h in range(24)
        ]
        base = _agg(rows)
        cut = _agg(rows, blocked={T: (_span(6, 12),)})
        assert cut[const.MAPPING_DEWPOINT] == base[const.MAPPING_DEWPOINT]
        assert cut[const.MAPPING_DATA_MULTIPLIER] == base[const.MAPPING_DATA_MULTIPLIER]
        assert cut[T] != base[T]


class TestThePlainMean:
    def test_rows_inside_a_span_are_dropped(self):
        assert _agg(_hourly())[T] == 11.5
        # Without hours 6..11: (0+...+5 + 12+...+23) / 18.
        assert _agg(_hourly(), blocked={T: (_span(6, 12),)})[T] == pytest.approx(12.5)

    def test_the_reading_of_the_return_counts(self):
        rows = [
            {const.RETRIEVED_AT: W, T: 0.0},
            {const.RETRIEVED_AT: W + 12 * H, T: 100.0},
        ]
        # The span is half-open: the row at its end is the return, and measured.
        assert _agg(rows, blocked={T: (_span(6, 12),)})[T] == 50.0

    def test_a_span_at_the_window_start_drops_the_boundary_as_a_sample(self):
        cut = _agg(_hourly(), blocked={T: (_span(0, 6),)})
        assert cut[T] == pytest.approx(sum(range(6, 24)) / 18)
        assert cut[const.MAPPING_MIN_TEMP] == 6.0
        assert cut[const.MAPPING_MAX_TEMP] == 23.0

    def test_a_span_at_the_window_end_drops_the_last_rows(self):
        cut = _agg(_hourly(), blocked={T: (_span(18, 24),)})
        assert cut[T] == pytest.approx(sum(range(18)) / 18)
        assert cut[const.MAPPING_MAX_TEMP] == 17.0
        assert cut[const.MAPPING_MIN_TEMP] == 0.0


class TestTheTimeWeightedMean:
    def test_a_value_is_not_held_into_a_span_and_holds_again_after_it(self):
        """A sensor that returns with the value it had writes no row (deadband,
        state_reported): after the span the value from before it holds again."""
        rows = [
            {const.RETRIEVED_AT: W, T: 10.0},
            {const.RETRIEVED_AT: W + 2 * H, T: 14.0},
        ]
        cut = _agg(rows, blocked={T: (_span(5, 15),)}, time_weighted=True)
        # 10 for 2 h and 14 for 3 h before the span, 14 again for the 9 h after it.
        assert cut[T] == pytest.approx((10 * 2 + 14 * 3 + 14 * 9) / 14)
        assert cut[const.MAPPING_MIN_TEMP] == 10.0
        assert cut[const.MAPPING_MAX_TEMP] == 14.0
        # Without the span the hold runs through: (10 * 2 + 14 * 22) / 24.
        assert _agg(rows, time_weighted=True)[T] == pytest.approx(328 / 24)

    def test_frozen_rows_inside_the_span_do_not_count(self):
        cut = _agg(_hourly(), blocked={T: (_span(6, 12),)}, time_weighted=True)
        assert cut[T] == pytest.approx(225 / 18)

    def test_a_window_that_starts_blocked_holds_the_boundary_after_the_span(self):
        """The boundary is the value from before the span: it holds from the span's
        end until the next reading, though it is no sample of the valid time."""
        rows = [
            {const.RETRIEVED_AT: W, T: 10.0},
            {const.RETRIEVED_AT: W + 9 * H, T: 20.0},
        ]
        cut = _agg(rows, blocked={T: (_span(0, 6),)}, time_weighted=True)
        assert cut[T] == pytest.approx((10 * 3 + 20 * 15) / 18)
        assert cut[const.MAPPING_MIN_TEMP] == 10.0


class TestFieldsWithoutValidTime:
    def test_a_field_blocked_throughout_is_left_out_and_not_filled(self):
        cut = _agg(_hourly(), blocked={T: (_span(0, 24),)}, last_entry={T: 20.0})
        assert T not in cut
        assert const.MAPPING_MAX_TEMP not in cut
        assert const.MAPPING_MIN_TEMP not in cut

    def test_a_field_with_no_value_to_hold_is_left_out(self):
        """No boundary and every row inside the span: nothing measured to hold."""
        rows = [{const.RETRIEVED_AT: W + h * H, T: 5.0} for h in range(7, 11)]
        assert T not in _agg(rows, blocked={T: (_span(6, 12),)})

    def test_the_carry_forward_fills_a_field_with_valid_time(self):
        cut = _agg(
            _hourly(const.MAPPING_DEWPOINT),
            blocked={T: (_span(6, 12),)},
            last_entry={T: 20.0},
        )
        assert cut[T] == 20.0
        assert cut[const.MAPPING_MAX_TEMP] == 20.0

    def test_a_blocked_field_without_readings_changes_nothing(self):
        rows = _hourly(const.MAPPING_DEWPOINT)
        assert _agg(rows, blocked={T: (_span(6, 12),)}) == _agg(rows)

    def test_a_single_value_is_used_verbatim(self):
        cut = _agg([{const.RETRIEVED_AT: W, T: 7.0}], blocked={T: (_span(10, 14),)})
        assert cut[T] == 7.0
        assert cut[const.MAPPING_MAX_TEMP] == cut[const.MAPPING_MIN_TEMP] == 7.0


@pytest.mark.parametrize(
    ("aggregate", "span", "expected"),
    [
        (const.MAPPING_CONF_AGGREGATE_FIRST, (0, 6), 6.0),
        (const.MAPPING_CONF_AGGREGATE_LAST, (18, 24), 17.0),
        (const.MAPPING_CONF_AGGREGATE_MAXIMUM, (18, 24), 17.0),
        (const.MAPPING_CONF_AGGREGATE_MINIMUM, (0, 6), 6.0),
        (const.MAPPING_CONF_AGGREGATE_MEDIAN, (6, 12), 14.5),
        (const.MAPPING_CONF_AGGREGATE_SUM, (6, 12), 225.0),
    ],
)
def test_each_aggregate_reads_only_the_valid_samples(aggregate, span, expected):
    rows = _hourly(WIND)
    assert _agg(rows, config=_config(aggregate))[WIND] != expected
    cut = _agg(rows, blocked={WIND: (_span(*span),)}, config=_config(aggregate))
    assert cut[WIND] == expected


class TestRain:
    RATE = _config(const.MAPPING_CONF_AGGREGATE_RIEMANNSUM, PRECIP)

    def test_a_rain_rate_is_integrated_over_its_valid_time_only(self):
        rows = _hourly(PRECIP, values=[2.0] * 24)
        assert _agg(rows, config=self.RATE)[PRECIP] == pytest.approx(46.0)
        # Six blocked hours at 2 mm/h book nothing; the pair across the span counts
        # only its one measured hour (5..6).
        cut = _agg(rows, blocked={PRECIP: (_span(6, 12),)}, config=self.RATE)
        assert cut[PRECIP] == pytest.approx(34.0)

    def test_a_rain_gauge_is_never_cut_even_if_asked(self):
        rows = [{const.RETRIEVED_AT: W + h * H, PRECIP: float(h)} for h in range(24)]
        assert _agg(rows, blocked={PRECIP: (_span(6, 12),)}) == _agg(rows)


def test_a_row_stamped_after_now_counts_as_measured():
    """Clock skew: the window runs to the late row, and the span ends long before."""
    rows = _hourly() + [{const.RETRIEVED_AT: NOW + 2 * H, T: 100.0}]
    cut = _agg(rows, blocked={T: (_span(6, 12),)})
    assert cut[T] == pytest.approx((225 + 100) / 19)
