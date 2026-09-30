# Weather buffer: one frame, and what the store holds

**Revision 4** of the weather-buffer time work. It **supersedes Revision 3**
(`specs/2026-09-28-weather-buffer-aware-writers-design.md`) **and its plan**
(`plans/2026-09-28-weather-buffer-aware-writers.md`), which must **not** be executed —
the evidence below shows it regresses a path that is correct today. Revision 3 and the
2026-09-21 spec stay authoritative only for what this one does not restate: the problem
statement and `D4`/`R3-3` (no detection).

**Date:** 2026-09-28 · **Issue:** `Eifel-Joe#22` · **Upstream:** `JustChr#160`
**Base:** `upstream/master` = `1876aa03` (v2026.09.27), re-fetched and verified
**Branch:** `fix/weather-buffer-aware-writers` (worktree `issue22-work/wt`), still at `1876aa03`,
no production code changed.
**Line numbers** refer to `1876aa03`.

**Status:** decided on everything except the on-disk form of the five stamps (R4-3), which is
JustChr's convention to decide. Recommendation: **Variant B**. **No plan until he answers.**

> **Addendum 2026-09-30 (end of this file) — where it differs, it wins.** JustChr chose **B**.
> The migration keys on the store's **minor** version (14.1 → 14.2), not 14 → 15: since HA
> 2026.3 a higher *major* version makes a rolled-back release fail setup. Line numbers moved
> to `0b9a71bd` in three files only (A6).

---

## Why Revision 3 cannot be built as planned

Measured by running master's own functions, with only `coerce_stamp` swapped for Revision 3's
Task-1 body where a row says so. Process at UTC, HA at Europe/Berlin, 1.0 h of real time
(last calculation 10:00Z = 12:00 Berlin, now 11:00Z = 13:00 Berlin). Evidence files in
`docs/superpowers/probes/` (see "Evidence").

| Probe | `1876aa03` today | with Rev-3 Task 1 | after Rev-3 Tasks 4–6 (store aware) |
|---|---|---|---|
| P4 — daily calculation, `aggregate_window` as `calculation.py:331-357` calls it | **1.0 h ✓** | **3.0 h** — regression | `TypeError` at `weather_aggregate.py:319` (`_hour_multiplier`) |
| P1 — live estimate, `_window_anchor` + `now_local` | 3.0 h (the reported bug) | **5.0 h** | 3.0 h, hourly rows running to 14.5 — two hours into the future |
| P2 — `_prune_mapping_buffer`, legacy rows, aware `now` | ok | ok | `TypeError` |
| P3 — `merge_or_append_mapping_reading`, legacy newest row, aware timestamp | ok | ok | `TypeError` |
| P6 — Revision 3's own end-to-end pin 2 (`min(hours) >= 12.0`) | — | **green**, with a 3.0 h window and rows 12.5 / 13.5 / 14.5 | — |

**Root cause.** Today `coerce_stamp(…, STAMP_FROM_STORE)` returns a naive value untouched, so
applying it twice, or not at all, is harmless. Revision 3's Task 1 makes it **lift** a naive
value from the process zone into HA's. From that moment every stored stamp must be converted
**exactly once**, and four classes of site break that (inventory IDs in brackets):

1. **The watermark is converted only inside `select_window`** (`weather_aggregate.py:167`,
   local rebinding). `aggregate_window` and `_effective_series` go on with the raw parameter
   at `:382`, `:414`, `:415`, `:729`, `:731` — the window bounds, the multiplier and the
   re-stamped boundary row (F-01, D.2–D.5). That is what turns the correct daily 1.0 h into
   3.0 h: rows are lifted, the watermark the window is measured from is not.
2. **The live path hands in values that are already HA-local** — `anchor` from
   `_parse_stored_as_ha_local` (`live_estimate.py:246-250`) and `now_local` from
   `coerce_stamp(dt_util.now(), STAMP_FROM_CLIENT)` (`:275`) — and the entry points convert
   them again at `:167`, `:368`, `:936`, `:1131` (F-02, matrix rows M3, M4, M7, M9).
3. **Eleven readers parse raw and never convert**: `calculation.py:331, :398, :808, :865,
   :975, :1116`, `store.py:1921, :1985`, `live_estimate.py:246, :249`, `auto_calc.py:135`
   (F-03, Section A). Against an aware or mixed store they raise at `store.py:1939, :1989,
   :1990` and `calculation.py:392, :400, :403, :407, :1123`. Only the calc-all loop
   (`calculation.py:460`, ERROR) and the live estimate (DEBUG) catch it; on the sensor-event
   path HA's dispatcher logs an ERROR and **the reading is lost**; prune, the ledger guard and
   the zone-POST calculate path catch nothing.
4. **Three of Revision 3's "16 persisting writers" persist nothing** —
   `__init__.py:1429` (solar clamp), `calculation.py:379` and `:934` (compare-only defaults) —
   and every real writer that holds a `now` shares it with comparisons
   (`calculation.py:432/:498`, `continuous_update.py:252/:378/:521`; F-05). Moving them to
   `dt_util.now()` makes the internals aware through the back door, which R3-1 rejected.

**Two further findings, independent of the plan:**

- **`_process_timezone()` is a fixed offset** — `datetime.now().astimezone().tzinfo`
  (`helpers.py:1015`) is today's offset, not the zone. A legacy stamp from before a DST change
  is read an hour off (P3 in the inventory: `2026-01-15T12:00Z` → 14:00 instead of 13:00), and
  the buffer keeps seven days (F-04).
- **R3-2's downgrade argument is inverted.** It skipped the `STORAGE_VERSION` bump so that a
  HACS rollback would not meet aware stamps. But the writers produce aware stamps within
  minutes of the upgrade, bump or not, and `1876aa03` then raises in the daily calculation
  (P4, right column: `now - watermark` with a naive `now` and an aware watermark). The
  calculation that would overwrite the watermark is the one that raises, so it does not heal.

**What Revision 3's pins would have missed.** Pin 1 checks `coerce_stamp` arithmetic against a
hand-built `now` and never enters an entry point. Pin 2 asserts `min(hours) >= 12.0`, which
holds for a 3.0 h window reaching into the future (P6). Neither calls a function that reads
the store.

---

## R4-1: One internal frame — naive HA-local, everywhere (both variants)

Every datetime on the buffer paths is naive HA-local — including every `now`. Named once:

```python
def local_naive_now() -> datetime:  # helpers.py, beside coerce_stamp
    return dt_util.now().replace(tzinfo=None)
```

It replaces the bare process clock at **19 sites**, classified from the inventory's Section C:

| Kind | Sites |
|---|---|
| persisting (13) | `calculation.py:267, :432, :498` · `continuous_update.py:252, :378, :521` · `store.py:1653` · `__init__.py:1506, :1516, :1632, :1644, :1799, :2023` |
| compare-only (3) | `calculation.py:379` (prune default), `:934` (`calculate_module` default), `__init__.py:1429` (solar clamp) |
| entry-point defaults (3) | `weather_aggregate.py:370, :938, :1133` — `weather_aggregate.py` keeps its `homeassistant`-free imports by importing the helper |

**The solar clamp is a second, unnamed instance of the expensive half.**
`_clamp_solar_reading` pairs the process clock (`__init__.py:1429`) with HA's offset (`:1430`)
and hands both to `clamp_solar_to_clear_sky` (`helpers.py:814`), which reads `when.hour` —
the same mismatched pair `calculation.py:796` warns about, applied to the ingest clamp. On an
affected install the clear-sky ceiling is computed for the wrong solar hour and a legitimate
reading can be clamped. `local_naive_now()` makes the pair consistent.

NOT-TO-DO: aware internals (R3-1's reasoning stands — a naive/aware mix inside the blanket
`except` silently disables the live estimate).

## R4-2: A legacy stamp is read at its own offset (both variants)

`_process_timezone()` returns `dateutil.tz.tzlocal()` instead of today's fixed offset:
the process zone **with its DST rules**, so each legacy stamp gets the offset that was valid
when it was written. `python-dateutil` is already a manifest requirement
(`manifest.json:18-21`) and already imported (`websockets.py:8`) — no new dependency. The
function stays the test seam; the suite monkeypatches it exactly as today.

## R4-3: The on-disk form — the open decision

| | **A — aware on disk** (JustChr's convention) | **B — naive HA-local on disk + one-time migration** |
|---|---|---|
| Code | 13 writers, 3 compare-only `now`s, 3 defaults, 11 readers in 4 modules (`calculation`, `store`, `live_estimate`, `auto_calc`), 4 entry points in `weather_aggregate` | 13 writers, 3 compare-only `now`s, 3 defaults, one migration step; readers unchanged |
| `TypeError` class | stays possible: any missed site mixes naive and aware, and the store is mixed for 7 days after the upgrade | cannot arise: nothing on these paths is aware (the aware ledger `ts` is already flattened, `calculation.py:64-65`) |
| HACS rollback | daily calculation raises permanently (P4) | one window misread by the offset on an affected install, then heals |
| Fixture churn | large (R2-3 measured ~100 at process UTC on an older base) | small — `STAMP_FROM_STORE` keeps returning naive values untouched |
| Self-describing stamps | yes | no — a change of HA's **own** configured zone misreads up to 7 days of buffer |
| JustChr's reasons | 1, 2, 3 | 1 and 3 (HA-local, not the process clock); not 2 (the ledger is aware) |

JustChr's reason 1 ("HA's configured zone is the one the user chose") and reason 3 (`dt_util`
so the integration need not care about the process clock) hold for both. Only reason 2 (the
bucket ledger is already aware) is specific to A. The downgrade consequence was not known when
he decided.

### Variant B (recommended)

1. **Migration 14 → 15** in `MigratableStore._async_migrate_func` (`store.py:603-862`), run
   when `old_version < 15`. One pass over the five fields of `D3`'s allowlist:
   `zones[i].last_calculated`, `.last_consumed_at`, `.last_updated`,
   `mappings[i].data[j].retrieved`, `mappings[i].data_last_updated`. **Watermark and buffer in
   the same pass** (`D3`'s hard rule; they live in the same file: `store.py:1560-1571`).
   - naive → read in the process zone at its own offset (R4-2) → HA-local → naive;
   - aware (should not exist) → `dt_util.as_local` → naive;
   - unparseable or `None` → left exactly as found (the readers already handle both);
   - **string in, string out** (`isoformat()`): `async_load` converts nothing
     (inventory Section E), so the loaded shape must not change.
   - The assumption goes here as a comment, with the rejected detection (`D4`) and the
     rejected "repair" to `DEFAULT_TIME_ZONE` — what JustChr asked for in `#160`.
2. **`coerce_stamp`**: `STAMP_FROM_STORE` keeps returning a naive value untouched — after the
   migration a stored naive value *is* HA-local. Its aware branch changes from the process
   zone to `dt_util.as_local`. The two provenances then behave alike. **Both names stay**,
   with a docstring saying why they now coincide; collapsing them is JustChr's call, not part
   of this fix.
3. **`_parse_stored_as_ha_local`** becomes correct as written: its "⚠️ MISMATCHED" docstring
   is rewritten, and `test_a_stored_stamp_is_still_read_in_ha_local_today` — pinned as "THE
   DEFECT … meant to be replaced" — is inverted.
4. **Readers stay**, because after the migration each compares HA-local with HA-local:
   `calculation.py`'s raw readers against a `local_naive_now()` `now`; `store.py:1921/:1985`
   against the continuous-update timestamps; the live anchor against `now_local`;
   `auto_calc.py:135` against its HA-local cutoff; `sensor._to_aware_datetime` attaches HA's
   zone (now right); `websockets._safe_parse_datetime` sorts one scale. B also removes F-07
   (daily and live twins disagreeing on the frame of pending credits).
5. **Rollback and re-upgrade, documented, not handled.** HA calls the migrate function on any
   version mismatch (`homeassistant/helpers/storage.py:391-419`); the old function passes an
   unknown version through (none of its branches match 15) and saves as 14. Old code then reads
   HA-local stamps as process-local: one window off by the offset on an affected install, no
   crash. A later re-upgrade migrates again and shifts once more: again one window.

### Variant A (if JustChr keeps "aware")

- **The read boundary:** every stored stamp is converted exactly once, where it leaves the
  store, with `STAMP_FROM_STORE` (legacy naive lifted per R4-2; aware via `as_local`); nothing
  already in the frame is converted again.
- **`weather_aggregate`'s `watermark` and `now` are already in the frame** — a third
  provenance, `STAMP_IN_FRAME` (naive untouched, aware → `as_local`), converts them **once**
  per entry point, and the converted watermark is what `:382`, `:414`, `:415`, `:729`, `:731`
  use. Row stamps keep `STAMP_FROM_STORE`.
- **The eleven readers** of root-cause item 3 move to `STAMP_FROM_STORE`;
  `_parse_stored_as_ha_local` becomes that call (its own NOT-TO-DO says it moves with the
  writers).
- **Writers:** internal `now` stays naive (R4-1); the persisted value is aware —
  `dt_util.as_local(now)` where it must equal an internal `now` (the calc-all watermark), else
  `dt_util.now()`.
- **Release note:** "no downgrade across this version" (P4).
- **Mixed-store pins** for prune, merge and `_hour_multiplier`, because the store holds both
  shapes for up to `BUFFER_RETENTION`.

## R4-4: No detection — `D4`/`R3-3` unchanged

Restated in one line because it is the part JustChr asked for: a DST fall-back and a
container-`TZ` fix have byte-identical signatures in a naive series, a future clamp is
direction-blind, and pairing naive against aware has no aware stamps to pair on a fresh
install. The residual error is Δ/24 of one window and heals.

## R4-5: `STORAGE_VERSION` — R3-2 revised

R3-2's reason (downgrade safety) is refuted above. Under **A** there is still no bump — the
legacy branch is read-time, and a bump would add nothing against the rollback hazard. Under
**B** the bump *is* the fix, and it is the downgrade-benign shape. The project convention
"`STORAGE_VERSION` stays put" (`store.py:473` and siblings) covers additive fields; this is a
value migration.

---

## End-to-end criterion (both variants)

A matrix, not two assertions: **2 paths × 2 store states**, exact values, through the real
functions that read the store.

- **Paths:** daily — the `calculation.py` functions that read the watermark themselves
  (`_aggregate_for_zone` → `aggregate_window`, `_hourly_et_for_zone` → `hourly_eto_priced`);
  live — `_window_anchor` → `_aggregate_live_window` and `_buffer_hourly_et`.
- **Store states:** legacy (a v14 payload with process-local naive stamps, loaded through the
  real `async_load`, i.e. through the migration under B) and fresh (stamps produced by the real
  writers).
- **Expected:** window = **1.0 h**, hourly row hours = **`[12.5]`**, `tz_offset_h` = **2.0**.
- **RED on `1876aa03`, visibly as an offset:** live 3.0 h and rows from 10.5. On the daily
  path the window is already right today, so there the **row hour** must go red — that is the
  expensive half and the reason this is a matrix.

Supporting pins: the migration (per-stamp offset across DST, watermark and buffer in one pass,
runs only below 15); the solar clamp at an hour where two hours move the clear-sky ceiling
measurably; `coerce_stamp` aware → HA-local; the inverted pins
(`test_live_estimate_time_provenance.py::test_a_stored_stamp_is_still_read_in_ha_local_today`,
`test_weather_aggregate.py::…::test_an_aware_stamp_is_read_in_the_process_zone_not_has`).
Verification must call the changed function (memory `verification-must-exercise-the-change`).

## Measurement

- **Every suite run under `TZ=UTC`** — the CI mirror. `TZ=UTC` sets the process zone on
  Windows (verified). The `hass` fixture sets HA to **US/Pacific**
  (`pytest_homeassistant_custom_component/common.py:262`), so on CI every `hass` test already
  runs with two different zones; locally without `TZ=UTC` the process would be Berlin and the
  shifts would differ from CI.
- **Baseline** on `1876aa03` under `TZ=UTC`: 7 failed / 3455 passed / 9 skipped / 367 errors,
  composition identical to the Berlin run (0/0 difference). File:
  `issue22-work/measure/baseline-1876aa03-tzutc.txt`. Only the delta counts; filter with the
  directory, `^(FAILED|ERROR) tests/`.

## Scope (Variant B)

**In:** `helpers.py` (`local_naive_now`, `_process_timezone`, `coerce_stamp`'s aware branch and
docstring) · `store.py` (`STORAGE_VERSION` 15, migration step, writer `:1653`) ·
`calculation.py` (5 sites) · `continuous_update.py` (3) · `__init__.py` (7, incl. the solar
clamp) · `weather_aggregate.py` (3 defaults) · `live_estimate.py` (`_parse_stored_as_ha_local`
docstring) · the comments the inventory lists in F-13 that the change makes false.

**Out, deliberately:**
- `weathermodules/*.py` (11 in-process TTL comparisons) and `generated_at` (4 display sites).
- Display readers `sensor.py`, `websockets.py`, the frontend — under B they become consistent
  by themselves.
- The raw-watermark uses in `weather_aggregate` (`:382` etc.): under B no aware or string
  watermark reaches them. (Under A they are in scope.)
- A stamp inside `data_last_entry` (F-12): unverified, and `aggregate_window` skips the key.
- Collapsing `STAMP_FROM_STORE`/`STAMP_FROM_CLIENT`; any detection, reconstruction or clamp.
- The runtime process-vs-HA zone warning and the `exc_info=True` one-liner — own PRs.

## Traps (measured)

- The store rule stops being idempotent the moment it transforms naive input. Before touching
  it, list every value that can reach it twice.
- `async_load` converts nothing: stamps are `str` after a restart and `datetime` after the next
  write. The comment at `store.py:1980-1984` claims watermarks are converted — they are not
  (F-08).
- The domain-move import copies the store as raw bytes (`migrate_domain.py:547`); under B the
  version-based migration covers it.
- `docs/superpowers/` is not gitignored. Never stage it on the feature branch (it names
  `Eifel-Joe#22`); not in `.git/info/exclude` either. Before any push:
  `grep -rn "Eifel-Joe" custom_components/ tests/` must be empty.
- No `nohup … &` for suite runs; before any verdict check that the run collected tests.

## Evidence

In `docs/superpowers/probes/`, run against a checkout of `1876aa03`. Probe numbers P1–P6 in
this spec are its own; the inventory numbers its in-memory probes separately (its
Appendix 2), and is cited here by its section and finding IDs (A-…, D.…, F-…) instead.
Re-run on 2026-09-28 from the archived copies: result lines identical to the recorded file.

- `2026-09-28-weather-buffer-frame-probe.py` — P1–P4 (real functions, Rev-3 Task-1 body
  swapped in where stated)
- `2026-09-28-weather-buffer-plan-pin-probe.py` — P6
- `2026-09-28-weather-buffer-probe-results.txt` — the output of both
- `2026-09-28-weather-buffer-stamp-inventory.md` — every read, write and comparison of the five
  stamps, with the try/except that would or would not catch a `TypeError` (191 `file:line`
  references checked against the source, 0 mismatches)

## Not part of this work

- The runtime check (process zone ≠ HA zone → warning), carried from Revision 2. Own PR.
- `exc_info=True` on `_intraday_for_zone`'s blanket `except`, plus first failure per refresh at
  WARNING. JustChr said yes, independent of both PRs. Own PR.
- The `TZ=` documentation — shipped as `JustChr#164`.

---

## Addendum 2026-09-30 — B chosen; the migration keys on the minor version; lines on `0b9a71bd`

Where this addendum differs from the text above, **it wins**. Nothing above is deleted, so the
reasoning that led here stays readable. Variant A and its list are out.

### A1 — The decision: Variant B

On `JustChr#160` (comment `5884685278`, 2026-09-29 06:08 UTC, account `JustChr`, OWNER) JustChr
chose **B** and took the scope as R4-1, R4-2 and "Variant B" list it: the five fields in one
pass, watermark and buffer together, legacy stamps read as process-local at their own offset;
writers on `dt_util.now().replace(tzinfo=None)`; `_process_timezone()` on `tzlocal()`; the solar
clamp; the matrix, red on master. An automated reply an hour earlier
(`watchtower-justchr[bot]`, `5884061101`) had answered as if A were chosen; he retracted it in
the same comment. His two additions, both for the migration comment (A5) and the release notes:

- the process-`TZ` assumption, in his words: a process `TZ` changed between writing and
  upgrading is misread;
- the cost R4-3 names: after the migration, a change of HA's **own** configured zone misreads
  up to a week of buffer.

### A2 — The migration keys on the minor version: 14.1 → 14.2

Supersedes B.1's "Migration 14 → 15 … run when `old_version < 15`", B.5, R4-5 and the Scope
line "`STORAGE_VERSION` 15".

**What B.5 got wrong.** It said a rolled-back release opens the migrated file, its migrate
function passes the unknown version through, and HA saves it as 14. That was checked against
the local HA 2024.12.5 only. Since **HA 2026.3.0** (home-assistant/core#164340)
`Store._async_load_data` raises `UnsupportedStorageVersionError` when the stored **major**
version is above `max_readable_version`, which defaults to the store's own version
(`homeassistant/helpers/storage.py:282-283` and `:441-443` at the tags 2026.3.0 and 2026.4.0,
absent at 2026.2.0 — read at the tags). HASI passes no `max_readable_version` (`store.py:903`)
and loads the store unguarded during setup (`__init__.py:191` → `store.py:907`). After
14 → 15, a rollback to 09.17 on current HA therefore fails setup until the user upgrades again
or restores a backup. We first said 2026.4; JustChr corrected it to 2026.3
(`5894821423`), and the files at the tags confirm him.

**What holds instead.** The guard compares the major version only. A differing minor version
sends the file through the migrate function, and HA passes the minor only to a migrate
function with **three** parameters: `len(inspect.signature(self._async_migrate_func).parameters)
== 2` → `(version, data)`, else `(version, minor_version, data)` (`storage.py:453-463` at
2026.3.0/2026.4.0, `:409-419` at 2024.12.5). A file without `minor_version` is read as minor 1
(`:431-433` resp. `:391-393`). So:

- `STORAGE_VERSION` stays **14**. A new `STORAGE_MINOR_VERSION = 2` is passed as
  `minor_version=` to `MigratableStore` (`store.py:903`). The convention "`STORAGE_VERSION`
  stays put" (`store.py:473` and siblings) is kept.
- The stamp step runs when `(old_major_version, old_minor_version) < (14, 2)`: every store
  written before this change, older majors included. The literal `(14, 2)` names the version at
  which the stamps changed meaning; it must not be spelled with `STORAGE_VERSION` /
  `STORAGE_MINOR_VERSION`, which will move again.
- **Rollback to 09.17** — JustChr checked it (`5894821423`), re-read here on `6d9c69e6`: 09.17's
  `_async_migrate_func(self, old_version, data)` has two parameters, so HA calls it with
  `(14, data)`. Its version branches are `== 3` and `<= 4` … `<= 13`; none runs, only the
  always-run config tail (setdefaults, strip of unknown config keys). Zones and buffers pass
  through, and HA saves the file back as 14.1 (`async_save` writes the store's own
  `minor_version`, `storage.py:468-475` at 2026.4.0). The old code then reads HA-local stamps as
  process-local: **one window misread by the offset on an affected install, then healed** —
  the behaviour JustChr based the decision on.
- **Re-upgrade** after such a rollback: the file is 14.1 again, the step runs again and shifts
  every stamp in it — those the rolled-back release wrote (correctly) and those the new release
  had written before the rollback (a second time): one more window. Documented (A5), not
  handled.
- CI's floor HA (2025.5.0) and the local test HA (2024.12.5) have no guard; the minor route
  behaves the same there.

### A3 — The migrate function's shape

HA picks the call form by the parameter count, so seeing the minor needs the three-parameter
form. The existing body stays **unchanged** under a new name, `_async_migrate_major(self,
old_version, data)`; a new `_async_migrate_func(self, old_major_version, old_minor_version,
data)` runs it and then the stamp step. Rejected: changing the signature in place.

| | split (chosen) | signature changed in place |
|---|---|---|
| 24 direct two-argument calls in 8 test files (the major steps v3–v13), plus 2 docstrings naming the function | renamed to `_async_migrate_major`; every assertion unchanged | each gets a `1` as minor and then also runs the stamp step on a fixture written for a major step |
| A4's test | calls the body 09.17 runs at version 14 | would need its own copy of it |
| diff in `store.py` | one renamed `def`, one new method | one changed `def` |

`test_import_storage_visibility.py:76` defines its own three-parameter pass-through and is not
affected.

### A4 — JustChr's test: a 14.2 store through the two-argument path

His request (`5894821423`): a test that feeds a 14.2 store through the **two-argument** path,
the way 09.17 will see it, and asserts that the buffers come back untouched.

- **The store as 09.17 opens it:** a test-local subclass of `MigratableStore` with major 14,
  minor 1 (HA's default) and a **two-parameter** `_async_migrate_func(old_version, data)` that
  records its arguments and delegates to `_async_migrate_major`. HA's own dispatch picks the
  path.
- **The 14.2 file is produced, not written by hand:** a 14.1 document goes through the real new
  store's `async_load` — the migration runs, HA saves 14.2 into `hass_storage` — and that saved
  file is what the 09.17-shaped store then loads.
- **Asserted:** the migrate function ran once, with `(14, <data>)` — the major only; zones and
  mappings come back equal to the 14.2 file (the three zone stamps, every row's `retrieved`,
  `data_last_updated`); the file is saved back as version 14, minor 1; nothing raises.
- **What it cannot show, said in its docstring:** it runs today's `_async_migrate_major`, not
  09.17's source. Diffed on 2026-09-30: 09.17's function (`6d9c69e6`, `store.py:593-846`) and
  today's (`0b9a71bd`, `:606-864`) differ by one config `setdefault`
  (`CONF_FORECAST_WEATHER_ENTITY`) and in nothing that touches zones or mappings. Rejected:
  vendoring 09.17's function into the tests — 254 lines, and it would still hydrate against
  today's `Config` and constants, so it would not be 09.17 either. Locally and on CI's floor
  job there is no guard; CI's job on the newest HA runs this test through the guarded code.

### A5 — The migration comment

One comment beside the step, after skill `code-doku`: **Wurzel** — legacy stamps were written
by a bare `datetime.now()`, so they are process-local, and every reader compares them with
HA-local values. **Fix** — one pass over the five fields: naive → process zone at its own
offset (`tzlocal()`, R4-2) → HA-local → naive; aware → HA-local; string in, string out;
anything unparseable, `None` or not a string left exactly as found. **Assumptions**, both from
A1: a process `TZ` changed between writing and upgrading is misread; after the migration a
change of HA's own zone misreads up to a week of buffer, because the stamps carry no offset.
**Rollback and re-upgrade** as in A2. **NOT-TO-DO:** detection (`D4`, R4-4); a "repair" to
`DEFAULT_TIME_ZONE` (`dt_util.as_local` attaches HA's zone to a naive value and cannot know
the process's); a major bump (A2). **siehe** the tests. The PR body names both assumptions for
the release notes.

After B, `_process_timezone()` has one caller left, this step (`coerce_stamp`'s aware branch
moves to `dt_util.as_local`, B.2); its docstring says so.

### A6 — Line numbers: `1876aa03` → `0b9a71bd`

`upstream/master` = `0b9a71bd` (re-fetched 2026-09-30). Only three backend files changed
(`git diff --stat`): `store.py` (+4 lines after 1680, a comment), `__init__.py` (+2 after 2007,
a comment), `websockets.py` (+9 after 380, +23 after 382, the zone POST). Every other cited file
is unchanged. Scripted check of every `file:line` reference in this spec and in the inventory
(718, repeats and continuation references `, :NNN` included): 614 unchanged, 80 moved with
identical text, **0 mismatches** (`probes/2026-09-30-weather-buffer-remap-refs.py`, output
beside it). The parser skips a continuation after a word (`:312-317 accept, :366-382`);
`websockets.py:382` checked by hand: now `:391`, same text. The moves that matter here:

| at `1876aa03` | at `0b9a71bd` |
|---|---|
| `store.py:1921`, `:1939`, `:1985`, `:1989`, `:1990`, `:1980-1984` | `:1925`, `:1943`, `:1989`, `:1993`, `:1994`, `:1984-1988` |
| `__init__.py:2023` (writer), `:2017-2022` (its comment), `:2109`, `:2162` | `:2025`, `:2019-2024`, `:2111`, `:2164` |
| `websockets.py:382`, `:384`, `:385`, `:489-493`, `:566-570`, `:577-589` | `:391`, `:416`, `:417`, `:521-525`, `:598-602`, `:609-621` |

Unchanged and exact: `store.py:198`, `:603-862`, `:903`, `:907`, `:1653`; `__init__.py:191`,
`:1429-1430`, `:1506`, `:1516`, `:1632`, `:1644`, `:1799`; all of `helpers.py`,
`calculation.py`, `continuous_update.py`, `weather_aggregate.py`, `live_estimate.py`,
`auto_calc.py`, `sensor.py`.

### A7 — Not settled here: how the suite reacts

Revision 4 calls B's fixture churn "small". That was reasoned, not measured, and B brings two
sources Revision 4 did not count: every test that puts a 14.1 document into `hass_storage` now
runs the stamp step, and every test that reads a writer's stamp back gets HA's clock (US/Pacific
under the `hass` fixture) instead of the process's (UTC under `TZ=UTC` and on CI). The plan's
dry run measures both on `0b9a71bd` before the plan is handed over.

### A8 — The end-to-end criterion and its pins, updated

As in "End-to-end criterion" above, with: the legacy store state is a **14.1** document
(`"minor_version": 1`, or none, which HA reads as 1); "runs only below 15" → **runs only below
14.2**; and A4's two-argument test joins the supporting pins.
