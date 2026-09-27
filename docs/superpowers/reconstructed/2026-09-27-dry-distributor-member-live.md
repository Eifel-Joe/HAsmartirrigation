# Live test: a dry distributor member run is not a delivery

- **Date:** 2026-09-27, HA-Test (`production` NOT touched)
- **Issue:** `Eifel-Joe#53` · **Branch:** `fix-a-dry-member-run-is-not-a-delivery`
- **Build under test:** `v2026.09.27b1`, commit `560fe52e`, a throwaway pre-release
  containing `upstream/master` `418ab8a0` + this fix and **nothing else**, so a finding
  here can only come from this change.
- **Build it replaced:** `v2026.09.22b1` — carries the two valve-safety fixes but leaves
  `distributor.py` untouched, so the defect is live on it.

## Setup

| | |
|---|---|
| Distributor | `Gardena1` (id 0), service mode, inlet `input_boolean.sonoff_emu_valve` |
| Flow sensor | `sensor.wasser_3_flow` — **reads `0`**, unit `m³/h`, `state_class measurement` (a RATE sensor) |
| Member zone | `Test2` (id 3), outlet 2, size 5 m², throughput 3 L/min |

The flow sensor had to be set by hand in the panel: distributor fields are read-only
over the MCP interface.

**Why this sensor exercises the genuine dry path and not an accident:** a rate sensor
reading `0` on every poll has an interval credited at 0 L on every poll, so
`metered_the_run()` is **true** — the meter accounted for the whole window — and
`delivered()` is `0.0`. That is the dry cistern, not a broken meter, which is exactly
the distinction the fix turns on.

## The three runs, same zone, same sensor, same service call

`irrigation_plus.run_zone` on `sensor.irrigation_plus_test2` with `duration: 1`, which
for a member zone routes through the distributor ring as a single-outlet manual run.
The first row used the scheduled cycle (`distributor_run_now`) instead; the second and
third are a matched pair on the identical call.

| time | planned | actual | volume | result | detail | build |
|---|---|---|---|---|---|---|
| 09:58:03 | 61 s | 61 s | **3.05 L** | `completed` | — | `v2026.09.22b1` |
| 10:15:59 | 60 s | 60 s | **3.0 L** | `completed` | — | `v2026.09.22b1` |
| **10:26:30** | 60 s | 60 s | **0 L** | **`failed`** | **`flow_never_started`** | **`v2026.09.27b1`** |

## The four observables

| | before the fix (10:15:59 run) | after the fix (10:26:30 run) |
|---|---|---|
| bucket | −5.0 → **−4.4** (credited 0.6 mm) | −5.0 → **−5.0**, unchanged |
| `water_used_total` | 1191.3 → **1194.3** (+3.0 L) | 1194.3 → **1194.3**, unchanged |
| `last_irrigation` | → **2026-09-27 10:15:59**, stamped | **2026-09-27 10:15:59**, i.e. still the OLD run's stamp |
| run log | `completed`, 3 L | **`failed`, `flow_never_started`, 0 L** |

`sensor.irrigation_plus_test2_last_water_used` also held at `3.0` — it declines a volume
of 0, so the last real delivery is not overwritten by a failure.

## The warning (Task 11)

```
2026-09-27 10:26:30.768 WARNING (MainThread) [custom_components.irrigation_plus.distributor]
Distributor 'Gardena1' outlet 2 (zone 3): the flow meter watched the whole 60 s window
and measured no water; recording the run as failed and crediting nothing
```

This doubles as proof that the new code was the code running: the string exists only in
this build. No zone fault was raised, by design — nothing on the distributor path ever
clears one (spec D2), so the warning is the visible channel.

## Scale of the defect, measured on the way

Before switching builds, one full scheduled cycle (`distributor_run_now`) ran with the
flow sensor already set and reading `0`. Four member zones each had **3.05 L** credited
and their buckets lifted from a deficit to 0 — **12.2 L booked as delivered, with the
meter reading zero the whole time** — `last_irrigation` stamped on all four, and every
problem sensor `off`. That is what the fix removes.

| zone | bucket | `water_used` | stamp |
|---|---|---|---|
| Test2 | −0.61 → 0.0 | 1188.25 → 1191.30 | 07:58:03 |
| Test3 | −0.61 → 0.0 | 1149.75 → 1152.80 | 07:59:24 |
| Test5 | −0.61 → 0.0 | 1207.40 → 1210.45 | 08:01:20 |
| Test6 | −0.61 → 0.0 | 1146.70 → 1149.75 | 08:02:41 |

## Loose ends, deliberately not chased

- **`Test4` (outlet 4, 7 s duration) behaved differently in that cycle:** its bucket
  moved (−0.07 → 0) while `water_used_total` stayed `0.0` and `last_irrigation` stayed
  `unknown`. Not investigated — it is independent of this change and was not a data
  point for the test. Worth a look if it recurs.
- **`irrigation_plus.set_bucket` targeted at a zone's *bucket* sensor returns HTTP 500**
  rather than rejecting the target; the zone's main sensor is the correct target. A
  pre-existing rough edge.
- **`set_bucket` does not recompute the zone's duration**, so a zone set to a deficit by
  hand is not "due" until the next calculation. During this test `calculate_zone` could
  not supply one either, because PirateWeather was returning **429** (rate limit) — which
  is why the matched pair used `run_zone`'s `duration_override` path instead of waiting
  for due-ness.

## State left on HA-Test

- `Gardena1` still carries `flow_sensor: sensor.wasser_3_flow`.
- `Test2`'s bucket sits at **−5 mm**, set by hand for this test, not a real deficit.
- `Test3`, `Test5`, `Test6` were reset to −0.61 by hand after the first cycle.
- The instance runs `v2026.09.27b1`, which does **not** contain the two valve-safety
  fixes that `v2026.09.22b1` had. Reinstall that build to get them back.
