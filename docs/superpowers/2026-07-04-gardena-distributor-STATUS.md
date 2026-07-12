# Gardena Wasserverteiler automatic — Feature Status

**Branch:** `feature/gardena-distributor` (from `production` v2026.07.10) · **38 feature commits** · working tree clean.
**What it is:** support for the Gardena "Wasserverteiler automatic" (Art. 1197) — one inlet valve feeding a pressure-driven ring of 2–6 outlets, one HASI zone per outlet. Open-loop position counting, restart-safe, fail-safe on desync.

## Status

| Plan | Scope | State |
|---|---|---|
| **A** Data layer | `DistributorEntry`, migration v10→v11, store CRUD | ✅ done, tested, reviewed |
| **B** Engine primitives | inlet actuation, advance+persist, uncertain/de-arm+notify, master window, duration estimate | ✅ done, tested, reviewed |
| **C** Cycle loop + recovery | Rule A/B sweep, guard, skip-pulse, safety-halt, phase-based restart reconciliation, test-run, re-sync | ✅ done, tested, reviewed |
| **D** Integration + services | `DistributorMixin` wired in, startup reconciliation hook, member-zone exclusion, 4 operation services | ✅ done, tested, reviewed |
| **E** Config API | `async_upsert_distributor` (create/update/delete, 400-guarded), HTTP POST view + WS read, zone POST accepts `distributor_id`/`outlet_number` | ✅ done, tested, reviewed |
| **F** Panel UI (frontend) | Lit/TS config + commissioning UI, i18n ×8, rollup build | ⏳ **next** — see `plans/2026-07-04-gardena-distributor-plan-f-panel-ui.md` |
| **G** Scheduler | automatic schedule dispatch + finish-anchor | ⏸ Beta 2 |

The **entire Python backend + integration + config API is complete** (`distributor.py` 519 LOC + store/websockets/services), all distributor tests green, 7 adversarial reviews passed (each caught & fixed real bugs). **Frontend is the only remaining piece before a testable beta.**

## What is exercisable NOW (before the UI)

- **Operate** an existing distributor from *Developer Tools → Services*: `smart_irrigation.distributor_test_run` / `distributor_set_outlet` / `distributor_resync_home` / `distributor_run_now` (each takes `distributor_id`).
- **Create/configure** a distributor before the UI exists needs an HTTP `POST /api/smart_irrigation/distributors` (e.g. curl with a long-lived token) — or just wait for Plan F. Zone→outlet mapping = POST the zone with `distributor_id` + `outlet_number`.
- **Guardrails already enforced:** a scheduled/`run_now` cycle runs only when `position_state == synced` AND `commissioning_confirmed`; the commissioning switch auto-drops to off on any `uncertain`; member zones are excluded from the normal watering path; restart reconciliation runs at startup.

## Dev facts

- **Tests (backend):** `PYTHONPATH=<S> <S>/uvenv312/Scripts/python.exe -m pytest tests/test_distributor*.py -p _local_socket_unblock` with `S = C:/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad` (system Python 3.13 does NOT work).
- **Build (frontend):** `cd custom_components/smart_irrigation/frontend && npm run build` (node v24 / npm 11; runs green). vitest: `npm run test`.
- **Test HA:** 192.168.10.196 (route MCP via `mcp__HA-Test__`). Never restart HA unprompted.
- **Beta:** PEP440 `bN` (e.g. `v2026.07.11b1`, NEVER `-betaN`), pre-release, HACS install on the test system, long live-test.

## Docs

- Spec: `docs/superpowers/specs/2026-07-04-gardena-distributor-design.md` (rev. 4).
- Plans: `docs/superpowers/plans/2026-07-04-gardena-distributor-plan-{a,b,c,d,e}-*.md` (done) + `-plan-f-panel-ui.md` (handoff for the frontend).
