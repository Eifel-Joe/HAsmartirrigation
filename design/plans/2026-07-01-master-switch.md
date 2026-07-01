# Master Switch / Pump Control — Implementation Plan

> **For agentic workers:** execute task-by-task, TDD. Steps use `- [ ]`.

**Goal:** Optional instance-level master switch (pump / main valve) that HASI
turns on before a watering cycle (with an optional pressure "kicker" pulse and a
settle delay) and optionally off after the last zone's planned end.

**Architecture:** A new `MasterMixin` (like `SelfClosingMixin`) owns the master
sequencing; the three actuation entry points in `irrigation.py` call its hooks.
Config is instance-level (`Config`), edited in General settings. Fully optional:
no master entity → HASI never touches the pump (today's behavior).

**Design ref:** `docs/specs/2026-06-30-self-closing-valve-mode.md` §4.4, §7 (plus
the user's kicker addition: off → pause → on to force pump restart).

**Local test runner (backend):**
`PYTHONPATH=<scratch> <uvenv312>/Scripts/python.exe -m pytest <targets> -p _local_socket_unblock -p no:cacheprovider -p no:sugar -o addopts="" --timeout=120 -q`

---

### Task 1: Config schema (const + Config + migration v11)

**Files:** `const.py`, `store.py`; Test: `tests/test_master.py` (new)

Fields (all optional, default off):
- `master_entity` (str, default None) — switch/valve/input_boolean to actuate.
- `master_settle_seconds` (int, default 10) — wait after turn-on before zone 1.
- `master_kick_enabled` (bool, default False) — pulse off→pause→on first.
- `master_kick_pause_seconds` (float, default 1.0) — the off↔on gap.
- `master_off_after` (bool, default False) — turn off after the cycle; False =
  stay powered (self-monitoring pump).

- [ ] **Step 1 — failing test:** `STORAGE_VERSION == 11`; a fresh `Config()` has
  the five master fields with the defaults above; migrating a v10 `data` dict
  seeds `config.master_settle_seconds=10`, `master_kick_pause_seconds=1.0`,
  and the booleans False, `master_entity=None`.
- [ ] **Step 2 — RED.**
- [ ] **Step 3 — implement:** add `CONF_MASTER_*` to const.py; add the five
  `attr.ib` fields to `Config`; `STORAGE_VERSION = 11`; migration
  `if old_version <= 10:` sets `data.setdefault("config", {}).setdefault(...)`
  for each; the config load in `async_load` reads them via
  `data["config"].get(CONF_MASTER_*, default)`.
- [ ] **Step 4 — GREEN** targeted + full suite (regression vs baseline).
- [ ] **Step 5 — commit.**

### Task 2: MasterMixin sequencing (`master.py`)

**Files:** Create `custom_components/smart_irrigation/master.py`; Test: `tests/test_master.py`

Methods:
- `_master_configured() -> bool` — `bool(config.master_entity)`.
- `async_master_begin_cycle()` — if configured and not already on: (kick →
  `homeassistant.turn_off` entity, sleep `kick_pause`), then
  `homeassistant.turn_on` entity, sleep `settle`, set `_master_on = True`.
  Idempotent within a cycle (a second call while on is a no-op, no re-settle).
- `_master_note_run(end_ts)` — record the latest expected end across active runs.
- `async_master_schedule_off()` — only if `master_off_after` and configured:
  (re)arm a single `async_call_later` for `max(end_ts) - now`; on fire, if the
  deadline has moved later reschedule, else `homeassistant.turn_off` + reset
  `_master_on`.

- [ ] **Step 1 — failing tests** (mock hass.services.async_call, monkeypatch the
  sleep):
  - kick on: begin_cycle calls turn_off, then (after pause) turn_on; settle
    respected; `_master_on` True.
  - no kick: begin_cycle calls only turn_on then settle.
  - not configured (no entity): begin_cycle is a no-op.
  - already on: second begin_cycle does nothing (no re-kick/re-settle).
  - off disabled (`master_off_after=False`): schedule_off never calls turn_off.
  - off enabled: schedule_off arms a timer; firing at/after deadline calls
    turn_off; a later-extended deadline reschedules instead of turning off.
- [ ] **Step 2 — RED.**
- [ ] **Step 3 — implement** `MasterMixin` (imports: async_call_later, dt_util,
  `from . import const`).
- [ ] **Step 4 — GREEN.**
- [ ] **Step 5 — commit.**

### Task 3: Wire into coordinator + irrigation entry points

**Files:** `__init__.py`, `irrigation.py`; Test: `tests/test_master.py`

- [ ] **Step 1 — failing test:** a stubbed coordinator whose
  `_irrigate_linked_entities` (or the shared dispatch helper) is driven with one
  eligible zone calls `async_master_begin_cycle` before the zone is actuated,
  and `async_master_schedule_off` after; with no master configured, neither
  side-effect changes behavior (classic regression).
- [ ] **Step 2 — RED.**
- [ ] **Step 3 — implement:** add `MasterMixin` to the `SmartIrrigationCoordinator`
  bases in `__init__.py`. In `irrigation.py`, at the start of the dispatch in
  `_irrigate_linked_entities`, `async_irrigate_now`, and `async_run_zone` (once a
  non-empty zone set is known), `await self.async_master_begin_cycle()` before
  the first valve, then note each run's end and `await self.async_master_schedule_off()`.
- [ ] **Step 4 — GREEN** targeted + full suite (regression-free; no-master path
  byte-identical).
- [ ] **Step 5 — commit.**

### Task 4: Frontend config UI + i18n

**Files:** `view-general.ts`, `const.ts`, `types.ts`, all 8 `localize/languages/*.json`

- [ ] **Step 1:** add a "Pump / Master switch" subsection under the General
  "watering" section: entity picker (`master_entity`), kicker toggle +
  kick-pause number, settle-seconds number, "turn off after" toggle. Each saves
  via `handleConfigChange({...})`.
- [ ] **Step 2:** add the config keys to `const.ts`, the `SmartIrrigationConfig`
  fields + defaults to `types.ts`.
- [ ] **Step 3:** add labels/help to `en.json` + `de.json`; the other six fall
  back (or fill via the i18n workflow).
- [ ] **Step 4 — build:** `npm run lint:fix && npm run build`; vitest; validate
  JSON; dist freshness.
- [ ] **Step 5 — commit** (`git add -f` dist bundles).

### Task 5: Docs + final review

- [ ] README "Self-closing valves & blueprints" section: add a short "Pump /
  master switch (optional)" note incl. the kicker + the self-monitoring-pump
  "leave on" default + the crash caveat (master_off exposes a non-self-closing
  pump; documented, not solved — spec §7).
- [ ] Full backend suite regression-free; frontend build green; dispatch a
  code-review subagent over the whole diff.
- [ ] Commit + push.

---

## Self-review
- Spec coverage: config (T1), sequencing incl. kicker + optional off (T2),
  wiring at all 3 entry points (T3), UI + i18n (T4), docs + review (T5).
- No placeholders; each backend task is test → RED → impl → GREEN → commit.
- Crash exposure (master_off + HA death) is documented, not solved (spec §7).
