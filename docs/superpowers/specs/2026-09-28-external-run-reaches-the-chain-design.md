# An external run reaches the chain

Design for `Eifel-Joe#64`. Base: `master` = `6acfc819` (= `upstream/master`, 0 ahead).

`Eifel-Joe#43` and `JustChr#179` closed the take-overs the chain can *see*: a run the
integration itself dispatched. This one is invisible to both halves of that defence,
and unlike `Eifel-Joe#45` it needs no rotating configuration — it bites the sequential
geometry, which is what the affected installation runs.

## The defect, measured

Both rows measured against `6acfc819` through the real `_credit_observed_watering` path,
not a simulation of it (probe `issue45-work/probe_observed_chain.py`, recorded in
`Eifel-Joe#64`). Zone 1 watering, zone 2 queued behind it, zone 2 opened externally:

| geometry | result |
|---|---|
| **sequential** | credit `bucket -20.000 -> -13.800` (+6.20 mm), `queue DANACH: [2]`, `zone_run_in_flight(2): False`, then `dispatched=[(1, 600.0), (2, 600.0)]` |
| **rotating**, against the branch carrying `JustChr#179` | credit lands, then still `dispatched=[(1, 300.0), (2, 300.0)]` |

## Why no existing guard sees it

`observed_watering.py` credits an external run through `_record_run` +
`async_write_watered_bucket`. It never calls `_sc_finish_run` or
`_chain_advance_for_run`, and it registers nothing anywhere: it only *reads*
`zone_run_in_flight` (`observed_watering.py:138`) to exclude valves the integration
opened itself.

| guard | why it misses |
|---|---|
| `zone_run_in_flight` at the zone's turn (`run_chain.py:367` sequential, `:683` rotating) | observed registers no run, so it answers `False` while the external valve is open |
| `_chain_forget_finished` (`run_chain.py:419`) | reached only via `_chain_advance_for_run`, which an observed run never calls |
| the rotating write-off (`JustChr#179`) | same — it fires on a finalisation that never happens |

## What makes it worse than double watering

**Measured on `6acfc819`** before the first line of production code, because the severity
claim rests on it (probe: `docs/superpowers/probes/2026-09-28-discarded-surplus-probe.py`,
run through the real `_credit_observed_watering`, the real `_chain_advance` and the real
`_run_ceiling` — only the harness's own mocks stand in, and the clamp under measurement is
not one of them):

```
external credit writes bucket: -13.800
dispatched:                    [(1, 600.0), (2, 600.0)]
buckets the cycle's run wrote: [(2, 0.0)]
ceiling for that run:          0.0
pre + delivered depth:         6.200
```

`_run_ceiling` (`irrigation.py:2789`) lets a normal run credit up to
`max(target, pre_bucket)`, i.e. `0.0` for a thirsty zone. In the sequential row above the
cycle's run is dispatched for a duration priced at bucket `-20`, delivers that water, but
may only credit up to `0.0` from `pre = -13.80`. The 6.20 mm of surplus the external run
created is **discarded, not carried** — the write the run actually makes is `(2, 0.0)`.

Two things the numbers settle that reading the code did not:

* the second dispatch reads the bucket **after** the external credit (`run_chain.py:330`
  re-reads the zone at dispatch), so the surplus is not an artefact of a stale snapshot —
  the run is priced from the old bucket at *plan* time and clamped at *credit* time, and
  those are the two different moments that make the water vanish;
* the discarded surplus **equals the external credit** (6.20 mm), and that is structural
  rather than a coincidence of the fixture: a correctly sized run covers exactly the
  original deficit, so whatever the external run already put in is precisely what
  overflows. The absolute figure scales with the external run; the identity does not.

So the failure is not symmetric with under-watering:

* **over-watering here is invisible** — the surplus leaves no trace in the bucket, so the
  next day's calculation asks for a full day's evapotranspiration on soil that holds
  extra water;
* **under-watering is visible** — a bucket left negative is exactly what the next cycle
  reads and makes up.

`_run_ceiling`'s discard is deliberate (it absorbs a timed run's lead-time over-credit)
and is **not** touched here.

## Why this installation is the affected one

Read from the running installation's diagnostics on 2026-09-28 — not assumed, and not
inferred from the feature flag alone, because the mechanism needs a watched entity per
zone:

| zone | mode | `observed_entity` | `maximum_duration` |
|---|---|---|---|
| 0 Kirschlorbeer | service | `valve.wasser_vorne` (= its `confirm_entity`) | 3600 |
| 1 Kirschbaum | service | `valve.wasser_hinten` (= its `confirm_entity`) | 3600 |
| 2 Beet | service | `valve.wasser_beet_valve_l1` (= its `confirm_entity`) | 2700 |

All three `automatic`, `zone_sequencing: sequential`, one daily "all zones" schedule.
Seven external runs are on record in the three zones' run logs: 72 s, 90 s, 718 s, 718 s,
2153 s, 10518 s, 21304 s. The trigger is not hypothetical on this box.

## Requirements

Two windows, the same split that made `Eifel-Joe#43` and `Eifel-Joe#45` separate pieces
of work:

1. **While the external run is open** — the chain's guard at the zone's turn must see it.
2. **After it has closed** — the chain must be told, because a predicate cannot recover a
   fact whose record has been removed (the lesson of `Eifel-Joe#45`).

Both geometries. No new persisted state. Nothing that makes the integration actuate or
finalise a valve it did not open.

## Options considered

| option | both windows? | cost |
|---|---|---|
| **chosen: two small pieces** — a fourth source in `zone_run_in_flight`, plus an entry into the chain at the close edge | yes | the fourth source changes every reader of that predicate, and one of them (`calculation.py:510`) has no pick-up on the observed path |
| observed becomes a real run: record in `CONF_ACTIVE_VALVE_RUNS`, finalised through the normal path | yes, from one mechanism | `async_resume_self_closing_runs` would adopt and finalise a run the integration never dispatched; `master.py:242` would block the boot-time master-off; `run_chain.py:319` would freeze a cycle on a leaked record; `_record_run` written twice |
| only the entry into the chain | window 2 only | leaves the likelier production case open: a hand-open during the morning cycle, with the turn arriving while it is open |
| window 1 only inside the chain (the two turn sites, not the predicate) | window 1 only, narrowly | a second, competing answer to the question `run_state.py` exists to answer exactly once |

Registration alone does **not** collapse the two windows: when the external run closes
before the zone's turn, its entry is gone and the chain waters. They collapse only if
observed also *finalises*, which is the expensive option above.

## The design

### Part 1 — window 1

`zone_run_in_flight` gains a fourth source, `_observed_run_in_flight`: an entry in the
existing `_observed_on_since` whose age is within the zone's external-run ceiling. No new
store — observed already records when the external valve opened.

The ceiling is not invented. It is lifted out of `_observed_capped_seconds` into one
helper both callers use: `maximum_duration` (or `CONF_DEFAULT_MAXIMUM_DURATION` when that
is absent or negative) plus `OBSERVED_CAP_MARGIN_SECONDS`. Bounded for the same reason
`_self_closing_run_in_flight` is bounded: a record that outlives its finaliser must not
block every future run of that zone with no way out. Here a valve stuck reporting `open`
would otherwise drop the zone from every cycle *and* park its calculation for ever.

Two obligatory companions, both consequences of widening the predicate:

* **`observed_watering.py:138` is switched to the question it actually asks.** That site
  means "did the integration itself open this?", and has been using `zone_run_in_flight`
  as a proxy for it. Asking the three integration-owned sources explicitly removes the
  self-hit by construction rather than by ordering luck.
* **`_credit_observed_watering` picks up the deferred calculation.**
  `calculation.py:510` gives way to a run in flight, and every one of the five pick-up
  sites is the teardown of a run the integration itself drove (`_release_chain_zones`,
  `_run_valve_metered`, `_sc_finish_run`, `async_stop_self_closing`,
  `async_run_distributor_cycle`). An observed run is none of them, so without this the
  zone's calculation stays parked until its next real run.

### Part 2 — window 2

At the close edge in `_observed_state_changed` — synchronously, in the callback, before
the credit task is created, so there is no `await` window for the chain to slip through —
an external run that meets the provenance line calls `_chain_drop_zone`.

That helper already does what is needed, and is the path `async_stop_zone` takes: it walks
every chain, clears the queue entry **and** `rotation.remaining` **and** `planned`, and
hands back the live-estimate marker under a `held` gate. Both geometries, no new state,
idempotent if part 1 already dropped the zone at its turn.

The whole remainder is written off rather than a proportional share — the decision already
taken for `Eifel-Joe#45`, and the only shape that reaches the rotating geometry at all: a
rotation's `remaining` is built once at cycle start and never re-read from the zone's
duration, so re-pricing the zone cannot touch it.

The write-off is keyed on the external **run**, not on the credit that follows it: it
fires even when `_credit_observed_watering` then books nothing (a zone without a size or a
throughput). The water was applied either way, and the chain's rule is one turn per cycle,
not one credit per cycle.

### The provenance line

The write-off fires at `OBSERVED_SAMPLE_MIN_RUN_SECONDS` (300 s) and not below it. That
constant already draws this exact distinction — "nobody hand-holds a valve for five
minutes, so a shorter open is probably testing rather than watering" — and this is a
provenance question, not a quantisation one: did someone water this zone, or poke its
valve? No new parameter.

What it deliberately leaves: an external open shorter than five minutes still loses its
water from the model, up to about 2.5 mm on the smallest zone. That is the bounded, milder
error, and the unbounded one is gone. It also keeps the two shortest recorded runs (72 s,
90 s) from costing a zone its whole day.

Window 1 has **no** such threshold: while the valve is open the zone is being watered,
however briefly, and dispatching a second run onto an open valve is wrong at any length.

## Explicitly not in this work

* **The distributor sweep.** `distributor.py` never asks `zone_run_in_flight` at all, so
  an externally watered member zone is invisible to it. A sibling of this defect, found
  while reading for it; its own issue, not this change.
* **`_run_ceiling`'s silent discard of a surplus** — deliberate, upstream-agreed.
* **Proportional accounting of the external run** — rejected for `Eifel-Joe#45`, and it
  cannot reach the rotating geometry.
* **Anything about what observed credits.** The credit is correct; only the chain's
  knowledge of it is missing.

## End-to-end criterion

A test per cell, all four driving the real `_credit_observed_watering` path, with an
external run of 600 s — past the provenance line, so both windows are in scope:

| geometry | external run at the zone's turn | expected |
|---|---|---|
| sequential | still open | zone dropped from the cycle, no second dispatch |
| sequential | closed before the turn | queue empty, no second dispatch |
| rotating | still open | remainder written off, no second slot |
| rotating | closed before the turn | remainder written off, no second slot |

Plus the other direction: a 72 s external open **keeps** the zone's turn, and an open
valve is never dispatched onto regardless of length.

Then: the full suite with no new failures against `issue45-work/baseline-6acfc819.txt`
(374 names, measured on this base); `black` and `ruff` clean; a mutation matrix over every
added line, with no survivor left standing on an argument instead of a measurement; and a
live run on HA-Test where a zone's valve is opened externally during a cycle and the log
shows the zone leaving the cycle instead of watering a second time.
