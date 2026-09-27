# Live test — the dry-run witness on the self-closing path (2026-09-27)

Verifies the reworked guard from
`specs/2026-09-26-self-closing-fault-lifecycle-design.md` §11 on HA-Test. The
earlier live test of this feature (`reconstructed/2026-09-27-dry-distributor-member-live.md`)
proved the chain ran but not that it judged correctly, because its flow sensor
had gone quiet five minutes before the valve opened — which is exactly the case
§11.1 is about. This one separates the two.

## Build

Throwaway pre-release **`v2026.09.27b2`**, branch `prerelease/v2026.09.27b2`,
commit `2a1ee093` = `upstream/master c5330c7f` + the two commits of the reworked
fix + version bump and rebuilt bundles. Installed via HACS, HA-Test restarted.
Confirmed loaded: `update.smart_irrigation_update` reported
`installed_version = v2026.09.27b2`, config entry state `loaded`.
`production` and HA-Prod untouched.

## Setup

- Zone **Grace Test** (`zone_id 8`), watering mode self-closing/service,
  `throughput 4.0` L/min, `maximum_duration 3600`. It had **no** flow sensor
  before this test.
- Flow source: **`input_number.hasi_flow_probe`**, unit `L/min`, held at `0.0`
  for every run. Set as the zone's flow sensor through the panel (the picker
  filters to `sensor.*` but has `allow-custom-entity`).
- Every run: `irrigation_plus.run_zone` with `duration: 1` (the service takes
  minutes, minimum 1), so a 60 s window with polls at 15/30/45/60 s.

**Why an `input_number` and not a template sensor.** The report time had to be
controllable, and a state-based template sensor may not re-render when its source
is written with an unchanged value. `input_number.set_value` goes straight through
`async_write_ha_state`, which HA's own `async_set` turns into a new report
regardless of change. Measured before the runs, and this is the linchpin of the
whole test:

| | value | `last_reported` | `last_changed` |
|---|---|---|---|
| before `set_value` | `0.0` | 11:41:58 | 11:41:58 |
| after `set_value(0)` | `0.0` | **11:46:02** | 11:41:58 |

**244 s apart with an unchanged value.** So the separator the design rests on
exists, and it is drivable on demand.

## The three runs — one variable

Same zone, same sensor, same reading `0`, same 60 s window. The **only**
difference is whether the sensor spoke during the run.

| run | sensor during the run | result | bucket | water used | problem sensor |
|---|---|---|---|---|---|
| **(b)** | **quiet** (`last_reported` stayed 11:46:02) | completed | −3.3317 → **−2.9317** | 0 → **4.0 L** | off |
| **(a)** | **reported ~5×, value never changed** (`last_reported` 11:54:58 vs `last_changed` 11:41:58) | **failed** | −2.9317 → **−2.9317** | 4.0 → **4.0 L** | **on**, `flow_never_started`, since 13:52:23 |
| **(c)** | **quiet** again | completed | −2.9317 → **−2.5317** | 4.0 → **8.0 L** | **on → off** |

- `4.0 L` is the time-based volume, `throughput 4 L/min × 1 min` — what master
  credits, and what §11.1 says a quiet sensor must keep.
- Run (a) left the bucket, the total AND `last_irrigation` untouched
  (11:47:40 before and after), so nothing recorded it as a delivery.
- Run (c) shows the other half of the fault's life: a good run ends the fault the
  dry one raised.

## Log

```
2026-09-27 13:52:23.637 WARNING [custom_components.irrigation_plus.irrigation]
    Zone 8 irrigation fault: flow_never_started
```

Once, for run (a) only. The PirateWeather `429`s around it are unrelated (the key
is rate-limited on this instance).

**And what is NOT in the log:** zero occurrences of
`"produced no readings this run"`. That warning fires when the meter never got a
numeric reading. It stayed silent for all three runs, which is the point — the
meter read on every poll in every run, and the verdict turned purely on whether
those readings were *reports*. Had the old witness still been in place, run (b)
and run (c) would have been written off as dry exactly like run (a).

## What this does not cover

- The distributor path. Its own guard inherits this form separately.
- A totalizer flow source. The probe is a rate sensor, so the `_declined` half of
  the witness (totalizer fall, rate gap wider than `max_gap_s`) is covered by
  unit tests and the measured probe, not by this live run.
- HA-Prod. Untouched.

## Cleanup, and what it left behind

Removed: the GitHub release `v2026.09.27b2`, its tag, and the remote branch
`prerelease/v2026.09.27b2`.

**Kept on purpose:** the LOCAL branch `prerelease/v2026.09.27b2` at `2a1ee093`, in
the worktree `D:/Entwicklung/HASI/pr174-work/prerel`. Without it this build would
not be reconstructable, and HA-Test is still running it.

**Open on HA-Test:** it runs `v2026.09.27b2` whose release no longer exists, so
HACS cannot reinstall or verify that version. The installed files are intact and
the instance works; but to put it back on a build HACS knows, install
`v2026.09.27b1` (upstream master without this fix) or `v2026.09.22b1` (the last
build carrying the valve-safety work).

`input_number.hasi_flow_probe` and Grace Test's flow-sensor field: see the
session handover for which of the two was still outstanding.
