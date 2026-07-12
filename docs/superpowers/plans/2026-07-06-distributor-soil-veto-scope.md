# Distributor soil-veto scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scope the distributor soil-moisture veto to the cycle's watering candidates (due + targeted) instead of the whole member ring, so a wet non-targeted/non-due member is left untouched.

**Architecture:** A local reorder in `_dist_run_sweep`'s scheduled (non-test, non-force) branch: build the watering candidates first (due, intersected with `only_zone_ids`), then veto ONLY those. Folds the old H5 subset filter into the pre-filter.

**Tech Stack:** Python 3.12 (local test env), Home Assistant custom integration, pytest.

**Spec:** `docs/superpowers/specs/2026-07-06-distributor-soil-veto-scope-design.md`

---

## Test environment (canonical local command)

From `D:\Entwicklung\HASI\HAsmartirrigation`:

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "<selector>" -q
```

## File structure

- **Modify** `custom_components/smart_irrigation/distributor.py` — `_dist_run_sweep` scheduled `else` branch (the `_apply_soil_moisture_veto(list(members))` + to_water + `only_zone_ids` filter block).
- **Modify** `tests/test_distributor_dispatch.py` — add 3 cycle-level scope tests near `test_cycle_only_zone_ids_waters_only_targeted_members`.

---

## Task 1: Scope the soil-veto to the cycle's watering candidates

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py` (scheduled `else` branch of `_dist_run_sweep`)
- Test: `tests/test_distributor_dispatch.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_distributor_dispatch.py` after `test_cycle_only_zone_ids_waters_only_targeted_members` (`_host`, `_dist`, `Mock`, `AsyncMock` are already imported):

```python
def _soil_members():
    return [
        {
            "id": 10 + i,
            "distributor_id": 0,
            "outlet_number": i + 1,
            "duration": 30,
            "bucket": -1,
            "bucket_threshold": 0,
            "state": "automatic",
        }
        for i in range(3)
    ]


def _soil_cycle_host():
    c = _host()
    c._dist_uses_master = Mock(return_value=False)  # bypass master entirely
    for m in (
        "_dist_persist_cycle",
        "_dist_open_inlet",
        "_dist_close_inlet",
        "_dist_credit_zone",
        "_dist_clear_cycle",
    ):
        setattr(c, m, AsyncMock())
    c._dist_advance = AsyncMock(side_effect=lambda did, cur, n: (cur % n) + 1)
    c._dist_sleep = AsyncMock()
    return c


async def test_soil_veto_scoped_to_target_subset():
    # Soil-veto scope (2026-07-06): a subset-targeted cycle must NOT pass a
    # non-targeted member to the veto — a wet member outside the target is left
    # untouched (re-anchored on its OWN cycle).
    c = _soil_cycle_host()
    c._dist_needs_water = Mock(return_value=True)  # all due
    seen = {}

    async def _veto(zs):
        seen["ids"] = [z.get("id") for z in zs]
        return zs  # dry -> all survive

    c._apply_soil_moisture_veto = _veto
    c.store.async_get_zones = AsyncMock(return_value=_soil_members())
    await c.async_run_distributor_cycle(
        _dist(id=0, current_outlet=1), only_zone_ids=[10]
    )
    assert seen["ids"] == [10]  # only the targeted member reached the veto; 11,12 untouched


async def test_soil_veto_skips_non_due_members():
    # Non-due members are not passed to the veto (matching the normal-zone path,
    # which vetoes only due zones) -> a non-due wet member is not re-anchored.
    c = _soil_cycle_host()
    c._dist_needs_water = Mock(side_effect=lambda z: z.get("id") == 10)  # only 10 due
    seen = {}

    async def _veto(zs):
        seen["ids"] = [z.get("id") for z in zs]
        return zs

    c._apply_soil_moisture_veto = _veto
    c.store.async_get_zones = AsyncMock(return_value=_soil_members())
    await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1))
    assert seen["ids"] == [10]  # non-due members 11,12 never reach the veto


async def test_soil_veto_drops_wet_targeted_member():
    # A targeted+due+WET member is vetoed: the veto drops it, so it isn't watered
    # (behaviour preserved through the reorder).
    c = _soil_cycle_host()
    c._dist_needs_water = Mock(return_value=True)

    async def _veto(zs):
        return [z for z in zs if z.get("id") != 11]  # member 11 is wet -> dropped

    c._apply_soil_moisture_veto = _veto
    c.store.async_get_zones = AsyncMock(return_value=_soil_members())
    ran = await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1))
    assert ran is True
    credited = {call.args[0].get("id") for call in c._dist_credit_zone.await_args_list}
    assert 11 not in credited  # wet member not watered
    assert credited == {10, 12}  # the dry targeted members watered
```

- [ ] **Step 2: Run them to verify they fail (2 RED, 1 already green)**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "test_soil_veto_scoped_to_target_subset or test_soil_veto_skips_non_due_members or test_soil_veto_drops_wet_targeted_member" -q
```
Expected: `test_soil_veto_scoped_to_target_subset` FAILS (current code passes `list(members)` = [10,11,12] to the veto, so `seen["ids"] == [10,11,12]`), `test_soil_veto_skips_non_due_members` FAILS (current passes all members, so seen == [10,11,12]), `test_soil_veto_drops_wet_targeted_member` PASSES (the veto's drop already excludes 11 on the current code).

- [ ] **Step 3: Implement the reorder**

In `custom_components/smart_irrigation/distributor.py`, replace the scheduled `else` branch block — currently:

```python
            survivors = await self._apply_soil_moisture_veto(list(members))
            survivor_ids = {m.get(const.ZONE_ID) for m in survivors}
            to_water = {
                m.get(const.ZONE_ID)
                for m in members
                if m.get(const.ZONE_ID) in survivor_ids and self._dist_needs_water(m)
            }
            if not to_water:
                return False

            # H5 (review #4): a schedule targeting a zone subset dispatches this
            # distributor if ANY member is in the subset; without this filter the
            # cycle would water ALL due members (Plan G's documented subset
            # limitation). Intersect `to_water` with the caller's target so a
            # subset run waters ONLY the targeted members — the non-targeted-but-
            # due members are then skip-pulsed in the sweep (the ring must still
            # advance through every outlet). Placed AFTER the first empty-guard so
            # a filter that removes everything returns False cleanly, and BEFORE
            # the pause/skip + master note-run below so we never arm the master
            # for an empty run.
            if only_zone_ids is not None:
                allow = {int(z) for z in only_zone_ids}
                to_water = {zid for zid in to_water if int(zid) in allow}
                if not to_water:
                    return False
```

with:

```python
            # Soil-veto scope (2026-07-06 design): apply the veto ONLY to the members
            # this cycle would actually water — due, intersected with the target subset
            # (only_zone_ids). A wet member that isn't this cycle's target OR isn't due
            # is left untouched (re-anchored on its OWN cycle), matching the normal-zone
            # path (_irrigate_linked_entities vetoes only due zones). This folds in the
            # old H5 subset filter: a subset run waters ONLY the targeted members; the
            # non-targeted-but-due members are then skip-pulsed in the sweep (the ring
            # must still advance through every outlet). Empty candidates / all-vetoed ->
            # return False cleanly before the master is armed.
            # siehe test_distributor_dispatch.py::test_soil_veto_scoped_to_target_subset
            allow = None if only_zone_ids is None else {int(z) for z in only_zone_ids}
            candidates = [
                m
                for m in members
                if self._dist_needs_water(m)
                and (allow is None or int(m.get(const.ZONE_ID)) in allow)
            ]
            survivors = await self._apply_soil_moisture_veto(candidates)
            to_water = {m.get(const.ZONE_ID) for m in survivors}
            if not to_water:
                return False
```

- [ ] **Step 4: Run the 3 tests to verify they pass**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "test_soil_veto_scoped_to_target_subset or test_soil_veto_skips_non_due_members or test_soil_veto_drops_wet_targeted_member" -q
```
Expected: all 3 PASS.

- [ ] **Step 5: Run the existing distributor cycle + subset + dispatch tests (no regression)**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_distributor_cycle.py tests/test_distributor_integration.py -q
```
Expected: PASS. In particular `test_cycle_only_zone_ids_waters_only_targeted_members`, `test_cycle_leading_skip_to_reach_later_due`, and `test_manual_single_target_advances_past_watered_outlet` (force path, unaffected) stay green.

- [ ] **Step 6: Format + full-suite regression + commit**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
"$OLD/uvenv312/Scripts/python.exe" -m black custom_components/smart_irrigation/distributor.py tests/test_distributor_dispatch.py
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -q 2>&1 | tail -3   # compare against baseline: no NEW failures
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_dispatch.py
git commit -F - <<'EOF'
fix(distributor): scope the soil-veto to the cycle's watering candidates

The scheduled distributor cycle vetoed the WHOLE member ring (re-anchor + skip-log
+ event) before the due/subset filter, so a wet non-targeted or non-due member was
re-anchored on an unrelated subset cycle. Reorder: build the watering candidates
first (due, intersected with only_zone_ids) and veto only those — matching the
normal-zone path. A wet member that isn't this cycle's target/due is left untouched
(re-anchored on its own cycle). Folds in the old H5 subset filter.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Self-review

- **Spec coverage:** scope decision (veto only due+targeted) → Step 3 reorder; effect on non-targeted/non-due members → tests 1 & 2; wet targeted member still vetoed → test 3; visibility (only vetoed members change, each skip-logged) → inherent in the scope (no code needed). All spec sections mapped.
- **Placeholders:** none — full test + implementation code, exact paths and commands.
- **Type/name consistency:** `only_zone_ids`, `allow`, `candidates`, `survivors`, `to_water`, `_dist_needs_water`, `_apply_soil_moisture_veto`, `const.ZONE_ID` all match the current code and each other; the 3 test names are referenced consistently in the plan and the docstring `siehe`.
