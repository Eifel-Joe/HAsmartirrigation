# Live test: a dry distributor member run, on the three-condition witness (2026-09-27, evening)

- **HA-Test only.** `production` and HA-Prod untouched.
- **Supersedes** `reconstructed/2026-09-27-dry-distributor-member-live.md` for the
  landed form. That protocol is still valid evidence for the **two**-condition witness
  the branch carried at the time — see "Why the earlier protocol does not carry over".
- Build: **`v2026.09.27b3`**, branch `prerelease/v2026.09.27b3`, commit `6a313d7c` =
  `upstream/master 1c071cf0` + the nine commits of the fix + version bump and rebuilt
  bundles, and nothing else. Installed via HACS, HA-Test restarted.
  Confirmed loaded: `update.smart_irrigation_update` →
  `installed_version = v2026.09.27b3` **and** config entry state `loaded`
  (HTTP 200 alone is not proof).

## Why the earlier protocol does not carry over

The 10:26:30 run in the superseded protocol was written off with
`sensor.wasser_3_flow`, and its stated reason was "a rate sensor reading 0 on every
poll prices every interval, so `metered_the_run()` is **true**". That held for the
two-condition witness (`_priced and not _declined`). `master` requires a third
condition — `_saw_report_after_open` — and that sensor does not report during a run.
On this build the same setup keeps its time-based credit, which is **correct**. So the
dry half had to be re-proved with a source that speaks.

## Setup

| | |
|---|---|
| Distributor | `Gardena1` (id 0), service mode, inlet `input_boolean.sonoff_emu_valve`, `use_master: true`, `pause 15 s`, `skip_pulse 15 s` |
| Member zone | **`Test2`** (zone id 3, outlet 2), size 5 m², throughput 3 L/min |
| Flow source | **`input_number.hasi_flow_probe`**, unit `L/min`, held at `0.0` for both runs |
| Field | distributor „Durchflusssensor (optional)", set by the user in the panel (distributor fields are read-only over MCP). Previous value `sensor.wasser_3_flow`. Verified afterwards from the diagnostics sub-tree: `flow_sensor: "input_number.hasi_flow_probe"` |
| Call | `irrigation_plus.run_zone` on `sensor.irrigation_plus_test2`, `duration: 1` (minutes, minimum 1) — the weather-independent path; it routes a member zone through `_dispatch_distributor_cycles(duration_override=…)` into the changed block |

**The separator, measured on this instance, not taken from the earlier protocol:**

| | value | `last_reported` | `last_changed` |
|---|---|---|---|
| after creation | `0.0` | 18:12:38Z | 18:12:38Z |
| after `set_value(0)` | `0.0` | **18:17:16Z** | 18:12:38Z |

**278 s apart with an unchanged value.** So `input_number.set_value` advances the
report on demand while the value stands still.

⚠️ **The MCP `ha_get_state` tool reports `last_reported` wrongly** — it returned
18:12:38 for the row above where HA's own template engine returned 18:17:16, and it
returns `last_reported == last_changed` for every entity. Every report time in this
document was read through `states.<entity>.last_reported` in a template render. A
timing claim made from `ha_get_state` is not evidence.

**Ring cost, worth knowing before repeating this:** `current_outlet` was 3 and Test2
is outlet 2, so each run first advanced the ring 3 → 4 → 5 → 6 → 1 → 2, five skip
pulses of 15 s. The metering window opened about **150 s** after the service call. A
driver script sized for the window alone would fall silent before the window and
starve the witness — the first draft of it did, at 90 s, and was lengthened to 270 s
before the run.

## The two runs — same zone, same sensor, same reading `0`, same 60 s window

The only variable is whether the sensor **spoke** during the window. The driver is a
temporary script writing `set_value(0)` every 3 s.

| run | sensor during the window | run log | bucket | `water_used_total` | `last_irrigation` |
|---|---|---|---|---|---|
| **A** — driver on | reported every 3 s, value never changed | **`failed`, `flow_never_started`, 0 L** | −5.0 → **−5.0** | 1194.3 → **1194.3** | **10:15:59, i.e. the OLD run's stamp** |
| **B** — driver off | **quiet** (`last_reported` 18:23:37Z, and unchanged through the whole run — 514 s of silence by the time the window opened) | `completed`, **3.0 L** | −5.0 → **−4.4** | 1194.3 → **1197.3** | → **20:33:09**, stamped |

Run A, from the zone's own run log:

```json
{"ts":"2026-09-27T20:22:56.956014+02:00","trigger":"distributor","planned_s":60,
 "actual_s":60,"volume_l":0,"result":"failed","detail":"flow_never_started"}
```

and `last_water_used` held at `3.0` — it declines a volume of 0, so the last real
delivery is not overwritten by a failure. `binary_sensor.irrigation_plus_test2_problem`
stayed **off**, which is by design: nothing on the distributor path clears a zone
fault, so none is raised.

Run B, from the same log:

```json
{"ts":"2026-09-27T20:33:09.022282+02:00","trigger":"distributor","planned_s":60,
 "actual_s":60,"volume_l":3,"result":"completed","detail":null}
```

**3.0 L is the time-based credit** — `throughput 3 L/min × 1 min` — and 0.6 mm on
5 m² is the −5.0 → −4.4 the bucket moved. That is what `master` credits for this run,
and what a quiet sensor has to keep.

**Run B is the one the two-condition witness would have failed.** A rate sensor
reading 0 prices every interval and refuses none, so `_priced and not _declined` is
true and the run would have been written off as dry: no credit, no stamp, a `failed`
entry — for a zone whose irrigation was working. The third condition is the only thing
that separates it from run A, and the two runs differ in nothing else.

## The warning (it is the only thing a user not reading the run log sees)

```
2026-09-27 20:22:56 WARNING [custom_components.irrigation_plus.distributor]
Distributor 'Gardena1' outlet 2 (zone 3): the flow meter watched the whole 60 s window
and measured no water; recording the run as failed and crediting nothing
```

Once, for run A only, from `distributor.py:1647` — inside the `if dry:` branch.

## Leftovers on HA-Test

- `input_number.hasi_flow_probe` — **kept** on purpose. The sister fix's live test
  deleted its probe and the next test had to recreate it.
- `script.hasi_flow_probe_speak` — the temporary driver, deleted after the test (done).
- **`Gardena1`'s flow-sensor field still points at the probe.** Restoring it to
  `sensor.wasser_3_flow` is a panel action, so it is the user's.
