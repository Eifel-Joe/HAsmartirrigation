# Live-Verifikation der Vorhersage-Gewichtung (Eifel-Joe#61) — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Ausnahme:** Tasks 3–10 schalten auf HA-Test und gehören in die Hauptsitzung (MCP `mcp__HA-Test__…`), nicht an Subagenten.

**Goal:** Die fünf Beobachtungen B1–B5 aus Eifel-Joe#61 auf HA-Test belegen, ohne Codeänderung, und den
Imperial-Verdacht (E3) per lokalem Probetest entscheiden.

**Architecture:** Zwei Wegwerf-Zonen (`classic` auf eigenen `input_boolean`s) auf HA-Test, ein eigener Zeitplan P61, drei
Phasen (`fixed_time` → `before_run` → Live-Estimate). Jede Gutschrift wird gegen ein unabhängiges Orakel O1 (`o1.py`, aus
dem geloggten Pirate-Rohdokument) und, wo möglich, gegen den Regen-Wächter (O2) geprüft.

**Tech Stack:** HA-Test per MCP (`ha_manage_custom_tool`-Sandbox mit `api_post`/`ws_send`/`call_tool`, `ha_call_service`,
`ha_get_logs`, `ha_eval_template`); Python 3.12 aus dem Repo-`.venv` für `o1.py` und den Probetest; pytest.

**Spec:** `docs/superpowers/specs/2026-10-07-forecast-weighting-live-verification-design.md` (freigegeben 2026-10-07).
**Revision 2 (2026-10-11):** Abschnitt „Revision 2“ am Ende ersetzt Task 4 und Task 10 und ergänzt Tasks 3, 5–9, 11
(Spec §10, E4–E6). Ausführungsreihenfolge dort.
**Code-Fakten:** `D:\Entwicklung\HASI\issue61-work\code-facts.md` (Q1–Q10, `upstream/master` `6a40e083`).

---

## Ausführungsregeln (gelten für jeden Task)

- **Instanz nennen:** vor jedem schreibenden MCP-Call im Chat „HA-Test“ sagen; nur `mcp__HA-Test__…`, nie `HA-Prod`.
- **Sicherheit:** Vor jedem Zeitpunkt, an dem P61 feuert, P61 zurücklesen (`zones` = nur 61-A) und 61-A
  (`watering_mode` = `classic`, `linked_entity` = `input_boolean.hasi61_a`). Abweichung → nicht warten, P61 sofort
  `enabled: false`, Rücksprache.
- **Warten ohne Vordergrund-`sleep`:** Monitor-Werkzeug mit until-Schleife auf die Uhrzeit, oder die Zeit mit Lesen
  füllen. HA-Test-Neustart ist in keinem Task nötig; falls doch: vorher ankündigen.
- **Zeiten:** nur aus HA (`ha_eval_template`, Log-Stempel). HA-Logstempel sind Ortszeit (Task 3 stellt den Offset fest).
  Zonen-Attributzeiten nie aus `ha_get_history`.
- **Schlüssel:** `ha_get_integration` gibt den Wetter-API-Schlüssel in `options` aus → diese Ausgabe nie in eine Datei.
  Rohe Log-Zeilen enthalten die Koordinaten von HA-Test → **nicht archivieren**; archiviert werden nur die extrahierten
  Stundenreihen (`*.series.json`, nur Zahlen).
- **Abbruch:** fällt ein Prüfkriterium durch → kein zweiter Anlauf mit umgebautem Aufbau, sondern Befund ins Protokoll,
  `superpowers:systematic-debugging`, Rücksprache. Ein Durchfaller kann ein echter Defekt sein.
- **Protokoll:** jedes Kriterium sofort in `issue61-work\livetest\protocol.md` (Rohzitat, O1, O2, Urteil). Vorlage in
  Task 3.

## Dateien

| Datei | Zweck |
|---|---|
| `D:\Entwicklung\HASI\issue61-work\o1.py` | Orakel O1: Stundenreihe laden, Fenster integrieren, Zeitpunkte scannen |
| `D:\Entwicklung\HASI\issue61-work\o1_test.py` | Tests für `o1.py` |
| `D:\Entwicklung\HASI\issue61-work\imperial_probe_test.py` | Probetest E3 gegen `src-6a40e083\` |
| `D:\Entwicklung\HASI\issue61-work\src-6a40e083\` | `git archive` von `upstream/master` (nur Lesen/Import) |
| `D:\Entwicklung\HASI\issue61-work\livetest\` | `protocol.md`, `config-before.json`, `config-after.json`, `doc-*.series.json` |

---

### Task 0: Arbeitsordner und Quellstand

**Files:** Create: `issue61-work\src-6a40e083\`, `issue61-work\_local_socket_unblock.py`, `issue61-work\livetest\`

- [x] **Step 1: Quellstand ohne Worktree ablegen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && git rev-parse --short upstream/master
mkdir -p /d/Entwicklung/HASI/issue61-work/src-6a40e083 /d/Entwicklung/HASI/issue61-work/livetest
git archive 6a40e083 custom_components | tar -x -C /d/Entwicklung/HASI/issue61-work/src-6a40e083
cp /d/Entwicklung/HASI/HAsmartirrigation/_local_socket_unblock.py /d/Entwicklung/HASI/issue61-work/
ls /d/Entwicklung/HASI/issue61-work/src-6a40e083/custom_components/irrigation_plus/live_estimate.py
```

Expected: erste Zeile `6a40e083` (sonst: Upstream hat sich bewegt → Code-Fakten Q1–Q10 gegen den neuen Stand prüfen,
bevor es weitergeht); `ls` zeigt die Datei.

---

### Task 1: Orakel `o1.py` (TDD)

**Files:** Create: `issue61-work\o1_test.py`, `issue61-work\o1.py`

- [x] **Step 1: Tests schreiben**

```python
"""Tests for o1.py, the oracle of the Eifel-Joe#61 live verification."""
from datetime import datetime, timedelta, timezone

import pytest

import o1

T0 = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
H = timedelta(hours=1)


def rows(rate_at=lambda k: 1.0, first=-30, last=40, drop=()):
    """Hourly rows [unix, rate] for stamps T0 + k h, k in [first, last]."""
    return [
        [int((T0 + k * H).timestamp()), rate_at(k)]
        for k in range(first, last + 1)
        if k not in drop
    ]


def test_an_aligned_window_sums_24_whole_hours():
    series = o1.hourly_series(rows())
    assert o1.window_mm(series, T0 + 2 * H, T0) == pytest.approx(24.0)


def test_a_rate_covers_the_hour_ending_at_its_stamp_pro_rata():
    # only the stamp T0+5h rains (6 mm/h), i.e. the interval (T0+4h, T0+5h]
    series = o1.hourly_series(rows(lambda k: 6.0 if k == 5 else 0.0))
    start = T0 + 4 * H + timedelta(minutes=33)
    assert o1.window_mm(series, start, T0) == pytest.approx(6.0 * 27 / 60)
    end_inside = T0 + 4 * H + timedelta(minutes=27) - 24 * H
    assert o1.window_mm(series, end_inside, end_inside) == pytest.approx(6.0 * 27 / 60)


def test_the_part_before_the_evaluation_is_cut_off():
    series = o1.hourly_series(rows())
    assert o1.window_mm(series, T0, T0 + 6 * H) == pytest.approx(18.0)


def test_a_window_beyond_the_series_is_refused():
    series = o1.hourly_series(rows())
    with pytest.raises(ValueError, match="not covered"):
        o1.window_mm(series, T0 + 30 * H, T0)


def test_a_hole_inside_the_window_is_refused_and_one_outside_is_not():
    series = o1.hourly_series(rows(drop={10}))
    with pytest.raises(ValueError, match="hole"):
        o1.window_mm(series, T0, T0)
    assert o1.window_mm(series, T0 + 11 * H, T0) == pytest.approx(24.0)


def test_negative_is_dry_and_a_duplicate_stamp_keeps_the_maximum():
    r = rows(lambda k: -1.0)
    r.append([int((T0 + 3 * H).timestamp()), 2.0])
    series = o1.hourly_series(r)
    assert o1.window_mm(series, T0, T0) == pytest.approx(2.0)


def test_a_raw_log_line_is_parsed_from_the_python_repr():
    line = (
        "\x1b[37m2026-10-07 09:12:01.123 DEBUG (SyncWorker_3) "
        "[custom_components.irrigation_plus.weathermodules.PirateWeatherClient] "
        "PirateWeatherClient get_data called API https://api.pirateweather.net/forecast/***/52.5,13.4"
        "?units=si and received {'currently': {'time': 1, 'icon': None}, 'hourly': {'data': "
        "[{'time': 1791331200, 'precipIntensity': 0.25, 'precipType': 'rain'}, "
        "{'time': 1791334800, 'precipIntensity': 0}]}, 'flags': {'units': 'si', 'x': True}}\x1b[0m"
    )
    parsed = o1.parse_log_line(line)
    assert parsed["logged_at"] == "2026-10-07 09:12:01.123"
    assert parsed["method"] == "get_data"
    assert parsed["hourly"] == [[1791331200, 0.25], [1791334800, 0]]
```

- [x] **Step 2: RED**

```bash
cd /d/Entwicklung/HASI/issue61-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest o1_test.py -q -p _local_socket_unblock
```

Expected: FAIL / collection error `ModuleNotFoundError: No module named 'o1'`.

- [x] **Step 3: `o1.py` schreiben**

```python
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
```

- [x] **Step 4: GREEN**

Gleicher Befehl wie Step 2. Expected: `7 passed`.

- [x] **Step 5: Mutationsprobe** (zeigt, dass die Tests die Regel tragen)

Je Mutation `o1.py` kopieren, eine Zeile ändern, Tests laufen lassen, Original zurück:
(a) `min(t, hi) - max(t - step, lo)` → `min(t + step, hi) - max(t, lo)` (Stunde ab Stempel);
(b) `lo = max(start, evaluated_at)` → `lo = start`; (c) `if b - a > step` → `if False`.
Expected: jede Mutation ≥ 1 FAIL. Ergebnis ins Protokoll.

---

### Task 2: Imperial-Probetest (E3)

**Files:** Create: `issue61-work\imperial_probe_test.py`

- [x] **Step 1: Test schreiben** — er behauptet das RICHTIGE Verhalten (Gutschrift in der Einheit des Defizits).
  RED bestätigt den Verdacht, GREEN widerlegt ihn. Kein Produktionscode, egal wie es ausgeht.

```python
"""Probe for Eifel-Joe#61 / E3: does the live path add a mm credit to an inch deficit?

forecast_weighting_credit returns rain.mm (calculation.py:1039-1137, no unit
conversion); the live path adds it to live_deficit, which is in DISPLAY units
(live_estimate.py:1353, :1607-1614): run sizing irrigation.py:2501, panel
live_estimate.py:1742-1744 -> _live_run_duration (:1637-1663).
"""
import sys
from types import SimpleNamespace

sys.path.insert(0, r"D:/Entwicklung/HASI/issue61-work/src-6a40e083")

from custom_components.irrigation_plus import const  # noqa: E402
from custom_components.irrigation_plus.duration_math import zone_run_duration  # noqa: E402
from custom_components.irrigation_plus.irrigation import IrrigationRunnerMixin  # noqa: E402
from custom_components.irrigation_plus.live_estimate import LiveEstimateMixin  # noqa: E402

CREDIT_MM = 5.08  # what forecast_weighting_credit hands over: millimetres


def zone(bucket):
    return {
        const.ZONE_ID: 1,
        const.ZONE_THROUGHPUT: 1.0,
        const.ZONE_SIZE: 10.0,
        const.ZONE_MULTIPLIER: 1.0,
        const.ZONE_MAXIMUM_DURATION: None,  # no cap: a capped control would pass trivially
        const.ZONE_LEAD_TIME: 0,
        const.ZONE_BUCKET_THRESHOLD: 0,
        const.ZONE_BUCKET: bucket,
        const.ZONE_DURATION: 100,
    }


def runner():
    return SimpleNamespace(
        store=SimpleNamespace(config=SimpleNamespace(live_estimate_enabled=True)),
        _duration_for_deficit=lambda z, d, m: zone_run_duration(z, d, m),
    )


def test_control_metric_panel_and_run_agree_with_the_mm_credit():
    z = zone(-12.7)
    expected = zone_run_duration(z, -12.7 + CREDIT_MM, True)
    assert expected > 0
    assert LiveEstimateMixin._live_run_duration(z, -12.7, True, CREDIT_MM) == expected
    d = IrrigationRunnerMixin._zone_run_decision(
        runner(), z, {"1": {"live_deficit": -12.7}}, True, credit=CREDIT_MM
    )
    assert d is not None and d.duration == expected


def test_imperial_panel_credits_the_forecast_in_the_deficits_unit():
    z = zone(-0.5)
    expected = zone_run_duration(z, -0.5 + CREDIT_MM / const.INCH_TO_MM_FACTOR, False)
    assert expected > 0
    assert LiveEstimateMixin._live_run_duration(z, -0.5, False, CREDIT_MM) == expected


def test_imperial_run_credits_the_forecast_in_the_deficits_unit():
    z = zone(-0.5)
    expected = zone_run_duration(z, -0.5 + CREDIT_MM / const.INCH_TO_MM_FACTOR, False)
    d = IrrigationRunnerMixin._zone_run_decision(
        runner(), z, {"1": {"live_deficit": -0.5}}, False, credit=CREDIT_MM
    )
    assert d is not None, "zone dropped: the mm credit covered the inch deficit"
    assert d.duration == expected
```

- [x] **Step 2: Laufen lassen**

```bash
cd /d/Entwicklung/HASI/issue61-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest imperial_probe_test.py -q -p _local_socket_unblock
```

Expected: `test_control_metric_…` PASS (sonst ist der Prüfaufbau falsch → erst den reparieren, das ist kein Befund).
Verdacht bestätigt: beide `imperial`-Tests FAIL (Panel liefert 0, Lauf `None` „zone dropped“). Ein Importfehler aus der
lokalen HA-Version (< 2025.5) ist kein Ergebnis: dann den Import auf das Nötige reduzieren und Rücksprache.

- [x] **Step 3:** Ausgabe wörtlich ins Protokoll (Abschnitt „E3“), mit dem Satz „bestätigt“ oder „widerlegt“.

---

### Task 3: Ausgangslage sichern (HA-Test, nur lesend)

**Files:** Create: `livetest\protocol.md`, `livetest\config-before.json`

- [x] **Step 1: Uhr und Zeitzone**

`mcp__HA-Test__ha_eval_template`: `{{ now().isoformat() }} | {{ utcnow().isoformat() }} | {{ now().tzinfo }}`
Expected: Offset `+02:00` (Europe/Berlin, Sommerzeit). Offset ins Protokoll; alle Log-Stempel = Ortszeit.

- [x] **Step 2: Konfiguration, Zeitpläne, Zonen sichern** — Sandbox (`ha_manage_custom_tool`, justification
  „irrigation_plus WS read, read-only“):

```python
c = await ws_send({"type": "irrigation_plus/config"})
s = await ws_send({"type": "irrigation_plus/schedules"})
z = await ws_send({"type": "irrigation_plus/zones"})
{"config": c.get("result"), "schedules": s.get("result"),
 "zones": [{k: x.get(k) for k in ("id", "name", "state", "watering_mode", "linked_entity", "module", "mapping")}
           for x in z.get("result", [])]}
```

Ergebnis mit dem Write-Tool nach `livetest\config-before.json` (enthält keinen Schlüssel: der steht nur in den
Entry-Optionen, nicht in `irrigation_plus/config` — vor dem Schreiben prüfen, dass kein Feld `pw_api_key`/`api_key`
vorkommt). Expected u. a.: `forecast_weighting_enabled` false, `precipitation_threshold_mm` 2, `autocalcmode`
`fixed_time`, `live_estimate_enabled` false, Zeitpläne `schedule_ec886994` + `schedule_1fac4605` enabled.

- [x] **Step 3: effektive Log-Pegel** `mcp__HA-Test__ha_get_logs(source="logger", search="irrigation_plus")` → ins Protokoll.

- [x] **Step 4: `livetest\protocol.md` anlegen**

```markdown
# Live-Protokoll Eifel-Joe#61 (HA-Test)
Spec: docs/superpowers/specs/2026-10-07-forecast-weighting-live-verification-design.md
Offset HA-Test: <aus Step 1>
| Kriterium | Zeit (UTC) | Rohzitat / Wert | O1 | O2 | Urteil |
|---|---|---|---|---|---|
```

---

### Task 4: Probe 0 — Rohdokument lesbar?

- [ ] **Step 1: Logger** — HA-Test, `mcp__HA-Test__ha_call_service(domain="logger", service="set_level", data=
  {"custom_components.irrigation_plus.weathermodules.PirateWeatherClient": "debug"})`.

- [ ] **Step 2: Abruf auslösen** — Sandbox `await ws_send({"type": "irrigation_plus/weather_forecast"})` (ruft
  `get_forecast_data`; ist der Cache frisch, kommt die Zeile mit dem nächsten 10-Minuten-Update über `get_data`).

- [ ] **Step 3: Extraktion in der Sandbox** (hält das Dokument aus dem Chat-Kontext):

```python
import re
r = await call_tool("ha_get_logs", {"source": "error_log", "search": "PirateWeatherClient get_", "limit": 5})
txt = r.get("log") if isinstance(r, dict) and "log" in r else (r.get("data", {}).get("log") if isinstance(r, dict) else str(r))
out = []
for line in (txt or "").split("\n"):
    if "called API" not in line:
        continue
    clean = re.sub(r"\x1b\[[0-9;]*m", "", line)
    i = clean.find("'hourly':")
    j = clean.find("'daily':", i)
    block = clean[i:j] if i >= 0 and j > i else ""
    pairs = re.findall(r"'time': (\d+),[^{}]*?'precipIntensity': ([-0-9.eE]+)", block)
    out.append({"logged_at": clean[:23],
                "method": "get_data" if "get_data called" in clean else "get_forecast_data",
                "line_len": len(clean), "n": len(pairs),
                "hourly": [[int(a), float(b)] for a, b in pairs]})
[{k: v for k, v in o.items() if k != "hourly"} for o in out], (out[0]["hourly"][:3] if out else None)
```

Expected: mindestens eine Zeile, `n` = 168 (oder 48 ohne `extend=hourly`), `line_len` groß, keine Abschneidung (das
letzte Paar hat einen Stempel ≈ Abruf + 167 h). **Geht das nicht** (kein `re` in der Sandbox, Antwortform anders,
Zeile abgeschnitten): Ersatzweg `mcp__HA-Test__ha_get_logs(source="error_log", search="PirateWeatherClient get_",
limit=1)` direkt, Zeile per Write-Tool nach `livetest\raw-probe.log`, dann `python o1.py extract`. Ist auch die Zeile
abgeschnitten → **Stopp, Rücksprache** (Spec §6 Probe 0).

- [ ] **Step 4: Ablage-Form festlegen** — die extrahierte Reihe als `livetest\doc-<logged_at HHMMSS>.series.json`
  (`{"logged_at", "method", "hourly"}`) per Write-Tool. Prüfen:
  `grep -cE "forecast/[A-Za-z0-9]{16,}|latitude|longitude" livetest/*.series.json` → `0` je Datei.
  `python o1.py window livetest/doc-….series.json <logged_at+1h als ISO mit Offset> <dto>` → eine Zahl, kein Fehler.
  Diese Extraktion (Sandbox-Code Step 3, als `save_as="hasi61_doc"` gespeichert) ist ab jetzt der Weg zu jedem Dokument.

---

### Task 5: Aufbau (HA-Test, schreibend)

- [x] **Step 1: Helfer** — HA-Test. Schema von `mcp__HA-Test__ha_config_set_helper` per ToolSearch laden;
  `ha_get_skill_guide(skill="home-assistant-best-practices", file="SKILL.md")` lesen, den dort genannten `BestPracticeKey`
  mitgeben, `MandatoryBPS=false` (Memory `hasi-livetest-capability-boundary`). Anlegen: `input_boolean` „hasi61_a“ und
  „hasi61_b“. Expected: `input_boolean.hasi61_a` / `_b` existieren, Zustand `off`.

- [x] **Step 2: Zonen** — HA-Test, Sandbox:

```python
a = await api_post("/irrigation_plus/zones", {"name": "HASI61 A", "size": 1, "throughput": 3, "state": "automatic",
    "module": 0, "mapping": 0, "linked_entity": "input_boolean.hasi61_a", "bucket_threshold": 0,
    "maximum_duration": 3600, "lead_time": 0, "multiplier": 1, "flow_sensor": None, "distributor_id": None})
b = await api_post("/irrigation_plus/zones", {"name": "HASI61 B", "size": 1, "throughput": 3, "state": "automatic",
    "module": 0, "mapping": 0, "linked_entity": "input_boolean.hasi61_b", "bucket_threshold": 0,
    "maximum_duration": 3600, "lead_time": 0, "multiplier": 1, "flow_sensor": None, "distributor_id": None})
z = await ws_send({"type": "irrigation_plus/zones"})
[{k: x.get(k) for k in ("id", "name", "state", "watering_mode", "linked_entity", "module", "mapping", "flow_sensor",
  "distributor_id", "size", "throughput")} for x in z.get("result", []) if str(x.get("name", "")).startswith("HASI61")]
```

Scheitert das Skript nach dem POST: erst lesen, nie blind wiederholen (Memory). Expected: zwei Zonen, `watering_mode`
`classic` (sonst `api_post(… {"id": N, "watering_mode": "classic"})`), `flow_sensor`/`distributor_id` `None`.
IDs als **A** und **B** ins Protokoll. Rate = 3 × 60 / 1 = **180 mm/h → 1 mm = 20 s**.
Sensor-Entitäten finden: `mcp__HA-Test__ha_search(query="hasi61", domain_filter="sensor")` → die Zonen-Sensoren mit
Attribut `id` = A bzw. B (Namen ins Protokoll als `SENSOR_A`, `SENSOR_B`).

- [x] **Step 3: Konfiguration** — HA-Test, Sandbox:

```python
r = await api_post("/irrigation_plus/config", {"forecast_weighting_enabled": True, "precipitation_threshold_mm": 100})
c = (await ws_send({"type": "irrigation_plus/config"})).get("result", {})
r, {k: c.get(k) for k in ("forecast_weighting_enabled", "precipitation_threshold_mm", "skip_irrigation_on_precipitation",
    "autocalcmode", "live_estimate_enabled", "precipitation_forecast_days")}
```

Expected: `True`, `100.0`, `True`, `fixed_time`, `False`, `1`.

- [x] **Step 4: Bestehende Zeitpläne aus** — HA-Test, Sandbox:

```python
for sid in ("schedule_ec886994", "schedule_1fac4605"):
    print(await ws_send({"type": "irrigation_plus/schedule_save", "schedule": {"id": sid, "enabled": False}}))
s = (await ws_send({"type": "irrigation_plus/schedules"})).get("result")
s
```

Expected: beide `enabled: false`; Antworten `success: true`.

- [x] **Step 5: P61 anlegen (noch ohne Zeitbezug zum Test)** — Startzeit vorläufig 04:00, Zone A:

```python
r = await ws_send({"type": "irrigation_plus/schedule_save", "schedule": {"name": "HASI61", "enabled": True,
    "action": "irrigate", "zones": "<A>", "recurrence": "daily", "start_mode": "time", "start_time": "04:00",
    "finish_mode": "none", "anchor": "start"}})
s = (await ws_send({"type": "irrigation_plus/schedules"})).get("result")
r, [x for x in (s if isinstance(s, list) else s.get("schedules", [])) if x.get("name") == "HASI61"]
```

Expected: `success: true`, eine Zeile mit `id` → als **P61** ins Protokoll.

- [x] **Step 6: Log-Pegel** — HA-Test, `logger.set_level` mit
  `{"custom_components.irrigation_plus.calculation": "debug", "custom_components.irrigation_plus.irrigation": "debug",
  "custom_components.irrigation_plus.live_estimate": "debug", "custom_components.irrigation_plus.skip_conditions": "debug",
  "custom_components.irrigation_plus": "info", "custom_components.irrigation_plus.scheduler": "info",
  "custom_components.irrigation_plus.auto_calc": "info"}`. Kontrolle `ha_get_logs(source="logger", search="irrigation_plus")`.

---

### Task 6: Phase 1a — B1, B2a, B2b

**Vorbedingung:** seit Anlage von A/B mindestens ein Wetter-Update (sonst rechnen sie nicht, `calculation.py:603-610`):
Sandbox `ws_send({"type": "irrigation_plus/weather_records", "mapping_id": "0", "limit": 3})` → jüngster Stempel nach
der Zonen-Anlage.

- [x] **Step 1: Dokument + Scan** — `run_saved="hasi61_doc"` → neueste Reihe als `doc-….series.json`. E = jetzt + 3 min.

```bash
cd /d/Entwicklung/HASI/issue61-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe o1.py scan livetest/doc-HHMMSS.series.json <E> <E+1h> <E+20h> 15
```

T1 = früheste Zeile mit O1(T1) > 0, |O1(T1) − O1(E)| ≥ 0,5 **und** |O1(T1) − O1(T1+24h)| ≥ 0,5. Keine → Spec E1
Ausweichweg, Rücksprache. T1 als Ortszeit `HH:MM` (P61 nimmt die nächste Gelegenheit von `HH:MM` nach jetzt).

- [x] **Step 2: P61 auf T1, Eimer setzen** — HA-Test. Sandbox
  `ws_send({"type": "irrigation_plus/schedule_save", "schedule": {"id": "<P61>", "start_time": "<HH:MM>"}})`;
  D = −(⌈max(O1(T1), O1(E))⌉ + 8) mm. `ha_call_service(domain="irrigation_plus", service="set_bucket",
  entity_id=["<SENSOR_A>", "<SENSOR_B>"], data={"new_bucket_value": D})`.
  Kontrolle Outlook: `upcoming_runs` nennt nur P61 mit `next_run_utc` = T1.

- [x] **Step 3: O2 vorher lesen, rechnen, O2 nachher lesen** — HA-Test:
  Sandbox `ws_send({"type": "irrigation_plus/irrigation_outlook"})` → `skip_preview.checks[precipitation].observed`;
  dann `ha_call_service(domain="irrigation_plus", service="calculate_zone", entity_id=["<SENSOR_A>", "<SENSOR_B>"])`;
  Rechenzeitpunkt = `last_calculated` von A/B (WS `zones`); dann Outlook erneut.

- [x] **Step 4: Belege holen**
  - `ha_get_logs(source="error_log", search="[calculate-module]", limit=20)` → Zeilen „forecast weighting X mm rain →
    effective bucket Y (true Z)“ für A und B, „no scheduled run resolves for zone <B>“ (nur B!).
  - `ha_get_logs(source="system")` → kein `irrigation_plus`-Fehler, kein „[async_update_zone_config] … no sensor data“
    (das wäre der Zonenzweig, der auch unter `before_run` läuft → Stopp).
  - WS `zones` für A, B: `bucket`, `duration`, `irrigation_target_bucket`, `explanation`, `last_calculated`.
  - `run_saved="hasi61_doc"`: Dokument mit `logged_at` ≤ Rechenzeitpunkt (das jüngste davor) → `doc-….series.json`.

- [x] **Step 5: Prüfen** (`o1.py window`, E = Rechenzeitpunkt mit Offset)

| Kriterium | Bestanden, wenn |
|---|---|
| B1 | Rohdokument vor der Rechnung im Log; Gutschrift-Zeilen vorhanden; kein Fehler |
| B2a | X(A) = O1(T1, E) ±0,01 **und** = O2 ±0,01 (O2 aus dem Outlook, dessen Dokument dasselbe ist — sonst O2 gegen O1 des neueren Dokuments); \|O1(T1) − O1(E)\| ≥ 0,5 |
| B2b | Fallback-Zeile für B; X(B) = O1(E, E) ±0,01 |
| beide | `explanation` enthält `(Z → Y)`; `duration` = \|Y\| / 180 × 3600 (±1 s); `irrigation_target_bucket` = Z − Y (±0,01) |

---

### Task 7: Phase 1b — B3 (Lauf mit Regen im Fenster)

- [x] **Step 1: neue Wetterzeile abwarten** — `weather_records` jüngster Stempel > `last_consumed_at` von A.
- [x] **Step 2: T3** = nächste volle Minute ≥ jetzt + 6 min (Ortszeit `HH:MM`). HA-Test: P61 `start_time` = T3;
  `set_bucket` A = D (wie Task 6); `calculate_zone` A. Dokument holen; X(A) = O1(T3, Rechenzeit) ±0,01 (Kontrolle);
  gespeicherte `duration` = d₃ und `irrigation_target_bucket` = g₃ notieren.
- [x] **Step 3: Sicherheits-Rücklesen** (Ausführungsregeln) — dann warten bis T3 + d₃ + 60 s (Monitor).
- [x] **Step 4: Belege** — Logs „Executing recurring schedule: HASI61“, „Metered (timed) irrigation: zone <A> for d s“;
  **keine** Zeile „Committing the pre-run calculation“ (unter `fixed_time` darf nicht gerechnet werden);
  `ha_get_history(entity_ids="input_boolean.hasi61_a", start_time="1h")` an/aus; WS `zones` A: `run_log[0]`, `bucket`.
- [x] **Step 5: Prüfen** — B3 bestanden, wenn `run_log[0].planned_s` = d₃ (±1 s), d₃ < \|Z₃\| / 180 × 3600,
  `result` = `completed`, und `bucket` nach dem Lauf = g₃ ±0,05.

---

### Task 8: Phase 2 — B4 (`before_run` aus dem Dispatch)

- [x] **Step 1: Modus** — HA-Test, Sandbox `api_post("/irrigation_plus/config", {"autocalcmode": "before_run"})`,
  zurücklesen. Log (INFO `custom_components.irrigation_plus`): „Automatic calculation runs before each irrigation run;
  no fixed-time calculation scheduled“.
- [x] **Step 2: neue Wetterzeile abwarten** (wie Task 7 Step 1); `set_bucket` A = D.
- [x] **Step 3: T4 wählen** — Dokument holen; `o1.py scan … <jetzt> <jetzt+6min> <jetzt+60min> 1`; T4 = früheste
  Minute mit O1(T4) > 0 und \|O1(T4) − O1(T4+24h)\| ≥ 0,5. P61 `start_time` = T4. Sicherheits-Rücklesen.
- [x] **Step 4: warten** bis T4 + 120 s, dann Belege:
  - Logkette in derselben Sekunde: „Executing recurring schedule: HASI61“ → „Committing the pre-run calculation for
    zones: …“ → „Calculating zone <A>“ → „[calculate-module]: forecast weighting X₄ mm …“.
  - WS `zones` A: `last_calculated` (= T4 auf die Sekunde), `duration` d₄, `irrigation_target_bucket` g₄.
  - Outlook `last_skip_evaluation`: `timestamp` ≈ T4, `checks[precipitation].observed` = O2.
  - Dokument mit `logged_at` ≤ T4 (eine Abruf-Zeile in derselben Sekunde VOR der Gutschrift-Zeile zählt).
- [x] **Step 5: warten** bis T4 + d₄ + 60 s; `run_log[0]`, `bucket`.
- [x] **Step 6: Prüfen** — B4 bestanden, wenn Logkette vollständig; `last_calculated` = T4 (±2 s); X₄ = O1(T4, T4) ±0,01
  = O2 ±0,01; \|O1(T4) − O1(T4+24h)\| ≥ 0,5; `run_log[0].planned_s` = d₄ (±1 s); `bucket` = g₄ ±0,05.

---

### Task 9: Phase 3 — B5 (Live-Estimate)

- [x] **Step 1: Modus** — HA-Test, Sandbox `api_post("/irrigation_plus/config", {"autocalcmode": "fixed_time",
  "live_estimate_enabled": True})`, zurücklesen.
- [x] **Step 2: Probe Schätzung** — `set_bucket` A = D; Outlook `zone_estimates["<A>"]`: `available` true,
  `live_deficit` < 0 und \|live_deficit\| > erwartete Gutschrift. Fehlt die Schätzung oder spiegelt `live_deficit` den
  gesetzten Eimer noch nicht (≈ D): ein Wetter-Update abwarten, einmal neu lesen; dann noch immer keine → **Stopp, Rücksprache** (`unavailable_reason` ins Protokoll).
- [x] **Step 3: T5** = nächste volle Minute ≥ jetzt + 6 min; P61 `start_time` = T5; Sicherheits-Rücklesen.
- [x] **Step 4: kurz vor dem Dispatch** (Monitor bis T5 − 90 s) Outlook lesen: `zone_estimates["<A>"]` →
  `live_deficit` D₅, `forecast_credit` C₅, `live_duration` L₅; Dokument holen.
- [x] **Step 5: warten** bis T5 + L₅ + 60 s; Belege: INFO „Live-estimate watering: zone <A> …s → Y s (live deficit D′)“,
  WS `zones` A `run_log[0]`.
- [x] **Step 6: Prüfen** — B5 bestanden, wenn C₅ = O1(T5, Lesezeit) ±0,01; L₅ < round(\|D₅\| / 180 × 3600);
  Y = `run_log[0].planned_s`; Y = L₅ (ist D′ ≠ D₅: Y = round(\|D′ + C₅\| / 180 × 3600) ±1 s). Optional: User sieht die
  Zonenkarte im Panel vor T5.

---

### Task 10: Rückbau und Vergleich (HA-Test, schreibend)

- [ ] **Step 1:** Sandbox: `ws_send({"type": "irrigation_plus/schedule_delete", "schedule_id": "<P61>"})`; beide alten
  Zeitpläne `enabled: True`; `api_post("/irrigation_plus/config", {"forecast_weighting_enabled": False,
  "precipitation_threshold_mm": 2, "autocalcmode": "fixed_time", "live_estimate_enabled": False})`;
  `api_post("/irrigation_plus/zones", {"id": A, "remove": True})`, ebenso B.
- [ ] **Step 2:** Helfer `input_boolean.hasi61_a`/`_b` löschen (Schema per ToolSearch: `ha_remove_helpers_integrations`).
- [ ] **Step 3:** `logger.set_level` für alle in Task 4/5 gesetzten Logger auf `warning` (= effektiver Pegel vorher laut
  Task 3 Step 3; ein HA-Neustart setzt ohnehin zurück).
- [ ] **Step 4:** Sicherung wie Task 3 Step 2 → `livetest\config-after.json`; Vergleich:

```bash
cd /d/Entwicklung/HASI/issue61-work/livetest && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -c "import json;a=json.load(open('config-before.json'));b=json.load(open('config-after.json'));print({k:(a['config'].get(k),b['config'].get(k)) for k in set(a['config'])|set(b['config']) if a['config'].get(k)!=b['config'].get(k)});print(a['schedules']==b['schedules']);print(a['zones']==b['zones'])"
```

Expected: leeres Dict bis auf laufzeitbedingte Felder (`fired_occurrences`, `active_valve_runs`) — jede andere Abweichung
wird zurückgesetzt und begründet ins Protokoll; `True`, `True`.

---

### Task 11: Abschluss (Texte nur mit Freigabe)

- [ ] **Step 1:** Protokoll vollständig; Ende-zu-Ende-Kriterium der Spec §9 Punkt für Punkt abhaken, mit Verweis auf die
  Protokollzeile.
- [ ] **Step 2: Upstream-Runde** seit der letzten (Memory `upstream-sweep-first`), vor jedem Außen-Schritt erneut.
- [ ] **Step 3: Texte im Chat zur Freigabe** (Form Regel P2: Englisch oben, Deutsch darunter):
  Ergebnis-Kommentar auf Eifel-Joe#61 (je Beobachtung ein Satz + Zahl; nicht beobachtet: `days` > 1,
  `hourlycalculation`, Verteiler-Mitglieder, imperial live); bei bestätigtem E3 ein neues Fork-Issue (Befund, Fundstellen,
  Probetest-Ausgabe; Label `typ:fehler` + Schwere nach User) im selben Zug; `Eifel-Joe#42`-Eintrag. CR per
  Python-Bytezählung = 0, nach `gh` zurücklesen und vergleichen.
- [ ] **Step 4:** nach Freigabe: Kommentar, #61 schließen, Issue/Label, `#42`.
- [ ] **Step 5: Archiv** (Regel P1, nach Push-Freigabe): Spec, Plan, `o1.py`, `o1_test.py`, `imperial_probe_test.py`,
  `livetest\protocol.md`, `*.series.json`, `config-*.json` nach `docs/superpowers/probes/2026-10-07-forecast-weighting-live/`
  auf `archive/design-history`; **keine** `raw-*.log` (Koordinaten). Dazu die aktuelle `docs/SESSION-STAND.md`
  (die Archivkopie kennt das Aufräumen vom 06.10. noch nicht). Commit-Message ohne `JustChr#N` („upstream PR N“).

**Gelegentlich, keine Schließbedingung (Spec §6 (ii)):** zeigt die Vorhersage solange #61 offen ist ein trockenes
24-h-Fenster, einen Lauf mit Gutschrift 0 nach Task 7 mitnehmen.

---

## Revision 2 (2026-10-11) — Ersatzort, Log-Stücke, Intervall

**Spec:** §10 (E4–E6), vom User freigegeben 2026-10-11. Diese Revision **ersetzt Task 4 und Task 10 ganz** und die
genannten Steps in Tasks 5–9; alles nicht Genannte gilt unverändert. Reihenfolge: Task 3 (Rest) → **3a** → **4R** →
**5R** → 6–9 (mit Ergänzungen R) → **10R** → 11. Ausführung wie bisher inline in der Hauptsitzung.

### Global Constraints (Rev. 2, Werte aus Spec §10)

- Ortskriterium: Startpunkte t in [jetzt, jetzt + 8 h] in 15-min-Schritten: R(t, t + 24 h) ≥ 2 mm und
  |R(t, t + 24 h) − R(t + 24 h, t + 48 h)| ≥ 0,5 mm; T1 in [jetzt + 1 h, jetzt + 20 h] mit |R(T1) − R(jetzt)| ≥ 0,5 mm.
- Höchstens **ein** Ortswechsel (Rang 2); trägt auch der nicht → Stopp, Rücksprache.
- Kandidaten nur in derselben UTC-Verschiebung wie HA-Test.
- Dokument vollständig = 168 Stundenwerte in 3600-s-Schritten, `'daily':` nach dem Stundenblock,
  `precipIntensity`-Zähler 177.
- Maßgeblich: letzter echter Abruf mit Log-Stempel vor der Gutschrift-Zeile; alle Dokumente seines Schubs mit gleicher
  Stundenreihe, sonst Stopp.
- Intervall während der Phasen `"10"`, nach dem Rückbau `"60"`; immer alle vier Felder `autoupdateenabled`,
  `autoupdateschedule`, `autoupdateinterval`, `autoupdatedelay` zusammen senden.
- D = −(⌈max(O1(T1), O1(E))⌉ + 15) mm; fällt eine Zone weg (wahrer Eimer + Gutschrift ≥ 0) → Stopp, kein Nachsetzen.
- Eine 429 während der Phasen = Umgebungsabbruch → Stopp, Rücksprache.
- HA-Tests eigene Koordinaten (`ha_latitude`/`ha_longitude`/`ha_elevation`) verlassen die Sandbox nie; der Testort
  steht im Protokoll mit Namen und Koordinaten auf 2 Nachkommastellen.

### Review Focus (Rev. 2)

1. Open-Meteo antwortet anders als angenommen (Endpunkt `/v1/gfs`, Unix-Stempel, Wert = Summe der Stunde bis zum
   Stempel) → Task 3a Step 5 prüft Zeilenzahl und Reichweite, bevor eine Rangliste gilt.
2. Das Neuladen nach `coordinates_save` hängt oder scheitert → Task 4R Step 3 wartet auf `state: loaded` und ein
   Systemlog ohne neuen `irrigation_plus`-Fehler.
3. Das Log-Fenster reicht nicht bis zum Abruf zurück (viele DEBUG-Zeilen) → jede Extraktion meldet `window_first`;
   liegt es nach `CUTOFF`, mit `OFFSET = 2000` erneut lesen und zusammenführen.
4. Die Dokumente eines Schubs unterscheiden sich → Identitätsprüfung in jeder Extraktion (Task 4R Step 4, Tasks 6R–9R).
5. 429 mitten in einer Phase → Systemlog-Kontrolle in jedem Beleg-Step (Tasks 6R–9R).

### Dateien (Rev. 2)

| Datei | Zweck |
|---|---|
| `issue61-work\scout.py` | Ortssuche + Kriterium (nutzt `o1.hourly_series`, `o1.window_mm`, `o1.load`) |
| `issue61-work\scout_test.py` | Tests für `scout.py` |
| `issue61-work\livetest\scout-HHMM.txt` | Rangliste eines Laufs |
| `issue61-work\livetest\coords-before.json`, `coords-after.json` | nur die `manual_*`-Felder |

### Sandbox-Baustein X — Rohdokumente aus dem Log (E5; von Task 4R, 6R–9R benutzt)

Nicht als `save_as` speichern (`CUTOFF` ändert sich je Einsatz). `CUTOFF` = HA-Ortszeit als `"YYYY-MM-DD HH:MM:SS"`,
`OFFSET` = 0 (oder 2000 beim Nachblättern). justification: „irrigation_plus raw-document extraction, read-only“.

```python
import re
CUTOFF = "2026-10-11 00:00:00"
OFFSET = 0
TS = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
r = await call_tool("ha_get_logs", {"source": "error_log", "limit": 2000, "order": "newest", "offset": OFFSET})
txt = r.get("log") if isinstance(r, dict) else str(r)
lines = [ANSI.sub("", l) for l in (txt or "").split("\n")]
lines = list(reversed(lines))
stamped = [l[:23] for l in lines if TS.match(l)]
docs = []
keys = []
series = []
n = 0
while n < len(lines):
    head = lines[n]
    m = n + 1
    if TS.match(head) and head[:23] >= CUTOFF and "PirateWeatherClient get_" in head and " called API " in head:
        parts = [head]
        while m < len(lines) and not TS.match(lines[m]):
            parts.append(lines[m])
            m += 1
        doc = "".join(parts)
        hi = doc.find("'hourly':")
        di = doc.find("'daily':", hi + 1) if hi >= 0 else -1
        block = doc[hi:di] if di > hi else ""
        pairs = re.findall(r"'time': (\d+),[^{}]*?'precipIntensity': ([-0-9.eE]+)", block)
        stamps = [int(a) for a, _ in pairs]
        key = ";".join([a + ":" + b for a, b in pairs])
        if key not in keys:
            keys.append(key)
            rows = [[int(a), float(b)] for a, b in pairs]
            series.append({"hourly": rows, "checksum": [len(rows), sum([x for x, _ in rows]),
                                                        round(sum([y for _, y in rows]), 4)]})
        docs.append({
            "logged_at": head[:23],
            "method": "get_data" if "get_data called" in head else "get_forecast_data",
            "chunks": len(parts),
            "n_hourly": len(pairs),
            "steps_ok": len(stamps) == 168 and all([stamps[i + 1] - stamps[i] == 3600 for i in range(len(stamps) - 1)]),
            "has_daily": di > hi >= 0,
            "n_precip": doc.count("'precipIntensity'"),
            "masked": "***" in doc,
            "key_pattern": bool(re.search(r"forecast/[A-Za-z0-9]{16,}", doc)),
            "series": keys.index(key),
        })
    n = m
{"window_first": stamped[0] if stamped else None, "window_last": stamped[-1] if stamped else None,
 "docs": docs, "series": series}
```

**Auswerten (gilt für jeden Einsatz):**
- `window_first` ≤ `CUTOFF`, sonst mit `OFFSET = 2000` nachlesen (Review Focus 3).
- Jedes Dokument: `n_hourly` 168, `steps_ok`, `has_daily`, `n_precip` 177, `masked` true, `key_pattern` false.
  Sonst → Stopp, Rücksprache (Probe 0 gescheitert).
- **Maßgebliches Dokument:** das letzte mit `logged_at` vor dem Stempel der Gutschrift-Zeile (bei Task 4R: das
  letzte überhaupt). **Schub** = alle Dokumente mit `logged_at` höchstens 5 s davor oder danach; alle müssen dieselbe
  `series`-Nummer tragen, sonst → Stopp, Rücksprache.
- Ablage: `{"logged_at": …, "method": …, "hourly": series[i].hourly}` per Write-Tool nach
  `livetest\doc-HHMMSS.series.json` (HHMMSS aus `logged_at`). Danach Prüfsumme lokal gegen `series[i].checksum`:

```bash
cd /d/Entwicklung/HASI/issue61-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -c "import json,sys;h=json.load(open(sys.argv[1],encoding='utf-8'))['hourly'];print([len(h),sum(a for a,_ in h),round(sum(b for _,b in h),4)])" livetest/doc-HHMMSS.series.json
grep -cE "forecast/[A-Za-z0-9]{16,}|latitude|longitude" livetest/doc-HHMMSS.series.json
```

Expected: dieselbe Liste wie `checksum`; `0`.

---

### Task 3 (Rest)

Steps 1–4 erledigt 2026-10-11 (Protokoll: Offset +02:00, `config-before.json` 07:14 UTC, Pegel `irrigation_plus`
WARNING, `protocol.md` angelegt).

- [x] **Step 5: Koordinaten-Ausgangslage** — HA-Test, Sandbox (nur lesend; justification „irrigation_plus WS read,
  read-only“):

```python
c = await ws_send({"type": "irrigation_plus/coordinates"})
{k: v for k, v in (c.get("result") or {}).items() if k.startswith("manual_")}
```

Ergebnis per Write-Tool nach `livetest\coords-before.json`. Expected: `{"manual_coordinates_enabled": false,
"manual_latitude": null, "manual_longitude": null, "manual_elevation": null}`.
`grep -c "ha_" livetest/coords-before.json` → `0`.

---

### Task 3a: Ortssuche `scout.py` (TDD, lokal)

**Files:** Create: `issue61-work\scout_test.py`, `issue61-work\scout.py`

**Interfaces:**
- Consumes: `o1.hourly_series(rows) -> list[tuple[datetime, float]]`, `o1.window_mm(series, start, evaluated_at,
  hours=24) -> float` (ValueError, wenn nicht gedeckt), `o1.load(path) -> dict` (Task 1).
- Produces: `scout.assess(series, now) -> {"ok": bool, "reserve": float, "worst_t": datetime, "t1": datetime,
  "r_now": float}`; CLI `python scout.py rank` und `python scout.py check <series.json> <now-iso>` (Task 4R).

- [x] **Step 1: Tests schreiben**

```python
"""Tests for scout.py, the stand-in site search of the Eifel-Joe#61 live verification (spec §10.2)."""
import json
from datetime import datetime, timedelta, timezone

import pytest

import scout

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
H = timedelta(hours=1)


def rows(rate_at, first=-2, last=72):
    """Hourly rows [unix, mm] for stamps NOW + k h; each value covers the hour ending at its stamp."""
    return [[int((NOW + k * H).timestamp()), rate_at(k)] for k in range(first, last + 1)]


def series(rate_at):
    return scout.o1.hourly_series(rows(rate_at))


def test_a_dry_site_fails():
    assert scout.assess(series(lambda k: 0.0), NOW)["ok"] is False


def test_rain_today_and_a_dry_tomorrow_passes():
    # 1 mm/h over (NOW, NOW+12h]: the weakest start is NOW+8h with 4 mm left -> reserve 4 - 2 = 2
    result = scout.assess(series(lambda k: 1.0 if 1 <= k <= 12 else 0.0), NOW)
    assert result["ok"] is True
    assert result["reserve"] == pytest.approx(2.0)


def test_more_rain_tomorrow_counts_as_a_contrast_too():
    # 0.25 mm/h today, 1 mm/h tomorrow: day 1 holds 6..12 mm, day 2 holds 24 mm -> reserve 6 - 2 = 4
    result = scout.assess(series(lambda k: 0.25 if 1 <= k <= 24 else (1.0 if 25 <= k <= 56 else 0.0)), NOW)
    assert result["ok"] is True
    assert result["reserve"] == pytest.approx(4.0)


def test_steady_rain_fails_on_the_plus_one_day_gap():
    result = scout.assess(series(lambda k: 1.0), NOW)
    assert result["ok"] is False
    assert result["reserve"] == pytest.approx(-0.5)


def test_without_a_t1_contrast_the_site_fails():
    # 4 mm in (NOW+20h, NOW+24h]: every start up to +8 h carries, but each T1 in [+1 h, +20 h] sees the same 4 mm
    result = scout.assess(series(lambda k: 1.0 if 21 <= k <= 24 else 0.0), NOW)
    assert result["ok"] is False
    assert result["reserve"] == pytest.approx(-0.5)


def test_check_reads_a_series_file(tmp_path, capsys):
    path = tmp_path / "doc.series.json"
    path.write_text(json.dumps({"logged_at": "x", "method": "get_data",
                                "hourly": rows(lambda k: 1.0 if 1 <= k <= 12 else 0.0)}), encoding="utf-8")
    assert scout.main(["scout.py", "check", str(path), NOW.isoformat()]) == 0
    out = capsys.readouterr().out
    assert "ok=True" in out
    assert "reserve=2.00" in out
```

- [x] **Step 2: RED**

```bash
cd /d/Entwicklung/HASI/issue61-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest scout_test.py -q -p _local_socket_unblock
```

Expected: Collection-Fehler `ModuleNotFoundError: No module named 'scout'`.

- [x] **Step 3: `scout.py` schreiben**

```python
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
```

- [x] **Step 4: GREEN** — Befehl wie Step 2. Expected: `6 passed`.

- [x] **Step 5: Mutationsprobe** (wie Task 1 Step 5, je eigener Ordner mit Kopien von `scout.py`, `scout_test.py`,
  `o1.py`, `_local_socket_unblock.py`): (a) `abs(day1 - day2) - min_gap` → `(day1 - day2) - min_gap`;
  (b) `min(day1 - min_rain, abs(day1 - day2) - min_gap)` → `abs(day1 - day2) - min_gap`;
  (c) `reserve = min(reserve, t1_gap - min_gap)` → `reserve = reserve`. Expected: jede Mutation ≥ 1 FAIL
  ((a) `test_more_rain_tomorrow…`, (b) `test_rain_today…`, (c) `test_without_a_t1…`). Ergebnis ins Protokoll.

- [x] **Step 6: Rangliste (live, Open-Meteo)**

```bash
cd /d/Entwicklung/HASI/issue61-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe scout.py rank | tee livetest/scout-$(date -u +%H%M).txt
```

Expected: erste Zeile `rows=96`, `first` = 00:00 UTC des Tages, `last` = `first` + 95 h (Review Focus 1); danach 27
Zeilen absteigend nach `reserve`. Keine Zeile mit `ok=True` → Stopp, Rücksprache (Ausweichweg trägt nicht). Rang 1 und
Rang 2 (die ersten beiden mit `ok=True`) mit Name, Breite, Länge, `elev` ins Protokoll.

---

### Task 4R: Ersatzort setzen + Probe 0 (HA-Test, schreibend) — ersetzt Task 4

- [x] **Step 1: Logger zuerst** — HA-Test, `mcp__HA-Test__ha_call_service(domain="logger", service="set_level",
  data={"custom_components.irrigation_plus.weathermodules.PirateWeatherClient": "debug"})`. Grund: bei Intervall 60
  cacht der Client 3599 s (`__init__.py:1356-1358`); nur der Schub des Neuladens liefert sofort ein Dokument, und der
  muss schon unter DEBUG laufen.

- [x] **Step 2: Koordinaten setzen** — `ha_eval_template` `{{ now().strftime('%Y-%m-%d %H:%M:%S') }}` → `CUTOFF`.
  HA-Test, Sandbox (justification „irrigation_plus coordinates WS, user-approved test step“), Werte von Rang 1
  (Breite/Länge auf 2 Stellen, Höhe gerundet):

```python
r = await ws_send({"type": "irrigation_plus/coordinates_save", "manual_coordinates_enabled": True,
                   "manual_latitude": 0.0, "manual_longitude": 0.0, "manual_elevation": 0})
c = await ws_send({"type": "irrigation_plus/coordinates"})
r, {k: v for k, v in (c.get("result") or {}).items() if k.startswith("manual_")}
```

(`0.0`/`0.0`/`0` durch die Werte von Rang 1 ersetzen.) Expected: `success: true`; `manual_*` = gesetzte Werte.

- [x] **Step 3: Neuladen fertig?** — HA-Test, Sandbox (nur lesend):

```python
e = await ws_send({"type": "config_entries/get", "domain": "irrigation_plus"})
[{k: x.get(k) for k in ("entry_id", "state", "reason")} for x in (e.get("result") or [])]
```

Expected: `state` `loaded`. `mcp__HA-Test__ha_get_logs(source="system", search="irrigation_plus")`: kein Eintrag mit
`timestamp` nach `CUTOFF` außer bekannten Warnungen (Liste ins Protokoll). Sonst → Stopp, Rücksprache.

- [x] **Step 4: Probe 0** — Baustein X mit `CUTOFF` aus Step 2. Auswerten wie dort; maßgeblich = das letzte Dokument.
  Expected: ≥ 1 Dokument nach `CUTOFF`, alle vollständig, eine `series`-Nummer im letzten Schub. Ablage + Prüfsumme +
  grep wie Baustein X.

- [x] **Step 5: Bestätigen** — `ha_eval_template` `{{ now().isoformat() }}` → NOW.

```bash
cd /d/Entwicklung/HASI/issue61-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe scout.py check livetest/doc-HHMMSS.series.json <NOW>
```

Expected: `ok=True`. Dann Step 7.

- [ ] ~~**Step 6: Nur falls Step 5 `ok=False`: einmal Rang 2**~~ (entfiel 2026-10-11: Step 5 `ok=True`) — Step 2 mit den Werten von Rang 2 (neues `CUTOFF`),
  dann Step 3, Step 4, Step 5. Wieder `ok=False` → Stopp, Rücksprache (Spec §10.2).

- [x] **Step 7: Protokoll** — Testort (Name, Breite/Länge 2 Stellen, Höhe), Reserve laut Open-Meteo und laut Pirate,
  `CUTOFF`, Dokument-Datei.

---

### Task 5R — ersetzt Task 5 Step 3 und Step 6 (Steps 1, 2, 4, 5 unverändert)

Reihenfolge: Step 1 (Helfer) → **Step 6R** → Step 2 (Zonen, **nach** Task 4R) → **Step 3R** → Step 4 → Step 5.

- [x] **Step 6R: Log-Pegel** (vorgezogen) — HA-Test, `logger.set_level` mit
  `{"custom_components.irrigation_plus.calculation": "debug", "custom_components.irrigation_plus.irrigation": "debug",
  "custom_components.irrigation_plus.live_estimate": "debug", "custom_components.irrigation_plus.skip_conditions": "debug",
  "custom_components.irrigation_plus": "info", "custom_components.irrigation_plus.scheduler": "info",
  "custom_components.irrigation_plus.auto_calc": "info"}` (PirateWeatherClient bleibt `debug` aus Task 4R). Kontrolle
  `ha_get_logs(source="logger", search="irrigation_plus")`.

- [x] **Step 3R: Konfiguration** — HA-Test, Sandbox:

```python
r = await api_post("/irrigation_plus/config", {"forecast_weighting_enabled": True, "precipitation_threshold_mm": 100,
    "autoupdateenabled": True, "autoupdateschedule": "minutes", "autoupdateinterval": "10", "autoupdatedelay": "0"})
c = (await ws_send({"type": "irrigation_plus/config"})).get("result", {})
r, {k: c.get(k) for k in ("forecast_weighting_enabled", "precipitation_threshold_mm", "skip_irrigation_on_precipitation",
    "autocalcmode", "live_estimate_enabled", "precipitation_forecast_days", "autoupdateinterval")}
```

Expected: `True`, `100`, `True`, `fixed_time`, `False`, `1`, `"10"`; dann
`ha_get_logs(source="error_log", search="Scheduled auto update", limit=2)` → jüngste Zeile „… for each 0:10:00“ mit
Stempel nach dem Aufruf.

---

### Ergänzungen R zu Tasks 6–9 (die genannten Steps gelten mit diesen Änderungen)

- **Task 6 Step 2:** D = −(⌈max(O1(T1), O1(E))⌉ **+ 15**) mm (statt + 8).
- **„Dokument holen“ in Task 6 Step 1/4, Task 7 Step 2, Task 8 Step 3/4, Task 9 Step 4:** Baustein X mit `CUTOFF` =
  15 min vor dem Rechen- bzw. Dispatch-Zeitpunkt, **unmittelbar nach der Auswertung** (Spec §10.3, im selben
  Zyklus); maßgebliches Dokument und Schub-Identität nach Baustein X.
- **Jeder Beleg-Step (Task 6 Step 4, Task 7 Step 4, Task 8 Step 4, Task 9 Step 5):** zusätzlich
  `ha_get_logs(source="error_log", search="status code: 429", limit=3)` → kein Stempel nach Task-5R-Beginn; sonst
  Umgebungsabbruch → Stopp, Rücksprache.
- **Jede Rechnung (Task 6 Step 5, Task 7 Step 2, Task 8 Step 6, Task 9 Step 2):** `duration` 0 oder effektiver Eimer
  ≥ 0 → Zone weggefallen → Phase nicht auswertbar → Stopp, Rücksprache, kein Nachsetzen.
- **Task 7 Step 2, Task 8 Step 2, Task 9 Step 2:** `set_bucket` A = D aus Task 6 (mit + 15).

---

### Task 10R: Rückbau und Vergleich (HA-Test, schreibend) — ersetzt Task 10

- [x] **Step 1:** Sandbox: `ws_send({"type": "irrigation_plus/schedule_delete", "schedule_id": "<P61>"})`; für
  `schedule_ec886994` und `schedule_1fac4605` `schedule_save` mit `enabled: True`; `api_post("/irrigation_plus/zones",
  {"id": A, "remove": True})`, ebenso B; dann

```python
r = await api_post("/irrigation_plus/config", {"forecast_weighting_enabled": False, "precipitation_threshold_mm": 2,
    "autocalcmode": "fixed_time", "live_estimate_enabled": False,
    "autoupdateenabled": True, "autoupdateschedule": "minutes", "autoupdateinterval": "60", "autoupdatedelay": "0"})
r
```

- [x] **Step 2:** Helfer `input_boolean.hasi61_a`/`_b` löschen (Schema per ToolSearch: `ha_remove_helpers_integrations`).

- [x] **Step 3: Koordinaten zurück** — Sandbox:

```python
r = await ws_send({"type": "irrigation_plus/coordinates_save", "manual_coordinates_enabled": False})
c = await ws_send({"type": "irrigation_plus/coordinates"})
r, {k: v for k, v in (c.get("result") or {}).items() if k.startswith("manual_")}
```

Ergebnis (nur `manual_*`) per Write-Tool nach `livetest\coords-after.json`; `grep -c "ha_" livetest/coords-after.json`
→ `0`. Neuladen wie Task 4R Step 3 prüfen (`loaded`). `ha_get_logs(source="error_log", search="Scheduled auto update",
limit=2)` → jüngste Zeile „… for each 1:00:00“ (das Neuladen plant mit dem gespeicherten Intervall).

- [x] **Step 4:** `logger.set_level` mit `"warning"` für `custom_components.irrigation_plus`, `….calculation`,
  `….irrigation`, `….live_estimate`, `….skip_conditions`, `….scheduler`, `….auto_calc`,
  `….weathermodules.PirateWeatherClient` (= effektiver Pegel vorher, Task 3 Step 3).

- [x] **Step 5:** Sicherung wie Task 3 Step 2 → `livetest\config-after.json`; Vergleich:

```bash
cd /d/Entwicklung/HASI/issue61-work/livetest && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -c "import json;a=json.load(open('config-before.json',encoding='utf-8'));b=json.load(open('config-after.json',encoding='utf-8'));print({k:(a['config'].get(k),b['config'].get(k)) for k in set(a['config'])|set(b['config']) if a['config'].get(k)!=b['config'].get(k)});print(a['schedules']==b['schedules']);print(a['zones']==b['zones']);print(json.load(open('coords-before.json'))==json.load(open('coords-after.json')))"
```

Expected: `{'autoupdateinterval': ('10', '60')}` plus höchstens laufzeitbedingte Felder (`fired_occurrences`,
`active_valve_runs`) — jede andere Abweichung zurücksetzen und begründet ins Protokoll; `True`, `True`, `True`.

- [x] **Step 6: HA-Test-Neustart** — im Chat ankündigen, dann `mcp__HA-Test__ha_restart`. Danach: Verteiler-Entitäten
  nicht mehr `unavailable` (`ha_search(query="Gardena1")`), Pegel `irrigation_plus` WARNING, Intervall-Zeile
  „… for each 1:00:00“ nach dem Neustart nicht nötig (INFO unsichtbar) — stattdessen WS `irrigation_plus/config`
  `autoupdateinterval` `"60"`.

---

### Ergänzung zu Task 11

- **Step 5 Archiv** zusätzlich: `scout.py`, `scout_test.py`, `livetest\scout-*.txt`, `livetest\coords-*.json`,
  `livetest\e3-imperial-probe.out`. Weiterhin **keine** Rohlog-Zeilen.
- Das Fork-Issue zur Abrufrate (Spec §10.5) ist nicht Teil dieses Plans; sein Text wird getrennt zur Freigabe vorgelegt.

---

## Revision 2a (2026-10-11) — Baustein X′ (sparsam), ersetzt Baustein X

**Anlass:** Task 4R Step 4 scheiterte mit `SANDBOX_LIMIT_EXCEEDED` („memory limit exceeded: 10486116 bytes >
10485760 bytes“). Gemessen: das Log-Fenster (500 Zeilen) hatte 4 382 545 Bytes mit 47 Abruf-Köpfen (19 um 09:20:42,
28 beim Neuladen um 11:20:16) und 282 Zeilen über 10 KB; Baustein X hält Rohtext, Zeilenliste und bereinigte Kopie
gleichzeitig. User-Entscheidung (Chat): sparsame Variante, gleiche Regeln. **Überall, wo der Plan „Baustein X“ sagt,
gilt Baustein X′**; Auswerten, Ablage und Prüfsumme unverändert wie unter Baustein X beschrieben.

**Abweichung zu X:** seitenweise (`PAGE` = 100 Zeilen, höchstens `MAXPAGES` = 10), Rohtext nach dem Zerlegen sofort
verworfen, Farbcodes nur an benutzten Zeilen entfernt, Fortsetzungsstücke am Seitenanfang wandern als `carry` an das
Ende der nächstälteren Seite; Doppelte (gleiches `logged_at` + `method`) fallen weg, Ergebnis chronologisch sortiert.
Blättern endet, sobald die älteste gelesene Zeile ≤ `CUTOFF` ist. **Risiko:** schreibt HA zwischen zwei Seitenabrufen
neue Zeilen, verschiebt sich die Grenze — ein dabei zerrissenes Dokument fällt als unvollständig auf (dann einmal neu
lesen; bleibt es unvollständig → Stopp, Rücksprache).

```python
import re
CUTOFF = "2026-10-11 00:00:00"
PAGE = 100
MAXPAGES = 10
ANSI = re.compile(r"\x1b\[[0-9;]*m")
TS = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d")
PAIR = re.compile(r"'time': (\d+),[^{}]*?'precipIntensity': ([-0-9.eE]+)")
docs = []
seen = []
keys = []
series = []
carry = []
earliest = None
latest = None
page = 0
while page < MAXPAGES:
    r = await call_tool("ha_get_logs", {"source": "error_log", "limit": PAGE, "order": "newest", "offset": page * PAGE})
    txt = r.get("log") if isinstance(r, dict) else str(r)
    r = None
    raw = (txt or "").split("\n")
    txt = None
    lines = list(reversed(raw)) + carry
    raw = None
    starts = [i for i in range(len(lines)) if TS.match(ANSI.sub("", lines[i][:40]))]
    page += 1
    if not starts:
        carry = lines
        lines = None
        continue
    carry = lines[:starts[0]]
    earliest = ANSI.sub("", lines[starts[0]][:40])[:23]
    if latest is None:
        latest = ANSI.sub("", lines[starts[-1]][:40])[:23]
    for j in range(len(starts)):
        i = starts[j]
        head = ANSI.sub("", lines[i][:300])
        if head[:23] < CUTOFF or "PirateWeatherClient get_" not in head or " called API " not in head:
            continue
        method = "get_data" if "get_data called" in head else "get_forecast_data"
        if (head[:23] + method) in seen:
            continue
        seen.append(head[:23] + method)
        end = starts[j + 1] if j + 1 < len(starts) else len(lines)
        doc = "".join([ANSI.sub("", lines[k]) for k in range(i, end)])
        hi = doc.find("'hourly':")
        di = doc.find("'daily':", hi + 1) if hi >= 0 else -1
        pairs = PAIR.findall(doc[hi:di] if di > hi else "")
        n_precip = doc.count("'precipIntensity'")
        masked = "***" in doc
        key_pattern = bool(re.search(r"forecast/[A-Za-z0-9]{16,}", doc))
        doc = None
        st = [int(a) for a, _ in pairs]
        key = ";".join([a + ":" + b for a, b in pairs])
        if key not in keys:
            keys.append(key)
            rows = [[int(a), float(b)] for a, b in pairs]
            series.append({"hourly": rows, "checksum": [len(rows), sum([x for x, _ in rows]),
                                                        round(sum([y for _, y in rows]), 4)]})
        docs.append({
            "logged_at": head[:23],
            "method": method,
            "chunks": end - i,
            "n_hourly": len(pairs),
            "steps_ok": len(st) == 168 and all([st[q + 1] - st[q] == 3600 for q in range(len(st) - 1)]),
            "has_daily": di > hi >= 0,
            "n_precip": n_precip,
            "masked": masked,
            "key_pattern": key_pattern,
            "series": keys.index(key),
        })
    lines = None
    if earliest <= CUTOFF:
        break
order = sorted([(docs[n]["logged_at"], n) for n in range(len(docs))])
{"window_first": earliest, "window_last": latest, "pages": page,
 "docs": [docs[n] for _, n in order], "series": series}
```

---

## Revision 2b (2026-10-11) — Ausführungshinweise aus dem Lauf

Belege: `issue61-work\livetest\protocol.md`. Keine Änderung an Kriterien oder Orakeln, nur Reihenfolge/Zeitwahl:

1. **`set_bucket` rückt `last_consumed_at` vor** (A 11:24:32 → 11:26:45). Danach muss erst eine neue Wetterzeile
   kommen, sonst rechnet die Zone still nicht. Richtige Folge in Task 6–9: `set_bucket` → neue Wetterzeile →
   P61-Zeit setzen → rechnen bzw. Dispatch abwarten.
2. **P61 vor der Rechnung auf die Phasenzeit stellen** (Task 7): eine Rechnung um 11:45:45 lief noch mit T1 als Anker
   (Gutschrift 11.33 = O1(T1)); sie zählt nicht für B3, die B3-Rechnung lief um 11:55:30 mit T3.
3. **T5 mit einem Zyklus Abstand** (Task 9): das Outlook zeigt die zwischengespeicherte Schätzung
   (`live_estimate.py:1769-1782`), der Dispatch rechnet frisch mit `run_start=utcnow()` (`irrigation.py:2352-2354`).
   T5 = 12:47 statt 12:42, damit zwischen P61-Änderung und Lesen (T5 − 90 s) ein Zyklus liegt.
4. **Mehrfach-Ziele im MCP-Dienstaufruf** als Liste in `data`, nicht als Komma-String im `entity_id`-Parameter (der
   wurde als EINE Entitäts-ID weitergereicht, HTTP 500).
