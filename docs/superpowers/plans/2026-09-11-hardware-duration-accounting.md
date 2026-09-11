# Hardware-Laufzeit ehrlich verbuchen — Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein Ventil, dessen Schluss der Hardware gehört und das nur ganze Minuten annimmt, soll so verbucht werden, wie es tatsächlich läuft — Gutschrift, Backstop, Lauf-Datensatz und Observed-Sperrfenster rechnen mit der aufgerundeten Dauer statt mit der gerechneten.

**Architecture:** Eine gemeinsame Funktion `hardware_window(seconds, unit)` in `duration_math.py` ersetzt die beiden zeilengleichen Kopien `_sc_convert` und `_dist_convert`. Sie gibt ein Paar zurück: den Wert für die Hardware und die Sekundenzahl, die dieser Wert bedeutet. Die drei Aufrufer schicken den ersten Wert an die Hardware und verbuchen den zweiten. Die Rundungsrichtung ändert sich nicht.

**Tech Stack:** Python 3.12, Home Assistant Custom Component, pytest mit `pytest-homeassistant-custom-component`.

**Spec:** `docs/superpowers/specs/2026-09-11-hardware-duration-accounting-design.md` (Branch `archive/design-history`)

**Arbeitsbranch:** `local/minute-rounding`, von `upstream/master` = `72406c8d`

**Testbefehl in diesem Repo** (kanonisch, nicht neu herleiten):

```bash
./.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock
```

Die lokale Suite ist unter Windows nicht vollständig lauffähig; maßgeblich ist die CI. Bekannt rot und nicht von dieser Änderung verursacht: `test_panel.py::test_async_register_panel_static_path_config`.

---

## File Structure

| Datei | Verantwortung nach der Änderung |
| --- | --- |
| `custom_components/irrigation_plus/duration_math.py` | **neu darin:** `hardware_window()` — die einzige Stelle, an der eine Dauer in die Einheit der Hardware übersetzt wird. Reine Arithmetik, nur `const`-Import, damit die Reinheitsbedingung des Moduls gewahrt bleibt. |
| `custom_components/irrigation_plus/self_closing.py` | `_sc_convert` wird zur dünnen Weiterleitung auf `hardware_window` (Mixin-Methode bleibt, weil `batch.py` sie über `self` erreicht). `async_run_self_closing` verbucht die wirksame Dauer. |
| `custom_components/irrigation_plus/batch.py` | Plan an den Controller bekommt den Hardware-Wert, `prepared` die wirksame Dauer. |
| `custom_components/irrigation_plus/distributor.py` | `_dist_convert` entfällt, `_dist_open_inlet` nutzt `hardware_window`; das Zyklus-Fenster wird auf die wirksame Dauer gesetzt. |
| `tests/test_duration_math_hardware_window.py` | **neu:** Einheitentests der Funktion selbst. |
| `tests/test_self_closing.py` | Ergänzt um Datensatz-, Gutschrift- und Backstop-Zusicherungen. |
| `tests/test_batch.py` | Ergänzt um Plan-gegen-Buchhaltung. |
| `tests/test_distributor_dispatch.py` | Ergänzt um Einlass-gegen-Fenster. |

---

## Task 1: Die gemeinsame Funktion

**Files:**
- Create: `tests/test_duration_math_hardware_window.py`
- Modify: `custom_components/irrigation_plus/duration_math.py` (ans Ende anfügen)

- [ ] **Step 1: Write the failing test**

```python
"""hardware_window: one duration, two answers — what the hardware is told,
and what that instruction actually means in seconds."""

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.duration_math import hardware_window


def test_seconds_hardware_is_told_the_rounded_seconds_and_means_them():
    assert hardware_window(263.0, const.DURATION_UNIT_SECONDS) == (263, 263.0)


def test_minutes_hardware_is_told_whole_minutes_and_means_more_seconds():
    # 263 s -> 5 minutes of hardware time, which IS 300 s of watering.
    assert hardware_window(263.0, const.DURATION_UNIT_MINUTES) == (5, 300.0)


def test_minutes_exact_multiple_is_unchanged():
    assert hardware_window(300.0, const.DURATION_UNIT_MINUTES) == (5, 300.0)


def test_minutes_sub_minute_still_rounds_up_to_one():
    # The operating principle: rather slightly too much than too little.
    assert hardware_window(15.0, const.DURATION_UNIT_MINUTES) == (1, 60.0)


def test_zero_and_none_water_nothing():
    assert hardware_window(0.0, const.DURATION_UNIT_MINUTES) == (0, 0.0)
    assert hardware_window(None, const.DURATION_UNIT_MINUTES) == (0, 0.0)


def test_unknown_unit_falls_back_to_seconds():
    assert hardware_window(263.0, "fortnights") == (263, 263.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_duration_math_hardware_window.py -p _local_socket_unblock -v`
Expected: FAIL — `ImportError: cannot import name 'hardware_window'`

- [ ] **Step 3: Write minimal implementation**

Ans Ende von `custom_components/irrigation_plus/duration_math.py`, und `import math` oben ergänzen:

```python
def hardware_window(seconds, unit):
    """``(value_for_the_hardware, seconds_that_value_means)``.

    A valve that owns its own close is told a duration in ITS unit. On
    minute-granularity hardware that instruction is rounded UP -- rather
    slightly too much water than too little -- so the window the valve really
    runs is longer than the duration that was priced. Everything that books the
    run (the optimistic credit, the run record, the backstop, the
    observed-watering suppression window) must use the second value, or the
    zone silently receives more water than its bucket ever sees.

    The rounding itself is unchanged from the two callers this replaces; only
    the second return value is new. Seconds hardware rounds to whole seconds
    and therefore means what it says.
    """
    seconds = float(seconds or 0)
    if seconds <= 0:
        return 0, 0.0
    if unit == const.DURATION_UNIT_MINUTES:
        minutes = max(1, math.ceil(seconds / 60.0))
        return minutes, float(minutes * 60)
    whole = int(round(seconds))
    return whole, float(whole)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_duration_math_hardware_window.py -p _local_socket_unblock -v`
Expected: PASS, 6 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_duration_math_hardware_window.py custom_components/irrigation_plus/duration_math.py
git commit -m "feat(duration): say what a hardware duration actually means in seconds"
```

---

## Task 2: `_sc_convert` leitet weiter

Die Mixin-Methode bleibt bestehen, weil `batch.py` sie über `self` erreicht und Task 3 sie dort gezielt ersetzt. Hier wird nur ihr Inneres zur Weiterleitung.

**Files:**
- Modify: `custom_components/irrigation_plus/self_closing.py:99-105`
- Test: `tests/test_self_closing.py:63` (bestehender Test, muss unverändert grün bleiben)

- [ ] **Step 1: Run the existing pin to see it green BEFORE the change**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_self_closing.py::test_convert_duration_minutes_rounds_up_sub_minute -p _local_socket_unblock -v`
Expected: PASS. Dieser Test pinnt die Rundung und darf sich nicht ändern — er ist die Zusicherung, dass die Weiterleitung dasselbe rechnet.

- [ ] **Step 2: Replace the body**

`self_closing.py`, `_sc_convert` ersetzen durch:

```python
    @staticmethod
    def _sc_convert(seconds: float, unit: str) -> int:
        """The value the hardware is told. See :func:`hardware_window`, which
        also returns what that value means in seconds — the number the books
        need."""
        value, _ = hardware_window(seconds, unit)
        return value
```

Import oben in `self_closing.py` ergänzen:

```python
from .duration_math import hardware_window
```

- [ ] **Step 3: Run the pin again**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_self_closing.py::test_convert_duration_minutes_rounds_up_sub_minute -p _local_socket_unblock -v`
Expected: PASS, unverändert

- [ ] **Step 4: Commit**

```bash
git add custom_components/irrigation_plus/self_closing.py
git commit -m "refactor(self-closing): route the unit conversion through duration_math"
```

---

## Task 3: Der self-closing-Lauf verbucht die wirksame Dauer

**Files:**
- Modify: `custom_components/irrigation_plus/self_closing.py:396` (direkt nach `is_opensprinkler = ...`)
- Test: `tests/test_self_closing.py`

- [ ] **Step 1: Write the failing test**

Ans Ende von `tests/test_self_closing.py` anfügen. Die Hilfsfunktionen zum Bauen einer Zone und eines Koordinators stehen oben in derselben Datei — die dort bereits benutzten Muster übernehmen, nicht neu erfinden.

```python
async def test_minute_zone_books_the_window_the_valve_actually_runs(hass):
    """263 s priced on minute hardware means 300 s of water. The run record,
    the optimistic credit and the backstop must all say 300, not 263 --
    otherwise the zone quietly receives 14% more than its bucket ever sees."""
    c = _coordinator(hass)
    zone = _zone(
        zone_id=2,
        duration=263.0,
        duration_unit=const.DURATION_UNIT_MINUTES,
        watering_mode=const.WATERING_MODE_SERVICE,
        run_service="script.valve",
        throughput=3.1,
        size=5.0,
        multiplier=1.5,
    )
    await c.store.async_update_zone(2, zone)

    # Runs are persisted through _sc_add_run (there is no getter); spy on it,
    # which is the style the rest of this file already uses.
    c._sc_add_run = AsyncMock()
    c._sc_schedule_cleanup = Mock()

    assert await c.async_run_self_closing(zone) is True

    record = c._sc_add_run.await_args.args[0]
    assert record[const.RUN_PLANNED_SECONDS] == 300.0

    # and the backstop is armed on the same number
    assert c._sc_schedule_cleanup.call_args.args[1] == 300.0

    # 3.1 L/min over 300 s = 15.5 L, not 13.588 L
    assert c._timed_volume_l(zone, 300.0) == pytest.approx(15.5)


async def test_seconds_zone_is_untouched(hass):
    """The pin for the other half: seconds hardware means what it says, so
    nothing about its accounting may move."""
    c = _coordinator(hass)
    zone = _zone(
        zone_id=3,
        duration=263.0,
        duration_unit=const.DURATION_UNIT_SECONDS,
        watering_mode=const.WATERING_MODE_SERVICE,
        run_service="script.valve",
    )
    await c.store.async_update_zone(3, zone)

    assert await c.async_run_self_closing(zone) is True
    assert c._sc_get_run(3)[const.RUN_PLANNED_SECONDS] == 263.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_self_closing.py -k "books_the_window or seconds_zone_is_untouched" -p _local_socket_unblock -v`
Expected: der erste Test FAIL mit `assert 263.0 == 300.0`, der zweite PASS

- [ ] **Step 3: Write minimal implementation**

In `async_run_self_closing`, direkt nach der Zeile `is_opensprinkler = is_opensprinkler_zone(zone)` einfügen:

```python
        # What the books must use. On minute-granularity hardware the valve is
        # told a rounded-UP duration and really runs that long, so pricing the
        # run at the unrounded number credits less water than the zone got and
        # arms the backstop to fire while the valve is still open. OpenSprinkler
        # is excluded on purpose: run_station takes whole seconds, so there is
        # no unit conversion to reconcile.
        # siehe test_self_closing.py::test_minute_zone_books_the_window_the_valve_actually_runs
        if not is_opensprinkler:
            _, planned_seconds = hardware_window(
                planned_seconds,
                zone.get(const.ZONE_DURATION_UNIT, const.DURATION_UNIT_SECONDS),
            )
```

Nichts weiter ändern: alle sieben Verwendungen von `planned_seconds` weiter unten — `_note_si_valve`, `_timed_volume_l`, `RUN_PLANNED_SECONDS`, das Start-Ereignis, `_sc_schedule_cleanup` und `_watch_start` — erben den korrigierten Wert dadurch automatisch. `_os_start_watch` liegt im `is_opensprinkler`-Zweig und bleibt unberührt.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_self_closing.py -p _local_socket_unblock -v`
Expected: beide neuen Tests PASS, keine Regression in der Datei

- [ ] **Step 5: Commit**

```bash
git add tests/test_self_closing.py custom_components/irrigation_plus/self_closing.py
git commit -m "fix(self-closing): book the window the valve actually runs"
```

---

## Task 4: Der Batch-Plan und seine Buchhaltung nennen dieselbe Dauer

**Files:**
- Modify: `custom_components/irrigation_plus/batch.py:232-242`
- Test: `tests/test_batch.py`

- [ ] **Step 1: Write the failing test**

Ans Ende von `tests/test_batch.py` anfügen; Aufbau nach dem Muster der dortigen Tests.

Kein Herauslösen nötig: `prepared` fließt direkt in `_batch_record_run(zone, watch_entity, seconds)` (`batch.py:313`), und genau dieses `seconds` ist die Zahl, die dort gebucht wird — `_note_si_valve`, `_timed_volume_l`, `_credited_depth_native`. Der Test bespitzelt also diese Methode.

```python
async def test_batch_plan_and_bookkeeping_agree_on_minute_hardware(hass):
    """The controller is told whole minutes and runs them. If the bookkeeping
    keeps the unrounded seconds, every batch zone is booked short by up to 59 s."""
    c = _coordinator(hass)
    zone = _zone(
        zone_id=4,
        duration=263.0,
        duration_unit=const.DURATION_UNIT_MINUTES,
        confirm_entity="switch.valve",
    )
    await c.store.async_update_zone(4, zone)
    c._batch_record_run = AsyncMock()
    calls = async_mock_service(hass, "script", "queue")

    await c.async_dispatch_batch_zones([zone], trigger="schedule")

    # minutes, to the controller
    assert calls[0].data["zones"][0]["duration"] == 5
    # seconds, to the books
    assert c._batch_record_run.await_args.args[2] == 300.0
```

Hinweis: Den Dienstnamen und die Nutzlast-Form aus den bestehenden Tests in `tests/test_batch.py` übernehmen — dort steht, wie `batch_run_service` in dieser Suite konfiguriert wird.

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_batch.py -k "plan_and_bookkeeping_agree" -p _local_socket_unblock -v`
Expected: FAIL — entweder `AttributeError: _batch_build_plan` oder `assert 263.0 == 300.0`

- [ ] **Step 3: Write minimal implementation**

In der Schleife `batch.py` die beiden Zeilen ersetzen:

```python
            unit = zone.get(const.ZONE_DURATION_UNIT, const.DURATION_UNIT_SECONDS)
            # The controller is told whole minutes and runs them, so the books
            # take the seconds that instruction means, not the priced number.
            # siehe test_batch.py::test_batch_plan_and_bookkeeping_agree_on_minute_hardware
            hw_value, effective_seconds = hardware_window(seconds, unit)
            prepared.append((zone, watch_entity, effective_seconds))
            plan.append(
                {
                    "zone_id": zone_id,
                    "zone_name": zone.get(const.ZONE_NAME),
                    "duration": hw_value,
                }
            )
```

Import oben in `batch.py` ergänzen:

```python
from .duration_math import hardware_window
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_batch.py -p _local_socket_unblock -v`
Expected: PASS, keine Regression

- [ ] **Step 5: Commit**

```bash
git add tests/test_batch.py custom_components/irrigation_plus/batch.py
git commit -m "fix(batch): book the duration the controller was actually given"
```

---

## Task 5: Das Verteiler-Einlassfenster

**Files:**
- Modify: `custom_components/irrigation_plus/distributor.py:62-68` (`_dist_convert` entfällt), `:70-80` (`_dist_open_inlet`), `:1287` (Fenster)
- Test: `tests/test_distributor_dispatch.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_service_inlet_window_matches_what_the_inlet_is_told(hass):
    """A service-mode inlet owns its own close. Told 5 minutes, it runs 300 s,
    so the cycle must time the outlet against 300 and not against 263."""
    c = _coordinator(hass)
    distributor = _distributor(
        watering_mode=const.WATERING_MODE_SERVICE,
        duration_unit=const.DURATION_UNIT_MINUTES,
        run_service="script.inlet",
        duration_field="duration",
    )
    calls = async_mock_service(hass, "script", "inlet")

    effective = await c._dist_open_inlet(distributor, 263.0)

    assert calls[0].data["duration"] == 5
    assert effective == 300.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py -k "inlet_window_matches" -p _local_socket_unblock -v`
Expected: FAIL — `_dist_open_inlet` gibt heute `None` zurück

- [ ] **Step 3: Write minimal implementation**

`_dist_convert` ersatzlos löschen. `_dist_open_inlet` gibt die wirksame Dauer zurück:

```python
    async def _dist_open_inlet(self, distributor: dict, seconds: float) -> float:
        """Open the inlet for a window; return the seconds it will really run.

        classic: the loop owns the timed close, so the window is what was asked
        for. service (self-closing): the hardware owns the close and, on
        minute-granularity hardware, rounds the window UP -- the caller must
        time the outlet against the returned value, not against its own.
        siehe test_distributor_dispatch.py::test_service_inlet_window_matches_what_the_inlet_is_told
        """
        if distributor.get("watering_mode") == const.WATERING_MODE_SERVICE:
            domain, service = self._dist_split_service(distributor.get("run_service"))
            data = {}
            unit = distributor.get("duration_unit", const.DURATION_UNIT_SECONDS)
            field = distributor.get("duration_field") or "duration"
            hw_value, effective_seconds = hardware_window(seconds, unit)
            data[field] = hw_value
            data["distributor_id"] = distributor.get("id")
            await self.hass.services.async_call(domain, service, data)
            return effective_seconds
```

Der übrige Rumpf der Funktion bleibt; am Ende des klassischen Zweigs `return float(seconds or 0)` ergänzen. Import oben in `distributor.py`:

```python
from .duration_math import hardware_window
```

An der Aufrufstelle `distributor.py:1378` das Fenster übernehmen:

```python
            window = await self._dist_open_inlet(distributor, window)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py tests/test_distributor_cycle.py -p _local_socket_unblock -v`
Expected: PASS, keine Regression

- [ ] **Step 5: Commit**

```bash
git add tests/test_distributor_dispatch.py custom_components/irrigation_plus/distributor.py
git commit -m "fix(distributor): time the outlet against the window the inlet really runs"
```

---

## Task 6: Die Zusicherung gegen eine neue Kopie

**Reihenfolge beachten:** dieser Task gehört VOR Task 5 geschrieben, sonst kann er nie rot werden — nach Task 5 gibt es die zweite Kopie in `distributor.py` nämlich schon nicht mehr. Schreiben, rot sehen, dann Task 5 bauen, dann grün sehen.

**Files:**
- Modify: `tests/test_duration_math_hardware_window.py`

- [ ] **Step 1: Write the failing test**

```python
import pathlib


def test_the_rounding_rule_exists_exactly_once():
    """The bug this fixes was one rounding rule living in two files that had to
    be changed together. Fail loudly if a third copy appears."""
    src = pathlib.Path(__file__).parent.parent / "custom_components" / "irrigation_plus"
    offenders = [
        p.name
        for p in src.glob("*.py")
        if p.name != "duration_math.py" and "math.ceil(seconds / 60" in p.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"unit conversion copied back into: {offenders}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_duration_math_hardware_window.py -k rounding_rule -p _local_socket_unblock -v`
Expected: FAIL mit `unit conversion copied back into: ['distributor.py']` — die zweite Kopie lebt hier noch.

- [ ] **Step 3: Jetzt Task 5 bauen, dann diesen Test erneut laufen**

Expected nach Task 5: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_duration_math_hardware_window.py
git commit -m "test(duration): pin that the rounding rule has exactly one home"
```

---

## Task 7: Volle Suite, Lint, Schwester-Pfad-Nachweis

- [ ] **Step 1: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q`
Expected: keine NEUEN Fehlschläge gegenüber dem Stand vor der Änderung. Bekannt rot: `test_panel.py::test_async_register_panel_static_path_config`. Die Zahl der Fehlschläge vor der Arbeit notieren und danach vergleichen — die lokale Umgebung ist unvollständig, deshalb zählt die Differenz und nicht die absolute Zahl.

- [ ] **Step 2: Lint (die zwei, die in CI zählen)**

```bash
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

- [ ] **Step 3: Schwester-Pfad-Nachweis**

```bash
grep -rn "math.ceil(seconds / 60" custom_components/irrigation_plus/
```

Expected: genau ein Treffer, in `duration_math.py`.

- [ ] **Step 4: Commit falls Lint etwas geändert hat**

```bash
git add -u && git commit -m "style: black"
```

---

## Self-Review gegen die Spec

| Spec-Anforderung | Task |
| --- | --- |
| Aufrunden bleibt, Bücher folgen | 1, 3 |
| `planned_s` = wirksames Fenster | 3 |
| Eine gemeinsame Funktion in `duration_math.py` | 1, 2, 5 |
| Reinheitsbedingung des Moduls gewahrt | 1 (nur `const` + `math`) |
| self-closing verbucht wirksam | 3 |
| Batch verbucht wirksam | 4 |
| Verteiler-Einlass verbucht wirksam | 5 |
| OpenSprinkler unberührt | 3 (`if not is_opensprinkler`) |
| Sekunden-Zone unverändert | 1, 3 |
| Pin gegen eine neue Kopie | 6 |
| Backstop feuert nicht vor dem Ventil | 3 (erbt aus `planned_seconds`) |

Keine offene Anforderung.
