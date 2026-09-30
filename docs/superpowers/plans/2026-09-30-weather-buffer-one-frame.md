# The weather buffer on one clock (variant B) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every weather-buffer stamp is written, stored and compared naive on Home
Assistant's clock, and a store an older release left behind is moved onto that clock once —
keyed on the storage **minor** version (14.1 → 14.2), so that a rolled-back release still
opens the file.

**Architecture:** One helper, `local_naive_now()`, replaces the bare process clock at the 19
sites that write or compare the five stamps. `coerce_stamp` reads an aware stamp on HA's
clock under both provenances. `MigratableStore` gets Home Assistant's three-argument migrate
hook: the unchanged major steps (renamed `_async_migrate_major`), then — below 14.2 — one pass
over the five stamps (naive → process zone at its own date's offset → HA-local; string in,
string out). `_process_timezone()` becomes `dateutil.tz.tzlocal()` and keeps one caller, the
migration. Design: `docs/superpowers/specs/2026-09-28-weather-buffer-one-frame-design.md`
(Revision 4 with its Addendum 2026-09-30, which wins) on `archive/design-history`.

**Tech Stack:** Python 3.12 locally / 3.13 on CI, Home Assistant custom component, pytest +
pytest-homeassistant-custom-component, freezegun, python-dateutil (already a manifest
requirement), `black`, `ruff`.

---

## This plan was run once before it was handed over

On 2026-09-30 Tasks 1–8 were applied to a throwaway worktree on `0b9a71bd`
(`D:\Entwicklung\HASI\issue22-work\probe-wt`, branch `probe/weather-buffer-one-frame`, removed
afterwards) — every code block taken from this file by script
(`…\probe\plan_blocks.py`, `…\probe\apply_task.py`, archived as
`docs/superpowers/probes/2026-09-30-weather-buffer-apply-*.py`), each RED and GREEN step
measured, then the full suite and the mutation matrix. Before that, an impact probe (every
production change, nothing else) measured how the existing suite reacts. Where the plan did
not hold, it was corrected in place; **"Findings of the dry run"** at the end says what and why.
The numbers, so a deviation shows at once:

| check | on `0b9a71bd` | with the change |
|---|---|---|
| impact probe: production changes only | 7 failed / 3466 passed | 16 failed / 3457 passed — 9 tests react: 3 pins to turn round, 6 expectations on the process clock (Tasks 3, 5) |
| Task 1's file | 12 failed, the matrix as offsets (daily rows 10.5–12.5, live 5.0 h), six writers at 10:00, clamp 814.5 W/m², census 20 sites | 12 passed (Task 5) |
| Task 2 | 1 failed (`local_naive_now`); the process-zone test red only with a DST zone | 8 passed; 1 passed without `TZ=UTC` |
| Task 3 | 6 failed / 40 passed | 46 passed |
| Task 4 | collection error (`STORAGE_MINOR_VERSION`) | 184 passed |
| Task 5 | 15 failed | 15 passed; neighbours 182 passed + the 12 baseline teardown errors |
| Task 6 grep | — | only lines about the past or the migration, and `generated_at` |
| `black` / `ruff` | — | clean after every task; `black` never reformatted plan code |
| tracker greps | — | empty |
| full suite, `TZ=UTC` | 7 / 3466 / 9 / 367, 374 names | 7 / 3489 / 9 / 367, the same 374 names; +23 = the new tests |
| diff against `upstream/master` | — | 28 files, +1194 / −345 (production and docs +252 / −226, tests +942 / −119) |
| mutation matrix | — | 33 of 33 killed, every source restored; 15 of the 19 clock sites also by a behavioural test, the census alone only for the four defaults no in-repo caller reaches |

Evidence kept outside the repo: `D:\Entwicklung\HASI\issue22-work\measure\` (impact run,
per-task red/green, both full runs, both mutation runs) and `…\probe\` (the scripts, the
pre-run diff, `mutations-result.json`).

---

## Ground rules for every task

**Worktree:** `D:\Entwicklung\HASI\issue22-work\wt`, branch `fix/weather-buffer-one-frame` from
`upstream/master` (Task 0 creates both). There is no `.venv` in it; the interpreter is named
absolutely. Scratch output goes to `D:\Entwicklung\HASI\issue22-work\` — never to `C:`.

**Commands, verbatim.** Backend tests, from the worktree root:

```bash
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock -q --no-header
```

Lint for CI, from the worktree root (only these two count, only on this path), **in every
task before its commit**:

```bash
uvx black custom_components/irrigation_plus/ ; uvx ruff check custom_components/irrigation_plus/
```

**Always under `TZ=UTC`** — the one exception is named in Task 2. Every test in this repo runs
with the `hass` fixture (`tests/conftest.py:56` pulls it in through
`enable_custom_integrations`), which puts HA on **US/Pacific**; CI's process runs at UTC; this
machine runs Europe/Berlin. A run without `TZ=UTC` is not comparable to the baseline. Under
freezegun a bare `datetime.now()` returns the frozen instant as UTC wall time whatever the
machine's zone, and `dt_util.now()` returns it in HA's zone.

**No tracker references in anything that goes upstream.** Code, comments, docstrings, test
names and commit messages carry no `Eifel-Joe#…`, no `#22`, no `Rev 4`, no `R4-…`, no
`A1`…`A8`, no `spec`, no `Task N`, no inventory IDs (`F-01`, `M3`, `B-12`). Upstream's own
numbers are fine, as elsewhere in the code (`calculation.py:1195` already names `#160`). This
plan and the design doc may name ours; nothing under `custom_components/`, `tests/` or
`docs/*.md` may. Task 7 greps for it.

**Every task that changes a file ends on a commit** — except Task 1, whose tests go in with
the task that turns them green. Stage by name (never `git add .`/`-A`). Multi-line messages via heredoc
(`git commit -F - <<'EOF'`), never PowerShell. Last line:
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

**Comments follow the skill `code-doku`:** for the migration step, `local_naive_now` and
`coerce_stamp` the root cause (`Wurzel:`), the fix, the rejected alternative (`NOT-TO-DO:`) and
the pinning test (`siehe …`), as the surrounding code already does. A comment the change makes
false is rewritten, not appended to.

**Windows traps that have cost time before:**
- The working copy is **CRLF** (`core.autocrlf=true`), the repository LF. The Edit tool keeps a
  file's endings; a script that writes files must read and write bytes and keep them, or
  `git diff` reports every line.
- `grep -c` with no match exits 1 and breaks an `&&` chain. Chain checks with `;`.
- No `nohup … &` for suite runs: use the tool's background mode, and before any verdict check
  that the run collected tests (its summary line exists and is not `0 passed`). Read a result
  file only after the run has ended — a `diff` on a growing file reports phantom regressions.
- `$?` behind `$(…)` on the same line is the substitution's status, not the command's.
- The FAILED/ERROR filter must require `tests/`: `grep -E "^(FAILED|ERROR) tests/"` — log lines
  start with `ERROR ` too.

---

## File structure

| File | Responsibility | Change |
|---|---|---|
| `custom_components/irrigation_plus/helpers.py` | stamp helpers | `local_naive_now()`, `lift_legacy_stamp()`; `_process_timezone()` → `tzlocal()`; `coerce_stamp`'s aware branch on HA's clock; the comment on the two provenances |
| `custom_components/irrigation_plus/store.py` | the store | `STORAGE_MINOR_VERSION = 2`; `_lift_legacy_stamps()`; `MigratableStore`: the three-argument hook and `_async_migrate_major`; `minor_version=` where the store is built; the writer at `:1653`; the comment at `:1984-1988` |
| `custom_components/irrigation_plus/calculation.py` | daily calculation | 5 clock sites; docstring `:47-55`, comments `:776-802`, `:1193-1197` |
| `custom_components/irrigation_plus/continuous_update.py` | event ingest | 3 clock sites; comment `:375-377` |
| `custom_components/irrigation_plus/__init__.py` | coordinator | 7 clock sites (the solar clamp among them); the `dt_datetime` alias and its note go; comment `:2019-2024` |
| `custom_components/irrigation_plus/weather_aggregate.py` | aggregation | 3 `now` defaults and the comment above each; `_parse` docstring |
| `custom_components/irrigation_plus/live_estimate.py` | live estimate | `_parse_stored_as_ha_local` docstring |
| `custom_components/irrigation_plus/auto_calc.py`, `sensor.py`, `const.py` | — | one comment each |
| `docs/usage-troubleshooting.md`, `docs/installation-download.md` | user docs | the container-`TZ` note, which this change makes false |
| `tests/test_weather_buffer_one_frame.py` | **new**: the end-to-end matrix, the solar clamp, the clock census | Task 1 |
| `tests/test_store_stamp_migration.py` | **new**: the migration, and the two-argument path | Task 4 |
| `tests/test_time_provenance.py`, `tests/test_live_estimate_time_provenance.py`, `tests/test_weather_aggregate.py` | provenance pins | two new tests, three inverted, twins built in HA's zone (Tasks 2, 3) |
| `tests/test_continuous_update.py`, `tests/test_store_operations.py`, `tests/test_zone_view_save.py` | writer expectations | the stamp expected on HA's clock (Task 5) |
| 8 test files that call the migrate function directly | major-step tests | `_async_migrate_func` → `_async_migrate_major` (Task 4) |

## Scope — checked while planning, nothing to change

Read on `0b9a71bd`. Every line number in this plan is that commit's; they differ from
Revision 4's `1876aa03` only in `store.py` ≥ 1681 (+4), `__init__.py` ≥ 2008 (+2) and
`websockets.py` ≥ 381 (spec Addendum A6).

| path | why it needs nothing |
|---|---|
| `live_estimate.py:264/:275`, `:1293`, `:1731`; `auto_calc.py:96-98` | already HA's clock, naive |
| `pending_bucket_events` (`calculation.py:47-72`) | flattens the aware ledger to HA-local; after this the window it is placed on is HA-local too (only its docstring changes, Task 6) |
| the readers `calculation.py:331/:398/:808/:865/:975/:1116`, `store.py:1925/:1989`, `live_estimate.py:246/:249`, `auto_calc.py:135` | unchanged by design: after the migration they compare HA-local with HA-local |
| `sensor._to_aware_datetime`, `websockets._safe_parse_datetime`, the frontend | display; consistent by themselves once the store is HA-local |
| `weathermodules/*.py` (TTLs), `services.py:273/:289`, `watering_calendar.py:79/:93` (`generated_at`) | in-process or display only; not one of the five stamps |
| `migrate_domain.py:547` | copies an old file's bytes; the version-based migration covers it |
| comments `websockets.py:66/:73`, `live_estimate.py:1188-1190/:1406-1411/:1435-1436` | still true: they describe an aware→UTC branch, or "naive local", which HA's clock is |

If `upstream/master` has moved when this plan is executed, re-read this table and every anchor
below before relying on them.

---

## Task 0: Worktree, base, baseline

- [ ] **Step 1: Confirm the base**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && git fetch upstream && git rev-parse --short=8 upstream/master
```

Expected: `0b9a71bd`. If it is anything else, **stop**: the baseline and every line number in
this plan are that commit's. Diff the backend against it (`git diff --stat 0b9a71bd upstream/master
-- custom_components/irrigation_plus/`), re-read the anchors of the files that moved, and
re-measure the baseline (Step 5, second command).

- [ ] **Step 2: Retire the Revision-3 worktree**

`issue22-work\wt` holds branch `fix/weather-buffer-aware-writers` at `1876aa03` — never pushed,
no commit of its own, only untracked copies of the design docs. Moved, not deleted:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && git -C /d/Entwicklung/HASI/issue22-work/wt status --short ; git worktree move /d/Entwicklung/HASI/issue22-work/wt /d/Entwicklung/HASI/_erledigt/issue22-wt-rev3 ; git worktree list | grep issue22
```

Expected: the status lists only `?? docs/superpowers/`; afterwards the worktree list shows
`_erledigt/issue22-wt-rev3` and no `issue22-work/wt`.

- [ ] **Step 3: Create the worktree and the socket plugin**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && git worktree add -b fix/weather-buffer-one-frame /d/Entwicklung/HASI/issue22-work/wt upstream/master ; git -C /d/Entwicklung/HASI/issue22-work/wt branch --unset-upstream ; cp _local_socket_unblock.py /d/Entwicklung/HASI/issue22-work/wt/ ; git -C /d/Entwicklung/HASI/issue22-work/wt status -sb | head -1
```

Expected: `## fix/weather-buffer-one-frame` with no `...upstream/master` after it —
`worktree add -b … upstream/master` sets the tracking to upstream, and `--unset-upstream`
takes it off before anything can be pushed there.

- [ ] **Step 4: Confirm pytest imports this worktree's code**

```bash
cp /d/Entwicklung/HASI/issue66-work/probe_import_origin.py /d/Entwicklung/HASI/issue22-work/ ; cd /d/Entwicklung/HASI/issue22-work/wt && PYTHONPATH=/d/Entwicklung/HASI/issue22-work TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_time_provenance.py --co -q -p probe_import_origin -p _local_socket_unblock | grep IMPORT-ORIGIN
```

Expected: both lines point into `D:\Entwicklung\HASI\issue22-work\wt\custom_components`.

- [ ] **Step 5: The baseline**

Measured on `0b9a71bd` under `TZ=UTC` on 2026-09-29: `7 failed, 3466 passed, 9 skipped, 367
errors`, 374 FAILED/ERROR names. If Step 1 read `0b9a71bd`, reuse it:

```bash
mkdir -p /d/Entwicklung/HASI/issue22-work/measure /d/Entwicklung/HASI/issue22-work/tmp ; cp /d/Entwicklung/HASI/issue66-work/measure/baseline-0b9a71bd-tzutc.txt /d/Entwicklung/HASI/issue66-work/measure/baseline-names.txt /d/Entwicklung/HASI/issue22-work/measure/ ; wc -l < /d/Entwicklung/HASI/issue22-work/measure/baseline-names.txt
```

Expected: `374`. Only if the base moved, measure it instead — in the background (tool option),
reading the file only after the run has ended:

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && export TEMP=D:/Entwicklung/HASI/issue22-work/tmp TMP=D:/Entwicklung/HASI/issue22-work/tmp TMPDIR=D:/Entwicklung/HASI/issue22-work/tmp ; TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header > /d/Entwicklung/HASI/issue22-work/measure/baseline-tzutc.txt 2>&1 ; grep -E "^(FAILED|ERROR) tests/" /d/Entwicklung/HASI/issue22-work/measure/baseline-tzutc.txt | sed 's/ - .*//' | sort -u > /d/Entwicklung/HASI/issue22-work/measure/baseline-names.txt
```

No commit: nothing has changed.

---

## Task 1: The criterion, as tests that fail today

**Files:**
- Create: `tests/test_weather_buffer_one_frame.py`

The end-to-end matrix — daily and live path × a store an older release left and a store this
release's writers filled, exact values — plus every writer the matrix does not reach, driven
once (its stamp must read HA's wall clock), the solar clamp, and a census of the process clock
in the six modules that write or compare the stamps. On the base all twelve fail, and the four
matrix cells fail **as offsets**, not as errors.

- [ ] **Step 1: Write the test file**

`tests/test_weather_buffer_one_frame.py`:

```python
"""One clock for the weather buffer, on the daily and the live path.

The scene is the install where the clock matters: the Home Assistant process runs at
UTC (a container started without ``TZ=``) and the user has set Europe/Berlin. The zone
was last calculated at 10:00 UTC -- 12:00 on the user's clock. Readings came in at
09:55, 11:00, 12:00 and 13:00 UTC, and it is now 13:00 UTC, 15:00 in Berlin. Three real
hours have passed, and the hours they cover are the user's 12:00-15:00.

Whichever path reads the buffer, and whichever release wrote it, it has to show a
window of exactly 3.0 h, hourly rows for the hours that start at 12:00, 13:00 and 14:00,
and the site's own offset, +2.0, on them. The daily path had the window right before
this change and the hours wrong: it measured the window on one clock, the process's, and
then priced the hours as if that clock were the user's. That is the half that moves the
solar radiation, and why the row hours are asserted everywhere, not the window alone.

Three hours, not one: the window length is ``abs(now - watermark)``, and with one hour
and a two-hour offset a process-clock ``now`` against a migrated watermark comes out at
|11:00 - 12:00| = 1 h -- the right answer for the wrong reason.

Two stores: one a release before 14.2 left on disk (process-local stamps, through the
real load and with it the store migration), and one this release's own writers filled,
clock read by clock read.

The process zone is substituted rather than set, because ``time.tzset()`` does not
exist on Windows. Under freezegun a bare ``datetime.now()`` reads the frozen instant as
UTC wall time whatever the machine's zone -- the container this scene needs.
"""

import ast
import datetime
import pathlib
import zoneinfo
from unittest.mock import AsyncMock, Mock

import pytest
from freezegun import freeze_time
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.irrigation_plus import (
    SmartIrrigationCoordinator,
    calculation,
    const,
    helpers,
    live_estimate,
)
from custom_components.irrigation_plus.et_estimate import SiteGeometry
from custom_components.irrigation_plus.store import STORAGE_KEY, SmartIrrigationStorage

UTC = datetime.UTC
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")
LAT, LON, ELEV = 50.0, 6.0, 200.0

# The user's 12:00-15:00, and nothing else: (row hour, row UTC offset) per hour.
EXPECTED_WINDOW_H = 3.0
EXPECTED_ROWS = [(12.5, 2.0), (13.5, 2.0), (14.5, 2.0)]

# A sensor group of fixed values: the poll writes a full row from it with no weather
# service and no entity state, and it carries the four fields the hourly form needs.
STATIC_GROUP = {
    field: {
        const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_STATIC_VALUE,
        const.MAPPING_CONF_STATIC_VALUE: value,
    }
    for field, value in (
        (const.MAPPING_TEMPERATURE, 20.0),
        (const.MAPPING_HUMIDITY, 50.0),
        (const.MAPPING_WINDSPEED, 2.0),
        (const.MAPPING_SOLRAD, 2.5),
    )
}

PACKAGE = (
    pathlib.Path(__file__).resolve().parent.parent / "custom_components" / "irrigation_plus"
)


@pytest.fixture
def utc_container_berlin_user(monkeypatch):
    """The process at UTC, Home Assistant at Europe/Berlin."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    before = dt_util.get_default_time_zone()
    dt_util.set_default_time_zone(BERLIN)
    yield
    dt_util.set_default_time_zone(before)


@pytest.fixture
async def coordinators(hass):
    """Every coordinator a test builds, released at teardown.

    The constructor arms the midnight counter; left armed, the test ends on a
    lingering timer.
    """
    built = []
    yield built
    for c in built:
        c._track_midnight_time_unsub()


async def _coordinator(hass, store, built):
    """A real coordinator over a real store, on a site with coordinates."""
    hass.data[const.DOMAIN] = {
        const.CONF_USE_WEATHER_SERVICE: False,
        const.CONF_WEATHER_SERVICE: None,
    }
    hass.config.units = METRIC_SYSTEM
    hass.config.language = "en"
    entry = Mock()
    entry.unique_id = "t"
    entry.data = {}
    entry.options = {}
    c = SmartIrrigationCoordinator(hass, None, entry, store)
    built.append(c)
    c.store = store
    c._effective_latitude = LAT
    c._effective_longitude = LON
    c._effective_elevation = ELEV
    # Measured radiation and no forecast days: the configuration the hourly form
    # prices, on both paths.
    module = Mock()
    module.name = "PyETO"
    module._solrad_behavior = "3"
    module.forecast_days = 0
    module.calculate = Mock(return_value=0.0)
    c.getModuleInstanceByID = AsyncMock(return_value=module)
    # The published estimate is not what this file measures.
    c.async_refresh_zone_estimates = AsyncMock()
    c.async_refresh_zone_estimates_throttled = AsyncMock()
    return c


async def _new_store(hass):
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    await store.async_update_config({const.CONF_HOURLY_CALCULATION: True})
    return store


async def _add_zone(store):
    """A sensor group of fixed values, a PyETO module on it, and a zone on both."""
    mapping = await store.async_create_mapping(
        {
            const.MAPPING_NAME: "Static",
            const.MAPPING_MAPPINGS: STATIC_GROUP,
            const.MAPPING_DATA: [],
        }
    )
    module = await store.async_create_module(
        {
            const.MODULE_NAME: "PyETO",
            "description": "",
            "config": {
                const.CONF_PYETO_SOLRAD_BEHAVIOR: "3",
                const.CONF_PYETO_FORECAST_DAYS: 0,
            },
        }
    )
    zone = await store.async_create_zone(
        {
            const.ZONE_NAME: "Front",
            const.ZONE_MAPPING: mapping[const.MAPPING_ID],
            const.ZONE_MODULE: module[const.MODULE_ID],
            const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
            const.ZONE_BUCKET: 0.0,
            const.ZONE_THROUGHPUT: 10.0,
            const.ZONE_SIZE: 10.0,
            const.ZONE_MULTIPLIER: 1.0,
            const.ZONE_MAXIMUM_DURATION: 3600,
            const.ZONE_LEAD_TIME: 0,
        }
    )
    return zone[const.ZONE_ID]


def _row(stamp):
    return {
        const.RETRIEVED_AT: stamp,
        **{field: cfg[const.MAPPING_CONF_STATIC_VALUE] for field, cfg in STATIC_GROUP.items()},
    }


async def _store_from_an_older_release(hass, hass_storage, built):
    """The zone as a release before 14.2 left it on disk, loaded the way setup loads it.

    Written through this code's own API and save, then given what such a release wrote:
    minor version 1 and every one of the five stamps on the process's clock (UTC here).
    """
    first = await _new_store(hass)
    zone_id = await _add_zone(first)
    await first.async_save()
    document = hass_storage[STORAGE_KEY]
    document["minor_version"] = 1
    for zone in document["data"]["zones"]:
        for key in (
            const.ZONE_LAST_CALCULATED,
            const.ZONE_LAST_CONSUMED,
            const.ZONE_LAST_UPDATED,
        ):
            zone[key] = "2026-07-15T10:00:00"
    for mapping in document["data"]["mappings"]:
        mapping[const.MAPPING_DATA] = [
            _row("2026-07-15T09:55:00"),
            _row("2026-07-15T11:00:00"),
            _row("2026-07-15T12:00:00"),
            _row("2026-07-15T13:00:00"),
        ]
        mapping[const.MAPPING_DATA_LAST_UPDATED] = "2026-07-15T13:00:00"
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    return await _coordinator(hass, store, built), store, zone_id


async def _store_this_release_wrote(hass, frozen, built):
    """The zone as this release's writers leave it, each stamp from its own clock read."""
    store = await _new_store(hass)
    c = await _coordinator(hass, store, built)
    frozen.move_to("2026-07-15 09:50:00")
    zone_id = await _add_zone(store)  # anchors last_consumed_at
    frozen.move_to("2026-07-15 09:55:00")
    await c._async_update_all()  # the poll stamps a row
    frozen.move_to("2026-07-15 10:00:00")
    await c._async_calculate_all()  # the calculation stamps the zone
    for hour in ("11:00", "12:00", "13:00"):
        frozen.move_to(f"2026-07-15 {hour}:00")
        await c._async_update_all()
    return c, store, zone_id


async def _daily(c, zone_id, monkeypatch):
    """The daily calculation's window and hourly rows, read off its own calls.

    Called without ``now``, so it reads its own clock the way the scheduled
    calculation does.
    """
    windows, rows = [], []
    aggregate_window = calculation.aggregate_window
    hourly_eto_priced = calculation.hourly_eto_priced

    def aggregate_spy(*args, **kwargs):
        out = aggregate_window(*args, **kwargs)
        windows.append(out[const.MAPPING_DATA_MULTIPLIER] * 24 if out else None)
        return out

    def priced_spy(*args, **kwargs):
        out = hourly_eto_priced(*args, **kwargs)
        rows.append([(r["hour"], r["tz_offset_h"]) for r in out[0]] if out else None)
        return out

    monkeypatch.setattr(calculation, "aggregate_window", aggregate_spy)
    monkeypatch.setattr(calculation, "hourly_eto_priced", priced_spy)
    await c.async_calculate_zone(zone_id)
    return windows, rows


def _window_h(aggregated):
    return aggregated[const.MAPPING_DATA_MULTIPLIER] * 24 if aggregated else None


def _live(c, zone, monkeypatch):
    """The live estimate's windows and hourly rows, through the functions that read the store.

    ``now`` is built the way the live refresh builds it (HA's clock, naive), which was
    right before this change; the anchor the store yields is what is under test. The
    second window is the call without ``now`` that ``_observed_precip_since_mm`` makes,
    which falls back on the aggregation's own default clock.
    """
    rows = []
    hourly_eto_priced = live_estimate.hourly_eto_priced

    def priced_spy(*args, **kwargs):
        out = hourly_eto_priced(*args, **kwargs)
        rows.append([(r["hour"], r["tz_offset_h"]) for r in out[0]] if out else None)
        return out

    monkeypatch.setattr(live_estimate, "hourly_eto_priced", priced_spy)
    anchor = live_estimate._window_anchor(zone)
    now_local = helpers.coerce_stamp(dt_util.now(), helpers.STAMP_FROM_CLIENT)
    window = _window_h(c._aggregate_live_window(zone, anchor, now=now_local))
    default_clock_window = _window_h(c._aggregate_live_window(zone, anchor))
    c._buffer_hourly_et(
        zone, anchor, now=now_local, geometry=SiteGeometry(LAT, LON, ELEV, 2.0, BERLIN)
    )
    return window, default_clock_window, rows


class TestTheDailyPath:
    async def test_a_store_an_older_release_left(
        self, hass, hass_storage, coordinators, monkeypatch, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 13:00:00"):
            c, _, zone_id = await _store_from_an_older_release(
                hass, hass_storage, coordinators
            )
            windows, rows = await _daily(c, zone_id, monkeypatch)
        assert windows == [pytest.approx(EXPECTED_WINDOW_H)]
        assert rows == [EXPECTED_ROWS]

    async def test_a_store_this_release_wrote(
        self, hass, coordinators, monkeypatch, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 09:50:00") as frozen:
            c, _, zone_id = await _store_this_release_wrote(hass, frozen, coordinators)
            windows, rows = await _daily(c, zone_id, monkeypatch)
        assert windows == [pytest.approx(EXPECTED_WINDOW_H)]
        assert rows == [EXPECTED_ROWS]


class TestTheLivePath:
    async def test_a_store_an_older_release_left(
        self, hass, hass_storage, coordinators, monkeypatch, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 13:00:00"):
            c, store, zone_id = await _store_from_an_older_release(
                hass, hass_storage, coordinators
            )
            window, default_clock_window, rows = _live(
                c, store.get_zone(zone_id), monkeypatch
            )
        assert window == pytest.approx(EXPECTED_WINDOW_H)
        assert default_clock_window == pytest.approx(EXPECTED_WINDOW_H)
        assert rows == [EXPECTED_ROWS]

    async def test_a_store_this_release_wrote(
        self, hass, coordinators, monkeypatch, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 09:50:00") as frozen:
            c, store, zone_id = await _store_this_release_wrote(
                hass, frozen, coordinators
            )
            window, default_clock_window, rows = _live(
                c, store.get_zone(zone_id), monkeypatch
            )
        assert window == pytest.approx(EXPECTED_WINDOW_H)
        assert default_clock_window == pytest.approx(EXPECTED_WINDOW_H)
        assert rows == [EXPECTED_ROWS]


class TestEveryWriterStampsHAsClock:
    """Each writer the matrix does not reach, driven once: its stamp reads HA's wall clock.

    Frozen at 10:00 UTC with the user at Europe/Berlin, every stamp must read 12:00. The
    census below catches a bare ``datetime.now()`` coming back; these catch any other
    wrong clock -- ``dt_util.utcnow()`` stripped of its zone would pass the census.
    """

    WALL = datetime.datetime(2026, 7, 15, 12, 0)

    @staticmethod
    async def _scene(hass, built):
        store = await _new_store(hass)
        c = await _coordinator(hass, store, built)
        zone_id = await _add_zone(store)
        return c, store, zone_id, store.get_zone(zone_id)[const.ZONE_MAPPING]

    async def test_the_poll_of_every_group(
        self, hass, coordinators, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 10:00:00"):
            c, store, zone_id, mapping_id = await self._scene(hass, coordinators)
            await c._async_update_all()
        (row,) = store.get_mapping_buffer(mapping_id)
        assert row[const.RETRIEVED_AT] == self.WALL
        assert store.get_zone(zone_id)[const.ZONE_LAST_UPDATED] == self.WALL

    async def test_the_poll_of_one_zone(
        self, hass, coordinators, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 10:00:00"):
            c, store, zone_id, mapping_id = await self._scene(hass, coordinators)
            await c._async_update_zone(zone_id)
        (row,) = store.get_mapping_buffer(mapping_id)
        assert row[const.RETRIEVED_AT] == self.WALL
        mapping = store.get_mapping(mapping_id)
        assert mapping[const.MAPPING_DATA_LAST_UPDATED] == self.WALL
        assert store.get_zone(zone_id)[const.ZONE_LAST_UPDATED] == self.WALL

    async def test_clearing_the_weather_data(
        self, hass, coordinators, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 10:00:00"):
            c, store, zone_id, _ = await self._scene(hass, coordinators)
            await c._async_clear_all_weatherdata()
        assert store.get_zone(zone_id)[const.ZONE_LAST_CONSUMED] == self.WALL

    async def test_a_sensor_group_switching_its_source(
        self, hass, coordinators, utc_container_berlin_user
    ):
        switched = {
            **STATIC_GROUP,
            const.MAPPING_TEMPERATURE: {
                const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
                const.MAPPING_CONF_SENSOR: "sensor.temperature",
            },
        }
        with freeze_time("2026-07-15 10:00:00"):
            c, store, zone_id, mapping_id = await self._scene(hass, coordinators)
            await c.async_update_mapping_config(
                mapping_id, {const.MAPPING_MAPPINGS: switched}
            )
        assert store.get_zone(zone_id)[const.ZONE_LAST_CONSUMED] == self.WALL

    async def test_a_burst_of_sensor_events(
        self, hass, coordinators, utc_container_berlin_user
    ):
        with freeze_time("2026-07-15 10:00:00"):
            c, store, zone_id, mapping_id = await self._scene(hass, coordinators)
            await c._async_continuous_update_for_mapping(mapping_id)
        mapping = store.get_mapping(mapping_id)
        assert mapping[const.MAPPING_DATA_LAST_UPDATED] == self.WALL
        assert store.get_zone(zone_id)[const.ZONE_LAST_UPDATED] == self.WALL

    async def test_the_baseline_a_new_sensor_subscription_seeds(
        self, hass, coordinators, utc_container_berlin_user
    ):
        hass.states.async_set("sensor.temperature", "20.0", {"unit_of_measurement": "°C"})
        with freeze_time("2026-07-15 10:00:00"):
            c, store, _, mapping_id = await self._scene(hass, coordinators)
            await store.async_update_mapping(
                mapping_id,
                {
                    const.MAPPING_MAPPINGS: {
                        const.MAPPING_TEMPERATURE: {
                            const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
                            const.MAPPING_CONF_SENSOR: "sensor.temperature",
                        }
                    }
                },
            )
            await store.async_update_config({const.CONF_CONTINUOUS_UPDATES: True})
            await c.async_setup_continuous_updates()
        c.async_teardown_continuous_updates()
        (row,) = store.get_mapping_buffer(mapping_id)
        assert row[const.RETRIEVED_AT] == self.WALL


class TestTheSolarClampReadsTheUsersClock:
    """The ingest clamp pairs its clock with HA's UTC offset, so it needs HA's clock.

    A user at New York, the container at UTC, 13:30 on the user's clock (17:30 UTC). At
    this site clear sky allows 1244.8 W/m2 at 13:30 local and 814.5 W/m2 at 17:30 local, so
    a 1000 W/m2 reading passes at the hour it was taken and is clamped at the process's.
    """

    async def test_a_bright_early_afternoon_is_judged_at_its_own_hour(
        self, hass, coordinators
    ):
        before = dt_util.get_default_time_zone()
        dt_util.set_default_time_zone(zoneinfo.ZoneInfo("America/New_York"))
        try:
            store = await _new_store(hass)
            c = await _coordinator(hass, store, coordinators)
            c._effective_latitude = 39.68987
            c._effective_longitude = -84.07865
            c._effective_elevation = 311.0
            reading = 1000.0 * const.W_TO_MJ_DAY_FACTOR
            with freeze_time("2026-06-21 17:30:00"):
                clamped = c._clamp_solar_reading(reading)
        finally:
            dt_util.set_default_time_zone(before)
        assert clamped == pytest.approx(reading)


class TestNoProcessClockOnTheBufferPaths:
    """The modules that write or compare the buffer's stamps read HA's clock, not the process's.

    A tripwire, not a proof -- the matrix above is the proof. This catches a bare
    ``datetime.now()`` coming back into one of these modules at a place the matrix does
    not reach. If one is ever needed here for something else, list it with its reason.
    """

    MODULES = (
        "__init__.py",
        "calculation.py",
        "continuous_update.py",
        "helpers.py",
        "store.py",
        "weather_aggregate.py",
    )
    ALLOWED: frozenset = frozenset()

    @staticmethod
    def _is_stdlib_clock(node):
        if isinstance(node, ast.Name):
            return node.id in ("datetime", "dt_datetime", "date")
        return (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "datetime"
            and node.attr in ("datetime", "date")
        )

    def test_none_of_them_reads_the_process_clock(self):
        found = []
        for name in self.MODULES:
            tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("now", "today")
                    and self._is_stdlib_clock(node.func.value)
                ):
                    found.append(f"{name}:{node.lineno}")
        assert sorted(set(found) - self.ALLOWED) == []
```

- [ ] **Step 2: Run it to verify it fails, as offsets**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_weather_buffer_one_frame.py -p _local_socket_unblock -q --no-header --tb=line
```

Expected: `12 failed`, one line each —
- both `TestTheDailyPath` cells: `assert [[(10.5, 2.0)... (12.5, 2.0)]] == [[(12.5, 2.0)...
  (14.5, 2.0)]]` — the window assertion above it **passes** (3.0 h): the daily window was
  right, its hours were not;
- both `TestTheLivePath` cells: `assert 5.0 == 3.0 ± 3.0e-06`;
- all six `TestEveryWriterStampsHAsClock` tests: `assert HAFakeDatetime(2026, 7, 15, 10, 0) ==
  datetime.datetime(2026, 7, 15, 12, 0)` — the process's clock where HA's is expected;
- the solar clamp: `assert 70.37467824637923 == 86.4 ± 8.6e-05` (814.5 W/m² instead of 1000);
- the census: 20 entries — `__init__.py:1429, 1506, 1516, 1632, 1644, 1799, 2025`,
  `calculation.py:267, 379, 432, 498, 934`, `continuous_update.py:252, 378, 521`,
  `helpers.py:1015`, `store.py:1653`, `weather_aggregate.py:370, 938, 1133`.

A cell that fails with an exception instead of a value is a broken fixture, not the defect:
stop and fix the fixture first.

- [ ] **Step 3: No commit**

The file goes in with Task 5, which turns it green. Until then stage by name.

---

## Task 2: One clock, named — and the process zone with its own rules

**Files:**
- Modify: `custom_components/irrigation_plus/helpers.py` (import block `:10`, `_process_timezone` `:1007-1015`, new function before `class CannotConnect`)
- Test: `tests/test_time_provenance.py`

- [ ] **Step 1: Write the two failing tests**

In `tests/test_time_provenance.py`, add the import (after `import pytest`):

```python
from freezegun import freeze_time
```

and, directly after `test_a_naive_value_is_returned_unchanged_under_either_provenance`, the
two tests:

```python
def test_local_naive_now_is_has_wall_clock_without_a_zone(split_zones):
    """The clock every weather-buffer stamp is written in and compared against."""
    with freeze_time("2026-09-21 10:00:00"):
        now = helpers.local_naive_now()

    assert now == datetime.datetime(2026, 9, 21, 12, 0)
    assert now.tzinfo is None


def test_the_process_zone_is_read_with_its_own_rules():
    """Each date at its own offset, not today's offset for every date.

    ``datetime.now().astimezone().tzinfo`` is a FIXED offset frozen at the moment of the
    call; in summer it reads a January stamp an hour off. The process zone cannot be set
    on Windows (no ``time.tzset()``), so this compares with what the C library says for
    each date. On a machine at UTC both are 0 and the check is idle; where the zone has
    DST it catches the fixed offset.
    """
    tz = helpers._process_timezone()

    for day in (
        datetime.datetime(2026, 1, 15, 12, 0),
        datetime.datetime(2026, 7, 15, 12, 0),
    ):
        assert tz.utcoffset(day) == day.astimezone().utcoffset(), day
```

- [ ] **Step 2: Run them to verify they fail**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_time_provenance.py -p _local_socket_unblock -q --no-header --tb=line ; /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest "tests/test_time_provenance.py::test_the_process_zone_is_read_with_its_own_rules" -p _local_socket_unblock -q --no-header --tb=line
```

The second command is **the exception to `TZ=UTC`**: the process-zone test can only fail where
the process zone has DST, and this machine runs Europe/Berlin.

Expected: first run `1 failed, 7 passed` — `AttributeError: module
'custom_components.irrigation_plus.helpers' has no attribute 'local_naive_now'` (the
process-zone test passes idle at UTC); second run `1 failed`, on
`datetime.datetime(2026, 1, 15, 12, 0)` — today's fixed +02:00 against January's +01:00.

- [ ] **Step 3: Implement**

In `custom_components/irrigation_plus/helpers.py`, the import — replace

```python
from homeassistant import exceptions
```

with

```python
from dateutil import tz as dateutil_tz
from homeassistant import exceptions
```

Replace `_process_timezone` (`:1007-1015`) —

```python
def _process_timezone():
    """The zone a bare ``datetime.now()`` writes in -- the PROCESS's, not HA's.

    Its own function for one reason: the suite has to be able to substitute it.
    ``time.tzset()`` does not exist on Windows, so a test cannot set the real process
    zone, and a test that only runs on CI is one we never watch go from red to green
    ourselves.
    """
    return datetime.now().astimezone().tzinfo
```

— with

```python
def _process_timezone():
    """The zone a bare ``datetime.now()`` wrote in -- the PROCESS's, with its DST rules.

    ``tzlocal()`` rather than ``datetime.now().astimezone().tzinfo``: the latter is
    TODAY's fixed offset, and a stamp from the other side of a DST change is then read
    an hour off -- the buffer keeps seven days. Its own function so the suite can
    substitute it: ``time.tzset()`` does not exist on Windows.
    """
    return dateutil_tz.tzlocal()
```

and insert, directly before `class CannotConnect(exceptions.HomeAssistantError):`,

```python
def local_naive_now() -> datetime:
    """HA's wall clock, naive: the one frame every weather-buffer stamp is in.

    Wurzel: the buffer's stamps were written by a bare ``datetime.now()`` -- the
      PROCESS's clock -- and read against HA's (the live estimate, the solar geometry).
      On Docker/Core without ``TZ=`` the two differ by the whole UTC offset.
    Fix: every writer of those stamps, and every ``now`` they are compared with, reads
      this.
    NOT-TO-DO: do not return it aware. A naive/aware mix inside the live estimate's
      blanket ``except`` switches the estimate off instead of raising.
    siehe tests/test_weather_buffer_one_frame.py
    """
    return dt_util.now().replace(tzinfo=None)


```

- [ ] **Step 4: Run them to verify they pass**

The same two commands as Step 2. Expected: `8 passed`, then `1 passed`.

- [ ] **Step 5: Lint, then commit**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && uvx black custom_components/irrigation_plus/ ; uvx ruff check custom_components/irrigation_plus/ ; git add custom_components/irrigation_plus/helpers.py tests/test_time_provenance.py ; git diff --cached --name-only
```

Expected: black and ruff clean, the two files listed.

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && git commit -q -F - <<'EOF'
fix(time): name HA's naive wall clock; read the process zone with its DST rules

local_naive_now() is the clock the weather-buffer stamps are about to be
written and compared in. _process_timezone() returned today's fixed offset,
which reads a stamp from the other side of a DST change an hour off; tzlocal()
answers per date.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log -1 --format=%s
```

---

## Task 3: An aware stamp is read on HA's clock, whichever provenance

**Files:**
- Modify: `custom_components/irrigation_plus/helpers.py:1000-1002` (the comment on the two provenances), `:1018-1059` (`coerce_stamp`)
- Modify: `custom_components/irrigation_plus/weather_aggregate.py:102-121` (`_parse` docstring)
- Modify: `custom_components/irrigation_plus/live_estimate.py:193-215` (`_parse_stored_as_ha_local` docstring)
- Test: `tests/test_time_provenance.py`, `tests/test_live_estimate_time_provenance.py`, `tests/test_weather_aggregate.py`

- [ ] **Step 1: Turn the pins round**

`tests/test_time_provenance.py` — replace the module docstring with

```python
"""The two time provenances, named -- and, since the store's 14.2 migration, one clock.

A naive timestamp on these paths used to mean one of two different things:

- a **stored** stamp was written by a bare ``datetime.now()``, so naive meant the zone
  the PROCESS was in;
- a **client** row is a site-local clock time that came out of a weather API, so naive
  means HA's configured zone, and always did.

The two agree on HA OS and Supervised, which is why the seam went unnoticed; on Docker or
Core without ``TZ=`` they differed by the whole UTC offset. Stored stamps are now written
on HA's clock (``local_naive_now()``) and the store migration moved the older ones, so
both provenances read the same way. The names stay: every call site still says which kind
it holds.

Coercion normalises to the NAIVE form both paths use -- it does not make anything aware.
An aware stamp inside the live estimate's blanket ``except`` would raise
``can't compare offset-naive and offset-aware`` there, i.e. silently disable the estimate.
"""
```

replace `test_the_same_instant_coerces_differently_per_provenance` (the whole function) with

```python
def test_an_aware_instant_is_read_on_has_clock_under_either_provenance(split_zones):
    """One aware instant, both provenances, one answer: 12:00 on the user's clock.

    Stored stamps are on HA's clock now, so the store provenance reads an aware one
    there too -- the answer the client provenance always gave. On the process's clock
    it was 10:00, the whole offset away.
    """
    instant = datetime.datetime(2026, 9, 21, 10, 0, tzinfo=UTC)

    stored = coerce_stamp(instant, STAMP_FROM_STORE)
    client = coerce_stamp(instant, STAMP_FROM_CLIENT)

    assert stored == datetime.datetime(2026, 9, 21, 12, 0)
    assert client == datetime.datetime(2026, 9, 21, 12, 0)
    assert stored.tzinfo is None and client.tzinfo is None
```

and the docstring of `test_a_naive_value_is_returned_unchanged_under_either_provenance` with

```python
    """A naive stamp is already in the frame, so nothing moves it.

    Every stamp a writer produces is naive on HA's clock, and so is every stamp the
    store migration leaves; coercing one again must not shift it.
    """
```

`tests/test_live_estimate_time_provenance.py` — replace the module docstring with

```python
"""Which zone the live estimate reads each kind of naive timestamp in.

Two kinds reach it:

- **stored** stamps (`last_calculated`, `last_updated`) are written on HA's clock
  (``local_naive_now()``), and the store's 14.2 migration moved the ones older
  releases wrote on the PROCESS's clock;
- **client** rows (the hourly forecast series) are site-local clock times off a
  weather API, so naive means HA's configured zone, and always did.

Both therefore read in HA's zone. The stored half used to be wrong: a bare
``datetime.now()`` wrote the process's clock, and on a container without ``TZ=`` this
reader was the whole UTC offset off.
"""
```

replace `test_a_stored_stamp_is_still_read_in_ha_local_today` (the whole function) with

```python
def test_a_stored_stamp_is_read_on_has_clock(split_zones):
    """The store now holds what this reader always assumed.

    ``_parse_stored_as_ha_local`` reads a stored stamp as HA-local: an aware value
    through ``dt_util.as_local``, a naive one as it is. Stamps used to be written on the
    process's clock, so on a container without ``TZ=`` that was the whole UTC offset
    off. Written on HA's clock now, and migrated there at 14.2, the reading is right --
    and the store provenance gives the same answer.
    """
    aware = datetime.datetime(2026, 9, 21, 10, 0, tzinfo=UTC)

    got = live_estimate._parse_stored_as_ha_local(aware)

    assert got == datetime.datetime(2026, 9, 21, 12, 0)
    assert helpers.coerce_stamp(aware, helpers.STAMP_FROM_STORE) == got
```

and the docstring of `test_a_naive_stored_stamp_passes_through_either_way` with

```python
    """Every stored stamp is naive, and a naive value is already in the frame.

    Both rules leave it alone. What put a naive stamp in the right frame is the write
    side and the store migration, not this reader -- which is why the defect was
    invisible here while it lasted.
    """
```

`tests/test_weather_aggregate.py` — add the import after `import pytest`:

```python
from homeassistant.util import dt as dt_util
```

and replace everything from `class TestSelectWindowAcceptsBothTimestampForms:` down to (not
including) `class TestSelectWindow:` with

```python
class TestSelectWindowAcceptsBothTimestampForms:
    """An AWARE stamp must not detonate here, and must land where its naive twin does.

    Every stamp in the buffer is naive, so these tests add a case rather than change
    one: without them, the first aware value reaching this function raises
    ``can't compare offset-naive and offset-aware datetimes`` inside a blanket
    ``except``, which does not crash anything -- it silently switches the live
    estimate off with a plausible "last calculated" still on display.

    A stored stamp's naive form is HA's clock (the writers use ``local_naive_now()``
    and the store's 14.2 migration moved older stamps), so an aware one is read on
    HA's clock, and its naive twin is the same wall time in HA's zone.
    """

    @staticmethod
    def _aware(offset_h, tz, **vals):
        naive = T0 + datetime.timedelta(hours=offset_h)
        return {const.RETRIEVED_AT: naive.replace(tzinfo=tz), **vals}

    def test_an_aware_retrieved_at_splits_where_its_naive_twin_does(self):
        ha = dt_util.get_default_time_zone()
        wm = T0 + datetime.timedelta(hours=2)
        naive_rows = [_r(h, Temperature=10 + h) for h in (0, 1, 2, 3, 4)]
        aware_rows = [self._aware(h, ha, Temperature=10 + h) for h in (0, 1, 2, 3, 4)]

        n_boundary, n_window = select_window(naive_rows, wm)
        a_boundary, a_window = select_window(aware_rows, wm)

        assert len(a_window) == len(n_window)
        assert [r["Temperature"] for r in a_window] == [
            r["Temperature"] for r in n_window
        ]
        assert (a_boundary is None) == (n_boundary is None)
        assert a_boundary["Temperature"] == n_boundary["Temperature"]

    def test_an_aware_watermark_splits_where_its_naive_twin_does(self):
        rows = [_r(h, Temperature=10 + h) for h in (0, 1, 2, 3, 4)]
        naive_wm = T0 + datetime.timedelta(hours=2)

        _, n_window = select_window(rows, naive_wm)
        _, a_window = select_window(
            rows, naive_wm.replace(tzinfo=dt_util.get_default_time_zone())
        )

        assert [r["Temperature"] for r in a_window] == [
            r["Temperature"] for r in n_window
        ]

    def test_an_aware_stamp_is_read_on_has_clock_not_the_process_s(self, monkeypatch):
        """HA's clock decides, not the process's.

        With the user at UTC+2 and the container at UTC, an 06:00 UTC stamp is 08:00 on
        the user's clock, so it falls AFTER an 07:00 watermark. Read on the process's
        clock it would be 06:00, on the other side of the split.
        """
        plus_two = datetime.timezone(datetime.timedelta(hours=2))
        monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
        before = dt_util.get_default_time_zone()
        dt_util.set_default_time_zone(plus_two)
        try:
            rows = [self._aware(0, UTC, Temperature=10)]  # 06:00 UTC == 08:00 HA
            wm = T0 + datetime.timedelta(hours=1)  # 07:00 on HA's clock

            boundary, window = select_window(rows, wm)
        finally:
            dt_util.set_default_time_zone(before)

        assert boundary is None, "08:00 is not at or before 07:00"
        assert len(window) == 1


class TestTheEntryPointsSurviveAnAwareNow:
    """An aware ``now`` must not detonate either, and must land in the rows' frame.

    Every caller passes ``now`` naive on HA's clock -- the daily calculation and the
    live estimate both read ``local_naive_now()`` -- and so does the default. An aware
    ``now`` is read on HA's clock, the frame of the rows it is compared against, so its
    naive twin is the same wall time in HA's zone.
    """

    def test_aggregate_window_accepts_an_aware_now(self):
        rows = [_r(0, Temperature=10), _r(1, Temperature=12)]
        cfg = {}
        naive_now = T0 + datetime.timedelta(hours=2)
        aware_now = naive_now.replace(tzinfo=dt_util.get_default_time_zone())

        plain = aggregate_window(rows, None, cfg, now=naive_now)
        aware = aggregate_window(rows, None, cfg, now=aware_now)

        assert aware == plain

    def test_build_substeps_accepts_an_aware_now(self):
        rows = [_r(0, Precipitation=0.0), _r(1, Precipitation=1.0)]
        cfg = {}
        naive_now = T0 + datetime.timedelta(hours=2)
        aware_now = naive_now.replace(tzinfo=dt_util.get_default_time_zone())

        plain = build_substeps(rows, None, cfg, now=naive_now)
        aware = build_substeps(rows, None, cfg, now=aware_now)

        assert aware == plain

    def test_build_hourly_rows_accepts_an_aware_now(self):
        rows = [_r(0, Temperature=10), _r(1, Temperature=12)]
        cfg = {}
        naive_now = T0 + datetime.timedelta(hours=2)
        aware_now = naive_now.replace(tzinfo=dt_util.get_default_time_zone())

        plain = build_hourly_rows(rows, None, cfg, now=naive_now)
        aware = build_hourly_rows(rows, None, cfg, now=aware_now)

        assert aware == plain


```

- [ ] **Step 2: Run them to verify they fail**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_time_provenance.py tests/test_live_estimate_time_provenance.py tests/test_weather_aggregate.py -p _local_socket_unblock -q --no-header --tb=line
```

Expected: `6 failed, 40 passed` —
- `test_time_provenance.py::test_an_aware_instant_is_read_on_has_clock_under_either_provenance`
  and `test_live_estimate_time_provenance.py::test_a_stored_stamp_is_read_on_has_clock`:
  `assert datetime.datetime(2026, 9, 21, 10, 0) == datetime.datetime(2026, 9, 21, 12, 0)` —
  the process's clock where HA's is expected;
- in `TestSelectWindowAcceptsBothTimestampForms`: the aware-rows twin `assert 5 == 2`, the
  aware-watermark twin `assert [] == [13, 14]`, and the inverted pin `08:00 is not at or before
  07:00`;
- `TestTheEntryPointsSurviveAnAwareNow::test_build_substeps_accepts_an_aware_now`.

Its two siblings pass on both sides: without a watermark neither `aggregate_window`'s
multiplier nor `build_hourly_rows` (which returns None for these rows) reads `now`, so they
pin only that an aware `now` does not raise. Left as they are.

- [ ] **Step 3: Implement**

`custom_components/irrigation_plus/helpers.py` — replace the comment above the two constants

```python
# The two things a NAIVE timestamp can mean on the weather-buffer paths. They are
# separate values rather than one flag because the coercion below refuses anything
# it does not recognise, and a typo must not silently pick one of the two rules.
```

with

```python
# The two kinds of stamp on the weather-buffer paths: written by this integration
# (store) and read off a weather API (client). Both are naive on HA's clock now and
# coerce alike; they stay separate values so every call site keeps saying which kind
# it holds, and because the coercion refuses anything it does not recognise -- a
# typo must not silently pick a rule.
```

and replace `coerce_stamp` (`:1018-1059`, the whole function) with

```python
def coerce_stamp(value, provenance) -> datetime | None:
    """Normalise a timestamp to the naive frame the weather-buffer paths use: HA's clock.

    Wurzel: a naive stamp on these paths meant one of two opposite things. Stored
      stamps were written by a bare ``datetime.now()`` (the PROCESS's zone); client rows
      are site-local clock times off a weather API (HA's zone). On Docker/Core without
      ``TZ=`` the two differ by the whole UTC offset.
    Fix: stored stamps are on HA's clock now -- the writers read ``local_naive_now()``
      and the store's 14.2 migration moved older ones -- so both provenances mean one
      frame: a naive value comes back untouched, an aware one is read on HA's clock.
      Both names stay, so every call site still says which kind of stamp it holds.
    NOT-TO-DO: do not give ``provenance`` a default. A caller must not be able to stay
      silent about which kind it holds.
    NOT-TO-DO: do not let this raise. Its callers sit inside a blanket ``except`` that
      turns a raise into the live estimate quietly going unavailable with a plausible
      "last calculated" still on display, so an unreadable value is no stamp and the
      caller keeps its fallback.
    siehe tests/test_time_provenance.py
    """
    if provenance not in (STAMP_FROM_STORE, STAMP_FROM_CLIENT):
        raise ValueError(f"unknown timestamp provenance: {provenance!r}")
    if value is None:
        return None
    try:
        parsed = as_datetime(value)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, datetime):
        return None
    if parsed.tzinfo is None:
        return parsed
    return dt_util.as_local(parsed).replace(tzinfo=None)
```

`custom_components/irrigation_plus/weather_aggregate.py` — replace the docstring of `_parse`
with

```python
    """A stored ``RETRIEVED_AT`` (datetime or ISO string) as a naive stamp on HA's clock.

    Wurzel: this returned whatever it was handed, so one aware value in the buffer
      raised ``can't compare offset-naive and offset-aware datetimes`` from inside a
      blanket ``except`` -- which switches the live estimate off and leaves a plausible
      "last calculated" on display.
    Fix: route it through the shared coercion under the store provenance. Stored stamps
      are naive on HA's clock (the writers read ``local_naive_now()``, the store's 14.2
      migration moved older ones), so a naive value comes back untouched and an aware
      one is read on HA's clock.
    siehe tests/test_weather_aggregate.py::TestSelectWindowAcceptsBothTimestampForms
    """
```

`custom_components/irrigation_plus/live_estimate.py` — replace the docstring of
`_parse_stored_as_ha_local` with

```python
    """A stored last_calculated/last_updated read as naive on HA's clock.

    Wurzel: it read a stored stamp as HA-local while the store wrote it on the PROCESS's
      clock (a bare ``datetime.now()``) -- on Docker/Core without ``TZ=`` the whole UTC
      offset apart. On the proxy path that pushed the anchor onto the next calendar day,
      so a whole day's ET was subtracted right after the daily calc.
    Fix: none here -- the store moved to this reader's frame. The writers read
      ``local_naive_now()`` and the store's 14.2 migration moved older stamps, so a naive
      value is HA-local and an aware one is converted with ``dt_util.as_local``: the
      same answer as ``coerce_stamp(value, STAMP_FROM_STORE)``.
    siehe tests/test_live_estimate_time_provenance.py::test_a_stored_stamp_is_read_on_has_clock
    """
```

- [ ] **Step 4: Run them to verify they pass**

The command of Step 2. Expected: `46 passed`.

- [ ] **Step 5: Lint, then commit**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && uvx black custom_components/irrigation_plus/ ; uvx ruff check custom_components/irrigation_plus/ ; git add custom_components/irrigation_plus/helpers.py custom_components/irrigation_plus/weather_aggregate.py custom_components/irrigation_plus/live_estimate.py tests/test_time_provenance.py tests/test_live_estimate_time_provenance.py tests/test_weather_aggregate.py ; git diff --cached --name-only
```

Expected: clean; six files.

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && git commit -q -F - <<'EOF'
fix(time): read an aware stored stamp on HA's clock, like a client row

Stored stamps move to HA's clock with this series, so the store provenance
now reads an aware one there too. Both provenance names stay; the pins that
recorded the old process-zone reading are turned round, and the aware twins
in the aggregation tests are built in HA's zone.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log -1 --format=%s
```

---

## Task 4: The store migration, 14.1 → 14.2

**Files:**
- Modify: `custom_components/irrigation_plus/helpers.py` (new `lift_legacy_stamp`, before `class CannotConnect`)
- Modify: `custom_components/irrigation_plus/store.py:191` (import), `:198` (`STORAGE_MINOR_VERSION`), before `:603` (`_lift_legacy_stamps`), `:603-606` (`MigratableStore`), `:903` (construction)
- Create: `tests/test_store_stamp_migration.py`
- Modify (rename only): `tests/test_batch_config_survives_v14.py`, `tests/test_master.py`, `tests/test_schedule_migration_v14.py`, `tests/test_store.py`, `tests/test_store_distributor.py`, `tests/test_store_legacy_migrations.py`, `tests/test_unit_system_migration.py`, `tests/test_zone_depth_defaults.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_store_stamp_migration.py`:

```python
"""A store older than 14.2 has its weather-buffer stamps moved onto HA's clock, once.

Up to minor version 1 the five stamps the weather-buffer paths compare -- three on each
zone, two on each sensor group -- were written by a bare ``datetime.now()``, the
PROCESS's clock. From 14.2 on they are naive on HA's clock, and loading an older store
rewrites what the release before left behind.

The process zone is substituted rather than set, because ``time.tzset()`` does not exist
on Windows.
"""

import copy
import datetime
import zoneinfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.irrigation_plus import const, helpers
from custom_components.irrigation_plus.store import (
    STORAGE_KEY,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
    MigratableStore,
    SmartIrrigationStorage,
)

UTC = datetime.UTC
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")
ZONE_STAMPS = (
    const.ZONE_LAST_CALCULATED,
    const.ZONE_LAST_CONSUMED,
    const.ZONE_LAST_UPDATED,
)


@pytest.fixture
def utc_container_berlin_user(monkeypatch):
    """The process at UTC, Home Assistant at Europe/Berlin: +2 h in July."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    before = dt_util.get_default_time_zone()
    dt_util.set_default_time_zone(BERLIN)
    yield
    dt_util.set_default_time_zone(before)


@pytest.fixture
def berlin_container_utc_user(monkeypatch):
    """The process at Europe/Berlin, Home Assistant at UTC: +1 h in January, +2 h in July."""
    monkeypatch.setattr(helpers, "_process_timezone", lambda: BERLIN)
    before = dt_util.get_default_time_zone()
    dt_util.set_default_time_zone(UTC)
    yield
    dt_util.set_default_time_zone(before)


def _data(*rows, stamp="2026-07-15T10:00:00"):
    """A store's data block: one zone and one sensor group, every stamp at ``stamp``."""
    return {
        "config": {},
        "zones": [{const.ZONE_ID: 1, **dict.fromkeys(ZONE_STAMPS, stamp)}],
        "mappings": [
            {
                const.MAPPING_ID: 1,
                const.MAPPING_DATA: [
                    {const.RETRIEVED_AT: row, const.MAPPING_TEMPERATURE: 20.0}
                    for row in (rows or (stamp,))
                ],
                const.MAPPING_DATA_LAST_UPDATED: stamp,
            }
        ],
    }


def _stamps(data):
    """Every stamp of a data block: the zone's three, each row's, the group's."""
    zone = data["zones"][0]
    mapping = data["mappings"][0]
    return (
        [zone[key] for key in ZONE_STAMPS]
        + [row[const.RETRIEVED_AT] for row in mapping[const.MAPPING_DATA]]
        + [mapping[const.MAPPING_DATA_LAST_UPDATED]]
    )


async def _migrate(hass, major, minor, data):
    store = MigratableStore(
        hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_MINOR_VERSION
    )
    return await store._async_migrate_func(major, minor, data)


async def _file_as_an_older_release_left_it(hass, hass_storage, *, minor=1):
    """A whole store document with process-local stamps, as setup will find it.

    Written through this code's API and save, so it hydrates; then given the minor
    version and the stamps a release before 14.2 wrote. ``minor=None`` drops the key,
    which is how releases older than HA's minor versions left it.
    """
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    mapping = await store.async_create_mapping(
        {const.MAPPING_NAME: "GW", const.MAPPING_MAPPINGS: {}, const.MAPPING_DATA: []}
    )
    await store.async_create_zone(
        {
            const.ZONE_NAME: "Front",
            const.ZONE_MAPPING: mapping[const.MAPPING_ID],
            const.ZONE_SIZE: 10.0,
            const.ZONE_THROUGHPUT: 10.0,
        }
    )
    await store.async_save()
    document = hass_storage[STORAGE_KEY]
    if minor is None:
        del document["minor_version"]
    else:
        document["minor_version"] = minor
    for zone in document["data"]["zones"]:
        zone.update(dict.fromkeys(ZONE_STAMPS, "2026-07-15T10:00:00"))
    for group in document["data"]["mappings"]:
        group[const.MAPPING_DATA] = [
            {const.RETRIEVED_AT: "2026-07-15T09:55:00", const.MAPPING_TEMPERATURE: 20.0}
        ]
        group[const.MAPPING_DATA_LAST_UPDATED] = "2026-07-15T10:00:00"
    return document


class TestTheFiveStampsMoveOntoHAsClock:
    async def test_every_stamp_moves_by_the_offset_in_one_pass(
        self, hass, utc_container_berlin_user
    ):
        """The watermark and the buffer it is compared with move together."""
        out = await _migrate(hass, 14, 1, _data())

        assert _stamps(out) == ["2026-07-15T12:00:00"] * 5

    async def test_each_stamp_is_read_at_its_own_dates_offset(
        self, hass, berlin_container_utc_user
    ):
        """The buffer keeps a week, enough to straddle a DST change.

        Today's offset for every stamp would read the January one an hour off.
        """
        out = await _migrate(
            hass, 14, 1, _data("2026-01-15T12:00:00", "2026-07-15T12:00:00")
        )

        rows = [row[const.RETRIEVED_AT] for row in out["mappings"][0][const.MAPPING_DATA]]
        assert rows == ["2026-01-15T11:00:00", "2026-07-15T10:00:00"]

    async def test_an_aware_stamp_is_read_as_the_instant_it_names(
        self, hass, utc_container_berlin_user
    ):
        out = await _migrate(hass, 14, 1, _data(stamp="2026-07-15T10:00:00+00:00"))

        assert _stamps(out) == ["2026-07-15T12:00:00"] * 5

    async def test_what_it_cannot_read_is_left_exactly_as_found(
        self, hass, utc_container_berlin_user
    ):
        data = {
            "config": {},
            "zones": [
                {
                    const.ZONE_ID: 1,
                    const.ZONE_LAST_CALCULATED: None,
                    const.ZONE_LAST_CONSUMED: "not a date",
                    const.ZONE_LAST_UPDATED: 12345,
                },
                {const.ZONE_ID: 2},
                "not a zone",
            ],
            "mappings": [
                # The field's legacy attrs default was the string "[]".
                {const.MAPPING_ID: 1, const.MAPPING_DATA: "[]"},
                {
                    const.MAPPING_ID: 2,
                    const.MAPPING_DATA: [
                        {const.MAPPING_TEMPERATURE: 20.0},
                        {const.RETRIEVED_AT: None},
                        "not a row",
                    ],
                    const.MAPPING_DATA_LAST_UPDATED: None,
                },
            ],
        }
        before = copy.deepcopy(data)

        out = await _migrate(hass, 14, 1, data)

        assert out["zones"] == before["zones"]
        assert out["mappings"] == before["mappings"]

    async def test_a_store_at_14_2_or_later_is_left_alone(
        self, hass, utc_container_berlin_user
    ):
        """The rewrite is not idempotent: run on an HA-local store it moves it again."""
        for minor in (2, 3):
            out = await _migrate(hass, 14, minor, _data(stamp="2026-07-15T12:00:00"))

            assert _stamps(out) == ["2026-07-15T12:00:00"] * 5

    async def test_an_older_major_is_moved_as_well(self, hass, utc_container_berlin_user):
        out = await _migrate(hass, 13, 1, _data())

        assert _stamps(out) == ["2026-07-15T12:00:00"] * 5


class TestThroughHomeAssistantsLoad:
    """The way setup meets it: Home Assistant's own Store decides to migrate."""

    async def test_a_14_1_file_is_moved_and_saved_as_14_2(
        self, hass, hass_storage, utc_container_berlin_user
    ):
        await _file_as_an_older_release_left_it(hass, hass_storage, minor=1)

        store = SmartIrrigationStorage(hass)
        await store.async_load()

        (zone,) = store.zones.values()
        assert (zone.last_calculated, zone.last_consumed_at, zone.last_updated) == (
            "2026-07-15T12:00:00",
        ) * 3
        (mapping,) = store.mappings.values()
        assert mapping.data_last_updated == "2026-07-15T12:00:00"
        assert [row[const.RETRIEVED_AT] for row in store.buffers[mapping.id]] == [
            "2026-07-15T11:55:00"
        ]
        saved = hass_storage[STORAGE_KEY]
        assert (saved["version"], saved["minor_version"]) == (14, 2)

    async def test_a_file_without_a_minor_version_counts_as_14_1(
        self, hass, hass_storage, utc_container_berlin_user
    ):
        await _file_as_an_older_release_left_it(hass, hass_storage, minor=None)

        store = SmartIrrigationStorage(hass)
        await store.async_load()

        (zone,) = store.zones.values()
        assert zone.last_consumed_at == "2026-07-15T12:00:00"


class TestARolledBackReleaseOpensTheFile:
    """What v2026.09.17 does with a file this release saved.

    Home Assistant refuses a stored MAJOR version above the one a Store reads
    (``UnsupportedStorageVersionError``, since HA 2026.3), which is why the stamps moved
    on the MINOR version. A release that knows only 14.1 opens a 14.2 file, runs its own
    two-argument migrate function on it and saves it back as 14.1. That is harmless only
    if the function leaves zones and buffers alone.

    The store below opens the file the way v2026.09.17 does: major 14, minor 1 (HA's
    default) and a migrate function with TWO parameters, so Home Assistant's own dispatch,
    not this test, decides to call it without the minor. Its body is this release's major
    steps. Against v2026.09.17's function they differ by one config default
    (``forecast_weather_entity``) and in nothing that touches zones or mappings -- read on
    2026-09-30; vendoring that release's function here would still hydrate against
    today's constants.
    """

    async def test_a_14_2_file_comes_back_untouched_and_is_saved_as_14_1(
        self, hass, hass_storage, utc_container_berlin_user
    ):
        await _file_as_an_older_release_left_it(hass, hass_storage, minor=1)
        await SmartIrrigationStorage(hass).async_load()  # the migration; saved as 14.2
        written = copy.deepcopy(hass_storage[STORAGE_KEY])
        assert (written["version"], written["minor_version"]) == (14, 2)

        seen = []

        class AsReleasedIn0917(MigratableStore):
            async def _async_migrate_func(self, old_version, data):
                seen.append(old_version)
                return await self._async_migrate_major(old_version, data)

        loaded = await AsReleasedIn0917(hass, 14, STORAGE_KEY).async_load()

        assert seen == [14]
        assert loaded["zones"] == written["data"]["zones"]
        assert loaded["mappings"] == written["data"]["mappings"]
        assert loaded["zones"][0][const.ZONE_LAST_CONSUMED] == "2026-07-15T12:00:00"
        saved = hass_storage[STORAGE_KEY]
        assert (saved["version"], saved["minor_version"]) == (14, 1)
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_store_stamp_migration.py -p _local_socket_unblock -q --no-header --tb=line
```

Expected: `1 error` during collection — `ImportError: cannot import name
'STORAGE_MINOR_VERSION'`.

- [ ] **Step 3: Implement the stamp rewrite**

`custom_components/irrigation_plus/helpers.py` — insert, directly before
`class CannotConnect(exceptions.HomeAssistantError):` (after `local_naive_now`),

```python
def lift_legacy_stamp(value):
    """One stamp of a pre-14.2 store, moved from the process's clock onto HA's.

    String in, string out: ``async_load`` converts nothing, so the loaded shape must
    stay what the file held. A naive value is read in the process zone at its own date's
    offset, an aware one as the instant it names; anything else -- ``None``, an
    unparseable string, a non-string -- comes back exactly as found. Why and when this
    runs: ``store._lift_legacy_stamps``.
    """
    if not isinstance(value, str):
        return value
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_process_timezone())
    return dt_util.as_local(parsed).replace(tzinfo=None).isoformat()


```

`custom_components/irrigation_plus/store.py` — the import (`:191`), replace

```python
from .helpers import as_datetime, loadModules, zone_depth_default
```

with

```python
from .helpers import as_datetime, lift_legacy_stamp, loadModules, zone_depth_default
```

after `STORAGE_VERSION = 14` (`:198`) add

```python
# Minor 2: the five weather-buffer stamps are naive on HA's clock (up to minor 1 they
# were on the process's). A MINOR bump on purpose -- see _lift_legacy_stamps.
STORAGE_MINOR_VERSION = 2
```

insert, directly before `class MigratableStore(Store):`,

```python
def _lift_legacy_stamps(data: dict) -> None:
    """Move the five weather-buffer stamps of a pre-14.2 store onto HA's clock, once.

    Wurzel: up to 14.1 they were written by a bare ``datetime.now()`` -- the PROCESS's
      clock -- while every reader compares them with HA-local values. On Docker/Core
      without ``TZ=`` the two differ by the whole UTC offset.
    Fix: the writers stamp ``local_naive_now()`` from 14.2 on; this rewrites what an
      older release left, in one pass, so a zone's watermark and the buffer rows it is
      compared with move together.
    Assumptions, both accepted upstream and named in the release notes:
      - the process zone at the upgrade is the one the stamps were written in -- a
        process ``TZ`` changed between writing and upgrading is misread;
      - after this, a change of HA's own time zone misreads up to a week of buffer:
        the stamps carry no offset.
    Why the MINOR version: since HA 2026.3 a Store refuses a stored major version above
      its own, so a major bump would turn a rollback into a failed setup. A release that
      knows 14.1 opens a 14.2 file, runs its own migrate function (whose steps stop at
      13) and saves it back as 14.1: one window read off by the offset, then healed. A
      later re-upgrade moves that file again -- one more window.
    NOT-TO-DO: detect the frame from the data. A DST fall-back and a container ``TZ``
      fix leave byte-identical traces in a naive series.
    NOT-TO-DO: ``dt_util.as_local`` on a naive value only attaches HA's zone; it cannot
      know the process's, so it moves nothing.
    siehe tests/test_store_stamp_migration.py
    """
    for zone in data.get("zones") or []:
        if not isinstance(zone, dict):
            continue
        for key in (ZONE_LAST_CALCULATED, ZONE_LAST_CONSUMED, ZONE_LAST_UPDATED):
            if key in zone:
                zone[key] = lift_legacy_stamp(zone[key])
    for mapping in data.get("mappings") or []:
        if not isinstance(mapping, dict):
            continue
        if MAPPING_DATA_LAST_UPDATED in mapping:
            mapping[MAPPING_DATA_LAST_UPDATED] = lift_legacy_stamp(
                mapping[MAPPING_DATA_LAST_UPDATED]
            )
        rows = mapping.get(MAPPING_DATA)
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and RETRIEVED_AT in row:
                    row[RETRIEVED_AT] = lift_legacy_stamp(row[RETRIEVED_AT])


```

in `MigratableStore`, replace

```python
class MigratableStore(Store):
    """Store subclass that supports migration for Irrigation Plus storage."""

    async def _async_migrate_func(self, old_version, data: dict):
```

with

```python
class MigratableStore(Store):
    """Store subclass that supports migration for Irrigation Plus storage."""

    async def _async_migrate_func(self, old_major_version, old_minor_version, data):
        """Home Assistant's migrate hook in its three-argument form: majors, then minors.

        Three parameters so that HA passes the stored minor version at all -- it calls a
        two-parameter function with the major only. The major steps are unchanged in
        ``_async_migrate_major``; a release that knows only 14.1 runs exactly those on a
        14.2 file (see ``_lift_legacy_stamps``).
        """
        data = await self._async_migrate_major(old_major_version, data)
        if (old_major_version, old_minor_version) < (14, 2):
            _lift_legacy_stamps(data)
        return data

    async def _async_migrate_major(self, old_version, data: dict):
```

and where the store is built (`:903`), replace

```python
        self._store = MigratableStore(hass, STORAGE_VERSION, STORAGE_KEY)
```

with

```python
        self._store = MigratableStore(
            hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_MINOR_VERSION
        )
```

- [ ] **Step 4: Rename the direct calls in the major-step tests**

They drive the unchanged major steps, which now live in `_async_migrate_major`; the rename also
fixes the two docstrings that name the function.

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && sed -i 's/_async_migrate_func/_async_migrate_major/g' tests/test_batch_config_survives_v14.py tests/test_master.py tests/test_schedule_migration_v14.py tests/test_store.py tests/test_store_distributor.py tests/test_store_legacy_migrations.py tests/test_unit_system_migration.py tests/test_zone_depth_defaults.py ; grep -rn --include=*.py "_async_migrate_func" tests/ ; grep -rc --include=*.py "_async_migrate_major" tests/ | grep -v ":0$" ; git diff --stat tests/ | tail -1
```

Expected: the first grep lists only `tests/test_import_storage_visibility.py:71` (its docstring)
and `:76` (its own three-parameter pass-through), and `tests/test_store_stamp_migration.py:90`
and `:274` (the new hook and the 09.17-shaped one); the counts are
`test_batch_config_survives_v14.py:3`, `test_master.py:1`, `test_schedule_migration_v14.py:4`,
`test_store.py:5`, `test_store_distributor.py:1`, `test_store_legacy_migrations.py:2`,
`test_store_stamp_migration.py:1`, `test_unit_system_migration.py:5`,
`test_zone_depth_defaults.py:5` — 27. Under Git Bash `sed -i` writes the eight files with
**LF** endings; git prints `LF will be replaced by CRLF` for each and normalises on `add`, so
`git diff --stat tests/` shows `8 files changed, 26 insertions(+), 26 deletions(-)` — the
renamed lines only.

- [ ] **Step 5: Run them to verify they pass**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_store_stamp_migration.py tests/test_batch_config_survives_v14.py tests/test_master.py tests/test_schedule_migration_v14.py tests/test_store.py tests/test_store_distributor.py tests/test_store_legacy_migrations.py tests/test_unit_system_migration.py tests/test_zone_depth_defaults.py tests/test_import_storage_visibility.py -p _local_socket_unblock -q --no-header --tb=line
```

Expected: `184 passed`.

The file from Task 1 at this point, for orientation (not a gate): all twelve still fail. The
two cells on the older release's store now fail on the clock, not on the store:
`TestTheDailyPath` on the **window**, `assert [1.0] == [3.0 ± 3.0e-06]` — the migrated
watermark (12:00) against the daily path's process clock (13:00) — and `TestTheLivePath` on
the call without `now`, `assert 1.0 == 3.0 ± 3.0e-06` (the aggregation's default clock).

- [ ] **Step 6: Lint, then commit**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && uvx black custom_components/irrigation_plus/ ; uvx ruff check custom_components/irrigation_plus/ ; git add custom_components/irrigation_plus/helpers.py custom_components/irrigation_plus/store.py tests/test_store_stamp_migration.py tests/test_batch_config_survives_v14.py tests/test_master.py tests/test_schedule_migration_v14.py tests/test_store.py tests/test_store_distributor.py tests/test_store_legacy_migrations.py tests/test_unit_system_migration.py tests/test_zone_depth_defaults.py ; git diff --cached --name-only | wc -l
```

Expected: clean; `11`.

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && git commit -q -F - <<'EOF'
fix(store): move a pre-14.2 store's weather-buffer stamps onto HA's clock

Up to minor version 1 the five stamps the buffer paths compare were written
on the process's clock. Loading such a store now rewrites them once, in one
pass, naive -> process zone at the stamp's own offset -> HA-local, string in
and string out. Keyed on the MINOR version: since HA 2026.3 a Store refuses a
higher major version, so a major bump would make a rollback fail setup; an
older release opens a 14.2 file, runs its two-argument migrate function and
saves it back as 14.1. The major steps move unchanged into
_async_migrate_major, which the major-step tests now call by that name.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log -1 --format=%s
```

---

## Task 5: Every writer and every `now` on HA's clock — 19 sites

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py:12, :30, :267, :379, :432, :498, :934`
- Modify: `custom_components/irrigation_plus/continuous_update.py:55, :69-74, :252, :375-378, :521`
- Modify: `custom_components/irrigation_plus/store.py:191, :1653`
- Modify: `custom_components/irrigation_plus/__init__.py:6-12, :55-67, :1429, :1506, :1516, :1632, :1644, :1799, :2019-2025`
- Modify: `custom_components/irrigation_plus/weather_aggregate.py:45, :356-371, :924-939, :1119-1134`
- Test: `tests/test_weather_buffer_one_frame.py` (from Task 1), `tests/test_continuous_update.py`, `tests/test_store_operations.py`, `tests/test_zone_view_save.py`

- [ ] **Step 1: Three writer tests expect HA's clock**

Each asserts the stamp one writer leaves; each expected the process's clock.

`tests/test_continuous_update.py` — add after
`from homeassistant.const import CONF_ELEVATION, STATE_UNAVAILABLE, STATE_UNKNOWN`:

```python
from homeassistant.util import dt as dt_util
```

and replace

```python
        # Keeps the FIRST reading's stamp, not the merged-in one.
        assert rows[0][const.RETRIEVED_AT] == datetime.datetime(2026, 8, 8, 12, 0, 0)
```

with

```python
        # Keeps the FIRST reading's stamp, not the merged-in one -- on HA's clock, the
        # frame every weather-buffer stamp is written in.
        assert rows[0][const.RETRIEVED_AT] == dt_util.as_local(
            datetime.datetime(2026, 8, 8, 12, 0, 0, tzinfo=datetime.UTC)
        ).replace(tzinfo=None)
```

`tests/test_store_operations.py`, in `test_new_zone_anchors_last_consumed_at` — replace

```python
        import datetime

        store = SmartIrrigationStorage(hass)
        await store.async_load()

        before = datetime.datetime.now()
```

with

```python
        from homeassistant.util import dt as dt_util

        store = SmartIrrigationStorage(hass)
        await store.async_load()

        # HA's clock, naive: the frame every weather-buffer stamp is written in.
        before = dt_util.now().replace(tzinfo=None)
```

and

```python
        after = datetime.datetime.now()
```

with

```python
        after = dt_util.now().replace(tzinfo=None)
```

`tests/test_zone_view_save.py` — add after `from freezegun import freeze_time`:

```python
from homeassistant.util import dt as dt_util
```

and replace

```python
    assert after[const.ZONE_LAST_CONSUMED] == SAVED_AT
```

with

```python
    # The moment of the save, on HA's clock -- the frame the window is measured in.
    assert after[const.ZONE_LAST_CONSUMED] == dt_util.as_local(
        SAVED_AT.replace(tzinfo=datetime.UTC)
    ).replace(tzinfo=None)
```

- [ ] **Step 2: Run them to verify they fail**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_weather_buffer_one_frame.py "tests/test_continuous_update.py::TestCoalescing::test_burst_of_different_fields_merges_into_one_row" "tests/test_store_operations.py::TestZoneOperations::test_new_zone_anchors_last_consumed_at" "tests/test_zone_view_save.py::test_a_lowered_maximum_clamps_the_stored_level_as_a_statement" -p _local_socket_unblock -q --no-header --tb=line
```

Expected: `15 failed` —
- the file from Task 1, all twelve: daily/older release `assert [1.0] == [3.0 ± 3.0e-06]`;
  daily/this release `assert [[(10.5, 2.0)... (12.5, 2.0)]] == [[(12.5, 2.0)... (14.5, 2.0)]]`;
  live/older release `assert 1.0 == 3.0 ± 3.0e-06` (the call without `now`); live/this release
  `assert 5.0 == 3.0 ± 3.0e-06`; the six writers `10:00 == 12:00`; the solar clamp
  `70.37467824637923 == 86.4`; the census with 19 entries (`helpers.py:1015` went in Task 2);
- `test_continuous_update.py`: `assert HAFakeDatetime(2026, 8, 8, 12, 0) ==
  datetime.datetime(2026, 8, 8, 5, 0)`;
- `test_store_operations.py`: `before <= watermark` fails, the watermark seven hours behind
  `before` (process UTC against HA's US/Pacific);
- `test_zone_view_save.py`: `assert HAFakeDatetime(2026, 5, 22, 9, 0) ==
  datetime.datetime(2026, 5, 22, 2, 0)`.

- [ ] **Step 3: `calculation.py`**

Replace `from datetime import datetime, timedelta` (`:12`) with

```python
from datetime import timedelta
```

replace `from .helpers import convert_between, loadModules` (`:30`) with

```python
from .helpers import convert_between, loadModules, local_naive_now
```

and replace **all five** occurrences of `= datetime.now()` (Edit with `replace_all`; `:267`,
`:379`, `:432`, `:498`, `:934` — the comments at `:52`, `:789`, `:1194` have no `= ` and stay
for Task 6) with `= local_naive_now()`.

- [ ] **Step 4: `continuous_update.py`**

Replace `from datetime import datetime, timedelta` (`:55`) with

```python
from datetime import timedelta
```

replace (`:69-74`)

```python
from .helpers import (
    convert_mapping_to_metric,
    resolve_sensor_unit,
```

with

```python
from .helpers import (
    convert_mapping_to_metric,
    local_naive_now,
    resolve_sensor_unit,
```

replace (`:375-378`)

```python
        # Naive local, exactly like the interval path's RETRIEVED_AT — the two
        # write into the SAME buffer and aggregate_window compares the stamps
        # against a naive-local watermark, so a tz-aware value here would raise.
        timestamp = datetime.now()
```

with

```python
        # Naive on HA's clock, exactly like the interval path's RETRIEVED_AT -- the
        # two write into the SAME buffer and aggregate_window compares the stamps
        # against a watermark in that frame, so a tz-aware value here would raise.
        timestamp = local_naive_now()
```

and then the two remaining `= datetime.now()` (`:252`, `:521`; `replace_all`) with
`= local_naive_now()`.

- [ ] **Step 5: `store.py`**

Replace the import from Task 4

```python
from .helpers import as_datetime, lift_legacy_stamp, loadModules, zone_depth_default
```

with

```python
from .helpers import (
    as_datetime,
    lift_legacy_stamp,
    loadModules,
    local_naive_now,
    zone_depth_default,
)
```

and in `async_create_zone` (`:1653`) replace `last_consumed_at=datetime.datetime.now()` with
`last_consumed_at=local_naive_now()`.

- [ ] **Step 6: `__init__.py`**

First the alias and its note (`:6-12`) — the note names `dt_datetime.now()`, so it goes before
the replace below. Replace

```python
import asyncio
import logging

# NB: alias the stdlib datetime class. This package ships a ``datetime.py``
# platform module (the rain-delay DateTimeEntity); importing that platform sets
# the ``datetime`` attribute on this package — which IS this module's global
# namespace — clobbering a global literally named ``datetime`` and breaking
# ``dt_datetime.now()`` at runtime. The alias keeps our global name collision-free.
from datetime import datetime as dt_datetime
from datetime import timedelta
```

with

```python
import asyncio
import logging
from datetime import timedelta
```

(`tests/test_datetime_platform_shadowing.py` still holds: no global named `datetime`, no
`datetime.now()` call.) Replace (`:61-62`)

```python
    corrected_azimuth_bearing,
    loadModules,
```

with

```python
    corrected_azimuth_bearing,
    loadModules,
    local_naive_now,
```

replace the writer in `_book_asserted_bucket` with its comment (`:2019-2025`)

```python
                # Naive local time, the convention every other writer of this
                # field uses -- ``calculation.py`` stamps it from the stdlib
                # clock, and an aware stamp would not compare against the
                # buffer's own. Aliased, because a global named ``datetime``
                # here is shadowed by the platform submodule of that name
                # (see tests/test_datetime_platform_shadowing.py).
                const.ZONE_LAST_CONSUMED: dt_datetime.now(),
```

with

```python
                # Naive on HA's clock, the frame every other writer of this field
                # uses -- an aware stamp would not compare against the buffer's own.
                const.ZONE_LAST_CONSUMED: local_naive_now(),
```

and then the six remaining `dt_datetime.now()` (`:1429` — the solar clamp — `:1506`, `:1516`,
`:1632`, `:1644`, `:1799`; `replace_all`) with `local_naive_now()`.

- [ ] **Step 7: `weather_aggregate.py`**

Replace `from .helpers import STAMP_FROM_STORE, coerce_stamp` (`:45`) with

```python
from .helpers import STAMP_FROM_STORE, coerce_stamp, local_naive_now
```

and replace **all three** identical blocks (`aggregate_window`, `build_hourly_rows`,
`build_substeps`; `replace_all`)

```python
    # `now` is the one input here whose provenance depends on the CALLER: the daily
    # calculation passes its own process clock, the live estimate passes HA-local, and
    # one live-estimate call site passes nothing and lands on this default. Nothing in
    # the signature can say which, so the coercion is the store's -- the frame of the
    # row stamps this value is about to be compared against, and the only frame in
    # which that comparison means anything. A naive value, which is every one of them
    # today, comes back untouched.
    # NOT-TO-DO: do not add a provenance parameter here to "solve" it. Measured: `now=`
    #   appears 94 times across 9 test files, so a required argument is ~94 test edits
    #   in a change whose whole point is that it moves no number.
    # siehe tests/test_weather_aggregate.py::TestTheEntryPointsSurviveAnAwareNow
    now = (
        coerce_stamp(now, STAMP_FROM_STORE)
        if now is not None
        else datetime.datetime.now()
    )
```

with

```python
    # `now` arrives naive on HA's clock from every caller -- the daily calculation and
    # the live estimate both read local_naive_now() -- and the default is that clock
    # too. An aware `now` is read on HA's clock by the store coercion, the frame of the
    # row stamps it is compared against; a naive one comes back untouched.
    # NOT-TO-DO: do not add a provenance parameter here: with one frame on every path
    #   there is nothing left for it to choose.
    # siehe tests/test_weather_aggregate.py::TestTheEntryPointsSurviveAnAwareNow
    now = coerce_stamp(now, STAMP_FROM_STORE) if now is not None else local_naive_now()
```

- [ ] **Step 8: Run them to verify they pass**

The command of Step 2. Expected: `15 passed`. `black` leaves all 69 files unchanged — the code
above is already in its format.

- [ ] **Step 9: The neighbours**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_continuous_update.py tests/test_store_operations.py tests/test_zone_view_save.py tests/test_datetime_platform_shadowing.py tests/test_solar_ingest_clamp.py tests/test_weather_aggregate.py tests/test_time_provenance.py tests/test_live_estimate_time_provenance.py tests/test_store_stamp_migration.py -p _local_socket_unblock -q --no-header --tb=line 2>&1 | tail -3
```

Expected: `182 passed, 12 errors`. The twelve are `test_solar_ingest_clamp.py`'s
lingering-timer teardown errors (its `coordinator` fixture leaves the midnight counter
armed), the same twelve names the baseline lists; the new file's coordinators release theirs.

- [ ] **Step 10: Lint, then commit**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && uvx black custom_components/irrigation_plus/ ; uvx ruff check custom_components/irrigation_plus/ ; git add custom_components/irrigation_plus/calculation.py custom_components/irrigation_plus/continuous_update.py custom_components/irrigation_plus/store.py custom_components/irrigation_plus/__init__.py custom_components/irrigation_plus/weather_aggregate.py tests/test_weather_buffer_one_frame.py tests/test_continuous_update.py tests/test_store_operations.py tests/test_zone_view_save.py ; git diff --cached --name-only | wc -l
```

Expected: clean; `9`.

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && git commit -q -F - <<'EOF'
fix(time): write and compare the weather-buffer stamps on HA's clock

Nineteen sites read the process's clock: thirteen that persist a buffer
stamp, three that only compare (the prune default, the calculate_module
default, the solar clamp) and the three entry-point defaults in
weather_aggregate. All of them now read local_naive_now(). On a container
without TZ= the daily path priced its hours two hours early (solar
geometry) and the live estimate measured a three-hour window for one hour;
the ingest clamp judged a reading at the wrong hour of sun. The end-to-end
matrix pins both paths on a migrated and on a freshly written store.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log -1 --format=%s
```

---

## Task 6: The comments and the user doc this change makes false

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py:47-56`, `:776-802`, `:1193-1197`
- Modify: `custom_components/irrigation_plus/auto_calc.py:93-95`, `custom_components/irrigation_plus/sensor.py:603-608`, `custom_components/irrigation_plus/const.py:734`, `custom_components/irrigation_plus/store.py:1984-1988` (at `0b9a71bd`; after Tasks 4 and 5 it sits about 50 lines lower), `custom_components/irrigation_plus/weather_aggregate.py:337`
- Modify: `docs/usage-troubleshooting.md:28-59`, `docs/installation-download.md:31`

No test: these are comments and prose. The criterion, named before the change: after it, the
grep in Step 3 finds the process's clock only where the text is about the past or the
migration.

- [ ] **Step 1: The code comments**

`calculation.py`, the docstring of `pending_bucket_events` — replace

```python
    Stored aware (see ``IrrigationRunnerMixin.async_write_watered_bucket``) and
    flattened to naive local here, because the window these have to be placed on
    is built from naive ``datetime.now()`` stamps and mixing the two raises.
```

with

```python
    Stored aware (see ``IrrigationRunnerMixin.async_write_watered_bucket``) and
    flattened to naive HA-local here, because the window these have to be placed on
    is built from naive stamps on HA's clock (``local_naive_now()``) and mixing the
    two raises.
```

`calculation.py`, in `_hourly_et_for_zone` — replace

```python
        # Buffer stamps are naive LOCAL times, so the solar-time correction wants
        # the local UTC offset. The site timezone is passed alongside so each row
```

with

```python
        # Buffer stamps are naive on HA's clock, so the solar-time correction wants
        # HA's UTC offset. The site timezone is passed alongside so each row
```

and replace the block

```python
        # ⚠️ MISMATCHED FRAMES, named here rather than left implicit.
        # This offset is HA's. The `now` handed to the same call below is
        # `datetime.now()`, i.e. the PROCESS's clock, and the buffer stamps it is
        # measured against are process-local too. On HA OS and Supervised the two
        # agree, which is why this went unnoticed; on Docker or Core without `TZ=`
        # the solar-time correction applies HA's offset to a process-local stamp.
        # By this module's own figures that is 0.26-0.74 % on daily ETo but
        # +23.5 % / -16 % on the radiation the clearness-ratio hold refills, because
        # Rso sits in the denominator there.
        # NOT-TO-DO: do not expect a switch to aware timestamps to fix this by itself.
        #   The offset does not travel as `tzinfo` -- it travels as this float, through
        #   `SiteGeometry.tz_offset_h` and on into `row["tz_offset_h"]`. A stamp that
        #   becomes aware leaves this arithmetic untouched and the suite green, which
        #   is exactly how the expensive half of this could be missed.
        # Not corrected here on purpose: correcting it moves numbers, and it has to
        # move together with the writers.
```

with

```python
        # This offset is HA's, and so are the stamps and the `now` it is applied to:
        # the writers read local_naive_now() and the store moved older stamps at 14.2.
        # They used to be the PROCESS's clock, and on Docker or Core without `TZ=` this
        # correction then priced the wrong hour of sun -- 0.26-0.74 % on daily ETo, but
        # +23.5 % / -16 % on the radiation the clearness-ratio hold refills, where Rso
        # sits in the denominator.
        # NOT-TO-DO: do not expect aware timestamps to guard this. The offset does not
        #   travel as `tzinfo` -- it travels as this float, through
        #   `SiteGeometry.tz_offset_h` and on into `row["tz_offset_h"]`, so a stamp in
        #   the wrong frame leaves this arithmetic untouched and the suite green. The
        #   row hour shows it: tests/test_weather_buffer_one_frame.py.
```

`calculation.py`, in `calculate_module` — replace

```python
                # dt_util, deliberately not this method's own `now`: that parameter
                # defaults to a bare datetime.now(), which is naive process-local
                # and is the seam #160 is about to move. expected_rain
                # compares aware instants either way, so taking the moment from
                # dt_util keeps this independent of how that lands.
```

with

```python
                # dt_util, deliberately not this method's own `now`: that value is
                # naive on HA's clock, and expected_rain compares aware instants.
                # Taking the moment from dt_util keeps this independent of the naive
                # frame the buffer uses.
```

`auto_calc.py` — replace

```python
        # Naive local, because that is what the store holds: calculation.py
        # stamps last_calculated with a bare datetime.now(). Comparing in that
        # space is what _parse_stored_as_ha_local exists for.
```

with

```python
        # Naive on HA's clock, because that is what the store holds: calculation.py
        # stamps last_calculated with local_naive_now(), and _parse_stored_as_ha_local
        # reads it in the same frame.
```

`sensor.py`, the docstring of `_to_aware_datetime` — replace

```python
    The store writes naive local datetimes (``datetime.now()``) for
    last_calculated/last_updated and aware ones (``dt_util.now()``) for
    last_irrigation; naive values are interpreted as local time.
```

with

```python
    The store writes last_calculated/last_updated naive on HA's clock
    (``local_naive_now()``) and last_irrigation aware (``dt_util.now()``); a naive
    value is therefore given HA's zone.
```

`const.py` — replace

```python
RETRIEVED_AT = "retrieved"  # when HA fetched the data (datetime.now())
```

with

```python
RETRIEVED_AT = "retrieved"  # when the data was fetched: naive, HA's clock
```

`store.py`, in `merge_or_append_mapping_reading` — replace

```python
            # A row loaded from disk still carries RETRIEVED_AT as the ISO
            # string the JSON round-trip left it in (async_load never converts
            # buffer rows the way it does zone watermarks) -- coerce before
            # comparing against the datetime coalesce_before/min_watermark, or
            # the very first reading after a restart raises.
```

with

```python
            # A row loaded from disk still carries RETRIEVED_AT as the ISO
            # string the JSON round-trip left it in -- async_load converts no
            # stamp, neither the buffer rows nor the zone watermarks -- so parse
            # it before comparing against the datetime coalesce_before /
            # min_watermark, or the very first reading after a restart raises.
```

`weather_aggregate.py`, in the docstring of `aggregate_window` (`:337`) — replace

```python
        now: override for "now" (testing); defaults to ``datetime.now()``.
```

with

```python
        now: override for "now" (testing); defaults to ``local_naive_now()``, HA's clock.
```

- [ ] **Step 2: The user doc**

`docs/usage-troubleshooting.md` — replace the whole section from
`## Docker or Core: the container's time zone {#container-timezone}` (`:28`) down to (not
including) the page footer after it, `> Main page: [Usage](usage.md)<br/>` (`:61`; the same
line also heads the page at `:7`), with

```markdown
## Docker or Core: the container's time zone {#container-timezone}

The integration stamps its weather readings on the clock you set in Home Assistant, under
**Settings → System → General**. The time zone of the container Home Assistant runs in
does not change the calculation.

Earlier releases stamped the readings on the container's clock. If you ran Home Assistant
in Docker, or as a Core install in a virtual environment, and the container's time zone
differed from Home Assistant's, the intra-day live estimate pulled away from the figure
the nightly calculation commits, and on installs that use solar radiation the radiation
figures were off as well. Home Assistant OS and Supervised keep the two in step, so this
could not happen there.

**When you upgrade from such a release,** the stamps already stored are converted once,
read in the container's time zone as it is at that moment. Leave the container's `TZ` as
it is until the upgrade has run. If you change it at the same time, the first
calculation afterwards covers a window stretched or squeezed by the difference; the next
one is right again.

```

`docs/installation-download.md` — delete step 5 of "After installing" (`:31`), the line that
begins `5. If you run Home Assistant in **Docker** or as a **Core** install, set the
container's `TZ`` — a new install no longer needs it, and the troubleshooting note covers an
upgrade.

- [ ] **Step 3: Check what is left**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && grep -n "PROCESS's clock\|process's clock\|bare datetime.now\|bare \`\`datetime.now\|process-local\|datetime.now()" custom_components/irrigation_plus/*.py ; grep -n "TZ" docs/installation-download.md docs/usage-troubleshooting.md
```

Expected — the code lines, and only these (line numbers after Tasks 2–6):
`calculation.py:790` ("They used to be the PROCESS's clock"), `helpers.py:1011`, `:1013`
(`_process_timezone`), `:1025` (`coerce_stamp`'s Wurzel), `:1058`, `:1059`
(`local_naive_now`'s Wurzel), `:1071` (`lift_legacy_stamp`), `live_estimate.py:196`
(`_parse_stored_as_ha_local`'s Wurzel), `store.py:615` (`_lift_legacy_stamps`'s Wurzel) — each
about the time before this change or about the migration — and `services.py:273`, `:289`,
`watering_calendar.py:79`, `:93` (`generated_at`, out of scope). In the docs only
`docs/usage-troubleshooting.md:42` (the upgrade advice); `installation-download.md` names no
`TZ` any more.

- [ ] **Step 4: Lint, then commit**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && uvx black custom_components/irrigation_plus/ ; uvx ruff check custom_components/irrigation_plus/ ; git add custom_components/irrigation_plus/calculation.py custom_components/irrigation_plus/auto_calc.py custom_components/irrigation_plus/sensor.py custom_components/irrigation_plus/const.py custom_components/irrigation_plus/store.py custom_components/irrigation_plus/weather_aggregate.py docs/usage-troubleshooting.md docs/installation-download.md ; git diff --cached --name-only | wc -l
```

Expected: clean; `8`.

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && git commit -q -F - <<'EOF'
docs(time): say which clock the buffer stamps are on

The comments that described the stamps as process-local, or the comparison
as mismatched, describe the code before this series. The troubleshooting
note told Docker and Core users to set TZ so the calculation came out
right; it no longer depends on it, and changing TZ at the upgrade is now
the one way to misread a window, so the note says to leave it until the
upgrade has run.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log -1 --format=%s
```

---

## Task 7: Gates

- [ ] **Step 1: Lint on the final tree**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && uvx black --check custom_components/irrigation_plus/ ; uvx ruff check custom_components/irrigation_plus/
```

Expected: `69 files would be left unchanged.` and `All checks passed!`

- [ ] **Step 2: The full suite, in the background**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && export TEMP=D:/Entwicklung/HASI/issue22-work/tmp TMP=D:/Entwicklung/HASI/issue22-work/tmp TMPDIR=D:/Entwicklung/HASI/issue22-work/tmp ; TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header > /d/Entwicklung/HASI/issue22-work/measure/branch-full-tzutc.txt 2>&1 ; tail -1 /d/Entwicklung/HASI/issue22-work/measure/branch-full-tzutc.txt
```

After it has ended:

```bash
cd /d/Entwicklung/HASI/issue22-work/measure && grep -E "^(FAILED|ERROR) tests/" branch-full-tzutc.txt | sed 's/ - .*//' | sort -u > branch-names.txt ; diff baseline-names.txt branch-names.txt && echo "names identical"
```

Expected: `7 failed, 3489 passed, 9 skipped, 11 warnings, 367 errors`, then `names identical`.
3489 = the baseline's 3466 + 23 new tests (12 in Task 1's file, 9 in the migration file, 2 in
`test_time_provenance.py`; the inverted pins replace tests, they add none). Every one of the
367 errors is the baseline's lingering-timer teardown error.

- [ ] **Step 3: No tracker reference, no stray names**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && git diff upstream/master -- custom_components/ tests/ docs/ | grep -nE "^\+.*(Eifel|#22\b|Rev(ision)? ?[34]|R4-|\bA[1-8]\b|\bspec\b|Task [0-9]|\b[BFM]-?[0-9]{1,2}\b)" ; git log --format=%B upstream/master..HEAD | grep -nE "Eifel|#22\b|Rev(ision)? ?[34]|R4-|Task [0-9]|\bspec\b"
```

Expected: both empty.

- [ ] **Step 4: The diff is what the plan says**

```bash
cd /d/Entwicklung/HASI/issue22-work/wt && git diff --stat upstream/master | tail -1 ; git diff --name-only upstream/master | sort
```

Expected: `28 files changed, 1194 insertions(+), 345 deletions(-)` (production and docs
+252/−226, most of it comments; tests +942/−119), and these 28 files:
the ten under `custom_components/irrigation_plus/` (`__init__.py`, `auto_calc.py`,
`calculation.py`, `const.py`, `continuous_update.py`, `helpers.py`, `live_estimate.py`,
`sensor.py`, `store.py`, `weather_aggregate.py`), the two docs, the two new test files and
fourteen changed ones (`test_batch_config_survives_v14.py`, `test_continuous_update.py`,
`test_live_estimate_time_provenance.py`, `test_master.py`, `test_schedule_migration_v14.py`,
`test_store.py`, `test_store_distributor.py`, `test_store_legacy_migrations.py`,
`test_store_operations.py`, `test_time_provenance.py`, `test_unit_system_migration.py`,
`test_weather_aggregate.py`, `test_zone_depth_defaults.py`, `test_zone_view_save.py`). No
frontend file, no `dist/` bundle, no `manifest.json`.

No commit: nothing has changed.

---

## Task 8: Mutation matrix

Each mutation must be killed by at least one named test. The runner is archived beside this
plan, `docs/superpowers/probes/2026-09-30-weather-buffer-mutate.py` on `archive/design-history`.
It applies one mutation at a time (exact match, line endings kept), runs the eight test files
this change touches under `TZ=UTC` with a 300 s timeout, restores the touched file byte for
byte, and at the end compares every source's sha256 with a snapshot taken before the first
mutation. Fourteen hand-written mutations (M01–M14: the helpers, the migration, the version
numbers), then the 19 clock sites each reverted on its own the way a regression would look —
the stdlib clock imported and called by its usual name (S01–S19). M02 (`_process_timezone`
back to a fixed offset) runs twice, with and without `TZ=UTC`: only a DST zone shows it
behaviourally.

- [ ] **Step 1: Run it, in the background (tool option), about 20 minutes**

```bash
cp /d/Entwicklung/HASI/pr139-work/archive-wt/docs/superpowers/probes/2026-09-30-weather-buffer-mutate.py /d/Entwicklung/HASI/issue22-work/probe/mutate.py ; cd /d/Entwicklung/HASI/issue22-work/wt && git status --short ; PYTHONIOENCODING=utf-8 /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe ../probe/mutate.py /d/Entwicklung/HASI/issue22-work/wt > ../measure/mutations-run.txt 2>&1 ; tail -2 ../measure/mutations-run.txt
```

`git status --short` must be empty before the run (the runner restores files, it does not
commit), and again after it. The per-mutation killers land in
`D:\Entwicklung\HASI\issue22-work\probe\mutations-result.json`.

Expected, as measured on 2026-09-30 with this plan's final Task 1 file: `33` lines `KILLED`,
then `every source restored byte-for-byte: True`, and `git status --short` empty. S-ids carry
the line numbers after Tasks 2–6; `test_a_store_…` appears once per path class (daily, live).

| id | mutation | verdict | killed by (tests, besides the census) |
|---|---|---|---|
| M01 | local_naive_now returns the process clock | KILLED | census; `test_burst_of_different_fields_merges_into_one_row`, `test_new_zone_anchors_last_consumed_at` +13 |
| M02 | _process_timezone back to today's fixed offset (needs a DST zone) | UTC:KILLED / no-TZ:KILLED | census; `test_the_process_zone_is_read_with_its_own_rules` (without `TZ=UTC` only) |
| M03 | coerce_stamp: an aware stored stamp on the process's clock again | KILLED | `test_a_stored_stamp_is_read_on_has_clock`, `test_an_aware_instant_is_read_on_has_clock_under_either_provenance` +4 |
| M04 | lift_legacy_stamp leaves a naive stamp as it is | KILLED | `test_a_14_2_file_comes_back_untouched_and_is_saved_as_14_1`, `test_an_older_major_is_moved_as_well` +6 |
| M05 | lift_legacy_stamp reads a naive stamp in the machine's zone, not the seam | KILLED | `test_each_stamp_is_read_at_its_own_dates_offset` |
| M06 | lift_legacy_stamp returns a datetime, not a string | KILLED | `test_an_aware_stamp_is_read_as_the_instant_it_names`, `test_an_older_major_is_moved_as_well` +4 |
| M07 | the stamp step keyed on 14.1 instead of 14.2 | KILLED | `test_a_14_2_file_comes_back_untouched_and_is_saved_as_14_1`, `test_an_aware_stamp_is_read_as_the_instant_it_names` +6 |
| M08 | the stamp step on every load, 14.2 included | KILLED | `test_a_store_at_14_2_or_later_is_left_alone` |
| M09 | STORAGE_MINOR_VERSION stays 1 | KILLED | `test_a_14_2_file_comes_back_untouched_and_is_saved_as_14_1`, `test_a_14_1_file_is_moved_and_saved_as_14_2` +3 |
| M10 | a MAJOR bump instead (STORAGE_VERSION 15) | KILLED | `test_a_14_2_file_comes_back_untouched_and_is_saved_as_14_1`, `test_a_14_1_file_is_moved_and_saved_as_14_2` +3 |
| M11 | the buffer rows are not moved | KILLED | `test_an_aware_stamp_is_read_as_the_instant_it_names`, `test_an_older_major_is_moved_as_well` +3 |
| M12 | data_last_updated is not moved | KILLED | `test_an_aware_stamp_is_read_as_the_instant_it_names`, `test_an_older_major_is_moved_as_well` +2 |
| M13 | last_calculated is not moved | KILLED | `test_an_aware_stamp_is_read_as_the_instant_it_names`, `test_an_older_major_is_moved_as_well` +2 |
| M14 | the hook never runs the stamp step | KILLED | `test_a_14_2_file_comes_back_untouched_and_is_saved_as_14_1`, `test_an_aware_stamp_is_read_as_the_instant_it_names` +7 |
| S01 | calculation.py:268 back on the process clock | KILLED | census; `test_clearing_the_weather_data` |
| S02 | calculation.py:380 back on the process clock | KILLED | census only — the prune default, which no in-repo caller reaches |
| S03 | calculation.py:433 back on the process clock | KILLED | census; `test_a_store_this_release_wrote` (daily, live) |
| S04 | calculation.py:499 back on the process clock | KILLED | census; `test_a_store_an_older_release_left`, `test_a_store_this_release_wrote` |
| S05 | calculation.py:930 back on the process clock | KILLED | census only — `calculate_module`'s default, which no in-repo caller reaches |
| S06 | continuous_update.py:253 back on the process clock | KILLED | census; `test_the_baseline_a_new_sensor_subscription_seeds` |
| S07 | continuous_update.py:379 back on the process clock | KILLED | census; `test_burst_of_different_fields_merges_into_one_row` |
| S08 | continuous_update.py:522 back on the process clock | KILLED | census; `test_a_burst_of_sensor_events` |
| S09 | __init__.py:1423 back on the process clock | KILLED | census; `test_a_bright_early_afternoon_is_judged_at_its_own_hour` |
| S10 | __init__.py:1500 back on the process clock | KILLED | census; `test_the_poll_of_one_zone` |
| S11 | __init__.py:1510 back on the process clock | KILLED | census; `test_the_poll_of_one_zone` |
| S12 | __init__.py:1626 back on the process clock | KILLED | census; `test_the_poll_of_every_group` |
| S13 | __init__.py:1638 back on the process clock | KILLED | census; `test_the_poll_of_every_group` |
| S14 | __init__.py:1793 back on the process clock | KILLED | census; `test_a_sensor_group_switching_its_source` |
| S15 | __init__.py:2015 back on the process clock | KILLED | census; `test_a_lowered_maximum_clamps_the_stored_level_as_a_statement` |
| S16 | store.py:1722 back on the process clock | KILLED | census; `test_new_zone_anchors_last_consumed_at` |
| S17 | weather_aggregate.py:356 back on the process clock | KILLED | census; `test_a_store_an_older_release_left`, `test_a_store_this_release_wrote` (live, the call without `now`) |
| S18 | weather_aggregate.py:916 back on the process clock | KILLED | census only — `build_hourly_rows`'s default, which no in-repo caller reaches |
| S19 | weather_aggregate.py:1103 back on the process clock | KILLED | census only — `build_substeps`'s default, which no in-repo caller reaches |

No commit: the tree is restored.

---

## Task 9: Review

Per skill `superpowers:requesting-code-review`, on `upstream/master..HEAD`, with the design doc
(Revision 4 + Addendum 2026-09-30) and this plan. The reviewer checks: every requirement of
the Addendum implemented (minor version, split hook, both assumptions in the comment,
JustChr's test); the matrix asserts exact values; nothing outside the scope table changed.
Findings go through `superpowers:receiving-code-review`; a fix is a new commit with its own
failing test, and its mutation joins Task 8.

---

## Task 10: Live test on HA-Test

The one property no local test can show is Home Assistant's own guard: the local test HA
(2024.12.5) and CI's floor (2025.5.0) have none, and CI's newest HA runs it only inside the
suite. HA-Test runs it for real. HA-Test is disposable and may be restarted — announce every
restart (memory `ha-no-auto-restart`).

Build and install a throwaway pre-release the way the distributor inlet gate did it (its
protocol: `docs/superpowers/reconstructed/2026-09-30-distributor-inlet-open-gate-live-on-ha-test.md`,
memory `hasi-production-on-upstream` for the ZIP): the branch head plus the version string,
tag `v<date>b1`, pre-release with the ZIP, installed through HACS. Branch push, tag and
release go to the fork, i.e. outward: **one approval in the chat first**, for all three.

- [ ] **L0 — Before:** note HA-Test's Home Assistant version (must be ≥ 2026.3 for L2 to
  exercise the guard; read on 2026-09-30: `core-2026.9.3`, HA OS 18.3, zone Europe/Berlin),
  the installed Irrigation Plus version, and per zone `last_calculated` as the zone sensors
  show it. Set the logger for `homeassistant.helpers.storage` to `info` (service
  `logger.set_level`).
- [ ] **L1 — Upgrade:** install the pre-release, restart. Expected: the log line
  `Migrating irrigation_plus.storage storage from 14.1 to 14.2`, the integration loaded, no
  error from `irrigation_plus`. HA OS keeps the process zone equal to HA's, so every
  `last_calculated` is unchanged — the migration is the identity there.
- [ ] **L2 — Roll back** to the release installed before L1, restart. Expected:
  `Migrating irrigation_plus.storage storage from 14.2 to 14.1`, **no**
  `UnsupportedStorageVersionError`, the integration loaded and its entities available.
- [ ] **L3 — Upgrade again**, restart. Expected: `from 14.1 to 14.2` again, loaded.
- [ ] **L4 — Put HA-Test back** as found: the version from L0 (or leave the pre-release if the
  user says so), the logger level. Record L0–L4 with log excerpts in
  `docs/superpowers/reconstructed/<date>-weather-buffer-one-frame-live-on-ha-test.md`.

---

## Task 11: Archive, PR text, PR, issues

- [ ] **Step 1:** design docs to `archive/design-history` (Regel P1): this plan with its
  checkboxes, the Task 10 protocol, the mutation runner and its result. Recipe: memory
  `preserve-design-docs-archive-branch`.
- [ ] **Step 2:** PR text, English, per skill `pr-workflow` — `## Problem` (the two clocks,
  measured: live window 3.0 h for 1.0 h, daily row hour 10.5 for 12.5, the clamp at the wrong
  hour), `## Fix` (one clock; the minor-version migration and why minor; the two assumptions
  for the release notes; the doc change), `## Testing` (the matrix, the migration tests,
  the two-argument test JustChr asked for, the mutation count, the live test L1–L3).
  No `Eifel-Joe`, no branch SHAs (memories `no-own-issue-refs-upstream`,
  `no-branch-shas-in-upstream-comments`). **Shown in the chat and approved before `gh`.**
- [ ] **Step 3:** after approval: `git push -u origin fix/weather-buffer-one-frame`, then
  `gh pr create --repo JustChr/HAsmartirrigation --base master --head
  Eifel-Joe:fix/weather-buffer-one-frame --title "…" --body-file <file>`; bind the PR
  (`ccd_pr`).
- [ ] **Step 4:** Eifel-Joe#22: a status comment (English above, German below) linking the PR;
  the label stays `upstream:freigegeben` (JustChr approved the build on `JustChr#160`);
  Eifel-Joe#42's index line. Texts approved in the chat first; posted equals approved (compare
  as JSON). After the merge: close Eifel-Joe#22 (Regel P2), move `issue22-work` to
  `_erledigt`, then the production rebuild with everything new (memory
  `hasi-production-on-upstream`).

---

## Findings of the dry run (2026-09-30) — the text above already carries them

**D1 — The one-hour scene was blind in the daily cell once the migration is in.** Revision 4's
criterion (1.0 h, row `[12.5]`) was drafted for one real hour. `_hour_multiplier`
(`weather_aggregate.py:311-318`) returns `abs(now - watermark)`, and with a +2 h offset a
process-clock `now` (11:00) against a migrated watermark (12:00) gives |−1 h| = 1 h: after
Task 4 the daily cell on the older release's store passed although the daily path still read
the process's clock. The scene now spans three real hours (10:00 → 13:00 UTC; 3.0 h, rows
12.5 / 13.5 / 14.5): on the base every cell fails as an offset, and after Task 4 the daily
cell fails on the window, `[1.0] == [3.0]`. The `abs()` — a negative window priced as a
positive one — is left as it is; it is a question of its own, not this change's.

**D2 — `sed -i` under Git Bash writes LF**, not the CRLF the text first claimed; git
normalises on `add`, the commit carries the renamed lines only. The rename check needed
`--include=*.py` (it matched `__pycache__`).

**D3 — The troubleshooting page carries its footer line twice** (`:7`, `:61`); Task 6 names the
one after the section.

**D4 — `aggregate_window`'s docstring said the default is `datetime.now()`**
(`weather_aggregate.py:337`); found by Task 6's grep, now part of Task 6.

**D5 — Task 6's first `calculation.py` replacement ended mid-line** and could not match; it
takes the two lines whole now.

**D6 — Every test in this repo has the `hass` fixture.** `tests/conftest.py:56` is autouse and
pulls it in through `enable_custom_integrations`, so HA is on US/Pacific even in tests that
take no `hass` parameter. This is why six existing tests reacted (Tasks 3 and 5) and why the
aware twins are built in HA's zone rather than in UTC.

**D7 — Thirteen of the nineteen clock sites were pinned by the census alone.** The first
mutation run killed 33 of 33, but for 13 sites the only killer was the source census. A
regression spelled differently — `dt_util.utcnow()` stripped of its zone — would have passed:
with a sensor group of constant values it does not matter which hour a buffer row lands in,
so the matrix could not see the row stamps. Task 1's file now drives each reachable writer
once and asserts the stamp it leaves (`TestEveryWriterStampsHAsClock`: both polls, the
weather-data reset, a source change, a sensor burst, the baseline seed), and the live path
asserts the call without `now` as well. Second run: 15 of the 19 sites are killed by a
behavioural test too; the census alone keeps the four defaults no in-repo caller reaches.

**For the review (Task 9), not changed:** `test_aggregate_window_accepts_an_aware_now` and
`test_build_hourly_rows_accepts_an_aware_now` pass on both sides (Task 3 Step 2); they pin
"an aware `now` does not raise", not its frame.
