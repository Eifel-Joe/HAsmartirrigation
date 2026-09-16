# Regen-Wächter: rollierendes 24-Stunden-Fenster — Implementation Plan (Umbau von PR #146)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Das Fenster des Niederschlags-Übersprungs läuft ab dem Laufstart über
`precipitation_forecast_days × 24` Stunden in absoluter UTC-Arithmetik, statt über
Ortskalendertage — und die zwei Clients, deren Stundenreihe dafür zu kurz reicht,
bekommen eine, die reicht.

**Architecture:** `forecast_window.py` verliert die Zeitzone ganz: `window_intervals`
schneidet feste 24-Stunden-Blöcke ab dem (nach UTC normalisierten) Laufstart, am
Auswertungszeitpunkt beschnitten wie bisher. `expected_rain` meldet statt
„Laufdatum abgedeckt" nun „erste 24 Stunden abgedeckt". Der Wächter reicht dem
Stunden-Accessor zusätzlich mit, bis wann er Abdeckung braucht; Met Office nimmt
daraufhin sein dreistündliches Dokument, wenn das stündliche nicht so weit reicht.
Pirate Weather fragt seine Stundenreihe mit `extend=hourly` an (168 statt 48 h).
Alles andere aus PR 2 bleibt: Stundenreihe zuerst, Lücken als Löcher, Tageseinträge
nur hinter der Reihe, Entscheidung auf dem gerundeten Wert, Gewichtung unangetastet.

**Tech Stack:** Python 3.12 (lokal) / 3.13 (CI), Home Assistant Custom Component,
pytest + freezegun, `zoneinfo`; Frontend Lit + vitest + eslint/prettier, Rollup.

**Spec:** `docs/superpowers/specs/2026-09-13-rain-guard-run-date-design.md`
(Branch `archive/design-history`), Nachtrag 2026-09-16, Entscheidungen E8–E12.
**Basis:** Branch `fix/rain-guard-run-date` @ `ef1ff65f` (master hereingemergt,
upstream v2026.09.16). Gemessene Basis: **7 failed / 2976 passed / 9 skipped /
320 errors**, Messdatei `D:\Entwicklung\HASI\pr146-work\baseline-ef1ff65f.txt`.

---

## Rahmen, den jeder Task kennen muss

- Repo: `D:\Entwicklung\HASI\HAsmartirrigation`, Paket `custom_components/irrigation_plus/`.
  Gearbeitet wird im Hauptbaum auf `fix/rain-guard-run-date`.
- Test-Kommando: `./.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- Lint: `uvx black custom_components/irrigation_plus/` und
  `uvx ruff check custom_components/irrigation_plus/`. ruff hat `B` und `I` an, also
  gelten `B905` (`zip` ohne `strict=`) und die Import-Reihenfolge.
- Frontend (in `custom_components/irrigation_plus/frontend`): `npx vitest run <pfad>`,
  `npm run lint`, Build `npm ci && npm run build`. **Der Build läuft `lint` vor
  `rollup`** — eine prettier-Beanstandung verhindert das Bündeln. Node v24.15.0.
  Temp/npm-Cache umleiten: `export TEMP=/d/Entwicklung/HASI/pr146-tmp
  TMP=/d/Entwicklung/HASI/pr146-tmp npm_config_cache=/d/Entwicklung/HASI/pr146-npm-cache`.
- Die lokale Suite hat Vorbestandsfehler — **immer gegen die Basis vergleichen**,
  nie gegen null. FAILED- und ERROR-Namen müssen identisch bleiben.
- **🔴 Zeitzone in Tests:** `tests/conftest.py` zieht per autouse
  `enable_custom_integrations` → `hass`, und das setzt `US/Pacific` für **jeden**
  Test, auch ohne `hass`-Parameter. Wer eine Zone braucht, fordert ein Fixture per
  Namen an, setzt sie mit `dt_util.set_default_time_zone` und stellt sie im `finally`
  zurück. Nie `monkeypatch.setattr(dt_util, "DEFAULT_TIME_ZONE", …)`.
- **Zeitzonen-Arithmetik:** Addition einer `timedelta` auf einen `ZoneInfo`-behafteten
  Zeitpunkt ist **Wanduhr**-Arithmetik (Berlin 2026-10-25 00:00 + 1 Tag = 25 echte
  Stunden). Vor jeder Addition nach UTC normalisieren. `==` auf aware datetimes
  vergleicht nur den Zeitpunkt.
- **NaN:** `max(0.0, nan)` ergibt `0.0`. `math.isfinite` VOR jedem `max` prüfen.
- **Mutationsprobe Pflicht**, je Probe:
  1. `cp <datei> /d/Entwicklung/HASI/pr146-work/mut/<name>.bak` und
     `sha256sum <datei> > /d/Entwicklung/HASI/pr146-work/mut/<name>.sha`
  2. Mutation mit dem Edit-Tool setzen, genannten Test laufen lassen (muss FAIL)
  3. `cp /d/Entwicklung/HASI/pr146-work/mut/<name>.bak <datei> && sha256sum -c /d/Entwicklung/HASI/pr146-work/mut/<name>.sha`

  **Nicht** `git checkout --` / `git stash`. Python-Hilfsskripte nie im Ordner
  `irrigation_plus` starten (dessen `datetime.py` verdeckt das Standardmodul).
  Keine Mutationsproben parallel zu anderen Agenten im selben Baum.
- Kommentare für nicht-triviale Stellen im Format des Skills `code-doku`:
  `Wurzel:` / `Fix-Logik:` / `NOT-TO-DO:` / `siehe`.
- Commits englisch, Ende `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`,
  mehrzeilig per `git commit -F - <<'EOF' … EOF`. Gezielt stagen. Zeilen, die mit
  `#` beginnen, löscht git still — „Issue #146 …" schreiben, nie „#146 …".
- **Kein Rebase.** Der Branch ist gepusht; Nachbesserungen sind neue Commits
  (`pr-workflow` §6).
- Keine SHAs des eigenen Arbeitsbranches in Code-Kommentaren, keine IP-Adressen,
  kein API-Schlüssel in Code, Test, Commit, PR oder Log.
- `push`, PR-Kommentare und HA-Neustarts **nur nach Freigabe im Chat** (Tasks 11, 12).

## Dateien

| Datei | Änderung | Task |
|---|---|---|
| `custom_components/irrigation_plus/forecast_window.py` | rollierende Blöcke, `tz` raus, Abdeckungsfeld umbenannt, Docstrings | 1 |
| `tests/test_forecast_window.py` | 5 Tests umgeschrieben, 2 ersetzt, Rest Signatur | 1 |
| `custom_components/irrigation_plus/skip_conditions.py` | Aufruf ohne `tz`, Abdeckungsziel an den Accessor, Log-Texte, Docstrings | 2 |
| `custom_components/irrigation_plus/const.py` | zwei Kommentare zur Zählweise | 2 |
| `tests/test_precipitation_guard.py` | 4 Werte-Tests, 2 Log-Tests, 1 Umkehrung | 3 |
| `tests/test_init.py` | `TestPrecipitationLookAhead` auf rollierend | 3 |
| `tests/test_skip_run_start_threading.py` | 8 Tests, nur Prosa | 3 |
| `custom_components/irrigation_plus/forecast_window.py` | Mutationspin Tagespreis | 4 |
| `custom_components/irrigation_plus/weathermodules/PirateWeatherClient.py` | `extend=hourly`, gemessene Tagesspanne im Docstring | 5 |
| `tests/test_pirateweather_daily.py`, `tests/fixtures/pirate_weather_berlin.json` | aufgezeichnete Antwort | 5 |
| `custom_components/irrigation_plus/weathermodules/MetOfficeClient.py` | `covering_until` wählt das Dokument | 6 |
| `.../OWMClient.py`, `.../OpenMeteoClient.py` | `covering_until` entgegennehmen und ignorieren | 6 |
| `tests/test_met_office_forecast_document.py` | +Abdeckungsziel | 6 |
| `tests/test_precipitation_guard_real_clients.py` | **neu**, umgeformt von JustChr | 7 |
| `frontend/localize/languages/*.json` (8) | `lookahead_help.skip` neu | 8 |
| `frontend/src/views/general/view-general.ts` (nur Prosa), `.test.ts` | Titel + 2 Zusicherungen | 8 |
| `frontend/dist/*` | neu gebaut, `git add -f` | 8 |
| `docs/configuration-when-to-water.md`, `docs/configuration-weather-location.md` | Zählweise je Modus | 8 |

**Erwartung am Ende:** pytest-Summe steigt (neue Real-Client-Datei + Pins), FAILED-
und ERROR-Namen identisch zur Basis; vitest unverändert 616. **Am Endstand
nachmessen, nicht wörtlich nehmen.**

---

### Task 0: Basis festhalten

- [ ] **Step 1: Stand prüfen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && git status --short && git log --oneline -1
```
Erwartet: nur `?? docs/SESSION-STAND.md`, HEAD `ef1ff65f`.

- [ ] **Step 2: Arbeitsordner anlegen**

```bash
mkdir -p /d/Entwicklung/HASI/pr146-work/mut
```

---

### Task 1: `forecast_window` — rollierende 24-Stunden-Blöcke

**Files:**
- Modify: `custom_components/irrigation_plus/forecast_window.py`
- Test: `tests/test_forecast_window.py`

- [ ] **Step 1: Die Tests umschreiben, die die Kalendertagform festhalten**

Fünf Tests kehren sich um, zwei werden ersetzt. Alle anderen behalten ihre
Erwartung und verlieren nur das `tz=`-Argument.

Umkehrungen (Erwartung neu):

| Test | heute | rollierend |
|---|---|---|
| `test_a_day_with_the_clocks_going_back_has_25_hours` | 25,0 mm | **24,0 mm** |
| `test_a_day_with_the_clocks_going_forward_has_23_hours` | 23,0 mm | **24,0 mm** |
| `test_24_hours_of_forecast_do_not_cover_a_25_hour_day` | mm 24,0, abgedeckt False | mm 24,0, **abgedeckt True** |
| `test_a_run_date_already_past_is_not_covered` | (…, False, False) | Block 0 überlebt den Schnitt → **True, True** |
| `test_a_one_day_window_on_a_run_date_already_past_is_empty` | (0,0, False, False) | **≈ (15,83, True, True)** |

Die ersten drei werden zu **einem** Test zusammengezogen, der die neue Aussage
trägt — eine Umstellungsnacht ändert an einem 24-Stunden-Block nichts:

```python
@pytest.mark.parametrize(
    ("label", "run_start"),
    [
        ("clocks back", _utc(2026, 10, 24, 22, 0)),   # 25-h-Ortstag in Berlin
        ("clocks forward", _utc(2027, 3, 27, 23, 0)),  # 23-h-Ortstag in Berlin
    ],
)
def test_a_daylight_saving_night_is_still_twenty_four_real_hours(label, run_start):
    # Die Blöcke sind absolute 24 Stunden; die Ortszeit zieht keine Grenze mehr.
    # Unter Kalendertagen ergaben dieselben Reihen 25,0 bzw. 23,0 mm.
    hourly = _hourly(run_start, 48, 1.0)
    rain = expected_rain(
        run_start=run_start,
        evaluated_at=run_start,
        days=1,
        hourly=hourly,
        daily=[],
    )
    assert rain.mm == pytest.approx(24.0)
    assert rain.first_24h_covered is True
    assert rain.complete is True
```

Die beiden „Laufdatum schon vorbei"-Tests werden ersetzt durch das, was unter dem
rollierenden Fenster die Aussage trägt — ein angebrochener erster Block zählt,
ein ganz vergangener nicht:

```python
def test_a_run_that_started_hours_ago_keeps_the_rest_of_its_first_block():
    # Lauf begann 21:50Z am 12., ausgewertet 06:00Z am 13.: der Rest des ersten
    # 24-h-Blocks (bis 21:50Z am 13.) ist noch da und wird bewertet.
    run_start = _utc(2026, 9, 12, 21, 50)
    rain = expected_rain(
        run_start=run_start,
        evaluated_at=_utc(2026, 9, 13, 6, 0),
        days=1,
        hourly=_hourly(_utc(2026, 9, 13, 0, 0), 48, 1.0),
        daily=[],
    )
    assert rain.mm == pytest.approx(15.833333, rel=1e-6)
    assert rain.first_24h_covered is True


def test_a_first_block_entirely_in_the_past_is_not_covered():
    # Mehr als 24 h nach dem Laufstart ist vom ersten Block nichts übrig. Ohne
    # diesen Fall entschiede eine Vorschau über den Regen des Folgetags.
    run_start = _utc(2026, 9, 12, 5, 0)
    rain = expected_rain(
        run_start=run_start,
        evaluated_at=_utc(2026, 9, 13, 6, 0),
        days=2,
        hourly=_hourly(_utc(2026, 9, 13, 0, 0), 48, 1.0),
        daily=[],
    )
    assert rain.first_24h_covered is False
    assert rain.complete is False
```

Ebenfalls anzupassen, weil die Ortszeit verschwindet — mit den Umbenennungen, auf
die sich die Mutationsproben in Step 7 beziehen:

| heute | neu |
|---|---|
| `test_the_rest_of_the_run_day_counts_from_the_evaluation` | `test_the_rest_of_the_run_block_counts_from_the_evaluation` |
| `test_the_evening_before_looks_at_the_run_date` | `test_the_evening_before_looks_at_the_run_s_own_window` |
| `test_a_three_hourly_slot_across_midnight_is_split` | `test_a_three_hourly_slot_across_a_block_edge_is_split` |
| `test_a_utc_day_entry_counts_against_a_local_date_by_overlap` | `test_a_daily_entry_counts_against_a_block_by_overlap` |

Bei allen übrigen Tests der Datei nur `tz=` aus dem Aufruf streichen und
`run_date_covered` → `first_24h_covered`; Erwartungen bleiben. **Die Datei hat 22
Testfunktionen / 28 gesammelte Fälle** — nachzählen, nicht schätzen. Für den Pin in
Step 8 kommt `import zoneinfo` dazu.

- [ ] **Step 2: Tests laufen lassen, sie müssen scheitern**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && ./.venv/Scripts/python.exe -m pytest tests/test_forecast_window.py -p _local_socket_unblock -q
```
Erwartet: FAIL — `expected_rain() got an unexpected keyword argument` bzw.
`AttributeError: 'ExpectedRain' object has no attribute 'first_24h_covered'`.

- [ ] **Step 3: `window_intervals` auf feste 24-Stunden-Blöcke**

```python
_DAY = datetime.timedelta(hours=24)


def window_intervals(run_start, days, evaluated_at):
    """``[(index, start, end)]`` in UTC: rolling 24-hour blocks from the run's start.

    Wurzel: the window used to be the run's LOCAL calendar date and the dates after
      it. That made the setting mean different things at different hours: with a
      look-ahead of 1 an evening run saw only the last hours of its own date, so
      every install watering in the evening would have gone from seeing tomorrow to
      seeing almost nothing, silently, on upgrade (JustChr on the pull request).
    Fix-Logik: block ``index`` is ``[run_start + index*24h, run_start + (index+1)*24h)``
      in absolute UTC hours. A daylight-saving night is 24 real hours again and Home
      Assistant's zone draws no boundary. The part before ``evaluated_at`` is cut
      off, because a forecast says nothing about hours already past; a block with
      less than the coverage tolerance left is dropped, so a first block wholly in
      the past disappears and ``index`` 0 is then missing from the list.
    NOT-TO-DO: do not add the offset to a zone-aware ``run_start`` without
      converting to UTC first -- adding a day to a ``ZoneInfo`` datetime is
      wall-clock arithmetic and a 25-hour night would come out as 24 hours of
      window shifted by one. And do not flatten the result to plain ``(start, end)``
      pairs: ``index`` is what tells a shrunken first block from a missing one, and
      with a look-ahead of 2 or more nothing else does.
    siehe tests/test_forecast_window.py::test_a_first_block_entirely_in_the_past_is_not_covered
    """
    start_utc = run_start.astimezone(_UTC)
    evaluated = evaluated_at.astimezone(_UTC)
    out = []
    for index in range(max(1, int(days))):
        block_start = start_utc + index * _DAY
        start = max(block_start, evaluated)
        end = block_start + _DAY
        if (end - start).total_seconds() > _COVERAGE_TOLERANCE_SECONDS:
            out.append((index, start, end))
    return out
```

`_local_midnight_utc` ersatzlos löschen.

- [ ] **Step 4: `ExpectedRain` und `expected_rain` nachziehen**

```python
class ExpectedRain(NamedTuple):
    """Forecast rain over a run's window, and how much of the window was covered."""

    mm: float
    # The first 24 hours from the run's start were fully covered (what is left of
    # them after the evaluation moment, that is).
    first_24h_covered: bool
    # Every 24-hour block of the window was fully covered.
    complete: bool
```

In `expected_rain` das `tz`-Argument streichen, `window_intervals(run_start, days,
evaluated_at)` aufrufen und die beiden Vorkommen von `run_date_covered` auf
`first_24h_covered` umbenennen. Der Docstring beschreibt die Blöcke statt der
Kalendertage.

- [ ] **Step 5: Modul-Docstring umschreiben**

Die Absätze über „calendar days", „the run's own local DATE" und den Abendlauf
ersetzen. Der Punkt über die 48-Stunden-Reichweite bekommt die neuen Zahlen und den
Hinweis, dass Pirate Weather ihn mit `extend=hourly` nicht mehr hat (Task 5) und Met
Office über das Abdeckungsziel (Task 6); stehen bleibt er für OWM und Open-Meteo als
„betrifft sie nicht". Die Unschärfe „Pirate Weather's hourly points are read as
ending at their stamp" bleibt, mit dem Zusatz, dass der erste Stempel gemessen auf
der angebrochenen Abrufstunde liegt. Der Satz „taken from the documentation, not
measured" fällt für die **Tagesspanne** weg (jetzt gemessen), bleibt aber für die
Stundenkonvention.

- [ ] **Step 6: Tests laufen lassen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && ./.venv/Scripts/python.exe -m pytest tests/test_forecast_window.py -p _local_socket_unblock -q
```
Erwartet: alle PASS.

- [ ] **Step 7: Mutationsproben**

| Mutation | muss brechen |
|---|---|
| `start = max(block_start, evaluated)` → `start = block_start` | `test_the_rest_of_the_run_block_counts_from_the_evaluation` |
| `index * _DAY` → `index * datetime.timedelta(days=1)` auf einem zonenbehafteten Start | neuer Pin aus Step 8 |
| `> _COVERAGE_TOLERANCE_SECONDS` → `> 0` | `test_a_first_block_entirely_in_the_past_is_not_covered` (mit einem Rest unter 1 s) |
| `intervals[0][0] == 0` → `True` | `test_a_first_block_entirely_in_the_past_is_not_covered` |
| Rückgabe auf `(start, end)` flach ziehen | derselbe Test |

- [ ] **Step 8: Pin gegen die Wanduhr-Falle**

```python
def test_a_zone_aware_run_start_is_measured_in_real_hours():
    # Berlin, Nacht der Rückstellung: run_start + 1 Tag ist dort 25 echte Stunden.
    # Ohne die Normalisierung nach UTC wäre der Block 25 h lang und die Reihe
    # deckte ihn nicht ab.
    berlin = zoneinfo.ZoneInfo("Europe/Berlin")
    run_start = datetime.datetime(2026, 10, 25, 0, 0, tzinfo=berlin)
    rain = expected_rain(
        run_start=run_start,
        evaluated_at=run_start,
        days=1,
        hourly=_hourly(run_start.astimezone(UTC), 24, 1.0),
        daily=[],
    )
    assert rain.mm == pytest.approx(24.0)
    assert rain.first_24h_covered is True
```

- [ ] **Step 9: Commit**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/forecast_window.py tests/test_forecast_window.py
git commit -F - <<'EOF'
fix(forecast): measure the window in 24-hour steps from the run's start

The window was the run's local calendar date and the dates after it, so the
look-ahead setting meant different things at different hours: with a look-ahead
of 1 an evening run saw only the hours left in its own date. Existing installs
that water in the evening would have moved from seeing tomorrow to seeing almost
nothing, with nothing in the upgrade to tell them.

Blocks are now absolute 24-hour spans from the run's start. A daylight-saving
night is 24 real hours again and Home Assistant's zone no longer draws a
boundary, so the zone leaves the module entirely. Hours before the evaluation
are still cut off, and a first block wholly in the past still leaves the guard
undeciding.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Der Wächter ruft ohne Zeitzone und mit Abdeckungsziel

**Files:**
- Modify: `custom_components/irrigation_plus/skip_conditions.py`
- Modify: `custom_components/irrigation_plus/const.py`

- [ ] **Step 1: Aufrufstelle umstellen**

In `_eval_precipitation`: `tz=dt_util.DEFAULT_TIME_ZONE,` aus dem
`expected_rain(...)`-Aufruf entfernen, `rain.run_date_covered` →
`rain.first_24h_covered`. Der `hourly`-Abruf bekommt das Abdeckungsziel:

```python
            now = dt_util.utcnow()
            start = dt_util.as_utc(run_start) if run_start is not None else now
            # How far the guard needs the series to reach. Met Office picks the
            # document it serves from this; the other clients hold one document
            # and ignore it.
            covering_until = start + datetime.timedelta(hours=24 * days)
            hourly = None
            if hasattr(client, "get_hourly_precipitation_forecast"):
                hourly = await self.hass.async_add_executor_job(
                    functools.partial(
                        client.get_hourly_precipitation_forecast,
                        covering_until=covering_until,
                    )
                )
```

`days` muss dafür **vor** dem `hourly`-Abruf berechnet werden — die Reihenfolge im
`try`-Block ändert sich also: `daily` → `days` → `covering_until` → `hourly`.

- [ ] **Step 2: Log-Texte**

```python
                    "Precipitation skip: the forecast does not cover the first "
                    "24 hours from the run's start, so rain is not deciding "
                    "this run"
```
und
```python
                    "Precipitation skip: the forecast covers only part of the "
                    "%s x 24-hour window",
```

- [ ] **Step 3: Docstrings**

`_eval_precipitation`: `Fix-Logik` auf die Blöcke umschreiben; der Satz „so an
evening run with a one-day window sees only the rest of its day" wird zu „so a run
that starts in the evening sees the night and the next morning". `NOT-TO-DO` bleibt
wörtlich (es geht um `get_forecast_data`, nicht um das Fenster) und bekommt einen
vierten Punkt: das Abdeckungsziel ist ein Hinweis an den Client, kein Filter — die
zurückgegebene Reihe wird unverändert integriert.
`async_evaluate_skip_conditions`: „window starts at its local date" → „window starts
at the moment it names".
`async_get_irrigation_outlook`: der `Wurzel:`-Block begründet das Überspringen
laufender Läufe mit „the window drops that whole date as past". Unter dem
rollierenden Fenster fällt nicht das Datum weg, sondern der Block schrumpft still
auf den Rest — die Begründung wird darauf umgeschrieben, der `not_before`-Sprung
**bleibt**.

- [ ] **Step 4: `const.py`**

Die zwei Kommentare an `CONF_PRECIPITATION_FORECAST_DAYS` und am
Gewichtungs-Gegenstück auf die neue Zählweise („24-hour steps from the run's start"
bzw. unverändert „from the day after the calculation").

- [ ] **Step 5: Ziel-Tests**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && ./.venv/Scripts/python.exe -m pytest tests/test_precipitation_guard.py tests/test_skip_run_start_threading.py -p _local_socket_unblock -q
```
Erwartet: die in Task 3 beschriebenen Fehlschläge, **keine** `TypeError`.

- [ ] **Step 6: Commit** (zusammen mit Task 3, wenn die Suite sonst rot bliebe —
sonst einzeln mit `fix(skip): the guard asks about 24-hour steps from the run's start`)

---

### Task 3: Die Wächter-Tests auf die neue Aussage

**Files:**
- Modify: `tests/test_precipitation_guard.py`, `tests/test_init.py`,
  `tests/test_skip_run_start_threading.py`

- [ ] **Step 1: Die vier Werte-Tests**

| Test | heute | rollierend | warum |
|---|---|---|---|
| `test_the_dry_day_before_the_rain_is_not_skipped` | 0,0 / False | **unverändert** | JustChr: „Please keep that test" |
| `test_the_rain_day_itself_is_skipped` | 2,15 / True | **unverändert** | Morgenfall aus #137 |
| `test_the_evening_outlook_for_tomorrow_looks_at_tomorrow` | 2,15 / True | **unverändert** | Fenster ab 06:20 des 13. |
| `test_rain_in_the_first_local_hour_is_not_on_the_day_before` | 0,0 / False | **2,15 / True** | Regen 00:00–01:00 des 13. liegt im Fenster ab 06:19 des 12. |
| `test_rain_in_the_first_local_hour_counts_for_the_run_date` | 2,15 / True | **0,0 / False** | derselbe Regen liegt vor dem Laufstart 06:20 |
| `test_a_window_whose_later_days_are_partly_covered_still_decides` | 4,58 | **5,00** | der UTC-15.-Eintrag fällt jetzt ganz ins Fenster |

Die beiden „first local hour"-Tests werden **zusammen** durch ein Paar ersetzt, das
die neue Grenze trägt (der Laufstart, nicht Ortsmitternacht), mit Namen wie
`test_rain_before_the_run_starts_does_not_count` und
`test_rain_in_the_night_after_the_run_starts_counts`. Die Konstante
`FIRST_LOCAL_HOUR` und ihr Kommentar („only Home Assistant's zone puts it on the
run's date") verschwinden mit ihnen.

- [ ] **Step 2: Die Umkehrung, die JustChr ausdrücklich verlangt**

```python
@pytest.mark.parametrize(
    ("days", "rain_at", "observed", "would_skip"),
    [
        # Mit einem Fenster von 1 reicht der Abendlauf über die Nacht: der Regen
        # am nächsten Morgen zählt. Unter Kalendertagen sah er nur drei Stunden.
        (1, _local(2026, 9, 14, 6, 0), 2.15, True),
        # Zwei Tage weiter liegt ausserhalb von 24 h und braucht das Fenster 2.
        (1, _local(2026, 9, 15, 6, 0), 0.0, False),
        (2, _local(2026, 9, 15, 6, 0), 2.15, True),
    ],
)
async def test_an_evening_run_with_a_one_day_window_sees_the_next_morning(
    berlin, days, rain_at, observed, would_skip
):
    with freeze_time(_local(2026, 9, 13, 21, 0)):
        result = await _coordinator(_client(rain_at))._eval_precipitation(
            _config(days=days)
        )
    assert (result["observed"], result["would_skip"]) == (observed, would_skip)
```

`_hourly` reicht heute vom lokalen 12. bis 15.; für den dritten Fall muss die Reihe
bis zum 16. laufen — den Bereich in `_hourly` von `range(1, 73)` auf `range(1, 97)`
erweitern und die Tageseinträge in `_forecast_days` um den 16. ergänzen.

- [ ] **Step 3: Die zwei Log-Tests**

`test_at_dispatch_an_uncovered_run_date_is_logged_at_info` und
`test_a_preview_logs_an_uncovered_run_date_at_debug` prüfen den Teilstring
`"does not cover the run's date"` → `"does not cover the first 24 hours"`. Namen
mit umbenennen.

- [ ] **Step 4: `test_init.py::TestPrecipitationLookAhead`**

Der Test friert 18:00Z ein und legt 5 mm in die Stunde, die um Ortszeit 10:00 des
Folgetags endet. Unter dem rollierenden Fenster liegt das **innerhalb** der ersten
24 h, der `days=1`-Fall kippt von (0,0 / False) auf (5,0 / True). Damit er weiter
das prüft, was er prüfen soll — dass die Einstellung das Fenster steuert —, wird
der Regen auf **30 Stunden nach dem eingefrorenen Zeitpunkt** gelegt:
`rain_at = frozen + 30 * hour`. Dann gilt: `days=1` → 0,0 / False, `days=2` →
5,0 / True, unabhängig von der Zeitzone der Testumgebung. Der Docstring
(„1-day window sees only the run's own date") wird auf „the first 24 hours from the
run's start" umgeschrieben.

- [ ] **Step 5: `test_skip_run_start_threading.py`**

Acht Tests, alle voll gemockt — sie prüfen nur, dass ein Laufbeginn ankommt, und
bleiben grün. Nur Prosa in Docstrings und Kommentaren anpassen, wo „run's date"
steht. **Nachzählen: acht, nicht sechs oder sieben.**

- [ ] **Step 6: Laufen lassen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && ./.venv/Scripts/python.exe -m pytest tests/test_precipitation_guard.py tests/test_skip_run_start_threading.py tests/test_init.py -p _local_socket_unblock -q
```
Erwartet: alle PASS ausser den bekannten Vorbestandsfehlern in `test_init.py`.

- [ ] **Step 7: Mutationsproben**

| Mutation | muss brechen |
|---|---|
| `covering_until = start + …` → `now + …` | Task 6 Test (Vorschau mit altem Dokument) |
| Log-Schwelle `_LOGGER.info if run_start is None` → immer `debug` | `…_logged_at_info` |
| `rain.first_24h_covered` → `rain.complete` | `test_a_window_whose_later_days_are_partly_covered_still_decides` |

- [ ] **Step 8: Commit**

```bash
git add custom_components/irrigation_plus/skip_conditions.py custom_components/irrigation_plus/const.py tests/test_precipitation_guard.py tests/test_init.py tests/test_skip_run_start_threading.py
git commit -F - <<'EOF'
fix(skip): the rain guard looks 24-hour steps ahead from the run's start

The guard no longer asks Home Assistant's zone which dates a run covers; it
asks the run's own start. An evening run with a look-ahead of 1 sees the night
and the next morning again, which is what the setting meant before this series
and what an existing install expects after an upgrade.

The pair of tests that pinned the old boundary (rain in the run date's first
local hour) is replaced by the pair that pins the new one: rain before the run
starts does not count, rain in the night after it does.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Die überlebende Mutation festnageln (JustChrs Fund)

**Files:**
- Modify: `custom_components/irrigation_plus/forecast_window.py` (nur Kommentar)
- Test: `tests/test_forecast_window.py`

Sein Befund: im Aufrufer von `_entries_behind` überlebt es, einen Tageseintrag über
feste 86400 s zu bepreisen statt über `(end - start)`. Nur ein Pirate-Weather-Tag
mit Zeitumstellung unterscheidet die beiden — und nur Pirate Weather kann so einen
Eintrag überhaupt liefern, weil die anderen drei Clients `day_start + 1 Tag` in UTC
bauen.

- [ ] **Step 1: Der tötende Test**

```python
@pytest.mark.parametrize(
    ("hours", "mutant_mm"),
    [(25, 22.92), (23, 21.08)],
)
def test_a_daily_entry_is_priced_over_its_own_span(hours, mutant_mm):
    # Pirate Weather stempelt seine Tagesblöcke auf Ortsmitternacht, ein
    # Umstellungstag ist dort 23 oder 25 Stunden lang. Wer ihn mit festen 86400 s
    # bepreist, rechnet in beide Richtungen falsch -- deshalb beide Fälle.
    start = _utc(2026, 10, 25, 0, 0)
    end = start + datetime.timedelta(hours=hours)
    entry = {
        const.FORECAST_DAY_START: start,
        const.FORECAST_DAY_END: end,
        const.MAPPING_PRECIPITATION: 23.0,
    }
    # Fenster deckt nur einen Teil der Spanne ab, sonst sind beide Preise gleich.
    rain = expected_rain(
        run_start=start,
        evaluated_at=start,
        days=1,
        hourly=[],
        daily=[entry],
    )
    assert rain.mm == pytest.approx(23.0 * min(24, hours) / hours, rel=1e-4)
    assert rain.mm != pytest.approx(mutant_mm, rel=1e-4)
```

**Zahlen beim Schreiben nachrechnen** — die Werte oben sind aus der Analyse
übernommen und müssen gegen den echten Helfer geprüft werden, bevor der Test
committet wird.

- [ ] **Step 2: Mutationsprobe**

`mm / (end - start).total_seconds()` → `mm / 86400.0`; der Test muss FAIL geben.

- [ ] **Step 3: `NOT-TO-DO`-Kommentar an die Stelle**

```python
    # NOT-TO-DO: do not price a daily entry over a fixed 86400 s. Three of the four
    #   clients build their span as a UTC date plus one day, which is always 24 h,
    #   so the constant passes every test built on them -- but Pirate Weather takes
    #   both ends from its own block stamps, and a daylight-saving day is 23 or 25
    #   hours there. day_span converts both ends to UTC before returning them, so
    #   (end - start) is real elapsed time and is the divisor that matches the mm.
    # siehe tests/test_forecast_window.py::test_a_daily_entry_is_priced_over_its_own_span
```

- [ ] **Step 4: Commit** `test(forecast): pin a daily entry to the price of its own span`

---

### Task 5: Pirate Weather fragt `extend=hourly`

**Files:**
- Modify: `custom_components/irrigation_plus/weathermodules/PirateWeatherClient.py`
- Create: `tests/fixtures/pirate_weather_berlin.json`
- Test: `tests/test_pirateweather_daily.py`

- [ ] **Step 1: Die aufgezeichnete Antwort ablegen**

Die am 2026-09-16 gemessene Antwort liegt unter
`D:\Entwicklung\HASI\pr146-work\pirate-extend-hourly.json` (Berlin 52.52/13.41,
168 Stundenwerte, 8 Tageseinträge, kein Schlüssel im Dokument — vor dem Kopieren
mit `grep -c` gegenprüfen). Auf `tests/fixtures/pirate_weather_berlin.json`
kopieren, auf die für den Test nötigen Felder eindampfen, und im Test-Docstring
festhalten, wann und wo sie aufgezeichnet wurde.

- [ ] **Step 2: Failing test — die Reihe reicht über 48 Stunden**

```python
def test_the_hourly_block_reaches_past_two_days():
    """Recorded from the live API on 2026-09-16 for Berlin (52.52/13.41)."""
    doc = json.loads(_FIXTURE.read_text())
    client = PirateWeatherClient("key", "1", 52.52, 13.41, 0)
    client._cached_doc = doc
    series = client.get_hourly_precipitation_forecast()
    span = series[-1][0] - series[0][0]
    assert span > datetime.timedelta(hours=48)
```

- [ ] **Step 3: `extend=hourly` in die URL**

```python
PirateWeather_URL = (
    "https://api.pirateweather.net/forecast/{}/{},{}?units={}&version={}"
    "&exclude=minutely,alerts&extend=hourly"
)
```

mit `Wurzel:`/`Fix-Logik:`/`NOT-TO-DO:`-Kommentar: ohne den Parameter reicht der
Block 48 Stunden ab dem Abruf, was ein rollierendes 24-Stunden-Fenster nur deckt,
solange das Dokument jünger als 23 Stunden ist; gemessen kostet der Parameter
30 986 → 85 602 Byte bei gleicher Antwortzeit und lässt den Tagesblock unberührt.
NOT-TO-DO: den Parameter nicht auch an `exclude` hängen und nicht annehmen, dass
jede Tarifstufe ihn liefert — gemessen wurde auf einem Schlüssel.

- [ ] **Step 4: Gemessene Tagesspanne im Docstring**

Der Kommentar „as the Pirate Weather API documentation describes it: taken from the
API, not measured against a live response" wird durch die Messung ersetzt: am
2026-09-16 für Berlin geprüft, `time` ist Ortsmitternacht (`2026-09-15T22:00Z` =
`2026-09-16T00:00+02:00`), alle Spannen im Dokument 86400 s; ein Umstellungstag lag
nicht im Fenster, die 23/25-Stunden-Annahme bleibt also unbelegt. Der Vorbehalt bei
`get_hourly_precipitation_forecast` (Beginn oder Ende der Stunde) **bleibt**, mit
dem Zusatz, dass der erste Stempel gemessen auf der angebrochenen Abrufstunde liegt.

- [ ] **Step 5: Tests + Mutationsprobe** (`extend=hourly` aus der URL entfernen →
Test aus Step 2 muss FAIL geben)

- [ ] **Step 6: Commit** `fix(pirate-weather): ask for the long hourly block`

---

### Task 6: Met Office wählt das Dokument nach dem Abdeckungsziel

**Files:**
- Modify: `custom_components/irrigation_plus/weathermodules/MetOfficeClient.py`
- Modify: `.../OWMClient.py`, `.../OpenMeteoClient.py`, `.../PirateWeatherClient.py`
- Test: `tests/test_met_office_forecast_document.py`

- [ ] **Step 1: Failing test**

Die vorhandene Datei baut ihre Dokumente über Helfer; die neuen Tests nutzen
dieselben. `_hourly_doc(first, steps)` liefert ein `timeSeries` im Stundentakt,
`_three_hourly_doc(first, steps)` eines im Dreistundentakt — beide mit
`totalPrecipAmount` je Schritt.

```python
FETCHED = datetime.datetime(2026, 9, 13, 6, 0, tzinfo=datetime.timezone.utc)


def _client_with_both_documents():
    client = MetOfficeClient(api_key="k", latitude=51.5, longitude=-0.1, elevation=10)
    # Beide Dokumente zur selben Zeit geholt: die Abrufzeit-Regel aus dem
    # vorigen Commit entscheidet hier nichts, nur die Reichweite.
    client._cached_hourly = _hourly_doc(FETCHED, 48)
    client._cached_three_hourly = _three_hourly_doc(FETCHED, 56)
    client._cached_hourly_at = datetime.datetime(2026, 9, 13, 8, 0)
    client._cached_three_hourly_at = datetime.datetime(2026, 9, 13, 8, 0)
    return client


def test_the_three_hourly_document_serves_when_the_hourly_one_stops_too_early():
    # Das stündliche Dokument reicht 48 h, das dreistündliche sieben Tage. Wer
    # Abdeckung bis in 60 Stunden braucht, bekommt das gröbere Produkt.
    client = _client_with_both_documents()
    target = FETCHED + datetime.timedelta(hours=60)
    series = client.get_hourly_precipitation_forecast(covering_until=target)
    assert series[-1][0] >= target


def test_the_hourly_document_keeps_serving_while_it_reaches_far_enough():
    # Innerhalb der 48 Stunden bleibt die feinere Auflösung erhalten: die
    # Stundenreihe hat einen Takt von einer Stunde, nicht von dreien.
    client = _client_with_both_documents()
    target = FETCHED + datetime.timedelta(hours=30)
    series = client.get_hourly_precipitation_forecast(covering_until=target)
    steps = {b[0] - a[0] for a, b in zip(series, series[1:], strict=False)}
    assert steps == {datetime.timedelta(hours=1)}


def test_without_a_target_the_hourly_document_still_wins():
    # live_estimate ruft ohne Ziel auf; sein Verhalten darf sich nicht ändern.
    client = _client_with_both_documents()
    series = client.get_hourly_precipitation_forecast()
    steps = {b[0] - a[0] for a, b in zip(series, series[1:], strict=False)}
    assert steps == {datetime.timedelta(hours=1)}
```

- [ ] **Step 2: `covering_until` entgegennehmen**

Alle vier Clients bekommen `def get_hourly_precipitation_forecast(self,
covering_until=None)`. Bei OWM, Open-Meteo und Pirate Weather steht im Docstring:
„Ein Client mit nur einem Dokument hat nichts zu wählen und ignoriert den Hinweis."
Met Office reicht ihn an `_forecast_document(covering_until)` durch:

```python
        doc = self._forecast_document(covering_until)
```

und dort, nach der bestehenden Regel über die Abrufzeiten:

```python
        # Wurzel: the hourly product runs 48 h from ITS OWN fetch. A rolling
        #   24-hour window needs coverage to run start + 24 h, so a document
        #   fetched nearly a day earlier stops inside the window -- and a daily
        #   entry cannot fill the gap, because it starts before the series ends.
        #   The guard then does not decide and the run waters into forecast rain.
        # Fix-Logik: when the caller says how far it needs coverage and the hourly
        #   series stops short of it while the three-hourly one reaches, serve the
        #   coarser product. Three-hourly steps are divided back to a rate, so a
        #   window total is the same; only the placing inside a step is coarser.
        # NOT-TO-DO: do not apply this to the temperature accessor -- the intra-day
        #   estimate reads short spans, where three-hourly placing does matter, and
        #   it never asks for coverage beyond the day.
        # siehe tests/test_met_office_forecast_document.py
```

Die Reichweite eines Dokuments wird aus seinem letzten `timeSeries`-Stempel
gelesen, nicht aus der Abrufzeit plus 48 h — die Annahme „48 h" steht sonst
ungeprüft im Code.

- [ ] **Step 3: Aufrufer** — `live_estimate` ruft weiter ohne das Argument
(unverändertes Verhalten, im Docstring benennen).

- [ ] **Step 4: Tests + Mutationsproben** (Bedingung invertieren; `covering_until`
ignorieren)

- [ ] **Step 5: Commit** `fix(met-office): serve the three-hourly series when the hourly one stops short`

---

### Task 7: JustChrs Real-Client-Tests, umgeformt

**Files:**
- Create: `tests/test_precipitation_guard_real_clients.py`

- [ ] **Step 1:** Seine Datei aus dem Kommentar auf #146 übernehmen
(`gh api repos/JustChr/HAsmartirrigation/issues/146/comments`), mit drei Änderungen:
  1. Das Fixture `berlin` **nicht** aus `tests.test_precipitation_guard` importieren
     — es gibt in dieser Suite keinen Präzedenzfall für modulübergreifende
     Fixture-Importe. Stattdessen in `tests/conftest.py` bereitstellen oder lokal
     definieren.
  2. Der Pirate-Weather-Fall speist sich aus `tests/fixtures/pirate_weather_berlin.json`
     (Task 5), mit auf den Testtag verschobenen Zeitstempeln, statt aus `_pirate_doc`.
  3. Erwartungen gegen das rollierende Fenster nachrechnen — laut Analyse halten
     alle neun Fälle, weil jedes Dokument bei `now` gebaut wird; **nachmessen, nicht
     glauben**.

- [ ] **Step 2:** Ein zehnter Fall, den seine Datei strukturell nicht erreichen kann
und der genau seine Sorge belegt: ein Dokument, das 23 Stunden vor dem Dispatch
abgerufen wurde und nicht neu geholt wird. Der Test fährt beide Blocklängen
gegeneinander und belegt damit in einem Zug die Lücke **und** dass Task 5 sie
schliesst:

```python
@pytest.mark.parametrize(
    ("hourly_points", "covered", "skips"),
    [
        # 48 Punkte: der Block reicht bis Abruf + 47 h, das Fenster braucht
        # Abruf + 23 h + 24 h = Abruf + 47 h ... und die Minuten der Abrufstunde
        # fehlen. Der Wächter entscheidet nicht, der Lauf giesst in den Regen.
        (48, False, False),
        # 168 Punkte (extend=hourly, seit diesem PR der Normalfall): abgedeckt.
        (168, True, True),
    ],
)
async def test_a_day_old_document_only_covers_the_window_with_the_long_block(
    hourly_points, covered, skips
):
    fetched = _local(2026, 9, 12, 7, 20)
    dispatch = _local(2026, 9, 13, 6, 20)          # 23 h 00 m spaeter
    doc = _pirate_doc_from_fixture(fetched, hourly_points, rain_ending_at=AFTERNOON)
    client = PirateWeatherClient("key", "1", 52.52, 13.41, 0)
    client.cache_seconds = 86399                    # taegliches Auto-Update
    client._cached_doc = doc
    client._cached_data_at = fetched
    client._cached_forecast_at = fetched
    with freeze_time(dispatch):
        result = await _coordinator(client)._eval_precipitation(_config())
    assert result["available"] is covered
    assert result["would_skip"] is skips
```

`_pirate_doc_from_fixture` nimmt die aufgezeichnete Antwort aus Task 5, verschiebt
alle Zeitstempel auf `fetched` und schneidet den Stundenblock auf `hourly_points`.
Der Regen wird in die Stunde gelegt, die um 14:00 Ortszeit am 13. endet — derselbe
Fall wie in #137. **Die genaue Minutenzahl beim Schreiben nachrechnen:** die
Abdeckung kippt bei `23 h minus den Minuten der Abrufstunde`, der Test muss auf der
richtigen Seite der Kante liegen und das im Kommentar begründen.

- [ ] **Step 3: Laufen lassen, Commit** `test(skip): drive the rain guard through the real weather clients`

---

### Task 8: Hilfetext, Doku, Panel, dist

**Files:**
- Modify: `frontend/localize/languages/{en,de,es,fr,it,nl,no,sk}.json`
- Modify: `frontend/src/views/general/view-general.test.ts`
- Modify: `docs/configuration-when-to-water.md`, `docs/configuration-weather-location.md`
- Rebuild: `frontend/dist/*`

- [ ] **Step 1: `weather_skip.lookahead_help.skip`, englisch**

> How many 24-hour steps of forecast to add up when checking for rain, counted
> from the moment the run starts: 1 = the 24 hours from the start of the run,
> 2 = the next 48 hours, and so on.

Der Satz über den Abendlauf entfällt ersatzlos. **`.water_less` bleibt Wort für
Wort unverändert** — die Gewichtung zählt weiter ab dem Tag nach der Berechnung.

- [ ] **Step 2: Die sieben anderen Sprachen** übersetzen (nicht das Englische
kopieren — `tests/test_i18n_completeness.py::test_no_value_is_left_as_the_english_string`
schlägt bei ≥ 4 gleichen Prosawörtern an).

- [ ] **Step 3: vitest**

`view-general.test.ts` nagelt den englischen Satz zweimal fest, in beide Richtungen
(`toContain` und `not.toContain`), und der `it(...)`-Titel selbst ist
Kalendertag-Prosa. Alle drei anpassen.

- [ ] **Step 4: Doku**

`configuration-when-to-water.md`: der Absatz „For *Water less* and *Skip watering*…"
bekommt die 24-Stunden-Zählung für *Skip watering*, der Satz über den Abendlauf
entfällt, *Water less* bleibt.
`configuration-weather-location.md`: „counted by local day starting with the day of
the run" → „counted in 24-hour steps from the start of the run".

- [ ] **Step 5: Build**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
export TEMP=/d/Entwicklung/HASI/pr146-tmp TMP=/d/Entwicklung/HASI/pr146-tmp npm_config_cache=/d/Entwicklung/HASI/pr146-npm-cache
npm run build
```
Dann `git add -f custom_components/irrigation_plus/frontend/dist/`.

- [ ] **Step 6: Commit** `i18n(skip): the look-ahead help counts 24-hour steps from the run's start`

---

### Task 9: Volle Suite, Lint, Geschwister-Prüfung

- [ ] **Step 1**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/ && uvx ruff check custom_components/irrigation_plus/
./.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q > /d/Entwicklung/HASI/pr146-work/after.txt 2>&1
diff <(grep -E "^(FAILED|ERROR)" /d/Entwicklung/HASI/pr146-work/baseline-ef1ff65f.txt | sort) \
     <(grep -E "^(FAILED|ERROR)" /d/Entwicklung/HASI/pr146-work/after.txt | sort)
```
Erwartet: `diff` leer, Summe höher als 2976.

- [ ] **Step 2: vitest**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend && npx vitest run
```

- [ ] **Step 3: dist reproduzierbar** — `npm run build`, dann SHA-256 gegen HEAD
vergleichen, `git restore --source=HEAD` bei bloss veraltetem Index-Stempel.

- [ ] **Step 4: Geschwister-Pfad-Check** — jeder Leser von
`get_hourly_precipitation_forecast` (`skip_conditions.py`, `live_estimate.py`) und
jeder Leser von `expected_rain`/`day_span` auf dasselbe Fehlermuster prüfen.

- [ ] **Step 5: Keine privaten Verweise** in hinzugefügten Zeilen: keine SHAs des
Arbeitsbranches, keine IP, kein API-Schlüssel, keine Koordinaten des Users.

```bash
git diff 0b418644..HEAD | grep -nE "^\+.*(95HAb2|192\.168\.|[0-9a-f]{7,40}\b)" | head
```

---

### Task 10: Texte nach aussen, Archiv (Freigabe nötig)

- [ ] **Step 1:** PR-Text und den Kommentar auf #146 im Chat vorlegen. Der Text
nennt **jede nicht abschaltbare Verhaltensänderung**: das Fenster ist am Dispatch
eine Obermenge des bisherigen (kann also streichen, wo vorher bewässert wurde), der
Abendlauf sieht wieder den nächsten Morgen, Pirate Weather fragt mehr Daten an,
Met Office kann gröber antworten. Dazu die Messtabelle als Antwort auf seine
Abdeckungsfrage, und die drei vorbestehenden Befunde aus dem Spec-Nachtrag.
- [ ] **Step 2:** Nach Freigabe pushen. **Achtung:** `archive/design-history` ist
drei Commits vor `origin` mit den #139-Dokumenten, deren Freigabe noch aussteht —
vor einem Push des Archivbranches klären, ob die mitgehen dürfen.
- [ ] **Step 3:** Design-Historie (dieser Plan + Spec-Nachtrag) auf
`archive/design-history` schieben, Worktree danach entfernen, keine
`worktree-*`-Branches zurücklassen.
- [ ] **Step 4:** Die drei vorbestehenden Befunde aus dem Spec-Nachtrag in
`D:\Entwicklung\HASI\ToDo.md` unter „Befunde" eintragen (nicht monotone Abdeckung;
`cache_seconds` bleibt nach Auto-Update-Aus stehen; zweite Reichweitenregel in
`day_projection`) — mit dem Vermerk, dass sie NICHT Teil dieses PR sind und vor
einer Meldung zu prüfen ist, ob upstream sie inzwischen angefasst hat.

---

### Task 11: Live-Test (eigene Freigabe, nach Task 9)

- [ ] HA-Test läuft auf Open-Meteo, das von der Abdeckungsfrage nicht betroffen ist
— der Live-Test prüft also die **Fensterform**, nicht die Härtung: Hilfetext je
Modus in der Oberfläche, Chip-Zahl gegen die Summe der Open-Meteo-Stundenwerte ab
Laufstart über 24 h (±0,05 mm), keine Exception im Log. Pirate Weather und Met
Office lassen sich hier nicht live prüfen; das gehört so in den PR-Text.
