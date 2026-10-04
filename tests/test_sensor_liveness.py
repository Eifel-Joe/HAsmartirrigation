"""Weather-sensor liveness: the pure rules, without Home Assistant."""

from datetime import datetime, timedelta

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.calculation import BUFFER_RETENTION
from custom_components.irrigation_plus.sensor_liveness import (
    Evidence,
    Outage,
    Seen,
    advance_outages,
    first_report_after,
    last_sign_of_life,
    outages_of,
    sensor_fields_by_entity,
)


def test_closed_outages_are_kept_as_long_as_the_buffer_may_keep_rows():
    """Closed outages are kept as long as the reading buffer may keep rows: the
    retention equals the buffer's cap."""
    assert (
        const.SENSOR_OUTAGE_RETENTION_DAYS * 86400 == BUFFER_RETENTION.total_seconds()
    )


def test_the_limits_are_the_documented_ones():
    """The docs name three hours and a check every five minutes; the startup grace
    is ten minutes."""
    assert const.SENSOR_STALE_AFTER_SECONDS == 3 * 3600
    assert const.SENSOR_LIVENESS_INTERVAL_SECONDS == 5 * 60
    assert const.SENSOR_LIVENESS_STARTUP_GRACE_SECONDS == 10 * 60


def _cfg(source, entity=None):
    cfg = {const.MAPPING_CONF_SOURCE: source}
    if entity is not None:
        cfg[const.MAPPING_CONF_SENSOR] = entity
    return cfg


def test_only_sensor_fields_with_an_entity_are_watched():
    mappings = {
        const.MAPPING_TEMPERATURE: _cfg(const.MAPPING_CONF_SOURCE_SENSOR, "sensor.t"),
        const.MAPPING_DEWPOINT: _cfg(const.MAPPING_CONF_SOURCE_SENSOR, "sensor.t"),
        # The panel clears the entity when a field's source changes; another
        # client can leave it behind.
        const.MAPPING_HUMIDITY: _cfg(
            const.MAPPING_CONF_SOURCE_WEATHER_SERVICE, "sensor.left_over"
        ),
        const.MAPPING_PRESSURE: _cfg(
            const.MAPPING_CONF_SOURCE_STATIC_VALUE, "sensor.left_over"
        ),
        const.MAPPING_EVAPOTRANSPIRATION: _cfg(
            const.MAPPING_CONF_SOURCE_NONE, "sensor.left_over"
        ),
        const.MAPPING_WINDSPEED: _cfg(const.MAPPING_CONF_SOURCE_SENSOR, ""),
        # The setup wizard stores a sensor field without an entity key.
        const.MAPPING_PRECIPITATION: _cfg(const.MAPPING_CONF_SOURCE_SENSOR),
        const.MAPPING_SOLRAD: "legacy bare string",
    }
    assert sensor_fields_by_entity(mappings) == {
        "sensor.t": (const.MAPPING_TEMPERATURE, const.MAPPING_DEWPOINT),
    }


def test_a_value_set_by_hand_is_never_watched():
    mappings = {
        const.MAPPING_PRESSURE: _cfg(
            const.MAPPING_CONF_SOURCE_SENSOR, "input_number.pressure"
        ),
        # Exempt is the input_number domain, not a name that merely contains it.
        const.MAPPING_HUMIDITY: _cfg(
            const.MAPPING_CONF_SOURCE_SENSOR, "sensor.input_number_mirror"
        ),
    }
    assert sensor_fields_by_entity(mappings) == {
        "sensor.input_number_mirror": (const.MAPPING_HUMIDITY,)
    }


T0 = datetime(2026, 7, 1, 12, 0, 0)


def _seen(entity_id="sensor.t", *, valid=True, reported=T0, changed=T0):
    return Seen(entity_id=entity_id, valid=valid, reported=reported, changed=changed)


class TestLastSignOfLife:
    def test_the_device_vouches_for_a_quiet_field(self):
        rain = _seen("sensor.rain", reported=T0 - timedelta(hours=5))
        temp = _seen("sensor.temp", reported=T0 - timedelta(minutes=1))
        assert last_sign_of_life(rain, [temp], None) == T0 - timedelta(minutes=1)

    def test_without_a_device_the_entity_vouches_for_itself(self):
        own = _seen(reported=T0 - timedelta(hours=2))
        assert last_sign_of_life(own, [], None) == T0 - timedelta(hours=2)

    def test_an_unavailable_entity_is_silent_whatever_its_device_does(self):
        own = _seen(valid=False, reported=T0)
        sibling = _seen("sensor.temp", reported=T0)
        remembered = T0 - timedelta(hours=4)
        assert last_sign_of_life(own, [sibling], remembered) == remembered

    def test_an_unavailable_sibling_does_not_vouch(self):
        own = _seen(reported=T0 - timedelta(hours=5))
        sibling = _seen("sensor.temp", valid=False, reported=T0)
        assert last_sign_of_life(own, [sibling], None) == T0 - timedelta(hours=5)

    def test_a_missing_entity_with_nothing_remembered_has_no_sign(self):
        assert last_sign_of_life(None, [], None) is None

    def test_the_remembered_sign_never_moves_backwards(self):
        own = _seen(reported=T0 - timedelta(hours=1))
        assert last_sign_of_life(own, [], T0) == T0

    def test_a_missing_entity_is_silent_whatever_its_device_does(self):
        sibling = _seen("sensor.temp", reported=T0)
        remembered = T0 - timedelta(hours=4)
        assert last_sign_of_life(None, [sibling], remembered) == remembered
        assert last_sign_of_life(None, [sibling], None) is None


class TestFirstReportAfter:
    def test_the_earliest_change_after_the_start_marks_the_return(self):
        start = T0 - timedelta(hours=6)
        own = _seen(changed=T0 - timedelta(minutes=3))
        sibling = _seen("sensor.temp", changed=T0 - timedelta(minutes=4))
        quiet = _seen("sensor.rain", changed=start - timedelta(hours=1))
        assert first_report_after(own, [sibling, quiet], start) == T0 - timedelta(
            minutes=4
        )

    def test_nothing_changed_since_the_start(self):
        start = T0 - timedelta(hours=6)
        own = _seen(changed=start - timedelta(minutes=1))
        assert first_report_after(own, [], start) is None

    def test_an_unavailable_state_is_not_a_return(self):
        start = T0 - timedelta(hours=6)
        own = _seen(valid=False, changed=T0)
        assert first_report_after(own, [], start) is None

    def test_an_unavailable_sibling_is_not_a_return(self):
        start = T0 - timedelta(hours=6)
        own = _seen(changed=T0 - timedelta(minutes=3))
        gone = _seen("sensor.battery", valid=False, changed=start + timedelta(hours=2))
        assert first_report_after(own, [gone], start) == T0 - timedelta(minutes=3)

    def test_a_change_at_the_start_itself_is_not_after_it(self):
        start = T0 - timedelta(hours=6)
        own = _seen(changed=T0 - timedelta(minutes=3))
        last = _seen("sensor.temp", changed=start)
        assert first_report_after(own, [last], start) == T0 - timedelta(minutes=3)

    def test_without_a_device_the_entity_marks_its_own_return(self):
        start = T0 - timedelta(hours=6)
        own = _seen(changed=T0 - timedelta(minutes=3))
        assert first_report_after(own, [], start) == T0 - timedelta(minutes=3)


def _record(**changes):
    return {"entity_id": "sensor.t", "start": "2026-07-01T08:00:00"} | changes


class TestOutageInTheStore:
    def test_round_trip(self):
        outage = Outage(
            "sensor.t", "dev1", ("Temperature",), T0 - timedelta(hours=4), T0
        )
        assert outage.to_store() == {
            "entity_id": "sensor.t",
            "device_id": "dev1",
            "fields": ["Temperature"],
            "start": "2026-07-01T08:00:00",
            "end": "2026-07-01T12:00:00",
        }
        assert Outage.from_store(outage.to_store()) == outage

    def test_an_open_outage_has_no_end(self):
        outage = Outage("sensor.t", None, ("Temperature",), T0)
        assert outage.to_store()["end"] is None
        assert Outage.from_store(outage.to_store()) == outage

    @pytest.mark.parametrize(
        "raw",
        [
            None,
            "text",
            {},
            {"entity_id": "sensor.t"},
            {"entity_id": "sensor.t", "start": "garbage"},
            {"start": "2026-07-01T08:00:00"},
            _record(entity_id=""),
            _record(fields=5),
            _record(fields="Temperature"),
            _record(fields=[1]),
            _record(fields=["Temperature", 1]),
            _record(end="garbage"),
        ],
    )
    def test_an_unreadable_record_is_dropped_not_raised(self, raw):
        assert Outage.from_store(raw) is None

    @pytest.mark.parametrize(
        "raw", [_record(), _record(fields=None), _record(fields=[])]
    )
    def test_a_record_without_its_optional_keys_still_reads(self, raw):
        assert Outage.from_store(raw) == Outage(
            "sensor.t", None, (), T0 - timedelta(hours=4)
        )


class TestOutagesOf:
    def test_it_keeps_what_is_readable_and_skips_the_rest(self):
        first = Outage("sensor.t", "dev1", ("Temperature",), T0 - timedelta(hours=6))
        last = Outage("sensor.w", None, ("Windspeed",), T0 - timedelta(hours=4), T0)
        stored = [first.to_store(), "junk", None, _record(fields=5), last.to_store()]
        assert outages_of({const.MAPPING_SENSOR_OUTAGES: stored}) == [first, last]

    @pytest.mark.parametrize(
        "mapping",
        [
            {},
            {const.MAPPING_SENSOR_OUTAGES: None},
            {const.MAPPING_SENSOR_OUTAGES: 5},
        ],
    )
    def test_a_group_without_a_ledger_list_has_no_outages(self, mapping):
        assert outages_of(mapping) == []


STALE = timedelta(seconds=const.SENSOR_STALE_AFTER_SECONDS)


def _evidence(last, *, fields=("Temperature",), device="dev1", recovered=None):
    return Evidence(fields=fields, device_id=device, last=last, recovered=recovered)


class TestAdvanceOutages:
    def test_silence_up_to_the_limit_is_bridged(self):
        assert advance_outages([], {"sensor.t": _evidence(T0 - STALE)}, T0) == (
            [],
            [],
            [],
        )

    def test_silence_past_the_limit_opens_an_outage_at_the_last_sign(self):
        last = T0 - STALE - timedelta(seconds=1)
        expected = Outage("sensor.t", "dev1", ("Temperature",), last)
        assert advance_outages([], {"sensor.t": _evidence(last)}, T0) == (
            [expected],
            [expected],
            [],
        )

    def test_an_open_outage_is_not_opened_twice(self):
        start = T0 - timedelta(hours=5)
        open_ = Outage("sensor.t", "dev1", ("Temperature",), start)
        assert advance_outages([open_], {"sensor.t": _evidence(start)}, T0) == (
            [open_],
            [],
            [],
        )

    def test_a_new_sign_closes_it_at_the_first_report(self):
        start = T0 - timedelta(hours=5)
        back = T0 - timedelta(minutes=4)
        open_ = Outage("sensor.t", "dev1", ("Temperature",), start)
        ended = Outage("sensor.t", "dev1", ("Temperature",), start, back)
        assert advance_outages(
            [open_], {"sensor.t": _evidence(T0, recovered=back)}, T0
        ) == ([ended], [], [ended])

    def test_without_a_recorded_change_the_newest_report_ends_it(self):
        start = T0 - timedelta(hours=5)
        open_ = Outage("sensor.t", "dev1", ("Temperature",), start)
        _, _, closed = advance_outages(
            [open_], {"sensor.t": _evidence(T0 - timedelta(minutes=1))}, T0
        )
        assert closed[0].end == T0 - timedelta(minutes=1)

    def test_an_outage_of_an_entity_no_longer_watched_ends_now(self):
        start = T0 - timedelta(hours=5)
        open_ = Outage("sensor.gone", "dev1", ("Temperature",), start)
        ended = Outage("sensor.gone", "dev1", ("Temperature",), start, T0)
        assert advance_outages([open_], {}, T0) == ([ended], [], [ended])

    def test_no_evidence_opens_nothing(self):
        assert advance_outages([], {"sensor.t": _evidence(None)}, T0) == ([], [], [])

    def test_closed_outages_older_than_the_retention_are_dropped(self):
        edge = T0 - timedelta(days=const.SENSOR_OUTAGE_RETENTION_DAYS)
        old = Outage(
            "sensor.a",
            None,
            ("Temperature",),
            edge - timedelta(hours=5),
            edge - timedelta(seconds=1),
        )
        kept = Outage(
            "sensor.b", None, ("Temperature",), edge - timedelta(hours=5), edge
        )
        still_open = Outage("sensor.c", None, ("Temperature",), T0 - timedelta(days=30))
        evidence = {"sensor.c": _evidence(T0 - timedelta(days=30), device=None)}
        outages, _, _ = advance_outages([old, kept, still_open], evidence, T0)
        assert outages == [kept, still_open]
