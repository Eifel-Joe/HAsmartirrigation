"""Read-only probe: does a pausing group's notice claim a cut the gate never makes?"""

import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

sys.path.insert(0, r"D:\Entwicklung\HASI\issue8-pr2-work\wt")

from custom_components.irrigation_plus import const  # noqa: E402
from custom_components.irrigation_plus.sensor_liveness import (  # noqa: E402
    Outage,
    SensorLivenessMixin,
    blocked_spans,
    outages_of,
    valid_share,
)
from custom_components.irrigation_plus.weather_aggregate import (  # noqa: E402
    effective_aggregate,
)

W = datetime(2026, 7, 1, 23, 0)
NOW = W + timedelta(hours=24)

# 1) A YAML utility-meter rain counter (sensor source, default aggregate) silent all day.
rain_cfg = {
    const.MAPPING_PRECIPITATION: {
        const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
        const.MAPPING_CONF_SENSOR: "sensor.daily_rain",
    }
}
outage = Outage("sensor.daily_rain", None, (const.MAPPING_PRECIPITATION,), W, None)
group = {
    const.MAPPING_ID: 1,
    const.MAPPING_NAME: "Garden",
    const.MAPPING_MAPPINGS: rain_cfg,
    const.MAPPING_ON_SILENT_SENSOR: const.ON_SILENT_SENSOR_PAUSE,
    const.MAPPING_SENSOR_OUTAGES: [outage.to_store()],
}
store = SimpleNamespace(
    config=SimpleNamespace(**{const.CONF_HOURLY_CALCULATION: False}),
    get_mapping=lambda _id: group,
)
mixin = SensorLivenessMixin()
mixin.store = store
gate = {
    f: s
    for f, s in blocked_spans(outages_of(group), W, NOW).items()
    if effective_aggregate(f, rain_cfg) != const.MAPPING_CONF_AGGREGATE_DELTA
}
print("rain gauge: notice key =", mixin._stale_issue_key(1))
print("rain gauge: gate blocks =", gate or None)

# 2) The docs' YAML wind_at_2m template (no device) flat at 0 from 21:00 to 07:00.
wind = Outage(
    "sensor.wind_at_2m",
    None,
    (const.MAPPING_WINDSPEED,),
    datetime(2026, 7, 1, 21, 0),
    datetime(2026, 7, 2, 7, 0),
)
spans = blocked_spans([wind], W, NOW)
print("calm night: blocked =", spans)
share = valid_share(
    spans,
    (
        const.MAPPING_DEWPOINT,
        const.MAPPING_TEMPERATURE,
        const.MAPPING_WINDSPEED,
        const.MAPPING_PRESSURE,
    ),
    W,
    NOW,
)
print(f"calm night: share of the day's ET booked = {share:.3f}")
