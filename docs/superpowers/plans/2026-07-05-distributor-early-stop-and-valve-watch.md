# Distributor early-stop + inlet-valve watch — Implementation Plan

> Execution: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** (4) end the watering cycle after the last due outlet instead of sweeping the full ring back to home; (5) opt-in per-distributor inlet-valve watch that advances the tracked position on a foreign pulse. Spec: `docs/superpowers/specs/2026-07-05-distributor-early-stop-and-valve-watch-design.md`.

**Tech Stack:** HA custom integration (Python), Lit/TS panel, pytest.

**Test env:**
```
S="C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad"
PYTHONPATH="$S" "$S/uvenv312/Scripts/python.exe" -m pytest <path> -p _local_socket_unblock -q
```

**Verified source (2026-07-05):** `distributor.py` `async_run_distributor_cycle` — `order` built at line 486-487, sweep loop `for i, zone in enumerate(order):` 490-585 (per-outlet: master note-run 527-548, persist/open/confirm/sleep(window)/credit/close 550-576, then pause block 578-585: persist-pausing, `_dist_master_window_off`, `_dist_sleep(pause)`, `current = _dist_advance(dist_id, current, n)`, `if i < n-1: _dist_master_window_on`), then `_dist_master_end` + `_dist_clear_cycle` 587-588. `distributor_cycle_estimate` 264-293. `DistributorEntry` in `store.py` (~331-369, 21 attr fields incl. `inlet_entity`, `current_outlet`, `active_cycle`, `position_state`). `_dist_store_update` fires `_distributor_updated` (I2). `async_upsert_distributor` create/update/delete (distributor.py ~661). Panel form `frontend/src/components/si-distributor-form.ts`; distributor type `frontend/src/types.ts:374-405`.

---

### Task E1: early-stop the sweep (Feature 4 core)

**Files:** `custom_components/smart_irrigation/distributor.py` (`async_run_distributor_cycle`). Test: `tests/test_distributor_cycle.py` (or `tests/test_distributor.py` — put it where the existing cycle tests live).

- [ ] **Step 1 — failing tests**
```python
# reuse the existing cycle-test host/fixtures (grep for a test that calls
# async_run_distributor_cycle with mocked _dist_open_inlet/_dist_sleep/_dist_advance).
async def test_cycle_stops_after_last_due_outlet():
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    for m in ("_dist_persist_cycle","_dist_open_inlet","_dist_close_inlet",
              "_dist_credit_zone","_dist_clear_cycle"):
        setattr(c, m, AsyncMock())
    advanced = []
    async def _adv(did, cur, n):
        nxt = (cur % n) + 1; advanced.append(nxt); return nxt
    c._dist_advance = AsyncMock(side_effect=_adv)
    c._dist_sleep = AsyncMock()
    c._apply_soil_moisture_veto = AsyncMock(side_effect=lambda z: z)
    # 6 outlets; only outlets 1 and 2 are due -> sweep must stop after outlet 2
    members = [
        {"id": 10+i, "distributor_id": 0, "outlet_number": i+1,
         "duration": 30 if i < 2 else 0, "bucket": -1, "bucket_threshold": 0,
         "state": "automatic"} for i in range(6)
    ]
    c.store.async_get_zones = AsyncMock(return_value=members)
    c._dist_needs_water = Mock(side_effect=lambda z: (z.get("duration") or 0) > 0)
    credited = []
    c._dist_credit_zone = AsyncMock(side_effect=lambda z, w: credited.append(z["outlet_number"]))
    await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1))
    assert credited == [1, 2]              # only the two due outlets watered
    assert advanced == [2]                 # exactly ONE advance (1->2); no return to home
    # opened the inlet exactly twice (outlets 1 and 2), never outlets 3-6
    assert c._dist_open_inlet.await_count == 2


async def test_cycle_leading_skip_to_reach_later_due():
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    for m in ("_dist_persist_cycle","_dist_open_inlet","_dist_close_inlet",
              "_dist_credit_zone","_dist_clear_cycle"):
        setattr(c, m, AsyncMock())
    c._dist_advance = AsyncMock(side_effect=lambda did, cur, n: (cur % n) + 1)
    c._dist_sleep = AsyncMock()
    c._apply_soil_moisture_veto = AsyncMock(side_effect=lambda z: z)
    # only outlet 3 due; outlets 1,2 must be skip-pulsed to reach it, then stop
    members = [
        {"id": 10+i, "distributor_id": 0, "outlet_number": i+1,
         "duration": 30 if i == 2 else 0, "bucket": -1, "bucket_threshold": 0,
         "state": "automatic"} for i in range(6)
    ]
    c.store.async_get_zones = AsyncMock(return_value=members)
    c._dist_needs_water = Mock(side_effect=lambda z: (z.get("duration") or 0) > 0)
    credited = []
    c._dist_credit_zone = AsyncMock(side_effect=lambda z, w: credited.append(z["outlet_number"]))
    await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1))
    assert credited == [3]                 # only outlet 3 watered
    assert c._dist_open_inlet.await_count == 3   # 1,2 skip-pulsed + 3 watered; stop (not 4,5,6)


async def test_test_run_still_sweeps_all_outlets():
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    for m in ("_dist_persist_cycle","_dist_open_inlet","_dist_close_inlet",
              "_dist_credit_zone","_dist_clear_cycle"):
        setattr(c, m, AsyncMock())
    c._dist_advance = AsyncMock(side_effect=lambda did, cur, n: (cur % n) + 1)
    c._dist_sleep = AsyncMock()
    members = [{"id": 10+i, "distributor_id": 0, "outlet_number": i+1,
                "duration": 0, "state": "automatic"} for i in range(6)]
    c.store.async_get_zones = AsyncMock(return_value=members)
    await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1), test_run=True)
    assert c._dist_open_inlet.await_count == 6    # test-run visits every outlet
```
> Read an existing `async_run_distributor_cycle` test first to match the exact host fixture (`_host`/`_dist`) and which leaf helpers must be mocked (persist/open/close/credit/clear/sleep/advance/soil-veto). Adjust the mocks to the real signatures. The assertions (credited outlets, advance count, open-inlet count) are the behavior to lock.

- [ ] **Step 2 — run, expect FAIL** (today it sweeps all 6 + advances 6×). Paste output.

- [ ] **Step 3 — implement** in `async_run_distributor_cycle`, after `order` is built (line 487) and `to_water` is known:
```python
        # Feature 4: end the sweep after the LAST due outlet. The ring only moves
        # forward and can't skip, so LEADING non-due outlets are still skip-pulsed
        # to reach a later due one; TRAILING non-due outlets (and the return to
        # home) are dropped. current_outlet is left at the last watered outlet;
        # the next cycle continues from there. Test-run visits every outlet.
        if test_run:
            sweep_len = n
        else:
            last_due = max(
                i for i in range(n) if order[i].get(const.ZONE_ID) in to_water
            )
            sweep_len = last_due + 1
```
Change the loop header to `for i, zone in enumerate(order[:sweep_len]):` and gate the pause/advance tail on `i < sweep_len - 1` (replace lines 578-585):
```python
            if i < sweep_len - 1:
                await self._dist_persist_cycle(
                    dist_id, current, const.DISTRIBUTOR_PHASE_PAUSING
                )
                await self._dist_master_window_off(distributor, concurrent)
                await self._dist_sleep(pause)
                current = await self._dist_advance(dist_id, current, n)
                await self._dist_master_window_on(distributor, concurrent)
```
(The old `if i < n - 1: _dist_master_window_on` is folded into this block — window_on only runs when we advance.) Everything else (master note, open/confirm/sleep/credit/close, `_dist_master_end`, `_dist_clear_cycle`) is unchanged.

- [ ] **Step 4 — run** the three tests + the full `tests/test_distributor.py tests/test_distributor_cycle.py tests/test_distributor_dispatch.py -q`. Existing cycle tests that asserted a full-ring sweep / return-to-home must be reconciled to early-stop (update expected advance/open counts; note each). The H5 `only_zone_ids` subset test and H7 master tests should still pass (a single-outlet run now stops right after that outlet — verify the master tests' open/advance counts and update if they assumed a full sweep). Paste summaries.

- [ ] **Step 5 — commit** `feat(distributor): end cycle after the last due outlet (early-stop)`

---

### Task E2: truncate the finish-anchor estimate to the early-stop sweep (Feature 4)

**Files:** `custom_components/smart_irrigation/distributor.py` (`distributor_cycle_estimate`). Test: `tests/test_distributor_dispatch.py`.

- [ ] **Step 1 — failing test**
```python
async def test_estimate_truncates_to_last_due_outlet():
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    # 6 members, only outlets 1 & 2 due (dur 30), 3-6 not due (dur 0)
    members = [{"id": 10+i, "distributor_id": 0, "outlet_number": i+1,
                "duration": 30 if i < 2 else 0} for i in range(6)]
    full_if_all = c.distributor_cycle_estimate(_dist(id=0, current_outlet=1), members)
    # only outlets 1&2 swept: 2 windows(30) + 1 pause + buffer — far less than
    # counting all 6 outlets' skip windows + 6 pauses
    only_two = [members[0], members[1]]
    assert c.distributor_cycle_estimate(_dist(id=0, current_outlet=1), members) < (
        c.distributor_cycle_estimate(_dist(id=0, current_outlet=1),
            members + [{"id": 99, "distributor_id": 0, "outlet_number": 7, "duration": 30}])
    )
    # concretely: with outlets 3-6 not due, the estimate must NOT include their
    # skip windows or pauses
    import math
    pause = 300  # _dist default pause_seconds (verify against _dist fixture)
    # sweep = outlets 1,2 => windows 30+30, pauses = 1 (k-1), + buffer
    # (settle omitted: _dist_uses_master mocked False)
    from custom_components.smart_irrigation import const as _c
    expected = 30 + 30 + 1 * pause + _c.DISTRIBUTOR_CYCLE_SAFETY_BUFFER_SECONDS
    assert c.distributor_cycle_estimate(_dist(id=0, current_outlet=1), members) == expected
```
> Verify the `_dist` fixture's `pause_seconds` (the plan assumes 300 default; the fixture may set a different value — read it and use the real number). Adjust `expected` accordingly. If `distributor_cycle_estimate` currently floors pause to `DISTRIBUTOR_MIN_PAUSE_SECONDS`, account for that.

- [ ] **Step 2 — run, expect FAIL** (current estimate counts all 6 outlets' windows + 6 pauses). Paste.

- [ ] **Step 3 — implement:** rework `distributor_cycle_estimate` to order from `current_outlet` and count only up to the last due outlet:
```python
    def distributor_cycle_estimate(self, distributor: dict, member_zones: list) -> float:
        """Deterministic wall-clock seconds for the (early-stop) sweep from the
        current position through the LAST due outlet — leading non-due outlets are
        skip-pulsed, trailing ones are not visited (Feature 4). Used to anchor
        finish-at schedules."""
        n = len(member_zones)
        if n == 0:
            return 0.0
        pause = max(int(distributor.get("pause_seconds") or 300),
                    const.DISTRIBUTOR_MIN_PAUSE_SECONDS)
        skip = max(int(distributor.get("skip_pulse_seconds") or 30),
                   const.DISTRIBUTOR_MIN_SKIP_PULSE_SECONDS)
        current = ((int(distributor.get("current_outlet") or 1) - 1) % n) + 1
        order = [member_zones[(current - 1 + k) % n] for k in range(n)]
        due_idx = [i for i in range(n) if float(order[i].get(const.ZONE_DURATION) or 0) > 0]
        if not due_idx:
            return 0.0
        k = due_idx[-1] + 1                     # outlets swept: current..last due
        windows = 0.0
        for z in order[:k]:
            dur = float(z.get(const.ZONE_DURATION) or 0)
            windows += dur if dur > 0 else skip
        total = windows + (k - 1) * pause
        if self._dist_uses_master(distributor) and self._dist_master_off_after():
            settle = float(getattr(self._master_cfg(), const.CONF_MASTER_SETTLE_SECONDS, 10) or 0)
            total += (k - 1) * settle
        return total + const.DISTRIBUTOR_CYCLE_SAFETY_BUFFER_SECONDS
```
> `member_zones` may be a subset (`in_scope`) from `get_total_irrigation_duration`; ordering by `(current-1+k)%n` over the passed list is a best-effort approximation consistent with the executor. The H2 caller passes the distributor's in-scope members; this keeps the same "estimate ≥ executed" tolerance.

- [ ] **Step 4 — run** `tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_schedule_time_anchor.py -q`. The G8/H2 estimate tests will need recomputed expected values (they used the all-outlets formula) — recompute by hand for the new truncated formula and update, noting each. No-distributor anchor tests stay byte-identical. Paste summaries.

- [ ] **Step 5 — commit** `fix(distributor): finish-anchor estimate follows the early-stop sweep`

---

### Task E3: `watch_inlet` store field (Feature 5)

**Files:** `custom_components/smart_irrigation/store.py` (`DistributorEntry`). Test: `tests/test_store_distributor.py`.

- [ ] **Step 1 — failing test:** create a distributor with `watch_inlet=True`, reload/`async_get_distributors`, assert it round-trips; a distributor created WITHOUT the key defaults to `False`. Mirror the existing DistributorEntry round-trip tests.
- [ ] **Step 2 — run FAIL** (`watch_inlet` not a field → dropped by the attrs allowlist).
- [ ] **Step 3 — implement:** add `watch_inlet = attr.ib(type=bool, default=False)` to `DistributorEntry` (next to `use_master`). No migration bump needed — the attrs allowlist drops unknown keys and applies the default for older saved distributors missing the key (mirror how `commissioning_confirmed`/`use_master` were added).
- [ ] **Step 4 — run** `tests/test_store_distributor.py tests/test_distributor.py -q` green.
- [ ] **Step 5 — commit** `feat(distributor): watch_inlet store field (opt-in inlet watch)`

---

### Task E4: inlet-watch listener + foreign-pulse advance (Feature 5)

**Files:** `custom_components/smart_irrigation/distributor.py` (listener lifecycle + handler); wired from setup + `async_upsert_distributor`. Test: `tests/test_distributor.py` / `tests/test_distributor_dispatch.py`.

Design: the coordinator holds `self._dist_inlet_watchers: dict[int, callable]` (distributor_id → unsub). A helper (re)registers per distributor based on `watch_inlet` + a state-observable `inlet_entity`.

- [ ] **Step 1 — failing tests** (unit-test the pure handler behavior; the HA `async_track_state_change_event` wiring is verified live):
```python
async def test_foreign_pulse_advances_when_idle():
    c = _host()
    c.store.get_distributor = Mock(return_value={
        "id": 0, "current_outlet": 2, "active_cycle": {}, "position_state": "synced"})
    c._dist_members = AsyncMock(return_value=[{"id": i} for i in range(6)])  # n=6
    c._dist_store_update = AsyncMock()
    await c._dist_on_inlet_pulse(0)            # off->on edge already decoded by caller
    # advanced 2 -> 3, persisted, stays synced
    c._dist_store_update.assert_awaited_once()
    args = c._dist_store_update.await_args.args
    assert args[0] == 0 and args[1]["current_outlet"] == 3


async def test_own_pulse_ignored_during_cycle():
    c = _host()
    c.store.get_distributor = Mock(return_value={
        "id": 0, "current_outlet": 2, "active_cycle": {"outlet": 2, "phase": "watering"}})
    c._dist_store_update = AsyncMock()
    await c._dist_on_inlet_pulse(0)
    c._dist_store_update.assert_not_awaited()   # HASI's own pulse -> ignored


async def test_foreign_pulse_wraps_at_n():
    c = _host()
    c.store.get_distributor = Mock(return_value={
        "id": 0, "current_outlet": 6, "active_cycle": {}, "position_state": "synced"})
    c._dist_members = AsyncMock(return_value=[{"id": i} for i in range(6)])
    c._dist_store_update = AsyncMock()
    await c._dist_on_inlet_pulse(0)
    assert c._dist_store_update.await_args.args[1]["current_outlet"] == 1   # wrap 6 -> 1
```
- [ ] **Step 2 — run FAIL** (`_dist_on_inlet_pulse` undefined).
- [ ] **Step 3 — implement:**
```python
    async def _dist_on_inlet_pulse(self, distributor_id) -> None:
        """A foreign inlet off->on pulse advanced the physical ring; keep our
        position in sync. Only counts when no HASI cycle is active (HASI pulses the
        inlet only during a cycle, which always has a non-empty active_cycle)."""
        dist = self.store.get_distributor(distributor_id)
        if dist is None or dist.get("active_cycle"):
            return
        members = await self._dist_members(distributor_id)
        n = len(members)
        if n == 0:
            return
        cur = int(dist.get("current_outlet") or 1)
        nxt = (cur % n) + 1
        await self._dist_store_update(distributor_id, {"current_outlet": nxt})

    @callback
    def _dist_inlet_state_listener(self, distributor_id):
        """Return a state-change handler that decodes an off->on edge and defers to
        _dist_on_inlet_pulse."""
        _OFF = {"off", "closed"}
        _ON = {"on", "open", "opening"}
        def _handler(event):
            old = event.data.get("old_state")
            new = event.data.get("new_state")
            if old is None or new is None:
                return
            if old.state in _OFF and new.state in _ON:
                self.hass.async_create_task(self._dist_on_inlet_pulse(distributor_id))
        return _handler

    def _dist_refresh_inlet_watch(self, distributor: dict) -> None:
        """(Re)register the inlet-state listener for a distributor per watch_inlet."""
        did = int(distributor.get("id"))
        watchers = getattr(self, "_dist_inlet_watchers", None)
        if watchers is None:
            watchers = self._dist_inlet_watchers = {}
        unsub = watchers.pop(did, None)
        if unsub:
            unsub()
        inlet = distributor.get("inlet_entity")
        if distributor.get("watch_inlet") and isinstance(inlet, str) and inlet:
            watchers[did] = async_track_state_change_event(
                self.hass, [inlet], self._dist_inlet_state_listener(did)
            )
```
Add `from homeassistant.helpers.event import async_track_state_change_event` and `callback` if missing. Wire it: in the coordinator's distributor setup (grep where `setup_SmartIrrigation_entities` replays distributors, or the coordinator's async_setup after distributors load), call `_dist_refresh_inlet_watch(d)` for each distributor; and in `async_upsert_distributor` after create/update call `_dist_refresh_inlet_watch(created_or_updated_dict)`, on delete pop+unsub the watcher. On integration unload, unsub all (add to the existing unload path).

- [ ] **Step 4 — run** the three handler tests + `tests/test_distributor.py tests/test_distributor_dispatch.py -q` green (the `_dist_store_update` firing `_distributor_updated` refreshes the `current_outlet` sensor automatically).
- [ ] **Step 5 — commit** `feat(distributor): opt-in inlet watch advances position on a foreign pulse`

---

### Task E5: panel `watch_inlet` toggle + i18n (Feature 5)

**Files:** `frontend/src/types.ts` (distributor type), `frontend/src/components/si-distributor-form.ts` (add the toggle + help note), `frontend/src/localize/languages/*.json` (8). Build: `npm run build`.

- [ ] **Step 1:** add `watch_inlet?: boolean;` to the `SmartIrrigationDistributor` type.
- [ ] **Step 2:** in `si-distributor-form.ts`, add a boolean toggle row "Einlass-Ventil auf Hand-Pulse überwachen" bound to `watch_inlet` (mirror the existing boolean rows in that form — e.g. how `use_master` used to be, or another `<ha-switch>`/checkbox row), emitting the same `distributor-changed` event. Add a help note that it only catches HA-observable actuation (not physical Gardena-lever pulses). Use i18n keys.
- [ ] **Step 3:** add the label + help i18n keys in all 8 language files (CRLF-canonical via Node). German label "Einlass-Ventil auf Hand-Pulse überwachen"; help "Erkennt nur Ventil-Schaltungen, die Home Assistant sieht — rein mechanische Pulse am Gerät bleiben unsichtbar."
- [ ] **Step 4:** `cd custom_components/smart_irrigation/frontend && npm run build` → EXIT 0; `npm test` green. Grep the new i18n keys across 8 files (each 1).
- [ ] **Step 5:** commit TS sources + translations (NOT dist) `feat(panel): watch_inlet toggle on the distributor form`

---

### Task REL: release b10
- [ ] Bump version ×3 (b9→b10). **REBUILD dist** (panel changed AND version bumped). `git add -f` the 3 bundles.
- [ ] `uvx black --check` clean; full distributor+entity+store+dispatch pytest green.
- [ ] Commit `build: release v2026.07.11b10`, push, show notes for approval, `gh release create v2026.07.11b10 --prerelease ...`.
- [ ] Verify on 192.168.10.196: a schedule with only early outlets due stops early (position stays mid-ring, no trailing skip-pulses); enabling `watch_inlet` + manually toggling the inlet in HA advances `current_outlet`.

---

## Self-review (done)
- **Spec coverage:** early-stop cycle (E1) + estimate (E2), watch_inlet field (E3) + listener/handler (E4) + panel/i18n (E5), release (REL). Both features covered.
- **Consistency:** E1 loop shape (k outlets, k-1 pauses/advances) matches E2 estimate `(k-1)*pause`; E4 ring-wrap `(cur % n)+1` matches E1/estimate ordering; `_dist_store_update` (E4) reuses the I2 signal so entities refresh.
- **No placeholders:** all code shown except the panel toggle (E5, mirror an existing boolean row) and i18n translations for nl/fr/it/es/sk/no (fill from the existing files' conventions).
