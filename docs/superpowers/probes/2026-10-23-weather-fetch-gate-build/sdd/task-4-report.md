# Task 4 report: a replayed failure is logged at DEBUG, not as a fresh error

Status: DONE
Commit: `49a5a3e8` on `fix/weather-client-fetch-gate` (parent `cb6c83ed`)
Subject: `fix(weather): a replayed failure is logged at DEBUG, not as a fresh error`
Trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (as the task and global-constraints.md say; the harness attribution reminder names a different model, the task text was followed)

## Implemented

- `weathermodules/fetch_gate.py`: new `failure_log_level(exc: BaseException) -> int` = `logging.DEBUG if is_replay(exc) else logging.ERROR`, placed right after `is_replay`, with a docstring that states the rule (an ERROR line means a request was made and failed).
- The five accessor log sites now read `_LOGGER.log(fetch_gate.failure_log_level(ex), "<unchanged message>", ex)` (black wrapped them over several lines):
  - `OpenMeteoClient.py`: `get_data` (was :198), `get_forecast_data` (was :308), `get_hourly_data` (was :475)
  - `MetOfficeClient.py`: `get_data` (was :467), `get_forecast_data` (was :570)
  - Located by message text, as the brief's line numbers are from the base commit. Message texts and return values are untouched.
- OWM and Pirate Weather: no change (gate wraps the whole method, their log code does not run in the pause). Confirmed by the four cases being green before any implementation.

Sister-path check: grepped every `except` and `_LOGGER.*` in `weathermodules/*.py`. Open-Meteo `_fetch_doc` and Met Office `_request` raise on every failure (`raise_for_status`), none return `None`, so a replay can only arrive as an exception at the five sites; the WARNING lines in `get_data` (missing values, empty series) sit behind a successful fetch and are not reachable by a replay. The other OWM/Pirate `_LOGGER.error` sites are inside the gated bodies.

## Files changed

- `custom_components/irrigation_plus/weathermodules/fetch_gate.py` (+12)
- `custom_components/irrigation_plus/weathermodules/OpenMeteoClient.py`
- `custom_components/irrigation_plus/weathermodules/MetOfficeClient.py`
- `tests/test_weather_clients_fetch_gate.py` (+`import logging`, two new tests)
- `tests/test_weather_fetch_gate.py` (one new test appended)

Total: 5 files, 105 insertions, 5 deletions. Working tree is CRLF, kept byte-wise (edits done by script with CRLF re-applied; `file` shows CRLF on all touched files; index is LF via autocrlf, so no churn in the diff).

## Tests added

1. `test_a_replayed_failure_logs_nothing_above_debug[case]` (the brief's test, parametrized over `CASES`): first call with `_failing(500)` (no assertion on its logs), `caplog.clear()`, `tick(30)`, second call: same outcome as the first, no new request, no record of `custom_components.irrigation_plus.weathermodules*` above DEBUG. Added on top of the brief's sketch: `caplog.set_level(DEBUG)` and an assertion that the gate's "replaying the last outcome" DEBUG line is present, so the pass is not vacuous for OWM/Pirate.
2. `test_every_open_meteo_accessor_logs_a_replay_at_debug[get_data|get_forecast_data|get_hourly_data]` (extra): `CASES` reaches only `get_forecast_data` of Open-Meteo, so `get_data` and `get_hourly_data` would otherwise be two of the five changed sites with no test. Also pins that the first real failure keeps logging exactly one ERROR line.
3. `test_failure_log_level_is_debug_for_a_replay_and_error_otherwise` (unit, `test_weather_fetch_gate.py`): real failure ERROR, replayed copy DEBUG, a plain `ValueError` (parse-error stand-in) ERROR.

Existing tests are unchanged.

## TDD evidence

RED (before the implementation), `-k replayed_failure`:

```
tests\test_weather_clients_fetch_gate.py ....FFF                         [100%]
FAILED ...::test_a_replayed_failure_logs_nothing_above_debug[openmeteo_doc]
FAILED ...::test_a_replayed_failure_logs_nothing_above_debug[met_hourly]
FAILED ...::test_a_replayed_failure_logs_nothing_above_debug[met_three_hourly]
================= 3 failed, 4 passed, 31 deselected in 2.16s ==================
```

The failing records were `Open-Meteo get_forecast_data error: %s` (OpenMeteoClient.py:308), `Met Office get_data error: %s` (:467) and `Met Office get_forecast_data error: %s` (:570), all at level 40. The four OWM/Pirate cases were green, as the brief expects.

GREEN (after): `-k replayed_failure` gave `7 passed, 31 deselected in 1.29s`.

Mutation check for the two extra tests: with `failure_log_level` temporarily forced to `return logging.ERROR`, `-k "log_level or replayed_failure or open_meteo_accessor"` gave `7 failed, 4 passed` (the unit test, the three table cases, the three Open-Meteo accessors; the four OWM/Pirate cases stay green). File restored from a byte copy (diff stat unchanged: 12 insertions), same selection then `11 passed`.

Step 4 (command: `TZ=UTC $PY -m pytest tests/test_weather_fetch_gate.py tests/test_weather_clients_fetch_gate.py tests/test_weather_modules.py -p _local_socket_unblock -q --no-header`):

```
tests\test_weather_fetch_gate.py ..................                      [ 17%]
tests\test_weather_clients_fetch_gate.py ............................... [ 47%]
..........                                                               [ 57%]
tests\test_weather_modules.py .......................................... [ 98%]
..                                                                       [100%]
============================ 103 passed in 11.02s =============================
```

Before the extra tests it was 99 passed (same three files). No test elsewhere asserts the five message texts (`grep` over `tests/` found no match). The full suite was not run, as instructed.

## Lint

```
uvx black custom_components/irrigation_plus/   -> All done! 71 files left unchanged.
uvx ruff check custom_components/irrigation_plus/ -> All checks passed!
```

Black also run on the two edited test files (CI does not lint `tests/`); one reformat, no content change.

## Self-review

- Commit message: English body, what and why, no issue numbers; `git log -1 --format=%B | grep "Eifel-Joe\|#[0-9]"` empty. Staged the five files explicitly; `git status` clean afterwards.
- No `time` binding or default-argument issues introduced; no new clocks.
- A replayed exception whose copy failed is marked on the original instance by Task 3's `_replay`; `failure_log_level` reads the same attribute, so that path also logs at DEBUG. Unit-tested only for the copy path (the uncopyable path is covered by Task 3's own test via `is_replay`).

## Concerns

None blocking. Two small points for the reviewer:
- The two extra tests go beyond the brief; they are small and cover sites the table cannot reach. Easy to drop if unwanted.
- Not run: the full suite and the CI lint on `tests/` (not part of the CI gate).
