# Cumulative Flow-Volume Arming + Calibration Advisory — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Meter + early-stop totalizer flow sensors (unit-driven, no toggle) for linked-entity zones and distributor members together; log a distributor run that hit the cap short of target as `partial` (Review-M-1); and warn on consistent over/under-delivery of a can't-stop distributor member with a recommended throughput correction.

**Architecture:** Shared unit-classification helpers in the `irrigation.py` base (used by both the zone reader and the distributor); retire `DISTRIBUTOR_CUMULATIVE_METERING_ENABLED`; add a totalizer branch to the zone metered loop; pass `stopped_early` through the distributor sweep; add a per-member calibration sampler that raises an HA persistent notification.

**Tech Stack:** Python 3.12, Home Assistant custom integration, pytest.

**Canonical test command (repo root `D:\Entwicklung\HASI\HAsmartirrigation`):**
```bash
./.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock
```
Format: `uvx black <files>`, `uvx ruff check <files>`.

**Branch:** `local/cumulative-flow-volume` (created off `production`; spec already committed).

---

### Task 1: Shared totalizer helpers in the irrigation base

**Files:**
- Modify: `custom_components/smart_irrigation/irrigation.py` (after `_flow_rate_to_l_per_min`, ~line 584)
- Test: `tests/test_flow_units.py` (new)

- [ ] **Step 1: Write the failing test** — `tests/test_flow_units.py`:

```python
"""Shared flow-sensor unit classification (rate vs totalizer) + total→litres."""

from custom_components.smart_irrigation import SmartIrrigationCoordinator as C


def test_rate_units_are_not_totalizer():
    assert C._flow_is_totalizer("l/min", None) is False
    assert C._flow_is_totalizer("m³/h", "measurement") is False


def test_totalizer_by_unit_without_slash():
    assert C._flow_is_totalizer("m³", None) is True
    assert C._flow_is_totalizer("L", "measurement") is True


def test_totalizer_by_state_class_overrides():
    # a total_increasing counter is a totalizer even with an odd/empty unit
    assert C._flow_is_totalizer("", "total_increasing") is True
    assert C._flow_is_totalizer("l/min", "total_increasing") is True


def test_no_unit_no_total_class_is_rate_fallback():
    assert C._flow_is_totalizer("", None) is False
    assert C._flow_is_totalizer(None, None) is False


def test_litres_from_total_conversions():
    assert C._flow_litres_from_total(2.0, "m³") == 2000.0
    assert round(C._flow_litres_from_total(1.0, "gal"), 6) == 3.785412
    assert C._flow_litres_from_total(5.0, "L") == 5.0
```

- [ ] **Step 2: Run RED**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_flow_units.py -p _local_socket_unblock`
Expected: FAIL — `AttributeError: ... has no attribute '_flow_is_totalizer'`.

- [ ] **Step 3: Add the shared helpers**

In `irrigation.py`, immediately AFTER `_flow_rate_to_l_per_min` (which ends at line 584 with `return value  # assume L/min`), add:

```python
    @staticmethod
    def _flow_is_totalizer(unit: str, state_class: str | None) -> bool:
        """A flow sensor is a cumulative TOTALIZER (vs an instantaneous rate) when its
        state_class is total_increasing, or when it carries a non-empty unit without a
        '/' (a rate unit always contains '/'). No unit and no total_increasing → treat
        as a rate (the historical zone default) — a unit is the precondition for
        totalizer metering."""
        if state_class == "total_increasing":
            return True
        u = (unit or "").strip()
        return bool(u) and "/" not in u

    @staticmethod
    def _flow_litres_from_total(value: float, unit: str) -> float:
        """Convert a cumulative flow-counter reading to litres (m³×1000, gal×3.785,
        else assume litres). Mirrors _flow_rate_to_l_per_min's unit strings/factors."""
        u = (unit or "").lower().strip()
        if u in ("m³", "m3", "cubic meter", "cubic meters"):
            return float(value) * 1000.0
        if u in ("gal", "gallon", "gallons"):
            return float(value) * 3.785411784
        return float(value)  # L / l / liter(s) / unknown -> assume litres
```

- [ ] **Step 4: Run GREEN**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_flow_units.py -p _local_socket_unblock`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/irrigation.py tests/test_flow_units.py
git commit -m "feat(flow): shared rate-vs-totalizer detection + total→litres helpers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Retire the flag; rewire the distributor to the shared detection

**Files:**
- Modify: `custom_components/smart_irrigation/const.py:659-669` (remove flag)
- Modify: `custom_components/smart_irrigation/distributor.py:476-491` (remove local helpers), `:493-511` (`_dist_read_flow` returns state_class), `:513-579` (`_dist_measure_window`)
- Test: `tests/test_distributor.py` (update the 3 flag tests)

- [ ] **Step 1: Update the distributor cumulative tests to the retired-flag behaviour**

In `tests/test_distributor.py`, the three tests at ~:477/:518/:527 currently monkeypatch the flag. Change them so cumulative is active WITHOUT the flag:
- `test_measure_window_cumulative_counter` (:477): delete the `monkeypatch.setattr(const, "DISTRIBUTOR_CUMULATIVE_METERING_ENABLED", True)` line; the 100→106 counter must still yield `delivered == 6.0`.
- `test_measure_window_counter_reset_is_unreliable` (:518): delete the monkeypatch line; behaviour unchanged (reset → None).
- `test_measure_window_cumulative_disabled_falls_back_none` (:527): RENAME to `test_measure_window_no_unit_falls_back_to_rate` and assert that a totalizer-less sensor (no unit, `state_class` None) is metered as a RATE (not None). If the existing fixtures make this awkward, instead assert a cumulative counter is now metered by default (delivered > 0) — the point is: default behaviour is now armed.

(Also update the two helper tests at :461/:469 that call `_dist_flow_unit_is_rate`/`_dist_flow_litres_from_total` to call the new shared `_flow_is_totalizer`/`_flow_litres_from_total`.)

- [ ] **Step 2: Run RED**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_distributor.py -k "cumulative or flow" -p _local_socket_unblock`
Expected: FAIL (flag/helpers no longer as referenced).

- [ ] **Step 3: Remove the flag const**

In `const.py`, delete lines 661-669 (the `DISTRIBUTOR_CUMULATIVE_METERING_ENABLED` comment block + `= False`). Keep `DISTRIBUTOR_FLOW_POLL_SECONDS = 5` (line 660).

- [ ] **Step 4: Remove the local distributor helpers**

In `distributor.py`, delete `_dist_flow_unit_is_rate` (lines 476-480) and `_dist_flow_litres_from_total` (lines 482-491). Their callers now use the shared `self._flow_is_totalizer` / `self._flow_litres_from_total` from the base.

- [ ] **Step 5: `_dist_read_flow` returns state_class**

Change `_dist_read_flow` (distributor.py:493-511) to also return the sensor's `state_class`:

```python
        unit = (
            state.attributes.get("unit_of_measurement", "") if state.attributes else ""
        )
        state_class = (
            state.attributes.get("state_class") if state.attributes else None
        )
        return value, unit, state_class
```
(update the docstring's `-> (value, unit)` to `-> (value, unit, state_class)`.)

- [ ] **Step 6: Rewrite the `_dist_measure_window` detection + drop the gate**

In `_dist_measure_window`, replace the block from `reading = self._dist_read_flow(sensor)` through the `last = ...` seed (distributor.py:538-549) with:

```python
        reading = self._dist_read_flow(sensor)
        if reading is None:
            await self._dist_sleep(window)  # dead meter -> full window, time-based
            return None, window, False
        _, unit, state_class = reading
        is_rate = not self._flow_is_totalizer(unit, state_class)
        last = None if is_rate else self._flow_litres_from_total(reading[0], unit)
```
Then inside the poll loop, update the two reads to unpack the triple and use the shared converter:
- `val, u = r` (line 563) → `val, u, _ = r`
- the cumulative branch (line 567) `cur = self._dist_flow_litres_from_total(val, u)` → `cur = self._flow_litres_from_total(val, u)`

(The gate `if not is_rate and not const.DISTRIBUTOR_CUMULATIVE_METERING_ENABLED:` at lines 544-548 is DELETED — a totalizer is now metered directly. The rate branch at line 565 is unchanged.)

- [ ] **Step 7: Run GREEN + distributor regression**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_distributor.py tests/test_distributor_dispatch.py -p _local_socket_unblock`
Expected: all pass (cumulative now armed by unit; rate unchanged).

- [ ] **Step 8: Commit**

```bash
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -m "feat(distributor): arm cumulative metering by unit; retire the flag

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Zone-side totalizer support in the metered loop

**Files:**
- Modify: `custom_components/smart_irrigation/irrigation.py` — `_read_flow_increment` (586-607) becomes totalizer-aware and stateful; the loop in `_run_valve_metered` (695-742) seeds/holds `last_total`.
- Test: `tests/test_metered_run.py` (append)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_metered_run.py`:

```python
async def test_metered_zone_totalizer_credits_delta_and_early_stops(monkeypatch):
    # A totalizer flow_sensor (m³, total_increasing) advancing 10.000 -> 10.010 m³
    # = 10 L per step must credit the measured delta and stop at the target volume.
    # (Follow the file's existing metered-run fixture conventions for building the
    # coordinator + zone with a flow_sensor and a stubbed hass.states sequence.)
    ...


async def test_metered_zone_totalizer_reset_contributes_zero(monkeypatch):
    # A mid-run counter reset (cur < last) must contribute 0 for that step and
    # reseed the baseline, never a negative or huge credit.
    ...
```
Fill these in following the existing real-flow test (`test_metered_run.py:197`), swapping the sensor's unit to `m³` + `state_class="total_increasing"` and feeding a rising counter sequence via the same state stub the file already uses.

- [ ] **Step 2: Run RED** — `./.venv/Scripts/python.exe -m pytest tests/test_metered_run.py -k totalizer -p _local_socket_unblock` → FAIL (totalizer read as a rate → wrong litres).

- [ ] **Step 3: Make `_read_flow_increment` totalizer-aware + stateful**

Replace `_read_flow_increment` (irrigation.py:586-607) with a version that, for a totalizer, returns the delta since the last reading held on the coordinator, and for a rate integrates as before:

```python
    def _read_flow_increment(self, zone: dict, step_seconds: float) -> float:
        """Litres a real flow sensor reports as delivered over ``step_seconds``.

        A rate sensor (unit contains '/') is integrated over the step. A totalizer
        (state_class total_increasing, or a non-'/' unit) returns the delta since the
        previous reading, held per-zone on ``self._flow_last_total``; a reset/rollover
        (cur < last) contributes 0 and reseeds the baseline. Returns 0.0 (and logs) when
        the sensor is unavailable/non-numeric so a flaky tick contributes nothing."""
        flow_sensor = zone[const.ZONE_FLOW_SENSOR]
        state = self.hass.states.get(flow_sensor)
        if state is None or state.state in ("unavailable", "unknown"):
            _LOGGER.warning("Flow sensor '%s' unavailable", flow_sensor)
            return 0.0
        try:
            raw = float(state.state)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Flow sensor '%s' non-numeric state '%s'", flow_sensor, state.state
            )
            return 0.0
        attrs = state.attributes or {}
        unit = attrs.get("unit_of_measurement", "L/min")
        if not self._flow_is_totalizer(unit, attrs.get("state_class")):
            return self._flow_rate_to_l_per_min(raw, unit) * step_seconds / 60.0
        totals = getattr(self, "_flow_last_total", None)
        if totals is None:
            totals = self._flow_last_total = {}
        zid = int(zone[const.ZONE_ID])
        cur = self._flow_litres_from_total(raw, unit)
        last = totals.get(zid)
        totals[zid] = cur
        if last is None or cur < last:  # first reading or reset/rollover
            return 0.0
        return cur - last
```

- [ ] **Step 4: Clear the per-zone baseline at run start**

In `_run_valve_metered`, right after `stopped = False` (irrigation.py:699), drop any stale totalizer baseline so the first read of THIS run seeds fresh:

```python
        stopped = False
        # Totalizer runs hold a per-zone "last counter reading" across the poll loop;
        # clear it at run start so the first read seeds this run's baseline (and a
        # totalizer's first increment is 0, not a jump from a prior run's counter).
        totals = getattr(self, "_flow_last_total", None)
        if totals is not None:
            totals.pop(int(zone_id), None)
```

- [ ] **Step 5: Run GREEN + zone regression**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_metered_run.py tests/test_run_zone.py -p _local_socket_unblock`
Expected: all pass (rate path unchanged; totalizer credits deltas + early-stops).

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/irrigation.py tests/test_metered_run.py
git commit -m "feat(zones): meter totalizer flow sensors (delta) in the metered run loop

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Review-M-1 — distributor `partial` run-log

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py:1210-1216` (sweep)
- Test: `tests/test_distributor_dispatch.py` (append)

- [ ] **Step 1: Write the failing test** — append to `tests/test_distributor_dispatch.py` (mirror the existing `test_sweep_*` fixtures):

```python
async def test_sweep_logs_partial_when_cap_hit_without_target():
    # A classic member with a flow_sensor whose measured volume never reaches the
    # target before the cap must be recorded RUN_RESULT_PARTIAL, not COMPLETED.
    # (Stub _dist_measure_window to return (measured_below_target, cap, False).)
    ...


async def test_sweep_logs_completed_when_target_reached():
    # stopped_early True (target hit) -> COMPLETED.
    ...
```
Build these off the existing `test_sweep_classic_passes_target_and_extend_cap` (test_distributor_dispatch.py:1289): stub `c._dist_measure_window = AsyncMock(return_value=(5.0, 900, False))` (below target, ran to cap) and assert the recorded run result is `const.RUN_RESULT_PARTIAL`; a second test with `(target, 120, True)` asserts `RUN_RESULT_COMPLETED`.

- [ ] **Step 2: Run RED** — `./.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py -k partial_when_cap -p _local_socket_unblock` → FAIL (always COMPLETED today).

- [ ] **Step 3: Stop discarding `stopped_early` + derive the result**

In `_dist_run_sweep`, replace the call site (distributor.py:1210-1216):

```python
            measured, actual_seconds, stopped_early = await self._dist_measure_window(
                distributor, window, cap=cap, target=target
            )
            if water:
                # Review-M-1: a metered run that reached its cap WITHOUT reaching a set
                # target is a partial (under-)delivery, not a completion. Only mark it
                # when we actually measured (measured is not None); a time-based fallback
                # can't tell, so it stays COMPLETED.
                run_result = (
                    const.RUN_RESULT_PARTIAL
                    if (measured is not None and target is not None and not stopped_early)
                    else const.RUN_RESULT_COMPLETED
                )
                await self._dist_credit_zone(
                    zone,
                    actual_seconds,
                    measured_l=measured,
                    planned_seconds=window,
                    result=run_result,
                )
```

- [ ] **Step 4: Run GREEN + regression**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_distributor_dispatch.py tests/test_distributor.py -p _local_socket_unblock`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_dispatch.py
git commit -m "fix(distributor): log a cap-without-target member run as partial (Review-M-1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Calibration advisory for can't-stop distributor members

**Files:**
- Modify: `custom_components/smart_irrigation/store.py` (ZoneEntry: two additive fields), `custom_components/smart_irrigation/const.py` (result/keys), `custom_components/smart_irrigation/distributor.py` (new `_dist_flow_calibration_check` + sweep wiring)
- Test: `tests/test_flow_calibration.py` (new)

- [ ] **Step 1: Add the store fields (additive, no schema bump — mirror `observed_entity`)**

In `store.py` ZoneEntry (after `observed_entity`, ~line 226):

```python
    flow_calibration_samples = attr.ib(type=list, factory=list)
    flow_calibration_advised = attr.ib(type=bool, default=False)
```
Ensure the zone-load path tolerates the new keys exactly as it does for `observed_entity`/`run_log` (`.get(...)` with the attr default). No `STORAGE_VERSION` bump.

Add const keys in `const.py` (near the other ZONE_* keys):
```python
ZONE_FLOW_CAL_SAMPLES = "flow_calibration_samples"
ZONE_FLOW_CAL_ADVISED = "flow_calibration_advised"
FLOW_CAL_MIN_SAMPLES = 3
FLOW_CAL_MAX_SAMPLES = 5
FLOW_CAL_DEVIATION = 0.15
```

- [ ] **Step 2: Write the failing tests** — `tests/test_flow_calibration.py` (new):

```python
"""Per-member flow calibration advisory (persistent notification)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.smart_irrigation import SmartIrrigationCoordinator, const
from custom_components.smart_irrigation.distributor import DistributorMixin
from custom_components.smart_irrigation.irrigation import IrrigationRunnerMixin
from custom_components.smart_irrigation.master import MasterMixin
from custom_components.smart_irrigation.skip_conditions import SkipConditionsMixin


class _Host(DistributorMixin, MasterMixin, SkipConditionsMixin, IrrigationRunnerMixin):
    pass


def _host():
    c = _Host()
    c.hass = Mock()
    c.hass.services.async_call = AsyncMock()
    c.store = Mock()
    c.store.async_update_zone = AsyncMock()
    return c


def _zone(**kw):
    z = {const.ZONE_ID: 3, const.ZONE_NAME: "Beet", const.ZONE_THROUGHPUT: 10.0,
         const.ZONE_FLOW_CAL_SAMPLES: [], const.ZONE_FLOW_CAL_ADVISED: False}
    z.update(kw)
    return z


async def test_no_notify_below_min_samples():
    c = _host()
    z = _zone(**{const.ZONE_FLOW_CAL_SAMPLES: [{"measured_l": 12.0, "target_l": 10.0}]})
    await c._dist_flow_calibration_check(z, measured_l=13.0, target_l=10.0, seconds=60.0)
    c.hass.services.async_call.assert_not_awaited()  # only 2 samples


async def test_notify_when_mean_over_threshold():
    c = _host()
    z = _zone(**{const.ZONE_FLOW_CAL_SAMPLES: [
        {"measured_l": 13.0, "target_l": 10.0}, {"measured_l": 12.5, "target_l": 10.0}]})
    await c._dist_flow_calibration_check(z, measured_l=13.0, target_l=10.0, seconds=60.0)
    c.hass.services.async_call.assert_awaited()  # mean deviation ~28% > 15%
    args = c.hass.services.async_call.await_args.args
    assert args[0] == "persistent_notification" and args[1] == "create"


async def test_within_band_clears_advised():
    c = _host()
    z = _zone(advised=True, **{const.ZONE_FLOW_CAL_ADVISED: True,
        const.ZONE_FLOW_CAL_SAMPLES: [
            {"measured_l": 10.1, "target_l": 10.0}, {"measured_l": 9.9, "target_l": 10.0}]})
    await c._dist_flow_calibration_check(z, measured_l=10.0, target_l=10.0, seconds=60.0)
    # back in band -> dismiss + clear advised
    changes = c.store.async_update_zone.await_args.args[1]
    assert changes[const.ZONE_FLOW_CAL_ADVISED] is False
```
(Adjust helper kwargs to match the file's zone-dict conventions.)

- [ ] **Step 3: Run RED** — `./.venv/Scripts/python.exe -m pytest tests/test_flow_calibration.py -p _local_socket_unblock` → FAIL (`_dist_flow_calibration_check` missing).

- [ ] **Step 4: Implement `_dist_flow_calibration_check`**

Add to `DistributorMixin` (distributor.py, near `_dist_credit_zone`):

```python
    async def _dist_flow_calibration_check(
        self, zone: dict, measured_l: float, target_l: float, seconds: float
    ) -> None:
        """Advisory for a can't-stop member: append this run's measured-vs-target sample
        and, once >= FLOW_CAL_MIN_SAMPLES are collected, raise ONE HA persistent
        notification when the mean signed deviation exceeds FLOW_CAL_DEVIATION, with a
        recommended throughput = the observed flow (measured L / actual minutes). Self-
        clears (dismiss + reset the advised marker) once back within band."""
        if not target_l or measured_l is None or seconds <= 0:
            return
        zone_id = zone.get(const.ZONE_ID)
        samples = list(zone.get(const.ZONE_FLOW_CAL_SAMPLES) or [])
        samples.append({"measured_l": float(measured_l), "target_l": float(target_l)})
        samples = samples[-const.FLOW_CAL_MAX_SAMPLES:]
        advised = bool(zone.get(const.ZONE_FLOW_CAL_ADVISED))
        changes = {const.ZONE_FLOW_CAL_SAMPLES: samples}
        notif_id = f"smart_irrigation_flow_cal_{zone_id}"
        if len(samples) >= const.FLOW_CAL_MIN_SAMPLES:
            devs = [
                (s["measured_l"] - s["target_l"]) / s["target_l"]
                for s in samples
                if s.get("target_l")
            ]
            mean = sum(devs) / len(devs) if devs else 0.0
            if abs(mean) > const.FLOW_CAL_DEVIATION and not advised:
                rec_lpm = float(measured_l) / (float(seconds) / 60.0)
                direction = "over" if mean > 0 else "under"
                await self.hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "notification_id": notif_id,
                        "title": "Smart Irrigation: check flow rate",
                        "message": (
                            f"Zone '{zone.get(const.ZONE_NAME)}' is consistently "
                            f"{direction}-watering (~{abs(mean) * 100:.0f}% off target "
                            f"over {len(samples)} runs). Its valve can't stop early, so "
                            f"consider setting the configured throughput to about "
                            f"{rec_lpm:.1f} L/min (currently "
                            f"{float(zone.get(const.ZONE_THROUGHPUT) or 0):.1f})."
                        ),
                    },
                )
                changes[const.ZONE_FLOW_CAL_ADVISED] = True
            elif abs(mean) <= const.FLOW_CAL_DEVIATION and advised:
                await self.hass.services.async_call(
                    "persistent_notification", "dismiss", {"notification_id": notif_id}
                )
                changes[const.ZONE_FLOW_CAL_ADVISED] = False
        await self.store.async_update_zone(zone_id, changes)
```

- [ ] **Step 5: Wire it into the sweep**

In `_dist_run_sweep`, right after the `_dist_credit_zone` call added in Task 4 (distributor.py ~1216), add — using the `can_stop` and `tv` already computed at :1120-1126:

```python
                # Calibration advisory: only a can't-stop member with a reliable measured
                # volume and a positive target can drift silently (a can-stop member
                # early-stops at target; a time-based fallback can't be trusted here).
                if not can_stop and measured is not None and tv > 0:
                    await self._dist_flow_calibration_check(
                        zone, measured_l=measured, target_l=tv, seconds=actual_seconds
                    )
```
Note: `can_stop` and `tv` are computed at distributor.py:1119-1126 inside `if water:`; ensure this advisory call is within the same `if water:` scope (they are in-scope there). If `tv` is only assigned under `if water:`, guard the advisory with `if water:` too.

- [ ] **Step 6: Run GREEN + regression**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_flow_calibration.py tests/test_distributor_dispatch.py tests/test_store_distributor.py -p _local_socket_unblock`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add custom_components/smart_irrigation/store.py custom_components/smart_irrigation/const.py custom_components/smart_irrigation/distributor.py tests/test_flow_calibration.py
git commit -m "feat(distributor): calibration advisory for can't-stop members (persistent notification)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: i18n — flow-sensor help mentions totalizer support (8 languages)

**Files:**
- Modify: `custom_components/smart_irrigation/frontend/localize/languages/*.json` (the `distributor_flow_sensor` help + the zone `flow_sensor` tooltip)
- Rebuild: `frontend/dist/*` via `npm run build`

- [ ] **Step 1:** In each of the 8 language files, extend the flow-sensor help text to note that BOTH a rate sensor (e.g. `l/min`) and a cumulative totalizer (e.g. `m³`, `state_class: total_increasing`) are supported — detected automatically from the unit. Keep it one added clause; translate per language (en/de authoritative, then es/fr/it/nl/no/sk). Locate the keys with:
`grep -rn "flow_sensor" custom_components/smart_irrigation/frontend/localize/languages/en.json`

- [ ] **Step 2: Rebuild dist**

Run: `cd custom_components/smart_irrigation/frontend && npm run build` (lint + rollup).

- [ ] **Step 3: dist-freshness check**

Run: `cd custom_components/smart_irrigation/frontend && npm run build` again; `git diff --quiet -- custom_components/smart_irrigation/frontend/dist/` → must be clean.

- [ ] **Step 4: Commit**

```bash
git add custom_components/smart_irrigation/frontend/localize custom_components/smart_irrigation/frontend/dist -f
git commit -m "i18n: note totalizer flow-sensor support in the flow_sensor help (8 langs)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Full regression, format, REGEL-8 sister-path review, plan doc

- [ ] **Step 1: Format** — `uvx black custom_components/smart_irrigation/ tests/test_flow_units.py tests/test_flow_calibration.py` then `uvx ruff check custom_components/smart_irrigation/irrigation.py custom_components/smart_irrigation/distributor.py custom_components/smart_irrigation/const.py custom_components/smart_irrigation/store.py`.

- [ ] **Step 2: Full suite** — `./.venv/Scripts/python.exe -m pytest -p _local_socket_unblock`. Confirm the count matches the pre-existing green baseline (the known lingering-timer/HA-setup env errors in test_init/test_panel/test_watering_calendar/test_schedule_time_anchor are pre-existing — compare against `production`, not zero).

- [ ] **Step 3: REGEL-8 sister-path review** — read the full `_dist_measure_window`, `_read_flow_increment`/`_run_valve_metered`, the sweep credit+advisory block, and grep every `_dist_flow_unit_is_rate`/`_dist_flow_litres_from_total`/`DISTRIBUTOR_CUMULATIVE_METERING_ENABLED` reference to confirm none remain (`grep -rn` across `custom_components` + `tests`). Confirm the rate path is byte-unchanged and the totalizer path is symmetric zone-vs-distributor except the documented streaming-vs-one-shot reset handling.

- [ ] **Step 4: Commit fixups + the plan doc**

```bash
git add -A
git commit -m "docs: implementation plan for cumulative flow-volume arming + style

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## After all tasks
- Code review (code-reviewer subagent) over the full diff.
- **HA-Test live verification against the real totalizer meter** (the open hardware gate) — confirm measured crediting + early-stop + a partial log + the advisory notification, before the prod release.
- **Delivery (user-gated):** cherry-pick source onto `production` + version bump (all three) + dist rebuild; release notes shown for approval (REGEL 5). Design/plan docs → `archive/design-history`. Upstream (JustChr) PR: separate later decision.

## Self-Review (author checklist — completed)
- **Spec coverage:** shared helpers + state_class (T1) ✓; retire flag + distributor rewire (T2) ✓; zone totalizer (T3) ✓; M-1 distributor partial (T4) ✓; member calibration advisory + store fields (T5) ✓; i18n (T6) ✓; regression/REGEL-8 (T7) ✓.
- **Placeholder scan:** test bodies in T3/T4/T5 marked `...` are intentionally deferred to the file's existing fixture conventions with explicit construction notes; every implementation step shows full code.
- **Type consistency:** `_flow_is_totalizer(unit, state_class)` / `_flow_litres_from_total(value, unit)` used identically in T2/T3; `_dist_read_flow` triple unpacked in T2; `_dist_flow_calibration_check(zone, measured_l, target_l, seconds)` signature matches its sweep call in T5; new const keys (`ZONE_FLOW_CAL_*`, `FLOW_CAL_*`) defined in T5 and used in T5.
