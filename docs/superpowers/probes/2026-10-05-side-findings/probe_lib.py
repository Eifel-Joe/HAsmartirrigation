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



def geometry(lat_deg, day):
    doy = day.timetuple().tm_yday
    sd = sol_dec(doy)
    sha = sunset_hour_angle(deg2rad(lat_deg), sd)
    dl = daylight_hours(sha)
    ird = inv_rel_dist_earth_sun(doy)
    ra = et_rad(deg2rad(lat_deg), sd, sha, ird)
    return doy, sha, dl, ra
