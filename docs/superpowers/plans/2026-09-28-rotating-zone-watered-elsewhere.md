# A rotating zone watered elsewhere — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A rotating zone that something else watered between its turns is not handed another slot, and so is not credited a second time.

**Architecture:** `Rotation` gains one field, `in_flight`, naming the zone whose slot the rotation itself dispatched. `_chain_rotation_advance` sets it; `_chain_advance` reads it where it already stamps `last_finish`, and writes off the remainder of any held zone that finalises while it is *not* the slot in flight.

**Tech Stack:** Python 3.12, pytest + pytest-homeassistant-custom-component, Home Assistant custom component.

**Spec:** `docs/superpowers/specs/2026-09-28-rotating-zone-watered-elsewhere-design.md`

---

## Working context

Worktree: `D:\Entwicklung\HASI\issue45-work\wt`, branch
`fix-a-rotating-zone-already-watered-keeps-its-turn`, base `6acfc819` (`upstream/master`).

A worktree has no `.venv` of its own. Every test command uses the main checkout's
interpreter by absolute path:

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock
```

Redirect the temp directories per command block so nothing lands on `C:`:

```bash
export TMPDIR=/d/Entwicklung/HASI/issue45-work/tmp TEMP=D:/Entwicklung/HASI/issue45-work/tmp TMP=D:/Entwicklung/HASI/issue45-work/tmp
```

Baseline for this base commit: `D:\Entwicklung\HASI\issue45-work\baseline-6acfc819.txt`,
**374 names**, counters `7 failed / 3388 passed / 9 skipped / 367 errors`.

**Nothing in this branch may reference our own issue tracker** — not code, not tests, not
commit messages. The probe this work started from carries `Eifel-Joe#45` and `JustChr#165`
in its docstring; neither is copied. Task 6 greps for it.

## File structure

| File | Responsibility | Change |
|---|---|---|
| `custom_components/irrigation_plus/run_chain.py` | the shared chain engine (service + OpenSprinkler, sequential + rotating) | Modify: `Rotation` (l. 52-64), `_chain_advance` (l. 312-318), `_chain_rotation_advance` (l. 718-722) |
| `tests/test_service_chain.py` | rotation dispatch behaviour, and the `_coord`/`_zone`/`_dispatch`/`_finish` fixtures the other chain suites import | Modify: one new class at the end |

All four tests go in `tests/test_service_chain.py`. The log-shape assertion goes there too
rather than beside its sibling in `tests/test_chain_carries_its_plan.py`: the fixtures are
local, the diff stays in one file, and that file's module docstring carries an own-issue
reference this branch must not touch. The new class docstring points at the sibling.

---

### Task 1: Pin the half that is already fixed

This test is **green from the start**. It is a regression pin, not a RED step: the
take-over guard it covers is master's, added by the upstream PR that fixed the other half,
and the fix in Task 3 must not disturb it. Its guarding power is demonstrated in Task 7,
not by failing now.

**Files:**
- Test: `tests/test_service_chain.py` (append at end of file)

- [ ] **Step 1: Append the new class with the control test**

```python
class TestARotatingZoneWateredElsewhere:
    """A rotating zone's turn is governed by ``remaining``, which records how much
    a zone has left — not who has already given it water.

    Two shapes of the same take-over, told apart by whether the other run is still
    going when the rotation reaches the zone. The log wording each one produces is
    asserted below; the sibling test for the still-running wording lives in
    tests/test_chain_carries_its_plan.py.
    """

    async def test_a_take_over_still_running_at_the_turn_is_written_off(self, hass):
        """The half the take-over guard already covers — kept so it cannot slip."""
        c = _coord(hass, ROTATING, slot=5, absorb=0)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [z1, z2])
        # Something else is STILL watering zone 2 when its turn comes.
        c.zone_run_in_flight = lambda zid: int(zid) == 2

        await _finish(c, 1)

        rot = c._chain_state(const.WATERING_MODE_SERVICE).rotation
        assert rot.remaining[2] == 0.0
        assert not any(zid == 2 for zid, _ in c._dispatched)
```

- [ ] **Step 2: Run it and confirm it passes**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && export TMPDIR=/d/Entwicklung/HASI/issue45-work/tmp TEMP=D:/Entwicklung/HASI/issue45-work/tmp TMP=D:/Entwicklung/HASI/issue45-work/tmp && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest "tests/test_service_chain.py::TestARotatingZoneWateredElsewhere" -p _local_socket_unblock -q
```

Expected: `1 passed`.

- [ ] **Step 3: Commit**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && git add tests/test_service_chain.py && git commit -F - <<'EOF'
test(chain): pin the take-over a rotation already writes off

The guard that drops a rotating zone whose turn arrives while another run
still holds it has no test of its own for the dispatch it prevents. Pin it
before touching the code around it.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: RED — the take-over that finished before the turn

**Files:**
- Test: `tests/test_service_chain.py` (inside `TestARotatingZoneWateredElsewhere`)

- [ ] **Step 1: Write the failing test**

Append inside the class from Task 1:

```python
    async def test_a_take_over_that_finished_before_the_turn_gets_no_slot(self, hass):
        """The run is gone by the zone's turn, so no predicate can still see it.

        ``_sc_finish_run`` removes the record before advancing the chain, which is
        what ``zone_run_in_flight`` reads. A zone watered in full and finished
        while the rotation waited therefore looks exactly like one that has been
        waiting its turn all along.
        """
        c = _coord(hass, ROTATING, slot=5, absorb=0)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        await _dispatch(c, [z1, z2])
        # Irrigate-now waters zone 2 in full and finishes BEFORE zone 1's slot
        # ends -- irrigation.py's manual run, dispatched outside the chain.
        await c.async_run_self_closing(dict(z2), trigger="manual")
        await _finish(c, 2)
        after_take_over = len(c._dispatched)

        await _finish(c, 1)

        rot = c._chain_state(const.WATERING_MODE_SERVICE).rotation
        later = c._dispatched[after_take_over:]
        assert not [d for d in later if d[0] == 2], later
        assert rot is None or rot.remaining[2] == 0.0
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && export TMPDIR=/d/Entwicklung/HASI/issue45-work/tmp TEMP=D:/Entwicklung/HASI/issue45-work/tmp TMP=D:/Entwicklung/HASI/issue45-work/tmp && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest "tests/test_service_chain.py::TestARotatingZoneWateredElsewhere::test_a_take_over_that_finished_before_the_turn_gets_no_slot" -p _local_socket_unblock -q
```

Expected: `1 failed`, with `AssertionError: [(2, 300.0)]` — the rotation handed zone 2 a
300 s slot although it had just been watered for its full 600 s.

Do **not** commit a red test on its own; Task 3 makes it green in the same commit.

---

### Task 3: GREEN — name the slot the rotation is waiting for

**Files:**
- Modify: `custom_components/irrigation_plus/run_chain.py:52-64` (`Rotation`)
- Modify: `custom_components/irrigation_plus/run_chain.py:312-318` (`_chain_advance`)
- Modify: `custom_components/irrigation_plus/run_chain.py:718-722` (`_chain_rotation_advance`)

- [ ] **Step 1: Add the field to `Rotation`**

Replace the class (currently l. 51-64):

```python
@dataclass
class Rotation:
    """A rotating cycle: what each zone has left, and when it last stopped.

    ``cursor`` indexes ``order`` at the zone dispatched last, so the next turn
    resumes after it instead of restarting at the top every time.

    ``in_flight`` is the zone whose slot this rotation dispatched and is waiting
    for, and it is the only thing here that records WHO watered rather than what
    or when. Without it a finalising run cannot be told apart from a take-over:
    ``remaining`` says how much a zone has left, ``last_finish`` says when one
    last stopped — for the absorption wait — and the run record a guard would
    read is removed before the chain is advanced. ``cursor`` cannot stand in for
    it: it keeps pointing at a zone after that zone's slot has ended, so a run
    finishing during an absorption wait would be read as the rotation's own.
    """

    slot: float
    absorption: float
    order: list = field(default_factory=list)
    remaining: dict = field(default_factory=dict)
    last_finish: dict = field(default_factory=dict)
    cursor: int = -1
    in_flight: int | None = None
```

- [ ] **Step 2: Set it at the dispatch**

In `_chain_rotation_advance`, replace the dispatch (currently l. 715-722, the comment
block ending `own bucket credit, its own flow sampling, its own log line.` and the `if`
that follows):

```python
            # A copy, so the slot is what this run is dispatched, credited and
            # measured for while the zone's own stored duration — what the panel
            # shows and what the next rotation would be built from — is left
            # alone. Every slot is a run in its own right: its own record, its
            # own bucket credit, its own flow sampling, its own log line.
            #
            # Claimed BEFORE the dispatch, not after it: a run that finalised
            # inside the await would find no claim and have its own slot written
            # off as a take-over. Left standing when the dispatch is refused,
            # which is deliberate — the refusal below sets the remainder to 0.0
            # and only a fresh Rotation restores it, so a stale claim can only
            # suppress a write-off for a zone that has nothing left to write off.
            rotation.in_flight = zone_id
            if await self.async_run_self_closing(
                dict(zone, **{const.ZONE_DURATION: slot}), trigger=state.trigger
            ):
                return
```

- [ ] **Step 3: Read it where the finish is already heard**

In `_chain_advance`, replace the `last_finish` block (currently l. 312-318):

```python
        if rotation is not None and finished_zone_id is not None:
            # Stamped as the turn ends, not as the slot was dispatched: what the
            # soil is given to absorb is the water, so the wait runs from the
            # moment the valve stopped.
            zid = int(finished_zone_id)
            if zid in rotation.remaining:
                rotation.last_finish[zid] = dt_util.utcnow()
                if rotation.in_flight == zid:
                    # The slot this rotation dispatched and was waiting for.
                    rotation.in_flight = None
                elif rotation.remaining[zid] > 0:
                    # Some other run watered a zone this rotation still holds and
                    # has now ended, so its remainder goes the way a zone taken
                    # over while the rotation waited already does. This is the
                    # only moment it can be caught: the run record a guard would
                    # read is removed before this call, so by the zone's own turn
                    # there is nothing left to see. Written off here rather than
                    # remembered for the turn, so a stop landing in between does
                    # not report an already-watered zone as abandoned.
                    policy = chain_policy_for(mode)
                    _LOGGER.info(
                        "%s rotation: writing off zone %s and its remaining "
                        "%.0fs, another run watered it before its turn",
                        policy.label if policy else mode,
                        zid,
                        rotation.remaining[zid],
                    )
                    rotation.remaining[zid] = 0.0
                    # Safe although that run has been and gone: a run's ceiling is
                    # decided at its own dispatch and frozen into its record, so
                    # the marker it used is long consumed. What goes back is the
                    # rotation's own leftover.
                    self._drop_live_run_marker(zid)
```

- [ ] **Step 4: Run the new class and confirm both tests pass**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && export TMPDIR=/d/Entwicklung/HASI/issue45-work/tmp TEMP=D:/Entwicklung/HASI/issue45-work/tmp TMP=D:/Entwicklung/HASI/issue45-work/tmp && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest "tests/test_service_chain.py::TestARotatingZoneWateredElsewhere" -p _local_socket_unblock -q
```

Expected: `2 passed`.

- [ ] **Step 5: Run the whole chain suite for regressions**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && export TMPDIR=/d/Entwicklung/HASI/issue45-work/tmp TEMP=D:/Entwicklung/HASI/issue45-work/tmp TMP=D:/Entwicklung/HASI/issue45-work/tmp && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_service_chain.py tests/test_chain_carries_its_plan.py tests/test_opensprinkler.py -p _local_socket_unblock -q
```

Expected: no failures. `test_two_zones_take_turns` in particular must still pass — it is
the ordinary rotation the write-off must not touch.

- [ ] **Step 6: Commit**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && git add custom_components/irrigation_plus/run_chain.py tests/test_service_chain.py && git commit -F - <<'EOF'
fix(chain): a rotating zone watered elsewhere keeps no turn

A rotating zone taken over between its turns was dispatched a slot anyway
and credited a second time. The guard that covers the same take-over while
the other run is still in flight cannot reach this one: _sc_finish_run
removes the run record before advancing the chain, and that record is what
zone_run_in_flight reads, so by the zone's turn there is nothing left to
see.

Nor could the rotation work it out from what it carried. remaining says how
much a zone has left and last_finish says when one last stopped, for the
absorption wait; neither says who watered. Rotation now names the slot it
dispatched, so a run of a held zone ending while that is some other zone is
a take-over, and its remainder is written off as a take-over's already is.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: The sister path the fix opens — a refused dispatch

A refusal leaves `in_flight` pointing at a zone that will never finalise. The reasoning
that this is harmless is in the code comment and the spec; this test is the evidence for
it — a take-over after a refusal is still caught.

**Files:**
- Test: `tests/test_service_chain.py` (inside `TestARotatingZoneWateredElsewhere`)

- [ ] **Step 1: Write the test**

```python
    async def test_a_refused_dispatch_does_not_shadow_a_later_take_over(self, hass):
        """A refusal leaves the claim pointing at a zone that never finalises.

        Harmless by construction — the refusal writes that zone's remainder off,
        and only a fresh rotation restores it — but the claim is read for every
        zone, so the one that matters is a DIFFERENT zone taken over afterwards.
        """
        c = _coord(hass, ROTATING, slot=5, absorb=0)
        z1, z2, z3 = _register(
            c, _zone(1, duration=600), _zone(2, duration=600), _zone(3, duration=600)
        )
        spy = c.async_run_self_closing

        async def _refuse_zone_2(zone, **kw):
            if int(zone[const.ZONE_ID]) == 2:
                return False
            return await spy(zone, **kw)

        c.async_run_self_closing = _refuse_zone_2
        await _dispatch(c, [z1, z2, z3])
        # Zone 1's slot ends; zone 2 refuses its slot; zone 3 is dispatched, so
        # the claim now names zone 3 and zone 2's stale claim is behind it.
        await _finish(c, 1)
        # Something else waters zone 1 in full and finishes while zone 3 runs.
        await c.async_run_self_closing(dict(z1), trigger="manual")
        await _finish(c, 1)
        after_take_over = len(c._dispatched)

        await _finish(c, 3)

        later = c._dispatched[after_take_over:]
        assert not [d for d in later if d[0] == 1], later
```

- [ ] **Step 2: Run it**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && export TMPDIR=/d/Entwicklung/HASI/issue45-work/tmp TEMP=D:/Entwicklung/HASI/issue45-work/tmp TMP=D:/Entwicklung/HASI/issue45-work/tmp && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest "tests/test_service_chain.py::TestARotatingZoneWateredElsewhere::test_a_refused_dispatch_does_not_shadow_a_later_take_over" -p _local_socket_unblock -q
```

Expected: `1 passed`.

If it fails, do **not** patch the test to match. It means the stale claim is not harmless
after all, and the decision recorded in the spec has to be reopened.

- [ ] **Step 3: Commit**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && git add tests/test_service_chain.py && git commit -F - <<'EOF'
test(chain): a refused slot does not hide a later take-over

The claim naming the dispatched slot is deliberately left standing when a
dispatch is refused. Pin what that rests on: the next take-over is still
caught.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5: The log must say which of the two reasons fired

The two take-over shapes end in the same write-off. Whoever is reading the log needs to
know which one happened — the sibling assertion for the still-running wording is
`test_a_rotating_zone_taken_over_says_which_reason_fired` in
`tests/test_chain_carries_its_plan.py`.

**Files:**
- Test: `tests/test_service_chain.py` (inside `TestARotatingZoneWateredElsewhere`)

- [ ] **Step 1: Write the test**

```python
    async def test_the_two_take_over_shapes_do_not_read_alike(self, hass, caplog):
        """Same outcome, different cause: the line has to name which one."""
        c = _coord(hass, ROTATING, slot=5, absorb=0)
        z1, z2 = _register(c, _zone(1, duration=600), _zone(2, duration=600))
        c._live_run_zones = {1, 2}
        await _dispatch(c, [z1, z2])
        await c.async_run_self_closing(dict(z2), trigger="manual")
        caplog.clear()

        await _finish(c, 2)

        messages = [
            r.getMessage()
            for r in caplog.records
            if "writing off zone 2 and its remaining" in r.getMessage()
        ]
        assert any("watered it before its turn" in m for m in messages), messages
        assert not any("took it over while it waited" in m for m in messages), messages
        assert 2 not in c._live_run_zones
```

- [ ] **Step 2: Run it**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && export TMPDIR=/d/Entwicklung/HASI/issue45-work/tmp TEMP=D:/Entwicklung/HASI/issue45-work/tmp TMP=D:/Entwicklung/HASI/issue45-work/tmp && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest "tests/test_service_chain.py::TestARotatingZoneWateredElsewhere" -p _local_socket_unblock -q
```

Expected: `4 passed`.

- [ ] **Step 3: Commit**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && git add tests/test_service_chain.py && git commit -F - <<'EOF'
test(chain): the two take-over shapes are told apart in the log

Both end in the same write-off, so the line is all a reader has to tell
which one happened. Pin the wording of each against the other.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Gates — suite, baseline, lint, reference checks

**Files:** none (verification only)

- [ ] **Step 1: Run the full suite**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && export TMPDIR=/d/Entwicklung/HASI/issue45-work/tmp TEMP=D:/Entwicklung/HASI/issue45-work/tmp TMP=D:/Entwicklung/HASI/issue45-work/tmp && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q > /d/Entwicklung/HASI/issue45-work/branch-run.txt 2>&1; tail -2 /d/Entwicklung/HASI/issue45-work/branch-run.txt
```

Expected: `passed` up by exactly 4 against the baseline's 3388, i.e. **3392**; `failed`,
`skipped` and `errors` unchanged at 7 / 9 / 367.

- [ ] **Step 2: Diff the failing names against the baseline**

```bash
cd /d/Entwicklung/HASI/issue45-work && grep -E "^(FAILED|ERROR) tests/" branch-run.txt | sed 's/ - .*$//' | sort -u > branch-names.txt && echo "branch: $(wc -l < branch-names.txt)  baseline: $(wc -l < baseline-6acfc819.txt)" && diff baseline-6acfc819.txt branch-names.txt && echo "NAME DIFF EMPTY"
```

Expected: `374` both sides and `NAME DIFF EMPTY`.

- [ ] **Step 3: Lint — the two checks CI runs**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && uvx black --check custom_components/irrigation_plus/ && uvx ruff check custom_components/irrigation_plus/
```

Expected: `All done!` / `All checks passed!`.

- [ ] **Step 4: The three reference checks, on the added lines only**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && git diff 6acfc819..HEAD -U0 | grep '^+' | grep -v '^+++' > /d/Entwicklung/HASI/issue45-work/added.txt; echo "Eifel-Joe: $(grep -c 'Eifel-Joe' /d/Entwicklung/HASI/issue45-work/added.txt)"; echo "issue-refs: $(grep -cE '(Eifel-Joe|Befund [0-9]|PR [A-T]\b|spec [A-Z][0-9]|Task [0-9]+[a-z]?\b)' /d/Entwicklung/HASI/issue45-work/added.txt)"; echo "branch-SHAs: $(grep -cE '\b[0-9a-f]{7,40}\b' /d/Entwicklung/HASI/issue45-work/added.txt)"
```

Expected: `0`, `0`, `0`. A non-zero count is a stop, not a note: read the offending lines
and remove the reference before anything is pushed.

- [ ] **Step 5: Confirm the diff touches only the two intended files**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && git diff 6acfc819..HEAD --stat
```

Expected: exactly `custom_components/irrigation_plus/run_chain.py` and
`tests/test_service_chain.py`. `frontend/dist/` is untouched — this change has no frontend
side, so no bundle rebuild and no `git add -f`.

---

### Task 7: Mutation matrix

Every new decision gets a mutation, and each is either caught or recorded as a documented
survivor with the reason. A survivor is read first as a weak test, then as a mutation that
changes nothing observable.

**Files:**
- Create: `D:\Entwicklung\HASI\issue45-work\mutations.json` (scratch, not committed)

- [ ] **Step 1: Apply each mutation in turn, run the class, record the result**

Run after each edit, then revert it:

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && export TMPDIR=/d/Entwicklung/HASI/issue45-work/tmp TEMP=D:/Entwicklung/HASI/issue45-work/tmp TMP=D:/Entwicklung/HASI/issue45-work/tmp && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_service_chain.py tests/test_chain_carries_its_plan.py -p _local_socket_unblock -q | tail -2 && git checkout -- custom_components/irrigation_plus/run_chain.py
```

| # | Mutation | Must be caught by |
|---|---|---|
| 1 | drop `rotation.in_flight = zone_id` at the dispatch | Task 1's control and `test_two_zones_take_turns` — every own slot becomes a take-over |
| 2 | `if rotation.in_flight != zid:` instead of `== zid` | Task 2 |
| 3 | drop the `elif` branch entirely | Task 2 |
| 4 | `elif rotation.remaining[zid] >= 0:` instead of `> 0` | expected **survivor** — a zone at 0.0 is written off to 0.0 and the extra log line is the only difference; record it with that reason |
| 5 | move `rotation.in_flight = zone_id` to after the `await` | Task 2 must stay green and nothing else may break; if nothing catches it, record it as a survivor with the ordering argument from the spec |
| 6 | drop `self._drop_live_run_marker(zid)` | Task 5 |
| 7 | change the log wording to the sibling's `took it over while it waited` | Task 5 |

- [ ] **Step 2: Write the matrix to `mutations.json`**

One object per row: `{"n": 1, "mutation": "...", "result": "killed" | "survived", "killed_by": "...", "why_survived": "..."}`.

- [ ] **Step 3: Confirm the tree is clean afterwards**

```bash
cd /d/Entwicklung/HASI/issue45-work/wt && git status --short && git diff --stat
```

Expected: empty — every mutation reverted.

---

## After the plan

- **Rule P1:** this plan and its spec are already on `archive/design-history`; add the
  measured outcome (gate counters, mutation matrix) there before the branch is finished.
- **Nothing is pushed and no `gh` command runs** until the text has been shown in chat and
  released.
- The PR body should carry the sister-path finding from the spec — `_claim_chain_zones`
  keeps the classic rotation immune — because it is what explains why only one of the two
  rotations needed this.
