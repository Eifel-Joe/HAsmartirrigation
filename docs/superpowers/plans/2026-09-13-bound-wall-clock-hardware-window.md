# Arm-Schranke mit Hardware-Fenster — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `bound_wall_clock` rechnet die Schranke für den zweistufigen Arm mit dem Fenster, das die Hardware wirklich läuft, statt eine Rundung je Minuten-Zone zu kurz.

**Architecture:** Eine track-basierte Umrechnung `hardware_priced_for_track(track, unit, seconds)` in `run_window.py` wird die einzige Stelle der Entscheidung; `hardware_priced_seconds` delegiert an sie. `ZoneRun` bekommt `duration_unit`, gesetzt an beiden Baustellen. `bound_wall_clock` rundet `maximum_duration + lead_time` (bzw. eine gelieferte `ceiling`) über dieselbe Funktion.

**Tech Stack:** Python 3.12 (lokal) / 3.13 (CI), Home Assistant Custom Component, pytest.

**Spec:** `docs/superpowers/specs/2026-09-13-bound-wall-clock-hardware-window-design.md` (Branch `archive/design-history`, `1c494f02`).

---

## Rahmen, den jeder Task kennen muss

- Repo: `D:\Entwicklung\HASI\HAsmartirrigation`, Paket `custom_components/irrigation_plus/`.
- Test-Kommando: `./.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- Lint: `uvx black custom_components/irrigation_plus/` und `uvx ruff check custom_components/irrigation_plus/`
- Vorbestands-Fehler der lokalen Suite: **immer gegen die Basis vergleichen.**
- **Mutationsprobe Pflicht**; Wiederherstellen per Byte-Backup + `sha256sum -c`, nicht `git checkout --`.
- Commits englisch, Ende: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Keine SHAs des eigenen Arbeitsbranches in Kommentaren.
- `push` und PR nur nach Freigabe im Chat.

## Dateien

| Datei | Änderung |
|---|---|
| `custom_components/irrigation_plus/run_window.py` | neue Funktion `hardware_priced_for_track`; `hardware_priced_seconds` delegiert; `ZoneRun.duration_unit`; `bound_wall_clock` rundet; `nominal_demand_seconds` setzt das Feld |
| `custom_components/irrigation_plus/irrigation.py` | `async_plan_zone_runs` setzt `duration_unit` |
| `tests/test_run_window.py` | `_run(unit=…)`; Tests für die Funktion und die Schranke |
| `tests/test_finish_anchor_hardware_window.py` | Feld-Verdrahtung beider Baustellen; Kreuz-Pin über alle Modi |

---

### Task 0: Branch und Basis

- [ ] **Step 1: Branch von upstream**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git status --short --branch
git fetch upstream
git checkout -b fix/bound-wall-clock-hardware-window upstream/master
git log --oneline -1
```
Expected: sauber (untracked `docs/SESSION-STAND.md` ok), HEAD = `upstream/master`.

- [ ] **Step 2: Basis messen**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q -rf 2>&1 | grep -E "^FAILED|passed|failed" > /d/Entwicklung/HASI/baseline-bound.txt
tail -1 /d/Entwicklung/HASI/baseline-bound.txt
```

---

### Task 1: Gemeinsame Umrechnung nach Track

**Files:**
- Modify: `custom_components/irrigation_plus/run_window.py` (neue Funktion vor `hardware_priced_seconds`; dessen Rumpf)
- Test: `tests/test_run_window.py`

- [ ] **Step 1: Import im Test erweitern**

In `tests/test_run_window.py` den Block `from custom_components.irrigation_plus.run_window import (` ersetzen:

```python
from custom_components.irrigation_plus.run_window import (
    PARALLEL_STATION_GROUP,
    TRACK_CLASSIC,
    TRACK_SELF_CLOSING,
    TRACK_STATION,
    StationFacts,
    ZoneRun,
    bound_wall_clock,
    concurrent_wall_clock,
    nominal_demand_seconds,
    nominal_zone_duration,
    rank,
    select,
    simulate_wall_clock,
    zone_eligible_for_demand,
)
```

durch:

```python
from custom_components.irrigation_plus.run_window import (
    PARALLEL_STATION_GROUP,
    TRACK_BATCH,
    TRACK_CLASSIC,
    TRACK_SELF_CLOSING,
    TRACK_STATION,
    StationFacts,
    ZoneRun,
    bound_wall_clock,
    concurrent_wall_clock,
    hardware_priced_for_track,
    nominal_demand_seconds,
    nominal_zone_duration,
    rank,
    select,
    simulate_wall_clock,
    zone_eligible_for_demand,
)
```

- [ ] **Step 2: Fehlschlagende Tests schreiben**

Direkt vor `class TestBoundWallClock:` einfügen:

```python
class TestHardwarePricedForTrack:
    """The one place a track and a unit decide the window a valve really runs.

    ``hardware_priced_seconds`` asks it from a zone dict, ``bound_wall_clock``
    from a ZoneRun; both must get the same answer for the same zone.
    """

    def test_a_classic_track_is_never_converted(self):
        minutes = const.DURATION_UNIT_MINUTES
        assert hardware_priced_for_track(TRACK_CLASSIC, minutes, 263.0) == 263.0

    def test_a_minute_unit_self_closing_track_runs_whole_minutes(self):
        minutes = const.DURATION_UNIT_MINUTES
        assert hardware_priced_for_track(TRACK_SELF_CLOSING, minutes, 263.0) == 300.0

    def test_a_batch_track_rounds_seconds_to_the_nearest_whole_second(self):
        seconds = const.DURATION_UNIT_SECONDS
        assert hardware_priced_for_track(TRACK_BATCH, seconds, 263.4) == 263.0

    def test_a_station_is_ceiled_to_the_whole_second(self):
        # run_station takes whole seconds with a ceiling; the unit is ignored.
        minutes = const.DURATION_UNIT_MINUTES
        assert hardware_priced_for_track(TRACK_STATION, minutes, 263.4) == 264.0

    def test_a_missing_unit_is_seconds(self):
        assert hardware_priced_for_track(TRACK_SELF_CLOSING, None, 263.6) == 264.0

    def test_an_unbounded_value_stays_unbounded(self):
        # math.ceil(inf) raises, and a zone with no fixed point must keep none.
        minutes = const.DURATION_UNIT_MINUTES
        assert hardware_priced_for_track(TRACK_SELF_CLOSING, minutes, math.inf) == (
            math.inf
        )
```

- [ ] **Step 3: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_run_window.py::TestHardwarePricedForTrack -p _local_socket_unblock -q`
Expected: FAIL, `ImportError: cannot import name 'hardware_priced_for_track'`.

- [ ] **Step 4: Funktion schreiben**

In `run_window.py` direkt vor `def hardware_priced_seconds(zone: dict, seconds: float) -> float:` einfügen:

```python
def hardware_priced_for_track(track: str, unit: str | None, seconds: float) -> float:
    """``seconds`` re-priced as the window a valve on ``track`` really runs.

    The single place the decision lives. :func:`hardware_priced_seconds` reaches
    it from a zone dict through :func:`track_for_zone`, :func:`bound_wall_clock`
    from a :class:`ZoneRun`, so the model and the arm cannot disagree about
    which zones convert or by which rule. ``track_for_zone`` is built from the
    same predicates this used to test directly:

    * ``classic`` — Irrigation Plus times the valve itself; unchanged.
    * ``station`` — ``run_station`` takes whole seconds with a ceiling and a
      floor of one; :func:`duration_math.opensprinkler_window`, unit ignored.
    * ``batch``, ``service`` — the hardware owns the close and is told the
      duration in its own unit; :func:`duration_math.hardware_window`. A missing
      unit is seconds, as the zone schema defaults it.

    A non-finite value is returned unchanged: ``math.ceil(inf)`` raises, and a
    zone with no configured bound must stay unbounded rather than acquire one.
    """
    priced = float(seconds or 0.0)
    if not math.isfinite(priced) or track == TRACK_CLASSIC:
        return priced
    if track == TRACK_STATION:
        return float(opensprinkler_window(priced))
    _, window = hardware_window(priced, unit or const.DURATION_UNIT_SECONDS)
    return window


```

- [ ] **Step 5: Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_run_window.py::TestHardwarePricedForTrack -p _local_socket_unblock -q`
Expected: 6 PASS.

- [ ] **Step 6: `hardware_priced_seconds` delegiert**

In `run_window.py` den Rumpf von `hardware_priced_seconds` ersetzen:

```python
    priced = float(seconds or 0.0)
    if not is_self_closing_zone(zone):
        return priced
    if is_opensprinkler_zone(zone):
        return float(opensprinkler_window(priced))
    _, window = hardware_window(
        priced, zone.get(const.ZONE_DURATION_UNIT, const.DURATION_UNIT_SECONDS)
    )
    return window
```

durch:

```python
    return hardware_priced_for_track(
        track_for_zone(zone),
        zone.get(const.ZONE_DURATION_UNIT, const.DURATION_UNIT_SECONDS),
        seconds,
    )
```

Im Docstring von `hardware_priced_seconds` die Zeile `    siehe tests/test_finish_anchor_hardware_window.py` ersetzen durch:

```python
    The rule itself lives in :func:`hardware_priced_for_track`, which
    :func:`bound_wall_clock` shares.

    siehe tests/test_finish_anchor_hardware_window.py
```

- [ ] **Step 7: Verhalten unverändert — bestehende Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_finish_anchor_hardware_window.py tests/test_run_window.py tests/test_run_plan_pricing.py -p _local_socket_unblock -q`
Expected: alle PASS (Teardown-Errors der lokalen Env gegen Basis vergleichen).

- [ ] **Step 8: Mutationsproben**

1. In `hardware_priced_for_track` `track == TRACK_CLASSIC` entfernen → `test_a_classic_track_is_never_converted` FAIL.
2. `if track == TRACK_STATION:` → `if False:` → `test_a_station_is_ceiled_to_the_whole_second` FAIL **und** `TestHardwarePricedSeconds::test_an_opensprinkler_zone_is_ceiled_not_rounded` FAIL (beweist die Delegation).
3. `not math.isfinite(priced) or ` entfernen → `test_an_unbounded_value_stays_unbounded` FAIL (`OverflowError`).
Wiederherstellen, `sha256sum -c` OK.

- [ ] **Step 9: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_run_window.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/run_window.py tests/test_run_window.py
git commit -F - <<'EOF'
refactor(run-window): decide the hardware window by track, in one place

hardware_priced_seconds tested a zone's mode predicates to decide whether and
how its valve rounds a duration. track_for_zone is built from exactly those
predicates, so the same decision can be keyed on the track -- which a ZoneRun
carries and a zone dict does not need to.

hardware_priced_for_track is now that single decision and hardware_priced_seconds
delegates to it. No behaviour change; the existing anchor tests pass unchanged.
A non-finite value passes through, because the next caller prices bounds that
can be infinite and math.ceil(inf) raises.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: `ZoneRun` trägt die Einheit

**Files:**
- Modify: `custom_components/irrigation_plus/run_window.py` (`ZoneRun`, `nominal_demand_seconds`)
- Modify: `custom_components/irrigation_plus/irrigation.py` (`async_plan_zone_runs`)
- Test: `tests/test_finish_anchor_hardware_window.py`, `tests/test_run_window.py` (`_run`)

- [ ] **Step 1: Imports im Anker-Test erweitern**

In `tests/test_finish_anchor_hardware_window.py` ersetzen:

```python
from custom_components.irrigation_plus.run_window import (
    hardware_priced_seconds,
    nominal_zone_duration,
)
```

durch:

```python
from custom_components.irrigation_plus import run_window
from custom_components.irrigation_plus.run_window import (
    ZoneRun,
    bound_wall_clock,
    hardware_priced_seconds,
    nominal_zone_duration,
    track_for_zone,
)
```

- [ ] **Step 2: Fehlschlagende Tests schreiben**

Am Ende von `tests/test_finish_anchor_hardware_window.py` anhängen:

```python
class TestZoneRunsCarryTheUnit:
    """Both producers of ZoneRun hand the bound the zone's duration unit.

    The bound prices from configuration and applies the same rounding the run
    does; without the unit it cannot tell 263 s of minute hardware from 263 s of
    second hardware.
    """

    @pytest.mark.asyncio
    async def test_the_plan_carries_the_unit(self):
        zones = [
            _zone(1, mode=const.WATERING_MODE_SERVICE),
            _zone(
                2, mode=const.WATERING_MODE_SERVICE, unit=const.DURATION_UNIT_SECONDS
            ),
        ]
        planned = await _coord(zones).async_plan_zone_runs()
        assert {p.zone_id: p.duration_unit for p in planned} == {
            1: const.DURATION_UNIT_MINUTES,
            2: const.DURATION_UNIT_SECONDS,
        }

    def test_the_nominal_projection_carries_the_unit(self, monkeypatch):
        captured = []

        def capture(runs, **_kwargs):
            captured.extend(runs)
            return 0.0

        monkeypatch.setattr(run_window, "concurrent_wall_clock", capture)
        run_window.nominal_demand_seconds(
            [_nominal_zone(1, mode=const.WATERING_MODE_SERVICE)],
            sequencing=SEQUENTIAL,
            max_slot_seconds=300,
            min_absorption_seconds=0,
            metric=True,
        )
        assert [r.duration_unit for r in captured] == [const.DURATION_UNIT_MINUTES]
```

- [ ] **Step 3: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_finish_anchor_hardware_window.py::TestZoneRunsCarryTheUnit -p _local_socket_unblock -q`
Expected: 2 FAIL, `AttributeError: 'ZoneRun' object has no attribute 'duration_unit'`.

- [ ] **Step 4: Feld anlegen**

In `run_window.py`, `class ZoneRun`, nach der letzten Zeile `    station: StationFacts | None = None` ergänzen:

```python
    duration_unit: str | None = None
```

Im Docstring von `ZoneRun` vor der schließenden `"""` ergänzen:

```python
    ``duration_unit`` is the zone's configured unit for a valve that owns its
    close. :func:`bound_wall_clock` prices from configuration, and the hardware
    window depends on it: 263 s of minute hardware really runs 300. Absent means
    seconds, as the zone schema defaults it.
```

- [ ] **Step 5: Beide Baustellen setzen das Feld**

In `irrigation.py`, `async_plan_zone_runs`, im Aufruf `ZoneRun(` ersetzen:

```python
                    station=station_facts(self.hass, zone),
                )
```

durch:

```python
                    station=station_facts(self.hass, zone),
                    duration_unit=zone.get(const.ZONE_DURATION_UNIT),
                )
```

In `run_window.py`, `nominal_demand_seconds`, im Aufruf `ZoneRun(` ersetzen:

```python
            station=(station_facts or {}).get(int(z.get(const.ZONE_ID))),
        )
```

durch:

```python
            station=(station_facts or {}).get(int(z.get(const.ZONE_ID))),
            duration_unit=z.get(const.ZONE_DURATION_UNIT),
        )
```

- [ ] **Step 6: Test-Helfer `_run` bekommt die Einheit**

In `tests/test_run_window.py` ersetzen:

```python
    flow=False,
    station=None,
):
```

durch:

```python
    flow=False,
    station=None,
    unit=None,
):
```

und im selben Helfer:

```python
        flow=flow,
        station=station,
    )
```

durch:

```python
        flow=flow,
        station=station,
        duration_unit=unit,
    )
```

- [ ] **Step 7: Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_finish_anchor_hardware_window.py tests/test_run_window.py -p _local_socket_unblock -q`
Expected: alle PASS.

- [ ] **Step 8: Mutationsproben**

1. In `irrigation.py` `duration_unit=zone.get(const.ZONE_DURATION_UNIT),` entfernen → `test_the_plan_carries_the_unit` FAIL.
2. In `run_window.py` `duration_unit=z.get(const.ZONE_DURATION_UNIT),` entfernen → `test_the_nominal_projection_carries_the_unit` FAIL.
Wiederherstellen, `sha256sum -c` OK.

- [ ] **Step 9: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_finish_anchor_hardware_window.py tests/test_run_window.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/run_window.py custom_components/irrigation_plus/irrigation.py tests/test_finish_anchor_hardware_window.py tests/test_run_window.py
git commit -F - <<'EOF'
feat(run-window): a ZoneRun carries its zone's duration unit

bound_wall_clock prices from configuration and cannot see the zone dict, so it
had no way to tell 263 s of minute hardware from 263 s of second hardware. Both
places that build a ZoneRun now hand it the unit; nothing reads it yet.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 3: `bound_wall_clock` rundet über die gemeinsame Funktion

**Files:**
- Modify: `custom_components/irrigation_plus/run_window.py` (`bound_wall_clock`)
- Test: `tests/test_run_window.py` (`TestBoundWallClock`), `tests/test_finish_anchor_hardware_window.py` (Kreuz-Pin)

- [ ] **Step 1: Fehlschlagende Tests in `TestBoundWallClock`**

In `tests/test_run_window.py` in `class TestBoundWallClock` nach `test_counts_rotating_absorption_structure` einfügen:

```python
    def _bound(self, runs, sequencing=SEQUENTIAL):
        return bound_wall_clock(
            runs,
            sequencing=sequencing,
            max_slot_seconds=300,
            min_absorption_seconds=0,
        )

    def test_a_minute_unit_self_closing_zone_is_bounded_at_its_window(self):
        # Told 5 whole minutes for a 263 s cap, the valve really runs 300.
        runs = [
            _run(
                0,
                100,
                maximum=263,
                track=TRACK_SELF_CLOSING,
                unit=const.DURATION_UNIT_MINUTES,
            )
        ]
        assert self._bound(runs) == 300

    def test_the_lead_time_is_rounded_together_with_the_cap(self):
        # The run sends cap + lead to the valve, so 2700 + 10 = 2710 s is told
        # 46 minutes and runs 2760 -- not 2700 rounded (2700) plus 10.
        runs = [
            _run(
                0,
                100,
                maximum=2700,
                lead_time=10,
                track=TRACK_SELF_CLOSING,
                unit=const.DURATION_UNIT_MINUTES,
            )
        ]
        assert self._bound(runs) == 2760

    def test_a_classic_zone_carrying_a_minute_unit_is_not_rounded(self):
        # Irrigation Plus times a classic valve itself; the unit is left over
        # configuration and must not stretch the bound.
        runs = [_run(0, 100, maximum=263, unit=const.DURATION_UNIT_MINUTES)]
        assert self._bound(runs) == 263

    def test_a_station_is_bounded_at_the_whole_second(self):
        runs = [_run(0, 100, maximum=263.4, track=TRACK_STATION)]
        assert self._bound(runs) == 264

    @pytest.mark.parametrize("sequencing", [SEQUENTIAL, PARALLEL, ROTATING])
    def test_an_unbounded_minute_zone_stays_unbounded(self, sequencing):
        runs = [
            _run(
                0,
                100,
                maximum=None,
                track=TRACK_SELF_CLOSING,
                unit=const.DURATION_UNIT_MINUTES,
            )
        ]
        assert self._bound(runs, sequencing) == math.inf
```

- [ ] **Step 2: Tests laufen rot**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_run_window.py::TestBoundWallClock -p _local_socket_unblock -q`
Expected: FAIL — `test_a_minute_unit_self_closing_zone_is_bounded_at_its_window` (263 ≠ 300), `test_the_lead_time_is_rounded_together_with_the_cap` (2710 ≠ 2760), `test_a_station_is_bounded_at_the_whole_second` (263.4 ≠ 264). Die Klassik- und Unendlich-Tests sind schon grün und pinnen, dass es so bleibt.

- [ ] **Step 3: Implementieren**

In `run_window.py`, `bound_wall_clock`, ersetzen:

```python
        # Keyed by zone id because that is ``durations``' contract, so two
        # runs sharing an id land on one entry. Take the longer rather than
        # letting the last one win: a collision that shortens the bound is
        # the direction that overruns the finish.
        ceilings[r.zone_id] = max(ceilings.get(r.zone_id, 0.0), cap)
```

durch:

```python
        # The valve runs the window its hardware is told, and the run sends the
        # whole cap-plus-lead duration: a minute-unit self-closing zone capped at
        # 2700 s with a 10 s lead is told 46 minutes and occupies 2760. Priced
        # through the same function hardware_priced_seconds uses, so the arm and
        # the run cannot disagree about which zones round or by which rule. A
        # caller's ceiling goes through it too; rounding a value already rounded
        # changes nothing, and an infinite one passes through untouched.
        cap = hardware_priced_for_track(r.track, r.duration_unit, cap)
        # Keyed by zone id because that is ``durations``' contract, so two
        # runs sharing an id land on one entry. Take the longer rather than
        # letting the last one win: a collision that shortens the bound is
        # the direction that overruns the finish.
        ceilings[r.zone_id] = max(ceilings.get(r.zone_id, 0.0), cap)
```

Im Docstring von `bound_wall_clock` den gesamten Absatz ab `    **KNOWN GAP — this bound does NOT apply the hardware window, so it is` bis einschließlich `    through two constructors.` ersetzen durch:

```python
    Each ceiling is the window the zone's valve really runs: a valve that owns
    its close is told the duration in its own unit, and minute hardware rounds
    up. The ceiling -- configured cap plus lead time, or a caller's ``ceiling``
    -- is priced through :func:`hardware_priced_for_track`, the function
    :func:`hardware_priced_seconds` prices the run with, keyed on the run's
    ``track`` and ``duration_unit``.
```

- [ ] **Step 4: Tests grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_run_window.py::TestBoundWallClock -p _local_socket_unblock -q`
Expected: alle PASS.

- [ ] **Step 5: Kreuz-Pin über alle Modi**

Am Ende von `tests/test_finish_anchor_hardware_window.py` anhängen:

```python
class TestTheBoundAndTheRunPriceTheSameWindow:
    """The arm's bound and the run price one zone through one decision.

    ``bound_wall_clock`` reads a ZoneRun, ``hardware_priced_seconds`` a zone
    dict; both reach ``hardware_priced_for_track``. Bypass it on the bound's
    side, key it on the unit instead of the track, or drop the station rule, and
    one mode below disagrees while every hand-computed test stays green.
    """

    @pytest.mark.parametrize("mode", WATERING_MODES)
    def test_a_single_zone_is_bounded_at_the_window_its_run_is_priced_at(self, mode):
        zone = _zone(1, mode=mode, unit=const.DURATION_UNIT_MINUTES)
        # confirm_seconds stays 0: the wall-clock reduction adds it on top of
        # the ceiling, and it is not what this pin compares.
        run = ZoneRun(
            zone_id=1,
            duration=0.0,
            depletion_ratio=1.0,
            maximum_duration=PRICED,
            track=track_for_zone(zone),
            duration_unit=zone.get(const.ZONE_DURATION_UNIT),
        )
        bound = bound_wall_clock(
            [run],
            sequencing=SEQUENTIAL,
            max_slot_seconds=300,
            min_absorption_seconds=0,
        )
        assert bound == hardware_priced_seconds(zone, PRICED)
```

- [ ] **Step 6: Pin grün**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_finish_anchor_hardware_window.py::TestTheBoundAndTheRunPriceTheSameWindow -p _local_socket_unblock -q`
Expected: PASS für jeden Modus.

- [ ] **Step 7: Mutationsproben**

1. In `bound_wall_clock` `cap = hardware_priced_for_track(r.track, r.duration_unit, cap)` entfernen → Minuten-, Vorlauf- und Stationstest FAIL, Kreuz-Pin `[service]` und `[batch]` FAIL.
2. Dieselbe Zeile ersetzen durch `cap = hardware_window(cap, r.duration_unit or const.DURATION_UNIT_SECONDS)[1]` (Einheit statt Track) → `test_a_classic_zone_carrying_a_minute_unit_is_not_rounded` FAIL, Kreuz-Pin `[classic]` FAIL.
3. In `hardware_priced_for_track` `if track == TRACK_STATION:` → `if False:` → `test_a_station_is_bounded_at_the_whole_second` FAIL (die Station fällt in den Sekunden-Zweig und wird zu 263 gerundet statt zu 264 aufgerundet; deshalb nutzt der Test den Bruchteil 263.4).
Wiederherstellen, `sha256sum -c` OK.

- [ ] **Step 8: Lint + Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_run_window.py tests/test_finish_anchor_hardware_window.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/run_window.py tests/test_run_window.py tests/test_finish_anchor_hardware_window.py
git commit -F - <<'EOF'
fix(run-window): bound the arm at the window the hardware really runs

bound_wall_clock gives the two-stage arm its fixed point from each zone's
configured maximum_duration plus lead time, and did not apply the hardware
rounding. A minute-unit self-closing zone capped at 263 s is told 5 minutes and
runs 300, so the bound came out one rounding short per zone -- per zone again
under sequential and rotating, where the track is a sum. Its own docstring calls
an under-estimate the direction the arm cannot afford.

The ceiling now goes through hardware_priced_for_track, the function the run's
pricing already uses, keyed on the ZoneRun's track and unit. Cap and lead are
rounded together because the run sends them together. An infinite bound stays
infinite.

A pin over every watering mode holds the bound of a single zone equal to what
hardware_priced_seconds prices that zone's run at, so the arm and the run cannot
drift apart on which zones round.

Follow-up to #135.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Volle Suite, Lint, Prüfungen

- [ ] **Step 1: Lint**

```bash
uvx black --check custom_components/irrigation_plus/ tests/
uvx ruff check custom_components/irrigation_plus/
```

- [ ] **Step 2: Suite gegen Basis**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q -rf 2>&1 | grep -E "^FAILED|passed|failed" > /d/Entwicklung/HASI/after-bound.txt
grep "^FAILED" /d/Entwicklung/HASI/baseline-bound.txt | sort > /tmp/bb.txt
grep "^FAILED" /d/Entwicklung/HASI/after-bound.txt | sort > /tmp/ab.txt
diff /tmp/bb.txt /tmp/ab.txt && echo "IDENTISCHE Vorbestands-Fehler"
tail -1 /d/Entwicklung/HASI/baseline-bound.txt; tail -1 /d/Entwicklung/HASI/after-bound.txt
```
Expected: identische Fehlernamen; `passed` um genau +19 höher (6 Funktion, 2 Verdrahtung, 7 Schranke davon 3 parametrisiert, 4 Kreuz-Pin — einer je Bewässerungsmodus `classic`, `service`, `opensprinkler`, `batch`).

- [ ] **Step 3: Keine zweite Rundungsentscheidung mehr**

```bash
grep -n "is_opensprinkler_zone(zone)\|opensprinkler_window(\|hardware_window(" custom_components/irrigation_plus/run_window.py
```
Expected: `opensprinkler_window(` und `hardware_window(` nur noch in `hardware_priced_for_track`; `is_opensprinkler_zone` nur noch in `track_for_zone`.

- [ ] **Step 4: Keine Branch-SHAs in Kommentaren**

```bash
git diff upstream/master --unified=0 -- custom_components/ | grep -E "^\+.*\b[0-9a-f]{8}\b" || echo "keine SHAs"
```

---

### Task 5: PR (Freigabe nötig)

- [ ] **Step 1: PR-Text entwerfen** (englisch): Bezug auf JustChrs „yes please" in #135, Wurzel, warum eine track-basierte Funktion statt einer zweiten Rundungslogik (Tabelle Track ↔ Prädikat), Wirkung (Entscheidungspunkt rückt je Minuten-Zone um bis zu eine Rundung früher), Tests mit Mutationstabelle, Suite-Zahlen gegen die Basis. Ende mit `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 2: Text im Chat zeigen und Freigabe abwarten.**
- [ ] **Step 3: Nach Freigabe:**

```bash
git push -u origin fix/bound-wall-clock-hardware-window
gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/bound-wall-clock-hardware-window --title "Bound the arm at the window the hardware really runs" --body-file <datei>
```
