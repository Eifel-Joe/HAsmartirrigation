"""Stand-in site search for the Eifel-Joe#61 live verification (spec §10.2, revision 2).

The home site of HA-Test has no rain in sight, so the test borrows the
coordinates of a public place that has. Open-Meteo's GFS run (free, no key)
ranks a fixed list of places in HA-Test's UTC offset by the spec's criterion;
the Pirate Weather document fetched at the chosen place then has to pass the
same criterion (``check``) before any phase starts. Rain sums reuse o1.py's
rule: each hourly value covers the hour ENDING at its stamp, pro rata.

    python scout.py rank
    python scout.py check <series.json> <now-iso>
"""
from __future__ import annotations

import json
import math
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

import o1

URL = (
    "https://api.open-meteo.com/v1/gfs?latitude={lat}&longitude={lon}"
    "&hourly=precipitation&forecast_days=4&timezone=GMT&timeformat=unixtime"
)

# Public places in HA-Test's UTC offset (CET/CEST).
CANDIDATES = [
    ("Bergen", 60.39, 5.32), ("Stavanger", 58.97, 5.73), ("Goeteborg", 57.71, 11.97),
    ("Esbjerg", 55.48, 8.45), ("Kopenhagen", 55.68, 12.57), ("Kiel", 54.32, 10.13),
    ("Rostock", 54.09, 12.10), ("Gdansk", 54.35, 18.65), ("Hamburg", 53.55, 9.99),
    ("Groningen", 53.22, 6.57), ("Bremen", 53.08, 8.80), ("Amsterdam", 52.37, 4.90),
    ("Koeln", 50.94, 6.96), ("Bruessel", 50.85, 4.35), ("Prag", 50.08, 14.44),
    ("Brest", 48.39, -4.49), ("Muenchen", 48.14, 11.58), ("Freiburg", 47.99, 7.85),
    ("Zuerich", 47.38, 8.54), ("Innsbruck", 47.27, 11.39), ("Nantes", 47.22, -1.55),
    ("Lyon", 45.76, 4.84), ("Mailand", 45.46, 9.19), ("Bordeaux", 44.84, -0.58),
    ("Genua", 44.41, 8.93), ("Bilbao", 43.26, -2.93), ("Santiago de Compostela", 42.88, -8.54),
]


def assess(series, now, horizon_h=8, step_min=15, min_rain=2.0, min_gap=0.5, t1_from_h=1, t1_to_h=20):
    """Spec §10.2 criterion; ``reserve`` >= 0 means it holds, smaller = closer to a threshold."""
    step = timedelta(minutes=step_min)
    reserve, worst = math.inf, None
    t = now
    while t <= now + timedelta(hours=horizon_h):
        day1 = o1.window_mm(series, t, t)
        day2 = o1.window_mm(series, t + timedelta(hours=24), t)
        margin = min(day1 - min_rain, abs(day1 - day2) - min_gap)
        if margin < reserve:
            reserve, worst = margin, t
        t += step
    r_now = o1.window_mm(series, now, now)
    t1, t1_gap = None, -math.inf
    t = now + timedelta(hours=t1_from_h)
    while t <= now + timedelta(hours=t1_to_h):
        gap = abs(o1.window_mm(series, t, now) - r_now)
        if gap > t1_gap:
            t1, t1_gap = t, gap
        t += step
    reserve = min(reserve, t1_gap - min_gap)
    return {"ok": reserve >= 0, "reserve": reserve, "worst_t": worst, "t1": t1, "r_now": r_now}


def fetch(lat, lon):
    """``(grid elevation m, [[unix, mm in the hour ending there], ...])`` from Open-Meteo GFS."""
    with urllib.request.urlopen(URL.format(lat=lat, lon=lon), timeout=30) as resp:
        doc = json.load(resp)
    hourly = doc["hourly"]
    return doc.get("elevation"), [list(p) for p in zip(hourly["time"], hourly["precipitation"])]


def _line(name, lat, lon, elevation, result):
    t1 = result["t1"].strftime("%d.%m %H:%M") if result["t1"] else "-"
    worst = result["worst_t"].strftime("%d.%m %H:%M") if result["worst_t"] else "-"
    return (
        f"ok={result['ok']} reserve={result['reserve']:.2f} r_now={result['r_now']:.2f} "
        f"worst={worst}Z t1={t1}Z {name} {lat:.2f} {lon:.2f} elev={elevation}"
    )


def main(argv):
    cmd = argv[1]
    if cmd == "check":
        series = o1.hourly_series(o1.load(argv[2])["hourly"])
        now = datetime.fromisoformat(argv[3]).astimezone(timezone.utc)
        print(_line("pirate", 0.0, 0.0, None, assess(series, now)))
        return 0
    if cmd == "rank":
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        found = []
        for name, lat, lon in CANDIDATES:
            elevation, raw = fetch(lat, lon)
            found.append((assess(o1.hourly_series(raw), now), name, lat, lon, elevation, raw))
        raw0 = found[0][5]
        print(f"now={now.isoformat()} rows={len(raw0)} first={raw0[0][0]} last={raw0[-1][0]}")
        for result, name, lat, lon, elevation, _ in sorted(found, key=lambda f: -f[0]["reserve"]):
            print(_line(name, lat, lon, elevation, result))
        return 0
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
