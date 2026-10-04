"""Weather-sensor liveness: the pure rules, without Home Assistant."""

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.calculation import BUFFER_RETENTION


def test_closed_outages_are_kept_as_long_as_the_buffer_keeps_rows():
    """A window cannot reach back further than the reading buffer keeps rows, so an
    outage that ended before that can no longer touch any calculation."""
    assert (
        const.SENSOR_OUTAGE_RETENTION_DAYS * 86400 == BUFFER_RETENTION.total_seconds()
    )
