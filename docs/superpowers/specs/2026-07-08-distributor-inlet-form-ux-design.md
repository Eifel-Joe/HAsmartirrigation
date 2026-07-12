# Distributor inlet-entity form UX — Design

Date: 2026-07-08
Branch: `feature/gardena-distributor`
Origin: user review of the distributor config panel (screenshot, 2026-07-08).

## Problem

Two UX issues in the distributor config form's inlet-watch section
(`si-distributor-form.ts` → `_renderInletWatchRows`):

1. **`inlet_entity` help text doesn't say what the field is for.** In service mode the
   inlet valve is optional (watch-only) but the help text (`inlet_entity_help_service`)
   doesn't call out that it is optional or that its purpose is foreign-pulse position
   tracking. The classic-mode help (`inlet_entity_help`) describes the actuated valve but
   not that it is also watched.
2. **The `watch_mode` row ("On a manual inlet pulse") is always shown**, even when no
   `inlet_entity` is set. Without an inlet entity there is nothing to watch, so the
   setting is meaningless — it should only appear once an inlet valve is chosen. (When an
   inlet IS set, the field is required — it already defaults to a value.)

## Decisions (user, 2026-07-08)

- Hide the `watch_mode` row unless `inlet_entity` is set (both watering modes).
- Extend both inlet help texts: service = "optional" + purpose; classic = actuated valve
  + also watched. In all 8 languages.

## Design

### Change 1 — conditional `watch_mode` row (`si-distributor-form.ts`, `_renderInletWatchRows`)

The method renders two `ha-settings-row`s: the `inlet_entity` picker (always) and the
`watch_mode` `<select>` (currently always). Wrap the second row so it renders only when
`d.inlet_entity` is truthy:

```ts
${d.inlet_entity
  ? html`<ha-settings-row> …watch_mode heading/description/select… </ha-settings-row>`
  : ""}
```

Everything inside the row (heading, `watch_mode_help` description, the tri-state
`<select>` with its `@change` emit) is unchanged — only its presence is now gated. The
`inlet_entity` picker row and its `@value-changed` emit are unchanged, so clearing the
inlet entity re-hides the row on the next render.

### Change 2 — extend inlet help texts (i18n, 8 languages, both keys)

`inlet_entity_help_service` (service, watch-only, optional) — English:
> "Optional. The ring valve Home Assistant watches for foreign pulses to keep the outlet
> position in sync (e.g. when the valve is opened manually or by an automation outside a
> HASI run — the setting below controls the reaction). Actuation is via the run/stop
> service; this field is only read, and is NOT the flow/confirm sensor. Leave empty to
> disable inlet watching."

`inlet_entity_help` (classic, actuated valve) — English:
> "The switch or valve entity that opens the water supply into the distributor. It is
> also watched for foreign pulses — the setting below controls the reaction."

German and the other 6 languages get equivalent wording, matching each file's tone.

**Phrase-preservation constraint (existing tests depend on it):** the service help MUST
keep the substrings `only read` and `NOT the flow/confirm sensor`; the classic help MUST
keep `opens the water supply into the distributor`. The changes are additive around those
phrases, so the existing render tests that assert them still pass.

## Testing (vitest, `si-distributor-form.test.ts`)

The test file renders `el.render()` and flattens it to a `text` string, asserting via
`toContain`. The existing watch-mode tests build fixtures WITHOUT an `inlet_entity`, so
Change 1 would hide the `watch_mode` row and break them. Therefore:

- **New test:** a fixture with NO `inlet_entity` → `text` does NOT contain the watch_mode
  select/heading (`"On a manual inlet pulse"`, `"<select"`); a fixture WITH an
  `inlet_entity` set → it DOES.
- **Update existing fixtures:** add `inlet_entity: "switch.x"` to the fixtures of the
  tests that assert the watch_mode select renders / emits / defaults (SERVICE-render,
  CLASSIC-render, three-options, emit-watch_mode, default-ignore) so they still exercise
  the now-gated row. Their assertions are otherwise unchanged.
- The help-text assertions (`only read`, `NOT the flow/confirm sensor`, `opens the water
  supply into the distributor`) stay green because Change 2 preserves those substrings.
- All 8 language JSON files parse.

## Out of scope

- No backend change (the `watch_mode` field, its persistence, and the runtime inlet-watch
  behaviour are unchanged — only the form's visibility + help copy change).
- No change to the tri-state options or the `inlet_entity` picker itself.
