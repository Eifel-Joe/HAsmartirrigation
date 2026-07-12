# Distributor notification i18n Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Localize the distributor halt notification (message + reason phrase) into all 8 languages, reusing the existing backend `localize()` mechanism.

**Architecture:** `_dist_mark_uncertain` builds its notification via `await localize(key, hass.config.language)` (as `calculation.py` does) instead of an English f-string, with new `panels.distributors.notify.*` keys in the 8 language JSONs. `.replace()` fills `{name}`/`{reason}` (no `str.format`, so a translation can't inject a field).

**Tech Stack:** Python 3.12 (backend `localize()` reads `localize/languages/*.json` via aiofiles); JSON i18n (8 languages).

**Spec:** `docs/superpowers/specs/2026-07-07-distributor-notify-i18n-design.md`

---

## Test env
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "<selector>" -q
```
black-format Python before committing. Commit via `git commit -F - <<'EOF' ... EOF`.

## File structure
- `custom_components/smart_irrigation/distributor.py` — add `from .localize import localize`; rewrite the message build in `_dist_mark_uncertain` (~`:137-161`).
- `custom_components/smart_irrigation/frontend/localize/languages/{en,de,nl,fr,es,it,no,sk}.json` — new `panels.distributors.notify` node.
- Tests: `tests/test_distributor.py`.

---

## Task 1: Localize the halt notification (backend)

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py` (imports + `_dist_mark_uncertain`)
- Test: `tests/test_distributor.py`

- [ ] **Step 1: Write the failing unit test** (mock `localize` — no file I/O)

Add to `tests/test_distributor.py` (imports `AsyncMock`, `Mock`, `_host`, `_dist`, `const`):
```python
async def test_mark_uncertain_localizes_notification(monkeypatch):
    # The halt notification is built via localize() keyed on hass.config.language,
    # with the reason phrase resolved and {name}/{reason} filled by replace().
    c = _host()
    c.hass.config.language = "de"
    seen = []

    async def _fake_localize(key, lang):
        seen.append((key, lang))
        if key.endswith(".reason.valve_did_not_open"):
            return "Ventil hat nicht geöffnet"
        if key.endswith(".halted"):
            return "Verteiler '{name}' angehalten ({reason})."
        return key

    monkeypatch.setattr(
        "custom_components.smart_irrigation.distributor.localize", _fake_localize
    )
    captured = {}
    c._dist_notify = AsyncMock(side_effect=lambda d, m: captured.update(msg=m))
    await c._dist_mark_uncertain(
        _dist(name="Garten"), reason=const.PROBLEM_VALVE_DID_NOT_OPEN
    )
    assert captured["msg"] == "Verteiler 'Garten' angehalten (Ventil hat nicht geöffnet)."
    # localized with the HA language, both keys fetched
    assert ("panels.distributors.notify.halted", "de") in seen
    assert (
        f"panels.distributors.notify.reason.{const.PROBLEM_VALVE_DID_NOT_OPEN}",
        "de",
    ) in seen
```

- [ ] **Step 2: Run it to verify it fails**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "test_mark_uncertain_localizes_notification" -q
```
Expected: FAIL — `distributor` has no attribute `localize` (monkeypatch target missing) / the message is still the English f-string.

- [ ] **Step 3: Implement — import + rewrite the message build**

In `distributor.py`, add to the imports (after `from . import const`):
```python
from .localize import localize
```
In `_dist_mark_uncertain`, replace the final `await self._dist_notify(distributor, f"Distributor '{...}' halted ({reason}). " "Re-sync and re-confirm required.")` call with:
```python
        lang = self.hass.config.language
        reason_text = await localize(
            f"panels.distributors.notify.reason.{reason}", lang
        )
        template = await localize("panels.distributors.notify.halted", lang)
        message = template.replace("{name}", str(distributor.get("name"))).replace(
            "{reason}", reason_text
        )
        await self._dist_notify(distributor, message)
```
(Leave the `_dist_store_update` de-arm and the `async_fire` halted-event block above it unchanged — the event still carries the raw `reason` code.)

- [ ] **Step 4: Run the new test + the existing mark_uncertain test**

The existing `test_mark_uncertain_de_arms_persists_fires_and_notifies` asserts the persist, the event `reason`, and that notify was awaited — NOT the message text. But it uses a bare Mock `hass.config.language`, which the new `await localize(...)` would pass to the real localize (real file I/O + graceful fallback). Update that test to mock localize too (add the same `monkeypatch.setattr(...distributor.localize..., _fake)` returning any string, e.g. a lambda `async def _f(k, l): return k`), so it stays a pure unit test. Then:
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock tests/test_distributor.py tests/test_distributor_cycle.py tests/test_distributor_dispatch.py -q
```
Expected: PASS, no regressions.

- [ ] **Step 5: black + commit**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
"$OLD/uvenv312/Scripts/python.exe" -m black custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git add custom_components/smart_irrigation/distributor.py tests/test_distributor.py
git commit -F - <<'EOF'
feat(distributor): localize the halt notification via the existing localize()

_dist_mark_uncertain now builds its persistent-notification message with
await localize(key, hass.config.language) (as calculation.py does) instead of an
English f-string, resolving a localized reason phrase and filling {name}/{reason}
by replace(). Keys land in the language JSONs in the next task; title unchanged.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 2: The 8-language strings + real-localize integration test

**Files:**
- Modify: `frontend/localize/languages/{en,de,nl,fr,es,it,no,sk}.json`
- Test: `tests/test_distributor.py`

- [ ] **Step 1: Add the keys (English + German canonical)**

Under `panels.distributors` in `en.json`, add a `notify` node (place next to the existing `distributors` sub-keys; match the file's 2-space nesting):
```json
        "notify": {
          "halted": "Distributor '{name}' halted ({reason}). Re-sync and re-confirm required.",
          "reason": {
            "valve_did_not_open": "valve did not open",
            "restart_mid_advance": "restarted mid-advance",
            "foreign_inlet_pulse": "manual inlet pulse"
          }
        },
```
`de.json`:
```json
        "notify": {
          "halted": "Verteiler '{name}' angehalten ({reason}). Neu synchronisieren und erneut bestätigen erforderlich.",
          "reason": {
            "valve_did_not_open": "Ventil hat nicht geöffnet",
            "restart_mid_advance": "Neustart während der Weiterschaltung",
            "foreign_inlet_pulse": "manueller Einlass-Puls"
          }
        },
```
Add the same `notify` node (4 strings) to nl, fr, es, it, no, sk with faithful translations matching each file's tone. Ensure the JSON stays valid (trailing commas correct for the insertion point).

- [ ] **Step 2: Write the real-localize integration test** (no mock — reads the shipped JSONs)

Add to `tests/test_distributor.py`:
```python
async def test_mark_uncertain_notification_real_localize_de_and_en():
    # End-to-end: the real localize() reads the shipped JSONs; DE yields the German
    # template + reason phrase, EN the English, keyed on hass.config.language.
    for lang, expected in (
        ("de", "Verteiler 'Garten' angehalten (Ventil hat nicht geöffnet). "
               "Neu synchronisieren und erneut bestätigen erforderlich."),
        ("en", "Distributor 'Garten' halted (valve did not open). "
               "Re-sync and re-confirm required."),
    ):
        c = _host()
        c.hass.config.language = lang
        captured = {}
        c._dist_notify = AsyncMock(side_effect=lambda d, m: captured.update(msg=m))
        await c._dist_mark_uncertain(
            _dist(name="Garten"), reason=const.PROBLEM_VALVE_DID_NOT_OPEN
        )
        assert captured["msg"] == expected
```

- [ ] **Step 3: Run it (+ verify all 8 langs parse)**
```bash
OLD=/c/Users/Nutzer/AppData/Local/Temp/claude/D--Entwicklung-HASI/340a4602-8887-4fd6-a74f-2f5a37f332fe/scratchpad
PYTHONPATH="$OLD" "$OLD/uvenv312/Scripts/python.exe" -m pytest tests/ -p _local_socket_unblock -k "test_mark_uncertain_notification_real_localize" -q
cd custom_components/smart_irrigation/frontend && node -e "for (const l of ['en','de','nl','fr','es','it','no','sk']) JSON.parse(require('fs').readFileSync('localize/languages/'+l+'.json'))" && echo "all langs parse" && cd -
```
Expected: PASS; all 8 JSONs parse. (If DE fails on the exact string, reconcile the JSON text with the test's expected string — they must match byte-for-byte.)

- [ ] **Step 4: Commit**
```bash
git add custom_components/smart_irrigation/frontend/localize/languages tests/test_distributor.py
git commit -F - <<'EOF'
i18n(distributor): halt-notification strings (8 languages)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Self-review

- **Spec coverage:** localize the halt message via existing `localize()`/`hass.config.language` → Task 1; reason-phrase mapping for the 3 codes → Task 1 (build) + Task 2 (strings); `.replace()` not `.format` → Task 1 Step 3; title unchanged (`_dist_notify` untouched) → Task 1; 8-language strings → Task 2; tests (localized per language, fallback via the real-localize test, existing tests green) → Tasks 1-2. All spec sections mapped.
- **Placeholders:** none — full test + impl code, exact keys and commands.
- **Type/name consistency:** `panels.distributors.notify.halted` + `panels.distributors.notify.reason.<code>` used identically in the impl, the mock test, the real test, and the JSON keys; `const.PROBLEM_VALVE_DID_NOT_OPEN` == `"valve_did_not_open"` matches the JSON key; `localize` import path `custom_components.smart_irrigation.distributor.localize` consistent between monkeypatch and impl.
