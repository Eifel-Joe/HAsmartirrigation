# Configurable distributor inlet-watch (tri-state, both modes) — Design

Date: 2026-07-07
Branch: `feature/gardena-distributor`
Phase: Fix-Roadmap Phase 2 (b) + (c) merged (see `hasi-distributor-fix-roadmap`, `hasi-distributor-selfclosing-inlet-watch-gap`, `hasi-distributor-position-ideas`)

## Problem

The E4 inlet-watch is a binary opt-in (`watch_inlet`, bool):
- ON → `_dist_refresh_inlet_watch` registers a state listener on `inlet_entity`; a
  foreign off→on pulse outside a HASI cycle advances the tracked position by 1
  (`_dist_on_inlet_pulse`), keeping HASI synced with manual/foreign actuations.
- OFF → **no listener at all** → a foreign pulse is never observed → the tracked
  position silently desyncs (the physical pressure-indexing ring advanced; HASI's
  stale position → the next cycle waters the WRONG outlets). There is no
  "uncertain on foreign pulse" path (`hasi-distributor-selfclosing-inlet-watch-gap`).

Two shortcomings, decided together (user, 2026-07-07):
1. **Reaction is binary.** Silent desync is dangerous; the user wants a middle ground
   (warn) and an explicit ignore, i.e. a tri-state reaction.
2. **Self-closing mode can't watch at all.** `inlet_entity` + the watch control live
   only in the classic form section (`_renderClassicRow`); a self-closing/service
   distributor cannot set `inlet_entity` or enable the watch via the UI, so E4 is
   UI-unreachable for self-closing distributors.

Mechanical truth: a pressure-driven indexing distributor advances on EVERY inlet
pressure pulse, so a foreign inlet pulse IS always a real ring advance. The only
questions are whether HASI can reliably observe it and how it should react.

## Decisions (user, 2026-07-07)

- **Tri-state reaction:** replace `watch_inlet` (bool) with `watch_mode` (enum):
  `count` / `warn` / `ignore`.
  - `count` = advance the tracked position on a foreign pulse (today's ON behaviour).
  - `warn` = mark the distributor `uncertain` (de-arm + notify; blocks scheduled
    watering until the user re-syncs) instead of silently desyncing.
  - `ignore` = do not observe (today's OFF behaviour; no listener).
- **Watched entity = `inlet_entity`, exposed in BOTH modes.** Classic: HASI actuates
  it AND (per `watch_mode`) watches it. Self-closing: watch-ONLY — the run/stop
  services actuate; `inlet_entity` is never switched, only read. A helper/hint text in
  self-closing mode makes this clear (and that it is NOT the flow/confirm sensor).
- **Default for new distributors:** `ignore` (matches today's `watch_inlet=False`
  default — no surprise auto-resync or warnings until the user opts in).
- **Migration:** existing distributors keep today's behaviour — when `watch_mode` is
  absent, derive it from the legacy `watch_inlet` (`True` → `count`, else → `ignore`).

## Design

### Data model (`store.py`)

- Add `watch_mode = attr.ib(type=str, default="ignore")` to the distributor attrs
  entry (alongside `inlet_entity` / `watch_inlet`, ~`store.py:344/365`).
- In the distributor load/migration path (~`store.py:823-841`), derive:
  `watch_mode=dist.get("watch_mode") or ("count" if dist.get("watch_inlet") else "ignore")`.
- Keep `watch_inlet` in the attrs entry as a read-only legacy field (older persisted
  records still carry it); the form stops writing it and writes `watch_mode` instead.
  New writes may drop `watch_inlet`. (Additive; no storage VERSION bump — mirrors the
  soil-veto feature's additive approach.)

### Backend behaviour (`distributor.py`)

- `_dist_refresh_inlet_watch`: register the listener when `inlet_entity` is a non-empty
  string AND `watch_mode != "ignore"` (was: `watch_inlet` truthy). Mode-agnostic —
  `inlet_entity` is read regardless of `watering_mode`; it is only ever ACTUATED by
  `_dist_open_inlet`/`_dist_close_inlet`, which are already service-gated (self-closing
  never switches it).
- `_dist_on_inlet_pulse`: branch on the distributor's `watch_mode`:
  - `count` → the current `(cur % n) + 1` advance + persist (unchanged).
  - `warn` → `await self._dist_mark_uncertain(dist, reason=<foreign inlet pulse>)`
    (de-arm + `zone`/distributor-halted event + notification). New reason constant.
  - `ignore` → unreachable (no listener); defensive no-op if somehow called.
  - The existing guard stays: only react when no HASI cycle is active
    (`active_cycle` empty) — HASI's own in-cycle pulses must never count/ warn.

### Frontend (`si-distributor-form.ts`, `view-distributor-settings.ts`, `types.ts`, `const.ts`, 8 × `localize/languages/*.json`)

- Move `inlet_entity` + the watch control out of `_renderClassicRow` into the shared
  section so both modes render them (or add to `_renderServiceRows` too). In
  self-closing mode, show a hint text: the field is the ring valve HASI *observes* for
  foreign pulses; actuation is via the run/stop service; it is NOT the flow/confirm
  sensor.
- Replace the `watch_inlet` toggle with a `watch_mode` 3-option select
  (count / warn / ignore).
- Types: `types.ts` `watch_inlet?: boolean` → add `watch_mode?: "count" | "warn" | "ignore"`
  (keep `watch_inlet?` typed for legacy reads); `const.ts` add the field key + option
  constants.
- i18n: field label, the 3 mode labels, and the self-closing hint text in ALL 8
  languages (`en, de, nl, fr, es, it, no, sk`). (`hasi-i18n-all-languages`.)

### Websocket / API (`websockets.py`)

- Ensure the distributor upsert/read passes `watch_mode` through (the CRUD drops
  unknown keys via the attrs allowlist, so `watch_mode` must be an allowed attr — it
  is, once added to the entry).

## Testing

Backend (pytest):
- `watch_mode=count` foreign pulse → position advances (current behaviour preserved).
- `watch_mode=warn` foreign pulse → `_dist_mark_uncertain` called, position NOT
  advanced.
- `watch_mode=ignore` → `_dist_refresh_inlet_watch` registers NO listener.
- `_dist_refresh_inlet_watch` registers a listener for a self-closing (service-mode)
  distributor with `inlet_entity` set + `watch_mode != ignore` (mode-agnostic).
- Legacy derive: a distributor dict with `watch_inlet=True` and no `watch_mode` loads
  as `watch_mode="count"`; `watch_inlet=False`/absent → `ignore`.
- In-cycle guard: a pulse while `active_cycle` is set is ignored for all modes.

Frontend (vitest): the form renders `inlet_entity` + `watch_mode` in both modes; the
self-closing hint text renders; the select writes `watch_mode`. (Build-only locally;
click-tested in the beta.)

## Rationale

- A foreign inlet pulse of a pressure-indexing valve is always a real ring advance, so
  observing it and reacting (count or warn) is mechanically justified; `ignore` remains
  for unreliable sensors that emit spurious edges.
- `warn` removes the dangerous silent desync (wrong-outlet watering) by surfacing it
  through the existing uncertain/de-arm path the user already knows.
- Reusing `inlet_entity` keeps the config surface small and matches the physical
  "inlet valve" concept across both modes; the self-closing hint disambiguates its
  watch-only role.

## Out of scope

The soil-veto (Phase 2a, shipped b20), the master-lifecycle fixes (b19), the JustChr
"credit water from observed irrigation" experimental feature (explicitly NOT this —
E4 only syncs position, never credits buckets), and any change to how the run/stop
services actuate self-closing valves.
