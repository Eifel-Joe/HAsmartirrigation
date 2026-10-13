"""The time a pausing sensor group does not book: blocked spans and the share left."""

from datetime import datetime, timedelta

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.sensor_liveness import (
    Outage,
    blocked_spans,
    group_pauses,
    valid_share,
)

T0 = datetime(2026, 7, 1, 0, 0, 0)  # window start, naive on HA's clock
END = T0 + timedelta(hours=24)
H = timedelta(hours=1)


def _outage(start_h, end_h=None, fields=("Temperature",), entity="sensor.t"):
    return Outage(
        entity,
        "dev1",
        tuple(fields),
        T0 + start_h * H,
        None if end_h is None else T0 + end_h * H,
    )


class TestBlockedSpans:
    def test_the_first_three_hours_are_bridged(self):
        spans = blocked_spans([_outage(2, 10)], T0, END)
        assert spans == {"Temperature": ((T0 + 5 * H, T0 + 10 * H),)}

    def test_an_outage_of_three_hours_or_less_blocks_nothing(self):
        assert blocked_spans([_outage(2, 5)], T0, END) == {}
        assert blocked_spans([_outage(2, 4)], T0, END) == {}

    def test_an_open_outage_blocks_up_to_the_window_end(self):
        spans = blocked_spans([_outage(20)], T0, END)
        assert spans == {"Temperature": ((T0 + 23 * H, END),)}

    def test_spans_are_cut_to_the_window(self):
        assert blocked_spans([_outage(-10, 4)], T0, END) == {
            "Temperature": ((T0, T0 + 4 * H),)
        }
        assert blocked_spans([_outage(-10, -1)], T0, END) == {}
        assert blocked_spans([_outage(30)], T0, END) == {}

    def test_overlapping_outages_of_one_field_merge(self):
        spans = blocked_spans(
            [_outage(0, 10, entity="sensor.a"), _outage(6, 14, entity="sensor.b")],
            T0,
            END,
        )
        assert spans == {"Temperature": ((T0 + 3 * H, T0 + 14 * H),)}

    def test_outages_whose_spans_touch_merge(self):
        spans = blocked_spans(
            [_outage(0, 10, entity="sensor.a"), _outage(7, 14, entity="sensor.b")],
            T0,
            END,
        )
        # sensor.a blocks 3..10 h and sensor.b 10..14 h: one span, not two.
        assert spans == {"Temperature": ((T0 + 3 * H, T0 + 14 * H),)}

    def test_separate_outages_stay_separate_and_sorted(self):
        spans = blocked_spans([_outage(10, 15), _outage(0, 5)], T0, END)
        assert spans == {
            "Temperature": ((T0 + 3 * H, T0 + 5 * H), (T0 + 13 * H, T0 + 15 * H))
        }

    def test_only_the_fields_the_outage_recorded_are_blocked(self):
        spans = blocked_spans(
            [_outage(0, 10, fields=("Dewpoint", "Humidity"))], T0, END
        )
        assert set(spans) == {"Dewpoint", "Humidity"}


class TestValidShare:
    def test_a_field_without_spans_is_valid_throughout(self):
        assert valid_share({}, ("Temperature",), T0, END) == 1.0

    def test_the_share_is_the_window_minus_the_span(self):
        blocked = {"Temperature": ((T0 + 6 * H, T0 + 12 * H),)}
        assert valid_share(blocked, ("Temperature", "Dewpoint"), T0, END) == 0.75

    def test_two_fields_silent_at_different_hours_leave_their_intersection(self):
        blocked = {
            "Temperature": ((T0, T0 + 6 * H),),
            "Dewpoint": ((T0 + 12 * H, T0 + 18 * H),),
        }
        # Not min(0.75, 0.75): together they leave 12 of 24 hours.
        assert valid_share(blocked, ("Temperature", "Dewpoint"), T0, END) == 0.5

    def test_overlapping_spans_count_once(self):
        blocked = {
            "Temperature": ((T0, T0 + 12 * H),),
            "Dewpoint": ((T0 + 6 * H, T0 + 12 * H),),
        }
        assert valid_share(blocked, ("Temperature", "Dewpoint"), T0, END) == 0.5

    def test_fields_that_are_not_asked_for_do_not_count(self):
        blocked = {"Solar Radiation": ((T0, END),)}
        assert valid_share(blocked, ("Temperature",), T0, END) == 1.0

    def test_a_field_blocked_throughout_leaves_nothing(self):
        blocked = {"Temperature": ((T0, END),)}
        assert valid_share(blocked, ("Temperature",), T0, END) == 0.0

    def test_an_empty_window_is_not_cut(self):
        blocked = {"Temperature": ((T0, END),)}
        assert valid_share(blocked, ("Temperature",), END, END) == 1.0


class TestGroupPauses:
    def test_only_a_stored_pause_pauses(self):
        assert group_pauses({const.MAPPING_ON_SILENT_SENSOR: "pause"}) is True
        assert group_pauses({const.MAPPING_ON_SILENT_SENSOR: "keep"}) is False
        assert group_pauses({}) is False
        assert group_pauses({const.MAPPING_ON_SILENT_SENSOR: "PAUSE"}) is False
