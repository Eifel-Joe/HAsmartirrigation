# Unified Flow-Measurement Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One shared, unit-tested flow-measurement engine (`FlowMeter`) that correctly measures delivered litres for a rate sensor, a per-run-reset counter (Sonoff/Z2M), and a lifetime totalizer — used by all three metered paths (linked-entity, self-closing/service, distributor), with a per-zone override and safe time-based fallbacks.

**Architecture:** A new pure-Python `flow_metering.py` holds the three unit-conversion functions (moved out of `irrigation.py`), a stateful `FlowMeter` fed one reading per poll (explicit `per_run`/`lifetime`; `lifetime` = keep-baseline never-over-credit, `per_run` = reseed once at the open reset), and two pure **cross-run learning** functions. The learning (which resolves an `auto` sensor to `per_run`/`lifetime` by observing whether it resets each run) lives in the coordinator + store, keyed per zone/distributor. Each call site reads its raw sensor and feeds the engine: the two blocking poll loops (linked-entity, distributor) feed it inline; the fire-and-forget self-closing path feeds it from a **non-blocking scheduled interval** and finalizes at run finish/stop. The calibration advisory generalizes from distributor-members to any can't-stop measured run (service zones included).

**Design note (REVISION 1):** the spec's REVISION 1 supersedes its original single-run `auto` heuristic (proven to over-credit by adversarial verification). The engine is `per_run`/`lifetime` only; `auto` is resolved across runs by the learning layer (`flow_reset_streak` >= 2 → `per_run`, else `lifetime`-safe). Tasks below implement REVISION 1.

**Tech Stack:** Python 3.12, Home Assistant custom integration, `attrs` store models, `voluptuous` websocket schemas, Lit/TypeScript frontend, pytest.

---

## Spec

`docs/superpowers/specs/2026-07-13-unified-flow-measurement-engine-design.md` (approved 2026-07-13).

**One correction vs the spec wording:** the spec says "add a light poll loop" to `async_run_self_closing`. That function is **fire-and-forget** (opens the valve, credits the bucket optimistically, schedules a cosmetic finish via `_sc_schedule_cleanup`, and returns immediately — the hardware owns the close). A *blocking* poll loop there would break the concurrency model. Task FM-5 therefore implements the spec's **intent** (sample the sensor across the run window, credit the measured volume) via a **non-blocking `async_track_time_interval`** started at open and cancelled at finish/stop. Behaviour (run timing, optimistic bucket credit) is unchanged; only sampling + a measured-vs-timed correction are added.

## File Structure

- **Create** `custom_components/smart_irrigation/flow_metering.py` — pure engine: `flow_rate_to_l_per_min`, `flow_is_totalizer`, `flow_litres_from_total`, `class FlowMeter`. No HA imports.
- **Create** `tests/test_flow_meter.py` — isolated engine unit tests (no HA).
- **Modify** `const.py` — `ZONE_FLOW_COUNTER_TYPE` + `FLOW_COUNTER_*` values + `FLOW_RESET_WINDOW_S` / `FLOW_NEAR_ZERO_FRAC` / `FLOW_NEAR_ZERO_FLOOR`.
- **Modify** `store.py` — `flow_counter_type` attr + `async_load` passthrough.
- **Modify** `websockets.py` — zone schema passthrough for `flow_counter_type`.
- **Modify** `irrigation.py` — delegate the 3 staticmethods to `flow_metering`; rework `_run_valve_metered` + `_irrigate_zone_flow_slot` (+ rotating orchestrator) to the engine; retire `_read_flow_increment` / `_flow_last_total`; add `_read_flow_sample`; add shared `_flow_calibration_check`.
- **Modify** `self_closing.py` — non-blocking interval sampling + measured finalize in `_sc_finish_run` / `async_stop_self_closing` + advisory.
- **Modify** `distributor.py` — `_dist_measure_window` → `FlowMeter`; call shared `_flow_calibration_check`.
- **Modify** `frontend/src/views/zones/view-zone-settings.ts` + `frontend/src/localize/languages/*.json` — conditional `flow_counter_type` select + i18n (8 langs).

## Conventions

- **Repo root:** `D:/Entwicklung/HASI/HAsmartirrigation`.
- **Python:** `.venv/Scripts/python.exe` (3.12).
- **Engine test (no HA):** `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_flow_meter.py -q`
- **HA-touching test:** append `-p _local_socket_unblock` (e.g. `... -m pytest tests/test_self_closing.py -p _local_socket_unblock -q`).
- **Known env baseline:** the full suite has pre-existing failures in `test_init` / `test_panel` / `test_watering_calendar` / `test_schedule_time_anchor` / `test_create_returns_id` (env artifacts, identical on production). "Full suite green" below means **no *new* failures vs this baseline**.
- **Format/lint:** `uvx black custom_components/smart_irrigation tests` and `uvx ruff check custom_components/smart_irrigation tests` (both must be clean).
- Follow the inline-documentation rules (REGEL 4): patch identifier, root, fix logic, test ref.

---

## REVISION 1 — AUTHORITATIVE (supersedes the original FM-1/FM-2 code blocks + adds learning hooks to FM-3/5/6)

The original FM-1 engine (single-run `auto` with `reset_window_s`/deferred confirmation) was proven to over-credit by adversarial verification. Per spec REVISION 1 the engine is `per_run`/`lifetime` only, and `auto` is resolved **across runs** by a learning layer. **Implement the code in THIS section; ignore the superseded `reset_window_s`/deferred-confirmation code in the original FM-1/FM-2 bodies further down.** The other tasks (FM-4/7/8/9) are unaffected except where noted.

### FM-1 (revised): pure engine + learning functions + tests

`custom_components/smart_irrigation/flow_metering.py` — FULL content:

```python
"""Unified flow-measurement engine + cross-run learning for Smart Irrigation.

A ``FlowMeter`` measures delivered litres for one run of one flow sensor:

* **rate** sensor (unit contains ``/``) — integrate ``rate x dt`` (monotonic-safe on at);
* **per-run counter** (``counter_type='per_run'``) — resets toward 0 at valve-open then
  holds the run's accumulated volume: reseed the baseline **once**, on the first near-zero
  drop (the open reset), then keep-baseline; credits the run's climb from the reset floor;
* **lifetime totalizer** (``counter_type='lifetime'`` — also the safe default for anything
  else, incl. ``'auto'``) — pure keep-baseline: a rise credits ``litres-last``, a drop keeps
  ``last`` and credits nothing. NEVER over-credits (the CFV-3 invariant).

The engine takes an EXPLICIT ``per_run``/``lifetime`` type — it does not auto-detect the
counter kind, because a per-run reset and a lifetime totalizer glitching to near-zero then
partially recovering are indistinguishable within one run (adversarial verification proved
the single-run heuristic over-credits). The kind is learned ACROSS runs by the two pure
functions below (``flow_learn_next_streak`` / ``flow_learn_resolve``), whose state
(``flow_last_end`` / ``flow_reset_streak``) the coordinator persists per zone/distributor.
Pure Python (no Home Assistant imports) so it is unit-tested in isolation.
"""

from __future__ import annotations

import math

# Cross-run learning tunables (see flow_learn_next_streak / flow_learn_resolve).
FLOW_LEARN_RESET_FACTOR = 0.5  # start < FACTOR x prev_end at a run's open == a reset
FLOW_LEARN_MIN_PREV_END = 1.0  # a prior end at/below this is too small to judge a reset
FLOW_LEARN_RESET_STREAK_THRESHOLD = 2  # consecutive open-resets that classify per_run


def flow_rate_to_l_per_min(value: float, unit: str) -> float:
    """Convert an instantaneous flow-rate reading to L/min."""
    u = (unit or "").lower().strip()
    if u in ("l/h", "liter/h", "liter/hour", "liters/hour", "liters/h"):
        return value / 60.0
    if u in ("m³/h", "m3/h", "m³/hour", "m3/hour"):
        return value * 1000.0 / 60.0
    if u in ("m³/min", "m3/min"):
        return value * 1000.0
    if u in ("gal/min", "gpm", "gallon/min", "gallons/min"):
        return value * 3.785411784
    if u in ("gal/h", "gal/hour", "gallon/h", "gallons/h"):
        return value * 3.785411784 / 60.0
    return value  # assume L/min


def flow_is_totalizer(unit: str, state_class: str | None) -> bool:
    """True when a flow sensor is a cumulative counter (vs an instantaneous rate)."""
    if state_class == "total_increasing":
        return True
    u = (unit or "").strip()
    if not u or "/" in u:
        return False
    return u.lower() not in ("gpm", "lpm", "gph", "lph")


def flow_litres_from_total(value: float, unit: str) -> float:
    """Convert a cumulative counter reading to litres (m³x1000, galx3.785, else L)."""
    u = (unit or "").lower().strip()
    if u in ("m³", "m3", "cubic meter", "cubic meters"):
        return float(value) * 1000.0
    if u in ("gal", "gallon", "gallons"):
        return float(value) * 3.785411784
    return float(value)  # L / l / liter(s) / unknown -> assume litres


def flow_learn_next_streak(prev_end, start_litres: float, streak: int) -> int:
    """Update the consecutive-open-reset streak from one run's open observation.

    No usable prior (``prev_end`` None or <= FLOW_LEARN_MIN_PREV_END) -> unchanged; a reset
    (``start_litres < FLOW_LEARN_RESET_FACTOR x prev_end``) -> ``streak + 1``; a monotonic
    open (start >= that) -> 0. A per-run counter resets to ~0 each run (start << prev_end);
    a lifetime totalizer is monotonic (start >= prev_end)."""
    if prev_end is None or prev_end <= FLOW_LEARN_MIN_PREV_END:
        return streak
    if start_litres < FLOW_LEARN_RESET_FACTOR * prev_end:
        return streak + 1
    return 0


def flow_learn_resolve(override, streak: int) -> str:
    """Resolve a sensor's counter type: an explicit ``per_run``/``lifetime`` override wins;
    else (``auto``/unknown) ``per_run`` once the streak reaches the threshold, else the
    over-credit-safe ``lifetime``."""
    o = (override or "auto").lower()
    if o in ("per_run", "lifetime"):
        return o
    return "per_run" if streak >= FLOW_LEARN_RESET_STREAK_THRESHOLD else "lifetime"


class FlowMeter:
    """Stateful per-run flow accumulator. See the module docstring."""

    def __init__(
        self,
        counter_type: str = "lifetime",
        *,
        near_zero_frac: float = 0.1,
        near_zero_floor: float = 1.0,
    ) -> None:
        # per_run reseeds once at the open reset; anything else (lifetime/auto/unknown)
        # never reseeds (keep-baseline, over-credit-safe).
        self._per_run = (counter_type or "").lower() == "per_run"
        self._near_zero_frac = float(near_zero_frac)
        self._near_zero_floor = float(near_zero_floor)
        self._is_totalizer: bool | None = None
        self._last_at: float | None = None  # rate: previous sample time
        self._last: float | None = None  # totalizer: previous litres baseline
        self._delivered = 0.0
        self._have_reading = False
        self._reset_done = False  # per_run: the one-time open reset already consumed

    def sample(self, value, unit: str, state_class: str | None, at: float) -> None:
        """Feed one poll reading. ``value`` may be None/non-numeric/NaN (ignored). ``at``
        is monotonic seconds since run start (the first sample defines t0)."""
        if value is None:
            return
        try:
            raw = float(value)
        except (ValueError, TypeError):
            return
        if not math.isfinite(raw):
            return  # NaN/inf: treat like an unavailable tick (ignore, don't poison)
        self._have_reading = True
        if self._is_totalizer is None:
            self._is_totalizer = flow_is_totalizer(unit, state_class)
        if self._is_totalizer:
            self._sample_totalizer(raw, unit)
        else:
            self._sample_rate(raw, unit, at)

    def _sample_rate(self, raw: float, unit: str, at: float) -> None:
        if self._last_at is not None and at > self._last_at:
            self._delivered += flow_rate_to_l_per_min(raw, unit) * (at - self._last_at) / 60.0
        if self._last_at is None or at > self._last_at:
            self._last_at = at

    def _sample_totalizer(self, raw: float, unit: str) -> None:
        litres = flow_litres_from_total(raw, unit)
        if self._last is None:  # seed the baseline
            self._last = litres
            return
        if litres >= self._last:  # rising: credit the true climb
            self._delivered += litres - self._last
            self._last = litres
            return
        # a drop: the one-time per-run open reset, else a glitch (keep baseline).
        if self._per_run and not self._reset_done and litres <= self._near_zero():
            self._last = litres  # reseed to the reset floor (credit nothing)
            self._reset_done = True
        # else glitch (or lifetime): keep _last, add nothing (never over-credit a dip)

    def _near_zero(self) -> float:
        return max(self._near_zero_floor, self._near_zero_frac * (self._last or 0.0))

    def delivered(self) -> float | None:
        """Measured litres this run, or None if no numeric reading was ever seen (the
        caller falls back to time-based). A live-but-dry meter returns 0.0."""
        if not self._have_reading:
            return None
        return self._delivered

    def last_total(self) -> float | None:
        """The last totalizer litres seen (the run's end value, for cross-run learning),
        or None for a rate sensor / no totalizer reading."""
        return self._last if self._is_totalizer else None
```

`tests/test_flow_meter.py` — FULL content:

```python
"""Unit tests for the pure FlowMeter engine + learning functions (no Home Assistant)."""

from custom_components.smart_irrigation.flow_metering import (
    FlowMeter,
    flow_is_totalizer,
    flow_learn_next_streak,
    flow_learn_resolve,
    flow_litres_from_total,
    flow_rate_to_l_per_min,
)


def _feed(meter, series):
    for value, unit, state_class, at in series:
        meter.sample(value, unit, state_class, at)
    return meter.delivered()


# --- rate ---
def test_rate_sensor_integrates_over_time():
    m = FlowMeter()
    assert _feed(m, [(6.0, "L/min", None, float(t)) for t in range(0, 121, 15)]) == 12.0


def test_rate_gpm_is_not_a_totalizer():
    assert flow_is_totalizer("gpm", None) is False
    m = FlowMeter()
    assert _feed(m, [(1.0, "gpm", None, 0.0), (1.0, "gpm", None, 60.0)]) == 3.785411784


def test_rate_non_monotonic_at_does_not_double_count():
    m = FlowMeter()
    series = [
        (6.0, "L/min", None, 0.0),
        (6.0, "L/min", None, 60.0),
        (6.0, "L/min", None, 30.0),  # backward -> skipped, no double count
        (6.0, "L/min", None, 90.0),
    ]
    assert _feed(m, series) == 9.0


# --- per_run (explicit) ---
def test_per_run_reset_at_open_credits_final():
    m = FlowMeter("per_run")
    series = [
        (62.0, "L", None, 0.0),
        (0.0, "L", None, 15.0),
        (3.0, "L", None, 30.0),
        (6.0, "L", None, 45.0),
        (9.0, "L", None, 60.0),
        (12.0, "L", None, 75.0),
        (12.0, "L", None, 120.0),
    ]
    assert _feed(m, series) == 12.0


def test_per_run_already_reset_at_open():
    m = FlowMeter("per_run")
    assert _feed(m, [(0.0, "L", None, 0.0), (5.0, "L", None, 30.0), (12.0, "L", None, 90.0)]) == 12.0


def test_per_run_coarse_reset_credits_full():
    m = FlowMeter("per_run")
    assert _feed(m, [(62.0, "L", None, 0.0), (0.0, "L", None, 15.0), (12.0, "L", None, 30.0)]) == 12.0


def test_per_run_reseeds_once_later_glitch_kept():
    m = FlowMeter("per_run")
    series = [
        (62.0, "L", None, 0.0),
        (0.0, "L", None, 15.0),
        (3.0, "L", None, 30.0),
        (6.0, "L", None, 45.0),
        (0.1, "L", None, 60.0),  # later near-zero dip -> glitch (already reseeded)
        (9.0, "L", None, 75.0),
        (12.0, "L", None, 90.0),
    ]
    assert _feed(m, series) == 12.0


def test_per_run_delayed_reset_any_time():
    m = FlowMeter("per_run")
    series = [(62.0, "L", None, 0.0), (62.0, "L", None, 20.0), (0.0, "L", None, 90.0), (4.0, "L", None, 120.0)]
    assert _feed(m, series) == 4.0


# --- lifetime (explicit) ---
def test_lifetime_credits_end_minus_start():
    m = FlowMeter("lifetime")
    assert _feed(m, [(1000.0, "L", "total_increasing", 0.0), (1012.0, "L", "total_increasing", 90.0)]) == 12.0


def test_lifetime_glitch_low_keeps_baseline():
    m = FlowMeter("lifetime")
    series = [
        (1000.0, "L", "total_increasing", 0.0),
        (1005.0, "L", "total_increasing", 40.0),
        (2.0, "L", "total_increasing", 55.0),
        (1006.0, "L", "total_increasing", 70.0),
    ]
    assert _feed(m, series) == 6.0


def test_lifetime_partial_rebound_no_over_credit():
    # THE adversarial case: glitch to near-zero then partial recovery must credit only
    # the true delta above baseline (1 L), never the phantom climb from the low.
    m = FlowMeter("lifetime")
    series = [(1000.0, "L", None, 0.0), (0.5, "L", None, 10.0), (800.0, "L", None, 20.0), (1001.0, "L", None, 30.0)]
    assert _feed(m, series) == 1.0


def test_lifetime_drop_and_stay_credits_zero():
    m = FlowMeter("lifetime")
    assert _feed(m, [(1000.0, "L", None, 0.0), (0.5, "L", None, 10.0), (800.0, "L", None, 20.0)]) == 0.0


# --- default / auto string is lifetime-safe ---
def test_default_counter_type_is_lifetime_safe():
    m = FlowMeter()
    assert _feed(m, [(62.0, "L", None, 0.0), (0.0, "L", None, 15.0), (12.0, "L", None, 30.0)]) == 0.0


def test_auto_string_treated_as_lifetime_safe():
    m = FlowMeter("auto")
    assert _feed(m, [(62.0, "L", None, 0.0), (0.0, "L", None, 15.0), (12.0, "L", None, 30.0)]) == 0.0


# --- guards ---
def test_no_numeric_reading_returns_none():
    m = FlowMeter()
    m.sample(None, "L/min", None, 0.0)
    m.sample("unavailable", "L/min", None, 15.0)
    assert m.delivered() is None


def test_dry_meter_returns_zero_not_none():
    m = FlowMeter("lifetime")
    assert _feed(m, [(5.0, "L", None, 0.0), (5.0, "L", None, 60.0)]) == 0.0


def test_nan_reading_ignored():
    m = FlowMeter("lifetime")
    assert _feed(m, [(1000.0, "L", None, 0.0), (float("nan"), "L", None, 10.0), (1005.0, "L", None, 20.0)]) == 5.0


def test_last_total_reports_end_value():
    m = FlowMeter("lifetime")
    _feed(m, [(1000.0, "L", None, 0.0), (1005.0, "L", None, 20.0)])
    assert m.last_total() == 1005.0
    r = FlowMeter()
    _feed(r, [(6.0, "L/min", None, 0.0), (6.0, "L/min", None, 60.0)])
    assert r.last_total() is None


def test_unit_conversions():
    assert flow_litres_from_total(2.0, "m³") == 2000.0
    assert flow_litres_from_total(1.0, "gal") == 3.785411784
    assert flow_rate_to_l_per_min(60.0, "L/h") == 1.0
    assert flow_is_totalizer("L", None) is True
    assert flow_is_totalizer("L/min", None) is False
    assert flow_is_totalizer("", "total_increasing") is True


# --- learning functions ---
def test_learn_next_streak_no_usable_prior():
    assert flow_learn_next_streak(None, 5.0, 0) == 0
    assert flow_learn_next_streak(0.5, 0.1, 3) == 3  # prev_end <= 1.0 -> unchanged


def test_learn_next_streak_reset_increments():
    assert flow_learn_next_streak(62.0, 0.4, 1) == 2  # 0.4 < 0.5*62 -> reset


def test_learn_next_streak_monotonic_zeroes():
    assert flow_learn_next_streak(62.0, 62.0, 3) == 0
    assert flow_learn_next_streak(1000.0, 1002.0, 2) == 0


def test_learn_resolve_override_wins():
    assert flow_learn_resolve("per_run", 0) == "per_run"
    assert flow_learn_resolve("lifetime", 5) == "lifetime"


def test_learn_resolve_auto_by_streak():
    assert flow_learn_resolve("auto", 0) == "lifetime"
    assert flow_learn_resolve("auto", 1) == "lifetime"
    assert flow_learn_resolve("auto", 2) == "per_run"
    assert flow_learn_resolve(None, 2) == "per_run"
```

Run (all tasks in REVISION 1 use the socket-unblock plugin — a repo-wide autouse conftest
fixture needs it even for the pure engine test):
`cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_flow_meter.py -q -p _local_socket_unblock` → all pass. Then `uvx black` + `uvx ruff check` clean. Commit.

### FM-2 (revised): store fields

const.py — keep `ZONE_FLOW_COUNTER_TYPE` + `FLOW_COUNTER_AUTO/PER_RUN/LIFETIME` + `FLOW_NEAR_ZERO_FRAC`/`FLOW_NEAR_ZERO_FLOOR`. **Drop `FLOW_RESET_WINDOW_S`** (unused). **Add:**

```python
ZONE_FLOW_LAST_END = "flow_last_end"  # cross-run learning: prev run's end litres
ZONE_FLOW_RESET_STREAK = "flow_reset_streak"  # consecutive open-resets observed
```

store.py — after `flow_counter_type = attr.ib(type=str, default="auto")` add:

```python
    # Cross-run flow-counter learning (auto mode): the previous run's end value (litres)
    # and the consecutive-open-reset streak. Additive; resolve per_run once the streak
    # reaches FLOW_LEARN_RESET_STREAK_THRESHOLD. See flow_metering.flow_learn_*.
    flow_last_end = attr.ib(type=float, default=None)
    flow_reset_streak = attr.ib(type=int, default=0)
```

Add both to the `const` import block and to `async_load` (next to `flow_counter_type`):

```python
                        flow_last_end=zone.get(ZONE_FLOW_LAST_END, None),
                        flow_reset_streak=zone.get(ZONE_FLOW_RESET_STREAK, 0) or 0,
```

websockets.py — the `flow_counter_type` passthrough stays; `flow_last_end`/`flow_reset_streak` are internal (NOT added to the CRUD schema — they must not be user-set). The distributor store object gets the same two fields (find the distributor attrs model + its load, mirror `flow_last_end`/`flow_reset_streak`; if the distributor is stored as a plain dict rather than an attrs model, the learning helper's `.get(...)` defaults cover absence — no model change needed, just persist via `_dist_store_update`).

Store test: default `flow_reset_streak == 0`, `flow_last_end is None`, and both round-trip.

### Learning hooks for FM-3 / FM-5 / FM-6 (shared)

Add these two helpers to the base mixin (`irrigation.py`), used by all three metered paths:

```python
    def _flow_build_meter(self, cfg: dict, sample):
        """Build a run's FlowMeter with the counter type resolved from the per-zone
        override or the learned cross-run streak, and return (meter, start_changes) where
        start_changes is a store dict to persist (an updated flow_reset_streak) or {}.
        ``sample`` is the valve-open (value, unit, state_class) read or None.

        Learning only applies to a totalizer sensor; a rate sensor / no reading resolves
        to the safe 'lifetime' default with no streak change."""
        override = cfg.get(const.ZONE_FLOW_COUNTER_TYPE, "auto")
        streak = int(cfg.get(const.ZONE_FLOW_RESET_STREAK) or 0)
        changes = {}
        if sample is not None and flow_is_totalizer(sample[1], sample[2]):
            start_l = flow_litres_from_total(sample[0], sample[1])
            new_streak = flow_learn_next_streak(
                cfg.get(const.ZONE_FLOW_LAST_END), start_l, streak
            )
            if new_streak != streak:
                changes[const.ZONE_FLOW_RESET_STREAK] = new_streak
            streak = new_streak
        resolved = flow_learn_resolve(override, streak)
        meter = FlowMeter(
            resolved,
            near_zero_frac=const.FLOW_NEAR_ZERO_FRAC,
            near_zero_floor=const.FLOW_NEAR_ZERO_FLOOR,
        )
        if sample is not None:
            meter.sample(*sample, at=0.0)  # valve-open seed
        return meter, changes

    def _flow_end_changes(self, meter) -> dict:
        """Store dict persisting this run's end value for the next run's reset check."""
        end = meter.last_total()
        return {} if end is None else {const.ZONE_FLOW_LAST_END: end}
```

**Each integration task (FM-3 linked-entity, FM-5 self-closing, FM-6 distributor):** replace the bare `FlowMeter(counter_type=...)` construction with `meter, start_changes = self._flow_build_meter(cfg, sample)`; persist `start_changes` at run start via the path's store update (`async_update_zone(zone_id, start_changes)` when non-empty; distributor: `_dist_store_update(dist_id, start_changes)`), and at run end persist `self._flow_end_changes(meter)` likewise. `cfg` is the zone (FM-3/5) or the distributor dict (FM-6); the distributor uses the same `ZONE_FLOW_*` keys on its own object. Each path adds a test that two consecutive per-run-reset runs flip the resolved type to measured (learning), and that `flow_last_end` is persisted at run end.

---

### Task FM-1: The `FlowMeter` engine + unit tests

> **⚠ SUPERSEDED by REVISION 1 above.** The engine/test code in this original block uses the removed single-run `reset_window_s`/deferred-confirmation `auto` design. Implement the REVISION 1 FM-1 instead. Kept for history.

**Files:**
- Create: `custom_components/smart_irrigation/flow_metering.py`
- Test: `tests/test_flow_meter.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_flow_meter.py`:

```python
"""Unit tests for the pure FlowMeter engine (no Home Assistant)."""

from custom_components.smart_irrigation.flow_metering import (
    FlowMeter,
    flow_is_totalizer,
    flow_litres_from_total,
    flow_rate_to_l_per_min,
)


def _feed(meter, series):
    """series: list of (value, unit, state_class, at)."""
    for value, unit, state_class, at in series:
        meter.sample(value, unit, state_class, at)
    return meter.delivered()


def test_rate_sensor_integrates_over_time():
    # 6 L/min steady for 120 s (samples every 15 s) -> ~12 L.
    m = FlowMeter()
    series = [(6.0, "L/min", None, float(t)) for t in range(0, 121, 15)]
    assert _feed(m, series) == 12.0


def test_rate_gpm_is_not_a_totalizer():
    # gpm is a rate abbreviation, not a totalizer unit.
    assert flow_is_totalizer("gpm", None) is False
    m = FlowMeter()
    # 1 gal/min for 60 s = 3.785411784 L.
    assert _feed(m, [(1.0, "gpm", None, 0.0), (1.0, "gpm", None, 60.0)]) == 3.785411784


def test_per_run_counter_reset_at_open_credits_final():
    # Verified Sonoff trace: 62 (stale) -> 0 (reset) -> climbs to 12; hold 12.
    m = FlowMeter()
    series = [
        (62.0, "L", None, 0.0),
        (0.0, "L", None, 15.0),
        (3.0, "L", None, 30.0),
        (6.0, "L", None, 45.0),
        (9.0, "L", None, 60.0),
        (12.0, "L", None, 75.0),
        (12.0, "L", None, 120.0),
    ]
    assert _feed(m, series) == 12.0


def test_per_run_counter_already_reset_at_open():
    # First read already caught 0; climbs to 12.
    m = FlowMeter()
    series = [(0.0, "L", None, 0.0), (5.0, "L", None, 30.0), (12.0, "L", None, 90.0)]
    assert _feed(m, series) == 12.0


def test_lifetime_totalizer_credits_end_minus_start():
    m = FlowMeter()
    series = [(1000.0, "L", "total_increasing", 0.0), (1012.0, "L", "total_increasing", 90.0)]
    assert _feed(m, series) == 12.0


def test_glitch_low_keeps_baseline_no_over_credit():
    # Lifetime counter dips to a low value mid-run then recovers: the recovery
    # must NOT credit the phantom climb from the dip (CFV-3 keep-baseline fix).
    m = FlowMeter(counter_type="lifetime")
    series = [
        (1000.0, "L", "total_increasing", 0.0),
        (1005.0, "L", "total_increasing", 40.0),  # +5
        (2.0, "L", "total_increasing", 55.0),     # glitch low (ignored, keep 1005)
        (1006.0, "L", "total_increasing", 70.0),  # +1 over 1005, not +1004
    ]
    assert _feed(m, series) == 6.0


def test_lifetime_override_never_resets_even_near_zero_in_window():
    # A near-zero drop within the reset window under 'lifetime' is a glitch, not a
    # reset -> baseline kept -> no phantom credit on recovery.
    m = FlowMeter(counter_type="lifetime")
    series = [
        (500.0, "L", None, 0.0),
        (0.5, "L", None, 10.0),    # near-zero, in window, but lifetime -> glitch
        (503.0, "L", None, 40.0),  # +3 over 500
    ]
    assert _feed(m, series) == 3.0


def test_per_run_override_resets_on_near_zero_drop_any_time():
    # 'per_run' treats a near-zero drop as a reset regardless of the window (covers
    # a delayed reset the user reported).
    m = FlowMeter(counter_type="per_run")
    series = [
        (62.0, "L", None, 0.0),
        (62.0, "L", None, 20.0),
        (0.0, "L", None, 90.0),   # delayed reset, OUTSIDE the 30 s window
        (4.0, "L", None, 120.0),
    ]
    assert _feed(m, series) == 4.0


def test_auto_delayed_reset_outside_window_falls_back_safe():
    # Under 'auto', a near-zero drop after the window is treated as a glitch, so a
    # per-run counter with a very delayed reset under-credits (safe) rather than
    # over-credits. delivered() stays 0.0 (fallback), never negative/inflated.
    m = FlowMeter(counter_type="auto")
    series = [
        (62.0, "L", None, 0.0),
        (0.0, "L", None, 90.0),   # delayed reset OUTSIDE window -> glitch, keep 62
        (4.0, "L", None, 120.0),  # 4 < 62 -> glitch, keep 62
    ]
    assert _feed(m, series) == 0.0


def test_no_numeric_reading_returns_none():
    m = FlowMeter()
    m.sample(None, "L/min", None, 0.0)
    m.sample("unavailable", "L/min", None, 15.0)
    assert m.delivered() is None


def test_dry_meter_returns_zero_not_none():
    # Readings seen, no flow -> 0.0 (caller distinguishes dry from 'no sensor').
    m = FlowMeter()
    assert _feed(m, [(5.0, "L", None, 0.0), (5.0, "L", None, 60.0)]) == 0.0


def test_unit_conversions():
    assert flow_litres_from_total(2.0, "m³") == 2000.0
    assert flow_litres_from_total(1.0, "gal") == 3.785411784
    assert flow_rate_to_l_per_min(60.0, "L/h") == 1.0
    assert flow_is_totalizer("L", None) is True
    assert flow_is_totalizer("L/min", None) is False
    assert flow_is_totalizer("", "total_increasing") is True
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_flow_meter.py -q`
Expected: FAIL — `ModuleNotFoundError: ... flow_metering`.

- [ ] **Step 3: Write the engine**

`custom_components/smart_irrigation/flow_metering.py`:

```python
"""Unified flow-measurement engine for Smart Irrigation.

A ``FlowMeter`` is created at the start of a metered run, fed one sensor reading per
poll via :meth:`FlowMeter.sample`, and finalized with :meth:`FlowMeter.delivered`. It
measures delivered litres for the three flow-sensor kinds the integration meets:

* **rate** sensor (unit contains ``/``, e.g. ``L/min``) — integrate ``rate x dt``;
* **per-run counter** (Sonoff/Z2M valve sensor: resets toward 0 at valve-open, then
  holds the run's accumulated volume) — credit the run's climb from the reset;
* **lifetime totalizer** (water meter / DIY counter: monotonic across runs) — credit
  the end-minus-start delta.

Pure Python (no Home Assistant imports) so it is unit-tested in isolation. Each call
site reads the raw sensor and feeds it here; classification and the reset-vs-glitch
discrimination live only here.

Reset vs glitch (the crux): a totalizer drop (``litres < last``) is either a per-run
RESET (reseed the baseline, credit nothing) or a transient GLITCH (keep the baseline,
credit nothing — so the recovery step credits only the true delta, never a phantom
climb from the dip; the CFV-3 keep-baseline fix). Discrimination:
* ``counter_type='per_run'`` -> a drop to near-zero is always the reset;
* ``counter_type='lifetime'`` -> a drop is never a reset (always a glitch);
* ``counter_type='auto'``     -> a drop is a reset only when near-zero AND within
  ``reset_window_s`` of run start. A very delayed reset therefore under-credits (safe
  fallback) rather than over-credits; the user sets ``per_run`` to cover that.
"""

from __future__ import annotations


def flow_rate_to_l_per_min(value: float, unit: str) -> float:
    """Convert an instantaneous flow-rate reading to L/min."""
    u = (unit or "").lower().strip()
    if u in ("l/h", "liter/h", "liter/hour", "liters/hour", "liters/h"):
        return value / 60.0
    if u in ("m³/h", "m3/h", "m³/hour", "m3/hour"):
        return value * 1000.0 / 60.0
    if u in ("m³/min", "m3/min"):
        return value * 1000.0
    if u in ("gal/min", "gpm", "gallon/min", "gallons/min"):
        return value * 3.785411784
    if u in ("gal/h", "gal/hour", "gallon/h", "gallons/h"):
        return value * 3.785411784 / 60.0
    return value  # assume L/min


def flow_is_totalizer(unit: str, state_class: str | None) -> bool:
    """True when a flow sensor is a cumulative counter (vs an instantaneous rate).

    total_increasing, or a non-empty unit without '/' that is not a known abbreviated
    rate unit. No unit and no total_increasing -> rate (the historical default)."""
    if state_class == "total_increasing":
        return True
    u = (unit or "").strip()
    if not u or "/" in u:
        return False
    return u.lower() not in ("gpm", "lpm", "gph", "lph")


def flow_litres_from_total(value: float, unit: str) -> float:
    """Convert a cumulative counter reading to litres (m³x1000, galx3.785, else L)."""
    u = (unit or "").lower().strip()
    if u in ("m³", "m3", "cubic meter", "cubic meters"):
        return float(value) * 1000.0
    if u in ("gal", "gallon", "gallons"):
        return float(value) * 3.785411784
    return float(value)  # L / l / liter(s) / unknown -> assume litres


class FlowMeter:
    """Stateful per-run flow accumulator. See the module docstring."""

    def __init__(
        self,
        *,
        counter_type: str = "auto",
        reset_window_s: float = 30.0,
        near_zero_frac: float = 0.1,
        near_zero_floor: float = 1.0,
    ) -> None:
        self._counter_type = (counter_type or "auto").lower()
        self._reset_window_s = float(reset_window_s)
        self._near_zero_frac = float(near_zero_frac)
        self._near_zero_floor = float(near_zero_floor)
        self._is_totalizer: bool | None = None
        self._started_at: float | None = None
        self._last_at: float | None = None  # rate: previous sample time
        self._last: float | None = None  # totalizer: previous litres baseline
        self._delivered = 0.0
        self._have_reading = False

    def sample(self, value, unit, state_class, at: float) -> None:
        """Feed one poll reading. ``value`` may be None/non-numeric (ignored). ``at``
        is monotonic seconds since run start (the first sample defines t0)."""
        if value is None:
            return
        try:
            raw = float(value)
        except (ValueError, TypeError):
            return
        self._have_reading = True
        if self._is_totalizer is None:
            self._is_totalizer = flow_is_totalizer(unit, state_class)
        if self._started_at is None:
            self._started_at = at
        if self._is_totalizer:
            self._sample_totalizer(raw, unit, at)
        else:
            self._sample_rate(raw, unit, at)

    def _sample_rate(self, raw: float, unit: str, at: float) -> None:
        if self._last_at is not None:
            dt = max(0.0, at - self._last_at)
            self._delivered += flow_rate_to_l_per_min(raw, unit) * dt / 60.0
        self._last_at = at

    def _sample_totalizer(self, raw: float, unit: str, at: float) -> None:
        litres = flow_litres_from_total(raw, unit)
        if self._last is None:  # seed the baseline
            self._last = litres
            return
        if litres >= self._last:  # rising: credit the true climb
            self._delivered += litres - self._last
            self._last = litres
            return
        # litres < last: reset (reseed, credit nothing) or glitch (keep baseline)?
        if self._is_reset(litres, at):
            self._last = litres
        # else glitch: keep _last, add nothing (never over-credit a transient dip)

    def _is_reset(self, litres: float, at: float) -> bool:
        near_zero = max(self._near_zero_floor, self._near_zero_frac * (self._last or 0.0))
        if litres > near_zero:
            return False  # not a drop toward ~0 -> glitch
        if self._counter_type == "lifetime":
            return False  # a lifetime counter never resets
        if self._counter_type == "per_run":
            return True  # per-run: a drop to ~0 is the reset (any time)
        started = self._started_at if self._started_at is not None else at
        return (at - started) <= self._reset_window_s  # auto: only within the window

    def delivered(self) -> float | None:
        """Measured litres this run, or None if no numeric reading was ever seen (the
        caller then falls back to time-based crediting). A live-but-dry meter returns
        0.0 (readings seen, no flow) so callers can distinguish it from 'no sensor'."""
        if not self._have_reading:
            return None
        return self._delivered
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_flow_meter.py -q`
Expected: PASS (14 tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/flow_metering.py tests/test_flow_meter.py
git commit -m "feat(flow): add unified FlowMeter engine (rate/per-run/lifetime)"
```

---

### Task FM-2: `flow_counter_type` store field + const + websocket passthrough

> **⚠ Use the REVISION 1 "FM-2 (revised)" fields above** (add `flow_last_end` + `flow_reset_streak`, drop `FLOW_RESET_WINDOW_S`). The `flow_counter_type` field + const values + the frontend visibility rule below stand; only the extra learning fields differ from this original block.

**Files:**
- Modify: `custom_components/smart_irrigation/const.py`
- Modify: `custom_components/smart_irrigation/store.py:228` (near `observed_entity`) and `store.py:789` (async_load)
- Modify: `custom_components/smart_irrigation/websockets.py:269` (zone schema)
- Test: `tests/test_store.py` (or the existing store test module) — add one test

- [ ] **Step 1: Write the failing test**

Add to `tests/test_store.py` (match the module's existing async store-fixture pattern; if the file uses a `store` fixture, reuse it):

```python
async def test_zone_flow_counter_type_round_trips(store):
    """flow_counter_type defaults to 'auto' and round-trips through the store."""
    zone = await store.async_create_zone({"name": "FM", "flow_counter_type": "per_run"})
    got = store.get_zone(zone[const.ZONE_ID])
    assert got["flow_counter_type"] == "per_run"

    default_zone = await store.async_create_zone({"name": "FM2"})
    assert store.get_zone(default_zone[const.ZONE_ID])["flow_counter_type"] == "auto"
```

(Import `const` as the module already does. If `async_create_zone` has a different signature here, mirror the neighbouring `observed_entity` store test.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_store.py -k flow_counter_type -p _local_socket_unblock -q`
Expected: FAIL — key `flow_counter_type` absent / default not `auto`.

- [ ] **Step 3: Add const keys**

In `const.py`, next to `ZONE_FLOW_SENSOR` / `FLOW_POLL_INTERVAL` (line 342-343) add:

```python
# Unified flow-measurement engine (flow_metering.FlowMeter). Per-zone override for
# how a totalizer flow sensor is read; 'auto' detects a per-run reset within the
# open window. See docs/superpowers/specs/2026-07-13-unified-flow-measurement-engine.
ZONE_FLOW_COUNTER_TYPE = "flow_counter_type"
FLOW_COUNTER_AUTO = "auto"
FLOW_COUNTER_PER_RUN = "per_run"
FLOW_COUNTER_LIFETIME = "lifetime"
FLOW_RESET_WINDOW_S = 30.0  # a near-zero totalizer drop within this of open == reset
FLOW_NEAR_ZERO_FRAC = 0.1  # "near zero" = max(FLOW_NEAR_ZERO_FLOOR, frac x last)
FLOW_NEAR_ZERO_FLOOR = 1.0
```

- [ ] **Step 4: Add the store attr + load passthrough**

In `store.py`, after `observed_entity = attr.ib(type=str, default=None)` (line 228) add:

```python
    # Unified flow engine (opt override): how a totalizer flow_sensor is read
    # ('auto' | 'per_run' | 'lifetime'). Default 'auto'. Additive (no schema bump).
    # See ZONE_FLOW_COUNTER_TYPE / flow_metering.FlowMeter.
    flow_counter_type = attr.ib(type=str, default="auto")
```

Add `ZONE_FLOW_COUNTER_TYPE` to the `const` import block (alphabetical, near `ZONE_FLOW_SENSOR` at line 132). In `async_load` where zones are reconstructed (line 789, next to `observed_entity=zone.get(...)`) add:

```python
                        flow_counter_type=zone.get(ZONE_FLOW_COUNTER_TYPE, "auto")
                        or "auto",
```

- [ ] **Step 5: Add the websocket schema passthrough**

In `websockets.py`, in the zone update schema next to `ZONE_FLOW_SENSOR` (line 269) add:

```python
                vol.Optional(const.ZONE_FLOW_COUNTER_TYPE): vol.Or(str, None),
```

- [ ] **Step 6: Run to verify it passes**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_store.py -k flow_counter_type -p _local_socket_unblock -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/store.py custom_components/smart_irrigation/websockets.py tests/test_store.py
git commit -m "feat(flow): add per-zone flow_counter_type field (auto/per_run/lifetime)"
```

---

### Task FM-3: linked-entity `_run_valve_metered` → `FlowMeter`

**Files:**
- Modify: `custom_components/smart_irrigation/irrigation.py` — delegate the 3 staticmethods (line 570-609) to `flow_metering`; add `_read_flow_sample`; rework `_run_valve_metered` seed + loop + final (line 738-853)
- Test: `tests/test_irrigation_flow.py` (or the existing metered-run test module) — add a metered-run test

- [ ] **Step 1: Write the failing test**

Add to the metered-run test module (mirror an existing `_run_valve_metered` real-flow test; use its coordinator + `hass.states.async_set` fixture pattern). This asserts a **per-run counter** is now measured correctly end-to-end:

```python
async def test_metered_run_credits_per_run_counter(coordinator, hass):
    """A per-run counter (resets at open, holds run total) credits its final value,
    not the stale-high open reading (the old totalizer branch measured ~0)."""
    zone = await _make_flow_zone(coordinator, flow_sensor="sensor.valve_vol", size=10)
    seq = iter([62.0, 0.0, 4.0, 8.0, 12.0, 12.0])  # open-stale -> reset -> climb -> hold

    def _next(*_a, **_k):
        try:
            hass.states.async_set("sensor.valve_vol", next(seq), {"unit_of_measurement": "L"})
        except StopIteration:
            pass

    # advance the sensor once per poll (hook into the test's fake sleep, as the
    # existing metered tests do), then run the metered valve:
    with _fake_flow_poll(hass, _next):
        await coordinator._run_valve_metered(zone, "switch.valve", real_flow=True)

    run = _last_run_log(coordinator, zone)
    assert run["volume"] == 12.0  # measured, not time-based
```

(If the existing metered tests drive the sensor differently, follow that harness; the assertion is the point — measured `12.0` from the per-run trace.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_irrigation_flow.py -k per_run_counter -p _local_socket_unblock -q`
Expected: FAIL — measured ~0 (old branch) or KeyError on the helper; not `12.0`.

- [ ] **Step 3a: Delegate the shared conversions to `flow_metering`**

In `irrigation.py`, add the import near the top with the other `from .` imports:

```python
from .flow_metering import (
    FlowMeter,
    flow_is_totalizer,
    flow_litres_from_total,
    flow_rate_to_l_per_min,
)
```

Replace the three staticmethod bodies (lines 570-609) so they delegate (keeps every existing caller/test working, one source of truth):

```python
    @staticmethod
    def _flow_rate_to_l_per_min(value: float, unit: str) -> float:
        """Convert a flow sensor reading to L/min. Delegates to flow_metering."""
        return flow_rate_to_l_per_min(value, unit)

    @staticmethod
    def _flow_is_totalizer(unit: str, state_class: str | None) -> bool:
        """Cumulative totalizer vs instantaneous rate. Delegates to flow_metering."""
        return flow_is_totalizer(unit, state_class)

    @staticmethod
    def _flow_litres_from_total(value: float, unit: str) -> float:
        """Cumulative counter reading -> litres. Delegates to flow_metering."""
        return flow_litres_from_total(value, unit)
```

- [ ] **Step 3b: Add a raw-sample reader**

Replace `_read_flow_increment` (lines 611-650) with a raw reader `_read_flow_sample` (the engine now owns the arithmetic). Mirrors `distributor._dist_read_flow`:

```python
    def _read_flow_sample(self, flow_sensor: str):
        """Current (value, unit, state_class) of a flow sensor, or None when it is
        unavailable/unknown/non-numeric (a flaky tick the FlowMeter simply skips)."""
        state = self.hass.states.get(flow_sensor)
        if state is None or state.state in ("unavailable", "unknown"):
            _LOGGER.warning("Flow sensor '%s' unavailable", flow_sensor)
            return None
        try:
            value = float(state.state)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Flow sensor '%s' non-numeric state '%s'", flow_sensor, state.state
            )
            return None
        attrs = state.attributes or {}
        return value, attrs.get("unit_of_measurement", "L/min"), attrs.get("state_class")
```

- [ ] **Step 3c: Rework the metered loop to feed the engine**

In `_run_valve_metered`, replace the totalizer-baseline seed block (lines 744-754) with a `FlowMeter` + valve-open seed:

```python
        # Iter FM-3 (unified flow engine): a real-flow run feeds one shared FlowMeter
        # (rate / per-run counter / lifetime totalizer, discriminated in flow_metering)
        # instead of the old per-zone _flow_last_total delta. Seed at valve-open so a
        # per-run counter's reset is observed inside the window. See test_flow_meter.py
        # and test_irrigation_flow.py::test_metered_run_credits_per_run_counter.
        meter = None
        if real_flow:
            meter = FlowMeter(
                counter_type=zone.get(const.ZONE_FLOW_COUNTER_TYPE, "auto"),
                reset_window_s=const.FLOW_RESET_WINDOW_S,
                near_zero_frac=const.FLOW_NEAR_ZERO_FRAC,
                near_zero_floor=const.FLOW_NEAR_ZERO_FLOOR,
            )
            sample = self._read_flow_sample(zone[const.ZONE_FLOW_SENSOR])
            if sample is not None:
                meter.sample(*sample, at=0.0)
```

Then in the poll loop, replace the increment line (line 783-784):

```python
                if real_flow:
                    sample = self._read_flow_sample(zone[const.ZONE_FLOW_SENSOR])
                    if sample is not None:
                        meter.sample(*sample, at=elapsed)
                    delivered = meter.delivered() or 0.0
                else:
                    delivered += rate_lpm * step / 60.0
```

(Note: `delivered` for real-flow is now the meter's cumulative — assign, not `+=`. The synthetic branch is unchanged.) The final-commit tail (lines 803-853) is unchanged: `delivered <= 0` still flags `FAULT_FLOW_NEVER_STARTED` for a dry/no-reading meter (the engine returns 0.0 dry, and `or 0.0` maps None -> 0.0), and `timed_out = real_flow and delivered < target_volume` still marks a partial.

- [ ] **Step 4: Run to verify it passes**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_irrigation_flow.py -p _local_socket_unblock -q`
Expected: PASS — the new test plus the existing metered/rate tests (rate integration unchanged; lifetime totalizer still end−start).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/irrigation.py tests/test_irrigation_flow.py
git commit -m "feat(flow): linked-entity metered run uses FlowMeter engine"
```

---

### Task FM-4: rotating `_irrigate_zone_flow_slot` → shared meter; retire `_read_flow_increment` (REGEL-8 sister path)

**Files:**
- Modify: `custom_components/smart_irrigation/irrigation.py` — `_irrigate_zone_flow_slot` (line 857-...) + the rotating orchestrator's per-zone setup (lines 972-982) and its slot call (line 1072-1074)
- Test: `tests/test_irrigation_flow.py` — add a rotating per-run-counter test

**Context:** the rotating scheduler opens each flow zone for several time-sliced *slots*. The old code kept the totalizer baseline on `self._flow_last_total[zid]` across slots. The unified engine keeps one `FlowMeter` per zone-run and threads it through the slots, so per-run/lifetime/rate all work and `_flow_last_total` is retired. After this task, `_read_flow_increment` and `_flow_last_total` have no callers and are removed.

- [ ] **Step 1: Write the failing test**

```python
async def test_rotating_flow_slot_per_run_counter(coordinator, hass):
    """Rotating flow slots share one FlowMeter per zone, so a per-run counter is
    measured across slots (the old path lost interval 1 and mishandled resets)."""
    zone = await _make_flow_zone(coordinator, flow_sensor="sensor.rot_vol", size=10)
    from custom_components.smart_irrigation.flow_metering import FlowMeter

    meter = FlowMeter()
    hass.states.async_set("sensor.rot_vol", 0.0, {"unit_of_measurement": "L"})
    seq = iter([3.0, 6.0, 9.0])

    def _next(*_a, **_k):
        try:
            hass.states.async_set("sensor.rot_vol", next(seq), {"unit_of_measurement": "L"})
        except StopIteration:
            pass

    with _fake_flow_poll(hass, _next):
        d1 = await coordinator._irrigate_zone_flow_slot(zone, "switch.v", 30.0, 100.0, meter)
    assert d1 == 9.0
    assert meter.delivered() == 9.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_irrigation_flow.py -k rotating_flow_slot -p _local_socket_unblock -q`
Expected: FAIL — `_irrigate_zone_flow_slot` takes 4 args, not 5 (`meter`).

- [ ] **Step 3a: Give the slot a shared meter**

Change `_irrigate_zone_flow_slot`'s signature (line 857-863) to accept a `meter`:

```python
    async def _irrigate_zone_flow_slot(
        self,
        zone: dict,
        entity_id: str,
        max_seconds: float,
        remaining_volume: float,
        meter: "FlowMeter",
    ) -> float:
        """Open a flow-meter zone for up to max_seconds or until remaining_volume is
        reached, feeding the zone-run's shared ``meter``. Returns litres delivered
        during THIS slot (the meter's cumulative advance while this slot ran)."""
```

Inside, replace the `accumulated += self._read_flow_increment(...)` loop body (lines 874-880) with meter feeding that returns the per-slot advance:

```python
        before = meter.delivered() or 0.0
        elapsed = 0.0
        while elapsed < max_seconds and (meter.delivered() or 0.0) - before < remaining_volume:
            stopped = await self._sleep_or_stopped(zone_id, const.FLOW_POLL_INTERVAL)
            elapsed += const.FLOW_POLL_INTERVAL
            sample = self._read_flow_sample(zone[const.ZONE_FLOW_SENSOR])
            if sample is not None:
                meter.sample(*sample, at=elapsed)
```

Adjust the slot's remaining logic/return so it returns `(meter.delivered() or 0.0) - before`, and drop the local `accumulated` variable and its `_LOGGER.debug` that referenced it (rewrite the debug to log `(meter.delivered() or 0.0) - before`). Keep the valve turn_on/turn_off and `_note_si_valve` as-is. **Read the full function first** to reconcile the stop/return tail with this loop.

- [ ] **Step 3b: Own the meter in the rotating orchestrator**

In the per-zone setup (`_irrigate_zones_rotating`, lines 972-982) replace the `_flow_last_total` clear with a per-zone meter dict:

```python
            flow_floor[zid] = raw_floor
            flow_by_id[zid] = z
            # Iter FM-4 (unified flow engine, REGEL-8 sister path to _run_valve_metered):
            # one FlowMeter per rotating flow zone, shared across its slots, so a per-run
            # counter / lifetime totalizer / rate is measured coherently across the whole
            # rotation. Replaces the retired self._flow_last_total delta baseline.
            flow_meter[zid] = FlowMeter(
                counter_type=z.get(const.ZONE_FLOW_COUNTER_TYPE, "auto"),
                reset_window_s=const.FLOW_RESET_WINDOW_S,
                near_zero_frac=const.FLOW_NEAR_ZERO_FRAC,
                near_zero_floor=const.FLOW_NEAR_ZERO_FLOOR,
            )
```

Initialize `flow_meter = {}` alongside the other per-zone dicts (`flow_floor`, `flow_by_id`, etc. — find their initialization above line 972 and add it there). Update the slot call (lines 1072-1074):

```python
                    delivered = await self._irrigate_zone_flow_slot(
                        z, entity_id, slot, rem_vol, flow_meter[zid]
                    )
```

- [ ] **Step 3c: Retire the dead code**

Delete `_read_flow_increment` (now no callers) and every `self._flow_last_total` reference (they were the two clears at ~747-749 — already replaced in FM-3 — and ~980-982, replaced above). Grep to confirm zero remaining references:

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -c "import pathlib,sys; t=pathlib.Path('custom_components/smart_irrigation/irrigation.py').read_text(encoding='utf-8'); sys.exit(1 if ('_read_flow_increment' in t or '_flow_last_total' in t) else 0)"`
Expected: exit 0 (no matches). Also `grep -rn _read_flow_increment tests/` and update any test that called it directly to feed a `FlowMeter` instead.

- [ ] **Step 4: Run to verify it passes**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_irrigation_flow.py -p _local_socket_unblock -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/irrigation.py tests/test_irrigation_flow.py
git commit -m "feat(flow): rotating flow slots share a FlowMeter; retire _read_flow_increment"
```

---

### Task FM-5: self-closing non-blocking interval sampling + measured finalize + advisory

**Files:**
- Modify: `custom_components/smart_irrigation/self_closing.py` — `async_run_self_closing` (start sampling at line 148, after `_sc_dispatch_open`); `_sc_finish_run` (line 87-124, finalize measured); `async_stop_self_closing` (line 232-276, finalize measured); add `_sc_start_flow_sampling` / `_sc_stop_flow_sampling` helpers
- Test: `tests/test_self_closing.py`

**Context:** `async_run_self_closing` is fire-and-forget. To measure without blocking, start an `async_track_time_interval` at open that samples a per-zone `FlowMeter`; cancel + read it at finish/stop. If HA restarts mid-run the in-memory meter is lost -> finish falls back to time-based (documented, safe). The optimistic bucket credit at open stays time-based; the finish **corrects** the bucket + usage to the measured volume when the meter yields one.

- [ ] **Step 1: Write the failing test**

```python
async def test_self_closing_credits_measured_flow(coordinator, hass):
    """A self-closing zone with a flow_sensor credits the measured volume at finish,
    not the time-based estimate."""
    zone = await _make_sc_zone(coordinator, flow_sensor="sensor.sc_vol", duration=120,
                               throughput=4.0)  # time-based would be 8 L over 2 min
    await coordinator.async_run_self_closing(zone)
    # simulate the interval sampling: per-run counter climbs 0 -> 12 during the window
    for i, v in enumerate([0.0, 6.0, 12.0, 12.0]):
        hass.states.async_set("sensor.sc_vol", v, {"unit_of_measurement": "L"})
        await coordinator._sc_sample_flow(zone[const.ZONE_ID], at=float(i * 40))
    await coordinator._sc_finish_run(zone[const.ZONE_ID])

    run = _last_run_log(coordinator, zone)
    assert run["volume"] == 12.0  # measured, not the 8 L time-based estimate
```

(Adapt `_make_sc_zone` / `_last_run_log` to the module's existing self-closing helpers. `_sc_sample_flow(zone_id, at)` is the sampling callback added below, exposed so the test drives it deterministically instead of the real interval.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_self_closing.py -k credits_measured_flow -p _local_socket_unblock -q`
Expected: FAIL — no `_sc_sample_flow`; run volume is time-based `8.0`.

- [ ] **Step 3a: Sampling lifecycle helpers**

Add to the self-closing mixin (imports: `from homeassistant.helpers.event import async_track_time_interval`, `from datetime import timedelta`, and `from .flow_metering import FlowMeter`):

```python
    def _sc_meters(self) -> dict:
        """Lazy per-zone {zone_id: (FlowMeter, cancel_cb, started_monotonic)}."""
        meters = getattr(self, "_sc_flow_meters", None)
        if meters is None:
            meters = self._sc_flow_meters = {}
        return meters

    def _sc_start_flow_sampling(self, zone: dict) -> None:
        """Start non-blocking interval sampling of a self-closing zone's flow_sensor.
        No-op when the zone has no flow_sensor. Feeds a per-zone FlowMeter that
        _sc_finish_run / async_stop_self_closing finalize into the measured volume."""
        sensor = zone.get(const.ZONE_FLOW_SENSOR)
        if not sensor:
            return
        zone_id = zone.get(const.ZONE_ID)
        meter = FlowMeter(
            counter_type=zone.get(const.ZONE_FLOW_COUNTER_TYPE, "auto"),
            reset_window_s=const.FLOW_RESET_WINDOW_S,
            near_zero_frac=const.FLOW_NEAR_ZERO_FRAC,
            near_zero_floor=const.FLOW_NEAR_ZERO_FLOOR,
        )
        started = dt_util.utcnow()
        # seed at open so a per-run counter's reset is observed inside the window
        self._sc_feed(meter, sensor, 0.0)

        async def _tick(now):
            self._sc_feed(meter, sensor, (now - started).total_seconds())

        cancel = async_track_time_interval(
            self.hass, _tick, timedelta(seconds=const.FLOW_POLL_INTERVAL)
        )
        self._sc_meters()[zone_id] = (meter, cancel, started)

    def _sc_feed(self, meter, sensor: str, at: float) -> None:
        state = self.hass.states.get(sensor)
        if state is None or state.state in ("unavailable", "unknown"):
            return
        try:
            value = float(state.state)
        except (ValueError, TypeError):
            return
        attrs = state.attributes or {}
        meter.sample(value, attrs.get("unit_of_measurement", "L/min"),
                     attrs.get("state_class"), at)

    async def _sc_sample_flow(self, zone_id, at: float) -> None:
        """Test/seam hook: feed the zone's meter one reading at monotonic ``at``."""
        entry = self._sc_meters().get(zone_id)
        if entry:
            meter, _cancel, _started = entry
            zone = self.store.get_zone(zone_id) or {}
            self._sc_feed(meter, zone.get(const.ZONE_FLOW_SENSOR), at)

    def _sc_measured_volume(self, zone_id) -> float | None:
        """Cancel sampling for a zone and return its measured litres (None = fall back
        to time-based: no sensor, meter lost to a restart, or no numeric reading)."""
        entry = self._sc_meters().pop(zone_id, None)
        if not entry:
            return None
        meter, cancel, _started = entry
        cancel()
        d = meter.delivered()
        return d if (d is not None and d > 0) else None
```

- [ ] **Step 3b: Start sampling at open**

In `async_run_self_closing`, right after `await self._sc_dispatch_open(zone)` (line 148):

```python
        # Iter FM-5 (unified flow engine): measure the delivered volume across the
        # fixed self-closing window via NON-blocking interval sampling (the run stays
        # fire-and-forget; the hardware still owns the close). Finalized in
        # _sc_finish_run / async_stop_self_closing. See test_self_closing.py.
        self._sc_start_flow_sampling(zone)
```

- [ ] **Step 3c: Finalize measured at finish**

In `_sc_finish_run` (line 102), replace the time-based `volume_l` with a measured-preferring value and correct the bucket delta:

```python
        measured = self._sc_measured_volume(zone_id)
        volume_l = measured if measured is not None else self._timed_volume_l(zone, planned_s)
        if measured is not None:
            # correct the open-time optimistic (time-based) bucket credit to measured
            timed_l = self._timed_volume_l(zone, planned_s)
            delta_depth = self._credited_depth_native(zone, measured) - \
                self._credited_depth_native(zone, timed_l)
            if delta_depth:
                ceiling = zone.get(const.ZONE_MAXIMUM_BUCKET)
                nb = float(zone.get(const.ZONE_BUCKET) or 0) + delta_depth
                if ceiling and nb > float(ceiling):
                    nb = float(ceiling)
                await self.store.async_update_zone(zone_id, {const.ZONE_BUCKET: nb})
                zone = self.store.get_zone(zone_id) or zone
```

Then the existing `_record_run(..., volume_l=volume_l, ...)` records the measured litres. After it, add the advisory (a self-closing zone can't stop early -> same advisory as a distributor member):

```python
        await self._flow_calibration_check(zone, measured, planned_s)
```

(`_flow_calibration_check` is created in FM-7; if FM-7 runs after FM-5, add this line there. To keep FM-5 independently green, guard: `if hasattr(self, "_flow_calibration_check"): await self._flow_calibration_check(zone, measured, planned_s)` — remove the guard in FM-7.)

- [ ] **Step 3d: Finalize measured on early stop**

In `async_stop_self_closing`, the meter has been sampling until now. Replace the time-based `delivered_l` (line 265) with the measured value when available:

```python
        measured = self._sc_measured_volume(zone_id)
        delivered_l = measured if measured is not None else self._timed_volume_l(zone, elapsed)
```

(The bucket correction above at line 259-261 still uses the time-based `delivered_frac`; leave it — an early stop is a coarse correction and the measured value only refines the recorded usage, matching the existing partial semantics.)

- [ ] **Step 4: Run to verify it passes**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_self_closing.py -p _local_socket_unblock -q`
Expected: PASS — the new test plus existing self-closing tests (zones without a flow_sensor take the `None` path and stay time-based, unchanged).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/self_closing.py tests/test_self_closing.py
git commit -m "feat(flow): self-closing zones measure flow via non-blocking sampling"
```

---

### Task FM-6: distributor `_dist_measure_window` → `FlowMeter`

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py` — `_dist_measure_window` (line 500-563)
- Test: `tests/test_distributor.py` (or the flow-window test module)

**Context:** preserve the tuple return `(delivered, actual_seconds, stopped_early)`, the `cap`/`target` early-stop, and the dead-meter/no-sensor fallbacks. Only the inner rate/totalizer arithmetic moves into the engine, which fixes the per-run-counter blind spot for the shared inlet meter. `counter_type` comes from the distributor config (falls back to `auto`).

- [ ] **Step 1: Write the failing test**

```python
async def test_dist_measure_window_per_run_counter(coordinator, hass):
    """The distributor inlet meter now measures a per-run counter correctly."""
    dist = {"flow_sensor": "sensor.inlet_vol"}
    seq = iter([50.0, 0.0, 4.0, 8.0, 8.0])  # stale -> reset -> climb -> hold

    def _next(*_a, **_k):
        try:
            hass.states.async_set("sensor.inlet_vol", next(seq), {"unit_of_measurement": "L"})
        except StopIteration:
            pass

    hass.states.async_set("sensor.inlet_vol", 50.0, {"unit_of_measurement": "L"})
    with _fake_dist_poll(hass, _next):
        delivered, actual, stopped = await coordinator._dist_measure_window(dist, 60.0)
    assert delivered == 8.0
    assert stopped is False
```

(Use the module's existing `_dist_measure_window` test harness; assertion: `8.0`, not the old delta-from-50 which measured ~0 / unreliable.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_distributor.py -k measure_window_per_run -p _local_socket_unblock -q`
Expected: FAIL — old branch flags the reset unreliable -> `None`, not `8.0`.

- [ ] **Step 3: Rework `_dist_measure_window`**

Replace the metering body (lines 527-563, from `reading = self._dist_read_flow(sensor)` to the `return`) with a `FlowMeter`:

```python
        reading = self._dist_read_flow(sensor)
        if reading is None:
            await self._dist_sleep(window)  # dead meter -> full window, time-based
            return None, window, False
        # Iter FM-6 (unified flow engine): the shared inlet meter now feeds a FlowMeter
        # (rate / per-run counter / lifetime totalizer). Preserves cap/target early-stop
        # and the None-fallback. See test_distributor.py::test_dist_measure_window_per_run.
        meter = FlowMeter(
            counter_type=distributor.get(const.ZONE_FLOW_COUNTER_TYPE, "auto"),
            reset_window_s=const.FLOW_RESET_WINDOW_S,
            near_zero_frac=const.FLOW_NEAR_ZERO_FRAC,
            near_zero_floor=const.FLOW_NEAR_ZERO_FLOOR,
        )
        meter.sample(reading[0], reading[1], reading[2], 0.0)  # valve-open seed
        elapsed = 0.0
        while elapsed < cap:
            if target is not None and (meter.delivered() or 0.0) >= target:
                break  # early stop: reached the target volume
            step = min(float(const.DISTRIBUTOR_FLOW_POLL_SECONDS), cap - elapsed)
            await self._dist_sleep(step)
            elapsed += step
            r = self._dist_read_flow(sensor)
            if r is not None:
                meter.sample(r[0], r[1], r[2], elapsed)
        delivered = meter.delivered()
        stopped_early = (
            target is not None and (delivered or 0.0) >= target and elapsed < cap
        )
        # Part B fail-safe: a live-but-dry meter delivered 0 L -> unreliable so the
        # caller falls back to time-based crediting (spec: delivered <= 0 -> None).
        reliable = delivered is not None and delivered > 0
        return (delivered if reliable else None), elapsed, stopped_early
```

Add `FlowMeter` to the distributor imports (`from .flow_metering import FlowMeter`). Remove the now-unused local `last` / `is_rate` / `reliable` initialization lines (531-536) that preceded the old loop.

- [ ] **Step 4: Run to verify it passes**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_distributor.py -p _local_socket_unblock -q`
Expected: PASS — the new test plus the existing Part A/B window tests (rate integration, target early-stop, dead-meter fallback all preserved).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -m "feat(flow): distributor measure-window uses FlowMeter engine"
```

---

### Task FM-7: generalize the calibration advisory to any can't-stop measured run

**Files:**
- Modify: `custom_components/smart_irrigation/irrigation.py` — add shared `_flow_calibration_check` (move the body from distributor)
- Modify: `custom_components/smart_irrigation/distributor.py` — `_dist_flow_calibration_check` (line 838-904) becomes a thin delegator; sweep callsite (line 1298) unchanged
- Modify: `custom_components/smart_irrigation/self_closing.py` — remove the `hasattr` guard added in FM-5 step 3c
- Test: `tests/test_distributor.py` advisory test still passes; add a self-closing advisory test

**Context:** the advisory logic is already generic (zone dict + measured_l + seconds; keys on observed rate vs configured throughput). Moving it to the shared base mixin lets the self-closing finish call it too. Keep `_dist_flow_calibration_check` as a delegator so the distributor sweep + its existing tests are untouched.

- [ ] **Step 1: Write the failing test**

```python
async def test_self_closing_advisory_after_three_off_runs(coordinator, hass):
    """A self-closing zone whose measured rate is >15% off configured throughput for
    >=3 runs raises one persistent_notification (same advisory as a distributor member)."""
    zone = await _make_sc_zone(coordinator, flow_sensor="sensor.sc_vol",
                               duration=60, throughput=4.0)  # cfg 4 L/min
    calls = _capture_service(hass, "persistent_notification", "create")
    for _ in range(3):
        # measured 6 L/min (50% over) each run
        await coordinator._flow_calibration_check(
            coordinator.store.get_zone(zone[const.ZONE_ID]), measured_l=6.0, seconds=60.0
        )
    assert len(calls) == 1
    assert "flow" in calls[0]["message"].lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_self_closing.py -k advisory -p _local_socket_unblock -q`
Expected: FAIL — `_flow_calibration_check` does not exist on the base.

- [ ] **Step 3a: Move the method to the base mixin**

Cut the entire `_dist_flow_calibration_check` body (lines 838-904 in `distributor.py`) into `irrigation.py` as `_flow_calibration_check` (identical body, renamed). It already uses only shared names (`self._throughput_lpm`, `const.ZONE_FLOW_CAL_*`, `const.FLOW_CAL_*`, `self.hass`, `self.store`), so no other change is needed. Ensure `convert_between` / `METRIC_SYSTEM` / `const.UNIT_LPM` / `const.UNIT_GPM` are already imported in `irrigation.py` (they are — used by `_metered_target_volume` / `_throughput_lpm`); if any is missing, add it.

- [ ] **Step 3b: Delegator in the distributor**

Replace the removed method in `distributor.py` with:

```python
    async def _dist_flow_calibration_check(
        self, zone: dict, measured_l: float, seconds: float
    ) -> None:
        """Distributor member advisory -> shared _flow_calibration_check (FM-7)."""
        await self._flow_calibration_check(zone, measured_l, seconds)
```

(The sweep callsite at line 1298 stays as-is, calling `_dist_flow_calibration_check`.)

- [ ] **Step 3c: Un-guard the self-closing call**

In `self_closing.py` `_sc_finish_run`, replace the FM-5 guarded line with the direct call:

```python
        await self._flow_calibration_check(zone, measured, planned_s)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests/test_self_closing.py tests/test_distributor.py -k "advisory or calibration" -p _local_socket_unblock -q`
Expected: PASS — new self-closing advisory + existing distributor advisory (via the delegator).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/irrigation.py custom_components/smart_irrigation/distributor.py custom_components/smart_irrigation/self_closing.py tests/test_self_closing.py
git commit -m "feat(flow): share flow-calibration advisory across can't-stop measured runs"
```

---

### Task FM-8: frontend conditional `flow_counter_type` select + i18n (8 languages)

**Files:**
- Modify: `frontend/src/const.ts` — export `ZONE_FLOW_COUNTER_TYPE`
- Modify: `frontend/src/views/zones/view-zone-settings.ts` — conditional select after the flow_sensor row (line 1349)
- Modify: `frontend/src/localize/languages/{en,de,nl,fr,es,it,sk,no}.json` — label + help + 3 option strings
- Test: `frontend/src/views/zones/view-zone-settings.test.ts` (or the nearest existing view test) — a visibility test

**Context:** show the select **only when the selected flow_sensor's unit indicates a totalizer** (unit without `/`, or `state_class: total_increasing`) — read from `this.hass.states[zone.flow_sensor]`. Hidden for a rate sensor and when no flow_sensor is set. Same conditional-row pattern as the distributor `watch_mode` field (UX-1).

- [ ] **Step 1: Write the failing test**

Mirror the UX-1 conditional-row test. Assert: with `zone.flow_sensor` pointing at a `hass.states` entry whose unit is `L` (totalizer), the `flow_counter_type` row renders; with unit `L/min` (rate) or no flow_sensor, it does not.

```typescript
it("shows flow_counter_type only for a totalizer flow_sensor", async () => {
  const el = await fixtureZoneSettings({
    zone: { flow_sensor: "sensor.vol" },
    states: { "sensor.vol": { state: "5", attributes: { unit_of_measurement: "L" } } },
  });
  expect(el.shadowRoot!.textContent).toContain("Counter type"); // en label

  const rate = await fixtureZoneSettings({
    zone: { flow_sensor: "sensor.rate" },
    states: { "sensor.rate": { state: "5", attributes: { unit_of_measurement: "L/min" } } },
  });
  expect(rate.shadowRoot!.textContent).not.toContain("Counter type");
});
```

(Adapt `fixtureZoneSettings` to the test file's actual harness; if none exists for this view, add the row-visibility assertion to the closest existing zone-settings test using its setup.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation/custom_components/smart_irrigation/frontend && npm run test -- view-zone-settings`
Expected: FAIL — "Counter type" not rendered.

- [ ] **Step 3a: Const + a totalizer-unit predicate**

In `frontend/src/const.ts` add `export const ZONE_FLOW_COUNTER_TYPE = "flow_counter_type";`.

In `view-zone-settings.ts`, add a small helper used by the template:

```typescript
  private _flowSensorIsTotalizer(zone: any): boolean {
    const entity = zone.flow_sensor;
    if (!entity) return false;
    const st = this.hass.states[entity];
    if (!st) return false;
    const unit = (st.attributes?.unit_of_measurement || "").trim();
    if (st.attributes?.state_class === "total_increasing") return true;
    if (!unit || unit.includes("/")) return false;
    return !["gpm", "lpm", "gph", "lph"].includes(unit.toLowerCase());
  }
```

- [ ] **Step 3b: The conditional select**

After the flow_sensor `</ha-settings-row>` (line 1349, still inside the same `? ... : ""` block), insert:

```typescript
                      ${this._flowSensorIsTotalizer(zone)
                        ? html`
                            <ha-settings-row>
                              <span slot="heading"
                                >${localize(
                                  "panels.zones.labels.flow_counter_type",
                                  this.hass.language,
                                )}</span
                              >
                              <span slot="description"
                                >${localize(
                                  "panels.zones.labels.flow_counter_type_help",
                                  this.hass.language,
                                )}</span
                              >
                              <ha-select
                                .value="${zone.flow_counter_type || "auto"}"
                                @selected="${(e: CustomEvent) =>
                                  this.handleEditZone(index, {
                                    ...zone,
                                    [ZONE_FLOW_COUNTER_TYPE]:
                                      (e.target as any).value || "auto",
                                  })}"
                                @closed="${(e: Event) => e.stopPropagation()}"
                              >
                                ${["auto", "per_run", "lifetime"].map(
                                  (opt) => html`<mwc-list-item value="${opt}"
                                    >${localize(
                                      `panels.zones.labels.flow_counter_type_${opt}`,
                                      this.hass.language,
                                    )}</mwc-list-item
                                  >`,
                                )}
                              </ha-select>
                            </ha-settings-row>
                          `
                        : ""}
```

Import `ZONE_FLOW_COUNTER_TYPE` from `../../const` (match the file's existing const-import style). Confirm `ha-select` / `mwc-list-item` are already used in this file (the mode/other selects use them); if a different select component is the house style, mirror that instead.

- [ ] **Step 3c: i18n — all 8 languages**

Add under `panels.zones.labels` in each `frontend/src/localize/languages/*.json`. English:

```json
"flow_counter_type": "Counter type",
"flow_counter_type_help": "How this cumulative flow sensor is read. Auto: detects a per-run reset at valve open. Per run: the sensor resets to ~0 each run and shows that run's total (e.g. Sonoff/Zigbee valves). Lifetime: a meter that only ever counts up across all runs (delta per run).",
"flow_counter_type_auto": "Auto (detect)",
"flow_counter_type_per_run": "Per run (resets each run)",
"flow_counter_type_lifetime": "Lifetime total (delta)"
```

German (`de.json`):

```json
"flow_counter_type": "Zählertyp",
"flow_counter_type_help": "Wie dieser kumulative Durchflusssensor gelesen wird. Auto: erkennt einen Reset pro Lauf beim Ventil-Öffnen. Pro Lauf: der Sensor springt zu Beginn jedes Laufs auf ~0 und zeigt die Menge dieses Laufs (z. B. Sonoff-/Zigbee-Ventile). Gesamtzähler: ein Zähler, der über alle Läufe nur hochzählt (Delta pro Lauf).",
"flow_counter_type_auto": "Auto (erkennen)",
"flow_counter_type_per_run": "Pro Lauf (setzt je Lauf zurück)",
"flow_counter_type_lifetime": "Gesamtzähler (Delta)"
```

Translate equivalently for `nl, fr, es, it, sk, no` (keep the `auto`/`per_run`/`lifetime` key names identical; translate only the values). Match the terminology already used for `flow_sensor` in each file.

- [ ] **Step 4: Run to verify it passes**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation/custom_components/smart_irrigation/frontend && npm run test -- view-zone-settings`
Expected: PASS. Then validate all 8 JSONs parse:
Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -c "import json,glob; [json.load(open(f,encoding='utf-8')) for f in glob.glob('custom_components/smart_irrigation/frontend/src/localize/languages/*.json')]; print('ok')"`
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/frontend/src
git commit -m "feat(flow): zone flow_counter_type select (totalizer sensors) + i18n (8 langs)"
```

---

### Task FM-9: regression + format + REGEL-8 holistic + build + fork release v2026.07.18

**Files:**
- Modify: `manifest.json` (line 11), `const.py` (`VERSION`), `frontend/package.json` (line 2) — bump to `v2026.07.18` / `2026.07.18`
- Build: `frontend/dist/*`

- [ ] **Step 1: Full backend suite (no new failures vs baseline)**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && .venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q`
Expected: only the known baseline failures (`test_init` / `test_panel` / `test_watering_calendar` / `test_schedule_time_anchor` / `test_create_returns_id`). Zero new failures. If anything else fails, fix before proceeding.

- [ ] **Step 2: Format + lint**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && uvx black custom_components/smart_irrigation tests && uvx ruff check custom_components/smart_irrigation tests`
Expected: black "reformatted/unchanged" clean; ruff "All checks passed".

- [ ] **Step 3: REGEL-8 sister-path holistic review**

Confirm all three metered paths now go through `FlowMeter` and share the advisory:
Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && grep -rn "FlowMeter(" custom_components/smart_irrigation/`
Expected: constructions in `irrigation.py` (`_run_valve_metered` + rotating orchestrator), `self_closing.py` (`_sc_start_flow_sampling`), `distributor.py` (`_dist_measure_window`).
Run: `cd D:/Entwicklung/HASI/HAsmartirrigation && grep -rn "_read_flow_increment\|_flow_last_total" custom_components/smart_irrigation/`
Expected: no matches (fully retired). Read each of the three integration sites once end-to-end to confirm the dry-meter/no-reading fallback and the valve-open seed are present in each.

- [ ] **Step 4: Frontend build**

Run: `cd D:/Entwicklung/HASI/HAsmartirrigation/custom_components/smart_irrigation/frontend && npm run build`
Expected: lint + rollup succeed; `dist/` updated.

- [ ] **Step 5: Version bump + commit**

Set `v2026.07.18` in `manifest.json`, `const.py` `VERSION`, and `2026.07.18` in `frontend/package.json`; rebuild dist (`npm run build`) so the baked version string matches.

```bash
git add -f custom_components/smart_irrigation/frontend/dist
git add custom_components/smart_irrigation/manifest.json custom_components/smart_irrigation/const.py custom_components/smart_irrigation/frontend/package.json
git commit -m "chore(release): unified flow-measurement engine v2026.07.18"
```

- [ ] **Step 6: Fork release + docs archive (deferred to delivery discussion)**

Do NOT push/release until the user confirms delivery (fork-release vs HA-Test first). When approved: apply the source onto `production` on a fresh branch from current `production`, bump the three versions there, rebuild dist, `gh api .../releases -X POST` with approved notes, and move `docs/superpowers/{specs,plans}/2026-07-13-unified-flow-measurement-engine*` to `archive/design-history` per the established recipe. Upstream (JustChr) PR is a separate later decision. **HA-Test/Prod live verification** against the real per-run counter (measured vs time-based, all three sensor types if available) is the acceptance gate — REGEL 1/verification-before-completion.

---

## Self-Review

**1. Spec coverage.**
- Engine (rate/per-run/lifetime, reset-vs-glitch) → FM-1. ✅
- Per-zone `flow_counter_type` (auto/per_run/lifetime, additive, no schema bump) → FM-2. ✅
- Unit-driven UI (shown only for totalizer sensors) + i18n 8 langs → FM-8. ✅
- linked-entity integration + retire CFV-3 `_flow_last_total` → FM-3 + FM-4. ✅
- service/self-closing integration + advisory → FM-5 + FM-7. ✅ (poll-loop wording corrected to non-blocking interval — documented under "Spec".)
- distributor integration (preserve cap/target early-stop) → FM-6. ✅
- advisory generalized from distributor-members to any can't-stop measured run → FM-7. ✅
- reset only within `reset_window_s` (auto), per_run/lifetime overrides → FM-1 `_is_reset`. ✅
- testing (engine unit tests incl. 62→0→12 trace, glitch keeps baseline, delayed reset, dry/None) → FM-1; path tests → FM-3/5/6; frontend visibility → FM-8; full suite + black/ruff → FM-9. ✅
- delivery (fork release, docs→archive, upstream later, live verify) → FM-9. ✅

**2. Placeholder scan.** Every code step carries real code. Tasks FM-3/4/5/8 note "adapt to the module's existing test harness" for test *setup* (unavoidable — the harness differs per module) but the asserted behaviour and all production code are concrete. No TBD/TODO left.

**3. Type/name consistency.** Engine public surface used identically everywhere: `FlowMeter(counter_type=, reset_window_s=, near_zero_frac=, near_zero_floor=)`, `.sample(value, unit, state_class, at)`, `.delivered() -> float | None`. Module functions `flow_rate_to_l_per_min` / `flow_is_totalizer` / `flow_litres_from_total` are referenced by those exact names in FM-1/3/8. Const keys `ZONE_FLOW_COUNTER_TYPE`, `FLOW_RESET_WINDOW_S`, `FLOW_NEAR_ZERO_FRAC`, `FLOW_NEAR_ZERO_FLOOR`, values `auto`/`per_run`/`lifetime` are consistent across FM-2/3/5/6/8. Shared advisory named `_flow_calibration_check` in FM-5/7 (with the FM-5 `hasattr` guard removed in FM-7). `_read_flow_sample` defined in FM-3, reused conceptually by FM-4/5/6 (self-closing uses its own inline `_sc_feed` to avoid a cross-mixin dependency — intentional, noted).

**Ordering note for the executor:** FM-2 must precede FM-3/5/6/8 (defines the const keys + field). FM-7 must run after FM-5 (removes the `hasattr` guard). FM-1 first (everything imports the engine). Otherwise tasks are independent.
