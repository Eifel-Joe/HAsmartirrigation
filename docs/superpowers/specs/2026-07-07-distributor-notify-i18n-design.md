# Distributor notification i18n — Design

Date: 2026-07-07
Branch: `feature/gardena-distributor`
Phase: Fix-Roadmap Phase 3 (3.3) (see `hasi-distributor-fix-roadmap`, `hasi-pending-notify-i18n`)

## Problem

The distributor's user-facing **notifications** (the persistent-notification bell +
an optional `notify_target`) are English-only. Confirmed live at Test 1.1 (a no-flow
halt showed an English bell message). They should be localized into all 8 supported
languages (`de, en, es, fr, it, nl, no, sk`).

The only distributor notification path:
- `_dist_mark_uncertain(distributor, reason)` (`distributor.py:137`) builds
  `f"Distributor '{name}' halted ({reason}). Re-sync and re-confirm required."`
  — English, and it embeds the **raw reason code** (e.g. `valve_did_not_open`) — then
  calls `_dist_notify(distributor, message)` (`distributor.py:112`), which posts the
  persistent notification (title `"Smart Irrigation"`) and forwards to `notify_target`.
- Callers pass three reason codes: `PROBLEM_VALVE_DID_NOT_OPEN` (`valve_did_not_open`,
  confirm-fail `:512`), `DISTRIBUTOR_REASON_RESTART_MID_ADVANCE` (`restart_mid_advance`,
  `:912`), `DISTRIBUTOR_REASON_FOREIGN_PULSE` (`foreign_inlet_pulse`, `:1021`).

## Existing mechanism (reused — no new machinery)

The backend already localizes strings: `calculation.py` uses
`from .localize import localize` and `await localize(key, self.hass.config.language)`.
`localize.py` provides `async def localize(string: str, language: str) -> str` which
loads the key from `localize/languages/<lang>.json`, **falls back to English**, then to
the key itself if not found. Language source = `self.hass.config.language` (exactly as
`calculation.py`). This design reuses that verbatim; it adds no new i18n mechanism.

## Design

Localize the halt notification in `_dist_mark_uncertain`:

1. Resolve the reason phrase:
   `reason_text = await localize(f"panels.distributors.notify.reason.{reason}", lang)`.
   An unmapped reason falls back (via `localize`) to the raw code — graceful.
2. Fetch the message template:
   `template = await localize("panels.distributors.notify.halted", lang)`.
3. Fill placeholders WITHOUT `str.format` (a translation must never be able to inject a
   format field): `message = template.replace("{name}", name).replace("{reason}", reason_text)`.
4. Pass `message` to `_dist_notify` (unchanged).

`lang = self.hass.config.language`. The notification **title** stays `"Smart Irrigation"`
(the integration/brand name — not translated, matching HA convention).

`_dist_mark_uncertain` and `_dist_notify` are already `async`, so the added `await
localize(...)` calls fit without signature changes. `distributor.py` adds
`from .localize import localize` (mirroring `calculation.py`).

### i18n keys (added under `panels.distributors.notify` in all 8 language files)

English (canonical):
- `halted`: `"Distributor '{name}' halted ({reason}). Re-sync and re-confirm required."`
- `reason.valve_did_not_open`: `"valve did not open"`
- `reason.restart_mid_advance`: `"restarted mid-advance"`
- `reason.foreign_inlet_pulse`: `"manual inlet pulse"`

German:
- `halted`: `"Verteiler '{name}' angehalten ({reason}). Neu synchronisieren und erneut bestätigen erforderlich."`
- `reason.valve_did_not_open`: `"Ventil hat nicht geöffnet"`
- `reason.restart_mid_advance`: `"Neustart während der Weiterschaltung"`
- `reason.foreign_inlet_pulse`: `"manueller Einlass-Puls"`

The other 6 languages (nl, fr, es, it, no, sk) get faithful translations matching each
file's tone.

## Testing

- `_dist_mark_uncertain` builds the message via `localize` keyed on
  `hass.config.language`; assert the DE language yields the German template + reason
  phrase, EN yields English.
- An unknown/unsupported `hass.config.language` falls back to English (the `localize`
  contract) — assert.
- The reason phrase maps each of the three codes; an unmapped code falls back to the
  raw code (no crash).
- The persistent-notification title is still `"Smart Irrigation"`.
- Regression: the existing `_dist_notify` behaviour (persistent notification +
  optional `notify_target`) is unchanged; existing distributor tests stay green
  (the halt-message assertion in `test_mark_uncertain_*` updates to the localized
  string — it currently asserts the English inline text).

Unit tests mock `localize` where convenient OR set `hass.config.language` and rely on
the real `localize` reading the JSONs (mirror how `calculation.py` tests do it).

## Out of scope

Zone/other notifications (only the distributor halt path is in scope), the
`notify_target` forwarding mechanism (unchanged), and any change to `localize.py`
itself or the language set.
