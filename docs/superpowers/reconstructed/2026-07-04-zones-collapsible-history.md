# Collapsible zone settings + gear deep-link scroll fix

> ⚠️ **Reconstructed on 2026-08-08** from git commits, the pull request and project memory — this is **not** a contemporaneous design doc. It summarises, from the best available evidence, how/why this change came to be and how it was implemented.

**Feature date:** 2026-07-04  ·  **PR:** —  ·  **Branch(es):** feature/zones-collapsible
**Commit(s):** ec263498

## Problem / Context
Setup → Zones rendered every zone's settings as one long, always-expanded list, so a multi-zone setup was hard to scan. The same view also had a broken dashboard-gear deep link: it already received the target zone id and contained scroll code, but the smooth scroll fired while the always-expanded `ha-form` elements were still upgrading. The layout grew under the in-flight scroll, so it landed back at the top.

## Options considered
Not reconstructable — the commit and PR record only the chosen solution.

## Decision
Make each zone a collapsible card, all collapsed by default, and let the deep link expand its own target and scroll to it. Collapsed siblings keep the layout small and stable, which both improves scannability and fixes the scroll: with a stable layout the smooth scroll lands reliably instead of being pushed back to the top.

## Implementation
Frontend-only, in `custom_components/smart_irrigation/frontend/src/views/zones/view-zone-settings.ts`. A `@state() _expanded = new Set<number>()` tracks expanded zone ids, with `_isExpanded()` / `_toggleZone()` helpers. `renderZone()` wraps the zone body in `${expanded ? html`…` : ""}` and makes the card header a `role="button"` toggle (click + Enter/Space keydown, `aria-expanded`) with an `mdi:chevron-up/down` icon. `updated()` was reworked: the old boolean `_scrolledToTarget` became `_scrolledTo: number | null`; a deep link first expands its target, then on the next update scrolls inside a `requestAnimationFrame`. Most of the diff is re-indentation from wrapping the existing body; the rebuilt `frontend/dist/smart-irrigation.js` bundle is generated output.

## Evidence
- PR: —
- Commit(s): ec263498 — feat(zones): collapsible zone settings + fix gear deep-link scroll
- Tests: —
- Memory: —

## Related
[[hasi-frontend-refresh-drill]]
