# Gardena Distributor — Plan H: Plan G review fixes

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Fix all 15 confirmed findings from the adversarial review of Plan G (scheduler→distributor dispatch). Restore correct shared-master coordination, share the eligibility predicate between the finish-anchor estimate and the executor, dispatch distributors from the manual entry points too, and close the test-coverage gaps.

**Architecture:** Plan G's master-end rework (G2) over-corrected by *always* deferring the master shutdown to the shared deadline. That (a) never lets a concurrent run's short deadline be extended to cover the distributor's own longer sweep, and (b) leaves `_master_on=True` after a solo cycle so a back-to-back sibling never re-kicks. Plan H makes the deferral *conditional on real overlap* (`concurrent`), notes each cycle's own sweep length to the deadline, and recomputes `concurrent` per distributor.

**Tech Stack:** HA custom integration, Python 3.12/3.13, pytest + unittest.mock. Test host `_DistHost(DistributorMixin, MasterMixin, SkipConditionsMixin, IrrigationRunnerMixin)` in `tests/test_distributor.py`; `_host()`/`_dist()` fixtures; dispatch tests in `tests/test_distributor_dispatch.py`.

**Test env (verbatim):**
```
S="C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad"
PYTHONPATH="$S" "$S/uvenv312/Scripts/python.exe" -m pytest <path> -p _local_socket_unblock -q
```
Format with `uvx black`; keep `uvx black --check custom_components/smart_irrigation/` clean.

---

## Task H1: Master coordination — cover the sweep, finalize solo synchronously, recompute concurrent per-distributor

Fixes findings #1/#5 (critical), #2 (high), #6 (medium).

**Files:**
- Modify `custom_components/smart_irrigation/distributor.py`: `_dist_master_end` (216-226), `async_run_distributor_cycle` (416, 463), `_dispatch_distributor_cycles` (243-260).
- Test: `tests/test_distributor_dispatch.py`.

**Design:**
- `_dist_master_end(self, distributor, *, concurrent=False)`:
  - not uses_master → `self._master_on = False; return` (unchanged).
  - `concurrent` True (real overlap) → defer: `self._master_note_run(0); await self.async_master_schedule_off()` (G2 overlap-safe path — never stomps a pending run).
  - else (solo) → finalize synchronously so a sibling re-arms: if `_dist_master_off_after()` → `await self._master_turn(False)`; then `self._master_on = False`; `self._master_off_deadline = None`; cancel any pending `_master_off_cancel`.
- `async_run_distributor_cycle`: right after `await self._dist_master_start(distributor)` (line 416), register the sweep length so a concurrent deadline covers it:
  ```python
  if not test_run and self._dist_uses_master(distributor):
      self._master_note_run(self.distributor_cycle_estimate(distributor, members))
      await self.async_master_schedule_off()
  ```
  and pass `concurrent` to BOTH `_dist_master_end` calls (the confirm-fail path at 442 and the normal end at 463): `await self._dist_master_end(distributor, concurrent=concurrent)`.
- `_dispatch_distributor_cycles`: move `concurrent = self._distributor_concurrent()` from before the loop (243) to inside, immediately before the run call (per-distributor, reflects the live deadline):
  ```python
  await self.async_run_distributor_cycle(dist, concurrent=self._distributor_concurrent())
  ```

- [ ] **Step 1 — failing tests** (append to `tests/test_distributor_dispatch.py`):

```python
async def test_cycle_notes_sweep_estimate_to_master_deadline():
    """A concurrent run must extend the shared deadline to cover the whole sweep."""
    c = _host(master_entity="input_boolean.pump", master_off_after=True)
    # pretend a normal-zone run already claimed the master with a SHORT deadline
    import datetime
    c._master_off_deadline = c._master_now() + datetime.timedelta(seconds=5)
    c._master_on = True
    c._dist_persist_cycle = AsyncMock()
    c._dist_open_inlet = AsyncMock()
    c._dist_close_inlet = AsyncMock()
    c._dist_credit_zone = AsyncMock()
    c._dist_advance = AsyncMock(return_value=1)
    c._dist_clear_cycle = AsyncMock()
    c._dist_sleep = AsyncMock()
    c.store.async_get_zones = AsyncMock(return_value=[
        {"id": 7, "distributor_id": 0, "outlet_number": 1, "duration": 600,
         "bucket": -1, "bucket_threshold": 0, "state": "automatic"},
    ])
    c._apply_soil_moisture_veto = AsyncMock(side_effect=lambda z: z)
    before = c._master_off_deadline
    await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1), concurrent=True)
    # deadline extended to cover the ~600s+ sweep, not the stale 5s
    assert c._master_off_deadline is None or c._master_off_deadline > before


async def test_master_end_finalizes_synchronously_when_solo():
    c = _host(master_entity="input_boolean.pump", master_off_after=True)
    c._master_on = True
    c._master_off_deadline = c._master_now()          # no future overlap
    c._master_turn = AsyncMock()
    await c._dist_master_end(_dist(id=0), concurrent=False)
    c._master_turn.assert_awaited_once_with(False)     # solo powers off now
    assert c._master_on is False
    assert c._master_off_deadline is None


async def test_master_end_defers_when_concurrent():
    c = _host(master_entity="input_boolean.pump", master_off_after=True)
    c._master_on = True
    import datetime
    c._master_off_deadline = c._master_now() + datetime.timedelta(seconds=120)
    c._master_turn = AsyncMock()
    c.async_master_schedule_off = AsyncMock()
    await c._dist_master_end(_dist(id=0), concurrent=True)
    c._master_turn.assert_not_awaited()                # never stomp a pending run
    c.async_master_schedule_off.assert_awaited_once()
    assert c._master_on is True


async def test_dispatch_recomputes_concurrent_per_distributor():
    """concurrent is read per-distributor, not once before the loop."""
    c = _host()
    c._rain_delay_active = Mock(return_value=False)
    seen = []
    async def _run(dist, *, concurrent=False):
        seen.append(concurrent)
        return True
    c.async_run_distributor_cycle = AsyncMock(side_effect=_run)
    # first call sees a future deadline (True), second sees it cleared (False)
    import datetime
    states = [c._master_now() + datetime.timedelta(seconds=60), None]
    c._distributor_concurrent = Mock(side_effect=[True, False])
    c.store.async_get_distributors = AsyncMock(return_value=[_dist(id=0), _dist(id=1)])
    c._dist_members = AsyncMock(side_effect=lambda did: [{"id": 10 + did, "distributor_id": did}])
    c._dist_needs_water = Mock(return_value=True)
    await c._dispatch_distributor_cycles("all")
    assert seen == [True, False]
```

- [ ] **Step 2 — run, expect FAILs** (`_dist_master_end` has no `concurrent` kwarg; concurrent read once; no note-run at start). Paste output.
- [ ] **Step 3 — implement** the three changes above. Update the existing `_dist_master_end` tests from G2 (`test_master_end_defers_to_pending_deadline_not_immediate_off` and any master-end-coupled tests) to pass `concurrent=True` where they assert the deferral, and add/keep a solo variant. Grep `_dist_master_end(` in tests and reconcile.
- [ ] **Step 4 — run** `tests/test_distributor.py tests/test_distributor_dispatch.py -q`, all pass. Paste summary.
- [ ] **Step 5 — commit** `fix(distributor): master coordination covers own sweep + solo-synchronous end (review #1,#2,#5,#6)`

---

## Task H2: Finish-anchor estimate — share eligibility predicate + two-track reduction

Fixes findings #11 (high), #12 (medium).

**Files:**
- Modify `custom_components/smart_irrigation/distributor.py`: add `_dist_eligible_for_run(self, distributor, members) -> bool` (the static gates the executor uses) and refactor `_dispatch_distributor_cycles` to call it (single source of truth).
- Modify `custom_components/smart_irrigation/skip_conditions.py`: `get_total_irrigation_duration` — gate distributors by `_dist_eligible_for_run` and reduce distributors as a sequential track, `max`ed with the normal-zone track.
- Test: `tests/test_distributor_dispatch.py`.

**`_dist_eligible_for_run` (extract the shared gates; distributor.py, near `_dispatch_distributor_cycles`):**
```python
def _dist_eligible_for_run(self, distributor: dict, members: list) -> bool:
    """Static + demand gates shared by the dispatcher and the finish-anchor
    estimate, so both agree on whether a distributor will actually sweep."""
    if distributor.get("position_state") != const.POSITION_STATE_SYNCED:
        return False
    if not distributor.get("commissioning_confirmed"):
        return False
    if distributor.get("active_cycle"):
        return False
    if not members:
        return False
    return any(self._dist_needs_water(m) for m in members)
```
`_dispatch_distributor_cycles` replaces its inline gates (245-258) with this helper (keep the separate target-subset check).

**`get_total_irrigation_duration` (skip_conditions.py) — replace the distributor loop + reduction:**
```python
    normal = []
    for zone in zones:
        if zone.get(const.ZONE_STATE) not in (
            const.ZONE_STATE_AUTOMATIC, const.ZONE_STATE_MANUAL,
        ):
            continue
        if target is not None and int(zone.get(const.ZONE_ID)) not in target:
            continue
        if zone.get(const.ZONE_DISTRIBUTOR_ID) is not None:
            continue
        duration = zone.get(const.ZONE_DURATION, 0) or 0
        if duration > 0:
            normal.append(duration)

    dist_track = 0
    for dist in await self.store.async_get_distributors():
        members = await self._dist_members(dist.get("id"))
        in_scope = [m for m in members
                    if target is None or int(m.get(const.ZONE_ID)) in target]
        if not in_scope:
            continue
        if not self._dist_eligible_for_run(dist, members):
            continue
        # distributor cycles are dispatched strictly sequentially regardless of
        # zone_sequencing, so their estimates always sum.
        dist_track += int(self.distributor_cycle_estimate(dist, in_scope))

    if self.store.config.zone_sequencing == const.CONF_ZONE_SEQUENCING_PARALLEL:
        normal_track = max(normal) if normal else 0
    else:
        normal_track = sum(normal)
    # normal zones run as background tasks concurrently with the awaited
    # distributor dispatch, so wall-clock is the longer of the two tracks.
    total = max(normal_track, dist_track)
    return int(total)
```

- [ ] **Step 1 — failing tests** (append to `tests/test_distributor_dispatch.py`):
```python
async def test_estimate_skips_unsynced_distributor():
    c = _host()
    c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_SEQUENTIAL
    members = [{"id": 7, "distributor_id": 0, "outlet_number": 1,
                "duration": 60, "state": "automatic"}]
    c.store.async_get_zones = AsyncMock(return_value=members)
    c.store.async_get_distributors = AsyncMock(return_value=[
        _dist(id=0, position_state=const.POSITION_STATE_UNCERTAIN)])
    c._dist_members = AsyncMock(return_value=members)
    c._dist_needs_water = Mock(return_value=True)
    assert await c.get_total_irrigation_duration("all") == 0   # executor would skip it


async def test_estimate_distributor_track_sums_even_in_parallel():
    c = _host()
    c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_PARALLEL
    m0 = [{"id": 7, "distributor_id": 0, "outlet_number": 1, "duration": 30, "state": "automatic"}]
    m1 = [{"id": 8, "distributor_id": 1, "outlet_number": 1, "duration": 30, "state": "automatic"}]
    c.store.async_get_zones = AsyncMock(return_value=m0 + m1)
    c.store.async_get_distributors = AsyncMock(return_value=[_dist(id=0), _dist(id=1)])
    c._dist_members = AsyncMock(side_effect=lambda did: m0 if did == 0 else m1)
    c._dist_needs_water = Mock(return_value=True)
    e0 = int(c.distributor_cycle_estimate(_dist(id=0), m0))
    e1 = int(c.distributor_cycle_estimate(_dist(id=1), m1))
    # sequential dispatch → the two distributor estimates SUM even under parallel
    assert await c.get_total_irrigation_duration("all") == e0 + e1
```
- [ ] **Step 2 — run, expect FAIL** (current counts the unsynced distributor; parallel uses max). Paste.
- [ ] **Step 3 — implement** the helper + estimate rework.
- [ ] **Step 4 — regression:** run `tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_schedule_time_anchor.py -q`. The existing G8 tests (`test_total_duration_uses_distributor_cycle_estimate_not_raw_sum`, `test_total_duration_parallel_takes_max_over_distributor_and_zones`) may need their expected values updated to the two-track model — recompute by hand and update, noting it in the commit. No-distributor anchor tests must stay byte-identical.
- [ ] **Step 5 — commit** `fix(distributor): finish-anchor shares executor eligibility + sequential distributor track (review #11,#12)`

---

## Task H3: Manual entry points dispatch distributors

Fixes findings #7 (medium), #8 (medium), #9 (medium), #10 (low). User decision: ALL manual paths dispatch distributors.

**Files:**
- Modify `custom_components/smart_irrigation/irrigation.py`: `async_irrigate_now` (~1441-1486) and `async_run_zone` (~1488-1519).
- Test: `tests/test_distributor_dispatch.py` (host has `IrrigationRunnerMixin`).

**Changes:**
- `async_irrigate_now(zone_id=None)`:
  - Add the member guard to its candidate filter (mirror irrigation.py:462): `and z.get(const.ZONE_DISTRIBUTOR_ID) is None` (fixes #9 — a stray-linked-entity member is not driven directly).
  - After the normal run completes, dispatch distributors for the same target: build `target = "all" if zone_id is None else [zone_id]` and `await self._dispatch_distributor_cycles(target)`. Place it so it runs even when the normal candidate list is empty (i.e. NOT behind the early `return` at the empty-list branch). Document that manual dispatch respects rain delay (consistent with the dedicated `distributor_run_now` service).
- `async_run_zone(zone_id, duration)`: before the `if not zone.get(ZONE_LINKED_ENTITY)` no-op, add: if `zone.get(const.ZONE_DISTRIBUTOR_ID) is not None:` → `await self._dispatch_distributor_cycles([zone_id]); return`. Add a comment that the distributor uses the member's stored duration, not the custom `duration` (a documented limitation of routing a member run through its ring).

- [ ] **Step 1 — failing tests:**
```python
async def test_irrigate_now_dispatches_distributor_for_member_only():
    c = _host()
    c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_PARALLEL
    c._rain_delay_active = Mock(return_value=False)
    c._apply_soil_moisture_veto = AsyncMock(side_effect=lambda z: z)
    c._apply_live_durations = AsyncMock(side_effect=lambda z: z)
    c.async_master_begin_cycle = AsyncMock()
    c.async_master_schedule_off = AsyncMock()
    c._master_note_run = Mock()
    c._irrigate_zones_parallel = AsyncMock()
    c._sc_is_self_closing = Mock(return_value=False)
    c._dispatch_distributor_cycles = AsyncMock()
    member = {"id": 7, "distributor_id": 0, "outlet_number": 1, "duration": 30,
              "bucket": -1, "bucket_threshold": 0, "state": "automatic"}
    c.store.async_get_zones = AsyncMock(return_value=[member])
    await c.async_irrigate_now()                       # general "water all"
    c._dispatch_distributor_cycles.assert_awaited_once_with("all")


async def test_run_zone_routes_member_to_distributor():
    c = _host()
    c._dispatch_distributor_cycles = AsyncMock()
    member = {"id": 7, "distributor_id": 0, "duration": 30, "state": "automatic"}
    c.store.async_get_zones = AsyncMock(return_value=[member])
    # async_run_zone resolves the zone from the store; ensure it dispatches
    await c.async_run_zone(7, 120)
    c._dispatch_distributor_cycles.assert_awaited_once_with([7])
```
> Read `async_irrigate_now` / `async_run_zone` first to match how they resolve the zone and what they mock; adjust the mocks so only the dispatch behaviour is asserted. If `async_run_zone` looks the zone up differently, mock that lookup accordingly.
- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement.**
- [ ] **Step 4 — run** `tests/test_distributor.py tests/test_distributor_dispatch.py -q`, all pass (the G9 member-exclusion lock must still pass — the new member guard in `async_irrigate_now` reinforces it).
- [ ] **Step 5 — commit** `feat(distributor): manual irrigate-now / run-zone dispatch member zones (review #7,#8,#9,#10)`

---

## Task H4: Rain-delay double skip-log

Fixes finding #3 (low).

**Files:** `custom_components/smart_irrigation/distributor.py` `_dispatch_distributor_cycles` rain-delay pre-check (238-240). Test: `tests/test_distributor_dispatch.py`.

**Change:** the dispatcher must record a skipped run only for the MEMBER zones it owns (the linked-entity path already records the non-member zones), avoiding a duplicate entry for shared targets. Fetch the in-scope member ids and record those:
```python
if self._rain_delay_active():
    want_all = zone_ids is None or zone_ids == "all"
    target = None if want_all else {int(z) for z in zone_ids}
    member_ids = []
    for dist in await self.store.async_get_distributors():
        for m in await self._dist_members(dist.get("id")):
            zid = int(m.get(const.ZONE_ID))
            if target is None or zid in target:
                member_ids.append(zid)
    if member_ids:
        await self._record_skipped_run(member_ids, const.SKIP_REASON_PAUSED)
    return
```
- [ ] **Step 1 — failing test:** with rain delay active and a mixed target `[3, 10, 11]` (3 normal, 10/11 members of distributor 0), assert `_record_skipped_run` is awaited once with only the member ids `[10, 11]`.
- [ ] **Step 2 — run FAIL** (currently records the whole `zone_ids`).
- [ ] **Step 3 — implement.** Update the G6 test `test_dispatch_rain_delay_records_skip_and_runs_nothing` to the new member-scoped signature (it must still assert a skip is recorded and nothing runs; give distributor 0 a member so the record fires).
- [ ] **Step 4 — run** dispatch suite green.
- [ ] **Step 5 — commit** `fix(distributor): rain-delay skip-run records only member zones (review #3)`

---

## Task H5: Outlet-precise zone subset

Fixes finding #4 (low). Implements the "known limitation" from Plan G.

**Files:** `custom_components/smart_irrigation/distributor.py` `async_run_distributor_cycle` (add optional `only_zone_ids` filter) + `_dispatch_distributor_cycles` (pass the target). Test: `tests/test_distributor_dispatch.py`.

**Change:** `async_run_distributor_cycle(self, distributor, *, concurrent=False, test_run=False, only_zone_ids=None)`. When `only_zone_ids` is not None, intersect `to_water` with it so non-targeted-but-due members are skip-pulsed (still physically visited, but not watered/credited):
```python
if not test_run and only_zone_ids is not None:
    allow = {int(z) for z in only_zone_ids}
    to_water = {zid for zid in to_water if int(zid) in allow}
    if not to_water:
        return False
```
(place right after `to_water` is built, before the `if not to_water: return False` guard — or fold into it). In `_dispatch_distributor_cycles`, pass `only_zone_ids=None if target is None else list(target)`.

- [ ] **Step 1 — failing test:** distributor 0 members 10,11,12 all due; `_dispatch_distributor_cycles([10])`; spy on `_dist_credit_zone` (or on the `to_water` reaching the cycle) and assert only zone 10 is watered/credited, 11 and 12 are skip-pulsed. (Mock the inlet/sleep/persist helpers; let `async_run_distributor_cycle` run for real with `only_zone_ids`.)
- [ ] **Step 2 — run FAIL.**
- [ ] **Step 3 — implement.**
- [ ] **Step 4 — run** dispatch + distributor suites green; the G5 subset test (`test_dispatch_respects_target_subset`) still passes (it mocks `async_run_distributor_cycle`, so the new kwarg must be accepted — verify `assert_awaited` still matches or update to `await_args`).
- [ ] **Step 5 — commit** `feat(distributor): outlet-precise zone subset on scheduled dispatch (review #4)`

---

## Task H6: Close the remaining test-coverage gaps

Fixes findings #13 (medium), #14 (low), #15 (low).

**Files:** `tests/test_distributor_dispatch.py`, `tests/test_scheduler_distributor.py`.

- [ ] **#13** — solo-sequential propagates `concurrent=False`: with SEQUENTIAL sequencing, `_master_off_deadline=None`, one due synced+confirmed distributor, assert `async_run_distributor_cycle.await_args.kwargs["concurrent"] is False`. (Distinct from the existing PARALLEL→True test.)
- [ ] **#14** — add a naive-sum guard to `test_total_duration_parallel_takes_max_over_distributor_and_zones` (or its H2 successor): also `assert total != <naive per-member sum>` so deleting the member-exclusion at skip_conditions.py is caught by the parallel test too.
- [ ] **#15** — scheduler ordering: in `test_scheduled_irrigate_dispatches_distributors_even_when_no_normal_zone`, attach both coordinator mocks to a parent `Mock()` via `attach_mock` and assert `parent.mock_calls` has `_irrigate_linked_entities` BEFORE `_dispatch_distributor_cycles` (and `_reset_days_since_irrigation` last) using `assert_has_calls`.
- [ ] **Run** all four test files green. Commit `test(distributor): close review coverage gaps (review #13,#14,#15)`

---

## After H1-H6
- Final `uvx black --check` + full targeted suite green.
- superpowers:finishing-a-development-branch.
- Beta b7: bump version ×3 (manifest.json, const.py VERSION with `v`, frontend/package.json without `v`), rebuild `dist`, `git add -f` the 3 bundles, `black --check`, push, `gh release create` prerelease on Eifel-Joe/HAsmartirrigation. Re-verify on the test HA (192.168.10.196): a mixed schedule run with `master_off_after=True` and a multi-outlet sweep — confirm the master stays powered through the full sweep and the finish anchor lands on target.
