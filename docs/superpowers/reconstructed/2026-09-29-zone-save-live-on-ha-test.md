# Zone save sends what changed — live on HA-Test, 2026-09-29

Instance: HA-Test (`mcp__HA-Test__…`, browser pane on the same instance). HA-Prod untouched.
Zone state read with `hass.callWS({type: "irrigation_plus/zones"})` in the browser console, never
through the diagnostics dump. Times are local (Europe/Berlin).

## Test zone

`Grace Test` (id 8), not a distributor member, service mode on the emulator scripts
`script.grace_emu_run` / `grace_emu_stop` (only `input_boolean.grace_emu_valve` switches).
`Test2` (id 3), named in the plan, is a member of distributor `Gardena1`: a distributor cycle
dispatches `_update_frontend` (`_dist_store_update`), so an open page is refreshed around such a
run and the RED would prove nothing. Recorded before the first run: name `Grace Test`, module 0,
bucket −3.7504691045135337, `last_consumed_at` 2026-09-28T23:00:00.392880, ledger empty,
`water_used_total` 8.

## A trap in the harness, not in the code

Runs 1 and 2 on `v2026.09.27b3` ended with the page's copy already fresh. A marker set on the
view element before run 2 was gone afterwards (`sameElement: false`), and the console call that
should have run at 12:54 ran at 13:09: the browser pane was hidden, the page was frozen, and the
HA frontend rebuilt the panel on resume — with freshly fetched zones. With the pane visible
(run 3 onward), the same element stayed, `_fetchData` was never called (wrapped and counted),
and the copy stayed stale as the design says. A live test of a stale page needs a visible page.

## Live RED — `v2026.09.27b3`

| step | time | server | page copy |
|---|---|---|---|
| before run 3 | 13:15:53 | bucket −2.9505, ledger 2 entries, used 16 | bucket −2.9505 |
| after run 3 (`run_zone`, 1 min) | 13:17:51 | bucket −2.5505, ledger 3 (new 13:16:09), used 20 | bucket −2.9505, same element, 0 fetches |
| name edited on the page (`Grace Test` → `Grace Test L`) | 13:18:14 | **bucket −2.9505**, **`last_consumed_at` 13:18:14.640789**, **ledger empty**, used 20 | — |

The run's credit undone, the watermark moved to the save time, the ledger emptied: the defect,
through the panel.

Sibling pages on the same build: two sensor group names edited 113 ms apart (input events on the
page's own fields; the browser tools need ~0.8 s per step, far over the 500 ms window) — only the
second reached the server (`My Sensor Group BB`); the first (`… AA`) was lost.

## The fix build

`v2026.09.29b1`: branch `prerelease/v2026.09.29b1`, commit `daf94beb` on top of the fix branch
head `34471593`; prerelease on the fork, `irrigation_plus.zip` built from the SHA, downloaded
back byte-identical (sha256 `36ae9e00…eb5be1`). Installed on HA-Test through HACS
(`update_information`, `download`), HA-Test restarted; `installed_version` `v2026.09.29b1`,
entry `loaded`, panel shows `v2026.09.29b1` after Ctrl+F5, the view has `_editZoneById` and a
`_pendingEdits` map.

## Live GREEN — `v2026.09.29b1`

| step | time | server | page copy |
|---|---|---|---|
| before the run | 13:25:43 | bucket −2.9505, `last_consumed_at` 13:18:14, ledger empty, used 20 | bucket −2.9505 |
| after the run | 13:27:38 | bucket −2.5505, ledger 1 (13:26:13), used 24 | bucket −2.9505, same element, 0 fetches |
| name edited on the page (`Grace Test L` → `Grace Test LL`) | 13:27:56 | name `Grace Test LL`, **bucket −2.5505**, **`last_consumed_at` 13:18:14**, **ledger entry kept** | — |

Extra checks on the fix build:

| check | result |
|---|---|
| two zones edited 105 ms apart (`Grace Test LLX`, `Test4X`) | both stored; buckets untouched |
| clear the module of `Grace Test`, reload | server `module: null`; the select shows `---Wähle---`, not "null" |
| set the bucket by hand (−1,5 typed in the form) | bucket −1.5, `last_consumed_at` 13:30:46 (the edit), ledger empty — the hand-set rule holds |
| two sensor groups 106 ms apart | both stored |
| two modules 105 ms apart (Static delta 0.1 / 0.2) | both stored |
| two distributors | not possible: HA-Test has one (`Gardena1`) |

## Restored afterwards

`Grace Test`: name, module 0, bucket −3.75 (the form rounds to two decimals; before: −3.7504…);
`last_consumed_at` is the restore time, not the original. Not restorable through the panel (both
on the strip list): `water_used_total` 8 → 24 L and `days_since_irrigation` 2 → 0 from the four
emulator runs. `Test4`: name. Sensor groups: both names. Modules: 2 exactly; 1 `config: null` →
`{}` (the API rejects `null`; `calcmodules/static` treats both as "no delta").

HA-Test stays on `v2026.09.29b1` until the PR is merged or the next build replaces it.
