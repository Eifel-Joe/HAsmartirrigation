# The distributor does not start over an open inlet — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A distributor cycle never starts while its inlet reports open, through every entry
and in every watch mode, except within 30 s of the integration's own close command; a refused
cycle is logged, notified and recorded in the members' history.

**Architecture:** One synchronous check in the claim (`async_run_distributor_cycle`), between
the in-flight guard and `inflight.add`, reads the inlet's live state. A refusal path runs only
after the claim has decided not to take the distributor, so it may await. `_dist_close_inlet`
stamps the loop time once a close command has actually been sent, and the check ignores an
open report for 30 s after that stamp. Nothing is persisted, and the finish-anchor estimate
is not touched. Design: `docs/superpowers/specs/2026-09-29-distributor-inlet-open-gate-design.md`
on `archive/design-history`.

**Tech Stack:** Python 3.12, Home Assistant custom component, pytest +
pytest-homeassistant-custom-component, `black`, `ruff`; the panel's JSON catalogues in eight
languages; rollup, for the two bundles that embed `en.json`.

---

## This plan was run once before it was handed over

On 2026-09-29 Tasks 1–8 were applied to a throwaway worktree on `0b9a71bd`
(`D:\Entwicklung\HASI\issue66-work\probe-wt`, detached, removed afterwards), each RED and GREEN
step measured, then the full suite and the mutation matrix. Where the plan text did not hold, the
**Addendum at the end** says what changed; it wins over the task text. The numbers, so a
deviation shows at once:

| check | on `0b9a71bd` | with the change |
|---|---|---|
| Task 1's test | FAILED at the claim, `assert True is False`; with that assertion removed still FAILED (`_dist_credit_zone` never awaited: the claim dropped the stash) | passed |
| `test_distributor_inlet_gate.py` with Task 2's tests | 11 failed / 8 passed, all 11 `assert True is False` | 19 passed |
| … with Task 3's tests | 6 failed / 21 passed (3× `AttributeError` on `SKIP_REASON_INLET_OPEN`); Step 6: 2 failed / 25 passed | 27 passed; with `test_i18n_completeness.py` 94 passed (67 i18n) |
| … with Task 4's tests | 2 failed / 31 passed, both `assert False is True` | 33 passed |
| … with Task 5's pins | — | 40 passed at the first run; no host stub was missing |
| the four distributor suites (Task 2 Step 7, Task 4 Step 8) | — | 207 passed both times; no FAILED/ERROR name outside the baseline |
| catalogues (Task 3 Step 7) | — | `3	1` per language, not `2	0` (Addendum A3) |
| `npm run build` | — | exit 0; only `irrigation-plus.js` and `irrigation-plus-card-impl.js` change; committed dist == fresh build |
| `black --check`, `ruff check` | — | clean after each task; `black` reformatted three places of the plan's code (Addendum A1, A2, A4) |
| reference greps (Task 7 Step 5) | the third grep is **not** empty on the base | empty with the corrected third grep (Addendum A6) |
| full backend suite, `TZ=UTC` | 7 failed / 3466 passed / 9 skipped / 367 errors (374 names) | 7 / 3506 / 9 / 367 with the 40 new tests; FAILED/ERROR names identical, 374 = 374 |
| mutation matrix | — | 18 killed of 18: 17 in the matrix; mutation 5 deadlocks an existing test there (`HANG`, Addendum A7) and is killed by `test_a_distributor_in_flight_is_not_reported_as_an_open_inlet` in its re-run. Mutation 2 kills all six entry pins, mutation 18 the estimate pin. Every source restored byte-for-byte, `sha256sum -c` OK |

Evidence kept outside the repo: `D:\Entwicklung\HASI\issue66-work\measure\baseline-0b9a71bd-tzutc.txt`
and `baseline-names.txt` (the real run reuses both, Addendum A8), `…\measure\probe-full-tzutc.txt`,
`…\probe\mutations-probe.json`, `…\probe\mutate.py`, `…\probe\blocks\` (every code block of this
plan, extracted and applied verbatim).

---

## Ground rules for every task

**Worktree:** `D:\Entwicklung\HASI\issue66-work\wt`, branch `fix/distributor-inlet-open-gate`
from `upstream/master` (Task 0 creates both). There is no `.venv` in it; the interpreter is
named absolutely. Scratch output goes to `D:\Entwicklung\HASI\issue66-work\` — never to `C:`.

**Commands, verbatim.** Backend tests, from the worktree root:

```bash
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock -q --no-header
```

Lint for CI, from the worktree root (only these two count, only on this path), **in every
task before its commit**:

```bash
uvx black custom_components/irrigation_plus/ tests/test_distributor_inlet_gate.py ; uvx ruff check custom_components/irrigation_plus/ tests/test_distributor_inlet_gate.py
```

Panel build, from `custom_components/irrigation_plus/frontend` (Task 3 only):

```bash
npm run build
```

**Always under `TZ=UTC`.** The `hass` fixture puts HA on US/Pacific, this machine runs Berlin,
CI runs UTC. A suite run without it is not comparable to the baseline.

**No tracker references in anything that goes upstream.** Code, comments, docstrings, test
names and commit messages carry no `Eifel-Joe#…`, no `#66`, no `R6`, no `H2`, no `spec`, no
`Task N`, no `L5`. Upstream's own numbers (`#181`, `#170`) are fine, as elsewhere in the code.
This plan and the design doc may name ours; nothing under `custom_components/` or `tests/`
may. Task 7 greps for it; that is the second line of defence.

**Every task ends on a commit.** Multi-line messages via heredoc (`git commit -F - <<'EOF'`),
never PowerShell. Last line: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

**Comments follow the skill `code-doku`:** for the non-trivial parts, the root cause
(`Wurzel:`), the fix, the rejected alternative (`NOT-TO-DO:`) and the pinning test
(`siehe …`), as the surrounding code in `distributor.py` already does.

**Windows traps that have cost time before:**
- `git status` shows untouched `dist/*.js` as `M` after a build (`core.autocrlf=true`
  artefact). `git diff --quiet -- <file>` decides; exit 0 means no content change.
- `dist/` is gitignored as a directory while its four bundles are tracked:
  `git add` without `-f` fails and swallows a chained commit. Always `git add -f`, then count
  `git diff --cached --name-only`.
- The language files are CRLF in the working copy and LF in the repository. Edit them only
  with Task 3's script, which reads and writes bytes.
- `grep -c` with no match exits 1 and breaks an `&&` chain. Chain checks with `;`.
- No `nohup … &` for suite runs; use the tool's background mode, and before any verdict
  check that the run collected tests (its summary line exists and is not `0 passed`).

---

## File structure

| File | Responsibility | Change |
|---|---|---|
| `custom_components/irrigation_plus/const.py` | constants | `SKIP_REASON_INLET_OPEN`, `DISTRIBUTOR_INLET_OPEN_STATES`, `DISTRIBUTOR_INLET_CLOSE_GRACE_SECONDS` |
| `custom_components/irrigation_plus/distributor.py` | the distributor mixin | `_dist_own_close_times`, the stamp in `_dist_close_inlet`, `_dist_inlet_reports_open`, `_dist_refuse_inlet_open`, the gate in `async_run_distributor_cycle` |
| `custom_components/irrigation_plus/frontend/localize/languages/*.json` (8) | the panel and backend catalogue | `panels.distributors.notify.inlet_open`, `panels.zones.outlook.checks.inlet_open` |
| `custom_components/irrigation_plus/frontend/dist/irrigation-plus.js`, `…/irrigation-plus-card-impl.js` | the two bundles that embed `en.json` | rebuilt (the other two bundles do not change) |
| `docs/configuration-distributors.md` | user documentation | one paragraph |
| `tests/test_distributor_inlet_gate.py` | **new**: every test of this work | Tasks 1–5 |

No file is split. Every change sits next to the state it guards: the claim's guards, the
close that actuates the inlet, the notification the halt already uses.

## Sister paths — checked while planning, nothing to fix

Read on `0b9a71bd`:

| path | why it needs nothing |
|---|---|
| every sweep entry | all reach `async_run_distributor_cycle` (`distributor.py:1166`): the schedule through `_dispatch_distributor_cycles` (`:412`), *Water all zones* and *Irrigate now*, the member run, `handle_distributor_run_now` (`:1886`), the test run `async_run_distributor_test` (`:1782`). One gate covers them. |
| direct zones | already guarded by `_drop_zones_already_running` (`irrigation.py:3379`) |
| `async_resume_distributor_cycles` (`:1810`) | closes an inlet after a restart and marks the ring uncertain; it starts nothing |
| the four callers of `_dist_close_inlet` | `:1255` safety close, `:1595` halt after a failed confirm, `:1725` end of each leg, `:1824` resume; all stamp through the one method |
| the finish-anchor estimate | reads `_dist_eligible_for_run` (`:383`), which this work does not touch |

If `upstream/master` has moved when this plan is executed, re-read this table before relying
on it.

---

## Task 0: Worktree, base, baseline

- [x] **Step 1: Confirm the base**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation && git fetch upstream && git rev-parse --short=8 upstream/master
```

Expected: `0b9a71bd`. If it is anything else, **stop**: the baseline below is measured on
the base, and the line numbers in this plan were read on `0b9a71bd`. Re-read the anchors this
plan edits (`_dist_close_inlet`, the claim's guards, the `SKIP_REASON_*` block, the
`DISTRIBUTOR_WATCH_MODE_*` block) and the sister-path table, then go on.

- [x] **Step 2: Create the worktree, the socket plugin, the import probe, the panel's
  dependencies**

```bash
mkdir -p /d/Entwicklung/HASI/issue66-work/measure /d/Entwicklung/HASI/issue66-work/tmp ; cd /d/Entwicklung/HASI/HAsmartirrigation && git worktree add -b fix/distributor-inlet-open-gate /d/Entwicklung/HASI/issue66-work/wt upstream/master ; cp /d/Entwicklung/HASI/HAsmartirrigation/_local_socket_unblock.py /d/Entwicklung/HASI/issue66-work/wt/ ; cp /d/Entwicklung/HASI/issue5-work/probe_import_origin.py /d/Entwicklung/HASI/issue66-work/ ; cd /d/Entwicklung/HASI/issue66-work/wt/custom_components/irrigation_plus/frontend && npm ci --no-audit --no-fund
```

`probe_import_origin.py` is copied because `issue5-work` is due to be cleaned up.

- [x] **Step 3: Confirm pytest imports this worktree's code**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && PYTHONPATH=/d/Entwicklung/HASI/issue66-work TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_cycle.py --co -q -p probe_import_origin -p _local_socket_unblock | grep IMPORT-ORIGIN
```

Expected: both lines point into `D:\Entwicklung\HASI\issue66-work\wt\custom_components`.

- [x] **Step 4: Measure the baseline on the base**

> **Addendum A8:** the dry run measured this on `0b9a71bd` into these very files. If Step 1
> read `0b9a71bd`, keep them and skip this step.

Run in the background (tool option, not `nohup … &`), then read the file only after the run
has ended:

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && export TEMP=D:/Entwicklung/HASI/issue66-work/tmp TMP=D:/Entwicklung/HASI/issue66-work/tmp TMPDIR=D:/Entwicklung/HASI/issue66-work/tmp ; TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header > /d/Entwicklung/HASI/issue66-work/measure/baseline-0b9a71bd-tzutc.txt 2>&1 ; tail -1 /d/Entwicklung/HASI/issue66-work/measure/baseline-0b9a71bd-tzutc.txt
```

Record the summary line in this plan. The local environment has known failures and errors
(Python 3.12 + HA 2024.12.5; CI is the authoritative gate), so Task 7 compares **names**, not
counts. Then extract the names once:

```bash
cd /d/Entwicklung/HASI/issue66-work/measure && grep -E "^(FAILED|ERROR) tests/" baseline-0b9a71bd-tzutc.txt | sed 's/ - .*//' | sort -u > baseline-names.txt ; wc -l baseline-names.txt
```

No commit: nothing has changed.

---

## Task 1: The measured case, as a test that fails today

The measurement in one unit test: the foreign open goes through the **real** inlet handler
(count mode, observed watering on), a cycle is asked for while the inlet is open, and the
foreign run's close edge must still credit the member whose outlet had the water. Today the
claim takes the distributor and pops the foreign open's stash (`distributor.py:1212`), so the
close edge finds nothing to credit. The sweep is stubbed: what it would water is the next
member, and that is exactly what the claim must not start.

**Files:**
- Create: `tests/test_distributor_inlet_gate.py`

- [x] **Step 1: Write the failing test**

> **Addendum A1:** write the last-but-one assertion as `black` does (wrapped in parentheses).

```python
"""A distributor cycle never starts while its inlet reports open (#181).

Measured on a test instance in count watch mode: a cycle claimed while a foreign
run held the inlet open watered over it. Opening an inlet that is already open
makes no edge, so the ring did not index; the leg was credited to the next member,
the member whose outlet had the water got nothing, and the stored position ended
one ahead while it still read synced. These tests pin the gate in the claim, what
a refused cycle leaves behind, and the grace after the integration's own close.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.irrigation_plus import const
from tests.test_distributor_cycle import _dist_cfg, _loop_host, _mem


def _gated_cfg(**kw):
    """A synced, confirmed distributor with an inlet entity."""
    d = _dist_cfg(inlet_entity="switch.inlet")
    d.update(kw)
    return d


def _gate_host(members=None, *, inlet_state="on", now=1000.0):
    """A cycle host whose inlet reports ``inlet_state`` and whose loop clock reads ``now``.

    ``inlet_state=None`` makes ``hass.states.get`` return None (the entity does not
    exist). The sweep is stubbed: these tests are about the claim's decision, and
    ``_dist_run_sweep`` returning True is what a delivered cycle looks like to it.
    ``_record_skipped_run`` is stubbed because the real one awaits the store.
    """
    c = _loop_host(
        members if members is not None else [_mem(1, 1), _mem(2, 2), _mem(3, 3)]
    )
    c.hass.config.language = "en"
    c.hass.states.get = Mock(
        return_value=None if inlet_state is None else SimpleNamespace(state=inlet_state)
    )
    c.hass.loop.time = Mock(return_value=now)
    c._dist_run_sweep = AsyncMock(return_value=True)
    c._record_skipped_run = AsyncMock()
    return c


def _evt(old, new):
    """A state-change event as the inlet handler reads it."""
    return SimpleNamespace(
        data={
            "old_state": SimpleNamespace(state=old),
            "new_state": SimpleNamespace(state=new),
        }
    )


async def test_a_foreign_open_keeps_its_credit_when_a_cycle_is_asked_for_meanwhile():
    c = _gate_host([_mem(1, 1), _mem(2, 2), _mem(3, 3)], now=100.0)
    c.hass.data = {}  # _dist_store_update fires the real dispatcher; short-circuit it
    c.store.config.observed_watering_enabled = True
    c.store.get_distributor = Mock(
        return_value=_gated_cfg(
            current_outlet=2,
            watch_mode=const.DISTRIBUTOR_WATCH_MODE_COUNT,
            skip_pulse_seconds=30,
            active_cycle={},
        )
    )
    tasks = []
    c.hass.async_create_task = Mock(
        side_effect=lambda coro: tasks.append(asyncio.ensure_future(coro))
    )
    handler = c._dist_inlet_state_handler(0)

    # The foreign open: count advances the stored position 2 -> 3 and stashes
    # outlet 2, the one that has the water.
    handler(_evt("off", "on"))
    await asyncio.gather(*tasks)
    tasks.clear()

    # A cycle is asked for while the inlet is still open.
    assert await c.async_run_distributor_cycle(_gated_cfg(current_outlet=3)) is False
    c._dist_run_sweep.assert_not_awaited()

    # The foreign run ends 300 s after it began: its member is credited.
    c.hass.loop.time.return_value = 400.0
    handler(_evt("on", "off"))
    await asyncio.gather(*tasks)

    zone, seconds = c._dist_credit_zone.await_args.args
    assert zone[const.ZONE_ID] == 2
    assert seconds == 300.0
    assert c._dist_credit_zone.await_args.kwargs["trigger"] == const.RUN_TRIGGER_OBSERVED
    # The only position write is the foreign open's own advance.
    c.store.async_update_distributor.assert_awaited_once_with(0, {"current_outlet": 3})
```

- [x] **Step 2: Run it to verify it fails**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_inlet_gate.py -p _local_socket_unblock -q --no-header
```

Expected: 1 failed, at the claim's line, with `assert True is False` — today the claim takes
the distributor over the open inlet. If it fails anywhere else (the handler, the pulse's
store write, the dispatcher), the host is wrong; fix the host before going on.

- [x] **Step 3: No commit**

The test stays red until Task 2, which commits it together with the gate (one commit per
green task).

---

## Task 2: The claim refuses a cycle while the inlet reports open

**Files:**
- Modify: `custom_components/irrigation_plus/const.py` (after the `DISTRIBUTOR_WATCH_MODE_*`
  block, `:1253-1257`)
- Modify: `custom_components/irrigation_plus/distributor.py` (a new method before
  `async_run_distributor_cycle`; the claim's guards, `:1197-1204`)
- Test: `tests/test_distributor_inlet_gate.py`

- [x] **Step 1: Write the failing tests**

Append to `tests/test_distributor_inlet_gate.py` (Task 1 created the file, its imports and
the helpers `_gated_cfg`, `_gate_host`, `_evt`; add `import pytest` to the imports):

```python
@pytest.mark.parametrize("state", ["on", "open", "opening", "closing"])
async def test_the_claim_refuses_while_the_inlet_reports_open(state):
    c = _gate_host(inlet_state=state)

    assert await c.async_run_distributor_cycle(_gated_cfg()) is False

    c._dist_run_sweep.assert_not_awaited()
    c._dist_persist_cycle.assert_not_awaited()  # no STARTING marker, no active_cycle
    c._dist_master_start.assert_not_awaited()
    c._dist_open_inlet.assert_not_awaited()  # a refusal actuates nothing
    c._dist_close_inlet.assert_not_awaited()
    assert 0 not in c._dist_inflight_ids()


@pytest.mark.parametrize("state", ["off", "closed", "unavailable", "unknown", "idle"])
async def test_the_claim_lets_a_cycle_through_when_the_inlet_is_not_open(state):
    c = _gate_host(inlet_state=state)

    assert await c.async_run_distributor_cycle(_gated_cfg()) is True

    c._dist_run_sweep.assert_awaited_once()


async def test_the_claim_lets_a_cycle_through_when_the_inlet_entity_does_not_exist():
    c = _gate_host(inlet_state=None)

    assert await c.async_run_distributor_cycle(_gated_cfg()) is True


@pytest.mark.parametrize("inlet", ["", None])
async def test_the_claim_lets_a_cycle_through_without_an_inlet_entity(inlet):
    c = _gate_host(inlet_state="on")

    assert await c.async_run_distributor_cycle(_gated_cfg(inlet_entity=inlet)) is True

    c.hass.states.get.assert_not_called()


@pytest.mark.parametrize(
    "watch_mode",
    [
        const.DISTRIBUTOR_WATCH_MODE_COUNT,
        const.DISTRIBUTOR_WATCH_MODE_WARN,
        const.DISTRIBUTOR_WATCH_MODE_IGNORE,
    ],
)
@pytest.mark.parametrize(
    "watering_mode", [const.WATERING_MODE_CLASSIC, const.WATERING_MODE_SERVICE]
)
async def test_the_claim_refuses_in_every_watch_and_watering_mode(
    watch_mode, watering_mode
):
    c = _gate_host(inlet_state="on")
    cfg = _gated_cfg(watch_mode=watch_mode, watering_mode=watering_mode)

    assert await c.async_run_distributor_cycle(cfg) is False

    c._dist_run_sweep.assert_not_awaited()
```

- [x] **Step 2: Run them to verify they fail**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_inlet_gate.py -p _local_socket_unblock -q --no-header
```

Expected: `test_the_claim_refuses_while_the_inlet_reports_open` (4 cases) and
`test_the_claim_refuses_in_every_watch_and_watering_mode` (6 cases) FAIL with
`assert True is False`; the pass-through tests (8 cases) pass already; Task 1's test still
fails.

- [x] **Step 3: Add the constant**

In `const.py`, directly after `DISTRIBUTOR_REASON_FOREIGN_PULSE = "foreign_inlet_pulse"`:

```python

# Distributor inlet gate (#181): a cycle is refused while its inlet reports one of
# these states -- open, on its way open, or not closed yet, so the ring has not
# indexed. Every other state (off, closed, unavailable, unknown, a missing entity)
# lets it through: "not available" is not "open".
DISTRIBUTOR_INLET_OPEN_STATES = frozenset({"on", "open", "opening", "closing"})
```

- [x] **Step 4: Add the check**

In `distributor.py`, directly before `async def async_run_distributor_cycle(`:

```python
    def _dist_inlet_reports_open(self, distributor: dict) -> str | None:
        """The inlet state that refuses a cycle now, or ``None`` (#181).

        Wurzel: the claim asked synced / confirmed / in flight and nothing about the
          inlet, so a cycle claimed while a foreign run held the inlet open watered
          over it: opening an inlet that is already open makes no edge, the ring does
          not index, the leg is credited to the next member, and the stored position
          ends one ahead while it still reads synced.
        Fix: refuse on exactly DISTRIBUTOR_INLET_OPEN_STATES. ``closing`` counts
          because the valve has not closed yet and the ring has not indexed. Nothing
          else refuses; a distributor without an inlet entity has no signal and keeps
          today's behaviour. Independent of the watch mode and the watering mode.
        Synchronous on purpose: the claim calls it between its in-flight check and
        ``inflight.add``, where an await would reopen the single-flight window.
        NOT-TO-DO: do not move this into _dist_eligible_for_run. Two entries call the
          claim directly (distributor_run_now, the test run), and that predicate also
          feeds the finish-anchor estimate, which must not depend on the moment it
          runs.
        siehe test_distributor_inlet_gate.py::test_the_claim_refuses_while_the_inlet_reports_open
        """
        entity_id = distributor.get("inlet_entity")
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state not in const.DISTRIBUTOR_INLET_OPEN_STATES:
            return None
        return state.state
```

- [x] **Step 5: Call it in the claim**

In `async_run_distributor_cycle`, replace

```python
        inflight = self._dist_inflight_ids()
        if dist_id in inflight:
            return False
        inflight.add(dist_id)
```

with

```python
        inflight = self._dist_inflight_ids()
        if dist_id in inflight:
            return False
        # #181: never start over an open inlet. After the in-flight guard, because
        # the integration's own sweep holds the inlet open and must read "in
        # flight", not "open"; before inflight.add with no await in between, so the
        # single-flight guarantee is unchanged.
        if self._dist_inlet_reports_open(distributor) is not None:
            return False
        inflight.add(dist_id)
```

- [x] **Step 6: Run the tests to verify they pass**

Same command as Step 2. Expected: every test in the file passes, **including Task 1's**.

- [x] **Step 7: Run the distributor suites for regressions**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor.py tests/test_distributor_cycle.py tests/test_distributor_dispatch.py tests/test_distributor_integration.py -p _local_socket_unblock -q --no-header
```

Expected: no failure that is not in `baseline-names.txt`. The existing hosts give `hass` a
`Mock`, whose `states.get(...).state` is a `Mock` and therefore never in the frozenset; the
tests that set `inlet_entity` stay green for that reason. If one fails, read why before
touching it.

- [x] **Step 8: Lint, then commit**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && uvx black custom_components/irrigation_plus/ tests/test_distributor_inlet_gate.py ; uvx ruff check custom_components/irrigation_plus/ tests/test_distributor_inlet_gate.py ; git add custom_components/irrigation_plus/const.py custom_components/irrigation_plus/distributor.py tests/test_distributor_inlet_gate.py ; git diff --cached --name-only
git commit -F - <<'EOF'
fix(distributor): do not start a cycle while the inlet reports open

A cycle claimed while a foreign run held the inlet open watered over it:
opening an inlet that is already open makes no edge, so the ring does not
index, the leg is credited to the next member, and the stored position ends
one ahead while it still reads synced. The claim now refuses while the
inlet reports on, open, opening or closing, in every watch mode and both
watering modes. Nothing else refuses; without an inlet entity nothing
changes.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

## Task 3: A refused cycle is visible — log, notification, history

**Files:**
- Modify: `custom_components/irrigation_plus/const.py` (after `SKIP_REASON_DAYS_BETWEEN`,
  `:189`)
- Modify: `custom_components/irrigation_plus/distributor.py` (a new method after
  `_dist_inlet_reports_open`; the gate in the claim)
- Modify: the eight files in `custom_components/irrigation_plus/frontend/localize/languages/`
- Rebuild: `frontend/dist/irrigation-plus.js`, `frontend/dist/irrigation-plus-card-impl.js`
- Test: `tests/test_distributor_inlet_gate.py`

- [x] **Step 1: Write the failing tests**

Append to `tests/test_distributor_inlet_gate.py` (add `import logging` to the imports).
**Addendum A2:** `_NOTICE` on one line, as `black` writes it.

```python
_NOTICE = (
    "Distributor 'Garten' did not start a watering cycle: its inlet switch.inlet was open."
)


async def test_a_refusal_is_logged_and_notified(caplog):
    c = _gate_host(inlet_state="on")

    with caplog.at_level(logging.WARNING):
        await c.async_run_distributor_cycle(_gated_cfg())

    assert (
        "Distributor 'Garten' did not start a cycle: inlet switch.inlet is on"
        in caplog.text
    )
    c.hass.services.async_call.assert_any_await(
        "persistent_notification",
        "create",
        {
            "title": "Irrigation Plus",
            "message": _NOTICE,
            "notification_id": f"{const.DOMAIN}_distributor_0",
        },
    )


async def test_a_refusal_is_forwarded_to_the_notify_target():
    c = _gate_host(inlet_state="on")

    await c.async_run_distributor_cycle(_gated_cfg(notify_target="notify.phone"))

    c.hass.services.async_call.assert_any_await("notify", "phone", {"message": _NOTICE})


async def test_a_refusal_records_every_member_as_an_explicit_list():
    c = _gate_host(inlet_state="on")

    await c.async_run_distributor_cycle(_gated_cfg())

    c._record_skipped_run.assert_awaited_once_with(
        [1, 2, 3], const.SKIP_REASON_INLET_OPEN, trigger="schedule"
    )


async def test_a_refusal_records_only_the_targeted_members():
    # The dispatcher hands the claim the schedule's whole target, direct zones
    # included: zone 9 is not a member and must get no entry.
    c = _gate_host(inlet_state="on")

    await c.async_run_distributor_cycle(_gated_cfg(), only_zone_ids=[2, 9])

    c._record_skipped_run.assert_awaited_once_with(
        [2], const.SKIP_REASON_INLET_OPEN, trigger="schedule"
    )


async def test_a_refusal_records_nothing_when_no_member_was_targeted():
    c = _gate_host(inlet_state="on")

    await c.async_run_distributor_cycle(_gated_cfg(), only_zone_ids=[9])

    c._record_skipped_run.assert_not_awaited()


async def test_a_refused_test_run_records_no_history():
    c = _gate_host(inlet_state="on")

    assert await c.async_run_distributor_cycle(_gated_cfg(), test_run=True) is False

    c._record_skipped_run.assert_not_awaited()
    c.hass.services.async_call.assert_awaited_once()  # the notification still goes out


async def test_a_refused_forced_member_run_is_recorded_as_manual():
    c = _gate_host(inlet_state="on")

    await c.async_run_distributor_cycle(
        _gated_cfg(), only_zone_ids=[2], force_water=True
    )

    c._record_skipped_run.assert_awaited_once_with(
        [2], const.SKIP_REASON_INLET_OPEN, trigger="manual"
    )


async def test_a_distributor_in_flight_is_not_reported_as_an_open_inlet(caplog):
    # The integration's own sweep holds the inlet open: the in-flight guard must
    # answer first, with no notification and no history entry.
    c = _gate_host(inlet_state="on")
    c._dist_inflight_ids().add(0)

    with caplog.at_level(logging.WARNING):
        assert await c.async_run_distributor_cycle(_gated_cfg()) is False

    c.hass.services.async_call.assert_not_awaited()
    c._record_skipped_run.assert_not_awaited()
    assert "did not start a cycle" not in caplog.text
```

- [x] **Step 2: Run them to verify they fail**

Same command as Task 2 Step 2. Expected: six FAIL — the log, the notification and the
history entry do not exist yet (`AttributeError` on `const.SKIP_REASON_INLET_OPEN` for the
three that name it). Two pass already: `…records_nothing_when_no_member_was_targeted` and the
in-flight test. They are pins, killed by mutations 17 and 5 in Task 8.

- [x] **Step 3: Add the skip reason**

In `const.py`, directly after `SKIP_REASON_DAYS_BETWEEN = "days_between"`:

```python
# Run-log / skip token recorded for a distributor's members when its cycle is
# refused because the inlet reported open at the claim (#181). Localized in the
# run-log via panels.zones.outlook.checks.inlet_open, like the ids above.
SKIP_REASON_INLET_OPEN = "inlet_open"
```

- [x] **Step 4: Add the refusal path**

In `distributor.py`, directly after `_dist_inlet_reports_open`:

```python
    async def _dist_refuse_inlet_open(
        self,
        distributor: dict,
        state: str,
        *,
        test_run: bool,
        only_zone_ids,
        force_water: bool,
    ) -> None:
        """Make a cycle refused over an open inlet visible: log, notify, record.

        Runs after the claim decided not to take the distributor, so it may await.
        The notification reuses the halt's per-distributor id, so a repeat replaces
        it. Its wording stays neutral about who opened the inlet: it can also be
        the late off report of the integration's own self-closing run.
        The history names exactly the members that did not get their water. The
        dispatcher hands the claim the schedule's whole target, direct zones
        included, so ``only_zone_ids`` is cut down to this distributor's members;
        without it, every member. Always an explicit list:
        ``_record_skipped_run(None, ...)`` means every zone of the installation.
        A test run never waters or credits, so it records nothing.
        siehe test_distributor_inlet_gate.py::test_a_refusal_records_only_the_targeted_members
        """
        name = distributor.get("name")
        entity_id = distributor.get("inlet_entity")
        _LOGGER.warning(
            "Distributor '%s' did not start a cycle: inlet %s is %s",
            name,
            entity_id,
            state,
        )
        # Filled by replace(), like the halt message, so a translation can never
        # inject a str.format field.
        template = await localize(
            "panels.distributors.notify.inlet_open", self.hass.config.language
        )
        message = template.replace("{name}", str(name)).replace(
            "{entity}", str(entity_id)
        )
        await self._dist_notify(distributor, message)
        if test_run:
            return
        members = [
            int(m.get(const.ZONE_ID))
            for m in await self._dist_members(distributor.get("id"))
        ]
        if only_zone_ids is not None:
            wanted = {int(z) for z in only_zone_ids}
            members = [zid for zid in members if zid in wanted]
        if not members:
            return
        await self._record_skipped_run(
            members,
            const.SKIP_REASON_INLET_OPEN,
            trigger="manual" if force_water else "schedule",
        )
```

- [x] **Step 5: Call it from the claim**

Replace the two lines Task 2 added to the claim,

```python
        if self._dist_inlet_reports_open(distributor) is not None:
            return False
```

with

```python
        blocking = self._dist_inlet_reports_open(distributor)
        if blocking is not None:
            await self._dist_refuse_inlet_open(
                distributor,
                blocking,
                test_run=test_run,
                only_zone_ids=only_zone_ids,
                force_water=force_water,
            )
            return False
```

and extend the comment above them by one line:
`# The refusal awaits only after this decision, holding nothing.`

- [x] **Step 6: Run the tests — the notification test still fails**

Expected: everything passes except `test_a_refusal_is_logged_and_notified` and
`test_a_refusal_is_forwarded_to_the_notify_target`: `localize` does not find the key yet and
hands back `panels.distributors.notify.inlet_open` itself.

- [x] **Step 7: Add both keys in all eight languages**

Write `D:\Entwicklung\HASI\issue66-work\add_keys.py`:

```python
"""Insert the two inlet-open keys into all eight panel catalogues, order and format kept.

The files are LF in the repository and CRLF in this working copy (core.autocrlf).
json.dumps(indent=2, ensure_ascii=False) + "\\n" reproduces the repository bytes
exactly (checked on 0b9a71bd), so writing LF is a pure two-line addition to git.
"""

import json
import sys
from pathlib import Path

WT = Path(sys.argv[1] if len(sys.argv) > 1 else r"D:\Entwicklung\HASI\issue66-work\wt")
LANGS = WT / "custom_components" / "irrigation_plus" / "frontend" / "localize" / "languages"

NOTIFY = {
    "en": "Distributor '{name}' did not start a watering cycle: its inlet {entity} was open.",
    "de": "Verteiler '{name}' hat einen Bewässerungszyklus nicht gestartet: sein Einlass {entity} war offen.",
    "es": "Distribuidor '{name}' no inició un ciclo de riego: su entrada {entity} estaba abierta.",
    "fr": "Distributeur '{name}' n'a pas démarré de cycle d'arrosage : son entrée {entity} était ouverte.",
    "it": "Distributore '{name}' non ha avviato un ciclo di irrigazione: il suo ingresso {entity} era aperto.",
    "nl": "Verdeler '{name}' heeft geen beregeningscyclus gestart: de inlaat {entity} stond open.",
    "no": "Fordeler '{name}' startet ikke en vanningssyklus: innløpet {entity} var åpent.",
    "sk": "Rozvádzač '{name}' nespustil zavlažovací cyklus: jeho vstupný ventil {entity} bol otvorený.",
}
CHECK = {
    "en": "Distributor inlet open",
    "de": "Verteiler-Einlass offen",
    "es": "Entrada del distribuidor abierta",
    "fr": "Entrée du distributeur ouverte",
    "it": "Ingresso del distributore aperto",
    "nl": "Inlaat van de verdeler open",
    "no": "Fordelerens innløp åpent",
    "sk": "Vstupný ventil rozvádzača otvorený",
}


def insert_after(block: dict, anchor: str, key: str, value: str) -> None:
    if key in block:
        raise SystemExit(f"{key} already present")
    items = list(block.items())
    index = [k for k, _ in items].index(anchor) + 1
    items.insert(index, (key, value))
    block.clear()
    block.update(items)


for lang in NOTIFY:
    path = LANGS / f"{lang}.json"
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    data = json.loads(raw)
    if (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8") != raw:
        raise SystemExit(f"{lang}: the file does not round-trip; stop and look")
    insert_after(data["panels"]["distributors"]["notify"], "halted", "inlet_open", NOTIFY[lang])
    insert_after(data["panels"]["zones"]["outlook"]["checks"], "no_demand", "inlet_open", CHECK[lang])
    path.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(lang, "ok")
```

Run it and check the diff is exactly two added lines per file:

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe /d/Entwicklung/HASI/issue66-work/add_keys.py ; git diff --numstat -- custom_components/irrigation_plus/frontend/localize/languages/
```

Expected: eight lines `2	0	…/<lang>.json`. Anything else: `git checkout -- <file>` and
read why. **Addendum A3: measured `3	1` per file, and that is right** (the comma after
`no_demand`, the last key of `checks`).

- [x] **Step 8: Run the tests and the catalogue checks**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_distributor_inlet_gate.py tests/test_i18n_completeness.py -p _local_socket_unblock -q --no-header
```

Expected: all pass. `test_i18n_completeness.py` checks the keys in both directions, the
named placeholders (`{name}`, `{entity}`) and that no language kept the English text.

- [x] **Step 9: Rebuild the panel and stage the two bundles**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt/custom_components/irrigation_plus/frontend && npm run build > /d/Entwicklung/HASI/issue66-work/build.log 2>&1 ; echo "build exit=$?" ; cd /d/Entwicklung/HASI/issue66-work/wt && git update-index --refresh > /dev/null 2>&1 ; for f in custom_components/irrigation_plus/frontend/dist/*.js; do git diff --quiet -- "$f" && echo "unchanged $f" || echo "CHANGED   $f"; done
```

Expected: `build exit=0`; `CHANGED` exactly for `irrigation-plus.js` and
`irrigation-plus-card-impl.js` (the two that embed `en.json`); the two card stubs unchanged.

- [x] **Step 10: Lint, then commit**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && uvx black custom_components/irrigation_plus/ tests/test_distributor_inlet_gate.py ; uvx ruff check custom_components/irrigation_plus/ tests/test_distributor_inlet_gate.py ; git add custom_components/irrigation_plus/const.py custom_components/irrigation_plus/distributor.py custom_components/irrigation_plus/frontend/localize/languages/ tests/test_distributor_inlet_gate.py ; git add -f custom_components/irrigation_plus/frontend/dist/irrigation-plus.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-impl.js ; git diff --cached --name-only | wc -l
```

Expected: `13` (const, distributor, eight catalogues, the test file, two bundles). Then:

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && git commit -F - <<'EOF'
feat(distributor): say so when a cycle is refused over an open inlet

A refused cycle used to be silent. It now logs a warning, raises the
distributor's notification (the halt's id, so a repeat replaces it, and
the notify target when one is set) and records a skipped run with the new
reason inlet_open for exactly the members the cycle was for: the
dispatcher passes the schedule's whole target, so it is cut down to this
distributor's members and always passed as a list. A test run records
nothing; a forced member run is recorded as manual. Both texts in all
eight languages.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

## Task 4: The integration's own close does not refuse the next cycle

**Files:**
- Modify: `custom_components/irrigation_plus/const.py` (after `DISTRIBUTOR_INLET_OPEN_STATES`)
- Modify: `custom_components/irrigation_plus/distributor.py` (`_dist_close_inlet`, `:132-143`;
  a new method after `_dist_inflight_ids`; `_dist_inlet_reports_open`)
- Test: `tests/test_distributor_inlet_gate.py`

- [x] **Step 1: Write the failing tests**

Append to `tests/test_distributor_inlet_gate.py`:

```python
def _grace_host():
    """A gate host with the REAL _dist_close_inlet (which stamps the close).

    _loop_host stubs _dist_close_inlet as an instance attribute; deleting it
    restores the method. The actuation underneath is stubbed instead, so the
    classic close sends nothing real. The clock starts at 1000.0.
    """
    c = _gate_host(inlet_state="on", now=1000.0)
    del c._dist_close_inlet
    c._dist_domain_turn = AsyncMock()
    return c


async def test_the_next_cycle_runs_within_the_grace_after_our_own_close():
    c = _grace_host()
    cfg = _gated_cfg()
    await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1029.0  # the inlet still reports on
    assert await c.async_run_distributor_cycle(cfg) is True

    c._dist_domain_turn.assert_awaited_once_with("switch.inlet", False)


async def test_the_grace_runs_out_after_thirty_seconds():
    c = _grace_host()
    cfg = _gated_cfg()
    await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1031.0
    assert await c.async_run_distributor_cycle(cfg) is False


async def test_a_stop_service_close_starts_the_grace():
    c = _grace_host()
    cfg = _gated_cfg(
        watering_mode=const.WATERING_MODE_SERVICE, stop_service="script.dist_stop"
    )
    await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1029.0
    assert await c.async_run_distributor_cycle(cfg) is True

    c.hass.services.async_call.assert_any_await(
        "script", "dist_stop", {"distributor_id": 0}
    )


async def test_a_service_distributor_without_stop_service_gets_no_grace():
    # Nothing is sent, so nothing proves the valve closed: a start over a
    # still-open self-closing valve is the defect the gate exists for.
    c = _grace_host()
    cfg = _gated_cfg(watering_mode=const.WATERING_MODE_SERVICE, stop_service=None)
    await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1001.0
    assert await c.async_run_distributor_cycle(cfg) is False


async def test_the_grace_belongs_to_the_distributor_that_closed():
    c = _grace_host()
    await c._dist_close_inlet(_gated_cfg(id=0))

    c.hass.loop.time.return_value = 1001.0
    assert await c.async_run_distributor_cycle(_gated_cfg(id=1)) is False


async def test_a_close_that_raised_starts_no_grace():
    c = _grace_host()
    c._dist_domain_turn = AsyncMock(side_effect=RuntimeError("inlet unreachable"))
    cfg = _gated_cfg()
    with pytest.raises(RuntimeError):
        await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1001.0
    assert await c.async_run_distributor_cycle(cfg) is False
```

- [x] **Step 2: Run them to verify they fail**

Same command as Task 2 Step 2. Expected: `test_the_next_cycle_runs_within_the_grace…` and
`test_a_stop_service_close_starts_the_grace` FAIL with `assert False is True`; the four
others pass already (they are the grace's boundaries, killed by mutations 7–10 in Task 8).

- [x] **Step 3: Add the constant**

In `const.py`, directly after `DISTRIBUTOR_INLET_OPEN_STATES = …`:

```python
# ...except within this many seconds of the integration's own close command for
# that inlet (#181): a slow or cloud-polled valve keeps reporting open for a while
# after it was told to close. The same patience VALVE_CONFIRM_TIMEOUT gives a valve
# to report open.
DISTRIBUTOR_INLET_CLOSE_GRACE_SECONDS = VALVE_CONFIRM_TIMEOUT
```

- [x] **Step 4: Keep the stamps**

> **Addendum A4 replaces the code of Steps 4 and 5:** a helper `_dist_stamp_own_close` does the
> stamping, and the `_dist_own_close_times` docstring is corrected.

In `distributor.py`, directly after `_dist_inflight_ids`:

```python
    def _dist_own_close_times(self) -> dict:
        """{distributor_id: loop time} of the integration's own last inlet close.

        Read by the inlet gate's grace (#181). In memory only, like the in-flight
        set: a restart forgets it, and after a restart the resume path closes the
        inlet and marks the ring uncertain anyway. Lazily created so no coordinator
        __init__ change is needed."""
        times = getattr(self, "_dist_own_close", None)
        if times is None:
            times = self._dist_own_close = {}
        return times
```

- [x] **Step 5: Stamp a sent close**

Replace `_dist_close_inlet` with:

```python
    async def _dist_close_inlet(self, distributor: dict) -> None:
        """Close the inlet. classic: domain-aware close. service: fire stop_service
        if configured, else rely on the hardware self-close (no-op).

        A close that was sent is stamped for the inlet gate's grace (#181): a slow
        or cloud-polled inlet keeps reporting open for a while after it was told to
        close, and the next cycle must not be refused for our own close. Stamped
        once the command returned -- a close that raised proves nothing -- and never
        for the service no-op: without a command nothing shows the valve closed.
        NOT-TO-DO: do not stamp before the await, and do not stamp the service
          branch without stop_service.
        siehe test_distributor_inlet_gate.py::test_a_service_distributor_without_stop_service_gets_no_grace
        """
        if distributor.get("watering_mode") == const.WATERING_MODE_SERVICE:
            stop = distributor.get("stop_service")
            if stop:
                domain, service = self._dist_split_service(stop)
                data = {}
                data["distributor_id"] = distributor.get("id")
                await self.hass.services.async_call(domain, service, data)
                self._dist_own_close_times()[distributor.get("id")] = (
                    self.hass.loop.time()
                )
            return
        await self._dist_domain_turn(distributor.get("inlet_entity"), False)
        self._dist_own_close_times()[distributor.get("id")] = self.hass.loop.time()
```

- [x] **Step 6: Honour the grace in the check**

In `_dist_inlet_reports_open`, replace the last line, `return state.state`, with:

```python
        # The state is read first, so the clock is consulted only for an open
        # report; a close stamped less than the grace ago is our own, still being
        # reported.
        closed_at = self._dist_own_close_times().get(distributor.get("id"))
        if (
            closed_at is not None
            and self.hass.loop.time() - closed_at
            < const.DISTRIBUTOR_INLET_CLOSE_GRACE_SECONDS
        ):
            return None
        return state.state
```

and add one paragraph to its docstring, before `Synchronous on purpose`:

```
        Grace: not within DISTRIBUTOR_INLET_CLOSE_GRACE_SECONDS of the integration's
          own close for this distributor (_dist_close_inlet stamps it). A foreign
          open inside that window goes unseen, a trade accepted on #181.
```

- [x] **Step 7: Run the tests to verify they pass**

Same command as Task 2 Step 2. Expected: all pass.

- [x] **Step 8: Run the distributor suites for regressions**

Same command as Task 2 Step 7. Expected: no failure outside `baseline-names.txt`. The real
`_dist_close_inlet` now reads `hass.loop.time()`; on a `Mock` host that returns a `Mock`,
which is stored and only ever compared after an open report — which a `Mock` state never
is.

- [x] **Step 9: Lint, then commit**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && uvx black custom_components/irrigation_plus/ tests/test_distributor_inlet_gate.py ; uvx ruff check custom_components/irrigation_plus/ tests/test_distributor_inlet_gate.py ; git add custom_components/irrigation_plus/const.py custom_components/irrigation_plus/distributor.py tests/test_distributor_inlet_gate.py ; git diff --cached --name-only
git commit -F - <<'EOF'
fix(distributor): our own close does not refuse the next cycle

_dist_close_inlet sends the close and does not wait for the inlet to
report closed, so a slow or cloud-polled inlet kept reading on or closing
after our own close and refused a cycle started right after it, although
nothing foreign had happened. A close command that was actually sent is
now stamped, and the gate ignores an open report for 30 s after it
(VALVE_CONFIRM_TIMEOUT, the patience a valve already gets to report open).
Service mode without a stop service sends nothing and gets no grace; a
close that raised starts none either.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

## Task 5: Every entry meets the gate; the finish-anchor estimate does not

Every sweep entry reaches the claim, but no existing test shows it: the tests of the
dispatcher, *Irrigate now*, the member run and `distributor_run_now` all mock the claim, and
only the test run reaches the real one (read on `0b9a71bd`). These pins drive each entry
through the **real** dispatcher and claim on the full distributor host, with only the sweep,
the history writer and the store's reads stubbed. They pass once Tasks 2–4 are in; mutation 2
(the gate never consulted) and mutation 18 (the eligibility predicate asks the inlet, the
place that was rejected) in Task 8 are what show they are load-bearing.

**Files:**
- Test: `tests/test_distributor_inlet_gate.py`

- [x] **Step 1: Write the pins**

Add to the imports:

```python
from tests.test_distributor import _dist, _host
from tests.test_distributor_integration import _call
```

Append:

```python
_MEMBER = {
    "id": 7,
    "distributor_id": 0,
    "outlet_number": 1,
    "duration": 30,
    "bucket": -1,
    "bucket_threshold": 0,
    "state": "automatic",
}


def _entry_host(inlet_state="on"):
    """The full distributor host with the REAL dispatcher and claim.

    Distributor 0 (``_dist``: classic, inlet ``switch.inlet``, synced, confirmed) has
    one due member, zone 7. Only the sweep, the history writer and the store's reads
    are stubbed, so a call through any entry meets the gate as it would in the
    coordinator.
    """
    c = _host()
    c.hass.config.language = "en"
    c.hass.states.get = Mock(return_value=SimpleNamespace(state=inlet_state))
    c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_SEQUENTIAL
    c._master_off_deadline = None
    c._rain_delay_active = Mock(return_value=False)
    c._sc_is_self_closing = Mock(return_value=False)
    c.store.async_get_zones = AsyncMock(return_value=[dict(_MEMBER)])
    c.store.get_zone = Mock(return_value=dict(_MEMBER))
    c.store.async_get_distributors = AsyncMock(return_value=[_dist(id=0)])
    c.store.get_distributor = Mock(return_value=_dist(id=0, active_cycle=None))
    c._dist_members = AsyncMock(return_value=[dict(_MEMBER)])
    c._dist_needs_water = Mock(return_value=True)
    c._dist_run_sweep = AsyncMock(return_value=True)
    c._record_skipped_run = AsyncMock()
    return c


def _assert_refused(c, trigger="schedule"):
    c._dist_run_sweep.assert_not_awaited()
    assert 0 not in c._dist_inflight_ids()
    c._record_skipped_run.assert_awaited_once_with(
        [7], const.SKIP_REASON_INLET_OPEN, trigger=trigger
    )


async def test_a_scheduled_dispatch_meets_the_gate():
    c = _entry_host()

    assert await c._dispatch_distributor_cycles("all") is False

    _assert_refused(c)


async def test_water_all_zones_meets_the_gate():
    c = _entry_host()

    await c.async_irrigate_now()

    _assert_refused(c)


async def test_irrigate_now_on_a_member_meets_the_gate():
    c = _entry_host()

    await c.async_irrigate_now("7")

    _assert_refused(c)


async def test_a_member_run_with_a_duration_meets_the_gate():
    # A forced run bypasses the rain delay and the demand gate, but not this one.
    c = _entry_host()

    await c.async_run_zone(7, 2)

    _assert_refused(c, trigger="manual")


async def test_distributor_run_now_meets_the_gate():
    c = _entry_host()

    await c.handle_distributor_run_now(_call(**{const.ATTR_DISTRIBUTOR_ID: 0}))

    _assert_refused(c)


async def test_the_test_run_meets_the_gate():
    c = _entry_host()

    assert await c.async_run_distributor_test(_dist(id=0)) is False

    c._dist_run_sweep.assert_not_awaited()
    c._record_skipped_run.assert_not_awaited()


async def test_the_finish_anchor_estimate_does_not_read_the_inlet():
    c = _entry_host(inlet_state="off")
    closed = await c.get_total_irrigation_duration("all")

    c.hass.states.get = Mock(return_value=SimpleNamespace(state="on"))
    opened = await c.get_total_irrigation_duration("all")

    assert closed > 0
    assert opened == closed
```

- [x] **Step 2: Run them**

Same command as Task 2 Step 2. Expected: all pass. A failure here is not a RED to fix in
production code: it means a host stub is missing for that entry (the entry's own guards,
e.g. the member run's `active_cycle` check at `irrigation.py:3438-3445`). Read the traceback,
fix the host, never the gate.

- [x] **Step 3: Lint, then commit**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && uvx black custom_components/irrigation_plus/ tests/test_distributor_inlet_gate.py ; uvx ruff check custom_components/irrigation_plus/ tests/test_distributor_inlet_gate.py ; git add tests/test_distributor_inlet_gate.py ; git diff --cached --name-only
git commit -F - <<'EOF'
test(distributor): every entry meets the inlet gate; the estimate does not

The schedule, water all zones, irrigate now, the member run with a
duration, distributor_run_now and the test run each reach the real
dispatcher and claim here and are refused while the inlet reports open.
The finish-anchor estimate returns the same with the inlet open and closed.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

> **Addendum A10:** after Task 5's commit, Task 5b adds one more pin in a commit of its own.

---

## Task 6: Documentation

**Files:**
- Modify: `docs/configuration-distributors.md`, section *Watching the inlet for foreign
  pulses* (`:69-79` on `0b9a71bd`)

- [x] **Step 1: Add the paragraph**

After the section's last paragraph (the one ending "which is exactly why **Set current
outlet** exists."), add (**Addendum A5:** as one line, like every paragraph of that file):

```markdown
Independently of the watch mode, a watering cycle **never starts while the inlet reports open**
(`on`, `open`, `opening` or `closing`), provided an inlet entity is set. The refused cycle
appears in the members' history as *Distributor inlet open* and as a notification. For 30
seconds after Irrigation Plus closed the inlet itself, an inlet that still reports open does
not block the next cycle, so a slow or cloud-polled valve does not refuse it; in self-closing
mode this needs a stop script. Re-sync only while the inlet is closed. A self-closing
distributor without an inlet entity has no such protection.
```

- [x] **Step 2: Commit**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && git add docs/configuration-distributors.md ; git commit -F - <<'EOF'
docs(distributor): a cycle does not start over an open inlet

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

## Task 7: Gates

- [x] **Step 1: Full backend suite**

Run in the background (tool option), read the file only after the run has ended:

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && export TEMP=D:/Entwicklung/HASI/issue66-work/tmp TMP=D:/Entwicklung/HASI/issue66-work/tmp TMPDIR=D:/Entwicklung/HASI/issue66-work/tmp ; TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header > /d/Entwicklung/HASI/issue66-work/measure/branch-full-tzutc.txt 2>&1 ; tail -1 /d/Entwicklung/HASI/issue66-work/measure/branch-full-tzutc.txt
```

Expected: the baseline's passed count plus the number of tests collected from
`tests/test_distributor_inlet_gate.py` (count them with `--co -q`), the same failed and
error counts.

- [x] **Step 2: Diff the failure names against the baseline**

```bash
cd /d/Entwicklung/HASI/issue66-work/measure && grep -E "^(FAILED|ERROR) tests/" branch-full-tzutc.txt | sed 's/ - .*//' | sort -u > branch-names.txt ; diff baseline-names.txt branch-names.txt && echo "NAMENS-DIFF LEER" ; wc -l baseline-names.txt branch-names.txt
```

Expected: `NAMENS-DIFF LEER`. A non-empty diff is a regression; read it before touching
anything.

- [x] **Step 3: The committed dist equals a fresh build**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt/custom_components/irrigation_plus/frontend && npm run build > /d/Entwicklung/HASI/issue66-work/build-gate.log 2>&1 ; echo "build exit=$?" ; cd /d/Entwicklung/HASI/issue66-work/wt && git update-index --refresh > /dev/null 2>&1 ; git diff --quiet -- custom_components/irrigation_plus/frontend/dist/ && echo "committed dist == fresh build"
```

- [x] **Step 4: Lint**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && uvx black --check custom_components/irrigation_plus/ tests/test_distributor_inlet_gate.py ; uvx ruff check custom_components/irrigation_plus/ tests/test_distributor_inlet_gate.py
```

- [x] **Step 5: The reference checks, on the added lines and the messages**

> **Addendum A6:** the third grep below is not empty on the base (upstream's own reporter
> credits); use `git grep -n "Eifel-Joe#" HEAD -- custom_components tests docs` instead.

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && git diff upstream/master...HEAD -U0 -- custom_components tests docs | grep '^+' | grep -nEi "eifel-joe|issue ?#66|#66\b|\bR6\b|\bH2\b|\bL5\b|spec\b|task [0-9]" ; git log upstream/master..HEAD --format=%B | grep -nEi "eifel-joe|#66\b|\bR6\b|spec\b|task [0-9]" ; grep -rn "Eifel-Joe" custom_components/ tests/ docs/ ; echo "--- alle drei ohne Ausgabe = sauber"
```

- [x] **Step 6: Commit any formatting churn**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && git status --short ; git diff --quiet || { git add custom_components/irrigation_plus tests && git commit -m "style: black" ; }
```

Read the `git status` list first: the card bundles may show as `M` (autocrlf). Those are not
churn; `git diff --quiet` ignores them.

---

## Task 8: Mutation matrix

Every decision this branch makes has a test that dies without it. Several tests in this plan
pass before their code exists (the pass-through cases, the in-flight order, the grace's
boundaries, the entry and estimate pins); the matrix is what proves they are load-bearing.

**Files:**
- Create: `D:\Entwicklung\HASI\issue66-work\mutate.py` (outside the repository)

- [x] **Step 1: Write the runner**

> **Addendum A7:** use the runner measured in the dry run (three guards added, among them a
> timeout; anchors 9, 11, 13, 14 follow A4): copy `issue66-work\probe\mutate.py` and
> `…\probe\mut5_rerun.py` to `issue66-work\`.

Copy the engine of `D:\Entwicklung\HASI\issue5-work\mutate.py` — `read_src`, `write_src`,
`run_pytest`, `main` — unchanged, drop `run_vitest` and the `VITEST_FILES` list, make
`run_all()` return `run_pytest()` alone, and replace everything above `MUTATIONS` and the
`MUTATIONS` list itself with:

```python
"""Apply each mutation, run the pytest files, record, revert (inlet gate branch).

Engine unchanged from issue5-work/mutate.py (archived as
docs/superpowers/probes/2026-09-29-zone-save-mutations.py); pytest only, because
this branch changes no TypeScript.

Run:
    python D:/Entwicklung/HASI/issue66-work/mutate.py [worktree]
"""

import io
import json
import os
import subprocess
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else r"D:\Entwicklung\HASI\issue66-work\wt"
PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
TMP = r"D:\Entwicklung\HASI\issue66-work\tmp"
OUT = r"D:\Entwicklung\HASI\issue66-work\mutations.json"

IP = os.path.join(WT, "custom_components", "irrigation_plus")
DIST = os.path.join(IP, "distributor.py")
CONST = os.path.join(IP, "const.py")

# Every test named as a killer below lives in one of these.
SUITES = [
    "tests/test_distributor_inlet_gate.py",
    "tests/test_distributor.py",
    "tests/test_distributor_cycle.py",
    "tests/test_distributor_dispatch.py",
    "tests/test_distributor_integration.py",
]

MUTATIONS = [
    (1, CONST, "closing no longer blocks",
     '{"on", "open", "opening", "closing"}', '{"on", "open", "opening"}',
     "test_the_claim_refuses_while_the_inlet_reports_open[closing]"),
    (2, DIST, "the gate is never consulted",
     "        blocking = self._dist_inlet_reports_open(distributor)\n",
     "        blocking = None\n",
     "every refusal test"),
    (3, DIST, "a missing entity blocks",
     "        if state is None or state.state not in const.DISTRIBUTOR_INLET_OPEN_STATES:\n",
     "        if state is not None and state.state not in const.DISTRIBUTOR_INLET_OPEN_STATES:\n",
     "test_the_claim_lets_a_cycle_through_when_the_inlet_entity_does_not_exist"),
    (4, DIST, "the claim is taken before the gate",
     "        blocking = self._dist_inlet_reports_open(distributor)\n",
     "        inflight.add(dist_id)\n"
     "        blocking = self._dist_inlet_reports_open(distributor)\n",
     "test_the_claim_refuses_while_the_inlet_reports_open (id left in flight)"),
    (5, DIST, "no in-flight guard: the gate answers for our own sweep",
     "        if dist_id in inflight:\n            return False\n",
     "",
     "test_a_distributor_in_flight_is_not_reported_as_an_open_inlet"),
    (6, DIST, "the history uses the whole target, direct zones included",
     "            members = [zid for zid in members if zid in wanted]\n",
     "            members = sorted(wanted)\n",
     "test_a_refusal_records_only_the_targeted_members"),
    (7, DIST, "a test run records history",
     "        if test_run:\n            return\n        members = [",
     "        members = [",
     "test_a_refused_test_run_records_no_history"),
    (8, DIST, "the grace never ends",
     "            < const.DISTRIBUTOR_INLET_CLOSE_GRACE_SECONDS\n",
     "            < float(\"inf\")\n",
     "test_the_grace_runs_out_after_thirty_seconds"),
    (9, DIST, "the service no-op stamps too",
     "                self._dist_own_close_times()[distributor.get(\"id\")] = (\n"
     "                    self.hass.loop.time()\n"
     "                )\n"
     "            return\n",
     "            self._dist_own_close_times()[distributor.get(\"id\")] = (\n"
     "                self.hass.loop.time()\n"
     "            )\n"
     "            return\n",
     "test_a_service_distributor_without_stop_service_gets_no_grace"),
    (10, DIST, "the grace is shared by every distributor",
     "        closed_at = self._dist_own_close_times().get(distributor.get(\"id\"))\n",
     "        closed_at = max(self._dist_own_close_times().values(), default=None)\n",
     "test_the_grace_belongs_to_the_distributor_that_closed"),
    (11, DIST, "the classic close is stamped before it is sent",
     "        await self._dist_domain_turn(distributor.get(\"inlet_entity\"), False)\n"
     "        self._dist_own_close_times()[distributor.get(\"id\")] = self.hass.loop.time()\n",
     "        self._dist_own_close_times()[distributor.get(\"id\")] = self.hass.loop.time()\n"
     "        await self._dist_domain_turn(distributor.get(\"inlet_entity\"), False)\n",
     "test_a_close_that_raised_starts_no_grace"),
    (12, DIST, "a forced member run recorded as schedule",
     'trigger="manual" if force_water else "schedule"',
     'trigger="schedule"',
     "test_a_refused_forced_member_run_is_recorded_as_manual"),
    (13, DIST, "the classic close is never stamped",
     "        await self._dist_domain_turn(distributor.get(\"inlet_entity\"), False)\n"
     "        self._dist_own_close_times()[distributor.get(\"id\")] = self.hass.loop.time()\n",
     "        await self._dist_domain_turn(distributor.get(\"inlet_entity\"), False)\n",
     "test_the_next_cycle_runs_within_the_grace_after_our_own_close"),
    (14, DIST, "the stop_service close is never stamped",
     "                await self.hass.services.async_call(domain, service, data)\n"
     "                self._dist_own_close_times()[distributor.get(\"id\")] = (\n"
     "                    self.hass.loop.time()\n"
     "                )\n",
     "                await self.hass.services.async_call(domain, service, data)\n",
     "test_a_stop_service_close_starts_the_grace"),
    (15, DIST, "an empty inlet entity is looked up",
     "        if not entity_id:\n            return None\n        state = ",
     "        state = ",
     "test_the_claim_lets_a_cycle_through_without_an_inlet_entity"),
    (16, DIST, "the refusal sends no notification",
     "        await self._dist_notify(distributor, message)\n        if test_run:",
     "        if test_run:",
     "test_a_refusal_is_logged_and_notified, test_a_refused_test_run_records_no_history"),
    (17, DIST, "an empty member list is still recorded",
     "        if not members:\n            return\n        await self._record_skipped_run(",
     "        await self._record_skipped_run(",
     "test_a_refusal_records_nothing_when_no_member_was_targeted"),
    (18, DIST, "the eligibility predicate asks the inlet too (the rejected place)",
     "        if not members:\n            return False\n        if not require_due:",
     "        if not members:\n            return False\n"
     "        if self._dist_inlet_reports_open(distributor) is not None:\n"
     "            return False\n"
     "        if not require_due:",
     "the estimate pin of Task 5"),
]
```

Every anchor must appear exactly once on the branch; the runner skips and reports any that
does not. If `black` reformatted an anchored line, adapt the anchor, not the code.

- [x] **Step 2: Run it**

> **Addendum A7:** the command, the re-run of mutation 5 and the expected output as measured
> are in A7; they replace the block below.

```bash
cd /d/Entwicklung/HASI/issue66-work && sha256sum wt/custom_components/irrigation_plus/distributor.py wt/custom_components/irrigation_plus/const.py > pre-mutation.sha ; /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe mutate.py /d/Entwicklung/HASI/issue66-work/wt 2>&1 | tail -40 ; sha256sum -c pre-mutation.sha
```

Expected: `every source restored byte-for-byte: True`, `18 killed / 18 applied / 18 total`,
two `OK` from `sha256sum -c`. Check each row's `summary` in `issue66-work\mutations.json`:
pytest must have collected. A run that collected nothing kills nothing and survives
everything.

- [x] **Step 3: Read every survivor as a weak test first**

Either add the assertion that kills it, or record the measurement that shows the mutated code
behaves identically. An argument is not a measurement.

---

## Task 9: Review

- [x] **Step 1:** `superpowers:requesting-code-review` on `git diff upstream/master...HEAD`,
  with this plan and the design doc. The reviewer checks: every requirement R1–R6 of the
  design has a change and a test; nothing outside the listed files moved; the comments follow
  `code-doku` (Wurzel, Fix, NOT-TO-DO, siehe); no tracker reference slipped in.
- [x] **Step 2:** Every finding goes through `superpowers:receiving-code-review`, verified
  before it is acted on. A change re-runs Task 7 and, if it touches a mutated line, Task 8.

---

## Task 10: Live test on HA-Test

HA-Test is `192.168.10.196`, tools `mcp__HA-Test__…`. Name the instance before every write.
**HA-Prod is not touched.** A HA-Test restart is allowed, but announce it first (memory
`ha-no-auto-restart`). Never print the integration entry's options: they carry the weather
API key. Read zone state through the panel's websocket in the browser pane
(`await document.querySelector("home-assistant").hass.callWS({type: "irrigation_plus/zones"})`),
not through `ha_get_integration(include_diagnostics=True)`.

The set-up is the one of the measurement record
(`docs/superpowers/reconstructed/2026-09-29-distributor-inlet-open-count-repro.md`): Gardena1
(id 0), service mode, `inlet_entity` = `input_boolean.sonoff_emu_valve`, `watch_mode: count`,
members zones 2–7 = outlets 1–6. **Test4 (zone 5) has a soil-moisture veto** — never a sweep
target. The emulator has no ring: the physical position is the number of the valve's off
edges (recorder), declared with `distributor_set_outlet` at the start. *Irrigate now* exists
only as the websocket `irrigation_plus/irrigate_now` with `zone_id`. The helpers of the
measurement are in `D:\Entwicklung\HASI\issue66-work\` (`hasi_read.py`, `repro_count.py`,
`evaluate_run.py`). Record for every step: the time, the claim's outcome, the notification,
the members' history, the stored position and `position_state`.

- [ ] **Step 1: A throwaway build with the fix** (outward-facing: push and release only after
  approval in the chat)

A branch `prerelease/v2026.09.30b1` (or the day it is built) from the fix branch's HEAD. Bump
the version to `v2026.09.30b1` in `manifest.json` and `const.py` `VERSION` (with `v`), and to
`2026.09.30b1` in `frontend/package.json` (without). Rebuild `dist` with the version baked
in, commit. `production` is not touched. After approval:

```bash
git push -u origin prerelease/v2026.09.30b1
gh release create v2026.09.30b1 --repo Eifel-Joe/HAsmartirrigation --prerelease --target <prerelease-SHA> --title "v2026.09.30b1" --notes "Throwaway build for a live test on a test instance. Not for use."
git archive --format=zip -o irrigation_plus.zip <prerelease-SHA>:custom_components/irrigation_plus
gh release upload v2026.09.30b1 irrigation_plus.zip --repo Eifel-Joe/HAsmartirrigation
```

HACS sees a new fork release only after its repository information is refreshed. Install it
on HA-Test through HACS and restart HA-Test (announced). Verify `installed_version` and the
config entry `loaded`. Reload the panel with Ctrl+F5.

- [ ] **Step 2: L1 `count`** — declare position 4, open the inlet by hand, *Irrigate now* on
  zone 6 (Test5). Expected: no claim (`watering_now`, the master and the run script stay
  off); the notification *Distributor 'Gardena1' did not start a watering cycle: its inlet
  input_boolean.sonoff_emu_valve was open.*; Test5's history shows *skipped — Distributor
  inlet open*. Close the inlet after at least 30 s open. Expected: Test4 (outlet 4) gets the
  observed credit; stored position 5 = model 5, `synced`.
- [ ] **Step 3: L2 `ignore`** — switch the watch mode to *Ignore* in the panel, open the
  inlet, *Irrigate now* on zone 6. Expected: refused, as in L1. Close the inlet; re-sync the
  position (the foreign pulse desynchronises the ring in `ignore`, as documented).
- [ ] **Step 4: L3 no edge** — open the inlet, restart HA-Test (announced), then *Irrigate
  now* on zone 6. Expected: refused. Record what the later close does to the position: that
  is the first measurement for the missed-edge issue (Eifel-Joe#69).
- [ ] **Step 5: L4 no false refusal** — inlet closed, *Irrigate now* on zone 6. Expected: a
  normal cycle with its terminal advance.
- [ ] **Step 6: L5 the grace after our own close** — rewire Gardena1 for this step only:
  `inlet_entity` = `input_boolean.grace_emu_valve`, `run_service` = `script.grace_emu_run`
  (`duration_field` = `seconds`), `input_number.grace_emu_off_delay` = 45, and as
  `stop_service` a do-nothing script created for the test (announce it before creating it on
  HA-Test, e.g. `script.grace_emu_noop` with a single `delay: 0`). The run script then closes
  the valve 45 s after the leg's window, while the integration's close command (the no-op
  stop) has already been sent. Single-member cycles only.
  - **L5a:** *Irrigate now* on one member; within 30 s of its leg's end, *Irrigate now* on
    another member. Expected: the second cycle starts.
  - **L5b:** a fresh run; the second *Irrigate now* 31–44 s after the leg's end, the inlet
    still `on`. Expected: refused, with the notification and the history entry.
- [ ] **Step 7: Restore everything as found** — the L5 wiring (`inlet_entity`,
  `run_service`, `stop_service`, `duration_field`), `grace_emu_off_delay` back to 0, the
  no-op script deleted, the watch mode back to `count`, the position re-synced, the valve and
  the master off. Record the live protocol for the archive:
  `docs/superpowers/reconstructed/2026-09-30-distributor-inlet-open-gate-live-on-ha-test.md`
  with the times, the values and the build SHA.

---

## Task 11: Archive, PR text, PR, issues

- [ ] **Step 1: Archive the design history (rule P1)**

Into `pr139-work/archive-wt`: this plan with its boxes ticked, `mutations.json` as
`docs/superpowers/probes/2026-09-30-distributor-inlet-gate-mutations.json`, the runner as
`docs/superpowers/probes/2026-09-30-distributor-inlet-gate-mutations.py`, and the live
protocol. Commit there; push `archive/design-history` after approval. Then check the feature
branch carries code, tests and the user doc only:

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && git diff upstream/master...HEAD --name-only
```

Expected: only paths under `custom_components/irrigation_plus/`, `tests/` and
`docs/configuration-distributors.md`.

- [ ] **Step 2: The PR body, shown in the chat for approval**

Nothing goes to GitHub without approval in the chat, corrections included. Structure:
`## Problem` / `## Fix` / `## Testing`: the defect as measured (credit to the neighbour,
position one ahead, still synced), the gate and its place (the claim, as agreed on `#181`),
the grace (30 s after our own close, only after a sent command), the feedback (log,
notification, history), the tests, the mutation matrix and the live results. `Closes #181`.
Then the `🤖 Generated with [Claude Code](https://claude.com/claude-code)` footer. No
reference to this fork's issues. Re-run Task 7 Step 5's greps with the body file as a third
target.

- [ ] **Step 3: Push and open the PR, after approval**

```bash
cd /d/Entwicklung/HASI/issue66-work/wt && git push -u origin fix/distributor-inlet-open-gate
gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/distributor-inlet-open-gate --title "fix(distributor): do not start a cycle while the inlet reports open" --body-file /d/Entwicklung/HASI/issue66-work/pr-body.md
```

- [ ] **Step 4: Our issues, after approval**

`Eifel-Joe#66` gets a comment with the PR link and, in the same move, the label
`upstream:gemeldet` (rule P2: a pull request is open); `upstream:freigegeben` stays.
`Eifel-Joe#69` gets L3's measurement as a comment. The tracking issue `Eifel-Joe#42` gets the
state change. English first, German below.

---

## Addendum 2026-09-29 (dry run) — where this section differs, it wins

Found by running Tasks 1–8 once on `0b9a71bd` (see *This plan was run once before it was handed
over*). Every replacement below was applied in the dry run and is what the numbers there were
measured on.

### A1 — Task 1: one assertion as black writes it (cosmetic)

`black` wraps the 89-character trigger assertion at Task 2's lint step. Write it that way in
Task 1 Step 1 already:

```python
    assert (
        c._dist_credit_zone.await_args.kwargs["trigger"] == const.RUN_TRIGGER_OBSERVED
    )
```

### A2 — Task 3 Step 1: `_NOTICE` on one line (cosmetic)

`black` joins the parenthesised string (99 characters; the parentheses do not make it fit):

```python
_NOTICE = "Distributor 'Garten' did not start a watering cycle: its inlet switch.inlet was open."
```

### A3 — Task 3 Step 7: the expected numstat is `3	1`, not `2	0`

`no_demand` is the **last** key of `checks`, so appending `inlet_open` after it puts a comma on
the `no_demand` line: per file one changed line and two added keys. Measured on all eight
files: `3	1`. The `halted` insertion sits before `reason` and touches no other line. Expected
output of Step 7: eight lines `3	1	…/<lang>.json`; the check that matters is that the `-` line
is exactly the `no_demand` line without its comma.

### A4 — Task 4 Steps 4–5: stamp through a one-line helper

As written, the service branch's stamp is 91 characters at that indentation, and `black` turns
it into

```python
                self._dist_own_close_times()[
                    distributor.get("id")
                ] = self.hass.loop.time()
```

— a second shape for the same statement next to the classic branch's one-liner, and mutation
anchors 9 and 14 no longer match. Both call sites use a helper instead (one writer, one line).

**Step 4** becomes (the `_dist_own_close_times` docstring is corrected as well, see A9):

```python
    def _dist_own_close_times(self) -> dict:
        """{distributor_id: loop time} of the integration's own last inlet close.

        Read by the inlet gate's grace (#181). In memory only, like the in-flight
        set: a restart forgets it, which can only cost a refusal (the safe
        direction), and the resume path's own close stamps afresh. Lazily created
        so no coordinator __init__ change is needed."""
        times = getattr(self, "_dist_own_close", None)
        if times is None:
            times = self._dist_own_close = {}
        return times

    def _dist_stamp_own_close(self, distributor: dict) -> None:
        """Stamp the integration's own close of this inlet: the grace starts now."""
        self._dist_own_close_times()[distributor.get("id")] = self.hass.loop.time()
```

**Step 5**: in the replacement `_dist_close_inlet`, the two stamps become
`self._dist_stamp_own_close(distributor)` — after `await self.hass.services.async_call(...)` inside
`if stop:`, and after `await self._dist_domain_turn(...)`. Docstring unchanged. Measured: `black`
leaves it as is; 33 passed, the four distributor suites 207 passed.

### A5 — Task 6: the paragraph on one line

`docs/configuration-distributors.md` writes every paragraph as a single line (on `0b9a71bd`
not one wrapped paragraph outside the front matter). Insert the Step 1 text as one line; the
rendering is identical.

### A6 — Task 7 Step 5: the third grep

`grep -rn "Eifel-Joe" custom_components/ tests/ docs/` is **not** empty on the base: JustChr
names Eifel-Joe as the reporter in `migrate_domain.py`, `self_closing.py`, `test_migrate_domain.py`,
`test_self_closing.py`, `test_service_watch.py` (plus their `.pyc`). That is upstream's text and
stays. The third check becomes:

```bash
git grep -n "Eifel-Joe#" HEAD -- custom_components tests docs
```

Measured: empty on the base and on the branch; the first two greps are empty on the branch.

### A7 — Task 8: the runner

Three guards added to the engine: it refuses to start while `distributor.py` or `const.py`
differ from `HEAD`; a run whose summary shows no `passed`/`failed` count is reported `BROKEN`,
never `survived`; and a run that has not ended after `MUT_TIMEOUT` seconds (default 300; a run
takes ~17 s) is killed together with its process tree and reported `HANG`. `OUT` takes an
optional second argument, and `MUT_ONLY="5,9"` limits a run to the listed mutations (for a
re-run after a review change). The anchors of mutations 9, 11, 13 and 14 follow A4:

```python
    (9, DIST, "the service no-op stamps too",
     "                self._dist_stamp_own_close(distributor)\n"
     "            return\n",
     "            self._dist_stamp_own_close(distributor)\n"
     "            return\n",
     "test_a_service_distributor_without_stop_service_gets_no_grace"),
    (11, DIST, "the classic close is stamped before it is sent",
     "        await self._dist_domain_turn(distributor.get(\"inlet_entity\"), False)\n"
     "        self._dist_stamp_own_close(distributor)\n",
     "        self._dist_stamp_own_close(distributor)\n"
     "        await self._dist_domain_turn(distributor.get(\"inlet_entity\"), False)\n",
     "test_a_close_that_raised_starts_no_grace"),
    (13, DIST, "the classic close is never stamped",
     "        await self._dist_domain_turn(distributor.get(\"inlet_entity\"), False)\n"
     "        self._dist_stamp_own_close(distributor)\n",
     "        await self._dist_domain_turn(distributor.get(\"inlet_entity\"), False)\n",
     "test_the_next_cycle_runs_within_the_grace_after_our_own_close"),
    (14, DIST, "the stop_service close is never stamped",
     "                await self.hass.services.async_call(domain, service, data)\n"
     "                self._dist_stamp_own_close(distributor)\n",
     "                await self.hass.services.async_call(domain, service, data)\n",
     "test_a_stop_service_close_starts_the_grace"),
```

**Mutation 5 deadlocks a test, and the engine had no timeout.** Without the in-flight guard,
`test_distributor_cycle.py::test_second_concurrent_cycle_rejected_by_single_flight_lock` starts its
second cycle into the same `release.wait()` as the first and never returns; the dry run's matrix
hung there until the pytest process was killed by hand. With the timeout guard it ends as `HANG`
(measured with `MUT_ONLY=5 MUT_TIMEOUT=60`: `HANG` after 60 s, no pytest process left behind,
the source restored). The venv's `python.exe` is a launcher whose child runs pytest, so the guard
kills the tree (`taskkill /T /F`); a plain `kill()` leaves the child running with the pipes open.
A hang is a detection — CI would fail on its job timeout — but not a clean one, so mutation 5 is
read from `mut5_rerun.py`, which applies it alone with exactly that one test deselected
(`--deselect`). `pytest-timeout` is installed but does not help: on Windows it uses the thread
method, which ends the whole run, not the one test.

Both scripts as measured: `D:\Entwicklung\HASI\issue66-work\probe\mutate.py` and `…\probe\mut5_rerun.py`
(first argument = worktree, default `issue66-work\wt`); copy them to `issue66-work\` for the real
run. Task 8 Step 2 then runs:

```bash
cd /d/Entwicklung/HASI/issue66-work && sha256sum wt/custom_components/irrigation_plus/distributor.py wt/custom_components/irrigation_plus/const.py > pre-mutation.sha ; PYTHONIOENCODING=utf-8 /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe mutate.py /d/Entwicklung/HASI/issue66-work/wt 2>&1 | tail -45 ; PYTHONIOENCODING=utf-8 /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe mut5_rerun.py ; sha256sum -c pre-mutation.sha
```

Expected, as measured: `every source restored byte-for-byte: True`,
`17 killed / 18 applied / 18 total; HANG: [5]`, then from the re-run
`KILLED BY test_a_distributor_in_flight_is_not_reported_as_an_open_inlet` and
`restored byte-for-byte: True`, then two `OK`. Run it in the background (~12 min); do not read
or evaluate the worktree while it mutates.

### A8 — Task 0 Step 4: reuse the baseline

The dry run measured the baseline on `0b9a71bd` into the real run's file names
(`issue66-work\measure\baseline-0b9a71bd-tzutc.txt`, `baseline-names.txt`, 374 names). If Step 1
reads `0b9a71bd`, keep both and skip Step 4; if the base moved, measure again as written.

### A9 — erratum in the design doc (restart), no behaviour change

The design says under *The grace after our own close*: "After a halt and after a restart the
distributor is uncertain, and the synced guard refuses before the gate is asked." True after a
halt and after a restart in the `pausing` phase; after a restart in `watering` (and `starting`)
`async_resume_distributor_cycles` closes the inlet and the distributor **stays synced**
(`distributor.py:1813-1816` on `0b9a71bd`, `test_distributor_cycle.py::test_resume_mid_watering_stays_synced_closes_inlet`). That close goes
through `_dist_close_inlet`, so it now stamps a grace like every other own close — consistent
with R6 ("every own close counts"). Only the wording was wrong; the Step 4 docstring said the
same and is corrected in A4.

### For the review (Task 9), not changed

The refusal path awaits `_dist_notify`; a `notify_target` whose service does not exist raises
there, and the claim then raises instead of returning `False` — for a scheduled dispatch that also
skips the distributors after it in the loop. The halt path (`_dist_mark_uncertain`) has the same
property today, inside the sweep. Consistent with it, so left as designed; the reviewer decides.

### A10 — after the code review of Tasks 1–2 (during execution): Task 5b, mutations 19–22

The per-task quality review of `c1ec30e5` (Tasks 1–2) found no defect in the gate; one finding is
taken, the rest are answered here.

**Taken — Task 5b.** Nothing pinned "no `await` between the in-flight check and `inflight.add`",
which the gate's docstring states and which Tasks 3–4 edit around: the existing
`test_second_concurrent_cycle_rejected_by_single_flight_lock` calls its second claim only after
the first has registered, so an inserted `await asyncio.sleep(0)` survived all distributor suites
(measured by the reviewer on a scratch copy). Task 5b, a commit of its own after Task 5, appends
`test_two_claims_scheduled_together_start_exactly_one_sweep` (two claims through `asyncio.gather`,
a sweep that yields; exactly one starts) and a second `siehe` line in the docstring of
`_dist_inlet_reports_open`. Full suite then 3466 + 41 = 3507 passed. The runner gains mutations
19 (a yield before `inflight.add`), 20 (a test run skips the gate), 21 (a forced member run skips
the gate) and 22 (the gate asked before the in-flight guard) — the last three because the reviewer
saw them survive on Task 2's commit alone and they must die once Tasks 3 and 5 are in. Anchors in
`issue66-work\probe\mutate.py`.

**Answered, not taken:**

| finding | why not |
|---|---|
| grace from the sweep's end also for service mode without `stop_service` | contradicts R6, a user decision: no command, no evidence the valve closed; a start over a still-open self-closing valve is the measured defect |
| a refusal notice for a cycle that would have found nothing to water (soil veto, nothing due) | the claim cannot know the sweep's later exits; recording every targeted member follows the rain-delay convention the design chose |
| `isinstance(inlet_entity, str)` guard like `_dist_refresh_inlet_watch` | unreachable: the websocket validates `cv.string`; a non-string would raise before `inflight.add`, leaking nothing |
| comment "never start over an open inlet" → "never claim while it reads open" | the residual window between claim and first open is listed in the design (*Explicitly not in this work*); the comment names the intent |
| cross-reference `closing` to the five private `("on", "open", "opening")` sets; `open → closing → closed` decodes no close edge | the const comment says why `closing` blocks; the close-edge gap is Eifel-Joe#69 |
| test module docstring and `_gate_host` describe later tasks; commit subject without `(#181)` | the file is built task by task; upstream squashes |

### A11 — after the code review of Task 3 (during execution): Task 3b, mutations 23–27

The review of `a8299a97` decided the question left open under *For the review (Task 9)*: the
refusal awaited `_dist_notify` unguarded, and Home Assistant's `async_call` raises
`ServiceNotFound` synchronously for a service that does not exist (a phone re-registered under a
new `notify.mobile_app_…` name). The reviewer measured it through the real dispatcher: distributor
A with an open inlet and a stale `notify_target`, distributor B closed — the dispatcher raised,
**B did not sweep**, and A's members got no history entry; before this branch the same state was a
silent `return False` and B watered. A report path must not stop another distributor's watering
(same class as the memory "Nebensächlicher Fetch darf die View nicht reißen"). The halt path in
`_dist_mark_uncertain` shares the property but raises after its own state write; it is upstream's
and stays untouched here.

**Task 3b**, a commit of its own after Task 3 (instructions: `issue66-work\prompts\t3-fix.md`):
`_dist_notify` in the refusal path inside `try/except Exception` with `_LOGGER.exception`; the
docstring says so, names "the members the cycle was for" (not "that did not get their water":
every targeted member is recorded, due or not) and labels the `None` trap as `NOT-TO-DO`;
`_dist_notify`'s first docstring line reads "a halt or a refusal". Tests:
`test_a_broken_notify_target_does_not_stop_the_history` (RED before the guard),
`test_a_refusal_is_notified_in_the_users_language` (de), `test_a_refusal_with_an_empty_target_records_nothing`,
`test_the_skip_reason_is_a_key_every_language_localizes`, and `_dist_members.assert_awaited_once_with(0)`
in the every-member test — each kills a mutant the reviewer saw survive. Dutch: `beregeningscyclus` →
`bewateringscyclus` ("bewater-" 56× in `nl.json`, "beregen-" 13×). Full suite then 3466 + 31 = 3497
after 3b; the later counts in this plan grow by four (Task 5: 3510, Task 5b: 3511).

Mutation runner: 16's anchor moves into the `try` (the notify replaced by `pass`); new 23 (the
guard removed: a failing notification propagates), 24 (the notice ignores the user's language),
25 (`if only_zone_ids:` — an empty target records every member), 26 (the skip code has no catalogue
key), 27 (`_dist_members` asked for another distributor).

Not taken: `int()` coercion pins (the dispatcher passes ints; low value); the trigger for
`distributor_run_now` and irrigate-now without a duration stays `schedule` (the claim only sees
`force_water`; the history table does not render the trigger).

### A12 — the sister path of A11 (user decision, 2026-09-29): Task 3c, the guard at the root

Task 3b's implementer found, and the re-review of `a2ae6bf2` measured, the same pattern in the halt
path: `_dist_mark_uncertain` awaits `_dist_notify` unguarded. With a stale target,
`async_resume_distributor_cycles` stopped after the first distributor — the next one's inlet was
never reconciled — and the error escaped the entry setup (`__init__.py:241`); a halt inside a sweep
aborted the dispatcher's other distributors. `_dist_notify`'s docstring itself calls the notify
target "an extra, optional channel". The user chose the root fix in this pull request (rule:
mirror bugs go into the same fix) over a separate issue: **Task 3c** guards only the optional
forward inside `_dist_notify` (`try/except Exception`, logged with the target; `NOT-TO-DO`: not
narrowed to `ServiceNotFound` — a schema rejection raises `vol.Invalid`, a corrupt target
`AttributeError`; not widened to `BaseException` — a cancellation must cancel) and **drops the 3b
guard** in the refusal path — one guard instead of two. Tests: `test_notify_a_failing_target_is_logged_not_raised`
and `test_notify_a_cancellation_still_cancels` in `test_distributor.py`,
`test_resume_goes_on_after_a_failing_notify_target` in `test_distributor_cycle.py` (the reviewer's
measured case: two distributors across a restart), the gate test's log text adjusted. Instructions:
`issue66-work\prompts\t3c-fix.md`. Full suite after 3c: 3497 + 3 = 3500; later counts grow by three
(Task 4: 3506, Task 5: 3513, Task 5b: 3514); the four distributor suites 210.

This changes upstream behaviour in the halt path, so the PR body names it.

Mutation runner, final list for Task 8: 16 back on its plan anchor (the refusal calls `_dist_notify`
plainly again); 23 becomes "the forward unguarded" (the root guard removed), plus 28 "the guard
widened to `BaseException`" (killer: the cancellation pin); 24–27 as in A11.

**Task 3d** (re-review of `a1088266`: "Ready to merge? Yes", one Minor taken): the NOT-TO-DO "do not
narrow to ServiceNotFound" had no killer — the reviewer measured three surviving mutants (narrowed
to `ServiceNotFound`; to `(ServiceNotFound, vol.Invalid)`; `_dist_split_service` moved out of the
`try`). `test_notify_a_failing_target_is_logged_not_raised` is parametrised over `ServiceNotFound`
and `vol.Invalid`, `test_notify_a_corrupt_target_is_logged_not_raised` (target `5`) is added, and the
docstring's `siehe` lines name every pin. Mutations 29–31 in the runner. Instructions:
`issue66-work\prompts\t3d-fix.md`. Full suite after 3d: 3502; the four distributor suites 212;
later: Task 4 3508, Task 5 3515, Task 5b 3516.

Not taken, separate issue proposed: a stale `stop_service` in `async_resume_distributor_cycles`
still stops the reconcile of the remaining distributors (measured by the reviewer on `a1088266`) —
an actuator, not an optional channel; isolating each distributor in that loop is a design question
of its own.

### A13 — after the code review of Task 4 (during execution): Task 4b, mutations 32–35

Task 4 went in as planned (`5d6fcfaf`: RED 2/35, GREEN 37, suites 212, full suite 3508, names
identical; the spec check rebuilt all three files byte-exact from base + blocks). The quality review
found the production code correct — stamp only after a returned command, per distributor, expiring
by construction on a monotonic clock, every own close through `_dist_close_inlet` — and four agreed
decisions unpinned, each a mutant that survived all 249 tests of the five distributor suites:

| mutant | new pin (Task 4b) |
|---|---|
| a `stop_service` close stamped before it is sent | `test_a_stop_service_that_raised_starts_no_grace` |
| the first close keeps its stamp (`setdefault`) | `test_a_later_close_restarts_the_grace` |
| the grace still holds at exactly 30 s (`<=`) | `test_the_grace_is_over_at_exactly_thirty_seconds` |
| every stamp kept under distributor 0 (the falsy id) | `test_the_grace_runs_for_a_distributor_that_is_not_number_zero` |

Plus two `siehe` lines (`_dist_close_inlet` → the raising-close test; `_dist_inlet_reports_open` →
the 30 s test). Mutations 32–35 in the runner. Instructions: `issue66-work\prompts\t4b-fix.md`. Gate
file 41, full suite 3512; later: Task 5 48 / 3519, Task 5b 49 / 3520. Not taken: the classic branch
stamps even when `_dist_domain_turn` sends nothing for an empty inlet entity — unobservable, the
gate returns before it reads the stamp.

### A14 — the final review (Task 9, 2026-09-30) and its fix commit

Opus reviewer over `upstream/master...dbefa0a7`: **"Yes, ready for the PR"**, no Critical, no
Important. Measured independently: full suite on a `git archive` copy 7 / 3520 / 9 / 367 with the
374 baseline names; lint with the exact CI versions (black 26.5.1, ruff 0.16.9) clean including the
three test files; both bundles equal the base plus exactly the two English insertions; upstream CI
on `0b9a71bd` (run 36601325803: HA 2026.2.3, pytest 9.0.0, pytest-asyncio 1.3.0) already runs the
same constructs (`ServiceNotFound(domain, service)`, `hass.data = {}` dispatcher hosts) green.

Six Minor findings; fix commit `842a4cec` (instructions `issue66-work\prompts\t9-fix.md`):

| # | finding | taken as |
|---|---|---|
| 1 | a close command that *returns* was accepted, not executed: a service failing in its background task is only logged, the stamp is set, and the gate overlooks that still-open inlet until the grace ends (probe on real `hass`, HA 2024.12.5) | behaviour stays (R6: "sent"); `_dist_close_inlet` docstring now `Wurzel:`/`Fix:` and says so; the `Grace:` paragraph names it next to the accepted trade; **the PR body names it** |
| 2 | a refusal can overwrite an open halt notification (same id) when the dispatcher claims B from its stale copy after B was halted during A's sweep (probe) | no code: the root is the stale-copies issue Eifel-Joe#71 — a comment there, text approved first |
| 3 | the grace for `closing` unpinned (mutant M-C survived) | the grace test parametrised over `on`/`closing`; mutation 36 |
| 4 | `_dist_notify`'s `Wurzel:` told the branch's intermediate state (the unguarded refusal never existed upstream) and missed the warn-mode watch | rewritten to upstream's callers; the refusal named as the new caller that would fail the same way |
| 5 | the docs paragraph: a refused test run writes no history; the grace counts from the sent command | paragraph corrected |
| 6 | `siehe` for the finish-anchor NOT-TO-DO | added |

For the PR body (reviewer): name A12 (the halt path's behaviour change), the **upgrade effect** (an
inlet entity that idles in `on`/`open`/`opening`/`closing` will refuse every cycle, with a
notification), and finding 1 as a second reason for the 30 s blind window.

### Execution record (2026-09-29/30)

Branch `fix/distributor-inlet-open-gate` in `issue66-work\wt` from `0b9a71bd`, twelve commits, none
pushed (the branch has no upstream tracking: `git worktree add -b … upstream/master` had set
`upstream/master` as its upstream, removed with `git branch --unset-upstream` right after creation):

| commit | content | full suite (`TZ=UTC`) |
|---|---|---|
| `c1ec30e5` | Tasks 1–2: the gate | 7 / 3485 / 9 / 367 |
| `a8299a97` | Task 3: log, notification, history, eight languages, dist | 3493 |
| `a2ae6bf2` | 3b: guard + four pins, Dutch wording (A11) | 3497 |
| `a1088266` | 3c: the guard at the root in `_dist_notify`, the 3b guard dropped (A12) | 3500 |
| `04fca3d3` | 3d: pins for every failure the guard takes (A12) | 3502 |
| `5d6fcfaf` | Task 4: the grace, with the A4 helper | 3508 |
| `f72da9b8` | 4b: four grace pins (A13) | 3512 |
| `3c1d3550` | Task 5: entry and estimate pins | 3519 |
| `56819851` | 5b: two claims start one sweep (A10) | 3520 |
| `dbefa0a7` | Task 6: the docs paragraph | 3520 |
| `842a4cec` | final-review fixes (A14) | 3521 |
| `2c221a7a` | the re-review's optional nit: a semicolon keeps the #181 trade apart from the failed close | docstring only; code AST-identical to `842a4cec`, gate 50 passed, lint clean |

Re-review of `842a4cec` (same Opus reviewer): **"Yes, ready for the pull request"**, no new finding;
code AST-identical to `dbefa0a7` apart from docstrings; every new sentence checked against the code
and against `homeassistant/core.py` of 2026.2.3 (non-blocking `async_call` raises only
`ServiceNotFound` and `vol.Invalid`; anything else is caught and logged in the background task);
full suite on a copy of `842a4cec` 7 / 3521 / 9 / 367, names identical. A first parallel run of the
reviewer showed one extra `ERROR at setup of tests/test_master.py::test_storage_version_is_14`
(`OSError: [WinError 10055]`, socketpair buffer exhausted by parallel pytest runs); green alone and
on the rerun — a local flake, not a regression.

Every run: 7 failed / 9 skipped / 367 errors with the 374 baseline names (`issue66-work\measure\*-names.txt`).
Every RED as predicted. Lint clean after each commit; committed dist == fresh build (Task 7).
Reference greps (A6) empty; the only issue number in the diff is `#181`. Mutation matrix on
`dbefa0a7`: 34 of 35 killed in `mutations.log`, mutation 5 `HANG` there and killed in
`mut5-rerun.log` (by the in-flight test and the 5b pin); mutation 36 (added with `842a4cec`) killed
by the `[closing]` case (`mutations-36.json`) — **36 of 36**. Runner and results under
`issue66-work\` (`mutate.py`, `mut5_rerun.py`, `mutations.json`, `mutations.log`, `mut5-rerun.log`).
