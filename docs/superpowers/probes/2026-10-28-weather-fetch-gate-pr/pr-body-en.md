## Problem

The weather clients check their cache without a lock. Every caller that starts before the first response is back makes its own request, and a failure is not cached at all: the next caller asks again at once, Pirate Weather three times without a pause (#196). Measured: 19 requests within 0.6 s per refresh, 30 after saving a schedule, and 5,505 + 552 errors during 46 hours of `429`. This is the PR for the three points you asked for on #196.

## Fix

**1. One shared fetch.** A new module `weathermodules/fetch_gate.py` puts a gate in front of every fetch that sets a timestamp. There are seven: OWM `get_data` and `get_forecast_data`, Pirate Weather `get_data` and `get_forecast_data`, Open-Meteo `_fetch`, Met Office `_fetch_hourly` and `_fetch_three_hourly`. Each gate has a thread lock, and freshness is checked *inside* the lock, so a waiter gets the cache that was just filled instead of asking itself. The clients run only in executor threads, hence a thread lock, not an `asyncio` lock; the event loop never takes one. One gate per timestamp rather than per client: current values and forecast stay independent, and a pause on one does not hold up the other.

**2. A pause after a failure, honouring `Retry-After`.**
- *A failure* is a run that fetched and left no new timestamp. That covers every way the seven fetches fail today (an exception, `None` after a non-200, `None` after an incomplete document) without a list of codes or types.
- *Length:* 60 s, doubled with each further failure in a row, at most the normal cache window `max(cache_seconds, 60)`; a success resets it. Why: 60 s already merges the measured bursts completely and matches the existing floor ("at most one call per method per minute"). The cap means a gate never asks more often during an outage than in normal operation. With a fixed 60 s that would be up to 1,440 requests a day against 144 at 10 min; Met Office allows 360 a day on the free plan and has two gates.
- *`Retry-After`* (seconds or an HTTP date) is a lower bound: if it is longer than the pause, it wins; a shorter one does not undercut the pause. At most 24 h; unreadable or in the past, it has no effect. The pause counts from the *start* of the failed run, as the refresh cycle does; `Retry-After` counts from the response that sent it.
- *What callers get during the pause:* exactly the outcome of the failure, the same return value, or an exception of the same type with the same message (a copy without the growing traceback). No old values are handed on, and every caller's failure path stays as it is today; the PR only changes the number of requests. The type has to stay because `__init__.py` catches `OSError` specifically.
- *Logs:* an ERROR line from a weather client still means a real request was made and failed. A replay is logged at DEBUG, with the end of the pause, or saying the caller waited through the failure. That includes the five accessors of Open-Meteo and Met Office above the gate; their return values do not change. The callers' logs outside `weathermodules/` stay as they are, e.g. the WARNING "No weather data to parse".
- *Clocks:* the pause runs on `time.monotonic()`, so it does not jump at a DST change or when the clock is set. The freshness check stays on `datetime.datetime.now()`, so the successful path is unchanged.

**3. A pause between Pirate Weather's retries:** 1 s, then 2 s, none after the last attempt. A `429` (at Pirate Weather "monthly quota exhausted") or a `Retry-After` ends the attempts at once: a second attempt a second later cannot succeed, or would ignore what the service asked for. Otherwise as today: three attempts, retried only on a non-200, network errors not retried.

**The successful path is unchanged**, as you asked: freshness, floor, timestamps, return values and log lines stay the same. The only difference is that a second concurrent caller waits and is served from the cache.

## Accompanying changes

- The freshness check now lives once in `fetch_gate.py`: the three identical `_is_fresh`, Open-Meteo's inline check, Met Office's own lifetime calculation in `_forecast_document`, and the four `_MIN_CACHE_SECONDS`. That is the shared helper you mentioned. I did not introduce a base class; the four clients stay independent, and `_SESSION` stays in each module because four test files patch it there.
- `override_cache` bypasses the cache as today and now the pause as well (a cached failure is something cached too). `validate_key` stays outside the gate, so a corrected key does not inherit the old one's pause.
- The dead `i = i + 1` in Pirate Weather's loops is gone; the loops now share one `_get_with_retries`.
- No frontend, no bundles, no translations. The docs describe neither fetching nor retries, so they stay as they are.

## Not built, your call

- **Pirate Weather's `Ratelimit-Reset`** is not read. It counts to the start of the next month, not to the next sensible request. With the 24 h cap it would give one request a day instead of one per cache window, on a key that is already exhausted. If you want it, it is one line in the gate.

## Dependencies

None. Based on the current `master`; no other open PR touches `weathermodules/`.

## Testing

- **91 new pytest cases** in two new files (`test_weather_fetch_gate.py`, `test_weather_clients_fetch_gate.py`); no existing test changed. The two tests you asked for exist for **each of the seven gates**: concurrent callers make exactly one request and all get the same result (red without the gate: 5 requests for 5 threads); after a failure, no request and the same outcome during the pause, a new request after it, both for a `None` return and for exceptions (same type and message). Also: the sequence 60 → 120 → 240 s and the cap, including `cache_seconds = 0`; `Retry-After` as seconds, as an HTTP date, longer, shorter, over 24 h, unreadable, in the past; Pirate `sleep(1)`/`sleep(2)` and `429` → one attempt; nothing above DEBUG for a replay; independent gates; waiters behind a slow failure share it; the pause counted from the start, `Retry-After` from the response.
- **16 mutations** of the load-bearing checks, each caught: lock removed, freshness outside the lock, pause before freshness, no doubling, no cap, `Retry-After` as an upper bound, `429` retried, replay logged at ERROR, pause counted from the end, waiter rule removed, and more.
- **Full suite locally** (Python 3.12, HA 2024.12): the failing tests are the same by name as on `master`, passed 4013 → 4104. `black` clean, `ruff` clean.
- **Live on a test instance** (Pirate Weather, 9 zones × 2 schedules, refresh every 10 min):
  - per cycle **1** real forecast fetch instead of 18; "Connection pool is full" 0 times instead of 8;
  - saving a schedule with an expired cache: **1** fetch instead of 30;
  - failure, provoked with an invalid latitude (95°) that Pirate Weather answers with `400`: runs only at intervals of 60/120/240/480/599 s, one ERROR line per run, concurrent callers share the failure (37 replays). 9 ERROR lines in 30 minutes across both gates, several of them from deliberate extra requests; before, 6,057 in 46 hours.
  - The first measurement showed an edge: the pause then counted from the *end* of the run, which took just over 3 s. At the cap the next 10-minute cycle therefore arrived 2 s early, and a gate that keeps failing asked only every second cycle. It now counts from the start; in the re-measurement the gate at the cap asks in every cycle again.
- **Not shown live:** `Retry-After`, because no service is known to send it; it is covered by the tests only. The individual gaps of 1 s and 2 s are only inferred from the run's duration, because urllib3's request log would show the key in the URL. Recovery *within* a pause: restoring the setting reloads the entry.

## Seen along the way, not in this PR

- Pirate Weather's `get_data` and `get_forecast_data` fetch the same URL and cache it separately; that is two requests per refresh where one would do (Open-Meteo does it with one document).
- The scheduler's projection cache multiplies the callers. After this PR the 18 calls per cycle are cache hits without network traffic, but still executor jobs.
- `override_cache` / `ATTR_OVERRIDE_CACHE` has no user in the integration code.

If you'd like an issue for any of them, just say.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
