# Evidence for specs/2026-09-28-weather-buffer-one-frame-design.md (Revision 4), probe P6.
# Run against a checkout of upstream 1876aa03 (see the sibling frame probe for the path).
# Archived copy: the original imported the sibling as `probe_frame`; here it is loaded from
# its dated file name instead. Nothing else differs.
"""Probe: what the plan's own end-to-end pin 2 sees under the plan's Task-1 rule."""
import datetime
import importlib.util
import pathlib
import sys

_spec = importlib.util.spec_from_file_location(
    "probe_frame",
    pathlib.Path(__file__).with_name("2026-09-28-weather-buffer-frame-probe.py"),
)
pf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pf)  # its own sections print first

from homeassistant.util import dt as dt_util  # noqa: E402

from custom_components.irrigation_plus import const, helpers  # noqa: E402
from custom_components.irrigation_plus import weather_aggregate as wa  # noqa: E402

pf.use(pf.task1_coerce)
helpers._process_timezone = lambda: pf.UTC
dt_util.set_default_time_zone(pf.BERLIN)
readings = [
    {const.RETRIEVED_AT: datetime.datetime(2026, 7, 15, 10, 0), const.MAPPING_TEMPERATURE: 20.0,
     const.MAPPING_HUMIDITY: 50.0, const.MAPPING_WINDSPEED: 2.0, const.MAPPING_SOLRAD: 2.5},
    {const.RETRIEVED_AT: datetime.datetime(2026, 7, 15, 11, 0), const.MAPPING_TEMPERATURE: 21.0,
     const.MAPPING_HUMIDITY: 48.0, const.MAPPING_WINDSPEED: 2.2, const.MAPPING_SOLRAD: 2.7},
]
rows = wa.build_hourly_rows(readings, None, {}, now=datetime.datetime(2026, 7, 15, 13, 0),
                            latitude=50.0, longitude=6.0, elevation=200.0, tz=pf.BERLIN)
hours = [r["hour"] for r in rows]
print("\n=== P6 plan pin 2 under Task-1 rule ===")
print("row hours:", hours, "| coverage:", [round(r["coverage_h"], 2) for r in rows])
print("plan assertion min(hours) >= 12.0 ->", min(hours) >= 12.0, "| rows[0].tz_offset_h ->", rows[0]["tz_offset_h"])
print("window hours covered:", round(sum(r["coverage_h"] for r in rows), 2), "(real: 13:00 local minus 12:00 local = 1.0)")
dt_util.set_default_time_zone(pf.UTC)
sys.exit(0)
