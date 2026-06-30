"""Store schema for the self-closing valve mode."""

from custom_components.smart_irrigation import const
from custom_components.smart_irrigation.store import STORAGE_VERSION, Config, ZoneEntry


def test_storage_version_is_9():
    assert STORAGE_VERSION == 9


def test_zone_entry_has_self_closing_fields():
    z = ZoneEntry()
    assert z.watering_mode == const.WATERING_MODE_CLASSIC
    assert z.run_service is None
    assert z.duration_field is None
    assert z.duration_unit == const.DURATION_UNIT_SECONDS
    assert z.run_data == {}
    assert z.stop_service is None
    assert z.stop_data == {}


def test_zone_entry_has_mqtt_fields():
    z = ZoneEntry()
    assert z.mqtt_topic is None
    assert z.mqtt_open_field is None
    assert z.mqtt_open_value is None
    assert z.mqtt_stop_value is None


def test_config_has_active_valve_runs():
    c = Config()
    assert c.active_valve_runs == []
