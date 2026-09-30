# Eifel-Joe#22 / JustChr#160 — the weather buffer on one clock, live on HA-Test, 2026-09-30

Plan: `docs/superpowers/plans/2026-09-30-weather-buffer-one-frame.md`, Task 10 (L0–L4), with the
execution addendum (E1–E12). Design: `docs/superpowers/specs/2026-09-28-weather-buffer-one-frame-design.md`
(Revision 4 + Addendum 2026-09-30, A2: the migration keys on the MINOR version so that a rollback
stays open on Home Assistant ≥ 2026.3).

Why live at all: Home Assistant's major-version guard (`UnsupportedStorageVersionError`, since
2026.3.0) exists in none of the test environments — the local venv runs HA 2024.12.5, upstream CI
runs 2025.5.0 and 2026.2.3 (Python 3.13; HA ≥ 2026.3 needs Python ≥ 3.14.2). HA-Test runs
2026.9.3: the only place where the rollback path meets the guard.

## The build

`v2026.09.30b2`: branch `prerelease/v2026.09.30b2`, commit `fabda3c0` on top of the fix branch head
`6e061bbc`; it differs from `6e061bbc` only by the version string in seven files (`manifest.json`,
`const.py`, `package.json`, the four bundles; one line each, checked by script against the parent
blob). Pre-release on the fork with `irrigation_plus.zip` built from the SHA (199 files, sha256
`22c9f439…`); tag on the fork → `fabda3c0`; asset HTTP 200 and downloaded back byte-identical.
The ZIP carries CRLF line endings: `git archive` on this machine applies `core.autocrlf=true`
(store.py: blob 107098 bytes + 2223 lines = 109321 in the ZIP). The b1 build of 2026-09-30 is the
same (103406 + 2151 = 105557). Harmless for Python and JSON; every fork release so far was built so.
Full suite on `6e061bbc` before the build: `7 failed, 3565 passed, 9 skipped, 380 errors`, failure
names identical to the 387 of the baseline on `6654a0ac`.

## Method

The migration runs when the store is loaded — inside `async_setup_entry` (`async_get_registry`,
cached per process; `async_setup` does not load it). At boot that is before `logger.set_level` can
act, and a restart resets a level set at runtime; `.storage/` is not on the MCP read list and the
diagnostics do not show the storage version. So each step: **disable the config entry → install
through HACS → restart → set `homeassistant.helpers.storage` to `info` → enable the entry**. The
store is then loaded, and migrated, at the enable — the same `async_setup_entry` →
`async_get_registry` → `Store.async_load` path as at boot — and HA's own INFO line shows the version
step. All through `mcp__HA-Test__…`; restarts announced in the chat.

## L0 — before (read just before L1)

HA-Test: `core-2026.9.3`, Home Assistant OS 18.3, Python 3.14.6, zone Europe/Berlin (guard active).
Irrigation Plus through HACS `v2026.09.30b1` (the inlet-gate build on `0b9a71bd`: `STORAGE_VERSION` 14,
no minor version, a two-parameter `_async_migrate_func` — the rollback target). Entry
`01M20AD0AWZJ15ZXSF1ECVJZN3` `loaded`, log level WARNING. `last_calculated` of all nine zone sensors
(`kirschlorbeer`, `beet`, `test1`–`test6`, `grace_test`): `2026-09-29 23:00:00`.

## L1 — upgrade to b2

`update_information`, entry disabled, `download v2026.09.30b2` (`store.py` 109321 bytes, `const.py`
70649 — the ZIP's sizes; modified 22:11:53), restart, level `info`, entry enabled:

```
2026-09-30 22:14:21.466 INFO (MainThread) [homeassistant.helpers.storage] Migrating irrigation_plus.storage storage from 14.1 to 14.2
```

Entry `loaded`. All nine `last_calculated` still `2026-09-29 23:00:00`: on HA OS the process zone is
HA's zone, so the migration is the identity — as designed. `irrigation_plus` in the system log: only
`PirateWeather API returned error status code: 429` (the free API's rate limit after restarts),
"No weather data to parse" following from it, and upstream's `via_device` deprecation notices.

## L2 — roll back to b1

Entry disabled, `download v2026.09.30b1` (`store.py` 105557 bytes = the b1 blob 103406 + 2151 CRLF),
restart, level `info`, entry enabled:

```
2026-09-30 22:17:24.989 INFO (MainThread) [homeassistant.helpers.storage] Migrating irrigation_plus.storage storage from 14.2 to 14.1
```

**No `UnsupportedStorageVersionError`** (none in the 2000-line window); entry `loaded`; the nine
`last_calculated` unchanged; errors only the 429 above. One `irrigation_plus` entity `unavailable`:
`button.irrigation_plus_distributor_gardena1_test_run` — unavailable since at least 20:00 (history),
by design while the distributor's commissioning is confirmed; not related.

This is the claim the minor-version design rests on: a release that knows only 14.1 opens a 14.2 file
on a guarded Home Assistant, runs its two-argument migrate function and saves the file back as 14.1.

## L3 — upgrade again

Entry disabled, `download v2026.09.30b2` (`store.py` 109321 bytes), restart, level `info`, enabled:

```
2026-09-30 22:20:11.273 INFO (MainThread) [homeassistant.helpers.storage] Migrating irrigation_plus.storage storage from 14.1 to 14.2
```

Entry `loaded`; `last_calculated` unchanged; the same single by-design `unavailable` button; errors
only the 429; no `UnsupportedStorageVersionError`. The re-upgrade lifts the file again (documented:
one more window on an affected install; the identity here).

## L4 — state left

By the user's choice (b): **v2026.09.30b2 stays installed** (HACS `installed_version v2026.09.30b2`),
entry enabled and loaded, `homeassistant.helpers.storage` back to `warning`. Three restarts in all,
each between its install (file times 22:11:53, 22:14:46, 22:18:09) and its migration line above.
The nightly calculation at 23:00 was not reached during the test.

## What this shows and what it does not

Shown on a guarded Home Assistant (2026.9.3): the upgrade migrates 14.1 → 14.2; the previous
release opens the 14.2 file and saves it as 14.1 without the guard firing; the re-upgrade migrates
again; the integration loads each time. Not shown here, because HA OS keeps the process zone equal
to HA's: the stamps actually moving by an offset — that is the Docker/Core case, pinned by the suite
(the end-to-end matrix and `test_store_stamp_migration.py`).
