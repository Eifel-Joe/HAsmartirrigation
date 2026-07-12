# Distributor experimental gating — Design

Date: 2026-07-08
Branch: `feature/gardena-distributor`
Origin: preparing the Gardena distributor feature for an upstream PR to JustChr. The
feature ships behind an opt-in experimental toggle (off by default), matching the other
Setup → Experimental features, with a "watch the first days" advisory.

## Problem

The Gardena distributor is a large, new feature that could not be fully hardware-tested
(no flow-rate sensor). For an upstream release it must be **opt-in and clearly marked
experimental**, so fresh users don't stumble into it. Today the Distributors tab and the
zone-side distributor-assignment control are always visible.

## Decisions (user, 2026-07-08)

- Gate the whole feature behind a new experimental flag `distributors_enabled` (default
  **off**), surfaced as a third toggle on Setup → Experimental.
- The Distributors UI stays where it is; the flag only controls **visibility** of the
  distributor surfaces (tab + zone selector), plus an experimental banner on the page.
- The backend engine is unchanged (already inert without configured distributors); the
  flag does not stop existing distributor cycles.

## Design

### Backend — the `distributors_enabled` flag

Add, in the `const.py` "Experimental features" block (alongside
`CONF_OBSERVED_WATERING_ENABLED` / `CONF_LIVE_ESTIMATE_ENABLED`):
```python
CONF_DISTRIBUTORS_ENABLED = "distributors_enabled"
CONF_DEFAULT_DISTRIBUTORS_ENABLED = False
```
Wire it through the config round-trip exactly like the other two experimental flags:
- `store.py` — include `distributors_enabled` in the config object (default False) so it
  serializes/deserializes and survives restart.
- `websockets.py` — `fetchConfig` returns it; `saveConfig` merges a partial
  `{distributors_enabled: bool}` without clobbering other settings (the existing
  merge-partial behaviour already does this).

Scope: the flag is a **UI-visibility gate**. No coordinator/engine code reads it — the
distributor engine is already inert unless distributors are configured, and a user who
disables the flag after assigning zones keeps their existing behaviour (we never silently
stop irrigation). This is the conservative, safe choice.

### Frontend — four gated surfaces

1. **Setup → Experimental (`view-experimental.ts`)** — add a third
   `_renderToggleCard("distributors", CONF_DISTRIBUTORS_ENABLED, config.distributors_enabled)`
   after the two existing cards, and extend the `ExperimentalFlag` union. The card's
   copy states the feature is experimental/beta and advises watching the first days of
   use closely. Frontend `const.ts` gains `CONF_DISTRIBUTORS_ENABLED`; `types.ts`
   `SmartIrrigationConfig` gains `distributors_enabled: boolean`.

2. **Setup → Distributors tab (`view-setup.ts`)** — currently the nav renders all
   `ESetupTab` values statically and `view-setup` does not read config. Add config
   fetching + the `DOMAIN + "_config_updated"` subscription (mirroring
   `view-experimental.ts`), then: (a) filter the Distributors button out of the nav when
   `!config.distributors_enabled`; (b) guard `_renderContent(ESetupTab.Distributors)` so
   a stale deep-link URL falls back to a safe tab (e.g. redirect to the default tab or
   render nothing) instead of showing the hidden page.

3. **Zone settings (`view-zone-settings.ts`)** — this view already fetches `config`
   (destructured in its load). Gate `_renderDistributorSelector(zone, index)` and its
   companion "distributor-managed" note on `config.distributors_enabled`, so the
   per-zone "Distributor" dropdown disappears when the feature is off. (`view-zones.ts`
   needs no change — its distributor fetch only gates a member zone's busy-hint, and with
   no assignments every zone is standalone, so the path is naturally inert.)

4. **Distributor page (`view-distributor-settings.ts`)** — add a slim experimental
   banner at the top of the page (near the existing `hints.pressure` /
   `hints.parallel_draw` blocks), carrying the "experimental — watch the first days"
   advisory. Reuse the warning-alert styling already used for the experimental banner.

### i18n (8 languages)

- `panels.experimental.distributors.{title,description,label,note}` — the toggle card.
- `panels.distributors.hints.experimental` (or similar) — the page banner.

Both in all 8 languages (en, de, nl, fr, es, it, no, sk).

### Edge case (accepted)

A zone already assigned to a distributor when the flag is later turned off: the selector
is hidden but the backend membership persists. Unreachable on a fresh upstream install
(default off ⇒ never assignable); only relevant on an install that had the flag on. We
simply hide — no data migration, no forced detach.

## Testing

- Backend: `distributors_enabled` defaults to False and round-trips through the store
  (unit test in the store/config suite).
- Frontend (vitest): `view-experimental` renders the third toggle; `view-setup` hides the
  Distributors nav button + content when the flag is off and shows them when on;
  `view-zone-settings` hides the distributor selector when off, shows it when on. Follow
  the existing DOM-shim + `flatten(render())` test style where those views are testable;
  otherwise assert on the render branch the way the current suites do.

## Out of scope

- No change to distributor engine/coordinator behaviour.
- No docs in this sub-project (the feature doc page + experimental-page update are a
  separate follow-up that lands in the PR branch).
- No change to the flow-volume metering or any other distributor logic.

## Release

Ship as pre-release `v2026.07.11b28` (Eifel-Joe, `feature/gardena-distributor`) for live
verification, then proceed to docs + the upstream PR construction.
