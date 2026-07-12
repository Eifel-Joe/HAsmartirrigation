# Distributor flow-volume Part B (early stop) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop a distributor member's watering at its metered target volume (JustChr zone scheme) — classic outlets may extend past the window up to the safety `maximum_duration`; self-closing-with-stop outlets stop early within the window; rate sensors only.

**Architecture:** `_dist_measure_window` gains a `cap` (time bound) and optional `target` (litres) and returns `(delivered, actual_seconds, stopped_early)`, breaking at the target. The sweep derives `target`/`cap` per outlet, notes the master at `cap` (Phase-1 terminal collapse brings it back to the real close), and credits the measured litres for the actual elapsed seconds. `_dist_credit_zone` credits a measured volume as gross depth (`_depth_from_volume_native`), fixing a Part A depth-fn inconsistency.

**Tech Stack:** Python 3.12, Home Assistant custom integration; JSON i18n (8 languages).

**Spec:** `docs/superpowers/specs/2026-07-07-distributor-flow-volume-part-b-design.md`

---

## Test env
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "<selector>" -q
```
black-format Python before committing. Commit via a Bash heredoc `git commit -F - <<'EOF' … EOF` — NEVER PowerShell.

## File structure
- `custom_components/smart_irrigation/distributor.py` — `_dist_credit_zone` (`:687`, depth-fn + planned/actual); `_dist_measure_window` (`:514`, tuple + cap + target); sweep derivation + master-note + credit wiring (`:926-1027`).
- `frontend/localize/languages/*.json` — `flow_sensor_help` early-stop note (8 langs).
- Tests: `tests/test_distributor.py` (credit + measure unit tests), `tests/test_distributor_dispatch.py` (sweep-level).

Reused (no change): `_metered_target_volume` (`irrigation.py:569`), `_zone_target_bucket` (`irrigation.py:64`), `_depth_from_volume_native` (`irrigation.py:1228`), `_credited_depth_native` (`irrigation.py:1245`), `ZONE_MAXIMUM_DURATION` (`const.py:289`), `DISTRIBUTOR_FLOW_POLL_SECONDS` (`const.py`), `WATERING_MODE_CLASSIC/SERVICE` (`const.py:540-541`).

---

## Task 1: `_dist_credit_zone` — gross depth for measured volume + planned/actual seconds

**Files:** Modify `distributor.py:687`; Test `tests/test_distributor.py`

- [ ] **Step 1: Update the two existing measured-credit tests + add new ones**

In `tests/test_distributor.py`, the existing `test_credit_zone_uses_measured_volume_when_given` mocks `_credited_depth_native` for the measured path — that is the bug being fixed. Replace it and add two tests:

```python
async def test_credit_zone_uses_measured_volume_when_given():
    c = _host()
    c.store.async_update_zone = AsyncMock()
    c._record_run = AsyncMock()
    c._depth_from_volume_native = Mock(return_value=1.0)  # measured -> GROSS depth
    c._credited_depth_native = Mock(return_value=999.0)   # must NOT be used
    c._timed_volume_l = Mock(return_value=999.0)          # must NOT be used
    z = {const.ZONE_ID: 7, const.ZONE_BUCKET: -5.0}
    await c._dist_credit_zone(z, 120, measured_l=8.0)
    c._timed_volume_l.assert_not_called()
    c._credited_depth_native.assert_not_called()
    c._depth_from_volume_native.assert_called_once_with(z, 8.0)
    assert c._record_run.await_args.kwargs["volume_l"] == 8.0


async def test_credit_zone_falls_back_to_timed_when_measured_none():
    c = _host()
    c.store.async_update_zone = AsyncMock()
    c._record_run = AsyncMock()
    c._credited_depth_native = Mock(return_value=1.0)     # timed -> multiplier-divided
    c._depth_from_volume_native = Mock(return_value=999.0)  # must NOT be used here
    c._timed_volume_l = Mock(return_value=4.0)
    z = {const.ZONE_ID: 7, const.ZONE_BUCKET: -5.0}
    await c._dist_credit_zone(z, 120, measured_l=None)
    c._timed_volume_l.assert_called_once()
    c._credited_depth_native.assert_called_once_with(z, 4.0)
    assert c._record_run.await_args.kwargs["volume_l"] == 4.0


async def test_credit_zone_records_planned_vs_actual_seconds():
    c = _host()
    c.store.async_update_zone = AsyncMock()
    c._record_run = AsyncMock()
    c._depth_from_volume_native = Mock(return_value=1.0)
    z = {const.ZONE_ID: 7, const.ZONE_BUCKET: -5.0}
    await c._dist_credit_zone(z, 45, measured_l=5.0, planned_seconds=120)
    kw = c._record_run.await_args.kwargs
    assert kw["planned_s"] == 120  # the plan was the full window
    assert kw["actual_s"] == 45    # early stop ran 45 s
```

- [ ] **Step 2: Run to verify failure**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "credit_zone_uses_measured or credit_zone_falls_back or credit_zone_records_planned" -q
```
Expected: FAIL (measured path still uses `_credited_depth_native`; `planned_seconds` kwarg unknown).

- [ ] **Step 3: Rewrite `_dist_credit_zone` (`distributor.py:687`)**

Replace the whole method with:
```python
    async def _dist_credit_zone(
        self, zone: dict, seconds: float, measured_l=None, planned_seconds=None
    ) -> None:
        """Credit a watered member zone's bucket and log the run.

        A metered (flow) volume credits the GROSS depth (_depth_from_volume_native),
        exactly like JustChr's real-flow zone runs — a measured volume carries no
        multiplier to divide out. The time-based fallback credits _timed_volume_l via
        _credited_depth_native (which divides out the zone multiplier that inflated the
        timed duration). ``seconds`` is the ACTUAL elapsed watering time (a Part B early
        stop can run less than the window, or a classic extend more); ``planned_seconds``
        (defaults to ``seconds``) is the originally planned window for the run log.
        """
        zone_id = zone.get(const.ZONE_ID)
        if measured_l is not None:
            volume_l = measured_l
            depth = self._depth_from_volume_native(zone, volume_l)
        else:
            volume_l = self._timed_volume_l(zone, seconds)
            depth = self._credited_depth_native(zone, volume_l)
        new_bucket = float(zone.get(const.ZONE_BUCKET) or 0) + depth
        ceiling = zone.get(const.ZONE_MAXIMUM_BUCKET)
        if ceiling is not None and new_bucket > float(ceiling):
            new_bucket = float(ceiling)
        await self.store.async_update_zone(zone_id, {const.ZONE_BUCKET: new_bucket})
        await self._record_run(
            zone_id,
            result=const.RUN_RESULT_COMPLETED,
            volume_l=volume_l,
            planned_s=planned_seconds if planned_seconds is not None else seconds,
            actual_s=seconds,
            trigger=const.RUN_TRIGGER_DISTRIBUTOR,
            add_to_total=True,
        )
```

- [ ] **Step 4: Run the credit tests + the full distributor suite**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_distributor_cycle.py -q
```
Expected: PASS. (The sweep still calls `_dist_credit_zone(zone, window, measured_l=measured)` — a 3-arg call, unaffected by the new optional `planned_seconds`.)

- [ ] **Step 5: black + commit**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
"$OLD/uvenv312/Scripts/python.exe" -m black custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git add custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -F - <<'EOF'
fix(distributor): credit measured volume as gross depth; log planned vs actual seconds

_dist_credit_zone now credits a measured (flow) volume via _depth_from_volume_native
(gross), matching JustChr's real-flow zone crediting, instead of _credited_depth_native
(which divides out the zone multiplier — correct only for the timed fallback). This
fixes an under/over-credit for members with multiplier != 1 that Part A introduced.
It also takes an optional planned_seconds so an early-stopped/extended run logs the
planned window and the actual elapsed time separately.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 2: `_dist_measure_window` — tuple return + `cap` + `target` early stop

**Files:** Modify `distributor.py:514` (+ the sweep call at `:1024`); Test `tests/test_distributor.py`

- [ ] **Step 1: Update the existing Part A measure tests to unpack the tuple, add early-stop tests**

The existing measure tests assert a scalar return. Update all six to unpack `(measured, _, _)`, and add four early-stop tests. Replace the block from `async def test_measure_window_cumulative_counter` through `test_measure_window_cumulative_disabled_falls_back_none` with:

```python
async def test_measure_window_cumulative_counter(monkeypatch):
    monkeypatch.setattr(const, "DISTRIBUTOR_CUMULATIVE_METERING_ENABLED", True)
    c, d = _flow_host()
    vals = iter([100.0, 102.0, 104.0, 106.0])
    c.hass.states.get = Mock(side_effect=lambda s: _state(next(vals), "L"))
    measured, actual, stopped = await c._dist_measure_window(d, 15)
    assert measured == 6.0
    assert actual == 15
    assert stopped is False


async def test_measure_window_rate_sensor():
    c, d = _flow_host()
    c.hass.states.get = Mock(return_value=_state(12.0, "L/min"))
    measured, actual, stopped = await c._dist_measure_window(d, 60)
    assert round(measured, 3) == 12.0
    assert actual == 60
    assert stopped is False


async def test_measure_window_no_sensor_returns_none():
    c = _host()
    c._dist_sleep = AsyncMock()
    measured, actual, stopped = await c._dist_measure_window(_dist(flow_sensor=None), 30)
    assert measured is None
    assert actual == 30
    assert stopped is False
    c._dist_sleep.assert_awaited_once_with(30)


async def test_measure_window_unavailable_falls_back_none():
    c, d = _flow_host()
    c.hass.states.get = Mock(return_value=None)
    measured, actual, stopped = await c._dist_measure_window(d, 30)
    assert measured is None
    assert actual == 30
    c._dist_sleep.assert_awaited_once_with(30)


async def test_measure_window_counter_reset_is_unreliable(monkeypatch):
    monkeypatch.setattr(const, "DISTRIBUTOR_CUMULATIVE_METERING_ENABLED", True)
    c, d = _flow_host()
    vals = iter([100.0, 102.0, 5.0, 7.0])
    c.hass.states.get = Mock(side_effect=lambda s: _state(next(vals), "L"))
    measured, _, _ = await c._dist_measure_window(d, 15)
    assert measured is None


async def test_measure_window_cumulative_disabled_falls_back_none():
    c, d = _flow_host()
    c.hass.states.get = Mock(return_value=_state(100.0, "L"))
    measured, actual, stopped = await c._dist_measure_window(d, 30)
    assert measured is None
    assert actual == 30
    c._dist_sleep.assert_awaited_once_with(30)


async def test_measure_window_early_stops_at_target():
    # 60 L/min == 1 L/s; target 30 L reached at 30 s (< 60 s cap)
    c, d = _flow_host()
    c.hass.states.get = Mock(return_value=_state(60.0, "L/min"))
    measured, actual, stopped = await c._dist_measure_window(d, 60, target=30.0)
    assert stopped is True
    assert actual == 30
    assert round(measured, 3) == 30.0


async def test_measure_window_classic_extend_past_window():
    # 30 L/min == 0.5 L/s; target 30 L needs 60 s — past the 30 s window, within 120 s cap
    c, d = _flow_host()
    c.hass.states.get = Mock(return_value=_state(30.0, "L/min"))
    measured, actual, stopped = await c._dist_measure_window(d, 30, cap=120, target=30.0)
    assert stopped is True
    assert actual == 60  # ran past the 30 s window
    assert round(measured, 3) == 30.0


async def test_measure_window_target_not_reached_runs_to_cap():
    # 60 L/min for a 30 s cap delivers 30 L < 100 L target -> full cap, no early stop
    c, d = _flow_host()
    c.hass.states.get = Mock(return_value=_state(60.0, "L/min"))
    measured, actual, stopped = await c._dist_measure_window(d, 30, target=100.0)
    assert stopped is False
    assert actual == 30
    assert round(measured, 3) == 30.0


async def test_measure_window_dead_sensor_sleeps_window_not_cap():
    # A classic-extend call passes cap=1200 but a dead sensor must sleep only the
    # window (30) so a dead meter never extends the run.
    c, d = _flow_host()
    c.hass.states.get = Mock(return_value=None)
    measured, actual, stopped = await c._dist_measure_window(d, 30, cap=1200, target=50.0)
    assert measured is None
    assert actual == 30
    c._dist_sleep.assert_awaited_once_with(30)
```

- [ ] **Step 2: Run to verify failure**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "measure_window" -q
```
Expected: FAIL (method returns a scalar, not a tuple; no `cap`/`target` params).

- [ ] **Step 3: Rewrite `_dist_measure_window` (`distributor.py:514`)**

```python
    async def _dist_measure_window(
        self, distributor: dict, window: float, *, cap=None, target=None
    ):
        """Sleep the outlet's window (or up to ``cap`` when early-stopping) and, if the
        distributor has a rate flow_sensor, meter the delivered litres. Returns a tuple
        ``(delivered, actual_seconds, stopped_early)``:

        - ``delivered`` — measured litres, or None to fall back to time-based crediting
          (no sensor / unreliable / a cumulative counter while metering is dormant).
        - ``actual_seconds`` — time actually elapsed (== ``window`` on any non-metering
          path; < ``cap`` when a ``target`` is hit; == ``cap`` at the safety cap).
        - ``stopped_early`` — True iff ``target`` was reached before ``cap`` elapsed.

        ``cap`` (defaults to ``window``) is the metering time bound: the classic-extend
        path passes the member's safety maximum_duration so a slow flow can still reach
        the target past the nominal window. Every NON-metering path sleeps only
        ``window`` (never ``cap``), so a dead / cumulative meter never extends the run.
        Part A behaviour is preserved when ``target`` is None (full ``cap`` elapses).
        """
        window = float(window or 0)
        cap = float(cap) if cap else window
        sensor = distributor.get("flow_sensor")
        if not sensor:
            await self._dist_sleep(window)
            return None, window, False
        reading = self._dist_read_flow(sensor)
        if reading is None:
            await self._dist_sleep(window)  # dead meter -> full window, time-based
            return None, window, False
        _, unit = reading
        is_rate = self._dist_flow_unit_is_rate(unit)
        # b23 ships RATE-ONLY: a cumulative counter is dormant behind the flag and gets
        # no metering (hence no early stop) — sleep the window, credit time-based.
        if not is_rate and not const.DISTRIBUTOR_CUMULATIVE_METERING_ENABLED:
            await self._dist_sleep(window)
            return None, window, False
        last = None if is_rate else self._dist_flow_litres_from_total(reading[0], unit)
        delivered = 0.0
        reliable = True
        elapsed = 0.0
        while elapsed < cap:
            if target is not None and delivered >= target:
                break  # early stop: reached the target volume
            step = min(float(const.DISTRIBUTOR_FLOW_POLL_SECONDS), cap - elapsed)
            await self._dist_sleep(step)
            elapsed += step
            r = self._dist_read_flow(sensor)
            if r is None:
                reliable = False
                continue
            val, u = r
            if is_rate:
                delivered += self._flow_rate_to_l_per_min(val, u) * step / 60.0
            else:
                cur = self._dist_flow_litres_from_total(val, u)
                if cur < last:  # counter reset / rollover -> unreliable
                    reliable = False
                else:
                    delivered += cur - last
                last = cur
        stopped_early = target is not None and delivered >= target and elapsed < cap
        return (delivered if reliable else None), elapsed, stopped_early
```

- [ ] **Step 4: Update the sweep call site to unpack (no behaviour change yet)**

At `distributor.py:1024`, change:
```python
            measured = await self._dist_measure_window(distributor, window)
```
to:
```python
            measured, actual_seconds, _ = await self._dist_measure_window(
                distributor, window
            )
```
(cap defaults to window, target None → identical timing + measurement to b23; `actual_seconds` is used in Task 3.)

- [ ] **Step 5: Run measure tests + full distributor suite**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_distributor_cycle.py tests/test_distributor_integration.py -q
```
Expected: PASS.

- [ ] **Step 6: black + commit**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
"$OLD/uvenv312/Scripts/python.exe" -m black custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git add custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -F - <<'EOF'
feat(distributor): _dist_measure_window early-stops at a target volume

The metered window loop now accepts an optional target (litres) and a cap (time bound,
default = window) and returns (delivered, actual_seconds, stopped_early). It breaks as
soon as the metered volume reaches the target; the classic-extend caller passes a larger
cap so a slow flow can reach the target past the nominal window. Every non-metering path
still sleeps only the window (never the cap), so a dead/cumulative meter never extends.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 3: Sweep wiring — derive target/cap, note master at cap, credit actual seconds

**Files:** Modify `distributor.py:942-1026` (sweep); Test `tests/test_distributor_dispatch.py`

- [ ] **Step 1: Write failing sweep-level tests**

Open `tests/test_distributor_dispatch.py`, mirror the existing `_cycle_mocks`/`_host`/`_dist` conventions (as the Part A `test_sweep_credits_measured_flow_volume` test does), and add. Adapt the fixture calls to the file's actual helpers; the invariants asserted must hold:

```python
async def test_sweep_classic_passes_target_and_extend_cap():
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    _cycle_mocks(c)
    c._dist_needs_water = Mock(return_value=True)
    c._zone_target_bucket = Mock(return_value=0.0)
    c._metered_target_volume = Mock(return_value=12.0)  # positive target
    seen = {}
    async def _fake_measure(distributor, window, *, cap=None, target=None):
        seen["window"] = window
        seen["cap"] = cap
        seen["target"] = target
        return 12.0, window, True
    c._dist_measure_window = _fake_measure
    credited = {}
    c._dist_credit_zone = AsyncMock(
        side_effect=lambda z, s, measured_l=None, planned_seconds=None: credited.update(
            seconds=s, measured=measured_l, planned=planned_seconds
        )
    )
    c.store.async_get_zones = AsyncMock(
        return_value=[
            {"id": 7, "distributor_id": 0, "outlet_number": 1, "duration": 60,
             "maximum_duration": 900, "bucket": -3, "bucket_threshold": 0,
             "state": "automatic"}
        ]
    )
    await c.async_run_distributor_cycle(
        _dist(id=0, current_outlet=1, watering_mode=const.WATERING_MODE_CLASSIC)
    )
    assert seen["target"] == 12.0
    assert seen["cap"] == 900          # classic extend cap == maximum_duration
    assert credited["measured"] == 12.0
    assert credited["planned"] == 60   # planned == the window


async def test_sweep_self_closing_target_no_extend():
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    _cycle_mocks(c)
    c._dist_needs_water = Mock(return_value=True)
    c._zone_target_bucket = Mock(return_value=0.0)
    c._metered_target_volume = Mock(return_value=8.0)
    seen = {}
    async def _fake_measure(distributor, window, *, cap=None, target=None):
        seen["cap"] = cap
        seen["target"] = target
        return 8.0, window, True
    c._dist_measure_window = _fake_measure
    c._dist_credit_zone = AsyncMock()
    c.store.async_get_zones = AsyncMock(
        return_value=[
            {"id": 7, "distributor_id": 0, "outlet_number": 1, "duration": 60,
             "maximum_duration": 900, "bucket": -3, "bucket_threshold": 0,
             "state": "automatic"}
        ]
    )
    await c.async_run_distributor_cycle(
        _dist(id=0, current_outlet=1,
              watering_mode=const.WATERING_MODE_SERVICE, stop_service="script.off")
    )
    assert seen["target"] == 8.0
    assert seen["cap"] == 60  # self-closing: no extension, cap == window


async def test_sweep_no_flow_sensor_no_target():
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    _cycle_mocks(c)
    c._dist_needs_water = Mock(return_value=True)
    c._zone_target_bucket = Mock(return_value=0.0)
    c._metered_target_volume = Mock(return_value=8.0)
    seen = {}
    async def _fake_measure(distributor, window, *, cap=None, target=None):
        seen["cap"] = cap
        seen["target"] = target
        return None, window, False
    c._dist_measure_window = _fake_measure
    c._dist_credit_zone = AsyncMock()
    c.store.async_get_zones = AsyncMock(
        return_value=[
            {"id": 7, "distributor_id": 0, "outlet_number": 1, "duration": 60,
             "maximum_duration": 900, "bucket": -3, "bucket_threshold": 0,
             "state": "automatic"}
        ]
    )
    await c.async_run_distributor_cycle(
        _dist(id=0, current_outlet=1,
              watering_mode=const.WATERING_MODE_CLASSIC, flow_sensor=None)
    )
    assert seen["target"] is None        # no meter -> no early stop
    assert seen["cap"] == 60             # cap == window
```

Note: `_dist()` in the dispatch test file must allow `flow_sensor`/`watering_mode`/`stop_service` overrides (the shared `_dist(**kw)` helper does `d.update(kw)`). If `_cycle_mocks` already mocks `_dist_measure_window`, override it AFTER calling `_cycle_mocks` (as above). If the file's zone-store method differs (e.g. `async_get_zones` vs a members helper), match the file.

- [ ] **Step 2: Run to verify failure**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "sweep_classic_passes_target or sweep_self_closing_target or sweep_no_flow_sensor_no_target" -q
```
Expected: FAIL (the sweep passes no `cap`/`target`; credit gets `window`, not the planned/actual split).

- [ ] **Step 3: Derive target/cap in the sweep (after `window` is finalized, `distributor.py:942`)**

Immediately after the `if duration_override is not None and water: window = float(duration_override)` block (`:941-942`) and BEFORE the master-note block (`:963`), insert:
```python
            # Part B (early stop): a watered member with a rate flow meter and a
            # positive volume target stops at the target instead of running the full
            # window. classic (we hold the inlet) may run up to the safety
            # maximum_duration to reach the target — past the nominal window when the
            # real flow is slower than the configured throughput. A self-closing valve
            # can only be stopped EARLY within its passed window (extension impossible),
            # and only when a stop_service is configured. The master note below uses
            # `cap` so the pump covers the (possibly extended) run; the terminal
            # _dist_master_end collapses it to the real close. `cap == window` for every
            # non-extend path, so the master note is byte-for-byte b23 there.
            # siehe docs/superpowers/specs/2026-07-07-distributor-flow-volume-part-b-design.md
            target = None
            cap = window
            if water:
                mode = distributor.get("watering_mode")
                can_stop = mode == const.WATERING_MODE_CLASSIC or (
                    mode == const.WATERING_MODE_SERVICE
                    and bool(distributor.get("stop_service"))
                )
                tv = self._metered_target_volume(zone, self._zone_target_bucket(zone))
                if distributor.get("flow_sensor") and tv > 0 and can_stop:
                    target = tv
                    if mode == const.WATERING_MODE_CLASSIC:
                        cap = max(
                            window, float(zone.get(const.ZONE_MAXIMUM_DURATION) or 14400)
                        )
```

- [ ] **Step 4: Note the master at `cap` instead of `window` (`distributor.py:968-973`)**

In the master-note block, change the `note` sum's first term from `window` to `cap`:
```python
                note = (
                    cap
                    + pause
                    + settle
                    + const.DISTRIBUTOR_CYCLE_SAFETY_BUFFER_SECONDS
                )
```
(Everything else in that block — the `confirm_entity` addend, `note_deadline`, `own_deadline` tracking — is unchanged. For non-extend outlets `cap == window`, so this is identical to b23.)

- [ ] **Step 5: Pass `cap`/`target` to the measure call and credit the actual seconds (`distributor.py:1024-1026`)**

Change:
```python
            measured, actual_seconds, _ = await self._dist_measure_window(
                distributor, window
            )
            if water:
                await self._dist_credit_zone(zone, window, measured_l=measured)
```
to:
```python
            measured, actual_seconds, _ = await self._dist_measure_window(
                distributor, window, cap=cap, target=target
            )
            if water:
                await self._dist_credit_zone(
                    zone, actual_seconds, measured_l=measured, planned_seconds=window
                )
```

- [ ] **Step 6: Run the new sweep tests + the full distributor suite**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_distributor_cycle.py tests/test_distributor_integration.py -q
```
Expected: PASS. The existing cycle tests use distributors without a `flow_sensor` and/or mock `_dist_measure_window`, so `target` is None and `cap == window` → master note + credit are byte-for-byte b23; the H7 master-note tests (`test_master_note_is_rolling_not_upfront_estimate`, `test_concurrent_longer_normal_zone_deadline_wins`) must stay green (they assert the rolling note, which now reads `cap == window`).

- [ ] **Step 7: black + commit**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
"$OLD/uvenv312/Scripts/python.exe" -m black custom_components/smart_irrigation/distributor.py tests/test_distributor_dispatch.py
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_dispatch.py
git commit -F - <<'EOF'
feat(distributor): early-stop a member sweep at its target volume

The sweep derives each watered member's volume target (_metered_target_volume) and a
time cap: classic outlets extend up to the safety maximum_duration, self-closing-with-
stop outlets cap at the window (no extension), everything else keeps target=None. The
master-off note now covers `cap` (Phase-1 terminal collapse brings it back to the real
close), the measure call threads cap+target, and crediting books the actual elapsed
seconds against the planned window. Rate sensors only; cumulative stays dormant.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 4: i18n — `flow_sensor_help` early-stop note (8 languages)

**Files:** Modify `frontend/localize/languages/{en,de,nl,fr,es,it,no,sk}.json`

- [ ] **Step 1: Append an early-stop clause to each `flow_sensor_help` value**

Grep `flow_sensor_help` under `panels.distributors` in each file (currently the rate-only b23 text). Append one sentence stating that, where the valve can be stopped (a classic inlet or a self-closing stop-service), the outlet is stopped early once the target volume is reached. English:
`… Where the valve can be stopped (a classic inlet, or a self-closing stop-service), the outlet also stops early once its target volume is reached.`
German:
`… Wo das Ventil gestoppt werden kann (classic-Einlass oder Self-Closing-Stop-Service), wird der Ausgang zudem bei erreichter Zielmenge vorzeitig gestoppt.`
Translate for the other 6, matching each file's tone. Keep the KEY name; only extend the value.

- [ ] **Step 2: Validate all 8 parse**
```bash
cd custom_components/smart_irrigation/frontend
node -e "for (const l of ['en','de','nl','fr','es','it','no','sk']) JSON.parse(require('fs').readFileSync('localize/languages/'+l+'.json','utf8')); console.log('all 8 parse OK')"
```
Expected: `all 8 parse OK`. (Do NOT build/commit dist — the release task rebuilds it.)

- [ ] **Step 3: Commit**
```bash
git add custom_components/smart_irrigation/frontend/localize/languages
git commit -F - <<'EOF'
i18n(distributor): flow_sensor help notes early stop at target volume (8 languages)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 5: Regression, code review, release (b24)

- [ ] **Step 1: Full backend suite vs baseline (no new failures) + black --check.**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -q 2>&1 | tail -3
```
Expected: the only failures/errors are the pre-existing 67 (7 failed + 60 errors in diagnostics/init/panel/schedule_time_anchor/watering_calendar) — 0 distributor failures.

- [ ] **Step 2: Code-review checkpoint** — dispatch `superpowers:code-reviewer` on the Part B diff vs the spec (focus: fail-safe never extends without healthy metering; classic-extend master note = cap + Phase-1 collapse never over-runs or turns the master off mid-sweep; self-closing cannot extend; depth-fn fix; one advance per outlet; H7 tests intact).

- [ ] **Step 3: Version bump b23 -> b24** (const.py, manifest.json, frontend/package.json) + `npm run build` (bakes b24 + the help text); same recipe as prior betas.

- [ ] **Step 4: Release** — show notes for approval (REGEL 5), then push + `gh release create v2026.07.11b24 --repo Eifel-Joe/HAsmartirrigation --prerelease --target feature/gardena-distributor`.

- [ ] **Step 5: Update memories** — `hasi-flow-volume-tracking-feature` (Part B shipped in b24), `hasi-distributor-fix-roadmap` (Phase 4 B done; remaining = cumulative arming later).

---

## Self-review

- **Spec coverage:** variant-split time cap (classic extend / self-closing window) → Task 3 derivation + Task 2 cap; automatic trigger on rate sensor + valid target → Task 3 gate; target = `_metered_target_volume` → Task 3; master note at cap + Phase-1 collapse → Task 3 Step 4; measured→gross depth fix → Task 1; actual-vs-planned seconds → Tasks 1+3; fail-safe never extends without healthy metering (window-only sleep on non-metering paths) → Task 2 method + `test_measure_window_dead_sensor_sleeps_window_not_cap`; rate-only/cumulative dormant → Task 2 (unchanged gate); i18n → Task 4; regression/review/release → Task 5. All spec sections mapped.
- **Placeholders:** none — full test + impl code; the `14400` default mirrors `_run_valve_metered`.
- **Type/name consistency:** `_dist_measure_window(distributor, window, *, cap, target) -> (delivered, actual_seconds, stopped_early)`, `_dist_credit_zone(zone, seconds, measured_l, planned_seconds)`, `_metered_target_volume`, `_zone_target_bucket`, `_depth_from_volume_native`, `WATERING_MODE_CLASSIC/SERVICE`, `ZONE_MAXIMUM_DURATION` are used consistently across tasks and match the current code.
