"""O1: the forecast-weighting credit, recomputed from a logged Pirate Weather document.

Live verification of Eifel-Joe#61 (spec 2026-10-07). Deliberately independent of
custom_components/irrigation_plus/forecast_window.py: it re-implements only the
rule that module documents -- each hourly rate covers the step ENDING at its
stamp, the window is [max(start, evaluated_at), start + 24 h), counted pro rata
per second -- and refuses a window the hourly series does not cover instead of
filling it from daily data. The verification picks its windows inside the series.

    python o1.py window <series.json|raw.log> <start-iso> <evaluated-iso>
    python o1.py scan   <series.json|raw.log> <evaluated-iso> <from-iso> <to-iso> <step-min>
    python o1.py extract <raw.log> <out.series.json>
"""
from __future__ import annotations

import ast
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_LINE = re.compile(
    r"^(?P<ts>\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) .*?PirateWeatherClient "
    r"(?P<method>get_forecast_data|get_data) called API \S+ and received (?P<doc>\{.*\})$"
)


def parse_log_line(line: str) -> dict:
    """``{'logged_at', 'method', 'hourly': [[unix, rate], ...]}`` from one raw log line.

    The client logs the document with ``%s``, i.e. as a Python repr, not JSON.
    """
    m = _LINE.match(_ANSI.sub("", line).strip())
    if not m:
        raise ValueError("not a PirateWeatherClient raw-document line")
    doc = ast.literal_eval(m.group("doc"))
    return {
        "logged_at": m.group("ts"),
        "method": m.group("method"),
        "hourly": [[r.get("time"), r.get("precipIntensity")] for r in doc["hourly"]["data"]],
    }


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith(".json"):
        return json.loads(text)
    return parse_log_line(text)


def hourly_series(rows) -> list[tuple[datetime, float]]:
    """Sorted ``(aware UTC stamp, mm/h)``; non-finite dropped, negative = dry, duplicates keep max."""
    by_stamp: dict[datetime, float] = {}
    for stamp, rate in rows:
        if stamp is None or rate is None:
            continue
        rate = float(rate)
        if not math.isfinite(rate):
            continue
        rate = max(rate, 0.0)
        t = datetime.fromtimestamp(int(stamp), tz=timezone.utc)
        by_stamp[t] = max(rate, by_stamp.get(t, rate))
    return sorted(by_stamp.items())


def window_mm(series, start: datetime, evaluated_at: datetime, hours: int = 24) -> float:
    """Rain in mm over ``[max(start, evaluated_at), start + hours)``; ValueError if not covered."""
    lo = max(start, evaluated_at)
    hi = start + timedelta(hours=hours)
    if (hi - lo).total_seconds() <= 1:
        raise ValueError("window lies wholly in the past")
    stamps = [t for t, _ in series]
    if len(stamps) < 2:
        raise ValueError("hourly series too short")
    step = min(b - a for a, b in zip(stamps, stamps[1:]))
    if lo < stamps[0] - step or hi > stamps[-1]:
        raise ValueError("window not covered by the hourly series")
    for a, b in zip(stamps, stamps[1:]):
        if b - a > step and a < hi and b - step > lo:
            raise ValueError(f"hole in the hourly series between {a} and {b}")
    total = 0.0
    for t, rate in series:
        overlap = (min(t, hi) - max(t - step, lo)).total_seconds()
        if overlap > 0:
            total += rate * overlap / 3600.0
    return total


def _iso(text: str) -> datetime:
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        raise SystemExit(f"timestamp without offset: {text}")
    return value.astimezone(timezone.utc)


def _fmt(series, start, evaluated_at) -> str:
    try:
        return f"{window_mm(series, start, evaluated_at):.4f}"
    except ValueError as e:
        return f"n/a ({e})"


def main(argv: list[str]) -> int:
    cmd = argv[1]
    if cmd == "extract":
        with open(argv[2], encoding="utf-8") as fh:
            parsed = parse_log_line(fh.read())
        with open(argv[3], "w", encoding="utf-8", newline="\n") as fh:
            json.dump(parsed, fh)
        print(f"{parsed['method']} {parsed['logged_at']} rows={len(parsed['hourly'])}")
        return 0
    series = hourly_series(load(argv[2])["hourly"])
    if cmd == "window":
        print(f"{window_mm(series, _iso(argv[3]), _iso(argv[4])):.4f}")
        return 0
    if cmd == "scan":
        ev, frm, to, step = _iso(argv[3]), _iso(argv[4]), _iso(argv[5]), int(argv[6])
        print(f"E={ev.isoformat()} O1(E)={_fmt(series, ev, ev)}")
        s = frm
        while s <= to:
            print(
                f"T={s.isoformat()} O1(T)={_fmt(series, s, ev)} "
                f"O1(T+24h)={_fmt(series, s + timedelta(hours=24), ev)}"
            )
            s += timedelta(minutes=step)
        return 0
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
