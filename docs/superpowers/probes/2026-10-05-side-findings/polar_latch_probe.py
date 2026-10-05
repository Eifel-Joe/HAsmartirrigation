"""Read-only probe: does a polar-night ZeroDivisionError latch the daily calculation?

Mirrors the control flow of calculation.py (bbf2e151):
  * async_calculate_zone: success path writes ZONE_LAST_CONSUMED = now (line 622);
    an exception from calculate_module (line 605) writes NOTHING (caught one level up,
    _async_calculate_all lines 531-540).
  * calculate_module line 1201: day = weather_day(ZONE_LAST_CONSUMED, now)
The REAL ``weather_day`` (weather_aggregate.py:230) and the REAL PyETO ``calculate``
(calcmodules/pyeto/__init__.py:209) are pulled out of extracted copies with ``ast``.
The integration package is NOT imported. Stdlib only.
"""

import ast
import datetime
import textwrap
from pathlib import Path

import probe_lib as P  # shared loader: real calculate() + vendored FAO-56, extracted copies only

HERE = Path(__file__).resolve().parent

# --- real weather_day() ---------------------------------------------------------------
wa_src = (HERE / "weather_aggregate_blob.py").read_text(encoding="utf-8")
wa_tree = ast.parse(wa_src)
ns = {"datetime": datetime}
for node in wa_tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "weather_day":
        exec(ast.get_source_segment(wa_src, node), ns)
weather_day = ns["weather_day"]


def simulate(lat, calc_hour, behavior="1", start=datetime.date(2026, 11, 1), end=datetime.date(2027, 3, 1)):
    mod = P.make(lat, behavior=behavior)
    w = P.winter_weather()
    watermark = datetime.datetime.combine(start, datetime.time(calc_hour, 0))
    timeline = []
    d = start + datetime.timedelta(days=1)
    while d <= end:
        now = datetime.datetime.combine(d, datetime.time(calc_hour, 0))
        day = weather_day(watermark, now)  # calculation.py:1201
        try:
            mod.calculate(
                weather_data=w,
                forecast_data=None,
                day=day,
                forecast_first_day=now.date() + datetime.timedelta(days=1),  # calculation.py:1206
            )
            watermark = now  # calculation.py:622
            timeline.append((d, day, "ok"))
        except ZeroDivisionError:
            timeline.append((d, day, "FAIL"))  # watermark untouched
        d += datetime.timedelta(days=1)
    return timeline


def summarize(timeline):
    fails = [t for t in timeline if t[2] == "FAIL"]
    if not fails:
        return "no failures"
    first = fails[0]
    last_ok_after = [t for t in timeline if t[0] > first[0] and t[2] == "ok"]
    pinned = sorted({t[1] for t in fails})
    return (
        f"first FAIL calc on {first[0]} (prices day {first[1]}); {len(fails)} failing calcs; "
        f"days priced while failing: {pinned[0]}..{pinned[-1]} ({len(pinned)} distinct); "
        f"successful calcs after first failure: {len(last_ok_after)}; "
        f"last calc in window ({timeline[-1][0]}): {timeline[-1][2]}"
    )


print("Daily calc at 23:00 (CONF_DEFAULT_CALC_TIME, const.py:321), default behaviour EstimateFromTemp,")
print("simulated 2026-11-02 .. 2027-03-01 with NO user intervention (no bucket edit, no weather reset):")
for lat in (50.0, 66.5, 66.6, 68.0, 69.0, 70.0):
    print(f"  lat {lat:5.1f}: {summarize(simulate(lat, 23))}")

print()
print("Same with calc at 00:00:")
for lat in (69.0,):
    print(f"  lat {lat:5.1f}: {summarize(simulate(lat, 0))}")

print()
print("Ground truth for comparison: days with daylight == 0 at 69N (stateless view):")
dark = []
d = datetime.date(2026, 11, 1)
while d <= datetime.date(2027, 3, 1):
    _, sha, dl, ra = P.geometry(69.0, d)
    if dl == 0.0:
        dark.append(d)
    d += datetime.timedelta(days=1)
print(f"  {dark[0]} .. {dark[-1]}  ({len(dark)} days)")

print()
print("Timeline excerpt at 69N / 23:00 around the start and after the sun returns:")
tl = simulate(69.0, 23)
for t in tl:
    if t[0] in (
        datetime.date(2026, 11, 22), datetime.date(2026, 11, 23), datetime.date(2026, 11, 24), datetime.date(2026, 11, 25),
        datetime.date(2026, 12, 21), datetime.date(2027, 1, 16), datetime.date(2027, 1, 17), datetime.date(2027, 1, 18),
        datetime.date(2027, 2, 1), datetime.date(2027, 3, 1),
    ):
        print(f"  calc on {t[0]} 23:00 prices day {t[1]} -> {t[2]}")

print()
print("Recovery check (user sets the bucket by hand => watermark moves to 'now', __init__.py:2021):")
# After the latch, emulate a manual bucket assertion on 2027-02-01 at 12:00 and continue.
mod = P.make(69.0)
w = P.winter_weather()
wm = datetime.datetime(2027, 2, 1, 12, 0)
now = datetime.datetime(2027, 2, 1, 23, 0)
day = weather_day(wm, now)
try:
    mod.calculate(weather_data=w, forecast_data=None, day=day, forecast_first_day=now.date() + datetime.timedelta(days=1))
    print(f"  after manual bucket edit: calc on {now} prices day {day} -> ok")
except ZeroDivisionError as e:
    print(f"  after manual bucket edit: FAIL {e}")
