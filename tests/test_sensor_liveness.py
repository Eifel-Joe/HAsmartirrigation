"""Weather-sensor liveness: the pure rules, without Home Assistant."""

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.calculation import BUFFER_RETENTION
from custom_components.irrigation_plus.sensor_liveness import sensor_fields_by_entity


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
        # A field switched away from a sensor can keep its old entity.
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
        const.MAPPING_CURRENT_PRECIPITATION: _cfg(const.MAPPING_CONF_SOURCE_SENSOR),
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
