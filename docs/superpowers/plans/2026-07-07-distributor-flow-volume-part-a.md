# Distributor flow-volume Part A (measurement) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Meter the actual delivered volume per distributor member window from the shared inlet flow sensor and credit the real litres instead of the time estimate; no early stop.

**Architecture:** The sweep's per-outlet `_dist_sleep(window)` becomes a poll-and-accumulate loop when the distributor has a `flow_sensor` — cumulative counter (snapshot-delta) or rate (integrate), classified by unit. `_dist_credit_zone` credits the measured litres; anything unreliable degrades to today's time-based crediting.

**Tech Stack:** Python 3.12, Home Assistant custom integration; JSON i18n (8 languages).

**Spec:** `docs/superpowers/specs/2026-07-07-distributor-flow-volume-part-a-design.md`

---

## Test env
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "<selector>" -q
```
black-format Python before committing. Commit via `git commit -F - <<'EOF' ... EOF`.

## File structure
- `custom_components/smart_irrigation/const.py` — `DISTRIBUTOR_FLOW_POLL_SECONDS`.
- `custom_components/smart_irrigation/distributor.py` — flow helpers + `_dist_measure_window`; `_dist_credit_zone` gains `measured_l`; the sweep window wiring (`:902-929`).
- `frontend/localize/languages/*.json` — flow_sensor help text update (8 langs).
- Tests: `tests/test_distributor.py` (helpers + crediting), `tests/test_distributor_dispatch.py` (sweep-level).

---

## Task 1: Flow-reading helpers + windowed measurement

**Files:** Modify `const.py`, `distributor.py`; Test `tests/test_distributor.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_distributor.py`:
```python
def _flow_host(sensor="sensor.inlet_flow"):
    c = _host()
    c._dist_sleep = AsyncMock()
    d = _dist(watering_mode=const.WATERING_MODE_SERVICE, flow_sensor=sensor)
    return c, d


def _state(val, unit):
    s = Mock()
    s.state = str(val)
    s.attributes = {"unit_of_measurement": unit}
    return s


def test_flow_unit_is_rate():
    c = _host()
    assert c._dist_flow_unit_is_rate("L/min") is True
    assert c._dist_flow_unit_is_rate("m³/h") is True
    assert c._dist_flow_unit_is_rate("L") is False
    assert c._dist_flow_unit_is_rate("m³") is False


def test_flow_litres_from_total_units():
    c = _host()
    assert c._dist_flow_litres_from_total(2.0, "L") == 2.0
    assert c._dist_flow_litres_from_total(2.0, "m³") == 2000.0
    assert round(c._dist_flow_litres_from_total(1.0, "gal"), 4) == 3.7854
    assert c._dist_flow_litres_from_total(5.0, "weird") == 5.0  # default litres


async def test_measure_window_cumulative_counter():
    # counter climbs 100 -> 106 L across the window -> 6 L delivered
    c, d = _flow_host()
    vals = iter([100.0, 102.0, 104.0, 106.0])  # open snapshot, then 3 poll reads
    c.hass.states.get = Mock(side_effect=lambda s: _state(next(vals), "L"))
    measured = await c._dist_measure_window(d, 15)  # 3 polls at 5 s
    assert measured == 6.0


async def test_measure_window_rate_sensor():
    # constant 12 L/min for 60 s -> 12 L
    c, d = _flow_host()
    c.hass.states.get = Mock(return_value=_state(12.0, "L/min"))
    measured = await c._dist_measure_window(d, 60)
    assert round(measured, 3) == 12.0


async def test_measure_window_no_sensor_returns_none():
    c = _host()
    c._dist_sleep = AsyncMock()
    measured = await c._dist_measure_window(_dist(flow_sensor=None), 30)
    assert measured is None
    c._dist_sleep.assert_awaited_once_with(30)  # single sleep, unchanged path


async def test_measure_window_unavailable_falls_back_none():
    c, d = _flow_host()
    c.hass.states.get = Mock(return_value=None)  # unavailable at open
    measured = await c._dist_measure_window(d, 30)
    assert measured is None
    c._dist_sleep.assert_awaited_once_with(30)  # full window, then time-based


async def test_measure_window_counter_reset_is_unreliable():
    c, d = _flow_host()
    vals = iter([100.0, 102.0, 5.0, 7.0])  # reset mid-window
    c.hass.states.get = Mock(side_effect=lambda s: _state(next(vals), "L"))
    measured = await c._dist_measure_window(d, 15)
    assert measured is None  # a backwards counter marks the window unreliable
```

- [ ] **Step 2: Run to verify failure**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "flow_unit_is_rate or flow_litres_from_total or measure_window" -q
```
Expected: FAIL (helpers/method undefined).

- [ ] **Step 3: Add the constant**

In `const.py`, near the distributor constants:
```python
# Distributor flow-metering poll interval (seconds) for volume measurement (Part A).
DISTRIBUTOR_FLOW_POLL_SECONDS = 5
```

- [ ] **Step 4: Add the helpers + measurement in `distributor.py`**

Add near the inlet-watch/cycle helpers:
```python
    @staticmethod
    def _dist_flow_unit_is_rate(unit: str) -> bool:
        """A flow unit is a RATE (per-time) iff it contains '/'; else a cumulative
        total counter."""
        return "/" in (unit or "")

    @staticmethod
    def _dist_flow_litres_from_total(value: float, unit: str) -> float:
        """Convert a cumulative flow-counter reading to litres. Mirrors
        _flow_rate_to_l_per_min's unit strings/factors (totals, not rates)."""
        u = (unit or "").lower().strip()
        if u in ("m³", "m3", "cubic meter", "cubic meters"):
            return float(value) * 1000.0
        if u in ("gal", "gallon", "gallons"):
            return float(value) * 3.785411784
        return float(value)  # L / l / liter(s) / unknown -> assume litres

    def _dist_read_flow(self, sensor: str):
        """Read a flow sensor -> (value, unit) or None when unavailable/non-numeric
        (fail-safe: the caller then degrades to time-based crediting)."""
        state = self.hass.states.get(sensor)
        if state is None or getattr(state, "state", None) in (
            "unavailable",
            "unknown",
            None,
            "",
        ):
            return None
        try:
            value = float(state.state)
        except (ValueError, TypeError):
            return None
        unit = state.attributes.get("unit_of_measurement", "") if state.attributes else ""
        return value, unit

    async def _dist_measure_window(self, distributor: dict, window: float):
        """Sleep the outlet's window; if the distributor has a flow_sensor, meter the
        delivered litres over it. Returns measured litres, or None to fall back to
        time-based crediting (no sensor, or an unreliable reading). Part A: never
        stops early — the full window always elapses."""
        sensor = distributor.get("flow_sensor")
        if not sensor:
            await self._dist_sleep(window)
            return None
        reading = self._dist_read_flow(sensor)
        if reading is None:
            await self._dist_sleep(window)  # dead meter -> full window, time-based
            return None
        _, unit = reading
        is_rate = self._dist_flow_unit_is_rate(unit)
        last = None if is_rate else self._dist_flow_litres_from_total(reading[0], unit)
        delivered = 0.0
        reliable = True
        elapsed = 0.0
        window = float(window or 0)
        while elapsed < window:
            step = min(float(const.DISTRIBUTOR_FLOW_POLL_SECONDS), window - elapsed)
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
        return delivered if reliable else None
```
Note: `_flow_rate_to_l_per_min` is a `@staticmethod` on the coordinator (via `IrrigationRunnerMixin`, mixed into the same class); `self._flow_rate_to_l_per_min(...)` resolves. `_DistHost` in the tests already mixes `IrrigationRunnerMixin`.

- [ ] **Step 5: Run tests to pass**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "flow_unit_is_rate or flow_litres_from_total or measure_window" -q
```
Expected: PASS (all 7).

- [ ] **Step 6: black + commit**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
"$OLD/uvenv312/Scripts/python.exe" -m black custom_components/smart_irrigation/const.py custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -F - <<'EOF'
feat(distributor): flow-metered window measurement (cumulative + rate)

Part A groundwork: _dist_measure_window meters the delivered litres over an outlet's
window from the distributor flow_sensor — cumulative counter snapshot-delta or rate
integration, classified by unit (reusing _flow_rate_to_l_per_min + matching total
factors). Returns None (fall back to time-based) when there is no sensor or the
reading is unreliable (unavailable/non-numeric/counter-reset). No early stop.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 2: Credit the measured volume + wire into the sweep

**Files:** Modify `distributor.py` (`_dist_credit_zone` `:606`, sweep window `:902-929`); Test `tests/test_distributor.py`, `tests/test_distributor_dispatch.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_distributor.py`:
```python
async def test_credit_zone_uses_measured_volume_when_given():
    c = _host()
    c.store.async_update_zone = AsyncMock()
    c._record_run = AsyncMock()
    c._credited_depth_native = Mock(return_value=1.0)
    c._timed_volume_l = Mock(return_value=999.0)  # must NOT be used
    z = {const.ZONE_ID: 7, const.ZONE_BUCKET: -5.0}
    await c._dist_credit_zone(z, 120, measured_l=8.0)
    c._timed_volume_l.assert_not_called()
    assert c._record_run.await_args.kwargs["volume_l"] == 8.0


async def test_credit_zone_falls_back_to_timed_when_measured_none():
    c = _host()
    c.store.async_update_zone = AsyncMock()
    c._record_run = AsyncMock()
    c._credited_depth_native = Mock(return_value=1.0)
    c._timed_volume_l = Mock(return_value=4.0)
    z = {const.ZONE_ID: 7, const.ZONE_BUCKET: -5.0}
    await c._dist_credit_zone(z, 120, measured_l=None)
    c._timed_volume_l.assert_called_once()
    assert c._record_run.await_args.kwargs["volume_l"] == 4.0
```

Add a sweep-level test to `tests/test_distributor_dispatch.py` (mirror `_cycle_mocks`):
```python
async def test_sweep_credits_measured_flow_volume():
    c = _host()
    c._dist_uses_master = Mock(return_value=False)
    _cycle_mocks(c)
    c._dist_needs_water = Mock(return_value=True)
    # measure returns 9.0 L for the single watered outlet
    c._dist_measure_window = AsyncMock(return_value=9.0)
    credited = {}
    c._dist_credit_zone = AsyncMock(
        side_effect=lambda z, s, measured_l=None: credited.update(v=measured_l)
    )
    c.store.async_get_zones = AsyncMock(
        return_value=[
            {"id": 7, "distributor_id": 0, "outlet_number": 1, "duration": 60,
             "bucket": -1, "bucket_threshold": 0, "state": "automatic"}
        ]
    )
    await c.async_run_distributor_cycle(_dist(id=0, current_outlet=1))
    assert credited["v"] == 9.0  # the measured volume reached crediting
```

- [ ] **Step 2: Run to verify failure**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "credit_zone_uses_measured or credit_zone_falls_back or sweep_credits_measured" -q
```
Expected: FAIL (`_dist_credit_zone` has no `measured_l`; sweep calls `_dist_sleep`, not `_dist_measure_window`).

- [ ] **Step 3: `_dist_credit_zone` gains `measured_l`**

Change the `_dist_credit_zone` signature + volume line (`distributor.py:606`):
```python
    async def _dist_credit_zone(
        self, zone: dict, seconds: float, measured_l: float | None = None
    ) -> None:
        """Credit a watered member zone's bucket and log the run. When a flow meter
        measured the delivered volume (Part A), credit that; otherwise fall back to
        the time-based estimate (_timed_volume_l)."""
        zone_id = zone.get(const.ZONE_ID)
        volume_l = (
            measured_l
            if measured_l is not None
            else self._timed_volume_l(zone, seconds)
        )
        depth = self._credited_depth_native(zone, volume_l)
```
(The rest of the method — `new_bucket`, ceiling cap, `async_update_zone`, `_record_run(volume_l=volume_l, ...)` — is unchanged.)

- [ ] **Step 4: Wire the sweep window (`:926-928`)**

Replace:
```python
            await self._dist_sleep(window)
            if water:
                await self._dist_credit_zone(zone, window)
```
with:
```python
            measured = await self._dist_measure_window(distributor, window)
            if water:
                await self._dist_credit_zone(zone, window, measured_l=measured)
```
(`_dist_measure_window` sleeps the full window itself — with or without a flow sensor — so the timing is unchanged. For a distributor without `flow_sensor` it does a single `_dist_sleep(window)` and returns None, so the time-based credit path is byte-for-byte the old behaviour.)

- [ ] **Step 5: Run the new tests + the full distributor suite**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock tests/test_distributor.py tests/test_distributor_dispatch.py tests/test_distributor_cycle.py tests/test_distributor_integration.py -q
```
Expected: PASS. The existing cycle tests mock `_cycle_mocks` (which mocks `_dist_sleep`); those distributors have no `flow_sensor` in `_dist()`, so `_dist_measure_window` takes the no-sensor branch (`_dist_sleep(window)` + None) — behaviour unchanged. `_cycle_mocks` may need `_dist_measure_window` NOT mocked (it isn't) so the real no-sensor branch runs; verify these stay green and, if any cycle test asserted `_dist_sleep` await args for the window, it still holds (the no-sensor branch calls `_dist_sleep(window)`).

- [ ] **Step 6: black + commit**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
"$OLD/uvenv312/Scripts/python.exe" -m black custom_components/smart_irrigation/distributor.py tests/test_distributor.py tests/test_distributor_dispatch.py
git add custom_components/smart_irrigation/distributor.py tests/test_distributor.py tests/test_distributor_dispatch.py
git commit -F - <<'EOF'
feat(distributor): credit the measured flow volume per member window

_dist_credit_zone takes an optional measured_l and credits it (bucket + run-log)
instead of the time estimate; the sweep replaces the per-outlet sleep with
_dist_measure_window and threads the measured litres into crediting. No sensor or an
unreliable reading -> unchanged time-based crediting.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 3: Frontend — flow_sensor help text (8 languages)

**Files:** Modify `frontend/localize/languages/{en,de,nl,fr,es,it,no,sk}.json`

- [ ] **Step 1: Update the help string**

Find the distributor `flow_sensor` help key in each language file (grep `flow_sensor` under `panels.distributors`). Its text currently says the meter is "not yet active" / for a future feature. Replace with wording that it now measures the actual delivered volume per outlet and is used for bucket crediting (still optional). English example:
`"The shared inlet water meter. When set, the actual delivered volume per outlet is measured and credited (instead of the time estimate). Optional; a cumulative counter (L/m³) or a flow rate (L/min) both work."`
German:
`"Der geteilte Einlass-Wasserzähler. Wenn gesetzt, wird die tatsächlich abgegebene Menge pro Ausgang gemessen und verbucht (statt der Zeitschätzung). Optional; ein kumulativer Zähler (L/m³) oder eine Durchflussrate (L/min) funktionieren beide."`
Translate for the other 6, matching each file's tone. Keep the KEY name; only change the value.

- [ ] **Step 2: Build + verify parse**
```bash
cd custom_components/smart_irrigation/frontend
npm run build 2>&1 | tail -3
node -e "for (const l of ['en','de','nl','fr','es','it','no','sk']) JSON.parse(require('fs').readFileSync('localize/languages/'+l+'.json'))" && echo OK
```
Expected: build succeeds; all 8 parse. (Do NOT commit dist — the release task rebuilds it.)

- [ ] **Step 3: Commit**
```bash
git add custom_components/smart_irrigation/frontend/localize/languages
git commit -F - <<'EOF'
i18n(distributor): flow_sensor help now describes live volume metering (8 languages)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 4: Regression, code review, release (b23)

- [ ] **Step 1: Full backend suite vs baseline (no new failures) + black --check.**
- [ ] **Step 2: Code-review checkpoint** — dispatch `superpowers:code-reviewer` on the Part A diff vs the spec (focus: fail-safe never breaks watering; cumulative vs rate correctness; no timing change; no-sensor path unchanged).
- [ ] **Step 3: Version bump b22 -> b23** (const.py, manifest.json, package.json) + `npm run build` (bakes b23 + the help text); same recipe as prior betas.
- [ ] **Step 4: Release** — show notes for approval (REGEL 5), then push + `gh release create v2026.07.11b23 --repo Eifel-Joe/HAsmartirrigation --prerelease --target feature/gardena-distributor`.
- [ ] **Step 5: Update memories** — `hasi-flow-volume-tracking-feature` (Part A shipped in b23, Part B next).

---

## Self-review

- **Spec coverage:** measurement poll-loop (cumulative + rate, unit-classified) → Task 1; crediting measured litres + sweep wiring → Task 2; fail-safe → time-based (unavailable/non-numeric/reset/no-sensor) → Tasks 1-2 tests; gating presence-based + help text → Task 2 (gating) + Task 3 (i18n); no early stop → out of scope, enforced by "full window always elapses". All spec sections mapped.
- **Placeholders:** none — full test + impl code; `DISTRIBUTOR_FLOW_POLL_SECONDS` pinned at 5.
- **Type/name consistency:** `_dist_measure_window`, `_dist_read_flow`, `_dist_flow_unit_is_rate`, `_dist_flow_litres_from_total`, `_dist_credit_zone(..., measured_l=None)`, `DISTRIBUTOR_FLOW_POLL_SECONDS`, and the reused `_flow_rate_to_l_per_min`/`_timed_volume_l`/`_credited_depth_native` names are consistent across tasks and match the current code.
