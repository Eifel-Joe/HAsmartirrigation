# Observed-Watering Measured-Flow Crediting — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Credit observed (externally-driven) watering from the MEASURED flow on flow-sensor zones and from a capped time×throughput estimate otherwise, so a valve stuck reporting `open` with no real flow no longer books phantom litres.

**Architecture:** Mirror the self-closing flow-sampling pattern (`self_closing.py:151-222`) inside `ObservedWateringMixin`: on the external open edge build a `FlowMeter` + start a non-blocking `async_track_time_interval` sampler; on the close edge finalize `delivered()`. Route the credit: measured>0 → `min(measured, sanity-ceiling)`, measured==0.0 → 0, dead sensor (`delivered() is None`) → capped time estimate + problem flag, no sensor → capped time estimate. A universal cap `min(seconds, maximum_duration + 30 s)` bounds every path and the usage stats.

**Tech Stack:** Python, Home Assistant custom component, pytest. FlowMeter engine is pure-Python (`flow_metering.py`). Coordinator helpers reused via `self` (mixin): `_flow_build_meter`, `_read_flow_sample`, `_credited_depth_native`, `_record_run`, `async_write_watered_bucket`.

**Spec:** `docs/superpowers/specs/2026-08-16-observed-flow-credit-design.md`
**Test command (canonical, per CLAUDE.md):** `./.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock`

---

## File Structure

- **Modify** `custom_components/smart_irrigation/const.py` — add `OBSERVED_CAP_MARGIN_SECONDS = 30`.
- **Modify** `custom_components/smart_irrigation/observed_watering.py` — cap helper, per-zone meter state + sampler (mirror self-closing), measured-flow routing in `_credit_observed_watering`, lifecycle cancels.
- **Modify** `tests/test_observed_watering.py` — new tests (reuse the existing `_obs_coord` fixture pattern).

**Key existing helpers (already on the coordinator, reachable via `self`):**
- `self._flow_build_meter(zone, sample) -> (meter, open_start_l)` (`irrigation.py:814`) — resolves counter type from stored streak, seeds meter at valve-open.
- `self._read_flow_sample(sensor) -> (value, unit, state_class) | None` (`irrigation.py:~800`).
- `self._credited_depth_native(zone, litres) -> depth` (used by self-closing at `self_closing.py:260`) — litres→bucket depth in native units. USE THIS for the measured path (do not re-derive `applied_mm`).
- `meter.delivered() -> float | None` (`flow_metering.py:195`) — measured litres, `0.0` when live-but-dry, `None` when no numeric reading ever seen.
- `const.FLOW_POLL_INTERVAL = 15`, `const.ZONE_MAXIMUM_DURATION`, `const.ZONE_FLOW_SENSOR`.

**Signature change:** `_credit_observed_watering(self, zone_id, seconds, measured_l=None, sensor_present=False)`. Defaults preserve today's behaviour for callers that pass neither (none remain after Task 4, but keeps tasks independently testable).

---

### Task 1: Cap constant + `_observed_capped_seconds`

**Files:**
- Modify: `custom_components/smart_irrigation/const.py`
- Modify: `custom_components/smart_irrigation/observed_watering.py`
- Test: `tests/test_observed_watering.py`

- [ ] **Step 1: Write the failing test**

```python
def test_capped_seconds_bounds_at_maximum_duration_plus_margin():
    coord = _obs_coord([])
    zone = {const.ZONE_MAXIMUM_DURATION: 3600}
    # under the cap: unchanged
    assert coord._observed_capped_seconds(zone, 1200) == 1200
    # over the cap: bounded to maximum_duration + OBSERVED_CAP_MARGIN_SECONDS
    assert coord._observed_capped_seconds(zone, 21304) == 3600 + const.OBSERVED_CAP_MARGIN_SECONDS


def test_capped_seconds_falls_back_when_no_maximum_duration():
    coord = _obs_coord([])
    # a zone without maximum_duration uses the default cap, still bounded
    zone = {}
    capped = coord._observed_capped_seconds(zone, 99999)
    assert capped == const.CONF_DEFAULT_MAXIMUM_DURATION + const.OBSERVED_CAP_MARGIN_SECONDS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py::test_capped_seconds_bounds_at_maximum_duration_plus_margin -p _local_socket_unblock`
Expected: FAIL — `AttributeError: ... '_observed_capped_seconds'` and `AttributeError: module const has no 'OBSERVED_CAP_MARGIN_SECONDS'`.

- [ ] **Step 3: Add the constant**

In `const.py`, next to the other observed constants (search `RUN_TRIGGER_OBSERVED` / `ZONE_OBSERVED_ENTITY`):

```python
# An observed (external) run can credit no more water than SI itself would ever
# run this valve for: cap its counted seconds at the zone's maximum_duration plus
# a small margin so a legitimate external run finishing just past the cap is not
# clipped. Guards non-flow zones (no sensor to contradict a stuck-open valve) and
# is the sanity ceiling on measured flow too.
OBSERVED_CAP_MARGIN_SECONDS = 30
```

- [ ] **Step 4: Implement `_observed_capped_seconds`**

In `observed_watering.py`, add to `ObservedWateringMixin`:

```python
    def _observed_capped_seconds(self, zone: dict, seconds: float) -> float:
        """Bound external run seconds at maximum_duration + margin (see const)."""
        max_dur = zone.get(const.ZONE_MAXIMUM_DURATION)
        if not max_dur:
            max_dur = const.CONF_DEFAULT_MAXIMUM_DURATION
        return min(float(seconds), float(max_dur) + const.OBSERVED_CAP_MARGIN_SECONDS)
```

Note: verify `const.CONF_DEFAULT_MAXIMUM_DURATION` is an int/float (it is defined at `const.py:264`). If it is wrapped (e.g. a tuple/timedelta), coerce to seconds in the helper.

- [ ] **Step 5: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -k capped_seconds -p _local_socket_unblock`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/observed_watering.py tests/test_observed_watering.py
git commit -m "feat(observed): add maximum_duration+margin cap helper for external runs"
```

---

### Task 2: Cap the non-flow (time×throughput) credit + usage stats

**Files:**
- Modify: `custom_components/smart_irrigation/observed_watering.py:142-200`
- Test: `tests/test_observed_watering.py`

Refactor `_credit_observed_watering` so the seconds used for BOTH the bucket credit and the recorded usage (`volume_l`, `actual_s`) are capped for the time-based (non-flow) path. Add the new params now (unused until Task 5) so the signature is stable.

- [ ] **Step 1: Write the failing test**

```python
def _credit_coord(zone):
    """Coordinator stub able to run _credit_observed_watering end to end."""
    coord = _obs_coord([])
    coord.store.get_zone = Mock(return_value=zone)
    coord._record_run = AsyncMock()
    coord.async_write_watered_bucket = AsyncMock()
    coord.hass.config = SimpleNamespace(units=Mock())  # non-metric path avoided below
    # force metric so size/throughput pass through unconverted
    import custom_components.smart_irrigation.observed_watering as ow
    coord.hass.config.units = ow.METRIC_SYSTEM
    return coord


async def test_non_flow_zone_credit_capped_at_maximum_duration():
    zone = {
        const.ZONE_ID: 2, const.ZONE_SIZE: 5.0, const.ZONE_THROUGHPUT: 3.1,
        const.ZONE_MAXIMUM_DURATION: 3600, const.ZONE_FLOW_SENSOR: None,
        const.ZONE_BUCKET: 0.0, const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
    }
    coord = _credit_coord(zone)
    await coord._credit_observed_watering(2, 21304)  # ~6h stuck-open
    # volume recorded uses capped seconds (3630 s), NOT 21304 s
    capped_l = 3.1 * ((3600 + const.OBSERVED_CAP_MARGIN_SECONDS) / 60.0)
    kwargs = coord._record_run.call_args.kwargs
    assert kwargs["volume_l"] == pytest.approx(capped_l)
    assert kwargs["actual_s"] == 3630
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py::test_non_flow_zone_credit_capped_at_maximum_duration -p _local_socket_unblock`
Expected: FAIL — recorded `volume_l`/`actual_s` use the raw 21304 s.

- [ ] **Step 3: Implement — cap the time-based path**

In `_credit_observed_watering`, change the signature and cap the seconds before the volume math. Replace the header + the `volume_l` block:

```python
    async def _credit_observed_watering(
        self, zone_id: int, seconds: float, measured_l=None, sensor_present: bool = False
    ) -> None:
        # ... unchanged guards (seconds<=0, zone None, size/throughput) ...

        # Cap the counted seconds: an external run credits no more than SI itself
        # would run this valve (see OBSERVED_CAP_MARGIN_SECONDS). Used for the
        # time-based volume AND as the sanity ceiling on measured flow.
        capped_s = self._observed_capped_seconds(zone, seconds)
        # ... metric size_m2 / tput_lpm block unchanged ...

        time_volume_l = tput_lpm * (capped_s / 60.0)
        volume_l = time_volume_l  # measured path overrides this in Task 5
```

Then make the run record use the capped values — change `actual_s=round(seconds)` to `actual_s=round(capped_s)`, and keep `volume_l=volume_l`. Keep the rest (`applied_native`, bucket write, duration-zero) computing from `volume_l`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -p _local_socket_unblock`
Expected: PASS (new test + all existing observed tests still green — existing tests use short durations under the cap, so their numbers are unchanged).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/observed_watering.py tests/test_observed_watering.py
git commit -m "fix(observed): cap non-flow time-based credit + usage at maximum_duration"
```

---

### Task 3: Per-zone meter state + sampler (mirror self-closing)

**Files:**
- Modify: `custom_components/smart_irrigation/observed_watering.py`
- Test: `tests/test_observed_watering.py`

Add `_observed_meters()` state, `_observed_start_flow_sampling(zone)`, the `_observed_sample_flow(zone_id, at)` test seam, and `_observed_finish_flow(zone_id) -> (measured, sensor_present)`. Mirror `self_closing.py:151-222` but with the crucial difference: distinguish `delivered()==0.0` (live-but-dry → measured `0.0`) from `None` (dead sensor → measured `None`), and always report `sensor_present`.

Imports to add at the top of `observed_watering.py`:

```python
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
```

- [ ] **Step 1: Write the failing test** (drive sampling via the seam, no real timer)

```python
def _sampler_coord(zone):
    coord = _obs_coord([])
    coord.store.get_zone = Mock(return_value=zone)
    # _read_flow_sample returns (value, unit, state_class); drive it from a list
    reads = {"v": 0.0}
    coord._read_flow_sample = Mock(side_effect=lambda s: (reads["v"], "L", "total_increasing"))
    coord._reads = reads
    # real _flow_build_meter is on the coordinator; it is pure enough to call, but
    # these unit coords are __new__'d — import the real method via the class.
    from custom_components.smart_irrigation import SmartIrrigationCoordinator as C
    coord._flow_build_meter = C._flow_build_meter.__get__(coord)
    coord._credited_depth_native = Mock(side_effect=lambda z, l: l / (z[const.ZONE_SIZE]))
    return coord


async def test_observed_finish_flow_measures_totalizer_delta():
    zone = {const.ZONE_ID: 2, const.ZONE_FLOW_SENSOR: "sensor.flow",
            const.ZONE_FLOW_COUNTER_TYPE: "lifetime", const.ZONE_SIZE: 5.0}
    coord = _sampler_coord(zone)
    coord._reads["v"] = 100.0          # valve-open baseline
    await coord._observed_start_flow_sampling(zone)
    coord._reads["v"] = 108.0          # +8 L delivered
    coord._observed_sample_flow(2, 15.0)
    measured, present = coord._observed_finish_flow(2)  # takes a final read (108)
    assert present is True
    assert measured == pytest.approx(8.0)
    assert 2 not in coord._observed_meters()  # entry popped, no leak


async def test_observed_finish_flow_dry_valve_returns_zero_not_none():
    zone = {const.ZONE_ID: 2, const.ZONE_FLOW_SENSOR: "sensor.flow",
            const.ZONE_FLOW_COUNTER_TYPE: "lifetime", const.ZONE_SIZE: 5.0}
    coord = _sampler_coord(zone)
    coord._reads["v"] = 103.0          # flat all the way (stuck-open dry)
    await coord._observed_start_flow_sampling(zone)
    coord._observed_sample_flow(2, 15.0)
    measured, present = coord._observed_finish_flow(2)
    assert present is True
    assert measured == 0.0             # NOT None — the bug case


async def test_observed_finish_flow_dead_sensor_returns_none():
    zone = {const.ZONE_ID: 2, const.ZONE_FLOW_SENSOR: "sensor.flow",
            const.ZONE_FLOW_COUNTER_TYPE: "lifetime", const.ZONE_SIZE: 5.0}
    coord = _sampler_coord(zone)
    coord._read_flow_sample = Mock(return_value=None)  # sensor never numeric
    await coord._observed_start_flow_sampling(zone)
    measured, present = coord._observed_finish_flow(2)
    assert present is True
    assert measured is None            # dead sensor -> caller falls back to capped time
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -k observed_finish_flow -p _local_socket_unblock`
Expected: FAIL — methods `_observed_start_flow_sampling` / `_observed_finish_flow` / `_observed_meters` missing.

- [ ] **Step 3: Implement — mirror self-closing sampler**

```python
    def _observed_meters(self) -> dict:
        m = getattr(self, "_observed_meters_state", None)
        if m is None:
            m = self._observed_meters_state = {}
        return m

    async def _observed_start_flow_sampling(self, zone: dict) -> None:
        """Start non-blocking interval sampling of an external run's flow_sensor."""
        sensor = zone.get(const.ZONE_FLOW_SENSOR)
        if not sensor:
            return
        zone_id = zone.get(const.ZONE_ID)
        self._observed_cancel_meter(zone_id)  # single-flight (Task 6)
        sample = self._read_flow_sample(sensor)
        meter, open_start_l = self._flow_build_meter(zone, sample)  # seeds at open
        started = dt_util.utcnow()

        async def _tick(now):
            self._observed_sample_flow(zone_id, (now - started).total_seconds())

        cancel = async_track_time_interval(
            self.hass, _tick, timedelta(seconds=const.FLOW_POLL_INTERVAL)
        )
        self._observed_meters()[zone_id] = (meter, cancel, open_start_l, started)

    def _observed_sample_flow(self, zone_id, at: float) -> None:
        """Feed the in-flight meter one reading (also the deterministic test seam)."""
        entry = self._observed_meters().get(zone_id)
        if not entry:
            return
        meter = entry[0]
        zone = self.store.get_zone(zone_id) or {}
        sample = self._read_flow_sample(zone.get(const.ZONE_FLOW_SENSOR))
        if sample is not None:
            meter.sample(*sample, at=at)

    def _observed_finish_flow(self, zone_id):
        """Cancel sampling; return (measured_l | None, sensor_present).

        Unlike self-closing, 0.0 (live-but-dry) is returned as 0.0 — NOT collapsed
        to None — so the caller credits 0 for a stuck-open valve. None means the
        sensor produced no numeric reading (dead/misconfigured) -> caller falls back
        to the capped time estimate + problem flag.
        """
        entry = self._observed_meters().pop(zone_id, None)
        if not entry:
            return None, False
        meter, cancel, _open_start_l, started = entry
        cancel()
        zone = self.store.get_zone(zone_id) or {}
        sensor = zone.get(const.ZONE_FLOW_SENSOR)
        final = self._read_flow_sample(sensor)
        if final is not None:
            meter.sample(*final, at=(dt_util.utcnow() - started).total_seconds())
        # NB: observed does NOT persist cross-run learning (flow_last_end /
        # flow_reset_streak) — interleaved external opens would poison the SI
        # runner's clean-sequence convergence. It only CONSUMES the learned type
        # via _flow_build_meter. (Distributor precedent, irrigation.py:1276.)
        return meter.delivered(), bool(sensor)
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -k observed_finish_flow -p _local_socket_unblock`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/observed_watering.py tests/test_observed_watering.py
git commit -m "feat(observed): per-zone flow sampler mirroring self-closing (0.0 vs None distinct)"
```

---

### Task 4: Wire the open/close edges to the sampler

**Files:**
- Modify: `custom_components/smart_irrigation/observed_watering.py:109-140`
- Test: `tests/test_observed_watering.py`

On the external OPEN edge, start the sampler (flow zones only). On the CLOSE edge, finish it and pass `(measured, sensor_present)` into the credit call.

- [ ] **Step 1: Write the failing test**

```python
async def test_open_edge_starts_sampler_for_flow_zone(monkeypatch):
    zone = {const.ZONE_ID: 2, const.ZONE_FLOW_SENSOR: "sensor.flow"}
    coord = _obs_coord([])
    coord._observed_zone_by_entity = {"valve.x": 2}
    coord._si_driven_until = {}
    coord.zone_run_in_flight = Mock(return_value=False)
    coord.store.get_zone = Mock(return_value=zone)
    started = {"n": 0}
    async def _fake_start(z):
        started["n"] += 1
    coord._observed_start_flow_sampling = _fake_start
    ev = _state_event("valve.x", old="closed", new="open")   # helper below
    coord._observed_state_changed(ev)
    await asyncio.sleep(0)  # let the create_task run
    assert started["n"] == 1
    assert coord._observed_on_since.get(2) is not None
```

Add a small `_state_event(entity, old, new)` helper near the top of the test file if one does not already exist (build a `SimpleNamespace` event with `data={"entity_id":..., "old_state": SimpleNamespace(state=old), "new_state": SimpleNamespace(state=new)}`).

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py::test_open_edge_starts_sampler_for_flow_zone -p _local_socket_unblock`
Expected: FAIL — sampler not started on open.

- [ ] **Step 3: Implement — edges**

In `_observed_state_changed`, on the open branch after recording `_observed_on_since[zone_id]`:

```python
            self._observed_on_since[zone_id] = dt_util.utcnow()
            zone = self.store.get_zone(zone_id) or {}
            if zone.get(const.ZONE_FLOW_SENSOR):
                self.hass.async_create_task(self._observed_start_flow_sampling(zone))
```

On the close branch, replace the credit dispatch:

```python
        elif old_on and not new_on:
            started = self._observed_on_since.pop(zone_id, None)
            measured, sensor_present = self._observed_finish_flow(zone_id)
            if started is None:
                return
            seconds = (dt_util.utcnow() - started).total_seconds()
            self.hass.async_create_task(
                self._credit_observed_watering(
                    zone_id, seconds, measured_l=measured, sensor_present=sensor_present
                )
            )
```

Note: call `_observed_finish_flow` BEFORE the `started is None` early-return so a sampler is always cancelled even on an untracked close (defensive against leaks).

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -p _local_socket_unblock`
Expected: PASS (new test + existing; existing close-edge tests still credit time-based because `_observed_finish_flow` returns `(None, False)` for their no-sensor zones).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/observed_watering.py tests/test_observed_watering.py
git commit -m "feat(observed): drive the flow sampler from the external open/close edges"
```

---

### Task 5: Route the credit by measured flow (the core fix)

**Files:**
- Modify: `custom_components/smart_irrigation/observed_watering.py` (`_credit_observed_watering`)
- Test: `tests/test_observed_watering.py`

Now consume `measured_l` / `sensor_present`: measured>0 → `min(credited_depth(measured), time-ceiling)`; measured==0.0 → 0 credit; dead sensor (`sensor_present and measured is None`) → capped time + set the zone problem flag; no sensor → capped time (unchanged Task 2 path).

- [ ] **Step 1: Write the failing tests**

```python
async def test_flow_zone_credits_measured_not_time(monkeypatch):
    zone = {const.ZONE_ID: 2, const.ZONE_SIZE: 5.0, const.ZONE_THROUGHPUT: 3.1,
            const.ZONE_MAXIMUM_DURATION: 3600, const.ZONE_FLOW_SENSOR: "sensor.flow",
            const.ZONE_BUCKET: 0.0, const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC}
    coord = _credit_coord(zone)
    coord._credited_depth_native = Mock(side_effect=lambda z, l: l / z[const.ZONE_SIZE])
    await coord._credit_observed_watering(2, 21304, measured_l=8.0, sensor_present=True)
    # credited from measured 8 L (=1.6 mm), NOT 21304 s × 3.1
    kwargs = coord._record_run.call_args.kwargs
    assert kwargs["volume_l"] == pytest.approx(8.0)


async def test_flow_zone_dry_valve_credits_zero():
    zone = {const.ZONE_ID: 2, const.ZONE_SIZE: 5.0, const.ZONE_THROUGHPUT: 3.1,
            const.ZONE_MAXIMUM_DURATION: 3600, const.ZONE_FLOW_SENSOR: "sensor.flow",
            const.ZONE_BUCKET: 0.0, const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC}
    coord = _credit_coord(zone)
    coord._credited_depth_native = Mock(side_effect=lambda z, l: l / z[const.ZONE_SIZE])
    await coord._credit_observed_watering(2, 21304, measured_l=0.0, sensor_present=True)
    # the 1349 L bug case: zero credit, bucket unchanged from 0.0
    coord.async_write_watered_bucket.assert_awaited()
    new_bucket = coord.async_write_watered_bucket.call_args.args[1]
    assert new_bucket == pytest.approx(0.0)
    assert coord._record_run.call_args.kwargs["volume_l"] == pytest.approx(0.0)


async def test_flow_zone_measured_capped_at_time_ceiling():
    zone = {const.ZONE_ID: 2, const.ZONE_SIZE: 5.0, const.ZONE_THROUGHPUT: 3.1,
            const.ZONE_MAXIMUM_DURATION: 3600, const.ZONE_FLOW_SENSOR: "sensor.flow",
            const.ZONE_BUCKET: 0.0, const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC}
    coord = _credit_coord(zone)
    coord._credited_depth_native = Mock(side_effect=lambda z, l: l / z[const.ZONE_SIZE])
    # sensor stuck at a huge constant reading -> measured absurdly high
    await coord._credit_observed_watering(2, 600, measured_l=99999.0, sensor_present=True)
    ceiling_l = 3.1 * ((600) / 60.0)  # capped_s == 600 (< max), ceiling = tput×capped_s
    assert coord._record_run.call_args.kwargs["volume_l"] == pytest.approx(ceiling_l)


async def test_flow_zone_dead_sensor_uses_capped_time_and_flags(monkeypatch):
    zone = {const.ZONE_ID: 2, const.ZONE_SIZE: 5.0, const.ZONE_THROUGHPUT: 3.1,
            const.ZONE_MAXIMUM_DURATION: 3600, const.ZONE_FLOW_SENSOR: "sensor.flow",
            const.ZONE_BUCKET: 0.0, const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC}
    coord = _credit_coord(zone)
    flagged = {"n": 0}
    coord._observed_flag_dead_sensor = Mock(side_effect=lambda zid, s: flagged.__setitem__("n", flagged["n"] + 1))
    await coord._credit_observed_watering(2, 21304, measured_l=None, sensor_present=True)
    capped_l = 3.1 * ((3600 + const.OBSERVED_CAP_MARGIN_SECONDS) / 60.0)
    assert coord._record_run.call_args.kwargs["volume_l"] == pytest.approx(capped_l)
    assert flagged["n"] == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -k "flow_zone" -p _local_socket_unblock`
Expected: FAIL — measured path not implemented; `_observed_flag_dead_sensor` missing.

- [ ] **Step 3: Implement — measured routing + dead-sensor flag**

Replace the `time_volume_l` / `volume_l` assignment (from Task 2) with the routing:

```python
        time_volume_l = tput_lpm * (capped_s / 60.0)
        if sensor_present and measured_l is not None:
            # Measured flow (may be 0.0 for a live-but-dry / stuck-open valve),
            # sanity-capped so a sensor stuck at a constant nonzero rate cannot
            # book more than the nameplate estimate for the same (capped) window.
            volume_l = min(float(measured_l), time_volume_l)
        elif sensor_present and measured_l is None:
            # Flow zone but the sensor produced no reading — do NOT trust the raw
            # external seconds; use the capped estimate and surface the sensor.
            volume_l = time_volume_l
            self._observed_flag_dead_sensor(zone_id, zone.get(const.ZONE_FLOW_SENSOR))
        else:
            volume_l = time_volume_l  # no flow sensor: capped time estimate
```

Add the flag helper (reuse the existing problem-sensor mechanism — check `binary_sensor.py` for the zone `problem` sensor / how self-closing raises `FAULT_FLOW_NEVER_STARTED`; the minimal form logs a warning ONCE and sets the zone's problem state):

```python
    def _observed_flag_dead_sensor(self, zone_id, sensor) -> None:
        """Surface a flow-sensor zone whose sensor gave no reading on an external run."""
        _LOGGER.warning(
            "Observed watering: zone %s flow sensor '%s' produced no reading this "
            "external run; credited the capped time-based estimate instead",
            zone_id, sensor,
        )
        # If a zone problem flag exists, set it here (see binary_sensor.py). Confirm
        # the exact mechanism during implementation; a log-only fallback is acceptable
        # if there is no per-zone transient problem setter.
```

`applied_mm`/`applied_native`/bucket-write stay as they are, computing from `volume_l`.

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -p _local_socket_unblock`
Expected: PASS (all new + existing).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/observed_watering.py tests/test_observed_watering.py
git commit -m "fix(observed): credit measured flow, zero a dry valve, cap+flag a dead sensor"
```

---

### Task 6: Lifecycle — single-flight + teardown cancel

**Files:**
- Modify: `custom_components/smart_irrigation/observed_watering.py` (`async_teardown_observed_watering`, `async_setup_observed_watering`, add `_observed_cancel_meter`)
- Test: `tests/test_observed_watering.py`

Ensure a sampler can never leak across reload/shutdown/re-subscribe and that a re-open cancels a prior sampler.

- [ ] **Step 1: Write the failing test**

```python
async def test_teardown_cancels_inflight_samplers():
    coord = _obs_coord([])
    cancel = Mock()
    coord._observed_meters()[2] = ("meter", cancel, None, "started")
    coord.async_teardown_observed_watering()
    cancel.assert_called_once()
    assert coord._observed_meters() == {}


async def test_reopen_cancels_prior_sampler(monkeypatch):
    zone = {const.ZONE_ID: 2, const.ZONE_FLOW_SENSOR: "sensor.flow",
            const.ZONE_FLOW_COUNTER_TYPE: "lifetime", const.ZONE_SIZE: 5.0}
    coord = _sampler_coord(zone)
    cancels = []
    monkeypatch.setattr(
        "custom_components.smart_irrigation.observed_watering.async_track_time_interval",
        lambda *a, **k: (cancels.append(Mock()) or cancels[-1]),
    )
    await coord._observed_start_flow_sampling(zone)
    await coord._observed_start_flow_sampling(zone)  # re-open before close
    cancels[0].assert_called_once()                  # first sampler cancelled
    assert list(coord._observed_meters()) == [2]     # exactly one entry
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -k "teardown_cancels or reopen_cancels" -p _local_socket_unblock`
Expected: FAIL — teardown does not cancel meters; `_observed_cancel_meter` missing.

- [ ] **Step 3: Implement**

```python
    def _observed_cancel_meter(self, zone_id) -> None:
        """Cancel and drop a zone's in-flight sampler, if any (no-op otherwise)."""
        entry = self._observed_meters().pop(zone_id, None)
        if entry is not None:
            entry[1]()  # cancel
```

In `async_teardown_observed_watering`, before clearing state:

```python
        for zone_id in list(self._observed_meters()):
            self._observed_cancel_meter(zone_id)
```

In `async_setup_observed_watering`, in the re-subscribe teardown block (where `self._observed_on_since = {}` is reset), also cancel any live meters:

```python
            for zone_id in list(self._observed_meters()):
                self._observed_cancel_meter(zone_id)
```

(`_observed_start_flow_sampling` already calls `_observed_cancel_meter` first — Task 3 — so re-open single-flight is covered once this method exists.)

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -p _local_socket_unblock`
Expected: PASS (all).

- [ ] **Step 5: Full suite + lint (no regressions)**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock
uvx black --check custom_components/smart_irrigation/
uvx ruff check custom_components/smart_irrigation/
```
Expected: full suite green (esp. `test_self_closing.py`, `test_distributor_cycle.py`, `test_observed_distributor_members.py` — the REGEL-8 sisters); black + ruff clean.

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_irrigation/observed_watering.py tests/test_observed_watering.py
git commit -m "fix(observed): cancel in-flight flow samplers on teardown/reload/re-open"
```

---

## Self-Review (author checklist — done at write time)

**Spec coverage:**
- Flow-zone measured credit → Task 5 (`test_flow_zone_credits_measured_not_time`). ✅
- Stuck-open dry → 0 → Task 5 (`test_flow_zone_dry_valve_credits_zero`). ✅
- Dead sensor → capped time + flag → Task 5 (`test_flow_zone_dead_sensor_uses_capped_time_and_flags`). ✅
- Non-flow capped time → Task 2. ✅
- Cap = maximum_duration + 30 → Task 1. ✅
- Flow-zone sanity ceiling → Task 5 (`test_flow_zone_measured_capped_at_time_ceiling`). ✅
- Stats capped → Task 2 (`actual_s`/`volume_l`). ✅
- No cross-run learning write → Task 3 (`_observed_finish_flow` deliberately omits `_flow_learn_end_changes`). ✅
- Lifecycle (single-flight, teardown) → Task 6. ✅
- REGEL-8 sisters unchanged → verified green in Task 6 Step 5.
- per_run mid-run reset needs polling → covered by the 15 s sampler (Task 3); **add a per_run observed test during implementation** if time allows (Task 3 currently tests lifetime; a per_run reset test strengthens it).

**Open confirmations for the implementer (do NOT block, resolve in-task):**
1. `const.CONF_DEFAULT_MAXIMUM_DURATION` numeric shape (Task 1 Step 4 note).
2. Exact zone problem-flag setter (Task 5 Step 3 note) — log-only fallback acceptable.
3. `_credited_depth_native` exact name/signature — confirm against `self_closing.py:260` (`_credited_depth_native`) before Task 5.

**Type consistency:** `_observed_finish_flow` returns `(measured|None, sensor_present:bool)` — consumed with that shape in Task 4 and routed in Task 5. `_credit_observed_watering(zone_id, seconds, measured_l=None, sensor_present=False)` stable from Task 2. Meter tuple `(meter, cancel, open_start_l, started)` identical to self-closing. ✅

## Live-Test (after merge-ready, own approved step)

Per project CLAUDE.md, "live" = HA-Prod, but there is an HA-Test instance (`mcp__HA-Test__`) with a Sonoff emulator (`*sonoff_emu*`, incl. a flow binary + self-closing run script) — run there FIRST: drive a valve `open` with a flat/zero flow sensor and confirm ~0 credit; then a real-flow run and confirm measured credit. Only then, with explicit approval, reproduce a phantom-`open` on HA-Prod.
