"""Read-only probe for candidates 3/5: what happens to a weather-service Precipitation value
when the sensor group's Precipitation source is "none" (const.MAPPING_CONF_SOURCE_NONE).

Uses the REAL source (pulled out with ``ast`` from blobs extracted at bbf2e151):
  * calculation.py:255   CalculationMixin.strip_foreign_source_values
  * weather_aggregate.py effective_aggregate / cumulative_* / _group_by_sensor / _aggregate
  * const.py             MAPPING_* and CUMULATIVE_RESET_FRAC constants
The integration package is NOT imported. Stdlib only.
"""

import ast
import datetime
import statistics
import textwrap
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---- const namespace (only plain assignments of MAPPING_* / CUMULATIVE_* / RETRIEVED_AT / OBSERVATION_TIME)
csrc = (HERE / "const_blob.py").read_text(encoding="utf-8")
cns = {}
for node in ast.parse(csrc).body:
    if isinstance(node, ast.Assign):
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if any(n.startswith(("MAPPING_", "CUMULATIVE_")) or n in ("RETRIEVED_AT", "OBSERVATION_TIME") for n in names):
            try:
                exec(ast.get_source_segment(csrc, node), cns)
            except Exception:  # noqa: BLE001  (a constant that needs something we did not load)
                pass
const = types.SimpleNamespace(**{k: v for k, v in cns.items() if not k.startswith("__")})

# ---- real functions
g = {"const": const, "statistics": statistics, "datetime": datetime}
wsrc = (HERE / "weather_aggregate_blob.py").read_text(encoding="utf-8")
want = {
    "effective_aggregate", "cumulative_reset_threshold", "cumulative_delta_increments",
    "cumulative_delta_total", "_group_by_sensor", "_aggregate", "_parse",
}
for node in ast.parse(wsrc).body:
    if isinstance(node, ast.FunctionDef) and node.name in want:
        if node.name == "_parse":
            continue  # needs helpers.coerce_stamp; replaced below with an identity for datetimes
        exec(ast.get_source_segment(wsrc, node), g)
    if isinstance(node, ast.Assign):
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "_INTEGRAL_AGGREGATES" in names:
            exec(ast.get_source_segment(wsrc, node), g)
g["_parse"] = lambda v: v  # stamps in this probe are already naive datetimes

calc_src = (HERE / "calculation_blob.py").read_text(encoding="utf-8")
for node in ast.parse(calc_src).body:
    if isinstance(node, ast.ClassDef) and node.name == "CalculationMixin":
        for sub in node.body:
            if isinstance(sub, ast.FunctionDef) and sub.name == "strip_foreign_source_values":
                seg = textwrap.dedent(ast.get_source_segment(calc_src, sub, padded=True))
                exec(seg, g)
strip = g["strip_foreign_source_values"]
effective_aggregate = g["effective_aggregate"]
_aggregate = g["_aggregate"]

print("constants: MAPPING_CONF_SOURCE_NONE =", repr(const.MAPPING_CONF_SOURCE_NONE),
      "| DEFAULT precipitation aggregate =", const.MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT_PRECIPITATION,
      "| CUMULATIVE_RESET_FRAC =", const.CUMULATIVE_RESET_FRAC)

PRECIP = const.MAPPING_PRECIPITATION
T0 = datetime.datetime(2026, 7, 1, 0, 0)


def service_row(mm):
    """What every weather-service client's get_data() puts in the row (Open-Meteo/OWM/Pirate/MetOffice)."""
    return {
        "Temperature": 18.0, "Humidity": 70.0, "Dewpoint": 12.0, "Windspeed": 2.0, "Pressure": 1013.0,
        "Current Precipitation": mm, PRECIP: mm,
    }


def mapping(precip_source, others="weather_service"):
    m = {k: {"source": others} for k in ("Temperature", "Humidity", "Dewpoint", "Windspeed", "Pressure")}
    m[PRECIP] = {"source": precip_source}
    return {const.MAPPING_MAPPINGS: m}


print()
print("A. strip_foreign_source_values (calculation.py:255) on a service row, by Precipitation source")
for src_name in ("none", "sensor", "static", "weather_service"):
    row = service_row(0.4)
    out = strip(None, row, mapping(src_name))
    print(f"   Precipitation source {src_name!r:18s}: Precipitation still in row? {PRECIP in out}")

print()
print("B. The aggregate the calculation then books (hourly service rows: 0.0, 0.4, 0.4, 0.0 mm in the past hour)")
hours = [0.0, 0.4, 0.4, 0.0]
samples = [(T0 + datetime.timedelta(hours=i), v) for i, v in enumerate(hours)]
for src_name in ("weather_service", "none"):
    cfg = mapping(src_name)[const.MAPPING_MAPPINGS]
    res = {}
    _aggregate({PRECIP: samples}, cfg, res, T0, T0 + datetime.timedelta(hours=3))
    print(f"   Precipitation source {src_name!r:18s}: aggregate rule = {effective_aggregate(PRECIP, cfg):10s} -> weatherdata['Precipitation'] = {res[PRECIP]:.3f} mm")
print("   (None / not used, i.e. what the label promises: 0.000 mm)")

print()
print("C. Case (b): no weather service, sensor group supplies no precipitation => the row has no Precipitation key")
wd = {"Temperature": 18.0}
print("   weatherdata.get('Precipitation', 0) ->", wd.get(PRECIP, 0), " (calculation.py:1209)")
