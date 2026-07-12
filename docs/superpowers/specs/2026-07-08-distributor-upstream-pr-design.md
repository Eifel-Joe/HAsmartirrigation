# Distributor upstream PR — reconstruction design

Date: 2026-07-08
Branch (source): `feature/gardena-distributor` (tip v2026.07.11b28)
Target: a clean PR of the Gardena distributor feature onto **JustChr `upstream/master`**
(tip db2ab45), opened from the Eifel-Joe fork.

## Problem

We need a clean, reviewable PR containing **only the distributor feature** on top of
current JustChr `upstream/master`, without fork branding, version bumps, or 35
`docs/superpowers/**` process files.

**Ancestry (verified 2026-07-08).** The distributor was built on the Eifel-Joe
**`production`** branch (release **v2026.07.10**), NOT directly on upstream: `production`
IS an ancestor of `feature/gardena-distributor` (merge-base = production's tip `424417e`),
and `feature/gardena-distributor` = `production` **+ 184 distributor commits** (0
production-only). So the **true, clean distributor feature is `git diff production…gardena`**
— production is the real base.

**production ≈ upstream in code (verified).** `git diff upstream/master origin/production`
is **only 8 non-logic files**: `README.md` (fork branding), the `VERSION`/`manifest`/
`package.json`/`dist` version strings, and `.github/workflows/release-zip.yml` (a CI file).
**No feature-code file differs.** Everything the user authored on production (soil-veto,
collapsible zones, the scheduler solar-offset fixes, `binary_sensor` init, keyboard-input
fix, the zone-header tweak) was merged into upstream and is **byte-identical** there — the
two branches only differ in release-tag cadence (JustChr's v2026.07.03 code == production's
v2026.07.10 code). `scheduler.py`, for instance, is **identical** in production and upstream.

**Consequence — nothing is lost, and the rebuild is low-conflict.** Because upstream's code
== production's code, applying the distributor diff (`production…gardena`) onto
`upstream/master` sits on an **identical code foundation**: no distributor code is dropped,
and conflicts are limited to the version-string / branding files we deliberately do not
carry. The distributor's own soil-veto-scope calls upstream's `_apply_soil_moisture_veto`
(irrigation.py) — present on upstream — so no reimplementation is needed.

## Scope (what the PR contains)

The complete **b28 distributor feature**: data layer, engine (`distributor.py`), cycle
loop, integration (coordinator/services/skip/scheduler/sensors/binary_sensor/master
coordination), config API (websockets/services.yaml), device entities, frontend
(components + views + setup nav + zone selector), i18n (8 languages) + HA translations,
inlet-watch modes, notify-i18n, soil-veto scope, graceful-restart reconcile, inlet-form
UX, and the **experimental gating** (opt-in `distributors_enabled` toggle, off by
default) — i.e. the feature ships opt-in/experimental.

**Flow-volume:** INCLUDED in its existing **rate-only (L/min)** form plus **early stop** —
this matches the flow-metering zones already have upstream. The **cumulative** metering
path stays in the code but **dormant** (`DISTRIBUTOR_CUMULATIVE_METERING_ENABLED = False`);
during reconstruction an **explanatory comment** is added at that flag so a reviewer sees
it is deliberate preparation for a future *joint zones+members* cumulative PR, not dead
code. Arming cumulative metering is explicitly a **separate future PR** (it also touches
zones).

**Docs:** the new `docs/configuration-distributors.md` + the companion edits to
`docs/configuration-experimental.md` and `docs/configuration.md` are included.

## Reconstruction mechanic (Approach A — corrected: base = production)

The clean distributor feature is `git diff origin/production…feature/gardena-distributor`.
Because upstream's code == production's code, that diff applies onto `upstream/master` with
conflicts only in version/branding files (which we drop). Mechanic:

1. Fresh branch `fix/gardena-distributor` (working name) **from `upstream/master`**.
   Never touch `production` or `feature/gardena-distributor` — they stay pristine, so
   nothing can be lost at the source; a bad reconstruction is simply discarded and redone.
2. **Apply the distributor delta.** Bring every file in
   `git diff --name-only origin/production…feature/gardena-distributor` onto the new branch
   with feature's version — `git checkout feature/gardena-distributor -- <file>` — because
   for each such file feature = production + distributor and production == upstream, so
   feature's version = upstream + distributor exactly. This covers the ~20 new
   distributor-only files (`distributor.py`, `distributor_entity.py`, the frontend
   distributor components/views, the distributor backend+frontend tests,
   `docs/configuration-distributors.md`) AND the touched shared files (`store.py`,
   `const.py`, `skip_conditions.py`, `irrigation.py`, `binary_sensor.py`, `scheduler.py`,
   `sensor.py`, `__init__.py`, `services.py`, `services.yaml`, `websockets.py`, `button.py`,
   `entity.py`, `diagnostics.py`, `master.py`, `self_closing.py`, `localize.py`, frontend
   `const.ts`/`types.ts`/`smart-irrigation.ts`/`data/websockets.ts`/`view-*.ts`, i18n ×8,
   HA `translations/*.json` ×8, `docs/configuration-experimental.md`,
   `docs/configuration.md`).
3. **Handle the deliberately-excluded files** that appear in that diff only as
   version/branding noise: do **NOT** take feature's version of `const.py`'s `VERSION`
   line, `manifest.json` / `frontend/package.json` version, or the pre-built
   `frontend/dist/*.js`. For `const.py`/`manifest`/`package.json`, take feature's file but
   **revert the version string to upstream's** (they also contain real distributor
   additions, so keep those and only reset the version). Rebuild `dist/` from source.
4. **Rebuild** the frontend `dist/` bundle (`npm run build`) — do not carry feature's
   minified artifacts.
5. Add the dormant-cumulative explanatory comment (see Scope).
6. **Spot-verify the low-conflict claim:** after step 2, `git diff upstream/master --stat`
   must show ONLY distributor content (+ the version files from step 3). If any
   non-distributor file (e.g. a soil-veto/collapsible/scheduler file) shows a real code
   delta, STOP — that would mean production≠upstream somewhere unexpected; investigate
   before continuing.

**Explicitly NOT carried:** all `docs/superpowers/**` (35 files); `README.md` (fork
branding — Eifel-Joe↔JustChr URLs, personal-build note); the `.github/workflows/`
divergence; the `VERSION` / `manifest` / `package.json` beta version strings (reset to
upstream's); the pre-built `frontend/dist/*.js` (rebuild instead). These are all either
absent from `production…gardena` or handled by step 3.

## Commit grouping (~6–8 logical layer commits)

Reconstruct the tree, then stage in layers:
1. **Data layer** — `store.py`, `const.py`, `entity.py`, `distributor_entity.py`.
2. **Engine** — `distributor.py`, `master.py` distributor bits, `self_closing.py` residue.
3. **Integration** — `__init__.py`, `skip_conditions.py`, `scheduler.py`, `sensor.py`,
   `binary_sensor.py`, `irrigation.py`, `button.py`, `diagnostics.py`, `localize.py`.
4. **Config API** — `services.py`, `services.yaml`, `websockets.py`.
5. **Frontend** — `frontend/src/**` (components, views, setup nav, zone gating,
   experimental toggle) + rebuilt `dist/`.
6. **i18n** — `frontend/localize/languages/*.json` (8) + HA `translations/*.json` (8).
7. **Docs** — `configuration-distributors.md` + experimental/index companion edits.
8. **Tests** — all distributor test files (or fold each test into its layer commit — TBD
   at plan time; a single tests commit is acceptable).

Grouping is a guide; the plan finalizes exact file→commit assignment. Each commit message
is plain English, no beta/version noise.

## Verification (the real correctness gate)

- **Full backend test suite green** on the reconstructed branch (via the local 3.12 env,
  `[[hasi-local-test-env-rebuild]]`), and **full frontend vitest suite green** + `tsc` +
  `npm run build` (lint) clean.
- **Diff audit:** `git diff upstream/master --stat` on the reconstructed branch shows
  **only distributor content** (+ the version files reset in mechanic step 3) — no
  README/superpowers/CI files and no phantom reverts of upstream's code. Spot-check the
  no-loss guarantee: `git diff upstream/master…HEAD -- scheduler.py binary_sensor.py`
  should equal the distributor delta only (upstream's scheduler/binary_sensor code intact,
  since production == upstream there).
- **REGEL 8 sister-path check** on the reconstructed `distributor.py` before finishing.

## PR opening (REGEL 5 — gated on user approval)

- Push the branch to the **Eifel-Joe fork**; open the PR **Eifel-Joe:<branch> →
  JustChr:master** via `gh pr create` (per `[[hasi-pr-build-recipe]]`).
- **Show the full PR title + body to the user and get approval BEFORE `gh pr create`.**
  Same for any accompanying issue or comments.
- PR body structure: `## Problem` / `## Fix` / `## Begleitende Änderungen` /
  `## Abhängigkeiten`. State that it is opt-in/experimental, that flow-volume is rate-only
  with cumulative dormant, and that it builds on the already-merged self-closing + master
  + soil-veto work. **No IP addresses, no fork branding.**

## Out of scope

- Arming cumulative flow metering (separate future zones+members PR).
- Any change to already-upstream features (soil-veto, collapsible, self-closing, master).
- The scheduler dispatch "Beta 2" and any not-yet-shipped distributor work.

## Risks

- **No source-branch data loss** by construction: `production` and `feature/gardena-distributor`
  are never modified; the PR is a fresh branch. A wrong reconstruction is discarded, not
  destructive.
- The one real assumption — "production code == upstream code" — is **verified up front**
  (only 8 version/branding/CI files differ) and **re-checked** by the mechanic step-6 stat
  guard + the diff audit. If a non-version file shows unexpected non-distributor delta, we
  stop and investigate rather than carry it.
- The reconstructed `dist/` must match source — mitigated by rebuilding from source and
  grepping the bundle for a known distributor string.
- Full backend + frontend test suites are the ultimate correctness gate; upstream's own
  tests (scheduler, binary_sensor, soil-veto) must stay green, proving no upstream code was
  reverted.
