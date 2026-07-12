# Configurable distributor inlet-watch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the binary `watch_inlet` with a tri-state `watch_mode` (count/warn/ignore) and make the inlet-watch reachable in both classic and self-closing modes.

**Architecture:** Backend first (store field + legacy derive, E4 reactions, CRUD passthrough), then frontend (shared inlet-watch form section with a tri-state select + mode-conditional help, i18n in 8 languages). Backend keys the listener + reaction on `watch_mode`; the frontend writes it.

**Tech Stack:** Python 3.12 + HA custom integration (backend); Lit/TypeScript + rollup + vitest (frontend); JSON i18n (8 languages).

**Spec:** `docs/superpowers/specs/2026-07-07-distributor-inlet-watch-modes-design.md`

---

## Test environment

Backend (from `D:\Entwicklung\HASI\HAsmartirrigation`):
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "<selector>" -q
```
Frontend (from `custom_components/smart_irrigation/frontend`): `npm test` (vitest), `npm run build` (lint + rollup).

## File structure

- `custom_components/smart_irrigation/const.py` — new `watch_mode` value constants + a foreign-pulse reason constant.
- `custom_components/smart_irrigation/store.py` — `watch_mode` attr on the distributor entry (~`:365`) + legacy derive in the load path (~`:823-841`).
- `custom_components/smart_irrigation/distributor.py` — `_dist_refresh_inlet_watch` (~`:528`) gate on `watch_mode != ignore`; `_dist_on_inlet_pulse` (~`:496`) branch count/warn.
- `custom_components/smart_irrigation/websockets.py` — ensure `watch_mode` flows through the distributor upsert/read.
- `custom_components/smart_irrigation/frontend/src/types.ts` (`:389`) + `const.ts` — add `watch_mode`.
- `custom_components/smart_irrigation/frontend/src/components/si-distributor-form.ts` — move inlet_entity + watch control to a shared `_renderInletWatchRows`, tri-state select, mode-conditional help.
- `custom_components/smart_irrigation/frontend/localize/languages/{en,de,nl,fr,es,it,no,sk}.json` — new label/help/option strings.
- Tests: `tests/test_distributor_dispatch.py` (E4 reactions), `tests/test_store.py` or `tests/test_distributor.py` (legacy derive), frontend `*.test.ts`.

---

## Task 1: Backend — `watch_mode` constants + store field + legacy derive

**Files:**
- Modify: `custom_components/smart_irrigation/const.py`
- Modify: `custom_components/smart_irrigation/store.py:365` (attr), `:823-841` (load derive)
- Test: `tests/test_distributor.py` (a store-level derive test using the store, or a focused unit)

- [ ] **Step 1: Add constants**

In `const.py`, near the other distributor constants, add:
```python
# Distributor inlet-watch reaction to a foreign inlet pulse (E4).
DISTRIBUTOR_WATCH_MODE_COUNT = "count"    # advance the tracked position
DISTRIBUTOR_WATCH_MODE_WARN = "warn"      # mark uncertain (de-arm + notify)
DISTRIBUTOR_WATCH_MODE_IGNORE = "ignore"  # do not observe
DISTRIBUTOR_REASON_FOREIGN_PULSE = "foreign_inlet_pulse"
```

- [ ] **Step 2: Write the failing store-derive test**

Add to `tests/test_distributor.py` (uses `_host`, `_dist`; `_dist` already carries a `watch_inlet`? — it does NOT, so this test builds dicts directly). Test the pure derive helper (added in Step 4):
```python
def test_watch_mode_derives_from_legacy_watch_inlet():
    c = _host()
    # explicit watch_mode wins
    assert c._dist_watch_mode({"watch_mode": "warn", "watch_inlet": True}) == "warn"
    # legacy watch_inlet True -> count
    assert c._dist_watch_mode({"watch_inlet": True}) == const.DISTRIBUTOR_WATCH_MODE_COUNT
    # legacy False / absent -> ignore
    assert c._dist_watch_mode({"watch_inlet": False}) == const.DISTRIBUTOR_WATCH_MODE_IGNORE
    assert c._dist_watch_mode({}) == const.DISTRIBUTOR_WATCH_MODE_IGNORE
```

- [ ] **Step 3: Run it to verify it fails**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "test_watch_mode_derives_from_legacy_watch_inlet" -q
```
Expected: FAIL — `_dist_watch_mode` not defined.

- [ ] **Step 4: Add the derive helper (single source of truth)**

In `distributor.py`, near the E4 helpers (~`:528`), add:
```python
    @staticmethod
    def _dist_watch_mode(distributor: dict) -> str:
        """The inlet-watch reaction mode, deriving from the legacy `watch_inlet`
        bool when `watch_mode` is absent (True -> count, else -> ignore) so existing
        distributors keep today's behaviour."""
        mode = distributor.get("watch_mode")
        if mode in (
            const.DISTRIBUTOR_WATCH_MODE_COUNT,
            const.DISTRIBUTOR_WATCH_MODE_WARN,
            const.DISTRIBUTOR_WATCH_MODE_IGNORE,
        ):
            return mode
        return (
            const.DISTRIBUTOR_WATCH_MODE_COUNT
            if distributor.get("watch_inlet")
            else const.DISTRIBUTOR_WATCH_MODE_IGNORE
        )
```

- [ ] **Step 5: Add the store attr + load derive**

In `store.py`, after `watch_inlet = attr.ib(...)` (`:365`), add:
```python
    # Inlet-watch reaction to a foreign inlet pulse (E4): count/warn/ignore.
    # Legacy watch_inlet is derived into this in the load path below.
    watch_mode = attr.ib(type=str, default="ignore")
```
In the distributor load/normalization path (`:823-841`), where the entry is rebuilt from `dist`, add alongside `watch_inlet=dist.get("watch_inlet", False)`:
```python
                        watch_mode=dist.get("watch_mode")
                        or ("count" if dist.get("watch_inlet") else "ignore"),
```

- [ ] **Step 6: Run the derive test + store tests**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "test_watch_mode_derives or distributor" -q
```
Expected: PASS.

- [ ] **Step 7: black + commit**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
"$OLD/uvenv312/Scripts/python.exe" -m black custom_components/smart_irrigation/const.py custom_components/smart_irrigation/store.py custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/store.py custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -F - <<'EOF'
feat(distributor): add watch_mode field + legacy watch_inlet derive

E4 tri-state inlet-watch groundwork: watch_mode (count/warn/ignore) on the
distributor entry, deriving from the legacy watch_inlet bool when absent
(True->count, else->ignore) so existing distributors keep today's behaviour.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 2: Backend — E4 reactions (count / warn / ignore)

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py` — `_dist_refresh_inlet_watch` (`:528-541`), `_dist_on_inlet_pulse` (`:496-509`)
- Test: `tests/test_distributor_dispatch.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_distributor_dispatch.py`:
```python
async def test_inlet_watch_registers_listener_unless_ignore(monkeypatch):
    # watch_mode != ignore + inlet_entity set -> a listener is registered (both modes).
    c = _host()
    calls = []
    monkeypatch.setattr(
        "custom_components.smart_irrigation.distributor.async_track_state_change_event",
        lambda hass, entities, handler: calls.append(entities) or (lambda: None),
    )
    # classic count
    c._dist_refresh_inlet_watch(
        _dist(id=0, inlet_entity="switch.inlet", watch_mode="count")
    )
    # self-closing (service) warn: still watches, mode-agnostic
    c._dist_refresh_inlet_watch(
        _dist(
            id=1,
            watering_mode=const.WATERING_MODE_SERVICE,
            inlet_entity="switch.ring",
            watch_mode="warn",
        )
    )
    # ignore -> no listener
    c._dist_refresh_inlet_watch(
        _dist(id=2, inlet_entity="switch.inlet", watch_mode="ignore")
    )
    assert calls == [["switch.inlet"], ["switch.ring"]]


async def test_inlet_pulse_count_advances_position():
    c = _host()
    c.store.get_distributor = Mock(
        return_value=_dist(id=0, current_outlet=1, watch_mode="count")
    )
    c._dist_members = AsyncMock(return_value=[{"id": 1}, {"id": 2}, {"id": 3}])
    c._dist_store_update = AsyncMock()
    c._dist_mark_uncertain = AsyncMock()
    await c._dist_on_inlet_pulse(0)
    c._dist_store_update.assert_awaited_once_with(0, {"current_outlet": 2})
    c._dist_mark_uncertain.assert_not_awaited()


async def test_inlet_pulse_warn_marks_uncertain_without_advancing():
    c = _host()
    d = _dist(id=0, current_outlet=1, watch_mode="warn")
    c.store.get_distributor = Mock(return_value=d)
    c._dist_members = AsyncMock(return_value=[{"id": 1}, {"id": 2}])
    c._dist_store_update = AsyncMock()
    c._dist_mark_uncertain = AsyncMock()
    await c._dist_on_inlet_pulse(0)
    c._dist_mark_uncertain.assert_awaited_once()
    # reason is the foreign-pulse code
    assert (
        c._dist_mark_uncertain.await_args.kwargs.get("reason")
        == const.DISTRIBUTOR_REASON_FOREIGN_PULSE
    )
    c._dist_store_update.assert_not_awaited()  # position NOT advanced


async def test_inlet_pulse_ignored_during_active_cycle():
    c = _host()
    c.store.get_distributor = Mock(
        return_value=_dist(id=0, watch_mode="warn", active_cycle={"outlet": 1})
    )
    c._dist_store_update = AsyncMock()
    c._dist_mark_uncertain = AsyncMock()
    await c._dist_on_inlet_pulse(0)
    c._dist_store_update.assert_not_awaited()
    c._dist_mark_uncertain.assert_not_awaited()
```

- [ ] **Step 2: Run to verify failure**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "test_inlet_watch_registers_listener_unless_ignore or test_inlet_pulse_count_advances_position or test_inlet_pulse_warn_marks_uncertain_without_advancing or test_inlet_pulse_ignored_during_active_cycle" -q
```
Expected: FAIL — the count/warn branch + the `watch_mode != ignore` gate don't exist yet (`test_inlet_pulse_warn...` gets a position advance instead of an uncertain mark; the listener test's ignore-case may still register).

- [ ] **Step 3: Implement `_dist_refresh_inlet_watch` gate**

Replace the tail of `_dist_refresh_inlet_watch` (`:537-541`):
```python
        inlet = distributor.get("inlet_entity")
        if distributor.get("watch_inlet") and isinstance(inlet, str) and inlet:
            watchers[did] = async_track_state_change_event(
                self.hass, [inlet], self._dist_inlet_state_handler(did)
            )
```
with:
```python
        inlet = distributor.get("inlet_entity")
        # E4 (2026-07-07): watch whenever a mode other than ignore is set — mode-
        # agnostic, so self-closing distributors (which name their ring valve in
        # inlet_entity but actuate via run/stop services) can watch it too.
        if (
            self._dist_watch_mode(distributor) != const.DISTRIBUTOR_WATCH_MODE_IGNORE
            and isinstance(inlet, str)
            and inlet
        ):
            watchers[did] = async_track_state_change_event(
                self.hass, [inlet], self._dist_inlet_state_handler(did)
            )
```

- [ ] **Step 4: Implement `_dist_on_inlet_pulse` branch**

Replace `_dist_on_inlet_pulse` body (`:501-509`) with:
```python
        dist = self.store.get_distributor(distributor_id)
        if dist is None or dist.get("active_cycle"):
            return
        mode = self._dist_watch_mode(dist)
        if mode == const.DISTRIBUTOR_WATCH_MODE_WARN:
            # A foreign pulse advanced the blind ring but the user asked to be warned
            # rather than auto-counted: de-arm + notify so they re-sync before the
            # next (now wrong-outlet) cycle.
            await self._dist_mark_uncertain(
                dist, reason=const.DISTRIBUTOR_REASON_FOREIGN_PULSE
            )
            return
        # count: keep the tracked position in step with the physical advance.
        members = await self._dist_members(distributor_id)
        n = len(members)
        if n == 0:
            return
        cur = int(dist.get("current_outlet") or 1)
        await self._dist_store_update(distributor_id, {"current_outlet": (cur % n) + 1})
```
(The `ignore` mode never reaches here — no listener is registered.)

- [ ] **Step 5: Run the 4 tests to verify pass + no E4 regression**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock tests/test_distributor.py tests/test_distributor_dispatch.py -q
```
Expected: PASS (incl. any existing inlet-watch tests, updated below if they assert the old `watch_inlet` gate).

- [ ] **Step 6: Update any existing E4 tests that assert the old `watch_inlet` gate**

Grep `tests/test_distributor_dispatch.py` for existing `_dist_refresh_inlet_watch` / `_dist_on_inlet_pulse` tests; where they build a distributor with `watch_inlet=True`, the legacy derive keeps them green (True->count) — leave them unless they assert "no listener when watch_inlet False", which now needs `watch_mode="ignore"` explicit. Run the suite (Step 5) and fix only the ones that fail, mirroring the new constants.

- [ ] **Step 7: black + commit**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
"$OLD/uvenv312/Scripts/python.exe" -m black custom_components/smart_irrigation/distributor.py tests/test_distributor_dispatch.py
git add custom_components/smart_irrigation/distributor.py tests/test_distributor_dispatch.py
git commit -F - <<'EOF'
feat(distributor): tri-state inlet-watch reactions (count/warn/ignore)

_dist_refresh_inlet_watch now registers the listener whenever watch_mode != ignore
(mode-agnostic, so self-closing distributors can watch their ring valve too), and
_dist_on_inlet_pulse branches: count advances the position (as before); warn marks
the distributor uncertain (de-arm + notify) instead of silently desyncing.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 3: Backend — CRUD/websocket passthrough for `watch_mode`

**Files:**
- Modify: `custom_components/smart_irrigation/websockets.py` (distributor upsert schema, if it allowlists keys)
- Test: `tests/test_distributor.py` (upsert round-trips watch_mode)

- [ ] **Step 1: Inspect the upsert path**

Read `websockets.py` around the distributor upsert and `async_upsert_distributor` (`distributor.py:956`). The store CRUD drops unknown keys via the attrs allowlist; since `watch_mode` is now an attr (Task 1), a POST carrying `watch_mode` persists. If the websocket handler has an explicit field schema (voluptuous), add `watch_mode` to it.

- [ ] **Step 2: Write the failing round-trip test**

Add to `tests/test_distributor.py`:
```python
async def test_upsert_persists_watch_mode():
    c = _host()
    c.store.async_update_distributor = AsyncMock(return_value={"id": 0})
    c.store.get_distributor = Mock(return_value={"id": 0})
    c._dist_refresh_inlet_watch = Mock()
    await c.async_upsert_distributor({"id": 0, "watch_mode": "warn"})
    changes = c.store.async_update_distributor.await_args.args[1]
    assert changes.get("watch_mode") == "warn"
```

- [ ] **Step 3: Run to verify (fails only if a schema strips it)**

```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "test_upsert_persists_watch_mode" -q
```
Expected: PASS if the attrs allowlist already lets it through; FAIL if a websocket voluptuous schema strips unknown keys — in which case add `vol.Optional("watch_mode"): str` to that schema and re-run.

- [ ] **Step 4: black + commit (if any change)**

```bash
git add -A custom_components/smart_irrigation/websockets.py tests/test_distributor.py
git commit -F - <<'EOF'
feat(distributor): pass watch_mode through the distributor upsert

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 4: Frontend — shared inlet-watch section + tri-state select

**Files:**
- Modify: `frontend/src/types.ts` (`:389`), `frontend/src/const.ts`
- Modify: `frontend/src/components/si-distributor-form.ts` (`render()` `:120-127`, `_renderClassicRow` `:157-205`)
- Test: `frontend/src/components/*.test.ts` (or the form's existing test)

- [ ] **Step 1: Types + const**

In `types.ts`, next to `watch_inlet?: boolean;` (`:389`) add:
```ts
  watch_mode?: "count" | "warn" | "ignore";
```
In `const.ts`, add the option constant (mirror how other selects are defined there):
```ts
export const DISTRIBUTOR_WATCH_MODES = ["count", "warn", "ignore"] as const;
```

- [ ] **Step 2: Write the failing vitest**

In the form's test file (create `si-distributor-form.test.ts` if none, mirroring an existing component test), assert:
- rendering a `watering_mode: "service"` distributor includes the `inlet_entity` field and the `watch_mode` select (was absent before);
- the `watch_mode` select has 3 options;
- changing it fires the config payload with `watch_mode`.
(Use the existing component-test harness/fixtures; follow an existing `*.test.ts` for mounting.)

Run: `cd custom_components/smart_irrigation/frontend && npm test -- si-distributor-form` → FAIL.

- [ ] **Step 3: Add a shared `_renderInletWatchRows`**

In `si-distributor-form.ts`:
- Remove the `inlet_entity` block (`:157-176`) and the `watch_inlet` block (`:184-203`) from `_renderClassicRow`.
- Add `private _renderInletWatchRows(lang: string): TemplateResult` containing: the `inlet_entity` entity picker (unchanged binding `this.distributor.inlet_entity`), with help text switching on `this.distributor.watering_mode === "service"` between `inlet_entity_help` and `inlet_entity_help_service`; and a `watch_mode` `<select>` (3 options, labels from `panels.distributors.labels.watch_mode_{count,warn,ignore}`, value `this.distributor.watch_mode ?? "ignore"`, writing `watch_mode`), with help `watch_mode_help`.
- In `render()` (`:120-127`), call `${this._renderInletWatchRows(lang)}` for BOTH branches (e.g. after the mode row, before `_renderSensorRows`).
- The `_configPayload` write path that currently sets `watch_inlet` (see the `:184` comment) now sets `watch_mode`; stop writing `watch_inlet`.

- [ ] **Step 4: Run vitest + build**

```bash
cd custom_components/smart_irrigation/frontend && npm test -- si-distributor-form && npm run build
```
Expected: vitest PASS; build (lint + rollup) succeeds.

- [ ] **Step 5: Commit (dist rebuilt in the release task, not here)**

```bash
git add custom_components/smart_irrigation/frontend/src
git commit -F - <<'EOF'
feat(distributor-ui): tri-state watch_mode select in a shared inlet-watch section

inlet_entity + watch_mode now render in both classic and self-closing modes, with
mode-conditional help (self-closing: the field is watch-only). Replaces the
watch_inlet toggle with a count/warn/ignore select.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 5: Frontend — i18n in 8 languages

**Files:**
- Modify: `frontend/localize/languages/{en,de,nl,fr,es,it,no,sk}.json`

- [ ] **Step 1: Add the strings (English canonical)**

Under `panels.distributors.labels` in `en.json` (next to `inlet_entity` `:705`), add:
```json
        "inlet_entity_help_service": "The ring valve Home Assistant watches for foreign pulses. Actuation is via the run/stop service — this field is only read, and is NOT the flow/confirm sensor.",
        "watch_mode": "On a manual inlet pulse",
        "watch_mode_help": "How to react when the inlet valve is opened outside a Home Assistant run (only pulses Home Assistant can see).",
        "watch_mode_count": "Count it (advance the position)",
        "watch_mode_warn": "Warn (mark position uncertain)",
        "watch_mode_ignore": "Ignore",
```
Keep the old `watch_inlet`/`watch_inlet_help` keys (harmless; can be removed later).

- [ ] **Step 2: Translate into the other 7 languages**

Add the same 5 keys to `de, nl, fr, es, it, no, sk` with proper translations, matching the tone of each file's existing distributor strings (`hasi-i18n-all-languages`). German example:
```json
        "inlet_entity_help_service": "Das Ring-Ventil, das Home Assistant auf Fremd-Pulse beobachtet. Geschaltet wird über den Run/Stop-Service — dieses Feld wird nur gelesen und ist NICHT der Fluss-/Bestätigungssensor.",
        "watch_mode": "Bei manuellem Einlass-Puls",
        "watch_mode_help": "Reaktion, wenn das Einlass-Ventil außerhalb eines Home-Assistant-Laufs geöffnet wird (nur für Home Assistant sichtbare Pulse).",
        "watch_mode_count": "Mitzählen (Position weiterschalten)",
        "watch_mode_warn": "Warnen (Position auf unsicher setzen)",
        "watch_mode_ignore": "Ignorieren",
```

- [ ] **Step 3: Build + verify all languages parse**

```bash
cd custom_components/smart_irrigation/frontend && npm run build
node -e "for (const l of ['en','de','nl','fr','es','it','no','sk']) JSON.parse(require('fs').readFileSync('localize/languages/'+l+'.json'))" && echo "all langs parse"
```
Expected: build succeeds; all 8 JSON files parse.

- [ ] **Step 4: Commit**

```bash
git add custom_components/smart_irrigation/frontend/localize/languages
git commit -F - <<'EOF'
i18n(distributor): watch_mode + self-closing inlet-watch strings (8 languages)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 6: Full regression + release (b21)

- [ ] **Step 1: Full backend suite vs baseline (no new failures)**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -q 2>&1 | tail -3
"$OLD/uvenv312/Scripts/python.exe" -m black --check custom_components/smart_irrigation/
```
- [ ] **Step 2: Code-review checkpoint** (REGEL 1) — dispatch `superpowers:code-reviewer` on the backend + frontend diff vs the spec before release.
- [ ] **Step 3: Version bump b20 -> b21** (all three: const.py, manifest.json, package.json) + `npm run build` (bakes b21) — same recipe as b20.
- [ ] **Step 4: Release** — show release notes for approval (REGEL 5), then `git push origin feature/gardena-distributor` + `gh release create v2026.07.11b21 --repo Eifel-Joe/HAsmartirrigation --prerelease --target feature/gardena-distributor`.
- [ ] **Step 5: Update memories** — `hasi-distributor-selfclosing-inlet-watch-gap` + `hasi-distributor-position-ideas` + `hasi-distributor-fix-roadmap` (Phase 2 b+c done).

---

## Self-review

- **Spec coverage:** data model (watch_mode + legacy derive + default ignore) → Task 1; backend reactions (count/warn/ignore + listener gate + mode-agnostic self-closing + in-cycle guard) → Task 2; CRUD passthrough → Task 3; frontend (inlet_entity in both modes + tri-state select + mode-conditional hint) → Task 4; i18n 8 languages → Task 5; regression + release → Task 6. All spec sections mapped.
- **Placeholder scan:** backend steps carry full test + impl code. Frontend Tasks 4-5 specify exact files, fields, i18n keys, and English/German strings; the remaining 6 languages and the exact Lit template follow the existing `watch_inlet`/`inlet_entity` code located at the cited anchors (`si-distributor-form.ts:157-205`, `en.json:705-708`) — filled during execution against those patterns.
- **Type/name consistency:** `watch_mode` values `count`/`warn`/`ignore` and `DISTRIBUTOR_WATCH_MODE_*` / `DISTRIBUTOR_REASON_FOREIGN_PULSE` / `_dist_watch_mode` used consistently across store, distributor, tests, types.ts, const.ts, and i18n keys `panels.distributors.labels.watch_mode*`.
