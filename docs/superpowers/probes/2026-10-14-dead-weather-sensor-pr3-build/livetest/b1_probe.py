"""B1 probe: does a buffer row INSIDE a pausing group's block change the ET of the valid time?

Rebuilds the HA-Test buffer of 2026-10-15 (constant readings, stamps from the live run)
and prices the window [W, now) with the PR 3 code (worktree c21478c8) twice: just before
the 12:32:06.287 poll row arrived and just after. Coordinates are approximate (the
probe is qualitative; HA-Test's real ones are not read here).
"""
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, r"D:\Entwicklung\HASI\issue8-pr3-work\wt")
from custom_components.irrigation_plus import const  # noqa: E402
from custom_components.irrigation_plus.et_estimate import SiteGeometry, hourly_eto_priced  # noqa: E402

D = datetime.fromisoformat
T, RH, WIND, SUN = const.MAPPING_TEMPERATURE, const.MAPPING_HUMIDITY, const.MAPPING_WINDSPEED, const.MAPPING_SOLRAD
VALUES = {T: 15.0, RH: 70.0, WIND: 2.0, SUN: 350 * 0.0864}
W = D("2026-10-15T09:30:25.800856")
BLOCK_FROM = D("2026-10-15T12:30:11.744301")
STAMPS = [
    "09:30:25.70", "09:31:02.95", "09:32:06.29", "10:32:06.32", "11:32:06.34",  # before the block
    "12:32:06.28",  # the hourly poll, inside the block
]
GEO = SiteGeometry(50.0, 6.8, 400.0, 2.0, ZoneInfo("Europe/Berlin"))
CFG = {f: {"source": "sensor", "sensorentity": "sensor.x_" + f.lower(), "unit": ""} for f in VALUES}


def rows_until(cut):
    out = []
    for s in STAMPS:
        stamp = D("2026-10-15T" + s)
        if stamp <= cut:
            out.append({const.RETRIEVED_AT: stamp, **VALUES})
    return out


def priced(now, *, pause):
    readings = rows_until(now)
    blocked = {f: ((BLOCK_FROM, now),) for f in VALUES} if pause else None
    res = hourly_eto_priced(readings, W, CFG, now=now, last_entry=dict(VALUES), geometry=GEO, blocked=blocked)
    if res is None:
        return None
    rows, series = res
    return sum(series), {r["hour_start"].strftime("%H"): (round(e, 5), r.get("coverage_h"), r.get("solar_mj_h")) for r, e in zip(rows, series)}


a = D("2026-10-15T12:32:06.018")  # after the outage opened, before the poll row
b = D("2026-10-15T12:32:06.287")  # right after the poll row
for pause in (True, False):
    ta, ha = priced(a, pause=pause)
    # Same "now" for both, so only the row differs:
    readings_b = rows_until(b)
    blocked = {f: ((BLOCK_FROM, b),) for f in VALUES} if pause else None
    rows_b, series_b = hourly_eto_priced(readings_b, W, CFG, now=b, last_entry=dict(VALUES), geometry=GEO, blocked=blocked)
    readings_nb = [r for r in readings_b if r[const.RETRIEVED_AT] < D("2026-10-15T12:32:06")]
    rows_nb, series_nb = hourly_eto_priced(readings_nb, W, CFG, now=b, last_entry=dict(VALUES), geometry=GEO, blocked=blocked)
    print("pause" if pause else "keep ")
    print("  now=b with the 12:32 row   :", round(sum(series_b), 5))
    print("  now=b without the 12:32 row:", round(sum(series_nb), 5))
    print("  diff                       :", round(sum(series_b) - sum(series_nb), 5))
    for rb, eb, rn, en in zip(rows_b, series_b, rows_nb, series_nb):
        if abs(eb - en) > 1e-9 or rb["hour_start"].hour >= 11:
            print("   hour", rb["hour_start"].strftime("%H"), "with:", round(eb, 5), rb.get("coverage_h"), rb.get("solar_mj_h"),
                  "| without:", round(en, 5), rn.get("coverage_h"), rn.get("solar_mj_h"))


print("\n--- hypothesis 2: the carry re-reduces from the hour boundary 12:00 ---")
H12 = D("2026-10-15T12:00:00")
for pause in (True, False):
    readings_b = rows_until(b)
    blocked = {f: ((BLOCK_FROM, b),) for f in VALUES} if pause else None
    full_rows, full_series = hourly_eto_priced(readings_b, W, CFG, now=b, last_entry=dict(VALUES), geometry=GEO, blocked=blocked)
    sub_rows, sub_series = hourly_eto_priced(readings_b, H12, CFG, now=b, last_entry=dict(VALUES), geometry=GEO, blocked=blocked)
    full12 = [(round(e, 5), r.get("coverage_h"), r.get("solar_mj_h")) for r, e in zip(full_rows, full_series) if r["hour_start"] == H12]
    sub12 = [(round(e, 5), r.get("coverage_h"), r.get("solar_mj_h")) for r, e in zip(sub_rows, sub_series) if r["hour_start"] == H12]
    print("pause" if pause else "keep ", "hour 12 full-window:", full12, "| from 12:00:", sub12)


print("\n--- pre-existing? no block at all, hour 12 without any solar sample (no 12:32 row) ---")
readings_nb = [r for r in rows_until(b) if r[const.RETRIEVED_AT] < D("2026-10-15T12:32:06")]
full_rows, full_series = hourly_eto_priced(readings_nb, W, CFG, now=b, last_entry=dict(VALUES), geometry=GEO, blocked=None)
sub_rows, sub_series = hourly_eto_priced(readings_nb, H12, CFG, now=b, last_entry=dict(VALUES), geometry=GEO, blocked=None)
f12 = [(round(e, 5), r.get("solar_mj_h")) for r, e in zip(full_rows, full_series) if r["hour_start"] == H12]
s12 = [(round(e, 5), r.get("solar_mj_h")) for r, e in zip(sub_rows, sub_series) if r["hour_start"] == H12]
print("no block, hour 12 full-window:", f12, "| from 12:00:", s12)
