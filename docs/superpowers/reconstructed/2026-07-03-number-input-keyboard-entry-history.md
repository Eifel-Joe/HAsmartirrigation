# Allow keyboard entry in master & zone-sequencing number inputs

> ⚠️ **Reconstructed on 2026-08-08** from git commits, the pull request and project memory — this is **not** a contemporaneous design doc. It summarises, from the best available evidence, how/why this change came to be and how it was implemented.

**Feature date:** 2026-07-03  ·  **PR:** —  ·  **Branch(es):** fix-number-input-keyboard-entry
**Commit(s):** e792944c

## Problem / Context
Four number inputs in the General/Setup view — master kick-pause, master settle, zone-sequencing max-consecutive-duration and min-absorption-time — could only be changed with the arrow keys; typed digits were discarded. Root cause: these fields used `.value="${live(...)}"` with an `@change` handler (commit on blur). The view re-renders on every `hass` update; because a typed value is not committed until blur, the next re-render runs the `live()` directive, sees the DOM value differ from the unchanged state, and reverts the field — wiping the input. Arrow keys work only because they fire `change` on each press.

## Options considered
Not reconstructable — the commit and PR record only the chosen solution.

## Decision
Align the four outlier fields with the pattern every other number input in the panel already uses: a plain `.value="${expr}"` (no `live()`) plus an `@input` handler that commits per keystroke. The commit message notes this established pattern works correctly, so the fix converges the outliers onto it rather than introducing a new mechanism.

## Implementation
Only `custom_components/smart_irrigation/frontend/src/views/general/view-general.ts` changed. Each of the four inputs dropped the `live()` directive, switched `@change` to `@input`, and moved parsing into a guarded handler that parses the value (`parseInt`/`parseFloat`) and only calls `handleConfigChange` when the result is not `NaN` (replacing the old `|| default` fallback). The `frontend/dist/smart-irrigation.js` bundle was rebuilt in the same commit.

## Evidence
- PR: —
- Commit(s): e792944c — fix(frontend): allow keyboard entry in master & zone-sequencing number inputs
- Tests: —
- Memory: —

## Related
—
