# A zone save sends what the edit changed — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A zone settings page left open across a run no longer writes the run's credit
back when any setting is edited.

**Architecture:** One piece per layer. The panel's `handleEditZone` receives only the change
an input sets, collects it per zone and posts `{id, ...changes}`, sending a cleared field as
`null`; its 35 call sites stop spreading the page's copy of the zone. The zone view strips six
more server-written fields for a panel still cached in a browser, and when an edit posts the
bucket or the maximum alone it completes the pair from the stored zone, so the store's clamp
works as before. That completion happens at the view, never in the store funnel. Design:
`docs/superpowers/specs/2026-09-29-zone-save-sends-what-changed-design.md` on
`archive/design-history`.

**Tech Stack:** Python 3.12, Home Assistant custom component, pytest +
pytest-homeassistant-custom-component, `black`, `ruff`; TypeScript + Lit, vitest,
eslint/prettier, rollup.

---

## This plan was run once before it was handed over

On 2026-09-29 every code change and every test below was applied to a throwaway worktree on
`1876aa03`, measured, and removed. The numbers it produced, so a deviation shows at once:

| check | on `1876aa03` | with the change |
|---|---|---|
| `tests/test_zone_view_save.py` | pin + B1–B3 FAILED, B4–B7 passed | 8 passed, 0 errors |
| `view-zone-settings-save.test.ts` | 8 failed | 8 passed |
| vitest, all files | 23 files, 629 passed | 24 files, 637 passed |
| `npx tsc --noEmit -p .` | 0 errors | 0 errors |
| `npm run build` | exit 0, 0 TS diagnostics | exit 0, 0 TS diagnostics; **only** `dist/irrigation-plus.js` changes content |
| full backend suite, `TZ=UTC` | 7 failed / 3455 passed / 9 skipped / 367 errors | 7 / 3462 / 9 / 367 with 7 new tests; FAILED/ERROR names identical, 375 = 375 |
| mutation matrix | — | 15 killed / 15, every source restored byte-for-byte |

The full-suite run started before B7 existed. With it, expect **3463** passed.

Evidence kept outside the repo: `D:\Entwicklung\HASI\issue5-work\measure\probe-full-tzutc.txt`,
`…\issue5-work\mutations.json`, `…\issue5-work\probe-tracked.diff`.

---

## Ground rules for every task

**Worktree:** `D:\Entwicklung\HASI\issue5-work\wt`, branch `fix/zone-save-sends-what-changed`
from `upstream/master` (Task 0 creates both). There is no `.venv` in it; the interpreter is
named absolutely.

**Commands, verbatim.** Backend tests, from the worktree root:

```bash
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock -q --no-header
```

Panel, from `custom_components/irrigation_plus/frontend`:

```bash
npx vitest run <file>        # the panel tests; CI does NOT run these
npx tsc --noEmit -p .        # type check; 0 errors on the base
npm run lint                 # eslint + prettier
npm run build                # lint + rollup; what CI runs
```

Lint for CI, from the worktree root (only these two count, only on this path):

```bash
uvx black custom_components/irrigation_plus/ ; uvx ruff check custom_components/irrigation_plus/
```

**Always under `TZ=UTC`.** The `hass` fixture puts HA on US/Pacific, this machine runs Berlin,
CI runs UTC. A suite run without it is not comparable to the baseline.

**No tracker references in anything that goes upstream.** Code, comments, docstrings, test
names and commit messages carry no `Eifel-Joe#…`, no `#5`, no `N1`, no `PR D`, no `spec` or
`Task N`. This plan and the design doc may; nothing under `custom_components/` or `tests/`
may. Task 5 greps for it, but that is the second line of defence.

**Every task ends on a commit.** Multi-line messages via heredoc (`git commit -F - <<'EOF'`),
never PowerShell. Last line: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

**Windows traps that have cost time before:**
- `git status` shows untouched `dist/*.js` as `M` after a build (`core.autocrlf=true`
  artefact). `git diff --quiet -- <file>` decides; exit 0 means no content change.
- `dist/` is gitignored as a directory while its four bundles are tracked:
  `git add` without `-f` fails and swallows a chained commit. Always `git add -f`, then count
  `git diff --cached --name-only`.
- `sed -i` turns CRLF files into LF here. Use the Edit tool or the Node script in Task 4.
- `grep -c` with no match exits 1 and breaks an `&&` chain. Chain checks with `;`.
- No `nohup … &` for suite runs; use the tool's background mode, and before any verdict
  check that the run collected tests (its summary line exists and is not `0 passed`).

---

## File structure

| File | Responsibility | Change |
|---|---|---|
| `custom_components/irrigation_plus/websockets.py` | the panel's HTTP endpoints | zone view: six more stripped fields, pair completion, rewritten comment block |
| `custom_components/irrigation_plus/store.py` | the zone store and its clamp | comment only: where the pair is completed and why not here |
| `custom_components/irrigation_plus/__init__.py` | coordinator, `_book_asserted_bucket` | comment only: the whole-zone post is no longer a given |
| `custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings.ts` | the zone settings page | `handleEditZone` takes the change; per-zone collection; `_selectValue`; 35 call sites |
| `custom_components/irrigation_plus/frontend/dist/irrigation-plus.js` | the built panel | rebuilt (the three card bundles do not change) |
| `tests/test_zone_view_save.py` | **new**: what the view forwards and what lands; the call-site pin | Tasks 1, 2, 4 |
| `custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings-save.test.ts` | **new**: what `handleEditZone` posts | Task 3 |
| `tests/test_manual_bucket_assertion.py`, `tests/test_distributor_integration.py` | existing | one docstring each, Task 4 |

No file is split. The change is small in every file it touches, and each change sits where
the state it guards already lives.

## Sister paths — checked while planning, nothing to fix

The global rule asks for structurally similar save paths. Every panel page that posts to the
backend was read on `1876aa03`:

| page | what it posts | server-written fields at risk |
|---|---|---|
| zone settings | the page's copy of the zone | **this defect** |
| distributor settings | `_configPayload(d)`, an explicit list of config fields (`view-distributor-settings.ts:229-252`) | none: `current_outlet`, `position_state` are excluded |
| general settings | `pick(this.config, [8 settings])` plus changes (`view-general.ts:202-211`, `:1528-1539`) | none: `rain_delay_until` is never posted |
| sensor groups | `{ id, name, mappings }` (`view-mappings.ts:359`) | none |
| schedules | the whole schedule (`view-schedules.ts:117`) | none: the server writes nothing into a schedule; the fired marker lives in `CONF_FIRED_OCCURRENCES` |

The zone page is the only one that posts a copy carrying fields the server writes. If
`upstream/master` has moved when this plan is executed, re-read the distributor and general
rows before relying on them.

---

## Task 0: Worktree and base

- [ ] **Step 1: Confirm the base**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && git fetch upstream && git rev-parse --short=8 upstream/master
```

Expected: `1876aa03`. If it is anything else, **stop**: every count in this plan, the
baseline file and the line numbers below were measured on `1876aa03`. Measure a new baseline
on the new base first (memory `rebaseline-when-the-base-moves`) and re-read the four anchors
this plan edits (the zone view's strip list, the store's clamp, the comment in
`_book_asserted_bucket`, `handleEditZone`).

- [ ] **Step 2: Create the worktree, the socket plugin, the panel's dependencies**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && git worktree add -b fix/zone-save-sends-what-changed /d/Entwicklung/HASI/issue5-work/wt upstream/master ; cp /d/Entwicklung/HASI/HAsmartirrigation/_local_socket_unblock.py /d/Entwicklung/HASI/issue5-work/wt/ ; cd /d/Entwicklung/HASI/issue5-work/wt/custom_components/irrigation_plus/frontend && npm ci --no-audit --no-fund
```

- [ ] **Step 3: Confirm pytest imports this worktree's code**

A memory warns that a worktree can end up testing another copy of the integration. Measured
on 2026-09-29 for worktrees outside the repo: it does not. Check it anyway; it takes a second.

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && PYTHONPATH=/d/Entwicklung/HASI/issue5-work TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_manual_bucket_assertion.py --co -q -p probe_import_origin -p _local_socket_unblock | grep IMPORT-ORIGIN
```

Expected: both lines point into `D:\Entwicklung\HASI\issue5-work\wt\custom_components`. The
plugin is `D:\Entwicklung\HASI\issue5-work\probe_import_origin.py`, kept from the probe run.

No commit: nothing has changed.

---

## Task 1: The strip list lets nothing the server writes come back

A panel still cached in a browser keeps posting whole zones. Six fields the server writes
still pass the strip list; the days-between counter among them is reset by every credit.

**Files:**
- Create: `tests/test_zone_view_save.py`
- Modify: `custom_components/irrigation_plus/websockets.py:347-382`

- [ ] **Step 1: Write the test file with the first test and a pin**

Create `tests/test_zone_view_save.py`:

```python
"""A zone save through the panel's view: what is forwarded, and what lands.

The panel used to post the whole zone it held on every edit. That copy is
re-read only on ``_update_frontend``, which a run's credit does not send, so a
page left open across a run posted its pre-run bucket back, and
``_book_asserted_bucket`` took the stale level for one set by hand. The panel
now sends only what an edit set. Two things stay with the view:

* the strip list, for a panel still cached in a browser that keeps posting
  whole zones: nothing the server writes may come back through it;
* the bucket/maximum clamp, which the store applies only when one payload
  carries both. A panel edit carries one, so the view completes the pair from
  the stored zone -- at this boundary, not in the store, which every other
  bucket writer passes through too.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from freezegun import freeze_time
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const
from custom_components.irrigation_plus.store import SmartIrrigationStorage
from custom_components.irrigation_plus.websockets import SmartIrrigationZoneView

T0 = datetime.datetime(2026, 5, 22, 6, 0, 0)
SAVED_AT = T0 + datetime.timedelta(hours=3)
LEDGER = [{"ts": T0.isoformat(), "mm": 1.0}]


@pytest.fixture
async def coordinator(hass):
    """A real coordinator over a real in-memory store, reachable from the view."""
    hass.data[const.DOMAIN] = {
        const.CONF_USE_WEATHER_SERVICE: False,
        const.CONF_WEATHER_SERVICE: None,
    }
    hass.config.units = METRIC_SYSTEM
    hass.config.language = "en"
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    entry = Mock()
    entry.unique_id = "t"
    entry.data = {}
    entry.options = {}
    c = SmartIrrigationCoordinator(hass, None, entry, store)
    c.store = store
    hass.data[const.DOMAIN]["coordinator"] = c
    yield c, store
    # The constructor arms the midnight counter; left armed, the test ends with
    # a lingering timer.
    c._track_midnight_time_unsub()


async def _zone(store, *, bucket, maximum_bucket):
    zone = await store.async_create_zone(
        {
            const.ZONE_NAME: "Front",
            const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
            const.ZONE_BUCKET: bucket,
            const.ZONE_MAXIMUM_BUCKET: maximum_bucket,
            const.ZONE_THROUGHPUT: 10.0,
            const.ZONE_SIZE: 10.0,
            const.ZONE_LAST_CONSUMED: T0,
            const.ZONE_PENDING_BUCKET_EVENTS: list(LEDGER),
        }
    )
    return zone[const.ZONE_ID]


async def _post(hass, data):
    """POST a zone save through the real view, the way the panel does."""
    request = MagicMock()
    request.app = {"hass": hass}
    request.json = AsyncMock(return_value=data)
    view = SmartIrrigationZoneView()
    view.json = MagicMock(return_value="OK")
    with freeze_time(SAVED_AT):
        await view.post(request)


async def test_a_whole_zone_post_does_not_write_back_what_the_server_writes(
    coordinator,
):
    """A panel still cached in a browser posts the whole zone it holds.

    These six are written by the server alone -- the days-between counter by
    every credit, in the same write, the rest by the calculation -- and none has
    an input on the form. A pre-run copy of the counter would undo the wait the
    run had just restarted.
    """
    c, store = coordinator
    zid = await _zone(store, bucket=0.0, maximum_bucket=30.0)
    fresh = {
        const.ZONE_DAYS_SINCE_IRRIGATION: 0,
        const.ZONE_IRRIGATION_TARGET_BUCKET: 0.0,
        const.ZONE_DELTA: -1.5,
        const.ZONE_EXPLANATION: "fresh",
        const.ZONE_CURRENT_DRAINAGE: 0.4,
        const.ZONE_NUMBER_OF_DATA_POINTS: 24,
    }
    await store.async_update_zone(zid, dict(fresh))
    stale = {
        const.ZONE_DAYS_SINCE_IRRIGATION: 3,
        const.ZONE_IRRIGATION_TARGET_BUCKET: -2.0,
        const.ZONE_DELTA: -4.0,
        const.ZONE_EXPLANATION: "stale",
        const.ZONE_CURRENT_DRAINAGE: 1.2,
        const.ZONE_NUMBER_OF_DATA_POINTS: 7,
    }

    await _post(c.hass, {const.ZONE_ID: zid, const.ZONE_NAME: "renamed", **stale})

    after = store.get_zone(zid)
    assert after[const.ZONE_NAME] == "renamed"
    assert {key: after[key] for key in fresh} == fresh


async def test_an_edit_after_a_credit_keeps_the_credit(coordinator):
    """The backend half of the defect: a run credits, then the panel saves.

    Posting only the edited field, nothing of the credit may move -- not the
    level, the ledger entry it booked, the watermark or the days-between reset.
    """
    c, store = coordinator
    zid = await _zone(store, bucket=-6.2, maximum_bucket=30.0)
    with freeze_time(T0 + datetime.timedelta(hours=1)):
        await c.async_write_watered_bucket(zid, 0.0)
    credited = store.get_zone(zid)

    await _post(c.hass, {const.ZONE_ID: zid, const.ZONE_NAME: "renamed"})

    after = store.get_zone(zid)
    assert after[const.ZONE_NAME] == "renamed"
    for key in (
        const.ZONE_BUCKET,
        const.ZONE_PENDING_BUCKET_EVENTS,
        const.ZONE_LAST_CONSUMED,
        const.ZONE_DAYS_SINCE_IRRIGATION,
    ):
        assert after[key] == credited[key], key
```

- [ ] **Step 2: Run it; see the first test fail for the right reason**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_zone_view_save.py -p _local_socket_unblock -q --no-header 2>&1 | grep -E "^E |passed|failed"
```

Expected: `1 failed, 1 passed`, and the `E` lines list all six fields as differing, e.g.
`{'days_since_irrigation': 3} != {'days_since_irrigation': 0}`. Any **error** at teardown is
a regression in the fixture (the midnight tracker must be cancelled), not the known artefact.

The second test is a **pin**: the backend already merges a partial post, so it passes on the
base. It is here because it is the backend half of the defect, stated as a test.

- [ ] **Step 3: Rewrite the comment and extend the strip list**

In `custom_components/irrigation_plus/websockets.py`, replace the comment block that starts
`# The panel's zone settings form saves a zone by POSTing the WHOLE zone object.` and ends
`# See test_zone_view_ignores_server_owned_fields.` (lines 347-365) with:

```python
        # The panel's zone settings form posts only the fields an edit set. A panel
        # still cached in a browser from before that posts the WHOLE zone object it
        # holds, and so may any other client of this endpoint.
        # Wurzel: that object is the page's copy, re-read only on _update_frontend,
        #   which a run's credit does not send. After a run it still carries the
        #   pre-run values, and posting it wrote them back: the run's usage total and
        #   history entry, the flow engine's learning, the consumption watermark
        #   (rewound, the next calculation folds an already-consumed window in
        #   again), the ledger, the days-between counter and the calculation's
        #   outputs.
        # Fix-Logik: drop every field the server writes and the form has no input
        #   for, so the store's own writers stay their only writers. The schema
        #   above still accepts them on purpose: rejecting a field an old panel
        #   sends would fail its whole save with a 400, whatever was being edited.
        # NOT-TO-DO: do not add a field the form edits (bucket, duration,
        #   multiplier, flow_counter_type, ...). In a whole-zone post a stale copy
        #   of one cannot be told from an edit of it; only the panel posting what
        #   it set keeps those safe.
        # See test_zone_view_ignores_server_owned_fields and test_zone_view_save.py.
```

Then, inside the `for _server_owned in (` tuple, directly after
`const.ZONE_PENDING_BUCKET_EVENTS,`, add:

```python
            # Reset to 0 in the same write as every credit: a pre-run copy
            # undoes the days-between wait the run has just restarted.
            const.ZONE_DAYS_SINCE_IRRIGATION,
            # The calculation's outputs.
            const.ZONE_IRRIGATION_TARGET_BUCKET,
            const.ZONE_DELTA,
            const.ZONE_EXPLANATION,
            const.ZONE_CURRENT_DRAINAGE,
            const.ZONE_NUMBER_OF_DATA_POINTS,
```

Leave the schema entries for `explanation`, `delta`, `number_of_data_points` and
`current_drainage` where they are: accepted and ignored is the point.

- [ ] **Step 4: Run the new file and the existing strip-list test**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_zone_view_save.py tests/test_distributor_integration.py -p _local_socket_unblock -q --no-header 2>&1 | tail -1
```

Expected: all passed, no errors.

- [ ] **Step 5: Lint**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && uvx black custom_components/irrigation_plus/ tests/test_zone_view_save.py ; uvx ruff check custom_components/irrigation_plus/
```

Expected: nothing reformatted, `All checks passed!`.

- [ ] **Step 6: Commit**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && git add custom_components/irrigation_plus/websockets.py tests/test_zone_view_save.py && git commit -F - <<'EOF'
fix(zones): a whole-zone save leaves what the server writes alone

A panel still cached in a browser posts the whole zone it holds. Six of
its fields are written by the server only, and the strip list let them
through: the days-between counter, which every credit resets in the same
write, and five outputs of the calculation. A pre-run copy of the counter
undid the wait the run had just restarted.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

## Task 2: A lone bucket or maximum is clamped at the view

The store clamps the bucket to the maximum only when one payload carries both. After Task 4
the panel posts one of them alone.

**Files:**
- Modify: `tests/test_zone_view_save.py` (append)
- Modify: `custom_components/irrigation_plus/websockets.py` (after the strip list)
- Modify: `custom_components/irrigation_plus/store.py:1680-1682` (comment)
- Modify: `custom_components/irrigation_plus/__init__.py:2003-2007` (comment)

- [ ] **Step 1: Append the tests**

Append to `tests/test_zone_view_save.py`:

```python
async def test_a_lone_bucket_is_clamped_to_the_stored_maximum(coordinator):
    """The form's bucket input posts the bucket alone; the cap still holds."""
    c, store = coordinator
    zid = await _zone(store, bucket=0.0, maximum_bucket=30.0)

    await _post(c.hass, {const.ZONE_ID: zid, const.ZONE_BUCKET: 50.0})

    assert store.get_zone(zid)[const.ZONE_BUCKET] == 30.0


async def test_a_lowered_maximum_clamps_the_stored_level_as_a_statement(
    coordinator,
):
    """Lowering the cap below the level clamps the level, as a whole-zone save
    did: the level moved because someone said where it can be, so the weather
    window restarts there (``_book_asserted_bucket``).
    """
    c, store = coordinator
    zid = await _zone(store, bucket=20.0, maximum_bucket=30.0)

    await _post(c.hass, {const.ZONE_ID: zid, const.ZONE_MAXIMUM_BUCKET: 10.0})

    after = store.get_zone(zid)
    assert after[const.ZONE_BUCKET] == 10.0
    assert after[const.ZONE_MAXIMUM_BUCKET] == 10.0
    assert after[const.ZONE_LAST_CONSUMED] == SAVED_AT
    assert after[const.ZONE_PENDING_BUCKET_EVENTS] == []


async def test_a_raised_maximum_leaves_the_level_and_the_window_alone(coordinator):
    """Completing the pair must not turn every maximum edit into a statement."""
    c, store = coordinator
    zid = await _zone(store, bucket=20.0, maximum_bucket=30.0)

    await _post(c.hass, {const.ZONE_ID: zid, const.ZONE_MAXIMUM_BUCKET: 40.0})

    after = store.get_zone(zid)
    assert after[const.ZONE_BUCKET] == 20.0
    assert after[const.ZONE_MAXIMUM_BUCKET] == 40.0
    assert after[const.ZONE_LAST_CONSUMED] == T0
    assert after[const.ZONE_PENDING_BUCKET_EVENTS] == LEDGER


async def test_a_new_zone_posted_with_a_bucket_and_no_maximum_is_created(
    coordinator,
):
    """Creating a zone has no stored zone to complete the pair from.

    The setup wizard and the panel's "add zone" both post a bucket without a
    maximum and without an id. Looking the missing value up would ask the store
    for zone ``None``, which it cannot answer.
    """
    c, store = coordinator

    await _post(
        c.hass,
        {
            const.ZONE_NAME: "New",
            const.ZONE_SIZE: 10.0,
            const.ZONE_THROUGHPUT: 5.0,
            const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
            const.ZONE_BUCKET: 0,
        },
    )

    assert [z[const.ZONE_NAME] for z in await store.async_get_zones()] == ["New"]


async def test_a_bucket_set_through_the_store_funnel_is_not_clamped(coordinator):
    """The pair is completed at the panel's boundary only.

    ``set_all_buckets`` posts a level without a maximum and has never been
    clamped. Completing the pair inside the store would change that for it and
    for every other writer the store serves.
    """
    c, store = coordinator
    zid = await _zone(store, bucket=0.0, maximum_bucket=30.0)

    with freeze_time(SAVED_AT):
        await c._async_set_all_buckets(50.0)

    assert store.get_zone(zid)[const.ZONE_BUCKET] == 50.0
```

- [ ] **Step 2: Run; see two fail for the right reason**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_zone_view_save.py -p _local_socket_unblock -q --no-header 2>&1 | grep -E "^E +assert|passed|failed"
```

Expected: `2 failed, 5 passed`, with `assert 50.0 == 30.0` and `assert 20.0 == 10.0`. The
raised-maximum, new-zone and funnel tests are **pins**: they pass on the base and guard
against a completion that turns every maximum edit into a statement, one that breaks zone
creation, and one moved into the store.

- [ ] **Step 3: Complete the pair at the view**

In `custom_components/irrigation_plus/websockets.py`, directly after the strip loop's
`data.pop(_server_owned, None)` and before `try:`, add:

```python
        # Wurzel: the store clamps the bucket to maximum_bucket only when one
        #   payload carries both. A whole-zone save always did; a panel edit of
        #   either now posts that one alone, which would slip past the cap.
        # Fix-Logik: complete the pair from the stored zone, so the store sees what
        #   a whole-zone save gave it. A level above the cap is clamped; a cap
        #   lowered below the level clamps the level, and _book_asserted_bucket
        #   books that as a statement, as it always did; a cap that leaves the
        #   level alone moves nothing.
        # NOT-TO-DO: do not read the missing value inside the store instead. Every
        #   bucket writer passes through it (credits, the calculation, a unit flip,
        #   set_all_buckets) and none of them is clamped there today.
        # See test_zone_view_save.py.
        if zone is not None and (const.ZONE_BUCKET in data) != (
            const.ZONE_MAXIMUM_BUCKET in data
        ):
            stored = coordinator.store.get_zone(zone)
            if stored is not None:
                missing = (
                    const.ZONE_MAXIMUM_BUCKET
                    if const.ZONE_BUCKET in data
                    else const.ZONE_BUCKET
                )
                data[missing] = stored.get(missing)
```

The `zone is not None` guard is load-bearing: `store.get_zone(None)` calls `int(None)`.

- [ ] **Step 4: Point the store's clamp comment at the view**

In `custom_components/irrigation_plus/store.py`, replace

```python
            # apply maximum bucket value
            # review finding J: guard changes[ZONE_BUCKET] presence like the
```

with

```python
            # apply maximum bucket value -- only when this payload carries both.
            # A panel edit posts one of them alone; the zone view completes the
            # pair from the stored zone before it gets here. Every other writer
            # (credits, the calculation, set_all_buckets) passes the bucket alone
            # and is deliberately not clamped here: see test_zone_view_save.py.
            # review finding J: guard changes[ZONE_BUCKET] presence like the
```

- [ ] **Step 5: Correct the comment in `_book_asserted_bucket`**

In `custom_components/irrigation_plus/__init__.py`, replace

```python
            # same payload carries one, which the panel's whole-zone save always
            # does. An unchanged bucket -- every panel save that edited some
            # other setting -- must not move anything.
```

with

```python
            # same payload carries one, which a whole-zone save always does and
            # the zone view arranges for a panel edit of either. An unchanged
            # bucket -- a whole-zone save from a panel still cached in a browser
            # that edited some other setting -- must not move anything.
```

- [ ] **Step 6: Run the three files**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_zone_view_save.py tests/test_manual_bucket_assertion.py tests/test_distributor_integration.py -p _local_socket_unblock -q --no-header 2>&1 | tail -1
```

Expected: `32 passed, 5 errors`. The 5 errors are `test_manual_bucket_assertion.py`'s
teardowns (`Lingering timer`), the same five the baseline carries. Anything else is new.

- [ ] **Step 7: Lint and commit**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && uvx black custom_components/irrigation_plus/ tests/test_zone_view_save.py ; uvx ruff check custom_components/irrigation_plus/
```

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && git add custom_components/irrigation_plus/websockets.py custom_components/irrigation_plus/store.py custom_components/irrigation_plus/__init__.py tests/test_zone_view_save.py && git commit -F - <<'EOF'
fix(zones): clamp a bucket or a maximum saved on its own

The store clamps the bucket to maximum_bucket only when one payload
carries both, which a whole-zone save always did. An edit that posts one
of them alone would slip past the cap. The zone view now completes the
pair from the stored zone, so a lone bucket is clamped and a lowered
maximum clamps the level, as before. The store itself stays as it was:
every other bucket writer passes through it, and none of them is clamped
there today.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

## Task 3: The panel posts what an edit set

**Files:**
- Create: `custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings-save.test.ts`
- Modify: `custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings.ts`

- [ ] **Step 1: Write the panel tests**

Create `custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings-save.test.ts`:

```typescript
import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

beforeAll(() => {
  (globalThis as any).HTMLElement = class {};
  (globalThis as any).customElements = {
    define() {},
    get() {
      return undefined;
    },
    whenDefined: () => Promise.resolve(),
  };
  (globalThis as any).window = globalThis;
  // _scheduleUpdate() defers a re-render to the next frame; nothing renders here.
  (globalThis as any).requestAnimationFrame = () => 0;
});

type ViewModule = typeof import("./view-zone-settings");
let View: ViewModule["SmartIrrigationViewZoneSettings"];
beforeAll(async () => {
  ({ SmartIrrigationViewZoneSettings: View } =
    await import("./view-zone-settings"));
});

// A zone as the page holds it: loaded before a run, so its bucket is the pre-run
// level. The server has credited the run since, and the page never heard of it:
// it re-reads only on _update_frontend, which a credit does not send.
function staleZone(id: number, extra: Record<string, unknown> = {}) {
  return {
    id,
    name: `Zone ${id}`,
    size: 10,
    throughput: 5,
    state: "automatic",
    duration: 0,
    bucket: -6.2,
    delta: 0,
    explanation: "",
    multiplier: 1,
    lead_time: 0,
    module: 1,
    mapping: 1,
    water_used_total: 12.5,
    run_log: [],
    ...extra,
  };
}

function make(zones: unknown[]) {
  const callApi = vi.fn().mockResolvedValue(true);
  const el: any = new View();
  el.hass = { language: "en", states: {}, callApi };
  el.zones = zones;
  return { el, callApi };
}

// What went over the wire: each POST body as JSON carries it, so an
// `undefined` value is gone here exactly as it is on the way to the server.
function bodies(callApi: ReturnType<typeof vi.fn>) {
  return callApi.mock.calls.map(([method, path, body]) => {
    expect([method, path]).toEqual(["POST", "irrigation_plus/zones"]);
    return JSON.parse(JSON.stringify(body));
  });
}

// That no call site hands handleEditZone the page's copy of the zone is pinned
// in tests/test_zone_view_save.py: CI runs pytest, not these tests.

describe("a zone edit posts what it set", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("sends the zone id and the edited field, nothing from the page's copy", () => {
    const { el, callApi } = make([staleZone(1)]);
    el.handleEditZone(0, { name: "Beet" });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([{ id: 1, name: "Beet" }]);
  });

  it("shows the edit at once and keeps the rest of the page's copy", () => {
    const { el } = make([staleZone(1)]);
    el.handleEditZone(0, { name: "Beet" });
    expect(el.zones[0]).toEqual({ ...staleZone(1), name: "Beet" });
  });

  it("saves every zone edited inside one debounce window", () => {
    const { el, callApi } = make([staleZone(1), staleZone(2)]);
    el.handleEditZone(0, { name: "Beet" });
    el.handleEditZone(1, { name: "Hecke" });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([
      { id: 1, name: "Beet" },
      { id: 2, name: "Hecke" },
    ]);
  });

  it("merges two edits to one zone into one post", () => {
    const { el, callApi } = make([staleZone(1)]);
    el.handleEditZone(0, { name: "Beet" });
    el.handleEditZone(0, { size: 12 });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([{ id: 1, name: "Beet", size: 12 }]);
  });

  it("does not post an edit twice once it has been sent", () => {
    const { el, callApi } = make([staleZone(1)]);
    el.handleEditZone(0, { name: "Beet" });
    vi.advanceTimersByTime(500);
    el.handleEditZone(0, { size: 12 });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([
      { id: 1, name: "Beet" },
      { id: 1, size: 12 },
    ]);
  });

  it("sends a cleared field as null, so the server stores the clear", () => {
    const { el, callApi } = make([staleZone(1)]);
    el.handleEditZone(0, { module: undefined });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([{ id: 1, module: null }]);
  });

  it("sends every field the edit set, even one the page's copy already shows", () => {
    // The state select resets the duration with the state. The page's copy may
    // show 0 while the server holds a calculated duration, so a difference
    // against the copy would drop the reset.
    const { el, callApi } = make([staleZone(1, { duration: 0 })]);
    el.handleEditZone(0, { state: "manual", duration: 0 });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([{ id: 1, state: "manual", duration: 0 }]);
  });
});

describe("select value for an optional id", () => {
  it("shows the empty option for a cleared id, and the id otherwise", () => {
    // The server returns a cleared module or mapping as null; String(null)
    // would select nothing instead of the empty option.
    const el: any = new View();
    expect(el._selectValue(null)).toBe("");
    expect(el._selectValue(undefined)).toBe("");
    expect(el._selectValue(3)).toBe("3");
    expect(el._selectValue(0)).toBe("0");
  });
});
```

No `node:` imports in this file: the project has no `@types/node`, and rollup's TypeScript
plugin type-checks test files too, so each import would print one warning per bundle.

- [ ] **Step 2: Run them; see all eight fail**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt/custom_components/irrigation_plus/frontend && npx vitest run src/views/zones/view-zone-settings-save.test.ts 2>&1 | grep -E "×|✓|Tests "
```

Expected: `8 failed`. The first test reports `expected [ { name: 'Beet' } ] to deeply equal
[ { id: 1, name: 'Beet' } ]`, the two-zone test gets one post instead of two, the last one
`_selectValue is not a function`.

- [ ] **Step 3: The type for an edit on the wire**

In `view-zone-settings.ts`, after `import "../../components/ip-zone-form";`, add:

```typescript

// A zone edit as it goes over the wire: a field the form cleared is null.
type ZoneEdit = {
  [K in keyof SmartIrrigationZone]?: SmartIrrigationZone[K] | null;
};
```

- [ ] **Step 4: The per-zone collection**

Directly after `private globalDebounceTimer: number | null = null;`, add:

```typescript
  // Edits not yet posted, per zone id (see handleEditZone).
  private _pendingEdits = new Map<number, ZoneEdit>();
```

- [ ] **Step 5: Replace `handleEditZone`**

Replace the whole method, from `private handleEditZone(` down to its closing brace (the one
after the final `this._scheduleUpdate();`), with:

```typescript
  // Wurzel: every call site passed `{ ...zone, [FIELD]: v }` and the whole
  //   object was posted. The page's copy is re-read only on _update_frontend,
  //   which a run's credit does not send, so after a run it still held the
  //   pre-run bucket. The next edit of any field wrote that back, and the
  //   backend took it for a level set by hand (_book_asserted_bucket).
  // Fix-Logik: a call site passes only what it sets. Edits are collected per
  //   zone and posted as `{ id, ...changes }`, every zone at once when the
  //   debounce runs out. A cleared field is `undefined`, which JSON drops (the
  //   server then kept the old value), so it is sent as null.
  // NOT-TO-DO: do not work the change out as a difference against the page's
  //   copy. That copy is what goes stale: the state select sets
  //   `{ state, duration: 0 }`, and against a copy already showing 0 the reset
  //   would never be sent.
  // See view-zone-settings-save.test.ts.
  private handleEditZone(
    index: number,
    changes: Partial<SmartIrrigationZone>,
  ): void {
    if (!this.hass) return;
    const zone = this.zones[index];
    if (!zone) return;

    // Replace the whole array so Lit's reactive system detects the change.
    this.zones = this.zones.map((z, i) =>
      i === index ? { ...z, ...changes } : z,
    );
    this._scheduleUpdate();

    // A zone without an id is one handleAddZone is still creating. It cannot
    // be expanded (_isExpanded), so no edit is expected to reach here.
    if (zone.id === undefined) return;
    const pending: ZoneEdit = { ...this._pendingEdits.get(zone.id) };
    for (const [key, value] of Object.entries(changes)) {
      (pending as Record<string, unknown>)[key] = value ?? null;
    }
    this._pendingEdits.set(zone.id, pending);

    if (this.globalDebounceTimer) clearTimeout(this.globalDebounceTimer);
    this.globalDebounceTimer = window.setTimeout(() => {
      this.globalDebounceTimer = null;
      this._savePendingEdits();
    }, 500);
  }

  private _savePendingEdits(): void {
    // Taken out before posting: an edit made while these are in flight
    // belongs to the next round.
    const edits = [...this._pendingEdits];
    this._pendingEdits.clear();
    if (!edits.length) return;
    this.isSaving = true;
    this._saveStatus = "saving";
    Promise.all(
      edits.map(([id, changes]) =>
        // null is how a cleared field travels; saveZone's type has no room
        // for it.
        this.saveToHA({ id, ...changes } as Partial<SmartIrrigationZone>),
      ),
    )
      .then(() => this._markSaved())
      .catch((error) => {
        console.error("Failed to save zone:", error);
        this._saveStatus = "idle";
        showErrorToast(this, this.hass, "common.errors.save_failed", error);
      })
      .finally(() => {
        this.isSaving = false;
        this._scheduleUpdate();
      });
  }

  // The select value for an optional id. A module or mapping the form cleared
  // comes back from the server as null, and String(null) matches no option.
  private _selectValue(id: number | string | null | undefined): string {
    return id == null ? "" : String(id);
  }
```

- [ ] **Step 6: Let `saveToHA` take a partial zone**

Replace

```typescript
  private async saveToHA(zone: SmartIrrigationZone): Promise<void> {
```

with

```typescript
  private async saveToHA(zone: Partial<SmartIrrigationZone>): Promise<void> {
```

- [ ] **Step 7: Bind the module and mapping selects through `_selectValue`**

Replace

```typescript
                    .value="${live(
                      zone.module !== undefined ? String(zone.module) : "",
                    )}"
```

with

```typescript
                    .value="${live(this._selectValue(zone.module))}"
```

and

```typescript
                    .value="${live(
                      zone.mapping !== undefined ? String(zone.mapping) : "",
                    )}"
```

with

```typescript
                    .value="${live(this._selectValue(zone.mapping))}"
```

- [ ] **Step 8: Run the panel checks**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt/custom_components/irrigation_plus/frontend && npx vitest run src/views/zones/view-zone-settings-save.test.ts 2>&1 | grep -E "Tests " ; npx vitest run 2>&1 | grep -E "Test Files|Tests " ; npx tsc --noEmit -p . ; echo "tsc exit=$?" ; npm run lint ; echo "lint exit=$?"
```

Expected: `8 passed (8)`; `24 passed (24)` files and `637 passed (637)` tests; `tsc exit=0`
with no output; `lint exit=0`. The 35 call sites still spread `...zone` at this point; a full
zone is a valid `Partial`, so it compiles. Task 4 fixes them.

- [ ] **Step 9: Commit**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && git add custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings.ts custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings-save.test.ts && git commit -F - <<'EOF'
fix(panel): a zone edit posts what it set, per zone, with the zone's id

handleEditZone now takes the change an input sets rather than the page's
copy of the zone. Edits are collected per zone and posted as the change
plus the id, every zone at once when the debounce runs out; the save
timer was shared by all zones and kept only the last one, so editing two
zones within half a second lost the first. A cleared field is sent as
null: undefined vanished from the JSON and the server kept the old value.
A module or mapping cleared that way comes back as null, so the two
selects map null to the empty option.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

## Task 4: No call site hands over the page's copy

**Files:**
- Modify: `tests/test_zone_view_save.py` (imports, a constant, the pin)
- Modify: `custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings.ts` (35 call sites)
- Modify: `tests/test_manual_bucket_assertion.py`, `tests/test_distributor_integration.py` (one docstring each)
- Modify: `custom_components/irrigation_plus/frontend/dist/irrigation-plus.js` (rebuilt)

- [ ] **Step 1: Add the pin to the backend suite**

CI runs pytest and no panel tests, so the pin on the panel's source lives here. In
`tests/test_zone_view_save.py`, change the import block to:

```python
import datetime
import pathlib
import re
from unittest.mock import AsyncMock, MagicMock, Mock
```

After `LEDGER = [{"ts": T0.isoformat(), "mm": 1.0}]`, add:

```python
PANEL = (
    pathlib.Path(__file__).parent.parent
    / "custom_components"
    / "irrigation_plus"
    / "frontend"
    / "src"
    / "views"
    / "zones"
    / "view-zone-settings.ts"
)


def test_the_panel_names_what_each_zone_edit_sets():
    """A tripwire on the panel's source, kept here because CI runs pytest only.

    Every settings input calls ``handleEditZone``. Handed ``{ ...zone, [FIELD]: v }``
    it posted the page's copy of the zone -- a pre-run bucket included, which the
    backend then booked as a level set by hand. Each call site now passes only
    what it sets. A tripwire, not a proof: a call site that copies the zone some
    other way walks straight past it.
    """
    src = PANEL.read_text(encoding="utf-8")
    calls = re.findall(r"this\.handleEditZone\(\s*\w+\s*,", src)
    # No length limit between the brace and the spread: in the deeper template
    # blocks the indentation alone is longer than a fixed window would allow.
    spreading = [
        src.count("\n", 0, m.start()) + 1
        for m in re.finditer(
            r"this\.handleEditZone\(\s*\w+\s*,\s*\{\s*\.\.\.zone\b", src
        )
    ]
    assert calls, "no handleEditZone call found: this pin no longer reads the panel"
    assert spreading == [], f"page copy of the zone spread at lines {spreading}"
```

The regex is deliberately unbounded between `{` and `...zone`. A first version captured a
40-character window after the comma and found only 23 of the 35 spreads: in the deeply
nested template blocks the indentation alone is longer than 40 characters, so a fix that
missed exactly those 12 would have passed it.

- [ ] **Step 2: Run the pin; see it list all 35**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_zone_view_save.py::test_the_panel_names_what_each_zone_edit_sets -p _local_socket_unblock -q --no-header 2>&1 | grep -E "AssertionError|passed|failed" ; /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -c "import re,pathlib;s=pathlib.Path(r'D:/Entwicklung/HASI/issue5-work/wt/custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings.ts').read_text(encoding='utf-8');print(len(re.findall(r'this\.handleEditZone\(\s*\w+\s*,\s*\{\s*\.\.\.zone\b',s)))"
```

Expected: `1 failed` with `page copy of the zone spread at lines [...]`, and the count `35`.

- [ ] **Step 3: Drop the spread at every call site**

The script is kept at `D:\Entwicklung\HASI\issue5-work\drop-zone-spread.cjs`. Recreate it
from here if it is gone:

```javascript
// Make every handleEditZone call site pass only what it sets.
// Run from custom_components/irrigation_plus/frontend.
const fs = require("fs");
const file = "src/views/zones/view-zone-settings.ts";
const spread = /this\.handleEditZone\(\s*index\s*,\s*\{\s*\.\.\.zone\b/g;
let src = fs.readFileSync(file, "utf8");
const before = (src.match(spread) || []).length;
// The plant-type handler builds its change in `next` and spread both.
src = src.replace(
  /(this\.handleEditZone\(\s*index\s*,\s*)\{\s*\.\.\.zone\s*,\s*\.\.\.next\s*\}/g,
  "$1next",
);
// Every other call site: drop the `...zone,` at the head of its object.
src = src.replace(/(this\.handleEditZone\(\s*index\s*,\s*\{)\s*\.\.\.zone\s*,/g, "$1");
const after = (src.match(spread) || []).length;
fs.writeFileSync(file, src);
console.log(`...zone spreads: before=${before} after=${after}`);
```

```bash
cd /d/Entwicklung/HASI/issue5-work/wt/custom_components/irrigation_plus/frontend && node /d/Entwicklung/HASI/issue5-work/drop-zone-spread.cjs
```

Expected: `...zone spreads: before=35 after=0`. The script keeps the file's CRLF line
endings (the removed span includes the line break before `...zone`, the kept one follows it).
Read the diff once: the plant-type site becomes `this.handleEditZone(index, next);`, the size
site `this.handleEditZone(index, { [ZONE_SIZE]: v });`, every other site loses one line.

- [ ] **Step 4: Run the pin and the panel checks**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_zone_view_save.py -p _local_socket_unblock -q --no-header 2>&1 | tail -1 ; cd custom_components/irrigation_plus/frontend && npx vitest run src/views/zones/view-zone-settings-save.test.ts 2>&1 | grep -E "Tests " ; npx tsc --noEmit -p . ; echo "tsc exit=$?" ; npm run lint ; echo "lint exit=$?"
```

Expected: `8 passed`; `8 passed (8)`; `tsc exit=0`; `lint exit=0` (prettier keeps the
multi-line objects as they are).

- [ ] **Step 5: Correct the two test docstrings that describe the old save**

In `tests/test_manual_bucket_assertion.py`, replace

```python
    """The panel POSTs the WHOLE zone on every settings save, bucket included.
```

with

```python
    """A panel still cached in a browser POSTs the WHOLE zone, bucket included.
```

In `tests/test_distributor_integration.py`, in `test_zone_view_ignores_server_owned_fields`,
replace

```python
    The panel saves a zone by POSTing the WHOLE zone object; a browser snapshot left
    open across a run carries a stale water_used_total + run log that would otherwise
    revert that run's usage total and delete its history entry. The same hazard applies
    to the flow engine's server-owned learning/calibration state (flow_last_end,
```

with

```python
    A panel still cached in a browser saves a zone by POSTing the WHOLE zone object;
    a snapshot left open across a run carries a stale water_used_total + run log
    that would otherwise revert that run's usage total and delete its history
    entry. The same hazard applies to the flow engine's server-owned
    learning/calibration state (flow_last_end,
```

- [ ] **Step 6: Build and stage the one bundle that changes**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt/custom_components/irrigation_plus/frontend && npm run build > /d/Entwicklung/HASI/issue5-work/build.log 2>&1 ; echo "build exit=$? ts-diagnostics=$(grep -c 'TS[0-9]\{4\}' /d/Entwicklung/HASI/issue5-work/build.log)" ; cd /d/Entwicklung/HASI/issue5-work/wt && git update-index --refresh > /dev/null 2>&1 ; for f in irrigation-plus.js irrigation-plus-card.js irrigation-plus-card-legacy.js irrigation-plus-card-impl.js; do git diff --quiet -- custom_components/irrigation_plus/frontend/dist/$f && echo "$f: unchanged" || echo "$f: CHANGED"; done
```

Expected: `build exit=0 ts-diagnostics=0`; `irrigation-plus.js: CHANGED`, the three card
bundles `unchanged` (they do not import this view). If a card bundle does change, commit it
too; do not drop a bundle whose content moved.

- [ ] **Step 7: Commit**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && git add custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings.ts tests/test_zone_view_save.py tests/test_manual_bucket_assertion.py tests/test_distributor_integration.py ; git add -f custom_components/irrigation_plus/frontend/dist/irrigation-plus.js ; git diff --cached --name-only | wc -l
```

Expected: `5`. Then:

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && git commit -F - <<'EOF'
fix(panel): stop saving the page's copy of a zone

Every settings input handed handleEditZone the whole zone with its one
field changed. The page re-reads its zones only on _update_frontend,
which a run's credit does not send, so after a run the copy still held
the pre-run bucket, and the next edit of any setting posted it back. The
backend took it for a level set by hand: the run's credit was undone,
the weather window restarted and the pending ledger was emptied. Each
call site now passes only what it sets; a test on the source keeps it
that way, in the suite CI runs.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

## Task 5: Gates

- [ ] **Step 1: Full backend suite**

Run in the background (tool option, not `nohup … &`):

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header > /d/Entwicklung/HASI/issue5-work/measure/branch-full-tzutc.txt 2>&1 ; tail -1 /d/Entwicklung/HASI/issue5-work/measure/branch-full-tzutc.txt
```

Expected: `7 failed, 3463 passed, 9 skipped, … 367 errors`.

- [ ] **Step 2: Diff the failure names against the baseline**

```bash
cd /d/Entwicklung/HASI/issue5-work/measure && grep -E "^(FAILED|ERROR) " branch-full-tzutc.txt | sed 's/ - .*//' | sort -u > branch-names.txt ; grep -E "^(FAILED|ERROR) " /d/Entwicklung/HASI/issue22-work/measure/baseline-1876aa03-tzutc.txt | sed 's/ - .*//' | sort -u > baseline-names.txt ; diff baseline-names.txt branch-names.txt && echo "NAMENS-DIFF LEER" ; wc -l baseline-names.txt branch-names.txt
```

Expected: `NAMENS-DIFF LEER`, both 375. A non-empty diff is a regression; read it before
touching anything.

- [ ] **Step 3: Panel gates**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt/custom_components/irrigation_plus/frontend && npx vitest run 2>&1 | grep -E "Test Files|Tests " ; npx tsc --noEmit -p . ; echo "tsc exit=$?" ; npm run build > /d/Entwicklung/HASI/issue5-work/build.log 2>&1 ; echo "build exit=$?" ; cd /d/Entwicklung/HASI/issue5-work/wt && git update-index --refresh > /dev/null 2>&1 ; git diff --quiet -- custom_components/irrigation_plus/frontend/dist/ && echo "committed dist == fresh build"
```

Expected: 24 files / 637 tests passed; `tsc exit=0`; `build exit=0`;
`committed dist == fresh build` (CI's freshness check does the same).

- [ ] **Step 4: Lint**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && uvx black custom_components/irrigation_plus/ tests/test_zone_view_save.py tests/test_manual_bucket_assertion.py tests/test_distributor_integration.py ; uvx ruff check custom_components/irrigation_plus/ tests/test_zone_view_save.py
```

- [ ] **Step 5: The reference checks, on the added lines and the messages**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && git diff upstream/master...HEAD -U0 -- custom_components tests | grep '^+' | grep -nEi "eifel-joe|issue ?#|befund|spec [A-Z0-9]|task [0-9]|\bN1\b|PR D" ; git log upstream/master..HEAD --format=%B | grep -nEi "eifel-joe|issue ?#|befund|spec [A-Z0-9]|task [0-9]|\bN1\b" ; grep -rn "Eifel-Joe" custom_components/ tests/ ; echo "--- alle drei ohne Ausgabe = sauber"
```

- [ ] **Step 6: Commit any formatting churn**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && git status --short ; git diff --quiet || { git add custom_components/irrigation_plus tests && git commit -m "style: black" ; }
```

Read the `git status` list first: it may list `dist/` card bundles as `M` (autocrlf). Those
are not churn; `git diff --quiet` ignores them.

---

## Task 6: Mutation matrix

Every decision this branch makes has a test that dies without it. Four tests in this plan are
known to pass on the base (the credit pin, the raised-maximum pin, the new-zone pin, the
funnel pin), so the matrix is what proves they are load-bearing.

**Files:**
- Use: `D:\Entwicklung\HASI\issue5-work\mutate.py` (kept; archived as
  `docs/superpowers/probes/2026-09-29-zone-save-mutations.py`)

- [ ] **Step 1: Check the runner against this branch**

Its mutation anchors are the exact lines of Tasks 1–4. If Task 5's `black` reformatted any
of them, the runner reports `anchor appears 0 times -- SKIPPED`; fix the anchor, not the code.
Its suite list must name the files the killers live in:
`tests/test_zone_view_save.py`, `tests/test_manual_bucket_assertion.py`,
`tests/test_distributor_integration.py`, plus the vitest file.

- [ ] **Step 2: Run it**

```bash
cd /d/Entwicklung/HASI/issue5-work && sha256sum wt/custom_components/irrigation_plus/websockets.py wt/custom_components/irrigation_plus/store.py wt/custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings.ts > pre-mutation.sha ; /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe mutate.py /d/Entwicklung/HASI/issue5-work/wt 2>&1 | tail -40 ; sha256sum -c pre-mutation.sha
```

Expected, as in the probe run:

| # | mutation | killed by |
|---|---|---|
| 1 | the six new strip entries gone | the whole-zone test |
| 2 | only `days_since_irrigation` gone | the whole-zone test |
| 3 | no pair completion | lone bucket, lowered maximum |
| 4 | completion when both or neither are posted | lone bucket, lowered maximum, three mock-based view tests |
| 5 | completion overwrites the posted value | lone bucket, lowered maximum, raised maximum |
| 6 | completion also on create | the new-zone test |
| 7 | the store completes the pair itself | the funnel test |
| 8 | posted without the zone id | six panel tests |
| 9 | one pending set for every zone | two zones in one window |
| 10 | an edit replaces the zone's pending edits | two edits to one zone |
| 11 | pending edits kept after posting | no second post |
| 12 | a cleared field stays `undefined` | cleared field as null |
| 13 | the change worked out against the page's copy | state + duration |
| 14 | a null id selects the text `"null"` | `_selectValue` |
| 15 | one call site spreads the page's copy again | the call-site pin |

Last lines: `every source restored byte-for-byte: True`, `15 killed / 15 applied / 15 total`,
and three `OK` from `sha256sum -c`. Also check each row's `summary` in
`issue5-work\mutations.json`: pytest must have collected (33 items) and vitest 8. A run that
collected nothing kills nothing and survives everything.

- [ ] **Step 3: Read every survivor as a weak test first**

Either add the assertion that kills it, or record the measurement that shows the mutated code
behaves identically. An argument is not a measurement.

---

## Task 7: Review

- [ ] **Step 1:** `superpowers:requesting-code-review` on `git diff upstream/master...HEAD`,
  with this plan and the design doc. The reviewer checks: every requirement R1–R7 has a
  change and a test; nothing outside the listed files moved; the comments follow `code-doku`
  (Wurzel, Fix-Logik, NOT-TO-DO) and none still describes the whole-zone save as the
  panel's normal case.
- [ ] **Step 2:** Every finding goes through `superpowers:receiving-code-review`, verified
  before it is acted on. A change re-runs Task 5 and, if it touches a mutated line, Task 6.

---

## Task 8: Live test on HA-Test

HA-Test is `192.168.10.196`, tools `mcp__HA-Test__…`. Name the instance before every write.
HA-Prod is not touched. A HA-Test restart is allowed, but announce it first (memory
`ha-no-auto-restart`). Zone fields can be set in the panel only. Read zone state through the
browser pane with the panel open: in its console,
`await document.querySelector("home-assistant").hass.callWS({type: "irrigation_plus/zones"})`.
**Not** through `ha_get_integration(include_diagnostics=True)`: that prints the weather API
key in plain text.

- [ ] **Step 1: The live RED, on today's build**

HA-Test runs `v2026.09.27b3` (verify: `update.smart_irrigation_update` →
`installed_version`). Choose a test zone (`Test2`, id 3, was used before) and record its
name, module and bucket.
1. Open Settings → Zones in the browser pane, expand the zone, and leave the page open.
2. Water it with the `run_zone` service and a `duration`. List the services first; the
   service name and its fields come from `ha_list_services`, not from memory.
3. When the run has credited (`water_used_total` has risen), read the zone through `callWS`:
   bucket, `last_consumed_at`, `pending_bucket_events`.
4. **Before touching the page**, confirm it still shows the pre-run bucket. If it refreshed
   in between, the run proves nothing; repeat.
5. On the still-open page, change the zone's name.
6. Read the zone again. Expected: the bucket back at the pre-run value, `last_consumed_at` at
   the save time, `pending_bucket_events` empty. That is the defect, live.

- [ ] **Step 2: A throwaway build with the fix** (outward-facing: push and release only after
  approval in the chat)

A branch `prerelease/v2026.09.29b1` from the fix branch's HEAD. Bump the version to
`v2026.09.29b1` in `manifest.json` and `const.py` `VERSION` (with `v`), and to `2026.09.29b1`
in `frontend/package.json` (without). Rebuild `dist` with the version baked in, then commit.
`production` is not touched. After approval: push the branch, create the prerelease on
exactly that commit, and attach the ZIP built from the commit SHA, never from the tag name
(the ZIP is what HACS installs):

```bash
git push -u origin prerelease/v2026.09.29b1
gh release create v2026.09.29b1 --repo Eifel-Joe/HAsmartirrigation --prerelease --target <prerelease-SHA> --title "v2026.09.29b1" --notes "Throwaway build for a live test on a test instance. Not for use."
git archive --format=zip -o irrigation_plus.zip <prerelease-SHA>:custom_components/irrigation_plus
gh release upload v2026.09.29b1 irrigation_plus.zip --repo Eifel-Joe/HAsmartirrigation
```

HACS sees a new fork release only after its repository information is refreshed
(`update_information` for `Eifel-Joe/HAsmartirrigation`). Install it on HA-Test through HACS
and restart HA-Test (announced). Verify `installed_version` = `v2026.09.29b1` and the config
entry `loaded`. Reload the panel with Ctrl+F5 (memory `hasi-frontend-refresh-drill`). The
release, its tag and the branch are throwaway: they can go once the PR is merged.

- [ ] **Step 3: The same sequence on the fix build**

Repeat Step 1's six points. Expected: bucket, `last_consumed_at` and
`pending_bucket_events` stay as the run left them; the name change lands.

- [ ] **Step 4: The three extra checks, on the fix build**
  - Edit two zones within half a second, reload: both edits are stored.
  - Clear a zone's module, reload: the select shows the empty option, not `null`, and
    `callWS` shows `module: null`.
  - Set the bucket by hand in the form: `last_consumed_at` moves to that moment and the
    ledger empties (JustChr#138 intact).

- [ ] **Step 5: Restore the test zone** (name, module, bucket as recorded in Step 1).
  Record the live protocol for the archive:
  `docs/superpowers/reconstructed/2026-09-29-zone-save-live-on-ha-test.md` with the times,
  values and the build SHA.

---

## Task 9: Archive, PR text, PR, issues

- [ ] **Step 1: Archive the design history (rule P1)**

Into `pr139-work/archive-wt`: this plan with its boxes ticked, `mutations.json` as
`docs/superpowers/probes/2026-09-29-zone-save-mutations-branch.json`, and the live protocol.
Commit there; push `archive/design-history` after approval. Then check the feature branch
carries code and tests only:

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && git diff upstream/master...HEAD --name-only
```

Expected: only paths under `custom_components/irrigation_plus/` and `tests/`.

- [ ] **Step 2: The PR body, shown in the chat for approval**

Nothing goes to GitHub without approval in the chat, corrections included. Structure:
`## Problem` / `## Fix` / `## Testing`, then the residual risk (a page left open across the
update keeps the old bundle and can revert a user-editable field once), and the
`🤖 Generated with [Claude Code](https://claude.com/claude-code)` footer. No reference to
this fork's issues. Re-run Task 5 Step 5's greps with the body file as a third target.

- [ ] **Step 3: Push and open the PR, after approval**

```bash
cd /d/Entwicklung/HASI/issue5-work/wt && git push -u origin fix/zone-save-sends-what-changed
gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/zone-save-sends-what-changed --title "fix(zones): a settings page left open across a run no longer undoes its credit" --body-file /d/Entwicklung/HASI/issue5-work/pr-body.md
```

- [ ] **Step 4: Our issues, after approval**

`Eifel-Joe#5` gets a comment and the label in the same move: why the build differs from the
body's allowlist (the form edits the bucket, so an allowlist of edited fields still lets the
stale value through), what was built instead, the PR link, and `upstream:gemeldet`. The
tracking issue `Eifel-Joe#42` gets the state change. English first, German below.

---

## Addendum 2026-09-29 (during execution) — where this section differs, it wins

Everything above stays as written. This section records what changed while the plan was
executed, and adds Tasks 4a–4c.

### Review findings folded into Tasks 1–4

| task | finding (reviewer, verified before acting) | change | commit |
|---|---|---|---|
| 1 | the credit pin passed with the credit turned into a no-op; `days_since_irrigation` defaults to 0 | seed the counter at 4; assert the credit happened (bucket 0.0, counter 0, ledger +1) | `52860467` |
| 1 | "After a run it still carries the pre-run values" is too absolute: a distributor cycle's start, advance and end dispatch `_update_frontend` (`distributor.py` `_dist_store_update`) | "it can still carry" | `52860467` |
| 2 | mutant `!=` → `or` survived: a post carrying both would get the posted maximum overwritten by the stored one | pin `test_a_post_that_carries_both_is_saved_as_it_was_posted` | `e8db0916` |
| 2 | the `stored is not None` guard had no test | pin `test_a_lone_bucket_for_an_id_the_store_does_not_know_creates_the_zone` | `e8db0916` |
| 2 | "credits, the calculation, a unit flip, set_all_buckets … none of them is clamped" is wrong: `convert_zone_values` (`unit_system.py`) writes bucket and maximum in one payload, so the flip IS clamped | the comments in `websockets.py` and `store.py` and the commit body name only credits, the calculation and `set_all_buckets` | `e8db0916` |
| 3 | the `zone.id === undefined` guard and the debounce window had no test | two vitest pins | `9618bd13` |
| 4 | the reset-bucket confirm runs its edit later (`_runPendingConfirm`); with the spread gone, the index at confirm time decides the zone, and a re-read in between can move another zone there | that one site calls `_editZoneById(zone.id, …)`; a vitest test (RED first) and a second pytest tripwire `test_a_confirmed_zone_edit_finds_its_zone_by_id` | Task 4 |

The other 34 call sites are synchronous event handlers (checked: none awaits before calling).
Trailers name the model that wrote each commit (`Claude Sonnet 5.5`), not the Opus line above.

### Tasks 4a–4c: the same shared save timer on three sibling pages

Found by the Task 3 review. One debounce timer that keeps only the object edited last — the
shape R2 fixes on the zone page — also sits on three more pages. The user first chose a
separate issue, then decided (2026-09-29): **into this PR, it belongs together**. These pages
post a whole object that carries no server-written field (sister-path table above), so only the
timer is wrong:

| page | method | lost |
|---|---|---|
| sensor groups | `view-mappings.ts` `handleEditMapping` | the first of two groups edited within 500 ms |
| distributors | `view-distributor-settings.ts` `handleEditDistributor` | the first of two distributors |
| modules | `view-modules.ts` `debouncedSave` (called by `handleEditConfig`) | the first of two modules |

`view-general.ts` already merges its deltas ("audit finding: silent per-field data loss") and
stays as it is. Each fix keeps the latest copy per object id in a map and, when the one timer
runs out, empties the map and saves every entry. Sensor groups and modules are not exported;
each gets `export { … };` at its end, as the zone and distributor views have, so the test can
build the element. Same harness as `view-zone-settings-save.test.ts`. Code must pass
`npm run lint` (prettier, printWidth 80); if lint flags only the formatting of changed lines,
`npx eslint --fix <file>` and read the diff.

Each task: export (where needed) → test file → RED (`1 failed | 1 passed (2)`; the second test
is a pin) → fix → GREEN (`2 passed (2)`) → `npx vitest run`, `tsc`, `npm run lint` → build
(only `dist/irrigation-plus.js` changes; `git add -f`, count) → one commit.

#### Task 4a: sensor groups

Files: create `frontend/src/views/mappings/view-mappings-save.test.ts`; modify
`frontend/src/views/mappings/view-mappings.ts`; rebuilt `dist/irrigation-plus.js`.

Export: after the class's closing `}` at the end of `view-mappings.ts`, add a blank line and
`export { SmartIrrigationViewMappings };`.

Test file:

```typescript
import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

beforeAll(() => {
  (globalThis as any).HTMLElement = class {};
  (globalThis as any).customElements = {
    define() {},
    get() {
      return undefined;
    },
    whenDefined: () => Promise.resolve(),
  };
  (globalThis as any).window = globalThis;
  // _scheduleUpdate() defers a re-render to the next frame; nothing renders here.
  (globalThis as any).requestAnimationFrame = () => 0;
});

type ViewModule = typeof import("./view-mappings");
let View: ViewModule["SmartIrrigationViewMappings"];
beforeAll(async () => {
  ({ SmartIrrigationViewMappings: View } = await import("./view-mappings"));
});

// A group without sensors: saveToHA checks each configured sensor entity
// against hass.states, and there is none to check.
function group(id: number, name: string) {
  return { id, name, mappings: {} };
}

function make(groups: unknown[]) {
  const callApi = vi.fn().mockResolvedValue(true);
  const el: any = new View();
  el.hass = { language: "en", states: {}, callApi };
  el.mappings = groups;
  return { el, callApi };
}

function saved(callApi: ReturnType<typeof vi.fn>) {
  return callApi.mock.calls.map(([method, path, body]) => {
    expect([method, path]).toEqual(["POST", "irrigation_plus/mappings"]);
    return body;
  });
}

describe("a sensor group edit is saved", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("saves every group edited inside one debounce window", () => {
    const { el, callApi } = make([group(1, "Garden"), group(2, "Bed")]);
    el.handleEditMapping(0, group(1, "Garden south"));
    el.handleEditMapping(1, group(2, "Bed north"));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      group(1, "Garden south"),
      group(2, "Bed north"),
    ]);
  });

  it("does not save a group twice once it has been saved", () => {
    const { el, callApi } = make([group(1, "Garden"), group(2, "Bed")]);
    el.handleEditMapping(0, group(1, "Garden south"));
    vi.advanceTimersByTime(500);
    el.handleEditMapping(1, group(2, "Bed north"));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      group(1, "Garden south"),
      group(2, "Bed north"),
    ]);
  });
});
```

Field, directly after `private globalDebounceTimer: number | null = null;`:

```typescript
  // Edited groups not saved yet, latest copy per id (see handleEditMapping).
  private _pendingSaves = new Map<number | undefined, SmartIrrigationMapping>();
```

In `handleEditMapping`, replace from `    // Use global debounce to reduce timer overhead` down to and
including `    }, 500); // Increased debounce time to reduce backend load` with:

```typescript
    // Wurzel: the one debounce timer kept only the group edited last, so a
    //   second group edited within half a second cancelled the first one's
    //   save: the page showed the edit, the server never got it.
    // Fix-Logik: keep the latest copy per group and save every one of them
    //   when the timer runs out, as the zone settings page does.
    // See view-mappings-save.test.ts.
    this._pendingSaves.set(updatedMapping.id, updatedMapping);
    if (this.globalDebounceTimer) {
      clearTimeout(this.globalDebounceTimer);
    }

    // Debounce saving to avoid excessive API calls during rapid editing
    this.globalDebounceTimer = window.setTimeout(() => {
      this.globalDebounceTimer = null;
      // Taken out before saving: an edit made while these are in flight
      // belongs to the next round.
      const batch = [...this._pendingSaves.values()];
      this._pendingSaves.clear();
      this.isSaving = true;
      Promise.all(
        batch.map((mapping) =>
          this.saveToHA(mapping).catch((error) => {
            console.error("Failed to save mapping:", error);
            showErrorToast(
              this,
              this.hass,
              "common.errors.save_failed",
              error,
            );
          }),
        ),
      ).finally(() => {
        this.isSaving = false;
        this._scheduleUpdate();
      });
    }, 500); // Increased debounce time to reduce backend load
```

Each group's save keeps its own `catch`, so a group with an invalid sensor still toasts and does
not stop the others.

Commit:

```
fix(panel): save every sensor group edited within one debounce window

The save timer was shared by all groups and kept only the one edited
last, so a second group edited within half a second dropped the first
group's save: the page showed the edit, the server never got it. Edits
are now kept per group, and every one of them is saved when the timer
runs out.
```

#### Task 4b: distributors

Files: create `frontend/src/views/setup/view-distributor-settings-save.test.ts`; modify
`frontend/src/views/setup/view-distributor-settings.ts`; rebuilt `dist/irrigation-plus.js`.
The class is already exported.

Test file: same imports and `beforeAll` shim as 4a, then:

```typescript
type ViewModule = typeof import("./view-distributor-settings");
let View: ViewModule["SmartIrrigationViewDistributorSettings"];
beforeAll(async () => {
  ({ SmartIrrigationViewDistributorSettings: View } =
    await import("./view-distributor-settings"));
});

function distributor(id: number, pause_seconds: number) {
  return { id, name: `Distributor ${id}`, pause_seconds };
}

function make(distributors: unknown[]) {
  const callApi = vi.fn().mockResolvedValue(true);
  const el: any = new View();
  el.hass = { language: "en", states: {}, callApi };
  el.distributors = distributors;
  return { el, callApi };
}

// Which distributor each save was for, and the value edited on it.
function saved(callApi: ReturnType<typeof vi.fn>) {
  return callApi.mock.calls.map(([method, path, body]) => {
    expect([method, path]).toEqual(["POST", "irrigation_plus/distributors"]);
    return [body.id, body.pause_seconds];
  });
}

describe("a distributor edit is saved", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("saves every distributor edited inside one debounce window", () => {
    const { el, callApi } = make([distributor(1, 5), distributor(2, 5)]);
    el.handleEditDistributor(0, distributor(1, 7));
    el.handleEditDistributor(1, distributor(2, 9));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      [1, 7],
      [2, 9],
    ]);
  });

  it("does not save a distributor twice once it has been saved", () => {
    const { el, callApi } = make([distributor(1, 5), distributor(2, 5)]);
    el.handleEditDistributor(0, distributor(1, 7));
    vi.advanceTimersByTime(500);
    el.handleEditDistributor(1, distributor(2, 9));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      [1, 7],
      [2, 9],
    ]);
  });
});
```

Field, directly after `private globalDebounceTimer: number | null = null;`:

```typescript
  // Edited distributors not saved yet, latest per id (handleEditDistributor).
  private _pendingSaves = new Map<
    number | undefined,
    SmartIrrigationDistributor
  >();
```

In `handleEditDistributor`, replace from
`    if (this.globalDebounceTimer) clearTimeout(this.globalDebounceTimer);` down to and including
the `    }, 500);` that closes the timer with:

```typescript
    // Wurzel: the one debounce timer kept only the distributor edited last,
    //   so a second one edited within half a second cancelled the first one's
    //   save: the page showed the edit, the server never got it.
    // Fix-Logik: keep the latest copy per distributor and save every one of
    //   them when the timer runs out, as the zone settings page does.
    // See view-distributor-settings-save.test.ts.
    this._pendingSaves.set(updated.id, updated);
    if (this.globalDebounceTimer) clearTimeout(this.globalDebounceTimer);
    this.globalDebounceTimer = window.setTimeout(() => {
      this.globalDebounceTimer = null;
      // Taken out before saving: an edit made while these are in flight
      // belongs to the next round.
      const batch = [...this._pendingSaves.values()];
      this._pendingSaves.clear();
      this.isSaving = true;
      this._saveStatus = "saving";
      Promise.all(
        batch.map((d) => saveDistributor(this.hass!, this._configPayload(d))),
      )
        .then(() => this._markSaved())
        .catch((error) => {
          console.error("Failed to save distributor:", error);
          this._saveStatus = "idle";
          showErrorToast(this, this.hass, "common.errors.save_failed", error);
        })
        .finally(() => {
          this.isSaving = false;
          this._scheduleUpdate();
        });
    }, 500);
```

Commit: as 4a, with "distributor(s)" for "group(s)":
`fix(panel): save every distributor edited within one debounce window`.

#### Task 4c: modules

Files: create `frontend/src/views/modules/view-modules-save.test.ts`; modify
`frontend/src/views/modules/view-modules.ts`; rebuilt `dist/irrigation-plus.js`.

Export: after the class's closing `}` at the end of `view-modules.ts`, add a blank line and
`export { SmartIrrigationViewModules };`.

Test file: same imports and `beforeAll` shim as 4a, then:

```typescript
type ViewModule = typeof import("./view-modules");
let View: ViewModule["SmartIrrigationViewModules"];
beforeAll(async () => {
  ({ SmartIrrigationViewModules: View } = await import("./view-modules"));
});

function mod(id: number, name: string) {
  return { id, name, config: {} };
}

function make(modules: unknown[]) {
  const callApi = vi.fn().mockResolvedValue(true);
  const el: any = new View();
  el.hass = { language: "en", states: {}, callApi };
  el.modules = modules;
  return { el, callApi };
}

// Which module each save was for, and the name it was saved with.
function saved(callApi: ReturnType<typeof vi.fn>) {
  return callApi.mock.calls.map(([method, path, body]) => {
    expect([method, path]).toEqual(["POST", "irrigation_plus/modules"]);
    return [body.id, body.name];
  });
}

describe("a module edit is saved", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("saves every module edited inside one debounce window", () => {
    const { el, callApi } = make([mod(1, "PyETO"), mod(2, "Static")]);
    el.handleEditConfig(0, mod(1, "PyETO east"));
    el.handleEditConfig(1, mod(2, "Static west"));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      [1, "PyETO east"],
      [2, "Static west"],
    ]);
  });

  it("does not save a module twice once it has been saved", () => {
    const { el, callApi } = make([mod(1, "PyETO"), mod(2, "Static")]);
    el.handleEditConfig(0, mod(1, "PyETO east"));
    vi.advanceTimersByTime(500);
    el.handleEditConfig(1, mod(2, "Static west"));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      [1, "PyETO east"],
      [2, "Static west"],
    ]);
  });
});
```

Replace the whole `debouncedSave` field, from `  // Debounced save operation for better performance`
to its closing `  })();`, with:

```typescript
  // Debounced save operation for better performance
  // Wurzel: the one debounce timer kept only the module edited last, so a
  //   second module edited within half a second cancelled the first one's
  //   save: the page showed the edit, the server never got it.
  // Fix-Logik: keep the latest copy per module and save every one of them
  //   when the timer runs out, as the zone settings page does.
  // See view-modules-save.test.ts.
  private debouncedSave = (() => {
    let timeoutId: number | null = null;
    const pending = new Map<number | undefined, SmartIrrigationModule>();
    return (module: SmartIrrigationModule) => {
      pending.set(module.id, module);
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      timeoutId = window.setTimeout(() => {
        timeoutId = null;
        // Taken out before saving: an edit made while these are in flight
        // belongs to the next round.
        const batch = [...pending.values()];
        pending.clear();
        batch.forEach((m) => this.saveToHA(m));
      }, 500); // 500ms debounce
    };
  })();
```

`saveToHA` already toasts a failure itself, as before.

Commit: `fix(panel): save every module edited within one debounce window`, body as 4a.

### Numbers after the addendum (replace the table at the top)

| check | plan | now |
|---|---|---|
| `tests/test_zone_view_save.py` | 8 | 11 |
| `view-zone-settings-save.test.ts` | 8 | 11 |
| three new `*-save.test.ts` (4a–4c) | — | 2 each |
| vitest, all files | 24 files / 637 | 27 files / 646 |
| three-file pytest run (Task 2 step 6 command) | 32 passed, 5 errors | 36 passed, 5 errors |
| full backend suite, `TZ=UTC` | 7 / 3463 / 9 / 367 | 7 / 3466 / 9 / 367; FAILED/ERROR names identical, 375 = 375 |
| mutation runner collection | pytest 33, vitest 8 | pytest 36, vitest 11 + 3 × 2 |
| build | only `dist/irrigation-plus.js` changes | unchanged, after every task |

### Task 6 additions

`mutate.py` runs every vitest file (`VITEST_FILES`: the zone save test and the three new ones).
Rows 16–27, each with its expected killer:

| # | file | mutation | killed by |
|---|---|---|---|
| 16 | websockets.py | `(… in data) != (` → `(… in data) or (` | carries-both pin |
| 17 | websockets.py | `if stored is not None:` → `if True:` | unknown-id pin |
| 18 | zone view | `if (zone.id === undefined) return;` removed | no-id vitest |
| 19 | zone view | the handleEditZone timer's `}, 500);` → `}, 1);` | window vitest |
| 20 | zone view | `this._editZoneById(zone.id, {` → `this.handleEditZone(index, {` | by-id pytest tripwire |
| 21 | zone view | `findIndex((z) => z.id === id)` → `findIndex((z) => z.id !== id)` | by-id vitest |
| 22 | mappings | `_pendingSaves.clear()` before every `set` | two-groups test |
| 23 | mappings | `_pendingSaves.clear()` after taking the batch removed | not-twice (groups) |
| 24 | distributors | as 22 | two-distributors test |
| 25 | distributors | as 23 | not-twice (distributors) |
| 26 | modules | `pending.clear()` before every `set` | two-modules test |
| 27 | modules | `pending.clear()` after taking the batch removed | not-twice (modules) |

Expected: `27 killed / 27 applied / 27 total`, every source restored byte-for-byte.

### Task 8 additions

- On today's build, after Step 1: rename two sensor groups within half a second (browser
  batch), reload. Expected: only the second name stored — the live RED for 4a–4c.
- On the fix build, after Step 4: the same for two sensor groups, two distributors (if HA-Test
  has two; otherwise say so) and two modules. Expected: both edits stored after a reload.
- Restore every name and value afterwards.
