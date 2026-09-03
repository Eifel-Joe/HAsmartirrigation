# Dedicated "History" tab for the irrigation run log

- **Date:** 2026-09-03
- **Status:** Design approved, spec under review
- **Area:** Frontend panel (`custom_components/smart_irrigation/frontend`)

## Problem

Each zone's run history (the "Bewässerungsverlauf" — recent runs plus cumulative
water usage) is rendered **inside the zone's settings card**, below the settings
fields (`view-zone-settings.ts`, `_renderRunHistory`). That placement mixes two
concerns: configuring a zone and reviewing what it has done. The settings card is
long, and the history is buried under it, so it reads as an afterthought rather
than a first-class view.

## Goal

Give the run history its own top-level tab, **"Verlauf"**, and move the per-zone
history out of the settings card entirely, so:

- Zone settings become settings only.
- The history is a deliberate destination with room to breathe.

## Non-goals (YAGNI — explicitly out of scope)

- Aggregated cross-zone timeline (the tab is per-zone, selected by the user).
- Filtering / search over the log.
- Deep-linking to a specific zone's history via the URL.
- Any change to the run-log data model, the backend, or how entries are recorded.
- Re-keying the existing `panels.zones.history.*` translation strings.

These may be revisited later; none are needed for the first version.

## Current state (what exists today)

- **Tabs** are driven by the `EMenuItems` enum in `smart-irrigation.ts`
  (`Zones = "zones"`, `Setup = "setup"`). The tab bar maps `Object.values(EMenuItems)`
  to `ha-tab-group-tab` (with a `.custom-tabs` fallback), labelling each with
  `localize("panels.<page>.title")`. `getView(path)` switches on `path.page` to
  render `smart-irrigation-view-zones` / `smart-irrigation-view-setup`.
- **Deep links** are honored: `firstUpdated` only redirects to Zones when the URL
  page is not a known `EMenuItems` value, so a new enum value is automatically a
  valid, refresh-safe page.
- **History rendering** lives in `view-zone-settings.ts`:
  - `_renderRunHistory(zone)` (called at ~line 1815) — an `ha-expansion-panel`
    with cumulative usage (`zone.water_used_total`, via `formatVolume` gated on
    `config.units === CONF_METRIC`) and, when `zone.run_log` is non-empty, a
    `.history-table` (columns: when / result / volume / detail); otherwise the
    `panels.zones.history.empty` note.
  - `_renderRunLogRow(entry, metric)` — one table row, with a result chip
    (`history-chip history-<result>`) and localized result label
    (`panels.zones.history.results.<result>`).
  - Both depend only on `this.hass`, `this.config?.units`, and the passed `zone`.
  - Strings live under `panels.zones.history.*` (title, total_used, empty, when,
    result, volume, detail, results.*).

## Design

### Chosen approach

Approach A: extract the history rendering into a **standalone presentational
component**, reuse it from a new **history view**, and remove it from the zone
settings. This matches the codebase's existing `si-*` component pattern and keeps
each unit single-purpose and independently testable.

### New tab

- Add `EMenuItems.History = "history"`.
- **Tab order:** `Zonen | Verlauf | Einrichtung` — declare `History` between
  `Zones` and `Setup` in the enum (the tab bar renders enum order).
- Label via a new i18n key `panels.history.title`.

### New component: `si-zone-history`

`src/components/si-zone-history.ts`, custom element `si-zone-history`.

- **Props:** `hass: HomeAssistant`, `zone: SmartIrrigationZone`, `config`. The
  metric flag is derived internally as `config?.units === CONF_METRIC`, exactly as
  `_renderRunHistory` does today.
- **Renders** exactly what `_renderRunHistory` + `_renderRunLogRow` render today —
  cumulative-usage row, the runs table (or the empty note), and the result chips —
  moved verbatim so the visual output is unchanged. The wrapping
  `ha-expansion-panel` is dropped: inside its own tab the history no longer needs
  to be collapsible (it is not competing with settings for space). The table and
  usage row render directly.
- **Reuses** the existing `panels.zones.history.*` strings — no re-keying.
- Pure presentation: no data fetching, no side effects.

### New view: `view-history.ts`

`src/views/history/view-history.ts`, custom element `smart-irrigation-view-history`,
following the structure of the other view components (`hass`, `narrow`, `path`).

- Obtains the zone list the same way `view-zones` / `view-zone-settings` do
  (from `hass` state / the store the panel already uses).
- Renders a **zone selector** — a dropdown (`ha-select`/native `<select>`,
  matching the controls used elsewhere in the panel) labelled
  `panels.history.select_zone`, defaulting to the **first zone**. Selection is
  held in local component state (no URL deep-link — see non-goals).
- Below it, `<si-zone-history .hass .zone=${selectedZone}>` for the selected zone.
- **Empty states:**
  - No zones configured → a short localized line using a new
    `panels.history.no_zones` string.
  - Selected zone with an empty `run_log` → the existing
    `panels.zones.history.empty` note (rendered by `si-zone-history`).

### Content switch

In `smart-irrigation.ts` `getView`, add `case "history":` returning
`<smart-irrigation-view-history .hass .narrow .path>`.

### Removal from zone settings

In `view-zone-settings.ts`:

- Remove the `_renderRunHistory(zone)` call (~line 1815) and the now-unused
  `_renderRunHistory` and `_renderRunLogRow` methods.
- Move (do not duplicate) any history-only CSS (`.history-table`, `.history-usage`,
  `.history-chip`, `.history-<result>`, etc.) that is no longer referenced by the
  settings view into `si-zone-history`'s styles. Leave shared styles that other
  parts of the settings still use.

### i18n

- New keys, added in **all eight languages** (en, de, es, fr, it, nl, no, sk):
  - `panels.history.title` — the tab label ("Verlauf" / "History" / …).
  - `panels.history.select_zone` — the dropdown label.
  - `panels.history.no_zones` — the message shown when no zones are configured.
- All existing `panels.zones.history.*` keys stay where they are and are reused by
  `si-zone-history`.

## Testing

Vitest, following the `si-schedule-dialog.test.ts` pattern (render the component,
introspect the flattened template):

- `si-zone-history`:
  - renders the cumulative-usage value and the runs table for a zone with a
    non-empty `run_log`;
  - renders the empty note (and no table) for a zone with an empty `run_log`;
  - renders one row per log entry with the correct result chip class.
- `view-history`:
  - defaults the selector to the first zone and renders that zone's history;
  - switching the selector to another zone renders the other zone's history;
  - shows the no-zones state when there are no zones.

The full frontend suite must stay green.

## Delivery

General-purpose UI improvement → upstream-able. Build as a normal fork feature; a
PR to JustChr and/or a production rebuild is a separate decision after the feature
is implemented, reviewed, and (per the project's manual-verification rule) checked
live in the panel (the observable criterion: the "Verlauf" tab appears, the
selector switches zones, and the selected zone's history renders — while the zone
settings no longer show a history section).

## Design history (Regel P1)

On completion, this spec plus the implementation plan move to the
`archive/design-history` branch before the dev branch is removed.
