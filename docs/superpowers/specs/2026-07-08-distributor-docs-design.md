# Distributor documentation page — Design

Date: 2026-07-08
Branch: `feature/gardena-distributor`
Origin: preparing the Gardena distributor feature for the upstream PR to JustChr. The
feature ships as an opt-in experimental toggle (b28); it now needs an end-user
documentation page on the Jekyll docs site (justchr.github.io/HAsmartirrigation).

## Problem

The distributor is a large, new, opt-in experimental feature with no documentation. The
Jekyll docs site has a page per configuration area (`configuration-*.md`) reached from the
`configuration.md` index and a Previous/Next breadcrumb chain; distributors are absent
from all of it.

## Decisions (user, 2026-07-08)

- One **comprehensive reference page** `configuration-distributors.md` (~150–200 lines,
  calibrated to `configuration-my-zones.md`), not a lean overview.
- **No images** at all (no screenshots, no placeholder markers) — text only.
- Placed in the breadcrumb chain **right after Experimental** (that is where the feature
  is enabled): `Sensor groups → Experimental → Distributors → Usage`.
- Prominent experimental/beta callout with the "watch the first days" advisory.

## Design

### New page: `docs/configuration-distributors.md`

Jekyll front matter + breadcrumb header matching the sibling pages:
```markdown
---
layout: default
title: "Configuration: Distributors"
---
# Mechanical water distributors

> Main page: [Configuration](configuration.md)<br/>
> Previous: [Experimental](configuration-experimental.md)<br/>
> Next: [Usage](usage.md)
```

Section outline (`##`/`###`), each scaled to its topic:

1. **Intro** — what a mechanical indexing / pressure distributor is (a single supply split
   across several outlets, advanced by pulsing the water on and off; Gardena Water
   Distributor as the consumer example, K-Rain/FIMCO indexing valves as the pro
   equivalent). The blind-outlet model: the device has no position feedback.
2. **Experimental — read first** — a blockquote callout: not fully hardware-tested; watch
   the first days of use closely; keep the device's manual override within reach; it is
   opt-in and can be switched back off at any time without losing data.
3. **Enabling it** — the *Setup → Experimental → Mechanical water distributors* toggle
   (off by default). Turning it on reveals the **Distributors** setup tab and the per-zone
   **Water distributor** field. Link to [Experimental](configuration-experimental.md).
4. **Creating a distributor** — name; the two inlet modes: **classic** (Home Assistant
   opens/closes an inlet switch/valve entity directly) vs **self-closing service** (a
   run/stop script actuates a device that closes itself; the inlet entity is watch-only).
   Inlet entity, pulse duration + unit (seconds/minutes).
5. **Assigning zones to outlets** — the per-zone *Water distributor* selector assigns a
   zone to the distributor; outlet numbers are arranged on the distributor page as a
   contiguous 1..n mapping; a member zone is watered through its outlet (its own valve and
   schedule are managed by the distributor). Unmapped outlets are skipped with a short
   pulse.
6. **Commissioning & position tracking** — blind outlets can't report position, so Smart
   Irrigation tracks it: an advance is counted on the inlet valve's **off-edge**. *Set
   current outlet* re-anchors the tracked position (with a safety confirm) after you turn
   the device by hand; the **test run** waters each mapped outlet ~30 s so you can watch
   it step and read off the pause it needs; **commissioning confirm** arms it for
   automatic cycles; a lost/ambiguous position marks the distributor **uncertain**
   (re-sync required).
7. **Advance pause & skip pulses** — the pause between outlets (long enough for the device
   to actually step; a 10 s floor is enforced) and the skip pulse used to pass an outlet
   with no mapped zone without watering it (also a 10 s floor).
8. **Master valve / pump coordination** — how a configured master valve/pump is switched
   for the distributor, the *master off after each zone* interaction with sequential /
   rotating sequencing (the pump cycles per outlet), and that a distributor feeds one
   outlet at a time so its zones water in sequence even under parallel sequencing.
9. **Watching the inlet for foreign pulses** — the optional inlet-watch and the three
   **watch modes**: *count it* (advance the tracked position), *warn* (mark the position
   uncertain), *ignore*. Only pulses Home Assistant can see are detected.
10. **Optional flow sensor** — assigning the distributor's shared inlet flow meter lets
    each outlet's delivered volume be measured and credited instead of the time estimate,
    and (where the valve can be stopped) stop early once the target volume is reached.
    **Caveat:** this path is rate-only and could not be hardware-tested — treat it as the
    least-proven part of an already-experimental feature.
11. **Troubleshooting & tips** — the pressure/flow requirement (≥ 1 bar, ≥ 20 l/h; a firm
    pulse is needed to advance reliably); re-sync with *Set current outlet* after a manual
    turn; the parallel-draw advisory; what "uncertain" means and how to clear it.

Tone/voice: match the existing docs (second-person, concise, **bold** for UI labels,
back-tick for entity/field names, cross-links to sibling pages). No images.

### Companion edits (small)

1. `configuration-experimental.md` — the page currently documents two bucket toggles.
   Since the distributor toggle now also lives on that tab, add a short **Mechanical water
   distributors** subsection (2–3 sentences: what it gates, that it is experimental, link
   to the new page). Change its breadcrumb **Next** from `Usage` to
   `[Distributors](configuration-distributors.md)`. (Its intro line "change how each zone's
   bucket is filled" describes the two bucket toggles; keep that accurate — the distributor
   toggle is a different kind of opt-in, so introduce it as such rather than lumping it in.)
2. `usage.md` — change its breadcrumb **Previous** from `Experimental` to
   `[Distributors](configuration-distributors.md)`.
3. `configuration.md` (index) — add **Distributors** to the numbered Setup-tabs list
   (between *My Zones* and *When to Water*, matching the tab order) with a one-line
   description + link, and mention it in the "suggested reading order" as an optional
   experimental extra.

## Out of scope

- No images/screenshots (user decision).
- No `navigation.yml` change (it only holds the six top-level sections; per-page nav is via
  the index + breadcrumbs).
- No code, no i18n, no release — this is docs only. It lands on the same branch and goes
  into the upstream PR.

## Testing / verification

Docs are Markdown; there is no test suite. Verification is: (a) internal links resolve to
existing files (`configuration-experimental.md`, `usage.md`, `configuration.md`,
`configuration-my-zones.md`, `configuration-schedules.md`); (b) the breadcrumb chain is
consistent in both directions (Experimental.Next → Distributors → Usage, and
Usage.Previous → Distributors); (c) the page renders as valid Markdown (headings, lists,
blockquote callout). A local `grep` link-check over the new/edited files suffices.
