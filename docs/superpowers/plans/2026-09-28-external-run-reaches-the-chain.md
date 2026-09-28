# An external run reaches the chain — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A zone watered from outside the integration is no longer watered a second time by
the cycle that holds it, in either geometry.

**Architecture:** Two small pieces. `zone_run_in_flight` gains a fourth source, fed by the
instant observed watering already records (`_observed_on_since`) and bounded by the same
external-run ceiling the credit is capped at — that closes the window while the external
valve is open, at both turn sites at once. At the close edge, an external run past the
provenance line calls `_chain_drop_zone`, the helper a stop already uses, which reaches the
queue and the rotation remainder in every chain — that closes the window after it. Design:
`docs/superpowers/specs/2026-09-28-external-run-reaches-the-chain-design.md`.

**Tech Stack:** Python 3.12, Home Assistant custom component, pytest +
pytest-homeassistant-custom-component, `black`, `ruff`.

---

## Ground rules for every task

**Test command** (verbatim from the project `CLAUDE.md`; from a worktree there is no local
`.venv`, so the interpreter is named absolutely):

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock
```

**Worktree:** `/d/Entwicklung/HASI/issue64-work/wt`, branch
`fix-an-external-run-reaches-the-chain`, based on `upstream/master` = `6acfc819`.
`_local_socket_unblock.py` is already copied in.

**No tracker references in anything that goes upstream.** Code, comments, docstrings, test
names, test docstrings and commit messages carry no `Eifel-Joe#…`, no `#64`, and no
in-house shorthand (`spec`, `Task 4`, `Befund 3`). This plan and the design doc may name
them; nothing under `custom_components/` or `tests/` may. Task 8 greps for it, but the
grep is the second line of defence, not the first.

**Every task ends on a commit.** Attribution line:
`Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

---

## File structure

| File | Responsibility | Change |
|---|---|---|
| `custom_components/irrigation_plus/observed_watering.py` | watches linked valves, credits external runs | new ceiling helper; the open edge asks the narrow question; the close edge tells the cycle; a wrapper owns the deferred calculation |
| `custom_components/irrigation_plus/run_state.py` | the one answer to "is a run holding this zone?" | fourth source; the wide answer and the narrow one get separate names |
| `custom_components/irrigation_plus/const.py` | constants + their reasoning | `OBSERVED_SAMPLE_MIN_RUN_SECONDS` gains a second caller, so its comment gains it too |
| `tests/test_chain_sees_external_runs.py` | **new** — the four end-to-end cells and the counter-case | created in Task 3, extended in Task 6 |
| `tests/test_run_in_flight.py` | the predicate's own unit tests | two tests next to the existing self-closing bound test |
| `tests/test_observed_watering.py` | the observed module's unit tests | ceiling helper, the self-hit, the wrapper; three existing stubs re-pointed |

No file is split: `observed_watering.py` is 506 lines and `run_state.py` 190, both well
inside what this codebase keeps in one module, and both changes belong where the state they
read already lives.

---

## Task 1: Measure the discarded surplus

The design's severity claim is read from code, not yet measured: after an external credit
the cycle's own run is priced from the *old* bucket but may only credit up to
`max(target, pre)`, so the surplus the external water created is dropped instead of
carried. Two code sites say so (`irrigation.py:2789`, `self_closing.py:806-808`). Measure
it before writing any production code — if the clamp does not bite, the fix is still right
but the issue's severity is not.

**Files:**
- Create: `tests/probe_discarded_surplus.py` (a probe, not a suite member; moved to
  `docs/superpowers/probes/` in Task 9)

- [ ] **Step 1: Write the probe**

```python
"""Does the cycle's own run discard the surplus an external run created?

Measured on master 6acfc819: zone 1 watering, zone 2 queued, zone 2 watered
externally, then zone 1 finishes and zone 2 is dispatched anyway. The number in
question is the bucket that dispatch WRITES, against the bucket the water it
delivered would imply.
"""

from types import SimpleNamespace

from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.irrigation_plus import const

from tests.test_service_chain import (
    SEQUENTIAL,
    _coord,
    _dispatch,
    _finish,
    _register,
    _zone,
)


def _observed_zone(zone_id, duration=600):
    z = _zone(zone_id, duration=duration)
    z[const.ZONE_OBSERVED_ENTITY] = f"switch.external_{zone_id}"
    z[const.ZONE_SIZE] = 5.0
    z[const.ZONE_THROUGHPUT] = 3.1
    z[const.ZONE_MAXIMUM_DURATION] = 3600
    z[const.ZONE_FLOW_SENSOR] = None
    z[const.ZONE_BUCKET] = -20.0
    z[const.ZONE_IRRIGATION_TARGET_BUCKET] = 0
    return z


async def test_probe_the_surplus_the_second_run_writes(hass):
    c = _coord(hass, SEQUENTIAL)
    c.hass.config = SimpleNamespace(units=METRIC_SYSTEM)
    c._observed_on_since = {}
    c._observed_zone_by_entity = {}
    z1, z2 = _register(c, _observed_zone(1), _observed_zone(2))

    await _dispatch(c, [z1, z2])

    # The external run of zone 2, through the real credit path.
    await c._credit_observed_watering(2, 600)
    credited = c.async_write_watered_bucket.await_args.args[1]
    print(f"\n  external credit writes bucket: {credited:.3f}")

    # async_write_watered_bucket is a mock here, so apply what it was told to
    # write -- that is the store state the cycle's dispatch would read.
    c._zones[2][const.ZONE_BUCKET] = credited
    c.async_write_watered_bucket.reset_mock()

    await _finish(c, 1)

    print(f"  dispatched:                    {c._dispatched}")
    writes = [call.args for call in c.async_write_watered_bucket.await_args_list]
    print(f"  buckets the cycle's run wrote: {writes}")
    ceiling = c._run_ceiling(dict(c._zones[2], **{const.ZONE_BUCKET: credited}))
    print(f"  ceiling for that run:          {ceiling}")
    print(f"  pre + delivered depth:         {credited + 20.0:.3f}")
```

- [ ] **Step 2: Run it and record the numbers**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/probe_discarded_surplus.py -p _local_socket_unblock -s -q
```

Expected: the probe PASSES (it asserts nothing) and prints five lines. The claim holds if
the bucket the cycle's run writes is the ceiling (`0.0` or the target) while
`pre + delivered depth` is above it — the difference is the discarded surplus.

If `_run_ceiling` or the dispatch raises on a missing zone field, add the field to
`_observed_zone` (the production zones carry `irrigation_target_bucket: 0`) and note what
was needed; do not mock `_run_ceiling` — the clamp is the thing being measured.

- [ ] **Step 3: Write the measurement into the design doc**

Replace the "Read from the code, **not yet measured**" paragraph in
`docs/superpowers/specs/2026-09-28-external-run-reaches-the-chain-design.md` with the
measured numbers, or — if the clamp does not bite — with what actually happens, and stop
to report it before continuing.

- [ ] **Step 4: Do not commit anything here**

Neither the probe nor `docs/` is committed on this branch. Project rule P1 puts the design
history on `archive/design-history`, and a branch that adds documents and removes them
again carries their commit messages into the pull request for nothing. They stay untracked
in the worktree — untracked files are not part of the diff — until Task 9 copies them to
the archive.

---

## Task 2: One ceiling for both questions

`_observed_capped_seconds` already owns the policy "how long can an external open
plausibly be": the zone's `maximum_duration`, or the default when that is unusable, plus
`OBSERVED_CAP_MARGIN_SECONDS`. Task 3 needs the same number for a different question.
Lift it out first so there is one policy, not two that drift.

**Files:**
- Modify: `custom_components/irrigation_plus/observed_watering.py` (new helper before
  `_observed_capped_seconds` at line 286; its body at lines 320-323 and 338 now read from it)
- Test: `tests/test_observed_watering.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_observed_watering.py`:

```python
def test_the_external_run_ceiling_is_the_zones_own_maximum_plus_the_margin():
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    ceiling, substituted = coord._observed_run_ceiling_seconds(
        {const.ZONE_MAXIMUM_DURATION: 2700}
    )
    assert ceiling == 2730.0
    assert substituted is False


def test_a_zone_with_no_usable_maximum_gets_the_default_ceiling_not_none():
    """A non-positive maximum must not read as "no ceiling": that would hand a
    stuck-open valve back its unbounded credit on exactly the zones with nothing
    else to fall back on."""
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    for max_dur in (None, 0, -1):
        ceiling, substituted = coord._observed_run_ceiling_seconds(
            {const.ZONE_MAXIMUM_DURATION: max_dur}
        )
        assert ceiling == 3630.0, max_dur
        assert substituted is True, max_dur
```

- [ ] **Step 2: Run them to verify they fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -p _local_socket_unblock -q -k ceiling
```

Expected: 2 failed, `AttributeError: 'SmartIrrigationCoordinator' object has no attribute
'_observed_run_ceiling_seconds'`.

- [ ] **Step 3: Add the helper**

Insert directly above `def _observed_capped_seconds(` in
`custom_components/irrigation_plus/observed_watering.py`:

```python
    def _observed_run_ceiling_seconds(self, zone: dict) -> tuple[float, bool]:
        """The longest external open still plausible for this zone, and whether the
        zone's own ``maximum_duration`` had to be substituted to say so.

        One policy, two questions. :meth:`_observed_capped_seconds` bounds the seconds
        an external run may CREDIT; ``RunStateMixin._observed_run_in_flight`` bounds how
        long one may count as being IN FLIGHT. Both mean the same thing, so both read it
        here instead of each spelling out the fallback and drifting apart.

        A non-positive or absent ``maximum_duration`` falls back to the default ceiling
        rather than to "no ceiling" — see :meth:`_observed_capped_seconds` for why
        mirroring the calculation path's ``>= 0`` reading would be wrong here. The flag
        is returned rather than warned about, because only the crediting caller can say
        whether the substitution actually bound anything.
        """
        max_dur = zone.get(const.ZONE_MAXIMUM_DURATION)
        substituted = not max_dur or max_dur < 0
        if substituted:
            max_dur = const.CONF_DEFAULT_MAXIMUM_DURATION
        return float(max_dur) + const.OBSERVED_CAP_MARGIN_SECONDS, substituted
```

- [ ] **Step 4: Make `_observed_capped_seconds` read from it**

In `_observed_capped_seconds`, replace these four lines:

```python
        max_dur = zone.get(const.ZONE_MAXIMUM_DURATION)
        substituted = not max_dur or max_dur < 0
        if substituted:
            max_dur = const.CONF_DEFAULT_MAXIMUM_DURATION
        capped = min(float(seconds), float(max_dur) + const.OBSERVED_CAP_MARGIN_SECONDS)
```

with:

```python
        ceiling, substituted = self._observed_run_ceiling_seconds(zone)
        capped = min(float(seconds), ceiling)
```

Leave the warning block and `return capped` untouched.

- [ ] **Step 5: Run the new tests and the whole observed suite**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py tests/test_experimental_features.py -p _local_socket_unblock -q
```

Expected: the two new tests PASS and no previously passing test in either file fails. The
existing cap tests are the pin for this refactor — a green suite here is what says the
extraction changed no behaviour.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/observed_watering.py tests/test_observed_watering.py
git commit -m "refactor(observed): name the external-run ceiling once"
```

---

## Task 3: The guard at the zone's turn sees an open external run

**Files:**
- Modify: `custom_components/irrigation_plus/run_state.py` (module docstring; new
  `_observed_run_in_flight`; `zone_run_in_flight` split at line 132)
- Modify: `custom_components/irrigation_plus/observed_watering.py:138` (the open edge asks
  the narrow question)
- Modify: `tests/test_observed_watering.py:282`, `:514`, `:630` (stubs re-pointed)
- Test: `tests/test_run_in_flight.py`, `tests/test_chain_sees_external_runs.py` (new)

- [ ] **Step 1: Write the failing end-to-end tests**

Create `tests/test_chain_sees_external_runs.py`:

```python
"""A zone watered from outside the integration, while a cycle holds it.

Observed watering credits such a run at its close and registers nothing while it is
open, so both halves of the cycle's defence were blind to it: the guard at the zone's
turn asks whether a run is in flight and got False from an open valve, and the
write-off that catches a zone watered elsewhere runs off a finalisation an external
run never reaches.

Two windows, therefore two groups of tests below: the run still open when the turn
comes, and the run already closed. The counter-case matters as much as the two -- a
few seconds of hand-testing at the tap must NOT cost a zone its turn.
"""

from datetime import timedelta
from types import SimpleNamespace

from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.irrigation_plus import const

from tests.test_observed_watering import _state_event
from tests.test_service_chain import (
    ROTATING,
    SEQUENTIAL,
    _coord,
    _dispatch,
    _finish,
    _ids,
    _register,
    _zone,
)


def _observed_zone(zone_id, duration=600):
    """A service zone with an observed entity, a size and a throughput.

    The plain chain zone has no size or throughput, and without them the credit path
    returns before it books anything -- the tests would then pass on a code path that
    never ran.
    """
    z = _zone(zone_id, duration=duration)
    z[const.ZONE_OBSERVED_ENTITY] = f"switch.external_{zone_id}"
    z[const.ZONE_SIZE] = 5.0
    z[const.ZONE_THROUGHPUT] = 3.1
    z[const.ZONE_MAXIMUM_DURATION] = 3600
    z[const.ZONE_FLOW_SENSOR] = None
    z[const.ZONE_BUCKET] = -20.0
    return z


def _observer(hass, sequencing, slot=5):
    """A chain coordinator that also watches its zones' valves."""
    c = _coord(hass, sequencing, slot=slot)
    c.hass.config = SimpleNamespace(units=METRIC_SYSTEM)
    c._observed_on_since = {}
    c._si_driven_until = {}
    c._observed_zone_by_entity = {f"switch.external_{zid}": zid for zid in (1, 2)}
    return c


def _external_open(c, zone_id):
    c._observed_state_changed(
        _state_event(f"switch.external_{zone_id}", old="closed", new="open")
    )


async def _external_close(c, hass, zone_id, after_seconds):
    """Close the valve as if it had been open for ``after_seconds``."""
    c._observed_on_since[zone_id] = dt_util.utcnow() - timedelta(seconds=after_seconds)
    c._observed_state_changed(
        _state_event(f"switch.external_{zone_id}", old="open", new="closed")
    )
    await hass.async_block_till_done()  # the credit runs as a task


async def test_a_sequential_cycle_skips_a_zone_whose_valve_is_open_externally(hass):
    c = _observer(hass, SEQUENTIAL)
    z1, z2 = _register(c, _observed_zone(1), _observed_zone(2))
    await _dispatch(c, [z1, z2])
    assert _ids(c) == [1]

    _external_open(c, 2)
    assert c._observed_on_since.get(2) is not None  # the open edge tracked it
    assert c.zone_run_in_flight(2) is True

    await _finish(c, 1)

    assert 2 not in _ids(c), f"zone 2 was watered on top of an open valve: {c._dispatched}"


async def test_a_rotation_writes_off_a_zone_whose_valve_is_open_externally(hass):
    c = _observer(hass, ROTATING, slot=300)
    z1, z2 = _register(c, _observed_zone(1), _observed_zone(2))
    await _dispatch(c, [z1, z2])
    assert _ids(c) == [1]

    _external_open(c, 2)
    await _finish(c, 1)

    assert 2 not in _ids(c), f"zone 2 got a slot on top of an open valve: {c._dispatched}"
    rotation = c._chain_state(const.WATERING_MODE_SERVICE).rotation
    assert rotation.remaining[2] == 0.0
```

- [ ] **Step 2: Write the failing predicate tests**

In `tests/test_run_in_flight.py`, directly after
`test_self_closing_record_past_its_window_does_not_count`:

```python
def test_an_open_external_run_counts(monkeypatch):
    """Observed watering registers no run record, so this is the only state that says
    a valve nobody in here opened is currently watering the zone."""
    coord = _coord(monkeypatch)
    coord._observed_on_since = {1: dt_util.utcnow()}
    assert coord.zone_run_in_flight(1) is True
    assert coord.zone_run_in_flight(2) is False


def test_an_external_run_past_its_ceiling_does_not_count(monkeypatch):
    """Same reason the self-closing window is bounded: an entry that outlived its
    close edge must not block the zone for ever. A valve still reporting open past the
    longest plausible run for the zone is a broken report, not water."""
    coord = _coord(monkeypatch)
    # The zone's maximum_duration is 36000 s, so the ceiling is 36030 s.
    coord._observed_on_since = {
        1: dt_util.utcnow() - dt_util.dt.timedelta(seconds=36031)
    }
    assert coord.zone_run_in_flight(1) is False


def test_the_narrow_question_ignores_an_external_run(monkeypatch):
    """The two questions are not the same question. The observed open edge asks the
    narrow one -- did WE open this valve? -- and must get False for an external run,
    or it would suppress the tracking of the very runs it exists to track."""
    coord = _coord(monkeypatch)
    coord._observed_on_since = {1: dt_util.utcnow()}
    assert coord._si_run_in_flight(1) is False
    assert coord.zone_run_in_flight(1) is True
```

- [ ] **Step 3: Run both new files to verify they fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_sees_external_runs.py tests/test_run_in_flight.py -p _local_socket_unblock -q
```

Expected: the two chain tests FAIL on their assertion (`zone 2 was watered on top of an
open valve: [(1, 600.0), (2, 600.0)]`, and the rotation's `remaining[2] == 300.0`),
`test_an_open_external_run_counts` FAILS (`assert False is True`),
`test_the_narrow_question_ignores_an_external_run` FAILS with `AttributeError` on
`_si_run_in_flight`. `test_an_external_run_past_its_ceiling_does_not_count` **passes
already** — it cannot fail before the fourth source exists. Note it: it is load-bearing
only under mutation, and Task 7 must kill the "drop the ceiling comparison" mutant with
it.

- [ ] **Step 4: Add the fourth source**

In `custom_components/irrigation_plus/run_state.py`, add the method after
`_distributor_run_in_flight`:

```python
    def _observed_run_in_flight(self, zone_id: int) -> bool:
        """An external open this integration did not drive is holding the zone.

        The fourth actuation path, and the only one with no record of its own: observed
        watering credits an external run at its close and registers nothing, so the
        guard at a zone's turn answered False while the valve was open and the cycle
        watered it a second time. It needs no new store -- ``_observed_on_since``
        already holds the instant the external valve opened, which is exactly what "in
        flight" means here.

        Bounded, for the same reason :meth:`_self_closing_run_in_flight` is bounded: an
        entry that outlives its close edge must not block the zone for ever. Unbounded,
        one valve stuck reporting ``open`` would drop the zone from every cycle AND park
        its calculation (which gives way to a run in flight) with no way out. The bound
        is the zone's own external-run ceiling -- the same number its credit is capped
        at -- so a valve still reporting open past the longest plausible run for that
        zone reads as a broken report rather than as water.

        The reads are defensive because this runs on every ``zone_run_in_flight`` call,
        including on coordinators built with ``__new__`` in tests, where the attribute
        may be absent and ``store`` is often a Mock whose every attribute answers with
        another Mock.
        """
        since = getattr(self, "_observed_on_since", None)
        if not isinstance(since, dict):
            return False
        started = since.get(zone_id)
        if started is None:
            return False
        zone = self.store.get_zone(zone_id)
        ceiling, _substituted = self._observed_run_ceiling_seconds(
            zone if isinstance(zone, dict) else {}
        )
        return (dt_util.utcnow() - started).total_seconds() < ceiling
```

- [ ] **Step 5: Split the two questions**

Replace `zone_run_in_flight` (currently at line 132) with:

```python
    def _si_run_in_flight(self, zone_id) -> bool:
        """True while a run THIS INTEGRATION dispatched is holding the zone.

        Split out of :meth:`zone_run_in_flight` when external runs joined that answer.
        The two had been the same question, and one caller only ever meant this
        narrower one: observed watering asks, at a valve's open edge, whether the
        integration opened it, so it can leave its own runs to the runner. Pointed at
        the wider answer it would suppress the tracking of the very runs it is there to
        track, the moment its own tracking fed that answer.
        """
        try:
            zid = int(zone_id)
        except (TypeError, ValueError):
            return False
        return (
            self._classic_run_in_flight(zid)
            or self._self_closing_run_in_flight(zid)
            or self._distributor_run_in_flight(zid)
        )

    def zone_run_in_flight(self, zone_id) -> bool:
        """True while ANY actuation path is watering this zone, ours or not."""
        try:
            zid = int(zone_id)
        except (TypeError, ValueError):
            return False
        return self._si_run_in_flight(zid) or self._observed_run_in_flight(zid)
```

Also extend the module docstring's first paragraph: after
"``active_cycle`` for a member zone", add

```
and ``_observed_on_since`` for a run
nothing in here started (in memory, no record at all).
```

- [ ] **Step 6: Run the tests — and watch the self-hit appear**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_sees_external_runs.py tests/test_run_in_flight.py tests/test_observed_watering.py tests/test_experimental_features.py -p _local_socket_unblock -q
```

Expected: the two chain tests and all three predicate tests now PASS, **and**
`test_open_edge_starts_sampler_synchronously_for_flow_zone` and its two siblings in
`tests/test_observed_watering.py` now behave differently, because they stub
`coord.zone_run_in_flight` — a stub the open edge no longer calls. Record what breaks or
what silently keeps passing: that is the self-hit the next step removes by construction.

- [ ] **Step 7: Point the open edge at the narrow question**

In `custom_components/irrigation_plus/observed_watering.py`, line 138, replace:

```python
            if self.zone_run_in_flight(zone_id) or self.hass.loop.time() < (
```

with:

```python
            if self._si_run_in_flight(zone_id) or self.hass.loop.time() < (
```

and append to the comment block directly above it (after the "…active_cycle are live for
exactly that window too." line):

```python
            #
            # Deliberately the NARROW question. The wide one now also answers True for
            # an external run this module is itself tracking, so asking it here would
            # make an open valve look like ours and stop the tracking that credits it.
```

- [ ] **Step 8: Re-point the three stubs**

In `tests/test_observed_watering.py`, at lines 282, 514 and 630, replace

```python
    coord.zone_run_in_flight = Mock(return_value=False)
```

with

```python
    coord._si_run_in_flight = Mock(return_value=False)
```

Each of those lines already sits under a comment about the SI check; the name is the only
thing that changes, and it now names the method the code under test actually calls.

- [ ] **Step 9: Add the self-hit test**

Append to `tests/test_observed_watering.py`:

```python
async def test_the_open_edge_tracks_a_second_external_open_of_the_same_zone():
    """The in-flight answer now includes external runs, and this edge must not read
    its own tracking as a run of ours: a stale entry -- a close edge that never
    arrived -- would otherwise make every later external open of that zone invisible,
    silently and for good."""
    zone = {const.ZONE_ID: 2, const.ZONE_FLOW_SENSOR: None, const.ZONE_SIZE: 5.0}
    coord = _obs_coord([zone])
    coord._observed_zone_by_entity = {"valve.x": 2}
    coord._si_driven_until = {}
    coord.hass.loop.time = Mock(return_value=1000.0)
    coord._observed_on_since = {2: dt_util.utcnow()}  # a run we are already tracking

    coord._observed_state_changed(_state_event("valve.x", old="closed", new="open"))

    assert coord._observed_on_since.get(2) is not None
```

Add `from homeassistant.util import dt as dt_util` to that file's imports if it is not
there yet, and check that `_obs_coord` gives the coordinator a `hass.loop`; if not, build
the coordinator the way `test_open_edge_starts_sampler_synchronously_for_flow_zone` does.

- [ ] **Step 10: Run the four suites green**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_sees_external_runs.py tests/test_run_in_flight.py tests/test_observed_watering.py tests/test_experimental_features.py -p _local_socket_unblock -q
```

Expected: all pass, including the three re-pointed tests.

- [ ] **Step 11: Commit**

```bash
git add custom_components/irrigation_plus/run_state.py custom_components/irrigation_plus/observed_watering.py tests/test_run_in_flight.py tests/test_observed_watering.py tests/test_chain_sees_external_runs.py
git commit -m "fix(chain): an open external run holds the zone it is watering"
```

---

## Task 4: The external run owns the calculation it displaced

A calculation landing while a valve is open now gives way and is deferred, and every site
that picks a deferral back up is the teardown of a run the integration drove. An external
run is none of them, so without this the zone's duration stays as it was until its next
real run.

**Files:**
- Modify: `custom_components/irrigation_plus/observed_watering.py` (new
  `_observed_run_finished`; the close edge schedules it instead of the credit)
- Test: `tests/test_observed_watering.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_observed_watering.py`:

```python
async def test_an_external_run_picks_up_the_calculation_it_displaced():
    """The zone counted as in flight while the valve was open, so a calculation that
    landed in that window was deferred. Nothing else will pick it up: every other
    pick-up site is the teardown of a run this integration drove."""
    zone = {
        const.ZONE_ID: 2,
        const.ZONE_SIZE: 5.0,
        const.ZONE_THROUGHPUT: 3.0,
        const.ZONE_MAXIMUM_DURATION: 3600,
        const.ZONE_BUCKET: -10.0,
    }
    coord = _obs_coord([zone])
    coord.async_run_deferred_calculation = AsyncMock()

    await coord._observed_run_finished(2, 600)

    coord.async_run_deferred_calculation.assert_awaited_once_with(2)


async def test_the_calculation_is_picked_up_even_if_the_credit_raises():
    """The pick-up is teardown: a credit that dies on a store write must not also cost
    the zone its calculation."""
    coord = _obs_coord([{const.ZONE_ID: 2}])
    coord.async_run_deferred_calculation = AsyncMock()
    coord._credit_observed_watering = AsyncMock(side_effect=RuntimeError("store down"))

    with pytest.raises(RuntimeError):
        await coord._observed_run_finished(2, 600)

    coord.async_run_deferred_calculation.assert_awaited_once_with(2)


async def test_the_close_edge_schedules_the_finish_not_the_bare_credit():
    zone = {const.ZONE_ID: 2, const.ZONE_FLOW_SENSOR: None, const.ZONE_SIZE: 5.0}
    coord = _obs_coord([zone])
    coord._observed_zone_by_entity = {"valve.x": 2}
    coord._si_driven_until = {}
    coord.hass.loop.time = Mock(return_value=1000.0)
    coord.hass.async_create_task = Mock()
    coord._observed_run_finished = Mock(return_value="finish_coro")

    coord._observed_state_changed(_state_event("valve.x", old="closed", new="open"))
    coord._observed_state_changed(_state_event("valve.x", old="open", new="closed"))

    coord.hass.async_create_task.assert_called_once_with("finish_coro")
```

- [ ] **Step 2: Run them to verify they fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -p _local_socket_unblock -q -k "displaced or credit_raises or schedules_the_finish"
```

Expected: 3 failed, `AttributeError: … '_observed_run_finished'` on the first two and
`assert_called_once_with('finish_coro')` failing on the third.

- [ ] **Step 3: Add the wrapper**

Insert directly above `async def _credit_observed_watering(` in
`custom_components/irrigation_plus/observed_watering.py`:

```python
    async def _observed_run_finished(
        self,
        zone_id: int,
        seconds: float,
        measured_l: float | None = None,
        sensor_present: bool = False,
    ) -> None:
        """Credit an external run, then pick up the calculation it displaced.

        A calculation landing while a valve is open gives way and is deferred, and every
        site that picks a deferral back up is the teardown of a run this integration
        drove. An external run is none of them, so now that one counts as being in
        flight the deferral needs an owner here, or the zone's duration stays as it was
        until its next real run.

        In a ``finally`` because the pick-up is teardown: a credit that raises must not
        also cost the zone its calculation. The pick-up is a no-op unless something was
        actually deferred, and never propagates, so it is cheap on every external run.
        """
        try:
            await self._credit_observed_watering(
                zone_id,
                seconds,
                measured_l=measured_l,
                sensor_present=sensor_present,
            )
        finally:
            await self.async_run_deferred_calculation(zone_id)
```

- [ ] **Step 4: Schedule it from the close edge**

In `_observed_state_changed`, replace

```python
            self.hass.async_create_task(
                self._credit_observed_watering(
                    zone_id, seconds, measured_l=measured, sensor_present=sensor_present
                )
            )
```

with

```python
            self.hass.async_create_task(
                self._observed_run_finished(
                    zone_id, seconds, measured_l=measured, sensor_present=sensor_present
                )
            )
```

- [ ] **Step 5: Run the observed suites**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py tests/test_experimental_features.py tests/test_observed_distributor_members.py -p _local_socket_unblock -q
```

Expected: the three new tests PASS and nothing that passed before fails. The existing
close-edge tests assert only *that* a task was scheduled, so the swapped coroutine does
not disturb them — confirm that in the output rather than assuming it.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/observed_watering.py tests/test_observed_watering.py
git commit -m "fix(observed): an external run runs the calculation it displaced"
```

---

## Task 5: The cycle hears about a closed external run

**Files:**
- Modify: `custom_components/irrigation_plus/observed_watering.py` (the close edge tells
  the chain)
- Modify: `custom_components/irrigation_plus/const.py:928` (the constant's comment gains
  its second caller)
- Test: `tests/test_chain_sees_external_runs.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_chain_sees_external_runs.py`:

```python
async def test_a_sequential_cycle_drops_a_zone_watered_externally_before_its_turn(hass):
    """The guard at the turn cannot save this one: the close edge removed the very
    state it reads, so by the time the zone's turn arrives there is nothing to see."""
    c = _observer(hass, SEQUENTIAL)
    z1, z2 = _register(c, _observed_zone(1), _observed_zone(2))
    await _dispatch(c, [z1, z2])

    _external_open(c, 2)
    await _external_close(c, hass, 2, after_seconds=600)
    assert c.zone_run_in_flight(2) is False  # the open window is over

    await _finish(c, 1)

    assert 2 not in _ids(c), f"zone 2 was watered again after its own run: {c._dispatched}"


async def test_a_rotation_drops_a_zone_watered_externally_between_its_turns(hass):
    c = _observer(hass, ROTATING, slot=300)
    z1, z2 = _register(c, _observed_zone(1), _observed_zone(2))
    await _dispatch(c, [z1, z2])

    _external_open(c, 2)
    await _external_close(c, hass, 2, after_seconds=600)

    await _finish(c, 1)

    assert 2 not in _ids(c), f"zone 2 got another slot: {c._dispatched}"
    rotation = c._chain_state(const.WATERING_MODE_SERVICE).rotation
    assert rotation.remaining[2] == 0.0


async def test_a_few_seconds_of_hand_testing_keeps_the_zones_turn(hass):
    """Withholding a zone's whole turn is the worse error of the two: the water it
    skips is real, while the water a short open leaves unaccounted is bounded by the
    line itself. Below the provenance line the cycle carries on."""
    c = _observer(hass, SEQUENTIAL)
    z1, z2 = _register(c, _observed_zone(1), _observed_zone(2))
    await _dispatch(c, [z1, z2])

    _external_open(c, 2)
    await _external_close(c, hass, 2, after_seconds=72)

    await _finish(c, 1)

    assert (2, 600.0) in c._dispatched, f"zone 2 lost its turn to a 72 s open: {c._dispatched}"
```

- [ ] **Step 2: Run them to verify they fail**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_sees_external_runs.py -p _local_socket_unblock -q
```

Expected: the two write-off tests FAIL (`zone 2 was watered again after its own run:
[(1, 600.0), (2, 600.0)]`; `remaining[2] == 300.0`), and
`test_a_few_seconds_of_hand_testing_keeps_the_zones_turn` PASSES already. Note it: that
one exists to keep the next step from over-reaching, and Task 7 must kill the "drop the
provenance gate" mutant with it.

- [ ] **Step 3: Tell the chain at the close edge**

In `_observed_state_changed`, insert between the `seconds = …` line and the
`self.hass.async_create_task(` call:

```python
            # A cycle holding this zone has to hear about the run. Its queue entry --
            # or its rotation remainder -- outlives the external open, and the guard at
            # the zone's turn reads state this close edge has just removed, so by that
            # turn there is nothing left to see. Told here the way a stop tells it,
            # through the one helper that reaches every chain's queue AND remainder.
            #
            # Gated on the same provenance line the flow advisory uses, and for the
            # same reading of it: below that line an open is more likely someone
            # testing the valve than watering. Withholding a zone's whole turn for a
            # few seconds of hand-testing is the worse error of the two -- the water it
            # skips is real, while the water a short open leaves unaccounted is bounded
            # by the line itself.
            if seconds >= const.OBSERVED_SAMPLE_MIN_RUN_SECONDS:
                self._chain_drop_zone(zone_id)
```

- [ ] **Step 4: Give the constant its second caller in the comment**

In `custom_components/irrigation_plus/const.py`, the comment block above
`OBSERVED_SAMPLE_MIN_RUN_SECONDS` opens with "Shortest external open the observed path will
offer to the flow-calibration advisory." Replace that first sentence with:

```python
# Shortest external open the observed path treats as watering rather than as testing.
# Two callers read it: the flow-calibration advisory, which will not sample a shorter
# open, and the close edge, which will not take a zone out of a running cycle for one.
```

Leave the rest of the block as it stands — the provenance argument it already makes is the
argument both callers rest on.

- [ ] **Step 5: Run the chain file and the observed suites**

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_chain_sees_external_runs.py tests/test_observed_watering.py tests/test_experimental_features.py tests/test_service_chain.py -p _local_socket_unblock -q
```

Expected: all five new tests in the chain file PASS, and nothing in the three existing
suites regresses.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/observed_watering.py custom_components/irrigation_plus/const.py tests/test_chain_sees_external_runs.py
git commit -m "fix(chain): a zone watered elsewhere leaves the cycle that held it"
```

---

## Task 6: Sister paths

The predicate is read at nine sites. Task 3 changed what all of them see, and only two of
them were the target. Go through the rest and record, per site, whether the new answer is
right — this is the project's sister-path rule, and it is the step that finds the mirror
bug rather than shipping it.

**Files:** read-only pass, then whatever it turns up

- [ ] **Step 1: List the call sites and judge each one**

```bash
grep -rn "zone_run_in_flight\|_si_run_in_flight" custom_components/irrigation_plus/*.py
```

For each site, write one line in `docs/superpowers/plans/` (append to this plan under a
"Sister paths" heading): the site, what the wider answer now does there, and whether that
is wanted. The expected judgements, to be confirmed or overturned by reading:

| site | new behaviour | wanted? |
|---|---|---|
| `calculation.py:510` | a calculation during an external run is deferred | yes — and Task 4 gave the deferral its owner |
| `irrigation.py:1092` (scheduled dispatch) | a zone whose valve is open externally is skipped | yes |
| `irrigation.py:3413` (`run_zone` / Irrigate-now) | refused while the valve is open externally | yes — dispatching onto an open valve is the defect, not the guard |
| `batch.py:226` | the zone is left out of the batch plan | yes |
| `self_closing.py:695` | a second self-closing dispatch is refused | yes |
| `run_chain.py:367`, `:683` | the two targets of this work | yes |
| `run_state.py:183` | a deferred calculation stays deferred while the valve is open | yes |
| `observed_watering.py:138` | now asks the narrow question | Task 3 |

- [ ] **Step 2: Check the one structural sibling that does NOT ask**

```bash
grep -rn "zone_run_in_flight" custom_components/irrigation_plus/distributor.py
```

Expected: no output. The distributor sweep never asks, so an externally watered member
zone is invisible to it — the same defect one subsystem over. It is out of scope for this
branch (the design says so); record it for a separate issue with the grep result as
evidence. Do not widen this branch to cover it.

- [ ] **Step 3: Leave the record untracked**

It goes to the archive in Task 9 with the rest of `docs/`, not onto this branch. If reading
a site changed the code, that change is its own commit with its own test — a judgement that
turns into an edit is a defect found, not a note.

---

## Task 7: Gates

- [ ] **Step 1: Full suite**

```bash
cd /d/Entwicklung/HASI/issue64-work/wt && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q > /d/Entwicklung/HASI/issue64-work/branch-run.txt 2>&1; tail -4 /d/Entwicklung/HASI/issue64-work/branch-run.txt
```

- [ ] **Step 2: Diff the failure names against the baseline on this base**

```bash
cd /d/Entwicklung/HASI/issue64-work && grep -E "^(FAILED|ERROR) " branch-run.txt | sed 's/ - .*//' | sort -u > branch-names.txt; sort -u /d/Entwicklung/HASI/issue45-work/baseline-6acfc819.txt > baseline.sorted; diff baseline.sorted branch-names.txt && echo "NAMENS-DIFF LEER"; wc -l baseline.sorted branch-names.txt
```

Expected: `NAMENS-DIFF LEER` and both counts 374. The baseline was measured on this exact
base (`6acfc819`) last session; it does not need re-measuring while the base stands. A
non-empty diff is a regression, not a baseline problem — read it before touching anything.

- [ ] **Step 3: Lint (only these two count in CI)**

```bash
cd /d/Entwicklung/HASI/issue64-work/wt && uvx black custom_components/irrigation_plus/ && uvx ruff check custom_components/irrigation_plus/
```

Expected: `black` reformats nothing (or reformats, in which case re-run the suites) and
`ruff` reports `All checks passed!`.

- [ ] **Step 4: The three reference checks, on the added lines only**

```bash
cd /d/Entwicklung/HASI/issue64-work/wt && git diff upstream/master...HEAD -U0 -- custom_components tests | grep '^+' | grep -nEi "eifel-joe|issue ?#|befund|spec [A-Z0-9]|task [0-9]|➀|⑪" ; git log upstream/master..HEAD --format=%B | grep -nEi "eifel-joe|issue ?#|befund|spec [A-Z0-9]|task [0-9]" ; echo "--- alle drei ohne Ausgabe = sauber"
```

All three must print nothing (the third is the PR body, added in Task 9 and re-checked
there). `-U0` and the `^+` filter keep this to lines this branch added; context lines from
`master` are not ours to fix and would only hide a real hit in noise.

- [ ] **Step 5: Commit any formatting churn**

```bash
git add -A custom_components tests && git commit -m "style: black" || echo "nichts zu formatieren"
```

---

## Task 8: Mutation matrix

Every line this branch added must have a test that dies without it. Two tests in this plan
are known not to fail on `master` — the ceiling bound and the provenance gate — so the
matrix is the only thing that proves they are load-bearing.

**Files:**
- Create: `/d/Entwicklung/HASI/issue64-work/mutate.py` (adapted from the archived runner)

- [ ] **Step 1: Copy the runner and point it at this work**

```bash
cd /d/Entwicklung/HASI && git -C pr139-work/archive-wt show archive/design-history:docs/superpowers/probes/2026-09-28-rotating-take-over-mutations.py > issue64-work/mutate.py; head -20 issue64-work/mutate.py
```

Edit it: `WT = r"D:\Entwicklung\HASI\issue64-work\wt"`, one target file per mutation
(`run_state.py`, `observed_watering.py`, `const.py`), and

```python
SUITES = [
    "tests/test_chain_sees_external_runs.py",
    "tests/test_run_in_flight.py",
    "tests/test_observed_watering.py",
    "tests/test_experimental_features.py",
]
```

**Check the suite list against the files the tests actually live in before trusting a
single result.** A missing file in this list once turned a broken run into a clean-looking
"0 killed, 12 survived".

- [ ] **Step 2: Define the mutations — one per decision, not one per line**

| # | mutation | must be killed by |
|---|---|---|
| 1 | `_observed_run_in_flight` returns `False` unconditionally | the two window-1 chain tests, `test_an_open_external_run_counts` |
| 2 | drop the ceiling comparison (`return started is not None`) | `test_an_external_run_past_its_ceiling_does_not_count` |
| 3 | ceiling `<` becomes `<=` | nothing is expected to catch this; if nothing does, say so and why the boundary is unobservable, or add the test |
| 4 | `zone_run_in_flight` returns only `_si_run_in_flight(zid)` | the two window-1 chain tests |
| 5 | the open edge asks `zone_run_in_flight` again | `test_the_open_edge_tracks_a_second_external_open_of_the_same_zone` |
| 6 | `_si_run_in_flight` drops the distributor source | the existing `test_distributor_cycle_counts_for_its_members` |
| 7 | drop the `if seconds >= …` gate (always drop the zone) | `test_a_few_seconds_of_hand_testing_keeps_the_zones_turn` |
| 8 | invert the gate (`<`) | the two window-2 chain tests |
| 9 | `_chain_drop_zone(zone_id)` removed | the two window-2 chain tests |
| 10 | `finally:` becomes a plain trailing `await` | `test_the_calculation_is_picked_up_even_if_the_credit_raises` |
| 11 | `_observed_run_ceiling_seconds` returns `max_dur` without the margin | the two ceiling tests |
| 12 | `substituted` always `False` | the default-ceiling test |

- [ ] **Step 3: Run the matrix**

```bash
cd /d/Entwicklung/HASI/issue64-work/wt && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe /d/Entwicklung/HASI/issue64-work/mutate.py; /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -c "import json;d=json.load(open(r'D:/Entwicklung/HASI/issue64-work/mutations.json'));print(sum(1 for r in d if r['killed']),'killed /',len(d))"
```

- [ ] **Step 4: Read every survivor as a weak test first**

A survivor is a test that does not test what it claims, before it is a harmless mutation.
Both "documented survivor" arguments made last session were wrong and the review overturned
them. For each survivor: either add the assertion that kills it, or record the measurement
that shows the mutated code is behaviourally identical. An argument is not a measurement.

- [ ] **Step 5: Record the matrix**

Write the table with its outcomes to
`docs/superpowers/plans/2026-09-28-external-run-reaches-the-chain-mutations.md` and commit
it.

---

## Task 9: Live test, archive, PR text

- [ ] **Step 1: Live on HA-Test, announced first**

HA-Test is `192.168.10.196`, tools `mcp__HA-Test__…`; announce before any write, and never
route by guessing at a base URL. `custom_components/**` is read-only over MCP, so the build
has to reach the test instance the way it always does; zone fields are set through the
panel, not over MCP.

The run: a zone with an `observed_entity` inside a sequential cycle, its valve opened
externally for more than 300 s while the cycle holds it, then closed. Expected in the log:
`taking zone N out of the cycle` (or the rotation's write-off line) and **no** second run
of that zone. Capture the log lines and the zone's `run_log` entry.

- [ ] **Step 2: Archive the design history (project rule P1)**

The archive names probes by date, so the two scratch files are renamed on the way in:

```bash
cd /d/Entwicklung/HASI && cp issue64-work/wt/docs/superpowers/specs/2026-09-28-external-run-reaches-the-chain-design.md pr139-work/archive-wt/docs/superpowers/specs/; cp issue64-work/wt/docs/superpowers/plans/2026-09-28-external-run-reaches-the-chain*.md pr139-work/archive-wt/docs/superpowers/plans/; cp issue64-work/wt/tests/probe_discarded_surplus.py pr139-work/archive-wt/docs/superpowers/probes/2026-09-28-discarded-surplus-probe.py; cp issue64-work/mutate.py pr139-work/archive-wt/docs/superpowers/probes/2026-09-28-external-run-mutations.py; cd pr139-work/archive-wt && git add docs && git status --short
```

Read the `git status` list before committing — it must be exactly these four files:

```bash
cd /d/Entwicklung/HASI/pr139-work/archive-wt && git commit -m "docs: the external-run chain work, spec through matrix"
```

Then confirm the feature branch carries code and tests only. `docs/` and the probe are
untracked, so there is nothing to remove — verify rather than assume:

```bash
cd /d/Entwicklung/HASI/issue64-work/wt && git diff upstream/master...HEAD --name-only; echo "--- untracked:"; git status --short
```

Expected: the name list holds only paths under `custom_components/irrigation_plus/` and
`tests/`, and `docs/` plus `tests/probe_discarded_surplus.py` appear under untracked.

- [ ] **Step 3: Write the PR body to a file and show it in the chat for approval**

Nothing goes to GitHub without approval in the chat, corrections included. Re-run the
Task 7 Step 4 greps with the body file added as the third target. The body names: the
defect, both windows, the provenance line and what it leaves, the sister path that is NOT
in scope, and the measured numbers — with no reference to our tracker.

- [ ] **Step 4: Push and open the PR, after approval**

```bash
cd /d/Entwicklung/HASI/issue64-work/wt && git push -u origin fix-an-external-run-reaches-the-chain
gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix-an-external-run-reaches-the-chain --title "fix(chain): a zone watered outside the integration keeps no turn" --body-file /d/Entwicklung/HASI/issue64-work/pr-body.md
```

- [ ] **Step 5: Comment on our issue and pull the label along**

`Eifel-Joe#64` gets the outcome as a comment (in JustChr's words if he objects, not a
summary of them) and the `upstream:gemeldet` label in the same move. The tracking issue
`Eifel-Joe#42` gets the state change. Both after approval in the chat.
