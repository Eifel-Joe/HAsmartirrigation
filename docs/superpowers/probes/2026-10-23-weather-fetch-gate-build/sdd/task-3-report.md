# Task 3 report: the pause after a failed fetch

Status: DONE_WITH_CONCERNS (concerns are small, see the end)
Commit: `cb6c83ed` fix(weather): a failed fetch pauses that document instead of being retried at once
Branch: `fix/weather-client-fetch-gate` in `D:\Entwicklung\HASI\issue89-work\wt`, on top of `7b5454b6`. Not pushed.

## Implemented (`weathermodules/fetch_gate.py`)

- `FIRST_PAUSE_SECONDS = 60`, `_MAX_DOUBLINGS = 16`, `_REPLAY_ATTR = "_fetch_gate_replay"`, `is_replay(exc)`
  (reads the attribute with `getattr(exc, "_fetch_gate_replay", False)`).
- `FetchGate` state: `_failures`, `_failed_at` (monotonic), `_outcome = (raised, value)`, `_retry_after = 0.0`
  (present, not read; Task 5 adds the Retry-After term).
- `run`: core ordering as in the brief (stamp read, `was_fresh`, pause check only when `not was_fresh and not
  override_cache`, fetch, `_settle`). Waiters behind a failed run find the pause and get the outcome with no request.
- `_settle`: new stamp (`!= before`) is a success and clears the state; unchanged stamp with `not was_fresh` is a
  failure (count, `time.monotonic()`, outcome); unchanged stamp with `was_fresh` (served from cache) does nothing.
- `_pause_left()`: computed on every check from `_failures`, `_failed_at` and the owner's current `cache_seconds`
  (`min(60 * 2 ** min(n-1, 16), cache_lifetime(cache_seconds))`), no stored deadline. `time.monotonic()` is called
  through the module at call time.
- `_replay(seconds_left)`: one DEBUG line (owner class, stamp attribute, failures in a row, seconds left), no
  ERROR/WARNING. Return value: the same value. Exception: `copy.copy(exc)` with the attribute set (helper
  `_replayable_copy`); if copying fails, the attribute is set on the original and it is raised with
  `with_traceback(None)` (raised outside the `except` so no `__context__` is attached).
- Ruling 2 applied: the NOT-TO-DO of the lock comment now says every path that reaches a gate runs in an executor
  thread, that `live_estimate.py` calls `get_hourly_precipitation_forecast` / `get_hourly_temperature_forecast` on the
  event loop, that this is safe only because those accessors read stored documents and never reach a gate, and that a
  gate must never be reached from such an accessor. I named the accessors and the file rather than line numbers, which
  go stale.
- Code-doku blocks (Wurzel, Fix-Logik, NOT-TO-DO, siehe): lock/`run` (updated), C3 in `_settle`, C7 at the
  `time.monotonic()` call in `_settle`, C5 in `_pause_left`. C10 has a two-line comment at the `override_cache`
  condition. Client modules untouched.

## Tests

`tests/test_weather_fetch_gate.py` (unit, fake owner): `_Owner` got `delay` and `error` (a factory for what
`fetch_raise` raises) so tests can set them. New tests: `test_a_failure_is_replayed_without_a_fetch_during_the_pause`,
`test_a_raised_failure_is_replayed_with_its_type_and_message`, `test_consecutive_failures_double_the_pause_up_to_the_cache_lifetime`
(gaps 60,120,240,480,599,599), `test_without_auto_update_the_pause_stays_at_sixty_seconds`,
`test_a_success_resets_the_backoff`, `test_override_cache_bypasses_the_pause`,
`test_waiters_served_from_cache_do_not_count_as_failures`, Review Focus 2 `test_a_shorter_update_interval_shortens_a_running_pause`,
Review Focus 3 `test_replay_of_an_uncopyable_exception_keeps_its_type`, Review Focus 4
`test_the_pause_runs_on_the_monotonic_clock` (no freezegun, `patch.object(time, "monotonic", ...)`), plus one extra,
`test_a_replay_logs_one_debug_line_and_nothing_louder`, which asserts only on the gate's own logger (ruling 5), not on
client log lines.

`tests/test_weather_clients_fetch_gate.py` (seven gates): `test_a_failed_fetch_pauses_its_gate` (7 rows),
Review Focus 1 `test_concurrent_callers_during_an_outage_share_one_failed_run` (7 rows),
`test_a_paused_forecast_does_not_hold_up_current_conditions` (OWM, Met Office), Review Focus 5
`test_validate_key_ignores_a_running_pause`. The five-thread scaffolding of `test_concurrent_callers_make_one_request`
moved into a helper `_five_callers_at_once(case, client, response)`, used by it and by the outage test; its
assertions are unchanged.

Two Task 2 unit tests had to change because they ran a failure and then immediately a success on the same gate, which
the pause now (correctly) replays. Their intent is unchanged:
- `test_run_hands_back_what_the_fetch_returned`: one gate per call.
- `test_run_lets_an_exception_through_and_lets_the_next_caller_in`: sets `override_cache = True` before the next
  caller, so the thread still gets in and fetches, which is what proves the lock was released.

## TDD evidence

RED (before touching `fetch_gate.py`; the new tests used `fetch_gate.is_replay` through the module so they failed per
test instead of an import error):
```
TZ=UTC $PY -m pytest tests/test_weather_fetch_gate.py tests/test_weather_clients_fetch_gate.py -p _local_socket_unblock -q --no-header
27 failed, 21 passed
```
Selected failures: unit `assert 2 == 1` (calls, no pause), `assert [1,1,1,1,1,1] == [60,120,240,480,599,599]`,
`AttributeError: 'FetchGate' object has no attribute '_failed_at'`, `assert [] == [10]` (no log line); clients
`test_concurrent_callers_during_an_outage...`: `assert 5 == 1` (five callers, five requests, i.e. the Task 2 reviewer's
finding), `assert 15 == 3` for Pirate; `test_a_failed_fetch_pauses_its_gate`: `assert 2 == 1` / `6 == 3`.
Pins that were already green as predicted: none of the three came out fully green, because I made them stronger than
the brief: `test_override_cache_bypasses_the_pause` first establishes a pause, `test_validate_key_ignores_a_running_pause`
asserts the pause on `get_data` before the key check, and `test_a_paused_forecast...` also asserts the forecast gate is
still shut. Without the pause those assertions fail, so all three were red.

GREEN after the implementation (and the two Task 2 test adjustments):
```
tests/test_weather_fetch_gate.py ................. ; tests/test_weather_clients_fetch_gate.py ...............................
48 passed in 7.56s
```
Brief Step 4 (both new files + test_weather_modules.py, test_pirateweather_daily.py,
test_met_office_forecast_document.py, test_precipitation_guard_real_clients.py):
```
128 passed in 12.91s
```
Flakiness: two new files run 3 more times: `48 passed in 7.63s`, `48 passed in 7.66s`, `48 passed in 7.75s`.

Outside the brief, as a sanity check (not the full suite): the other test files that touch the weather clients
(`test_duration_math_hardware_window`, `test_hourly_*_forecast`, `test_live_estimate_*`, `test_openmeteo_hourly`,
`test_precipitation_guard`, `test_pressure_shared_across_clients`): `265 passed, 189 errors`; every error is the
known teardown `Lingering timer after test` (pre-existing local-environment noise, memory
`hasi-local-test-env-rebuild`), no FAILED.

Mutation probes on `fetch_gate.py` (each killed by at least one test, file restored byte-identical afterwards):
no cap (3 tests), no doubling (1), `time.time()` instead of `time.monotonic()` (monotonic test only), `from time import
monotonic` (monotonic test), override ignored (2), waiters counted as failures (1), no reset on success (1), never copy
(1), replay logged at ERROR (1), stored deadline instead of recomputing (Review Focus 2 test).

## Lint

`uvx black custom_components/irrigation_plus/`: `71 files left unchanged`. `uvx ruff check
custom_components/irrigation_plus/`: `All checks passed!`. The two new test files are also black/ruff clean.
`git log c46c41fc..HEAD | grep "Eifel-Joe\|#[0-9]"` only matches the git `Author:` header lines, not any message text.
Working tree stays CRLF (`git ls-files --eol`: `i/lf w/crlf`), the diff stat shows no line-ending churn.

## Self-review

- Every test named in the brief exists with that name (seven unit + three Review Focus unit; four client tests with the
  two Review Focus ones). C3, C4 (return values), C5, C7, C10, C11 are covered; logging beyond the gate's own DEBUG line
  is Task 4.
- Ruling 1: waiters behind a failure make no request and get the outcome; proven by the outage test (red 5 == 1, green 1).
- Rulings 3-7 applied as written. No stored deadline, `_retry_after` unused, monotonic at call time, one DEBUG line,
  replay copy / fallback, comments in the code-doku shape.
- Black-box check of the replay of a returned value: only `None` occurs as a failure return in the seven fetch points,
  so replaying the same object is safe (no mutable value is shared).

## Concerns (minor)

1. `_retry_after` is a field nothing reads or writes yet (as ordered). Its comment says what it will hold; until Task 5
   it is dead state.
2. Fallback replay of an uncopyable exception marks the original instance, which the first caller may still be
   inspecting; a second thread replaying at that very moment could make the first caller's `is_replay()` read True. Needs
   an exception class that cannot be copied (the `requests`/`OSError`/`ValueError` family copies fine) and a race
   inside microseconds; it only changes a log level in Task 4. The brief prescribes this fallback, so I kept it.
3. `_outcome` keeps the failed exception, and with it its traceback and frames, until the next fetch at that gate
   (seven gates at most). Storing a traceback-free copy at settle time would avoid it; I kept the brief's shape.
4. In the unchanged Open-Meteo body `_cached_doc is not None` is part of the freshness check, while the gate's
   `was_fresh` only looks at the stamp. They can differ only if the stamp is fresh and the document is None, which the
   code never produces.
