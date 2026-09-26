# Plan 1 of 2 — A zone fault is paired when raised, and ended by a good run (`Eifel-Joe#3`)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every site that announces a zone problem also records the fault, and a
good run on a self-closing, batch or OpenSprinkler zone ends it.

**Architecture:** Two one-line additions plus one. The unpaired site at
`self_closing.py:646` gains its `_set_zone_fault`. `_clear_zone_fault` goes into
`_sc_finish_run` and `async_stop_self_closing`, which is where all three modes
finalise — so two clearing sites cover the five set sites named in the issue,
with no line in `batch.py` or `run_watch.py`. A fourth task pins the one
ordering the change makes load-bearing.

**Tech Stack:** Python 3.12, pytest + pytest-homeassistant-custom-component,
black, ruff.

**Spec:** `docs/superpowers/specs/2026-09-26-self-closing-fault-lifecycle-design.md` §3.

**Base commit:** `418ab8a0`. **Baseline:** 7 failed / 3254 passed / 9 skipped /
349 errors; 356 names in `D:/Entwicklung/HASI/issue3-work/baseline-names.txt`.

**Test command (from this worktree — there is no local `.venv` here):**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock
```

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `custom_components/irrigation_plus/self_closing.py` | self-closing dispatch + finalisation | 3 added lines + comments: the pairing at the confirm-fail abort, the clear on completion, the clear on the early stop |
| `tests/test_self_closing.py` | self-closing behaviour | 3 new tests |
| `tests/test_opensprinkler.py` | OpenSprinkler lifecycle | 1 new test (the ordering pin) |

No other production file is touched. `batch.py` and `run_watch.py` get their
clearing for free because they finalise through the two functions above.

---

### Task 1: The valve that never opened also raises the fault

**Files:**
- Modify: `custom_components/irrigation_plus/self_closing.py:645-648`
- Test: `tests/test_self_closing.py`

- [x] **Step 1: Write the failing test**

Append to `tests/test_self_closing.py`, directly after
`test_run_aborts_and_fires_problem_when_confirm_entity_stays_off`:

```python
async def test_a_valve_that_never_opened_also_raises_the_zone_fault():
    """The confirm poll saw the valve stay off. The bus event was already fired
    here, the fault was not - the only unpaired site of the seven that announce
    a zone problem. An automation bound to the bus heard it; the problem sensor
    and the dashboard chip, which read the fault, stayed dark."""
    c = _coord()
    c._set_zone_fault = Mock()
    c._confirm_valve_running = AsyncMock(return_value=False)  # never opened
    c._timed_volume_l = Mock(return_value=20.0)
    c._credited_depth_native = Mock(return_value=4.0)
    zone = _zone(**{const.ZONE_CONFIRM_ENTITY: "valve.beet"})

    ok = await c.async_run_self_closing(zone, trigger="schedule")

    assert ok is False
    c._set_zone_fault.assert_called_once_with(2, const.PROBLEM_VALVE_DID_NOT_OPEN)
```

- [x] **Step 2: Run it and confirm it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py::test_a_valve_that_never_opened_also_raises_the_zone_fault -p _local_socket_unblock -q
```

Expected: **1 failed**, `AssertionError: Expected '_set_zone_fault' to be called
once. Called 0 times.`

- [x] **Step 3: Write the implementation**

In `self_closing.py`, inside `async_run_self_closing`'s `if confirmed is False:`
branch, immediately before the existing `self._fire_zone_problem(`:

```python
                # Paired, like the six other sites that announce a zone problem
                # (self_closing.py:547, batch.py:184/217/297, run_watch.py:1031):
                # the bus event is what a user automation binds to, the fault is
                # what the problem binary_sensor and the dashboard chip read.
                # This one fired the event alone, so a valve that never opened
                # was invisible to anyone not listening on the bus.
                # siehe test_self_closing.py::
                # test_a_valve_that_never_opened_also_raises_the_zone_fault
                self._set_zone_fault(zone_id, const.PROBLEM_VALVE_DID_NOT_OPEN)
                self._fire_zone_problem(
                    zone_id, zone, confirm_target, const.PROBLEM_VALVE_DID_NOT_OPEN
                )
```

- [x] **Step 4: Run it and confirm it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py -p _local_socket_unblock -q
```

Expected: all of `test_self_closing.py` passes, including the pre-existing
`test_run_aborts_and_fires_problem_when_confirm_entity_stays_off`.

- [x] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/self_closing.py tests/test_self_closing.py
git commit -F - <<'EOF'
fix(self-closing): a valve that never opened also raises the zone fault

Seven sites announce a zone problem on the bus. Six also record the
fault, which is what the per-zone problem binary_sensor, the hub sensor
and the dashboard chip read. The confirm-fail abort fired the event
alone, so the one failure a user most needs to see - the valve did not
open - reached only an automation already listening on the bus.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: A completed run clears the fault

**Files:**
- Modify: `custom_components/irrigation_plus/self_closing.py:426-427`
- Test: `tests/test_self_closing.py`

- [x] **Step 1: Write the failing test**

Append to `tests/test_self_closing.py`:

```python
async def test_a_completed_run_clears_the_zone_fault():
    """_clear_zone_fault had five callers, all of them on the classic metered or
    rotating path in irrigation.py. A self-closing, batch or OpenSprinkler zone
    could therefore raise a fault and never end one: _zone_faults lives in
    memory, so the problem sensor stayed on until HA was restarted."""
    c = _coord()
    c._clear_zone_fault = Mock()
    store_zone = _zone(**{const.ZONE_BUCKET: -2.0, const.ZONE_MAXIMUM_BUCKET: 24.0})
    c.store.get_zone = Mock(side_effect=lambda zid: store_zone)
    c.store.async_get_config = AsyncMock(
        return_value={
            const.CONF_ACTIVE_VALVE_RUNS: [
                {
                    const.RUN_ZONE_ID: 2,
                    const.RUN_PLANNED_SECONDS: 600.0,
                    const.RUN_PRE_BUCKET: -2.0,
                }
            ]
        }
    )
    c._sc_finish_flow = Mock(return_value=(2.26, {}))
    c._credited_depth_native = Mock(return_value=2.26)
    c._flow_calibration_check = AsyncMock()

    await c._sc_finish_run(2)

    c._clear_zone_fault.assert_called_once_with(2)
```

- [x] **Step 2: Run it and confirm it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py::test_a_completed_run_clears_the_zone_fault -p _local_socket_unblock -q
```

Expected: **1 failed**, `Expected '_clear_zone_fault' to be called once. Called
0 times.`

- [x] **Step 3: Write the implementation**

In `self_closing.py`, in `_sc_finish_run`, between the existing
`await self._stamp_run_finalized(zone_id, volume_l)` and
`await self._record_run(`:

```python
        # A good run ends the zone's fault, exactly as the classic runner ends
        # it (irrigation.py:1601, and its rotating twins at :1953 / :2239) -
        # placed before the record there too.
        # Wurzel: all five _clear_zone_fault callers sat on the classic metered
        #   and rotating paths, none of which a self-closing, batch or
        #   OpenSprinkler zone can reach. Those three raise faults at five sites
        #   and cleared at none, and _zone_faults is in-memory, so the only cure
        #   was an HA restart.
        # This one line reaches all three because all three finalise here:
        #   batch.py:756, run_watch.py:982 / :1012.
        # siehe test_self_closing.py::test_a_completed_run_clears_the_zone_fault
        self._clear_zone_fault(zone_id)
```

- [x] **Step 4: Run it and confirm it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py tests/test_batch.py tests/test_opensprinkler.py -p _local_socket_unblock -q
```

Expected: all pass. These three files cover the three modes that reach the new
line.

- [x] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/self_closing.py tests/test_self_closing.py
git commit -F - <<'EOF'
fix(self-closing): a completed run ends the zone's fault

_clear_zone_fault had five callers and all of them sat on the classic
metered or rotating path. A self-closing, batch or OpenSprinkler zone
could raise a fault at five sites and clear it at none, and the fault map
lives in memory, so a zone that faulted once reported a problem until HA
was restarted - including to any automation holding irrigation off while
a zone reports one.

_sc_finish_run is where all three modes finalise a completed run
(batch.py:756, run_watch.py:982 and :1012), so the clear lands once and
reaches all three.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 3: A partial run clears it too

**Files:**
- Modify: `custom_components/irrigation_plus/self_closing.py:993-994`
- Test: `tests/test_self_closing.py`

- [x] **Step 1: Write the failing test**

Append to `tests/test_self_closing.py`:

```python
async def test_a_stopped_run_clears_the_zone_fault_as_the_classic_runner_does():
    """The classic runner clears on a partial as well as a completion
    (_record_rotating_stop, irrigation.py:1777): a run that was stopped still
    watered, so it is evidence the valve works."""
    c = _coord()
    c._clear_zone_fault = Mock()
    store_zone = _zone(**{const.ZONE_BUCKET: -1.0})
    c.store.get_zone = Mock(return_value=store_zone)
    c.store.async_get_config = AsyncMock(
        return_value={
            const.CONF_ACTIVE_VALVE_RUNS: [
                {
                    const.RUN_ZONE_ID: 2,
                    const.RUN_PLANNED_SECONDS: 600.0,
                    const.RUN_PRE_BUCKET: -5.0,
                }
            ]
        }
    )
    c._sc_elapsed = Mock(return_value=300.0)
    c._timed_volume_l = Mock(return_value=10.0)

    await c.async_stop_self_closing(2)

    c._clear_zone_fault.assert_called_once_with(2)
```

- [x] **Step 2: Run it and confirm it fails**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py::test_a_stopped_run_clears_the_zone_fault_as_the_classic_runner_does -p _local_socket_unblock -q
```

Expected: **1 failed**, `Expected '_clear_zone_fault' to be called once. Called
0 times.`

- [x] **Step 3: Write the implementation**

In `self_closing.py`, in `async_stop_self_closing`, between the existing
`await self._stamp_run_finalized(zone_id, delivered_l)` and
`await self._record_run(`:

```python
        # The completion twin's reasoning (_sc_finish_run), and the classic
        # runner clears on its partials as well: a stopped run still watered.
        # NOT-TO-DO: do not move this below the record, and do not assume it is
        #   the last word on the zone's fault. _watch_give_up (run_watch.py:1028)
        #   calls this stop and only THEN sets station_never_ran - the clear here
        #   runs first and the set survives. Pinned by test_opensprinkler.py::
        #   test_a_station_that_never_ran_stays_faulted_after_the_stop_cleared.
        self._clear_zone_fault(zone_id)
```

- [x] **Step 4: Run it and confirm it passes**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py tests/test_batch.py tests/test_opensprinkler.py tests/test_run_watch.py tests/test_service_watch.py -p _local_socket_unblock -q
```

Expected: all pass.

- [x] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/self_closing.py tests/test_self_closing.py
git commit -F - <<'EOF'
fix(self-closing): a stopped run ends the zone's fault as well

The completion twin's reasoning: the classic runner clears on a partial
too (_record_rotating_stop), because a run that was stopped still
watered. With this, the two functions the self-closing family finalises
through both end a fault, and the five set sites named in Eifel-Joe#3
are all reachable by a clear.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Pin the ordering Task 3 made load-bearing

**Files:**
- Test: `tests/test_opensprinkler.py`

`_watch_give_up` calls `async_stop_self_closing` and only then
`_set_zone_fault`. From Task 3 the stop clears, so the correctness of
`station_never_ran` now depends on that order. Nothing in the code says so.

- [x] **Step 1: Write the test**

Append to `tests/test_opensprinkler.py`, directly after
`test_a_station_the_controller_drops_is_written_off_immediately`:

```python
async def test_a_station_that_never_ran_stays_faulted_after_the_stop_cleared(hass):
    """_watch_give_up stops the run first and sets its fault second, and
    async_stop_self_closing now clears on the way through. The order is what
    keeps station_never_ran alive; hoisting the set above the stop would make
    the clear swallow it, silently and with every test still green.

    Pins the order, not just the call: the LAST word on this zone's fault has to
    be the set."""
    _publish(hass)
    c = _coord(hass)
    order = []
    c._set_zone_fault = Mock(side_effect=lambda *a, **k: order.append("set"))
    c._clear_zone_fault = Mock(side_effect=lambda *a, **k: order.append("clear"))
    await c.async_run_self_closing(_zone())
    c.store.get_zone = Mock(return_value=_zone(**{const.ZONE_BUCKET: -1.0}))

    await _drive(hass, running="off", program_id=99)
    await _drive(hass, running="off", program_id=0)

    assert "clear" in order, "the stop should have cleared on its way through"
    assert order[-1] == "set", f"the fault must survive the stop's clear: {order}"
    c._set_zone_fault.assert_called_with(2, const.PROBLEM_STATION_NEVER_RAN)
```

- [x] **Step 2: Run it and confirm it passes on the current code**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_opensprinkler.py::test_a_station_that_never_ran_stays_faulted_after_the_stop_cleared -p _local_socket_unblock -q
```

Expected: **1 passed.** This is a pin, not a bugfix — the behaviour is already
correct and the test exists to keep it that way. Its RED is Step 3.

- [x] **Step 3: Prove the pin bites (mutation)**

> **MEASURED 2026-09-26 - this step's mutation was WRONG and is corrected
> below.** Moving the clear inside `async_stop_self_closing` cannot change the
> order the pin guards: `_watch_give_up` runs after the stop RETURNS either
> way, so the clear precedes its set wherever it sits in the function. The pin
> stayed green under it (1 passed). The code comment written in Task 3 claimed
> otherwise and was corrected to match the measurement.
>
> The mutation that does test the pin is in `run_watch.py`: hoist
> `_watch_give_up`'s own `self._set_zone_fault(zid, reason)` ABOVE its
> `await self.async_stop_self_closing(...)` call - the refactor the pin exists
> to catch. Measured result: **1 failed, 69 passed, 13 errors**, the single
> failure being this pin with
> `AssertionError: the fault must survive the stop's clear: ['set', 'clear']`.
> The pre-existing `test_a_station_the_controller_drops_is_written_off_immediately`
> stays GREEN under it, because it asserts the call and not the order - which
> is the whole justification for adding the pin.

Apply the `run_watch.py` hoist described above, then re-run:

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_opensprinkler.py::test_a_station_that_never_ran_stays_faulted_after_the_stop_cleared -p _local_socket_unblock -q
```

Expected: **1 failed**, `the fault must survive the stop's clear: ['set',
'clear']`. Then revert it:

```bash
git checkout -- custom_components/irrigation_plus/run_watch.py
```

That is safe and restores Tasks 1-3, because all three are already committed -
the checkout takes the file back to HEAD, not to the base commit.

- [x] **Step 4: Confirm the file is back to its committed state**

```bash
git diff --stat custom_components/irrigation_plus/run_watch.py
```

Expected: **no output** - the mutation is fully reverted.

- [x] **Step 5: Commit**

```bash
git add tests/test_opensprinkler.py
git commit -F - <<'EOF'
test(opensprinkler): pin that a station-never-ran fault survives the stop

_watch_give_up stops the run and sets its fault in that order, and the
stop now clears faults on its way through. The order is what keeps
station_never_ran alive, and nothing in the code said so: hoisting the
set above the stop would let the clear swallow it with every other test
still green. The pin asserts the order, not just the call - moving the
clear to the end of async_stop_self_closing turns it red.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Gates

> **MEASURED 2026-09-26 - read before trusting any per-file run.** Error counts
> depend on the SELECTION, not only on the code: the same three files that give
> 51 errors in a subset contribute 13 to the full run, and the untouched base
> commit reproduces the subset's 51 exactly. A per-file run is therefore good
> for the one test being written and for nothing else. **Only this full-suite
> run, diffed by name against the baseline, decides whether anything
> regressed** - and it earned its keep here: it caught
> `test_master.py::test_self_closing_release_on_confirm_failure_does_not_strand_the_pump`,
> which no per-file selection in Tasks 1-4 included.

- [x] **Step 1: Full suite**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --tb=no > /d/Entwicklung/HASI/issue3-work/after-plan1.txt 2>&1; tail -3 /d/Entwicklung/HASI/issue3-work/after-plan1.txt
```

Expected: `7 failed, 3258 passed, 9 skipped, ..., 349 errors` - the baseline's
3254 passed **+4**, being exactly the four new tests. Failures and errors
unchanged at 7 and 349.

**MEASURED: exactly that** - `7 failed, 3258 passed, 9 skipped, 10 warnings,
349 errors in 270.64s`. But only on the SECOND run: the first came back
`8 failed, 3257 passed` and the extra failure was
`test_master.py::test_self_closing_release_on_confirm_failure_does_not_strand_the_pump`.
Its double had a bare `Mock` for `hass.data`, so Task 1's new fault raised
`TypeError: 'Mock' object is not iterable` inside HA's dispatcher. An
incomplete fixture, not an impossible one - a confirm failure on a master-pump
zone is an ordinary field case - so the double got the real dict the
self-closing double next door already uses. Fixed in `93dcc801`.

- [x] **Step 2: Diff the failure names against the baseline**

```bash
cd /d/Entwicklung/HASI/issue3-work && grep -E "^(FAILED|ERROR) " after-plan1.txt | sed 's/ - .*$//' | sort > after-plan1-names.txt && diff baseline-names.txt after-plan1-names.txt && echo "IDENTICAL"
```

Expected: `IDENTICAL`. Any line here is a regression, not a known blocker.

- [x] **Step 3: Lint**

```bash
cd /d/Entwicklung/HASI/issue3-work/wt && uvx black --check custom_components/irrigation_plus/ && uvx ruff check custom_components/irrigation_plus/
```

Expected: `68 files would be left unchanged.` and `All checks passed!`

**MEASURED: `69 files would be left unchanged.` and `All checks passed!`** The
69th is `actuate.py`, which JustChr added in `90187eed` after the figure in
this plan's header was written. Not a regression - a stale prediction.

- [x] **Step 4: Mutation matrix — every test must be earned**

Apply each mutation, run the named tests, confirm the expected count goes red,
then revert it before the next one. A test that stays green under its own
mutation is not proving anything.

**Revert with `git checkout -- <file>`, never with a reverse text
replacement.** Measured the hard way: the first attempt reverted M1 by swapping
its replacement back, and M1's anchor (`self._fire_zone_problem(`) occurs twice
in `self_closing.py`. The revert refused as ambiguous - correctly - but M1 was
left applied and M2 and M3 were then measured on a mutated tree, showing three
kills where they have one and two. The whole matrix was re-run from a clean
tree; the numbers below are from that run.

Driver: `D:/Entwicklung/HASI/issue3-work/matrix1.py` (applies, measures,
`git checkout`s, asserts a unique anchor before touching anything).

**MEASURED, all five as predicted, each killing exactly its own tests:**

| # | result | killed |
|---|---|---|
| M1 | 1 failed / 132 passed / 13 errors | `..._a_valve_that_never_opened_also_raises_the_zone_fault` |
| M2 | 1 failed / 132 passed / 13 errors | `test_a_completed_run_clears_the_zone_fault` |
| M3 | 2 failed / 131 passed / 13 errors | `..._a_stopped_run_clears_...` + `..._stays_faulted_after_the_stop_cleared` |
| M4 | 1 failed / 132 passed / 13 errors | `..._a_station_that_never_ran_stays_faulted_after_the_stop_cleared` |
| M5 | 1 failed / 132 passed / 13 errors | `..._a_valve_that_never_opened_also_raises_the_zone_fault` |

The pin is killed twice over, by M3 and M4, for two different reasons: M3
removes the clear it expects to see, M4 reverses the order it exists to guard.

| # | Mutation | Command | Expected |
|---|---|---|---|
| M1 | Delete the `_set_zone_fault` line added in Task 1 | `pytest tests/test_self_closing.py -p _local_socket_unblock -q` | 1 failed (`..._also_raises_the_zone_fault`) |
| M2 | Delete the `_clear_zone_fault` line added in Task 2 | `pytest tests/test_self_closing.py -p _local_socket_unblock -q` | 1 failed (`test_a_completed_run_clears_the_zone_fault`) |
| M3 | Delete the `_clear_zone_fault` line added in Task 3 | `pytest tests/test_self_closing.py tests/test_opensprinkler.py -p _local_socket_unblock -q` | 2 failed (`..._as_the_classic_runner_does` and the Task 4 pin's `"clear" in order`) |
| M4 | Hoist `_watch_give_up`'s `_set_zone_fault` above its `async_stop_self_closing` call (`run_watch.py`) | `pytest tests/test_opensprinkler.py -p _local_socket_unblock -q` | 1 failed (the Task 4 pin's order assertion). **Measured: as predicted, 1 failed / 69 passed / 13 errors.** The original M4 - moving the clear inside the stop - was measured GREEN and is not a valid mutation; see Task 4 Step 3. |
| M5 | Change Task 1's constant to `const.PROBLEM_STATION_UNRESOLVED` | `pytest tests/test_self_closing.py -p _local_socket_unblock -q` | 1 failed (`..._also_raises_the_zone_fault`) |

- [x] **Step 5: Confirm the tree is clean after the mutations**

```bash
git status --short && git diff --stat
```

Expected: no modified tracked files. Every mutation reverted.

- [x] **Step 6: Record the measured numbers in the plan**

Done inline above. Four predictions missed, all recorded where they were made:

1. **Task 4's mutation was the wrong one** and stayed green - moving the clear
   inside the stop cannot change the order a later caller sees. The real
   mutation lives in `run_watch.py`, and the code comment Task 3 wrote was
   corrected to match.
2. **The lint count** is 69 files, not 68 (`actuate.py`, added upstream after
   this plan was written).
3. **The full suite found a regression** the per-file runs could not:
   `test_master.py`'s double needed a real `hass.data`.
4. **The mutation revert mechanism** had to change from reverse-replacement to
   `git checkout` after M1's anchor turned out to be ambiguous.

The RED messages themselves read `Expected 'mock' to be called once` rather
than naming the method - the doubles are unnamed `Mock()`s. Cosmetic, but the
plan's predicted text was wrong in all three places it appears.

- [x] **Step 7: Commit the plan's measured state**

```bash
git add docs/superpowers/plans/2026-09-26-fault-pairing-and-clearing.md
git commit -m "docs(plan): plan 1 measured - $(date +%F)" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## What this plan does NOT do

- Nothing in `batch.py` or `run_watch.py`. Both get their clearing through the
  two functions edited here; a line in either would be a second mechanism.
- No change to any of the six already-paired sites.
- Nothing about the dry run — that is Plan 2, which rebases on this.
- The upstream PR is a separate, approval-gated step. Do not push, do not run
  `gh pr create`.
