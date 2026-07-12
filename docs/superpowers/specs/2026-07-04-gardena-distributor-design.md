# Design: Gardena "Wasserverteiler automatic" Support

- **Date:** 2026-07-04 (rev. 4 — user feedback incorporated)
- **Status:** Approved (brainstorming complete) — ready for implementation plan
- **Branch:** `feature/gardena-distributor` (from `production`, v2026.07.10)
- **Feature area:** `custom_components/smart_irrigation` (Eifel-Joe fork)

---

## 1. Problem

The Gardena "Wasserverteiler automatic" (Art. 1197) is a purely **mechanical, pressure-driven** water distributor: one inlet feeds **2–6 outlets**, watered **strictly one at a time** in a fixed ring (1 → 2 → … → n → 1). It has **no electronics and no interface** — HA can neither read its position nor command it directly.

The only thing HA can drive is the **inlet valve** in front of the distributor. Each time water flows and then stops with a sufficient pressure-bleed pause, the device **advances to the next active outlet**. So the outlet position is **stateful**, and HASI must **count** advances **open-loop** and **persist** the position, because it cannot measure it.

HASI already has *sequential zone sequencing* and a *master switch*, but **outlet selection and pulse-advance on a shared distributor** is new logic.

### 1.1 Device facts (from the Art. 1197 manual, cited)

- **Advance is pressure-driven**, via a water OFF→ON cycle at the distributor inlet, *or* the physical **Wahl-Taste** on the device. **No time-based auto-reset** — position stays put until the next pulse (confirmed with the user).
- **Reliable switching needs a pause.** Gardena's own computer (Art. 1892) inserts **≥ 5 min** between programs. Below **1 bar** flow pressure or **20 l/h** flow the device **does not advance** (Ch. 2 + Ch. 8).
- **Skipped-but-active outlet:** Gardena's reference waters a non-due outlet **30 s** purely to advance (Ch. 5, moisture case). This is the "minimal pulse".
- **Desync is the primary hazard.** Ch. 8, verbatim: *"Wenn die Zuordnung der Programme zu den Ausgängen verloren geht, kann erheblicher Schaden durch Überwässerung oder Austrocknung entstehen …"*
- **Outlets 1 and 2 are mandatory**, 3–6 enabled by physical flow levers → **n ∈ {2..6}**. Enabling/disabling an outlet is a **physical device change** (flow lever), invisible to HASI.
- **Position is only visible** in the physical window; only changeable via the physical Wahl-Taste. HA can do neither → **HASI is open-loop / blind**: it can *count*, never *measure*, position.

### 1.2 Fundamental limitation (load-bearing for the whole design)

Because HASI is blind, **it cannot detect a wrong-outlet desync and cannot autonomously re-home** (advancing n times from an unknown position returns to that same unknown position). Every safety mechanism below is built around this: the design **preserves** a known sync and **fails safe** (halt + require a human re-sync) when sync becomes doubtful. It can **never verify** that a completed cycle watered the correct plants.

---

## 2. Goals & Non-Goals

### Goals (MVP / Beta 1)
1. Model a distributor as a first-class object; support **multiple** distributors, each with **2–6 outlets**.
2. Run a **cycle** that sweeps the ring in outlet order, watering due zones and pulse-advancing skipped ones.
3. **Persist** outlet position; survive HA restart.
4. **Manual re-sync** (service + button) as the recovery mechanism.
5. **Fail-safe** on doubtful sync (halt + notify + require re-sync).
6. **Configurable** pause and skip-pulse durations (defaults 300 s / 30 s) with warnings.
7. Full **panel UI branch** to create/configure distributors and map zones to outlets.
8. **i18n** for all new strings in all 8 languages.
9. **Commissioning test-run** (short sweep) + a **confirmation gate** keeping the distributor inert until the user confirms a successful test.

### Non-Goals (later iterations)
- Auto re-home via an outlet-specific sensor (extra hardware; the shared inlet sensor cannot identify an outlet).
- Multiple schedules per distributor beyond what the schedule infra gives for free.
- Per-outlet statistics dashboards.

---

## 3. Architecture Overview

A **`Distributor`** is a new first-class store collection (alongside `zones`, `modules`, `mappings`), with its own UI branch. It is **not** a zone. It owns: inlet-valve actuation config, optional shared confirm/flow sensor on the inlet, pause/skip-pulse durations, persisted outlet position + `position_state`, optional notify target, schedule(s), and an ordered ring of member zones mapped to outlets 1..n.

Member **zones** are ordinary HASI zones (unchanged calculation) plus `distributor_id` and `outlet_number`. Member zones do **not** own a valve entity (the inlet is shared) and do **not** own their own schedule (the distributor triggers them). They are **excluded** from the normal `_irrigate_linked_entities` dispatch (§5.4).

| Concern | Owner | Change |
|---|---|---|
| **When** the ring runs | Distributor schedule | new (reuses schedule infra + new target type) |
| **Whether / how long** each zone waters | Per-zone calculation | unchanged |
| **Order** | Physical outlet number | forced |

---

## 4. Data Model

### 4.1 New: `Distributor`

| Field | Type | Notes |
|---|---|---|
| `id`, `name` | str | |
| `watering_mode` | enum | `classic` \| `service` — actuation of the **inlet** valve |
| `inlet_entity` | entity | classic: switch/**valve**/input_boolean to open/close (valve.* needs `open_valve`/`close_valve`, see §6) |
| `run_service`/`stop_service`/`duration_field`/`duration_unit`/`run_data` | | service mode (self-closing blueprint) |
| `confirm_entity` | entity, opt | flow confirmation, physically on the **distributor inlet** |
| `flow_sensor` | entity, opt | flow meter, physically on the **distributor inlet** (downstream of any branch to other zones — §6) |
| `pause_seconds` | int | default **300** (§4.5 floor) |
| `skip_pulse_seconds` | int | default **30** (§4.5 floor) |
| `current_outlet` | int (1..n) | **persisted after every advance** |
| `position_state` | enum | `synced` \| `uncertain` — **defaults to `uncertain` on creation** (§4.2) |
| `notify_target` | notify service/entity, opt | halt notifications |
| `use_master` | bool | engage the global master (default: true iff a master is configured). If **false**, all master steps in §5.3 are omitted (inlet-only cycle). |
| `schedules` | list | reuse schedule infra via a new distributor target type (§5.5) |
| `commissioning_confirmed` | bool | default **false** — the distributor is **inert** (no scheduled / `run_now` watering) until the user confirms a successful test run. Can only be set true while `position_state == synced`; **auto-cleared to false on any transition to `uncertain`** (§7). Toggling on requires a UI confirmation popup (§4.2, §5.1). |

Master whole-cycle vs per-window coupling is **derived from the existing `master_off_after`** setting (§5.3) — no new field.

### 4.2 Initial position trust (fail-safe on creation)

A newly created distributor — and any distributor materialised by migration — **starts `position_state = uncertain`**, never `synced`. The physical device may sit at any outlet; HASI has never observed it. The **first cycle is blocked** by the §5.1 guard until the user performs an initial re-sync (read the window → `distributor_set_outlet`). This prevents a first run watering blind over wrong outlets.

**Commissioning flow (surfaced in UI):**
1. Map member zones to outlets 1..n.
2. Advance the physical device to **outlet 1** (Wahl-Taste, reading the window) and re-sync to 1, so the healthy steady state — each cycle begins at outlet 1 — holds from the start.
3. Press the **Test-run button** (§10): a short sweep watering **each outlet 30 s** regardless of due/skip. *Watch* that every zone is watered in the correct order and the device advances reliably with the chosen pause/skip. Repeat (adjust mapping/pause/skip, re-sync) until correct.
4. Only then set the **commissioning-confirmed** checkbox/switch (a **confirmation popup** appears) to release the distributor for scheduled operation.

Until `commissioning_confirmed` is set, the distributor **never** waters via a schedule (§5.1).

### 4.3 Zone additions & mapping validation

Zone gains `distributor_id` (null = normal zone) and `outlet_number` (1..n).

- Member zones occupy outlets **1..n contiguously** (no gaps/duplicates), **n ∈ {2..6}**. Every active device outlet maps to **exactly one** HASI zone.
- **Ring-topology change forces re-sync:** any change to n (add/remove a member, remap outlets) implies the user moved a physical flow lever — a device change HASI cannot observe and that itself may alter the ring/position. Such a change **sets `position_state = uncertain`**, **clamps** `current_outlet` into 1..n, and **clears `commissioning_confirmed`** — the prior successful test no longer applies to the changed ring, so a re-sync + re-test + re-confirm is required before the next cycle.

### 4.4 Persistence & migration

- Distributors are a **new top-level store collection**. This touches four hardcoded spots in `store.py` (all must be edited — the code does **not** loop over collections): `SmartIrrigationStorage.__init__` (add `self.distributors`), `async_load` (add a `"distributors"` hydration block), `_data_to_save` (append `store_data["distributors"]` — currently a hardcoded dict of config/zones/modules/mappings, so distributors are silently **not** persisted unless added), and `_async_migrate_func` (v10 → v11). Plus CRUD (`async_create/update/delete_distributor`, reusing `generate_next_id`) and the panel command surface in `websockets.py`/`panel.py` (panel CRUD goes through WebSocket/HTTP, not config_flow).
- **In-flight cycle record** `{distributor_id, outlet, phase, started, expected_advance_at}` for restart reconciliation. **Caution:** the `Config` attrs class is a **strict allowlist** — the migration strips any config key not in `attr.fields_dict(Config)`. So this key must be a declared `Config` attr, or (preferred) live on the distributor object / a dedicated store list, else it is silently deleted on every load.
- **Zone-field footgun:** new `ZoneEntry` attrs (`slots=True, frozen=True`) must **also be hydrated explicitly in `async_load`** with `zone.get(...)`; the existing self-closing fields carry a comment warning they "silently revert on every reload" if this hydration is omitted. Migration alone is insufficient.
- **Storage migration v10 → v11:** create empty `distributors`; add `distributor_id=None`, `outlet_number=None` to every zone (+ async_load hydration).

### 4.5 Duration floors (silent-desync mitigation)

`pause_seconds` and `skip_pulse_seconds` too short → the device silently fails to advance while HASI still increments and persists `current_outlet` → **cumulative off-by-one for the rest of the cycle, undetectable open-loop.**
- **Hard minimum 10 s** for both `pause_seconds` and `skip_pulse_seconds` — values below are rejected/clamped. 10 s suffices to bleed pressure on typical setups; the true safe value depends on what is connected.
- The UI keeps an explicit **warning** (not a soft hint): *too short → silent, cumulative desync HASI cannot detect*; it additionally warns when `skip_pulse_seconds` is below the connected valve's min-runtime (e.g. Tuya 60 s).
- The UI directs the user to an **observed first run** and further test runs until confident that the chosen pause/skip reliably advance the device (§4.2).

---

## 5. Operating Cycle

Triggered by a distributor schedule (§5.5) or `distributor_run_now` (§7). One firing = one cycle. A distributor is **single-flight**: a second trigger while a cycle is active for that distributor is rejected.

### 5.1 Cycle algorithm

1. **Guard:** a scheduled cycle or `distributor_run_now` runs only if `position_state == synced` **and** `commissioning_confirmed == true`; otherwise **halt** (notify on a `synced` failure), do not run — this blocks the first-ever run (§4.2) and any unconfirmed/uncertain distributor (avoids the Ch. 8 wrong-outlet damage). The **Test-run** (§10) is **exempt** from the `commissioning_confirmed` requirement but still needs `synced` + single-flight.
2. **Rule B — empty cycle:** if **no** member zone needs *actual watering* today (predicate §5.2) → do nothing, no switching, position unchanged. No advances ⇒ no drift. A whole-cycle rain-delay or all-vetoed/all-not-due day collapses to Rule B.
3. **Rule A — full sweep:** if **≥ 1** zone needs actual watering → engage master (if configured, §5.3), then, in physical order **starting at `current_outlet`**, exactly **one ON-window per outlet** servicing all n outlets:
   - zone needs water → open inlet for its **calculated duration**; else → open inlet for **`skip_pulse_seconds`**;
   - if a sensor is configured, confirm flow and attribute the run/volume to the active zone (§6);
   - close inlet → wait `pause_seconds` → device advances → **persist** new `current_outlet`;
   - **no-flow while watering** (sensor configured) → close, mark `uncertain`, **halt + notify**, stop cycle.
4. After n ON-windows the position returns to where the cycle **started**. Master off per §5.3.

**Start position:** a healthy cycle **begins at `current_outlet` and does not re-home** (autonomous re-home is impossible, §1.2). "Ends at outlet 1" is only the steady-state observation when the previous cycle also started at 1; it is **not** a re-home step. A cycle is numerically correct from any known start position (each zone serviced once, in ring order).

**Invariant caveat:** "exactly n advances, ends at start" guarantees only **advance-count consistency**, *not* correct outlet-to-zone alignment. If `current_outlet` has silently drifted by one, the cycle still completes and "ends at start" while every zone received its neighbour's water. Correctness depends solely on an accurate `current_outlet`, which is unverifiable open-loop.

### 5.2 Skip vs. empty predicate

- **Needs actual watering** = zone is AUTOMATIC (or manual-run), calculated `duration > 0`, and not currently held (rain-delay) or soil-vetoed.
- A zone **skipped** (not-due / soil-vetoed / rain-delay-held / **disabled**) inside a Rule-A sweep still gets a **skip-pulse** — its outlet is a physical ring position that cannot be omitted.
- **Explicit rule (load-bearing):** *A disabled member zone MUST still receive a `skip_pulse_seconds` advance. Disabling a zone in HASI does NOT remove its outlet from the ring; only a physical flow-lever change (which changes n, §4.3) does.*
- Rule B (no switching) applies **only** when **no** zone needs actual watering; otherwise it is a full Rule-A sweep with the non-watering outlets skip-pulsed.
- Skip-pulse windows are **not** credited to the bucket.

### 5.3 Master coupling

Derived from `master_off_after`: **true** → master off whenever not watering → off during inter-outlet pauses → **cycles per window**; **false** → **stays on** the whole cycle. If `use_master = false`, all master steps are omitted (inlet-only).

**NOT-TO-DO (critical):** never toggle the master while **any** inlet is open — the distributor would see an extra pressure edge and advance unintentionally. Strict per-window order: `Master ON → settle → inlet OPEN → water → inlet CLOSE → pause (= advance) → Master OFF`. The distributor sees pressure changes **only** via its inlet valve.

**Implementation reality (feasibility):** `MasterMixin` holds a **single** instance-level cycle (`self._master_on`, `_master_off_deadline`, one `async_call_later` timer) and turns off via a **deferred** timer, not a synchronous per-window off; `async_master_begin_cycle` no-ops while `_master_on` is set. Per-window synchronous on/off therefore needs **new MasterMixin primitives** (synchronous `on`/`off` that bypass the deferred model) and must reconcile ownership with the shared `_master_on` flag — it is **not** a free derivation of `master_off_after`.

**Multi-holder arbitration** (multiple distributors and/or normal zones sharing one master): **reference-count** master holders; **forbid any master-off while ANY inlet (any distributor or zone) is open**; when the master is shared, fall back to **whole-cycle** (stays on until the last holder finishes). Per-window cycling applies only when a distributor holds the master **exclusively**. Behaviour with distributors of opposite `master_off_after` sharing one master is defined by "off only when no holder needs it and no inlet is open."

### 5.4 Sequencing integration (dispatch)

The distributor is **dispatched by its own entry point** (`async_run_distributor_cycle`), **not** by piggybacking the zone list — `_irrigate_linked_entities` builds a flat list of zone dicts keyed on `ZONE_LINKED_ENTITY`, has no item abstraction, and member zones have no linked entity. Requirements:
- `_irrigate_linked_entities` must **exclude** zones with `distributor_id` set (a stray linked entity on a member zone must never double-water).
- The **rotating** time-slicer must **never** receive member zones.
- "**Atomic** in sequential/rotating" is achieved by running the whole sweep as its own task; it is inherently non-interleaved.
- **Parallel mode is best-effort with an explicit, undetected desync risk:** concurrent draw can drop inlet pressure below 1 bar and silently prevent an advance, which HASI cannot detect. **Recommended: run distributors in sequential mode.** The UI warns against watering too much simultaneously.

### 5.5 Schedule binding

Schedules currently bind to zones only (`SCHEDULE_CONF_ZONES`; `_perform_schedule_action` → `_irrigate_linked_entities`). Add a **schedule target discriminator** (e.g. `SCHEDULE_CONF_DISTRIBUTORS` / a target type) and a **branch** in `_perform_schedule_action` that calls `async_run_distributor_cycle`.

**Finish-anchored schedules are supported** (sunset/solar "finish by…"). The whole-cycle duration is deterministic and known at schedule-eval time (the daily calculation has already set each member's duration), so HASI provides a **distributor-aware duration estimate**:

`estimate = Σ (per-zone due duration OR skip_pulse_seconds) + n·pause_seconds + master settle/kick overhead + safety_buffer`

fed to the finish-anchor math (`_estimate_duration` / `async_get_upcoming_runs` / `_setup_finish_tracker`) in place of the per-zone assumption. The **safety buffer** absorbs pause/settle slack so the sweep reliably finishes by the anchor. The estimate must integrate with the (recently fixed) finish-tracker without reintroducing the negative-offset busy-loop.

---

## 6. Actuation & Run Tracking

The distributor needs a **bespoke run loop** — the existing `_run_valve_metered` is **not** reusable (it opens `zone[ZONE_LINKED_ENTITY]`, reads a **per-zone** flow sensor, and has no pause/advance step). Reusable **leaf helpers only:** `_confirm_valve_running`, `_record_run`, `_timed_volume_l`, and the depth-from-volume helper.

- **classic:** open inlet → wait duration → close → pause. Inlet open/close must use the **valve-domain mapping** from `MasterMixin._master_turn` (a `valve.*` inlet needs `open_valve`/`close_valve`, not `turn_on`/`turn_off`) — extract it into a shared helper.
- **service (self-closing):** fire `run_service` with duration → hardware self-closes → wait (duration + pause) → advance. Mind min-runtime (§4.5).

**Shared inlet confirm/flow sensor**, attributed to the active outlet:
- `confirm_entity`: confirm "flow on" at open (`_confirm_valve_running`); no flow during a watering window → safety-halt (§7).
- `flow_sensor`: measure delivered volume during the window → credit the active zone via `_record_run(zone_id=member_zone, volume_l=…)` (the runner calls this directly). Skip-pulses are **not** credited.

**Explicit limitation (must sit next to the credit logic):** the shared inlet sensor sees **total flow only**; it can **never** identify which outlet is live. A "flow confirmed" reading is **not** position confirmation — if the position has silently drifted, the sensor happily confirms flow and HASI credits the **wrong** zone's bucket while watering the wrong plants, with no halt. Flow metering thus protects only against **total no-flow**, never against wrong-outlet desync, and can **launder** a desync into false bucket credit. This is an accepted consequence of open-loop operation.

---

## 7. Recovery & Safety

- **Persistence:** `current_outlet` + `position_state` written after **every** advance. "**Confirmed advance**" for a blind device means only "**the pause timer elapsed**" — there is no real confirmation signal. Persist ordering must guarantee a crash in the gap between the physical advance and the persist write resolves to **`uncertain`**, never a wrongly-incremented `synced` position.
- **Restart reconciliation** (mirrors `self_closing.py`):
  - crash **during a watering window** (before the advance) → position still known → close inlet defensively, **abort** the cycle at the known position, stay `synced`. **Un-serviced remaining zones are skipped for the day; the next scheduled cycle resumes from `current_outlet`.**
  - crash **during pause/advance** (or power loss with the inlet open) → advance completion unknown → mark **`uncertain`** → halt next cycle + notify + require re-sync.
- **External / manual actuation between cycles:** if `inlet_entity` changes state **outside** a HASI cycle (manual open, a foreign automation, power event) → mark `position_state = uncertain`. The physical **Wahl-Taste cannot be detected** by HASI → after pressing it the user must re-sync; the UI states this responsibility.
- **Manual re-sync (primary):** service `distributor_set_outlet` (distributor + outlet N read from the window) **and** a per-distributor button; convenience "set to 1". Sets `position_state = synced`.
- **Safety-halt (only with a configured sensor):** flow expected but none → close inlet, mark `uncertain`, stop cycle, **notify** `notify_target`. Without a sensor there is no detection → pure open-loop trust.
- **`uncertain` blocks the next cycle** (§5.1 guard) — HASI waits for a re-sync rather than watering blind.
- **Any transition to `uncertain` also clears `commissioning_confirmed`** (the arm-switch drops to off) — a lost or doubtful sync automatically **de-arms** the distributor. Re-arming requires the full sequence: re-sync (`distributor_set_outlet` → `synced`) → optional test-run → re-set the confirmation switch (popup). The switch **cannot** be set while `uncertain`; the off switch is the visible signal that user action is needed.

---

## 8. Configuration & UI

New **Distributor** branch in the panel: create/edit/delete distributors (§4.1 fields); pause/skip inputs with the explicit failure-mode text (§4.5); notify picker; master engagement; a **parallel-mode / concurrent-draw pressure warning**; a **Test-run button** (short 30 s/outlet sweep, §10); a **commissioning-confirmed checkbox/switch** with a **confirmation popup** that gates scheduled operation (§4.1/§5.1); a visible note that the **Wahl-Taste is undetectable → re-sync after use**, that **changing outlets forces a re-sync + re-confirm** (§4.3), and the **commissioning flow** (device to outlet 1, re-sync, test-run, then confirm — §4.2); and — when **master "off after irrigation"** is enabled on **sequential or rotating** sequencing — a note that the master (**pump**) is **cycled per outlet** during the distributor's pauses (§5.3). Zone form gains a "belongs to distributor X, outlet N" selector; when set, the zone's own valve/schedule fields are hidden/disabled. Validation: contiguous 1..n, n ≥ 2. CRUD is wired through `websockets.py`/`panel.py` (§4.4).

**Visual convention (hard requirement):** the distributor branch must **reuse the existing panel's look** — the same cards, form controls, toggles, spacing, typography and layout patterns already used for zones/modules. It must **blend into the current UI**, not introduce a new visual style. Study the existing frontend components first and mirror them.

## 9. Internationalization

All new UI strings (config, mapping, pause/skip failure-mode text, warnings, re-sync service, notify) in **all 8 languages**.

## 10. Services & Events

- `distributor_set_outlet` (re-sync; sets `synced`), `distributor_resync_home` (set to 1), `distributor_run_now` (manual cycle — **subject to the §5.1 guard** and **single-flight** per distributor; rejected if a cycle is active), `distributor_test_run` (commissioning sweep: **every** outlet 30 s regardless of due/skip; requires `synced` + single-flight; **exempt** from `commissioning_confirmed`; lets the user observe advancing + mapping).
- Reuse `EVENT_IRRIGATE_STARTED`/`_FINISHED`/`ZONE_PROBLEM`; add a distributor-halted/uncertain event carrying the reason. Notifications go to `notify_target`.

## 11. Testing Strategy (TDD)

Tests follow `test_master.py`/`test_self_closing.py` (mixin host + `AsyncMock`):
- cycle loop: Rule-A full sweep, Rule-B empty no-op, skip-pulse path, the skip-vs-empty predicate (incl. whole-cycle rain-delay → Rule B, disabled zone → skip-pulse);
- start-at-`current_outlet` (no re-home) and advance count = n;
- position persistence + persist-ordering (crash-in-gap → uncertain);
- restart reconciliation matrix (mid-watering abort → skip remainder, stay synced; mid-pause → uncertain);
- fresh-install → `uncertain` blocks first cycle; ring-topology change (n change) → `uncertain` + clamp; external inlet actuation → `uncertain`;
- manual re-sync service; safety-halt on no-flow; `uncertain` blocks next cycle;
- master coupling (whole vs per-window; `use_master=false` inlet-only; NOT-TO-DO ordering; multi-holder arbitration / shared-master fallback);
- valve-domain inlet actuation (`valve.*` → open_valve/close_valve);
- `distributor_run_now` (uncertain-guard + single-flight);
- `distributor_test_run` (fixed 30 s/outlet across all outlets; requires `synced`; exempt from `commissioning_confirmed`; single-flight);
- commissioning gate: scheduled / `run_now` cycle blocked while `commissioning_confirmed == false`; a ring-topology (n) change clears it;
- any `uncertain` transition (safety-halt, mid-pause restart, external actuation, n change) auto-clears `commissioning_confirmed`; the switch cannot be armed while `uncertain`;
- distributor cycle duration estimate for finish-anchored schedules (Σ durations + n·pause + skip pulses + safety buffer);
- sequencing exclusion (member zones excluded from `_irrigate_linked_entities`; never handed to the rotating slicer);
- store round-trip (all four store.py insertion points; Config-allowlist not stripping the in-flight key; zone-field async_load hydration);
- storage migration v10 → v11.

## 12. Versioning & Beta

- Branch `feature/gardena-distributor` from `production` (v2026.07.10).
- Beta 1 = **full feature incl. panel UI + i18n** (the user must be able to configure what to test).
- Beta version **PEP440 `bN`** (e.g. `v2026.07.11b1`), released as **pre-release**, installable on the **test system 192.168.10.196** via HACS. Frontend rebuilt (`dist`).
- Long live-test phase before any promotion to `production`.

## 13. Out-of-Scope (future)

Auto re-home via an outlet-specific sensor; multiple schedules per distributor; per-outlet statistics.

## 14. Key Assumptions

- The inlet valve is downstream of the (optional) global master; the `flow_sensor`/`confirm_entity` are on the **distributor inlet** (downstream of any branch to other zones).
- Normal zones and distributors share the global master and typically the supply → concurrency governed by the sequencing setting (sequential recommended) + pressure warning.
- The device behaves per the Art. 1197 manual (variant B: no auto-reset), confirmed by the user.

## 15. Codebase Integration Notes (from feasibility review)

Load-bearing implementation cautions surfaced against the real code (to be honoured by the plan):
1. **Bespoke runner**, not `_run_valve_metered` reuse (§6); only leaf helpers reusable.
2. **New synchronous MasterMixin primitives** for per-window on/off; reconcile with the shared single-cycle `_master_on` state (§5.3).
3. **Own store collection** = 4 hardcoded `store.py` edits + CRUD + WS/HTTP panel commands; `_data_to_save` is a hardcoded dict (§4.4).
4. **Migration footguns:** `ZoneEntry` new attrs need explicit `async_load` hydration; `Config` is a strict allowlist that strips unknown keys (§4.4).
5. **Schedule binding** needs a new target discriminator + dispatch branch; start-anchor only in Beta 1 (§5.5).
6. **Valve-domain mapping** required for a `valve.*` inlet (§6).
