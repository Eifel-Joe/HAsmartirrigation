# Observed-watering run-history entry — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** When observed watering credits a zone, also write one persistent `observed` run-history entry (result = `observed`, the estimated volume, added to the usage total) — for both service and linked-entity zones.

**Architecture:** One `_record_run(...)` call inside the shared `_credit_observed_watering`, plus a new `RUN_RESULT_OBSERVED` token and its frontend chip label/style. No new config; part of the already-opt-in observed-watering feature.

**Tech Stack:** Python (HA coordinator mixin), Lit/TypeScript, pytest + vitest. Spec: `docs/superpowers/specs/2026-07-12-observed-watering-runlog-design.md`.

**Dev branch:** `local/observed-runlog` (checked out, from `production` v2026.07.14).

**Test env (do NOT rebuild):** Python 3.12 env is built. From repo root prefix Bash with `export PATH="/mingw64/bin:/usr/bin:/bin:$PATH"`; run tests as `./.venv/Scripts/python.exe -m pytest <path> -p _local_socket_unblock --tb=short -q`. Ignore `ProactorEventLoop`/`_ssock` teardown noise. Frontend: `custom_components/smart_irrigation/frontend`, `npm run lint`/`npm run build` (PATH needs `/c/Program Files/nodejs`).

---

## File Structure
- `custom_components/smart_irrigation/const.py` — `RUN_RESULT_OBSERVED = "observed"`.
- `custom_components/smart_irrigation/observed_watering.py` — `_record_run(...)` call in `_credit_observed_watering`.
- `custom_components/smart_irrigation/frontend/localize/languages/{en,de,es,fr,it,nl,no,sk}.json` — `panels.zones.history.results.observed`.
- `custom_components/smart_irrigation/frontend/src/views/zones/view-zone-settings.ts` — `.history-observed` chip CSS.
- `tests/test_experimental_features.py` — new run-log/total test.

---

## Task 1: Backend — write the run-log entry

**Files:** `const.py`, `observed_watering.py`; Test: `tests/test_experimental_features.py`.

- [ ] **Step 1: Failing test** — append to `tests/test_experimental_features.py` (after the observed tests, reusing `_observer_coordinator`):
```python
async def test_observed_credit_writes_run_log_and_total(monkeypatch):
    coord = _observer_coordinator(monkeypatch)
    # _record_run lives in irrigation.py and dispatches there; stub that too.
    monkeypatch.setattr(
        "custom_components.smart_irrigation.irrigation.async_dispatcher_send", Mock()
    )
    coord.store.get_zone = Mock(
        return_value={
            const.ZONE_ID: 1,
            const.ZONE_SIZE: 10.0,
            const.ZONE_THROUGHPUT: 10.0,
            const.ZONE_BUCKET: -5.0,
            const.ZONE_MAXIMUM_BUCKET: 50.0,
        }
    )

    await coord._credit_observed_watering(1, 60)  # 1 min @ 10 L/min = 10 L

    # the run-log/usage-total update is a separate async_update_zone call
    log_calls = [
        c
        for c in coord.store.async_update_zone.await_args_list
        if const.ZONE_RUN_LOG in c.args[1]
    ]
    assert log_calls, "observed credit should append a run-log entry"
    changes = log_calls[-1].args[1]
    entry = changes[const.ZONE_RUN_LOG][0]
    assert entry["result"] == const.RUN_RESULT_OBSERVED
    assert entry["volume_l"] == pytest.approx(10.0)
    assert changes[const.ZONE_WATER_USED_TOTAL] == pytest.approx(10.0)
```

- [ ] **Step 2: Run — expect FAIL**
`./.venv/Scripts/python.exe -m pytest tests/test_experimental_features.py::test_observed_credit_writes_run_log_and_total -p _local_socket_unblock --tb=short -q`
Expected: FAIL — `AttributeError: ... RUN_RESULT_OBSERVED` (const missing) and/or no run-log call.

- [ ] **Step 3: const** — in `const.py`, after `RUN_RESULT_SKIPPED = "skipped"` (~line 390):
```python
# External run credited by observed watering (opt-in): the zone's valve ran
# outside Smart Irrigation and its estimated volume was credited to the bucket.
RUN_RESULT_OBSERVED = "observed"
```

- [ ] **Step 4: record the run** — in `observed_watering.py::_credit_observed_watering`, immediately BEFORE the existing bucket `await self.store.async_update_zone(zone_id, {ZONE_BUCKET, ZONE_LAST_IRRIGATION})` (~line 172), insert:
```python
        # Persistent, visible record of the external run (survives later bucket
        # changes, unlike the bucket credit). add_to_total credits the estimated
        # litres into the zone's usage total. Placed before the bucket update so
        # the bucket write stays the method's final async_update_zone call.
        await self._record_run(
            zone_id,
            result=const.RUN_RESULT_OBSERVED,
            volume_l=volume_l,
            actual_s=round(seconds),
            trigger="observed",
            add_to_total=True,
        )
```
`_record_run` is on the coordinator (irrigation.py); `self._record_run` resolves. `const` is already imported. Do NOT change the bucket update or the log line below it.

- [ ] **Step 5: Run — expect PASS + no regressions**
`./.venv/Scripts/python.exe -m pytest tests/test_experimental_features.py -p _local_socket_unblock --tb=short -q`
Expected: all pass — the new test AND the existing observed tests (they assert `async_update_zone.await_args` = the bucket call, which is still the LAST call because `_record_run` runs before it).
Also: `./.venv/Scripts/python.exe -m pytest tests/test_run_history.py -p _local_socket_unblock --tb=short -q` (the `_record_run` helper) → green.

- [ ] **Step 6: Commit**
```
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/observed_watering.py tests/test_experimental_features.py
git commit -m "$(printf 'feat(observed): write a persistent run-history entry for external runs\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Task 2: Frontend — chip label + style (8 languages)

**Files:** `frontend/localize/languages/{en,de,es,fr,it,nl,no,sk}.json`, `frontend/src/views/zones/view-zone-settings.ts`.

- [ ] **Step 1: i18n** — in each `<lang>.json`, add an `observed` key to `panels.zones.history.results` (next to `completed`/`skipped`):
  - en `"Observed"`, de `"Beobachtet"`, es `"Observado"`, fr `"Observé"`, it `"Osservato"`, nl `"Waargenomen"`, no `"Observert"`, sk `"Pozorované"`.
  Keep valid JSON; verify each parses (`node -e "JSON.parse(require('fs').readFileSync('localize/languages/<l>.json','utf8'))"`).

- [ ] **Step 2: chip CSS** — in `view-zone-settings.ts`, after the `.history-skipped { ... }` block (~line 2078-2080), add:
```css
      .history-observed {
        background: #00897b;
      }
```
(Teal — distinct from completed-green / skipped-blue. The chip class `history-observed` is produced automatically by the existing `history-${entry.result}` template, and the label by `panels.zones.history.results.observed`; no other TS change is needed. Verify by reading the render code ~line 1679/1703.)

- [ ] **Step 3: lint** — in `frontend/`: `npm run lint` → clean. Do NOT `npm run build` yet (Task 3).

- [ ] **Step 4: Commit**
```
git add custom_components/smart_irrigation/frontend/src custom_components/smart_irrigation/frontend/localize
git commit -m "$(printf 'feat(frontend): Observed run-history chip label + style (8 langs)\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

> **Frontend test note:** the run-history row has no vitest harness (existing convention); the chip is verified by lint + build + the live test. Backend behavior is covered by Task 1.

---

## Task 3: Regression, review, build, deliver

- [ ] **Step 1: Full backend suite** — `./.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q --tb=line`; compare to baseline (pre-existing 3 failed / 60 errors), expect the new test passing, no new failures.
- [ ] **Step 2: black + ruff** — `uvx black --check custom_components/smart_irrigation/` and `uvx ruff check custom_components/smart_irrigation/` → clean.
- [ ] **Step 3: Frontend build** — in `frontend/`: `npm test` then `npm run build`.
- [ ] **Step 4: REGEL-8 sister-path** — confirm `_credit_observed_watering` is the ONLY credit point (both linked + observed zones flow through it); no other observed path needs the entry. Confirm the existing observed tests still assert the bucket write correctly.
- [ ] **Step 5: Code review** — dispatch `superpowers:code-reviewer` over `production..HEAD`. Focus: run-log entry correct (result/volume/total), existing bucket behavior unchanged, feature-off byte-identical.
- [ ] **Step 6: Commit dist** — `git add -f custom_components/smart_irrigation/frontend/dist` + commit `build(frontend): rebuild dist with observed run-history chip`.
- [ ] **Step 7: Delivery (gated on user)** — per REGEL 5, show release notes; release as v2026.07.15 (merge feature commits onto `production`, exclude `docs/superpowers`, bump version, rebuild dist, release via `gh api .../releases`). Prepare clean upstream branch `feature/observed-watering-runlog` from `upstream/master` (no PR). Archive design docs. Update ToDo.md + memory.

---

## Self-Review
**Spec coverage:** result token (T1) ✓; single-point `_record_run` with add_to_total (T1) ✓; both zone types (shared path) ✓; chip label 8 langs + style (T2) ✓; no new config / off = unchanged ✓.
**Placeholders:** none — all 8 result labels given verbatim.
**Type consistency:** `RUN_RESULT_OBSERVED == "observed"` matches the frontend `history-observed` class + `panels.zones.history.results.observed` key + `trigger="observed"`; `_record_run(zone_id, *, result, volume_l, actual_s, trigger, add_to_total)` matches the existing signature.
