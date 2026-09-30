# Eifel-Joe#66 / JustChr#181 — the inlet gate live on HA-Test, 2026-09-30

Plan: `docs/superpowers/plans/2026-09-29-distributor-inlet-open-gate.md`, Task 10 (L1–L5) and
Addendum A15. Design: `docs/superpowers/specs/2026-09-29-distributor-inlet-open-gate-design.md`.
The defect this answers: `2026-09-29-distributor-inlet-open-count-repro.md`.

## The build

`v2026.09.30b1`: branch `prerelease/v2026.09.30b1`, commit `7cb8d9c7` on top of the fix branch head
`2c221a7a`. It differs from `2c221a7a` only by the version string in seven files (`manifest.json`,
`const.py`, `package.json`, the four bundles) — checked byte-wise: each file equals its `2c221a7a`
content with the version replaced. Prerelease on the fork, `irrigation_plus.zip` built from the SHA
(199 files, sha256 `a3f6ce00…14bca6b`), downloaded back byte-identical, HTTP 200. Installed through
HACS (`update_information`, `download v2026.09.30b1`); `const.py`, `distributor.py`,
`irrigation.py`, `websockets.py` and `__init__.py` on HA-Test byte-identical with the ZIP (sha256; the
MCP file tool returns UTF-8 as Latin-1, undone before comparing). HA-Test restarted 06:30; entry
`loaded`, HACS `installed_version v2026.09.30b1`.

## Set-up, read before the first step

As in the 2026-09-29 record: Gardena1, id 0, `watering_mode: service` (`script.sonoff_emu_run`,
`seconds`), `inlet_entity: input_boolean.sonoff_emu_valve`, `watch_mode: count`, skip pulse and
pause 15 s, master `input_boolean.test_pumpe`, flow sensor `input_number.hasi_flow_probe`, no
`stop_service`, no notify target; stored outlet 3, `synced`, no active cycle. Members zones 2–7 =
outlets 1–6. Logger `custom_components.irrigation_plus` at `warning`. No `irrigation_plus`
notification.

## Method

* `issue66-work\live\live66.py` over the MCP client of `pr146-work` (endpoint read from a local
  secrets file, never printed; the entry's options never read). Every line carries HA's own clock
  (`ha=`); `last_changed` and `last_triggered` are rendered by HA's template engine.
* Watch mode and wiring changed through the panel's own endpoint, `POST /api/irrigation_plus/distributors`
  with `{id: 0, …}` from the logged-in page — the server path of the panel's save button
  (`async_upsert_distributor` → `_dist_refresh_inlet_watch`).
* Every *Irrigate now* is the websocket `irrigation_plus/irrigate_now` with one `zone_id`.
* Notifications read with `persistent_notification/get`. HA-Test runs in German, so the notification
  is the German catalogue text; the logs of this run show its `ä` as `Ã¤`, an artefact of the MCP
  transport (the notification itself reads correctly in HA-Test's UI, screenshot from the user).
* Logger at `info` from 06:34 until the first restart; a restart resets it to `warning`.

## L1 — `count`

| time | event |
|---|---|
| 06:34:48.253 | declared outlet 4 (`distributor_set_outlet`) |
| 06:34:48.324 | foreign ON (`sonoff_emu_valve`), flow probe 10 L/min |
| 06:34:48.329 | stored outlet 4 → 5 (the advance at the seen on edge) |
| 06:34:51.424 | `irrigate_now` zone 6: `no zones with linked entity and duration > 0` (the direct list is empty) |
| 06:34:51.425 | WARNING `Distributor 'Gardena1' did not start a cycle: inlet input_boolean.sonoff_emu_valve is on` |
| 06:34:51.430 | notification `irrigation_plus_distributor_0`: *Verteiler 'Gardena1' hat einen Bewässerungszyklus nicht gestartet: sein Einlass input_boolean.sonoff_emu_valve war offen.* |
| 06:34:51.434 | Test5 (zone 6): `skipped`, `inlet_open`, trigger `schedule` |
| to 06:35:04 | `watering_now` off, master off, `script.sonoff_emu_run` not triggered (last run 2026-09-29 20:31:08) |
| 06:35:30.448 | foreign OFF, 42.1 s after the ON |
| 06:35:30.451 | Test4 (zone 5): `observed`, 42 s, 2.11 L; `water_used_total` 0 → 2.106 |

Stored 5 = model 5 (declared 4, one off edge), `synced`. **As expected**, and the reverse of H2–H5 of
the 2026-09-29 record: no claim, the stash kept, the right member credited, the position right.

## L2 — `ignore`

Watch mode `ignore` at 06:36:30. Foreign ON 06:36:38.869: stored stays 5 (no listener).
`irrigate_now` zone 6 → WARNING 06:36:43.125, notification replaced 06:36:43.127, Test5 `skipped` /
`inlet_open` 06:36:43.131; no claim. OFF 06:37:01.697: stored 5, model 6 — the desync `ignore` is
documented to leave. Re-synced to 6 at 06:37:21. **As expected.**

## L3 — an open inlet across a restart

**First attempt, discarded.** 06:37:23 `sonoff_emu_valve` opened in `ignore`, 06:38:38 `count`,
restart: the valve came back `off` at 06:39:10.431. The helper is created with `initial: false`
(helper list), so every start closes it — nothing to test. `input_boolean.grace_emu_valve` has no
`initial` and keeps its state across a restart. L3 therefore ran with Gardena1 wired to it
(`inlet_entity: input_boolean.grace_emu_valve`, `run_service: script.grace_emu_run`, no stop service)
and, by the user's decision, in both variants.

**L3a — the on edge unseen.** 06:46:10 wiring as above, `ignore`; 06:46:19 declared 2; 06:46:20.468
grace ON (no listener, no advance); 06:49:41 `count` — the listener is registered over an inlet that is
already on, so no edge; restart, back 06:50:14: inlet `on` (restored), stored 2, `count`, `synced`.

| time | event |
|---|---|
| 06:50:41.820 | WARNING `… inlet input_boolean.grace_emu_valve is on`; notification 06:50:41.824; Test5 `skipped` / `inlet_open` 06:50:41.827; no claim |
| 06:50:54.104 | inlet OFF: stored stays **2**, model 2 → **3** |

**Refused, as expected.** The close then left the stored position **one behind the model, still
`synced`**, and Test2 (outlet 2, open 06:46:20–06:50:54 including the restart) got no observed credit.

**L3b — the on edge seen before the restart.** 06:51:09.915 declared 3; 06:51:09.984 grace ON in
`count` → stored 3 → 4 at 06:51:09.989 (the stash is in memory); restart, back 06:51:47: inlet `on`,
stored 4, `synced`.

| time | event |
|---|---|
| 06:51:54.300 | WARNING refusal; notification 06:51:54.303; Test5 `skipped` / `inlet_open` 06:51:54.306; no claim |
| 06:52:06.654 | inlet OFF: stored 4 = model 4 (declared 3, one off edge), `synced` |

**Refused, as expected.** Position consistent; Test3 (outlet 3, ~57 s open) got no observed credit —
the stash does not survive a restart.

### What L3 measures for Eifel-Joe#69

| case | stored after the close | model | observed credit |
|---|---|---|---|
| L3a: open with no listener (opened in `ignore`, `count` armed while open, then restart) | 2 | 3 — **one behind, `synced`** | lost |
| L3b: on edge seen, then restart | 4 | 4 — consistent | lost (the stash is in memory) |

"Across a restart" has two outcomes: an advance booked at a seen on edge is persisted and survives, the
stash does not. Only an on edge that no listener saw leaves the position behind. Case 2 of the issue
(a close through `closing`) was not run: the emulator has no `closing` state.

## L4 — no false refusal

Sonoff wiring back at 06:52:25 (`count`). 06:52:31.269 declared 5; `irrigate_now` zone 6 → claim,
`watering_now` on 06:52:31.328, master on; `script.sonoff_emu_run` 06:52:36.360, valve ON 06:52:36.365
→ OFF 06:53:37.374 (61 s); Test5 `completed` 61 s, 10.17 L at 06:53:37.404; terminal advance 5 → 6 at
06:53:37.465; `watering_now` and master off 06:53:37.527. Stored 6 = model 6, `synced`; no refusal
warning. **As expected.**

## L5 — the grace after our own close

`input_number.grace_emu_off_delay` 45 (06:54:05); `script.grace_emu_noop` created 06:54:27 (one
`delay: 0`, mode `parallel`; announced first); wiring 06:54:37: inlet `input_boolean.grace_emu_valve`,
`run_service: script.grace_emu_run`, `stop_service: script.grace_emu_noop`, `seconds`, `count`. The
no-op script's `last_triggered` is the time the integration's close command was sent — the stamp.

**Deviation from the plan:** every leg ended after 20 s, not 61 s (run logs: planned 61, actual 20,
3.33 L, `completed`). With a stop service the member can stop, and at the probe's 10 L/min the metered
volume reached the leg's target after 20 s. The run script closes the valve at its own start + 61 + 45 s,
so the inlet kept reporting `on` for ~86 s after the integration's close, not 45 s — the window the
test needs, only longer.

**L5a**

| time | event |
|---|---|
| 06:54:47.254 | declared 2; `irrigate_now` zone 3 (Test2) → claim, `watering_now` on 06:54:47.361 |
| 06:54:52.434 | `script.grace_emu_run`; grace ON 06:54:52.449 |
| 06:55:12.545 | **own close** (no-op `stop_service`); terminal advance 2 → 3 at 06:55:12.606; `watering_now` off 06:55:12.690; the inlet still `on` |
| 06:55:22.697 | `irrigate_now` zone 4 (Test3) → **claimed**, `watering_now` on: **10.15 s after the own close**, inlet `on` |
| 06:55:28.084 | `script.grace_emu_run` again (after the master settle) |
| 06:55:48.131 | second own close; terminal advance 3 → 4 |
| 06:57:14.108 | grace OFF |

Test2 `completed` 06:55:12.487, Test3 `completed` 06:55:48.080 (20 s, 3.33 L each). No refusal
warning. **As expected: the grace held.**

**L5b**

| time | event |
|---|---|
| 06:58:10.246 | declared 6; `irrigate_now` zone 7 (Test6) → claim 06:58:10.393 |
| 06:58:15.560 | `script.grace_emu_run`; grace ON 06:58:15.603 |
| 06:58:35.754 | **own close**; terminal advance 6 → 1 at 06:58:35.896; `watering_now` off 06:58:36.050 |
| 06:59:10.846 | `irrigate_now` zone 2 (Test1) → WARNING refusal, **35.09 s after the own close**, inlet `on`; notification 06:59:10.849; Test1 `skipped` / `inlet_open` 06:59:10.853; `watering_now`, master and the run script untouched |
| 07:00:01.698 | grace OFF |

Test6 `completed` 06:58:35.701 (20 s, 3.33 L). **As expected: refused once the grace was over.**

## The log over the whole run

The refusal warning appears exactly five times — L1, L2, L3a, L3b, L5b — and never in L4 or L5a.
Nothing else from the integration but known noise: PirateWeather `429` bursts after each store write
(rate limit of the weather module), `No weather data to parse` after each restart, Home Assistant's
`via_device` deprecation and the custom-integration notice.

## Restored (07:00:40–07:00:59)

Wiring back to `input_boolean.sonoff_emu_valve` / `script.sonoff_emu_run`, no stop service,
`seconds`, `count` — the distributor record equals the one read at the start except the position,
which was then set: stored outlet 3, `synced`. `script.grace_emu_noop` deleted;
`grace_emu_off_delay` 0; both valves and the master off, probe 0; logger `warning`; notification
`irrigation_plus_distributor_0` dismissed.

**Left as is:** HA-Test runs `v2026.09.30b1` (before: `v2026.09.29b1`, the zone-save fix since merged
upstream as `0b9a71bd`, on which this build stands). The members' history and credits: Test4 +2.106 L
(observed), Test5 +10.17 L, Test2, Test3, Test6 +3.33 L each; `skipped` / `inlet_open` entries: Test5
×4, Test1 ×1. The buckets are recalculated nightly.

## Files

`docs/superpowers/probes/2026-09-30-inlet-gate-live/`: `live66.py` (the helper), `session.log` (raw
record of every helper call from 06:39 on), `l1.log`, `l2.log`, `l3-first-attempt.log` (L2's re-sync
and the discarded L3 attempt). `live66.py` imports `mcp_test` from `pr146-work` (not archived: it reads
its endpoint from a local secrets file) and `hasi_read` (archived with the 2026-09-29 record).
