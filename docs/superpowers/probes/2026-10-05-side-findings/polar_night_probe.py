"""Read-only probe for candidate 4 (PyETO polar night) at upstream bbf2e151.

Runs the REAL ``calculate`` / ``calculate_et_for_day`` source of
calcmodules/pyeto/__init__.py (pulled out with ``ast`` from an extracted copy; the
integration package itself is NOT imported) against the REAL vendored FAO-56
library (calcmodules/pyeto/pyeto/*, extracted copies). Stdlib only.
"""

import ast
import datetime
import enum
import logging
import math
import sys
import textwrap
import traceback
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "pyeto_extracted"))

import pyeto  # noqa: E402  (the vendored library copy)
from pyeto import (  # noqa: E402
    avp_from_tdew,
    convert,
    cs_rad,
    daylight_hours,
    deg2rad,
    delta_svp,
    et_rad,
    fao56_penman_monteith,
    inv_rel_dist_earth_sun,
    net_in_sol_rad,
    net_out_lw_rad,
    net_rad,
    psy_const,
    sol_dec,
    sol_rad_from_sun_hours,
    sol_rad_from_t,
    sunset_hour_angle,
    svp_from_t,
)

logging.basicConfig(level=logging.CRITICAL)
_LOGGER = logging.getLogger("probe")

# ---------------------------------------------------------------- build the real module code
src = (HERE / "pyeto_module_init.py").read_text(encoding="utf-8")
tree = ast.parse(src)
ns = {
    "datetime": datetime,
    "mean": mean,
    "_LOGGER": _LOGGER,
    "Enum": enum.Enum,
    "avp_from_tdew": avp_from_tdew,
    "convert": convert,
    "cs_rad": cs_rad,
    "daylight_hours": daylight_hours,
    "deg2rad": deg2rad,
    "delta_svp": delta_svp,
    "et_rad": et_rad,
    "fao56_penman_monteith": fao56_penman_monteith,
    "inv_rel_dist_earth_sun": inv_rel_dist_earth_sun,
    "net_in_sol_rad": net_in_sol_rad,
    "net_out_lw_rad": net_out_lw_rad,
    "net_rad": net_rad,
    "psy_const": psy_const,
    "sol_dec": sol_dec,
    "sol_rad_from_sun_hours": sol_rad_from_sun_hours,
    "sol_rad_from_t": sol_rad_from_t,
    "sunset_hour_angle": sunset_hour_angle,
    "svp_from_t": svp_from_t,
}

wanted_methods = {"calculate", "calculate_et_for_day"}
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "SOLRAD_behavior":
        exec(ast.get_source_segment(src, node), ns)
    elif isinstance(node, ast.FunctionDef) and node.name == "solrad_behavior_value":
        exec(ast.get_source_segment(src, node), ns)
    elif isinstance(node, ast.Assign):
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if any(n.startswith(("MAPPING_", "DEFAULT_")) or n == "DAILY_FORM_FIELDS" for n in names):
            exec(ast.get_source_segment(src, node), ns)
    elif isinstance(node, ast.ClassDef) and node.name == "PyETO":
        for sub in node.body:
            if isinstance(sub, ast.FunctionDef) and sub.name in wanted_methods:
                seg = ast.get_source_segment(src, sub, padded=True)
                exec(textwrap.dedent(seg), ns)

Behav = ns["SOLRAD_behavior"]


class Stub:  # carries exactly the attributes the real methods read
    forecast_days = 0


Stub.calculate = ns["calculate"]
Stub.calculate_et_for_day = ns["calculate_et_for_day"]


def make(lat, elev=100.0, behavior="1", coastal=False):
    o = Stub()
    o._latitude = lat
    o._elevation = elev
    o._coastal = coastal
    o._solrad_behavior = ns["solrad_behavior_value"](behavior)
    return o


def winter_weather(with_solrad=None):
    w = {
        "Dewpoint": -8.0,
        "Minimum Temperature": -10.0,
        "Maximum Temperature": -5.0,
        "Windspeed": 3.0,
        "Pressure": 1000.0,
        "Temperature": -7.5,
        "Humidity": 85.0,
        "Precipitation": 0.0,
    }
    if with_solrad is not None:
        w["Solar Radiation"] = with_solrad
    return w


def where(exc):
    """Innermost frame inside the extracted vendored library or module copy."""
    tb = traceback.extract_tb(exc.__traceback__)
    for fr in reversed(tb):
        p = fr.filename.replace("\\", "/")
        if "pyeto_extracted" in p or "pyeto_module_init" in p or "<string>" in p:
            name = p.split("/")[-1]
            return f"{name}:{fr.lineno} ({fr.line})" if fr.line else f"{name}:{fr.lineno}"
    fr = tb[-1]
    return f"{Path(fr.filename).name}:{fr.lineno}"


def run(label, fn):
    try:
        v = fn()
        return ("OK", v)
    except Exception as e:  # noqa: BLE001
        return (type(e).__name__, f"{e} @ {where(e)}")


# ------------------------------------------------------------------ 0. solar geometry
print("=" * 78)
print("0. Solar geometry at bbf2e151 (FAO-56 sol_dec, vendored sunset_hour_angle)")
print("   max |sol_dec| =", round(math.degrees(0.409), 3), "deg  -> polar-night threshold lat =",
      round(90 - math.degrees(0.409), 3), "deg")


def geometry(lat_deg, day):
    doy = day.timetuple().tm_yday
    sd = sol_dec(doy)
    sha = sunset_hour_angle(deg2rad(lat_deg), sd)
    dl = daylight_hours(sha)
    ird = inv_rel_dist_earth_sun(doy)
    ra = et_rad(deg2rad(lat_deg), sd, sha, ird)
    return doy, sha, dl, ra


for lat, day in [
    (50.0, datetime.date(2026, 12, 21)),
    (65.0, datetime.date(2026, 12, 21)),
    (66.5, datetime.date(2026, 12, 21)),
    (66.6, datetime.date(2026, 12, 21)),
    (69.0, datetime.date(2026, 12, 21)),
    (69.0, datetime.date(2026, 6, 21)),
    (-69.0, datetime.date(2026, 6, 21)),
    (-69.0, datetime.date(2026, 12, 21)),
    (90.0, datetime.date(2026, 12, 21)),
]:
    doy, sha, dl, ra = geometry(lat, day)
    print(f"   lat {lat:6.1f}  {day}  doy {doy:3d}  sha {sha:.4f} rad  daylight {dl:6.3f} h  Ra {ra:8.4f} MJ/m2/d")

# ------------------------------------------------------------------ 1. polar-night day ranges
print()
print("=" * 78)
print("1. Days per year with daylight == 0 (sha == 0), non-leap 2026 (doy 1..365)")
for lat in (60, 65, 66.5, 66.6, 67, 68, 69, 69.7, 70, 71, 75, 80, 85, 89.9, -66.6, -67, -69, -70, -75, -80):
    dark = []
    sun24 = []
    for doy in range(1, 366):
        d = datetime.date(2026, 1, 1) + datetime.timedelta(days=doy - 1)
        _, sha, dl, ra = geometry(lat, d)
        if dl == 0.0:
            dark.append(d)
        if dl >= 24.0 - 1e-9:
            sun24.append(d)
    rng = f"{dark[0]:%m-%d}..{dark[-1]:%m-%d}" if dark else "-"
    # Southern/northern ranges can wrap the year end; show first/last by doy and the count
    wrap = ""
    if dark and (dark[-1] - dark[0]).days + 1 != len(dark):
        # wraps around new year: report the two stretches
        a = [d for d in dark if d.month >= 7]
        b = [d for d in dark if d.month < 7]
        wrap = f" (wraps: {a[0]:%m-%d}..12-31 + 01-01..{b[-1]:%m-%d})"
    print(f"   lat {lat:6.1f}: polar-night days = {len(dark):3d}  {rng}{wrap};   midnight-sun days = {len(sun24):3d}")

# ------------------------------------------------------------------ 2. per behaviour, per latitude, on 21 Dec and 15 Dec (calendar day)
print()
print("=" * 78)
print("2. calculate_et_for_day (the real method) on a polar-night day: behaviour x latitude")
print("   weather: Tmin -10, Tmax -5, Tdew -8, wind 3 m/s, 1000 hPa; elevation 100 m")
names = {
    "1": "EstimateFromTemp (DEFAULT)",
    "2": "EstimateFromSunHours",
    "3": "DontEstimate, no Solar Radiation value",
    "3s": "DontEstimate, Solar Radiation sensor = 1.0",
    "4": "EstimateFromSunHoursAndTemperature",
}
for lat in (50.0, 66.5, 69.0, 70.0, -69.0):
    day = datetime.date(2026, 12, 21) if lat > 0 else datetime.date(2026, 6, 21)
    print(f"   --- lat {lat} on {day} ---")
    for key, label in names.items():
        beh = "3" if key == "3s" else key
        w = winter_weather(with_solrad=1.0 if key == "3s" else None)
        res, val = run(label, lambda: make(lat, behavior=beh).calculate_et_for_day(w, day=day))
        if res == "OK":
            print(f"      {label:44s} -> OK  delta={val:.4f} mm")
        else:
            print(f"      {label:44s} -> {res}: {val}")

# ------------------------------------------------------------------ 3. the REAL daily entry point (calculate), exact kwargs of calculation.py:1195-1207
print()
print("=" * 78)
print("3. calculate() as called by calculation.py:1195 (weather_data, forecast_data=None, day=..., forecast_first_day=...)")
day = datetime.date(2026, 12, 21)
for key, label in names.items():
    beh = "3" if key == "3s" else key
    w = winter_weather(with_solrad=1.0 if key == "3s" else None)
    res, val = run(
        label,
        lambda: make(69.0, behavior=beh).calculate(
            weather_data=w,
            forecast_data=None,
            day=day,
            forecast_first_day=day + datetime.timedelta(days=1),
        ),
    )
    print(f"   69N 21 Dec  {label:44s} -> {res}: {val}")

# ------------------------------------------------------------------ 4. the calendar's call: 15th of each month, default behaviour
print()
print("=" * 78)
print("4. watering_calendar.py:286 -- calculate_et_for_day(weather_data, day=date(2024, month, 15)) per month, 69N")
for key in ("1", "2", "4"):
    out = []
    for month in range(1, 13):
        w = {
            "Temperature": 0.0, "Minimum Temperature": -5.0, "Maximum Temperature": 5.0,
            "Humidity": 70.0, "Windspeed": 3.0, "Pressure": 1013.0, "Dewpoint": -3.0, "Precipitation": 50.0,
        }
        res, val = run("m", lambda: make(69.0, elev=0.0, behavior=key).calculate_et_for_day(w, day=datetime.date(2024, month, 15)))
        out.append("ok" if res == "OK" else res[:5])
    print(f"   behaviour {key} ({names[key]}): {out}")

# ------------------------------------------------------------------ 5. full-year sweep: which days raise, by latitude and behaviour
print()
print("=" * 78)
print("5. Full-year sweep (2026, 365 days): number of days on which calculate_et_for_day RAISES")
hdr = "   lat     " + "  ".join(f"beh{k:>2s}" for k in names)
print(hdr)
for lat in (50.0, 60.0, 66.0, 66.6, 68.0, 69.0, 70.0, 75.0, 80.0, -66.6, -69.0, -75.0):
    cells = []
    first_exc = defaultdict(set)
    for key in names:
        beh = "3" if key == "3s" else key
        n = 0
        for doy in range(1, 366):
            d = datetime.date(2026, 1, 1) + datetime.timedelta(days=doy - 1)
            w = winter_weather(with_solrad=1.0 if key == "3s" else None)
            # use a seasonally plausible T (does not matter for the divisions)
            res, val = run("d", lambda: make(lat, behavior=beh).calculate_et_for_day(w, day=d))
            if res != "OK":
                n += 1
                first_exc[key].add(f"{res} @ {val.split(' @ ')[-1]}")
        cells.append(f"{n:5d}")
    print(f"   {lat:6.1f}  " + "  ".join(cells))
    for key, exc in first_exc.items():
        print(f"           beh {key}: {sorted(exc)}")

# ------------------------------------------------------------------ 6. what does the divisor look like at the edge?
print()
print("=" * 78)
print("6. Edge: first/last day with exact zero at 66.6N and 69N, and the smallest non-zero daylight next to it")
for lat in (66.6, 69.0):
    prev = None
    rows = []
    for doy in range(300, 366):
        d = datetime.date(2026, 1, 1) + datetime.timedelta(days=doy - 1)
        _, sha, dl, ra = geometry(lat, d)
        rows.append((d, dl, ra))
    first_zero = next((r for r in rows if r[1] == 0.0), None)
    idx = rows.index(first_zero) if first_zero else None
    if idx:
        for r in rows[idx - 2: idx + 2]:
            print(f"   lat {lat}: {r[0]}  daylight {r[1]:.6f} h  Ra {r[2]:.6f}")
    print()
