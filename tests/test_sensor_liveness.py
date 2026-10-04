"""Weather-sensor liveness: the pure rules, without Home Assistant."""

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.calculation import BUFFER_RETENTION


def test_closed_outages_are_kept_as_long_as_the_buffer_keeps_rows():
    """Closed outages cover the same days as the readings they describe: they are
    kept exactly as long as the reading buffer keeps rows."""
    assert (
        const.SENSOR_OUTAGE_RETENTION_DAYS * 86400 == BUFFER_RETENTION.total_seconds()
    )


def test_the_limits_are_the_documented_ones():
    """The docs name three hours and a check every five minutes, the startup grace
    is ten minutes; every other test derives its times from these constants."""
    assert const.SENSOR_STALE_AFTER_SECONDS == 3 * 3600
    assert const.SENSOR_LIVENESS_INTERVAL_SECONDS == 5 * 60
    assert const.SENSOR_LIVENESS_STARTUP_GRACE_SECONDS == 10 * 60
