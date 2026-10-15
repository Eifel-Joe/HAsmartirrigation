"""B1 on upstream/master 6a40e083: carry-style re-reduction from the hour boundary vs the full window."""
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, r"D:\Entwicklung\HASI\issue8-pr3-work\upstream-src")
from custom_components.irrigation_plus import const  # noqa: E402
from custom_components.irrigation_plus.et_estimate import SiteGeometry, hourly_eto_priced  # noqa: E402
import custom_components.irrigation_plus.et_estimate as m  # noqa: E402

print("module from:", m.__file__)
D = datetime.fromisoformat
T, RH, WIND, SUN = const.MAPPING_TEMPERATURE, const.MAPPING_HUMIDITY, const.MAPPING_WINDSPEED, const.MAPPING_SOLRAD
VALUES = {T: 15.0, RH: 70.0, WIND: 2.0, SUN: 350 * 0.0864}
W = D("2026-10-15T09:30:25.800856")
NOW = D("2026-10-15T12:32:06.287")
H12 = D("2026-10-15T12:00:00")
STAMPS = ["09:30:25.70", "09:31:02.95", "09:32:06.29", "10:32:06.32", "11:32:06.34"]
readings = [{const.RETRIEVED_AT: D("2026-10-15T" + s), **VALUES} for s in STAMPS]
GEO = SiteGeometry(50.0, 6.8, 400.0, 2.0, ZoneInfo("Europe/Berlin"))
CFG = {f: {"source": "sensor", "sensorentity": "sensor.x_" + f.lower(), "unit": ""} for f in VALUES}
full_rows, full_series = hourly_eto_priced(readings, W, CFG, now=NOW, last_entry=dict(VALUES), geometry=GEO)
sub_rows, sub_series = hourly_eto_priced(readings, H12, CFG, now=NOW, last_entry=dict(VALUES), geometry=GEO)
f12 = [(round(e, 5), r.get("solar_mj_h")) for r, e in zip(full_rows, full_series) if r["hour_start"] == H12]
s12 = [(round(e, 5), r.get("solar_mj_h")) for r, e in zip(sub_rows, sub_series) if r["hour_start"] == H12]
print("upstream, hour 12 full-window:", f12, "| from 12:00:", s12)
