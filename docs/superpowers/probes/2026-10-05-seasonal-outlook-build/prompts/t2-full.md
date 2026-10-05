# Task 2: Die Menge fragt die Regel der Rechnung und skaliert mit Kc

You implement exactly this one task of the plan. The plan is written in German; the code, tests and commit messages in it are English and final.

## Context

You are one of several implementers working through a plan, one task at a time, for the Home
Assistant custom integration "Irrigation Plus" (package `custom_components/irrigation_plus`). A
controller dispatches each task; a script and a reviewer check your work afterwards.

The fix: the 12-month seasonal outlook (`custom_components/irrigation_plus/watering_calendar.py`,
`async_generate_watering_calendar`) must price a month by the rules of the real calculation, and
its synthetic climate must do what its comments say. Measured defects: the PyETO branch added the
month's rain to the ET and the volume subtracted it again (ET column showed rain, volume ignored
rain); rain was subtracted for every module although the calculation books rain only for PyETO
(the rule is `calculation.zone_module_models_weather`); the zone's crop coefficient Kc was never
applied; the Static module's daily bucket delta (negative = demand) was read as a monthly ET, so
every demand became 0 L; Passthrough multiplied by 30 instead of the month's days; humidity, wind
and temperate rain peaked in July although commented "higher in winter", and the southern
hemisphere mirrored only the temperature. The climate stays synthetic (constants unchanged) and
every place that shows or describes it now calls it an illustration derived from latitude.

**This plan was already run once, task by task, in a throwaway worktree on the same base commit
`bbf2e151`.** Every block below was applied verbatim; every RED/GREEN expectation in the section
"Measured in the dry run" is what was actually observed. The plan's blocks, applied to the base,
reproduce the tested end state byte for byte (checked by the controller). If what you see differs
from an expectation, STOP and report (status BLOCKED or DONE_WITH_CONCERNS) with the exact output
— do not improvise a fix, do not adapt a block.

## Ground rules (binding)

**Worktree:** `D:\Entwicklung\HASI\issue10-work\wt` (Git Bash path
`/d/Entwicklung/HASI/issue10-work/wt`), branch `fix/seasonal-outlook`. Work ONLY there. Never touch
`D:\Entwicklung\HASI\HAsmartirrigation` (the main checkout) or any other worktree. There is no
`.venv` in the worktree; the interpreter is named absolutely. Scratch output goes under
`D:\Entwicklung\HASI\issue10-work\` — never to `C:`.

**Shell:** use the Bash tool (Git Bash, POSIX syntax). No PowerShell. Do not use `sleep`.

**Applying the plan's blocks — use the script, do not type the code yourself.** Every edit of a
task is dictated verbatim in the plan ("Ersetze in `F`: … durch: …" = replace, "Hänge an `F` an:"
= append to the end of the file). The script applies them exactly, keeps the file's CRLF line
endings, and refuses (prints `STOP: anchor … found Nx`, changes nothing) if an anchor is not found
exactly once:

```bash
cd /d/Entwicklung/HASI/issue10-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe apply_plan_task.py <N> tests
cd /d/Entwicklung/HASI/issue10-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe apply_plan_task.py <N> code
```

`tests` applies the task's edits to files under `tests/` (the failing tests), `code` applies all
other edits of the task (the implementation, catalogues, docs). TDD order is binding: `tests`
first, then RED, then `code`, then GREEN. A `STOP: anchor` message is a hard stop: report it.

**Tests, verbatim, from the worktree root** (the plan writes `…` for the interpreter prefix):

```bash
cd /d/Entwicklung/HASI/issue10-work/wt && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock -q
```

**Known local teardown ERROR (pre-existing, not a defect):** every test that uses the
`coordinator` fixture ends locally with an additional `ERROR at teardown of … Lingering timer
after test` (the coordinator's `_reset_event_fired_today` time listener; all eleven existing
calendar tests are in the baseline that way; upstream CI runs them clean). Read RED and GREEN from
the **call phase**: "failed" / "passed". The number of these teardown ERRORs per run equals the
number of selected fixture tests and does not change between RED and GREEN. An ERROR that is
**not** "at teardown" with "Lingering timer" is real: STOP. Count them with
`grep -c "ERROR at teardown of"` and `grep -c "Lingering timer after test"` on the output.

**Lint, from the worktree root, before every commit** (only these count in CI):

```bash
cd /d/Entwicklung/HASI/issue10-work/wt && uvx black custom_components/irrigation_plus/ tests/test_watering_calendar.py ; uvx ruff check custom_components/irrigation_plus/
```

Expected: black reports every file unchanged (`… files left unchanged`, nothing reformatted) and
ruff `All checks passed!`. The dictated blocks are already black-clean; if black reformats
anything, keep black's output and report it (DONE_WITH_CONCERNS) with the file and lines.

**The full test suite is run by the controller after your commit** (about 6 minutes). Do not run
`pytest tests` yourself, and do not start any other pytest run after your commit.

**No tracker references in anything that goes upstream.** Code, comments, docstrings, test names
and commit messages carry no `Eifel-Joe#…`, no spec or task numbers (`Task 3`, `spec E2`, `A4`),
no plan or branch names. The dictated text is already clean — keep it that way.

**Commits:** exactly the message given in the task, multi-line via heredoc
(`git commit -F - <<'EOF' … EOF`), copied verbatim including the `Co-Authored-By:` trailer as it
stands in the task. Stage files by name (never `git add .` / `-A`). Do not push, do not amend
commits of earlier tasks, do not create branches, do not touch `git stash`.

**Windows traps:**
- The `.py`, `.json`, `.md`, `.yaml`, `.ts` files are CRLF in the working copy
  (`core.autocrlf=true`) and LF in the repository. Git prints "LF will be replaced by CRLF" or
  "CRLF will be replaced by LF" warnings — harmless.
- `grep -c` with no match exits 1 and breaks an `&&` chain; chain checks with `;`.
- Python printing non-ASCII needs `PYTHONIOENCODING=utf-8`.
- pytest prints `±` in approx assertions; your terminal may show it as `�`. Same value.

## Report

Status (DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT), then for every step the command and
the **verbatim last lines** of its output: the script's lines, for RED the summary line plus the
failing test names and their `E ` lines, for GREEN the summary line, the teardown-ERROR counts,
the whole-file runs, the lint output, `git log --oneline -3` and `git show --stat HEAD`. Do not
summarise outputs in your own words where the output itself fits.

## Your task — the plan's text, verbatim

Read it to understand what the edits do and why. The edits themselves are applied by `apply_plan_task.py` (see the ground rules), not typed by you. Where the task text and the run order below differ in how a command is spelled, the run order wins; the expected results are the same.

### Task 2: Die Menge fragt die Regel der Rechnung und skaliert mit Kc

**Files:** Modify `custom_components/irrigation_plus/watering_calendar.py` (Import, `_calculate_monthly_watering_volume`);
Test `tests/test_watering_calendar.py`.

- [ ] **Schritt 1: Die zwei bestehenden Volumen-Tests bekommen ihr Modul ausdrücklich**

Der Mock-Store liefert für jede ID das PyETO-Modul; die Zonen dieser zwei Tests nennen künftig ihr Modul selbst, statt
vom Auffangverhalten des Mocks zu leben. Erwartungen unverändert.

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        test_zone = {
            ZONE_SIZE: 100.0,  # 100 m²
            ZONE_MULTIPLIER: 1.0,
        }
```
**durch:**
```python
        test_zone = {
            ZONE_SIZE: 100.0,  # 100 m²
            ZONE_MULTIPLIER: 1.0,
            ZONE_MODULE: 1,  # PyETO: the module rain is booked for
        }
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
        test_zone = {ZONE_SIZE: 100.0, ZONE_MULTIPLIER: 1.0}
```
**durch:**
```python
        test_zone = {
            ZONE_SIZE: 100.0,
            ZONE_MULTIPLIER: 1.0,
            ZONE_MODULE: 1,  # PyETO: the module rain is booked for
        }
```

- [ ] **Schritt 2: Rote Tests anhängen**

**Hänge an `tests/test_watering_calendar.py` an:**
```python

    @pytest.mark.asyncio
    async def test_kc_scales_the_et_term_and_not_the_rain(self, coordinator):
        """As in the calculation: et_delta = delta x kc, precipitation unscaled."""
        zone = {ZONE_SIZE: 10.0, ZONE_MULTIPLIER: 1.0, ZONE_MODULE: 1, ZONE_KC: 0.5}

        volume = coordinator._calculate_monthly_watering_volume(
            zone, 62.0, {"precipitation": 20.0}
        )

        assert volume == pytest.approx((62.0 * 0.5 - 20.0) * 10.0)  # 110 L

    @pytest.mark.asyncio
    async def test_a_zone_whose_kc_is_none_reads_as_the_default(self, coordinator):
        """A stored ``kc: None`` falls back to 1.0, as in the calculation."""
        zone = {ZONE_SIZE: 10.0, ZONE_MULTIPLIER: 1.0, ZONE_MODULE: 1, ZONE_KC: None}

        volume = coordinator._calculate_monthly_watering_volume(
            zone, 62.0, {"precipitation": 20.0}
        )

        assert volume == pytest.approx((62.0 - 20.0) * 10.0)

    @pytest.mark.asyncio
    async def test_a_module_without_rain_gets_none_subtracted(
        self, coordinator, mock_store
    ):
        """Static and Passthrough book no rain in the calculation, so here neither."""
        mock_store.get_module.return_value = {"id": 1, MODULE_NAME: "Static"}
        zone = {ZONE_SIZE: 10.0, ZONE_MULTIPLIER: 1.0, ZONE_MODULE: 1}

        volume = coordinator._calculate_monthly_watering_volume(
            zone, 93.0, {"precipitation": 60.0}
        )

        assert volume == pytest.approx(930.0)
```

- [ ] **Schritt 3: RED prüfen**

Run: `… -m pytest tests/test_watering_calendar.py -k "kc_scales or kc_is_none or module_without_rain" -p
_local_socket_unblock -q`
Expected: 2 failed (`420.0 == 110.0`, `330.0 == 930.0`), 1 passed (`kc_is_none` ist ein Pin für den `None`-Fall; er
ist schon heute grün, weil Kc noch gar nicht gelesen wird). Dazu 3 teardown-ERRORs.

- [ ] **Schritt 4: Implementierung**

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
from . import const
from .const import SmartIrrigationError
```
**durch:**
```python
from . import const
from .calculation import zone_module_models_weather
from .const import SmartIrrigationError
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        """Calculate monthly watering volume in liters for a zone.

        Args:
            zone: Zone configuration dictionary.
            et_mm: Monthly evapotranspiration in mm.
            month_data: Monthly climate data.

        Returns:
            float: Watering volume in liters.

        """
        zone_size_m2 = zone.get(const.ZONE_SIZE, 1.0)  # Default 1 m²
        multiplier = zone.get(const.ZONE_MULTIPLIER, 1.0)
        precipitation_mm = month_data.get("precipitation", 0.0)
```
**durch:**
```python
        """Calculate monthly watering volume in liters for a zone.

        A day of the calculation, summed over the month: the zone's Kc scales the
        ET term and not the rain, and rain counts only for a module the
        calculation books it for (``zone_module_models_weather``, the question
        the calculation itself asks).

        Args:
            zone: Zone configuration dictionary.
            et_mm: Monthly evapotranspiration in mm, before the zone's Kc.
            month_data: Monthly climate data.

        Returns:
            float: Watering volume in liters.

        """
        zone_size_m2 = zone.get(const.ZONE_SIZE, 1.0)  # Default 1 m²
        multiplier = zone.get(const.ZONE_MULTIPLIER, 1.0)
        kc = zone.get(const.ZONE_KC, const.CONF_DEFAULT_KC)
        if kc is None:
            kc = const.CONF_DEFAULT_KC
        if zone_module_models_weather(self.store, zone):
            precipitation_mm = month_data.get("precipitation", 0.0)
        else:
            # Static and Passthrough hand back a number the install supplied; the
            # calculation books no rain for them, so neither does the projection.
            precipitation_mm = 0.0
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        net_water_need_mm = max(0, et_mm - precipitation_mm)
```
**durch:**
```python
        net_water_need_mm = max(0, et_mm * kc - precipitation_mm)
```

- [ ] **Schritt 5: GREEN prüfen**

Run: wie Schritt 3. Expected: 3 passed (+ 3 teardown-ERRORs). Dann die ganze Datei → kein „failed“.

- [ ] **Schritt 6: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_watering_calendar.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/watering_calendar.py tests/test_watering_calendar.py
git commit -F - <<'EOF'
fix(calendar): the seasonal volume follows the calculation's rain and Kc

The calculation books rain only for a module that models weather (PyETO)
and scales the ET term, not the rain, by the zone's crop coefficient.
The seasonal volume subtracted rain for every module and never read Kc.
It now asks zone_module_models_weather, the question the calculation and
the live estimate already ask, and applies Kc like the calculation does.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

## Run order (binding)

1. **Precondition:** `git -C /d/Entwicklung/HASI/issue10-work/wt status --porcelain` prints nothing and `git -C /d/Entwicklung/HASI/issue10-work/wt rev-list --count bbf2e151..HEAD` prints `1`. Otherwise STOP.
2. **Failing tests:** `cd /d/Entwicklung/HASI/issue10-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe apply_plan_task.py 2 tests`
3. **RED:** `cd /d/Entwicklung/HASI/issue10-work/wt && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_watering_calendar.py -k "kc_scales or kc_is_none or module_without_rain" -p _local_socket_unblock -q` — expected `2 failed, 1 passed, 13 deselected, 3 errors` (see below).
4. **Implementation:** `cd /d/Entwicklung/HASI/issue10-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe apply_plan_task.py 2 code`
5. **GREEN:** the RED command again — expected `3 passed, 13 deselected, 3 errors`.
6. **Whole files:** `cd /d/Entwicklung/HASI/issue10-work/wt && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_watering_calendar.py tests/test_watering_calendar_api.py tests/test_i18n_completeness.py -p _local_socket_unblock -q` — no `failed`, every ERROR a teardown `Lingering timer` one.
7. **Lint:** the lint command from the ground rules.
8. **Stage and commit:** the task's `git add` line(s) (from the worktree root), then the count check if the task gives one, then the task's `git commit -F - <<'EOF' … EOF` verbatim.
9. **Report** as described in the ground rules. Do not run anything after the commit.

## Measured in the dry run

- RED (measured): `2 failed, 1 passed, 13 deselected, 3 errors`; teardown ERRORs = the `errors` count, each `Lingering timer`.
- RED `E ` lines (measured):
  - `E   assert 420.0 == 110.0 ± 1.1e-04`
  - `E   assert 330.0 == 930.0 ± 9.3e-04`
- GREEN (measured): `3 passed, 13 deselected, 3 errors`.
- Whole files, the three-file run (measured): `87 passed, 16 errors`. The calendar file alone would read `16 passed, 16 errors` (computed).
