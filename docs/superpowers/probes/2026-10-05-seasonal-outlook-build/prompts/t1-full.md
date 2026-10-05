# Task 1: Die PyETO-ET enthält keinen Regen

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

### Task 1: Die PyETO-ET enthält keinen Regen

**Files:** Modify `custom_components/irrigation_plus/watering_calendar.py` (Docstring, Imports,
`_calculate_monthly_et_pyeto`); Test `tests/test_watering_calendar.py`.

- [ ] **Schritt 1: Imports und Hilfen der Testdatei**

**Ersetze in `tests/test_watering_calendar.py`:**
```python
from datetime import date
from unittest.mock import AsyncMock, Mock, patch
```
**durch:**
```python
import json
import math
import pathlib
from datetime import date
from unittest.mock import AsyncMock, Mock, patch
```

**Ersetze in `tests/test_watering_calendar.py`:**
```python
    ZONE_ID,
    ZONE_MAPPING,
```
**durch:**
```python
    ZONE_ID,
    ZONE_KC,
    ZONE_MAPPING,
```

- [ ] **Schritt 2: Die zwei roten Tests anhängen**

**Hänge an `tests/test_watering_calendar.py` an:**
```python


_ROOT = pathlib.Path(__file__).parent.parent / "custom_components" / "irrigation_plus"

# Weather for the PyETO helper; only the mocked equation reads it.
_JULY_WEATHER = {
    "avg_temp": 25.0,
    "min_temp": 15.0,
    "max_temp": 35.0,
    "precipitation": 50.0,
    "humidity": 65.0,
    "wind_speed": 3.0,
    "pressure": 1013.25,
    "dewpoint": 18.0,
}


def _module_instance(name, **attrs):
    """A calculation-module instance as the calendar sees it: a name and its call."""
    module = Mock()
    module.name = name
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


class TestAMonthIsPricedByTheCalculationsRules:
    """The projection prices a month the way the calculation prices its days.

    Only PyETO books rain, Kc scales the ET term and not the rain, and a
    module's daily figure is scaled by the days of the month.
    """

    @pytest.mark.asyncio
    async def test_a_pyeto_month_carries_no_rain(self, coordinator, mock_pyeto_module):
        """The equation returns -ET0 with no rain in it; the month is ET0 x days.

        Adding the month's rain to it showed rain as ET, and subtracting it again
        later left the volume blind to rain.
        """
        mock_pyeto_module.calculate_et_for_day = Mock(return_value=-2.0)

        july = coordinator._calculate_monthly_et_pyeto(
            _JULY_WEATHER, mock_pyeto_module, 7
        )

        assert july == pytest.approx(62.0)  # 2.0 mm x 31 days

    @pytest.mark.asyncio
    async def test_a_pyeto_zone_has_the_rain_subtracted_once(
        self, coordinator, mock_pyeto_module
    ):
        """Through the whole calendar: ET without rain, the volume net of it once."""
        mock_pyeto_module.calculate_et_for_day = Mock(return_value=-2.0)

        with patch.object(
            coordinator,
            "getModuleInstanceByID",
            new=AsyncMock(return_value=mock_pyeto_module),
        ):
            calendar_data = await coordinator.async_generate_watering_calendar(
                zone_id=1
            )

        july = calendar_data[1]["monthly_estimates"][6]
        rain = july["average_precipitation_mm"]
        assert july["estimated_et_mm"] == pytest.approx(62.0)
        # The fixture zone: 100 m2, multiplier 1, no Kc (reads as 1.0).
        assert july["estimated_watering_volume_liters"] == pytest.approx(
            round(max(0.0, 62.0 - rain) * 100.0, 1)
        )
```

- [ ] **Schritt 3: RED prüfen**

Run: `… -m pytest tests/test_watering_calendar.py -k "carries_no_rain or subtracted_once" -p _local_socket_unblock -q`
Expected: 2 failed — `assert 112.0 == 62.0 ± …` und `assert 122.0 == 62.0 ± …` (heute steckt der Monatsregen in der ET). Dazu 2 teardown-ERRORs.

- [ ] **Schritt 4: Implementierung**

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
elevation). Named watering_calendar (not calendar) to avoid shadowing the stdlib
``calendar`` module, which _calculate_monthly_et_pyeto imports locally.
"""

import logging
```
**durch:**
```python
elevation). Named watering_calendar (not calendar) to avoid shadowing the stdlib
``calendar`` module, which this module imports.
"""

import calendar
import logging
```

**Ersetze in `custom_components/irrigation_plus/watering_calendar.py`:**
```python
        # Get days in month
        import calendar

        days_in_month = calendar.monthrange(2024, month)[
            1
        ]  # Use 2024 as reference year

        # Convert daily ET delta to monthly total (remove precipitation since we want just ET)
        daily_et = abs(daily_et_delta) + month_data["precipitation"] / days_in_month
        return daily_et * days_in_month
```
**durch:**
```python
        days_in_month = calendar.monthrange(2024, month)[1]  # 2024: reference year

        # The delta is -ET0 with no precipitation in it (calculate_et_for_day
        # returns ``-eto``), so the month's ET is its size times the days. Rain is
        # subtracted once, in the volume, and only where the calculation books it.
        return abs(daily_et_delta) * days_in_month
```

- [ ] **Schritt 5: GREEN prüfen**

Run: wie Schritt 3. Expected: 2 passed (+ 2 teardown-ERRORs). Dann `… -m pytest tests/test_watering_calendar.py -p
_local_socket_unblock -q` → kein „failed“.

- [ ] **Schritt 6: Lint und Commit**

```bash
uvx black custom_components/irrigation_plus/ tests/test_watering_calendar.py
uvx ruff check custom_components/irrigation_plus/
git add custom_components/irrigation_plus/watering_calendar.py tests/test_watering_calendar.py
git commit -F - <<'EOF'
fix(calendar): the seasonal ET carries no rain

calculate_et_for_day returns -ET0 with no precipitation in it. The PyETO
branch nevertheless added the month's rain to the ET and the volume
subtracted it again, so the seasonal outlook showed rain as evaporation
and the watering volume never went down for rain.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

## Run order (binding)

1. **Precondition:** `git -C /d/Entwicklung/HASI/issue10-work/wt status --porcelain` prints nothing and `git -C /d/Entwicklung/HASI/issue10-work/wt rev-list --count bbf2e151..HEAD` prints `0`. Otherwise STOP.
2. **Failing tests:** `cd /d/Entwicklung/HASI/issue10-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe apply_plan_task.py 1 tests`
3. **RED:** `cd /d/Entwicklung/HASI/issue10-work/wt && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_watering_calendar.py -k "carries_no_rain or subtracted_once" -p _local_socket_unblock -q` — expected `2 failed, 11 deselected, 2 errors` (see below).
4. **Implementation:** `cd /d/Entwicklung/HASI/issue10-work && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe apply_plan_task.py 1 code`
5. **GREEN:** the RED command again — expected `2 passed, 11 deselected, 2 errors`.
6. **Whole files:** `cd /d/Entwicklung/HASI/issue10-work/wt && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_watering_calendar.py tests/test_watering_calendar_api.py tests/test_i18n_completeness.py -p _local_socket_unblock -q` — no `failed`, every ERROR a teardown `Lingering timer` one.
7. **Lint:** the lint command from the ground rules.
8. **Stage and commit:** the task's `git add` line(s) (from the worktree root), then the count check if the task gives one, then the task's `git commit -F - <<'EOF' … EOF` verbatim.
9. **Report** as described in the ground rules. Do not run anything after the commit.

## Measured in the dry run

- RED (measured): `2 failed, 11 deselected, 2 errors`; teardown ERRORs = the `errors` count, each `Lingering timer`.
- RED `E ` lines (measured):
  - `E   assert 112.0 == 62.0 ± 6.2e-05`
  - `E   assert 122.0 == 62.0 ± 6.2e-05`
- GREEN (measured): `2 passed, 11 deselected, 2 errors`.
- Whole files, the three-file run (measured): `84 passed, 13 errors`. The calendar file alone would read `13 passed, 13 errors` (computed).
