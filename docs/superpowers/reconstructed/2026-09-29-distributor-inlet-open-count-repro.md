# Eifel-Joe#66 / JustChr#181 — reproduction, count mode, HA-Test, 2026-09-29

**Build on HA-Test:** `v2026.09.29b1` (`daf94beb`). Against `1876aa03` it changes only the zone
save path (`websockets.py` zone view, `store.py` maximum-bucket clamp on panel saves, comments in
`__init__.py`, the version in `const.py`). `distributor.py`, `irrigation.py`,
`observed_watering.py`, `run_state.py` and `actuate.py` are identical to `1876aa03`
(`git diff --stat 1876aa03 daf94beb`).

**Setup (read before the run):** distributor Gardena1, id 0, `watering_mode: service`
(`script.sonoff_emu_run`), `inlet_entity: input_boolean.sonoff_emu_valve`, `watch_mode: count`,
`skip_pulse_seconds: 15`, `pause_seconds: 15`, `use_master: true` (`input_boolean.test_pumpe`,
settle 5 s), `flow_sensor: input_number.hasi_flow_probe`; `observed_watering_enabled: true`.
Six members, zones 2–7 = outlets 1–6. Test4 (zone 5, outlet 4) carries a soil-moisture veto
(`sensor.basilikum_soil_moisture`, threshold 30), so the target was Test5 (zone 6, outlet 5):
due, duration 61 s, bucket −0.6094, no veto.

**Trigger:** websocket `irrigation_plus/irrigate_now` with `zone_id: 6` — `async_irrigate_now`,
the method behind *Water all zones*, narrowed to one member: the direct list is empty (log
14:30:55.094 "irrigate_now: no zones with linked entity and duration > 0"), then
`_dispatch_distributor_cycles([6])` → `_dist_eligible_for_run` (`:524`) →
`async_run_distributor_cycle(only_zone_ids=[6])` → claim → sweep. *Water all zones* passes the
same gates with `only_zone_ids=None`; it was not used because it would also have run the direct
zone "Grace Test" (563 s).

**Ring model:** the emulator has no ring. The model is the one the code documents
(`distributor.py:1744-1768`): the ring steps one outlet on every inlet OFF edge. The physical
start was declared with `distributor_set_outlet(0, 4)`.

## Recorder timeline (local time, UTC+2)

```
14:29:00.000  valve off · stored outlet 3 · watering_now off · master off · probe 0.0 · script off
14:30:14.563  stored outlet 3 → 4        (distributor_set_outlet: declared physical start 4)
14:30:14.686  valve ON                   (foreign open; by the model, outlet 4 flows)
14:30:14.690  stored outlet 4 → 5        (count mode advances at the ON edge, distributor.py:954)
14:30:14.745  probe 10.0 L/min           (water flowing)
14:30:55.110  watering_now on            (irrigate_now → cycle claimed while the inlet is open)
14:30:55.114  master on
14:31:00.135  script.sonoff_emu_run on   (opens an inlet that is already on: no edge)
14:32:01.143  valve OFF                  (the only OFF edge: by the model the ring steps 4 → 5)
14:32:01.155  script off
14:32:01.335  stored outlet 5 → 6        (terminal advance, distributor.py:1774)
14:32:01.359  master off
14:32:01.414  watering_now off
14:32:01.677  probe 0.0
```

The valve has exactly one ON and one OFF in the recorder (`ha_get_history`,
`significant_changes_only: false`), nothing between them.

## Results

| # | Prediction from reading `1876aa03` | Measured |
|---|---|---|
| H1 | count mode advances the stored position at the foreign ON edge | ✓ 4 → 5, 4 ms after the ON |
| H2 | a cycle is claimed and runs over the open inlet; its open makes no edge | ✓ claimed 40.4 s into the foreign open; one ON, one OFF |
| H3 | the leg is credited to the zone at the advanced position | ✓ Test5 (zone 6): new run 14:32:01, `distributor`, 61 s, **10.17 L**, `completed`; `water_used_total` 1215.15 → 1225.32; bucket −0.6094 → 0.0 |
| H4 | the zone that actually received the water gets nothing | ✓ Test4 (zone 5): no new run-log entry, `water_used_total` 0 → 0, although by the model its outlet flowed 106.5 s (14:30:14.686–14:32:01.143) |
| H5 | afterwards the stored position is one ahead of the ring, still `synced` | ✓ stored 6, model 5 (4 + one OFF edge); `position_state: synced`, `commissioning_confirmed: true` |

**Consequence (from the model, not measured beyond this run):** nothing prompts a re-sync, so
every later cycle waters and credits the outlet after the one it names, until someone re-syncs.

## Restored afterwards (HA-Test)

`distributor_set_outlet(0, 3)` (stored position as found), logger `custom_components.irrigation_plus`
back to `warning`; valve, master and probe off/0. Left as is: Test5's credit (+10.17 L,
bucket 0.0) — additive total, the bucket is recalculated nightly.

## Not run

- `ignore` mode (the default) — needs `watch_mode` changed in the panel (HTTP view, not reachable
  over MCP). Expected from reading: no advance, the member at the flowing outlet is watered on top of
  the foreign run, positions stay consistent.
- An inlet open without a seen off→on edge (HA restart while open, `unavailable` → on) — needs a
  restart; reading only (`distributor.py:1013-1015`).

## Files

In `docs/superpowers/probes/2026-09-29-inlet-open-repro/`:
`repro_count.py` (sequence), `repro-count-run2.log` (1-s samples), `history-run2.txt` (recorder),
`evaluate-run2.txt` (run logs, store), `hasi_read.py`, `evaluate_run.py`, `baseline-zones-5-6.txt`.
Run 1 (`repro-count-run1.log`) aborted at its first read, before any write (template result parsing).
The scripts import the local MCP client `pr146-work\live\mcp_test.py`, which is not archived: it
reads its endpoint from a local secrets file.

Design that follows from this record:
`docs/superpowers/specs/2026-09-29-distributor-inlet-open-gate-design.md`.
