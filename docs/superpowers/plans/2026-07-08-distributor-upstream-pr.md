# Distributor upstream PR reconstruction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this is git branch surgery, not TDD — execute inline with checkpoints). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Produce a clean branch containing ONLY the Gardena distributor feature on top of JustChr `upstream/master`, verified by the full test suite + a diff audit, then open a PR (gated on user approval).

**Architecture:** The distributor feature = `git diff origin/production…feature/gardena-distributor`. Since `production` code == `upstream/master` code (verified: only 8 version/branding/CI files differ, no feature-code file), checking out feature's version of the distributor-touched files onto a fresh upstream branch yields `upstream + distributor` exactly. Version strings are reset to upstream's; `dist/` is rebuilt; `manifest.json`/`package.json` keep upstream's (JustChr branding). Nothing is destructive — `production` and `feature/gardena-distributor` are never modified.

**Tech Stack:** git, Python (HA integration), Lit/TS frontend, gh CLI.

**Spec:** `docs/superpowers/specs/2026-07-08-distributor-upstream-pr-design.md`

---

## Preconditions
- Local pytest env (`[[hasi-local-test-env-rebuild]]`): `NEW="/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/b0bd5d8c-56f1-46b8-88e3-5b43193abbf1/scratchpad"`, `PY="$NEW/uvenv312/Scripts/python.exe"`.
- `git fetch upstream` is current (upstream/master = db2ab45, v2026.07.03).
- Working tree clean on `feature/gardena-distributor` (only `uv.lock` untracked).

---

## Task 1: Build the reconstructed tree on a fresh upstream branch

**Files:** creates branch `fix/gardena-distributor`; brings the distributor delta.

- [ ] **Step 1: Fresh branch from upstream/master**
```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git checkout -b fix/gardena-distributor upstream/master
```
Expected: new branch at db2ab45. (`production` and `feature/gardena-distributor` untouched.)

- [ ] **Step 2: Bring the distributor-touched files from feature (all except the version/branding files).**
```bash
git checkout feature/gardena-distributor -- $(git diff --name-only origin/production...feature/gardena-distributor \
  | grep -v 'docs/superpowers/' \
  | grep -vE 'frontend/dist/' \
  | grep -vE 'custom_components/smart_irrigation/manifest\.json$' \
  | grep -vE 'custom_components/smart_irrigation/frontend/package\.json$')
```
This stages the 20 new distributor files + ~51 shared files (`store.py`, `const.py`, `distributor.py`, all frontend src, i18n ×8, HA translations ×8, the 3 docs, distributor tests, etc.). `manifest.json` + `frontend/package.json` are deliberately left as upstream's (the distributor changed only their version). `dist/` is left as upstream's for now (rebuilt in Step 5).

- [ ] **Step 3: Reset the `const.py` VERSION string to upstream's.** `git checkout` brought feature's `const.py` (with real distributor constants) but its `VERSION = "v2026.07.11b28"`. Reset it:
```bash
sed -i 's/^VERSION = "v2026.07.11b28"/VERSION = "v2026.07.03"/' custom_components/smart_irrigation/const.py
grep -m1 '^VERSION' custom_components/smart_irrigation/const.py
```
Expected: `VERSION = "v2026.07.03"`. (If the beta string differs, adjust the sed to match the actual current VERSION line — verify with `grep '^VERSION' const.py` first.)

- [ ] **Step 4: Add the dormant-cumulative explanatory comment** at `const.py` (the line `DISTRIBUTOR_CUMULATIVE_METERING_ENABLED = False`, ~L649). Use Edit to replace that single line with a commented block:
```python
# Cumulative (snapshot-delta) flow metering is implemented but kept DORMANT for now:
# the distributor ships rate-only (L/min) metering, matching the flow-metering zones
# already use. Cumulative metering is intended to be armed for zones AND distributor
# members together in a later change, so the code path is present but gated off here to
# avoid a half-wired feature. Flipping this to True without the companion zone work would
# double-count. See the distributor docs / PR discussion.
DISTRIBUTOR_CUMULATIVE_METERING_ENABLED = False
```
(Match surrounding indentation; the constant is module-level.)

- [ ] **Step 5: Rebuild the frontend `dist/` bundle from the new source.**
```bash
cd custom_components/smart_irrigation/frontend
npm run build 2>&1 | tail -5
grep -c "Mechanical water distributors" dist/smart-irrigation.js
cd /d/Entwicklung/HASI/HAsmartirrigation
```
Expected: build succeeds (lint clean — the b28 test files were already prettier-fixed on feature), and the distributor string count is `1`. `dist/*.js` now reflect the reconstructed source.

- [ ] **Step 6: DIFF AUDIT (the no-loss / low-conflict gate).**
```bash
echo "=== changed vs upstream (should be distributor-only) ==="
git add -A && git diff --cached --stat upstream/master | tail -30
echo "=== upstream code intact? (these must show ONLY distributor additions, no reverts of upstream fixes) ==="
git diff --cached upstream/master -- custom_components/smart_irrigation/scheduler.py custom_components/smart_irrigation/binary_sensor.py | head -40
echo "=== must NOT appear: README.md, docs/superpowers, .github/workflows, manifest/package version bumps ==="
git diff --cached --name-only upstream/master | grep -iE 'README|superpowers|\.github/|manifest\.json|package\.json' || echo "clean — none of the excluded files changed"
```
Expected: changed files are distributor-only; `scheduler.py`/`binary_sensor.py` show only the small distributor additions (upstream's own code intact); the excluded-files grep prints "clean". **If any non-distributor code delta or excluded file appears, STOP and investigate** — do not proceed.

---

## Task 2: Verify — full test suites + REGEL 8

**Files:** none (verification).

- [ ] **Step 1: Backend full suite.**
```bash
PYTHONPATH="$NEW" "$PY" -m pytest tests/ -p _local_socket_unblock -q 2>&1 | tail -12
```
Expected: distributor + upstream tests pass. Baseline pre-existing failures (diagnostics/init/panel/etc. per `[[hasi-local-test-env-rebuild]]`, ~7 failed + 60 errors) unchanged; **0 distributor regressions, and the soil-veto/scheduler/binary_sensor tests (upstream's) stay green** — proving no upstream code was reverted.

- [ ] **Step 2: Frontend suite + type-check.**
```bash
cd custom_components/smart_irrigation/frontend
npm test 2>&1 | tail -6
npx tsc --noEmit && echo "tsc clean"
cd /d/Entwicklung/HASI/HAsmartirrigation
```
Expected: all vitest tests pass (38/38 from b28); tsc clean.

- [ ] **Step 3: REGEL 8 sister-path check.** Read `distributor.py` end-to-end (esp. `async_run_distributor_cycle`, the sweep, master-note, the `_dist_measure_window` early-stop branches, and the graceful-restart `finally`). Confirm no branch of a shared function carries the bug pattern the b19–b27 fixes addressed, and that the reconstruction didn't drop any b19–b28 fix. Note findings; fix in place only if a real gap is found (re-run Steps 1–2 if so).

---

## Task 3: Stage into ~6–8 logical layer commits

**Files:** none new — re-commits the Task 1 tree in layers.

- [ ] **Step 1: Unstage everything, then commit layer by layer.**
```bash
git reset -q   # unstage; working tree (the reconstructed files) is preserved
```

- [ ] **Step 2: Commit each layer.** Stage the listed paths and commit. Adjust paths to those that actually changed (some may not exist / not differ — `git add` silently skips unchanged). Messages are plain English, no beta noise.

**(1) Data layer:**
```bash
git add custom_components/smart_irrigation/store.py custom_components/smart_irrigation/const.py custom_components/smart_irrigation/entity.py custom_components/smart_irrigation/distributor_entity.py
git commit -m "feat(distributor): data layer — store entries, config flag, entities

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
**(2) Engine:**
```bash
git add custom_components/smart_irrigation/distributor.py custom_components/smart_irrigation/master.py custom_components/smart_irrigation/self_closing.py
git commit -m "feat(distributor): cycle engine + master/pump coordination

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
**(3) Integration:**
```bash
git add custom_components/smart_irrigation/__init__.py custom_components/smart_irrigation/skip_conditions.py custom_components/smart_irrigation/scheduler.py custom_components/smart_irrigation/sensor.py custom_components/smart_irrigation/binary_sensor.py custom_components/smart_irrigation/irrigation.py custom_components/smart_irrigation/button.py custom_components/smart_irrigation/diagnostics.py custom_components/smart_irrigation/localize.py
git commit -m "feat(distributor): integrate into coordinator, scheduler, sensors, skip conditions

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
**(4) Config API:**
```bash
git add custom_components/smart_irrigation/services.py custom_components/smart_irrigation/services.yaml custom_components/smart_irrigation/websockets.py
git commit -m "feat(distributor): services + websocket config API

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
**(5) Frontend:**
```bash
git add custom_components/smart_irrigation/frontend/src/ custom_components/smart_irrigation/frontend/dist/
git commit -m "feat(distributor): panel UI — distributor tab, zone selector, experimental toggle

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
**(6) i18n:**
```bash
git add custom_components/smart_irrigation/frontend/localize/languages/ custom_components/smart_irrigation/translations/
git commit -m "i18n(distributor): panel + config strings (8 languages)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
**(7) Docs:**
```bash
git add docs/configuration-distributors.md docs/configuration-experimental.md docs/configuration.md
git commit -m "docs(distributor): reference page + experimental/index wiring

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
**(8) Tests:**
```bash
git add tests/
git commit -m "test(distributor): backend suites (cycle, dispatch, entities, store, integration)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 3: Confirm the tree is fully committed and still audits clean.**
```bash
git status --short | grep -v uv.lock || echo "(clean)"
git diff --stat upstream/master | tail -3
git log --oneline upstream/master..HEAD
```
Expected: working tree clean (except uv.lock); the cumulative diff vs upstream is distributor-only; ~8 commits listed.

---

## Task 4: PR text + open (REGEL 5 — gated on user approval)

**Files:** none (git/gh).

- [ ] **Step 1: Push the branch to the Eifel-Joe fork.**
```bash
git push -u origin fix/gardena-distributor 2>&1 | tail -3
```

- [ ] **Step 2: Draft the PR title + body** (structure: `## Problem` / `## Fix` / `## Begleitende Änderungen` / `## Abhängigkeiten`). It must state: opt-in/experimental (off by default), flow-volume is rate-only with cumulative dormant, builds on the already-merged self-closing + master + soil-veto work, could not be fully hardware-tested (watch first days). **No IP addresses, no fork branding.** Save to a scratch file.

- [ ] **Step 3: SHOW the full PR title + body to the user and WAIT for approval.** Do NOT run `gh pr create` before the user approves the text (REGEL 5). Apply any requested edits and re-show.

- [ ] **Step 4: After approval, open the PR** Eifel-Joe:fix/gardena-distributor → JustChr:master:
```bash
gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/gardena-distributor --title "<approved title>" --body-file <scratch/pr-body.md>
```
(Per `[[hasi-pr-build-recipe]]`. The `--head Eifel-Joe:…` form opens the cross-fork PR.)

- [ ] **Step 5: Update memory** — `[[hasi-distributor-fix-roadmap]]`: upstream PR opened (link); `[[hasi-fork-strategy]]` if the fork relationship shifts.

---

## Self-review

- **Spec coverage:** clean branch from upstream (T1.1) ✓; distributor delta via checkout (T1.2) ✓; version reset (T1.3) ✓; dormant comment (T1.4) ✓; dist rebuild (T1.5) ✓; diff audit / no-loss gate (T1.6) ✓; full test suites + upstream-code-intact proof (T2) ✓; REGEL 8 (T2.3) ✓; ~6–8 logical commits (T3) ✓; PR gated on approval, no branding/IP, body structure (T4) ✓. Exclusions (superpowers/README/manifest-branding/version/dist-artifacts) handled by T1.2 filters + T1.3 + T1.6 grep.
- **No placeholders:** the file list is generated deterministically (T1.2), version/dormant edits are exact, commit layers list explicit paths. The PR title/body is intentionally drafted at T4.2 and gated for user approval (REGEL 5) — not a plan placeholder.
- **No-loss guarantee:** source branches never modified; correctness proven by the diff audit (T1.6) + upstream tests staying green (T2.1).
