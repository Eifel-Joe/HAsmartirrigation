"""The freshness check the four weather clients share."""

import datetime
import logging
import threading
import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from freezegun import freeze_time

from custom_components.irrigation_plus.weathermodules import fetch_gate
from custom_components.irrigation_plus.weathermodules.fetch_gate import (
    cache_lifetime,
    is_fresh,
)


def test_cache_lifetime_has_a_floor_of_sixty_seconds():
    assert cache_lifetime(0) == 60
    assert cache_lifetime(59) == 60
    assert cache_lifetime(599) == 599


@freeze_time("2026-10-23 12:00:00")
def test_is_fresh_matches_the_clients_old_rule():
    now = datetime.datetime.now()
    assert is_fresh(None, 599, False) is False
    assert is_fresh(now, 599, True) is False  # override_cache
    assert is_fresh(now - timedelta(seconds=598), 599, False) is True
    assert is_fresh(now - timedelta(seconds=599), 599, False) is False
    assert is_fresh(now - timedelta(seconds=59), 0, False) is True  # floor


class _Owner:
    """What a gate needs from a client: the cache settings, a stamp, a fetch point."""

    def __init__(self):
        self.cache_seconds = 600
        self.override_cache = False
        self.stamp = None
        self.cached = None
        self.calls = 0  # requests that actually went out
        self.delay = 0.2  # how long ``fetch_ok`` takes
        self.error = lambda: ValueError("boom")  # what ``fetch_raise`` raises

    def _serve_cached(self):
        return fetch_gate.is_fresh(self.stamp, self.cache_seconds, self.override_cache)

    def fetch_ok(self):
        """Serve the cache while fresh, else make one slow request and keep it."""
        if self._serve_cached():
            return self.cached
        self.calls += 1
        time.sleep(self.delay)  # long enough for the other thread to arrive meanwhile
        self.cached = "document"
        self.stamp = datetime.datetime.now()
        return self.cached

    def fetch_none(self):
        """Like ``fetch_ok``, but the request yields nothing and nothing is kept."""
        if self._serve_cached():
            return self.cached
        self.calls += 1
        return None

    def fetch_raise(self):
        """Like ``fetch_ok``, but the request fails and nothing is kept."""
        if self._serve_cached():
            return self.cached
        self.calls += 1
        raise self.error()


def _in_threads(*calls):
    """Run each call in its own thread; return what each one returned or raised."""
    results = [None] * len(calls)

    def worker(index, call):
        try:
            results[index] = call()
        except Exception as ex:
            results[index] = ex

    # daemon: a call that never returns must fail the test, not hang the run
    threads = [
        threading.Thread(target=worker, args=(index, call), daemon=True)
        for index, call in enumerate(calls)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert not any(thread.is_alive() for thread in threads)
    return results


def test_run_serialises_two_threads_onto_one_fetch():
    owner = _Owner()
    gate = fetch_gate.FetchGate(owner, "stamp")
    results = _in_threads(
        lambda: gate.run(owner.fetch_ok), lambda: gate.run(owner.fetch_ok)
    )
    assert owner.calls == 1
    assert results == ["document", "document"]


def test_run_hands_back_what_the_fetch_returned():
    # One gate each: after a failed fetch a gate pauses, and this is not about that.
    owner = _Owner()
    assert fetch_gate.FetchGate(owner, "stamp").run(owner.fetch_none) is None
    assert fetch_gate.FetchGate(owner, "stamp").run(owner.fetch_ok) == "document"


def test_run_lets_an_exception_through_and_lets_the_next_caller_in():
    owner = _Owner()
    gate = fetch_gate.FetchGate(owner, "stamp")
    with pytest.raises(ValueError, match="boom"):
        gate.run(owner.fetch_raise)
    owner.override_cache = True  # the pause after the failure is not what this is about
    # A lock left held by the failed run would hang this call.
    assert _in_threads(lambda: gate.run(owner.fetch_ok)) == ["document"]


def test_two_gates_do_not_wait_for_each_other():
    owner = _Owner()
    first = fetch_gate.FetchGate(owner, "stamp")
    second = fetch_gate.FetchGate(owner, "stamp")
    inside = threading.Event()
    release = threading.Event()

    def hold():
        inside.set()
        release.wait(timeout=5)
        return "held"

    holder = threading.Thread(target=lambda: first.run(hold))
    holder.start()
    try:
        assert inside.wait(timeout=5)
        assert _in_threads(lambda: second.run(lambda: "free")) == ["free"]
    finally:
        release.set()
        holder.join(timeout=5)
    assert not holder.is_alive()


class _Picky(Exception):
    """An exception ``copy.copy`` cannot rebuild: its constructor wants a keyword."""

    def __init__(self, text, *, code):
        super().__init__(text)
        self.code = code


def _gaps(gate, owner, fetch, frozen, requests):
    """Seconds between the real requests when a caller asks once a second."""
    moments = []
    for second in range(5000):
        before = owner.calls
        gate.run(fetch)
        if owner.calls > before:
            moments.append(second)
            if len(moments) == requests:
                break
        frozen.tick(1)
    assert len(moments) == requests
    return [
        later - earlier for earlier, later in zip(moments, moments[1:], strict=False)
    ]


def test_a_failure_is_replayed_without_a_fetch_during_the_pause():
    owner = _Owner()
    gate = fetch_gate.FetchGate(owner, "stamp")
    with freeze_time("2026-10-23 12:00:00") as frozen:
        assert gate.run(owner.fetch_none) is None
        assert owner.calls == 1
        frozen.tick(59)
        assert gate.run(owner.fetch_none) is None
        assert owner.calls == 1
        frozen.tick(2)
        assert gate.run(owner.fetch_none) is None
        assert owner.calls == 2


def test_a_raised_failure_is_replayed_with_its_type_and_message():
    owner = _Owner()
    owner.error = lambda: OSError("down")
    gate = fetch_gate.FetchGate(owner, "stamp")
    with freeze_time("2026-10-23 12:00:00") as frozen:
        with pytest.raises(OSError, match="down") as real:
            gate.run(owner.fetch_raise)
        frozen.tick(30)
        with pytest.raises(OSError, match="down") as replayed:
            gate.run(owner.fetch_raise)
        with pytest.raises(OSError, match="down") as replayed_again:
            gate.run(owner.fetch_raise)
    assert owner.calls == 1
    assert fetch_gate.is_replay(replayed.value)
    assert not fetch_gate.is_replay(real.value)  # the real failure is not marked
    assert replayed.value is not real.value
    assert replayed_again.value is not replayed.value  # no traceback piling up


def test_replay_of_an_uncopyable_exception_keeps_its_type():
    owner = _Owner()
    owner.error = lambda: _Picky("odd", code=7)
    gate = fetch_gate.FetchGate(owner, "stamp")
    with freeze_time("2026-10-23 12:00:00") as frozen:
        with pytest.raises(_Picky, match="odd"):
            gate.run(owner.fetch_raise)
        frozen.tick(30)
        with pytest.raises(_Picky, match="odd") as replayed:
            gate.run(owner.fetch_raise)
    assert owner.calls == 1
    assert fetch_gate.is_replay(replayed.value)


def test_consecutive_failures_double_the_pause_up_to_the_cache_lifetime():
    owner = _Owner()
    owner.cache_seconds = 599
    gate = fetch_gate.FetchGate(owner, "stamp")
    with freeze_time("2026-10-23 12:00:00") as frozen:
        gaps = _gaps(gate, owner, owner.fetch_none, frozen, requests=7)
    assert gaps == [60, 120, 240, 480, 599, 599]


def test_without_auto_update_the_pause_stays_at_sixty_seconds():
    owner = _Owner()
    owner.cache_seconds = 0
    gate = fetch_gate.FetchGate(owner, "stamp")
    with freeze_time("2026-10-23 12:00:00") as frozen:
        gaps = _gaps(gate, owner, owner.fetch_none, frozen, requests=4)
    assert gaps == [60, 60, 60]


def test_a_success_resets_the_backoff():
    owner = _Owner()
    owner.delay = 0
    gate = fetch_gate.FetchGate(owner, "stamp")
    with freeze_time("2026-10-23 12:00:00") as frozen:
        gate.run(owner.fetch_none)  # failure 1: pause 60
        frozen.tick(60)
        gate.run(owner.fetch_none)  # failure 2: pause 120
        frozen.tick(120)
        assert gate.run(owner.fetch_ok) == "document"  # success
        frozen.tick(601)  # the entry has aged out
        calls = owner.calls
        gate.run(owner.fetch_none)  # one failure again, not the third in a row
        frozen.tick(59)
        gate.run(owner.fetch_none)
        assert owner.calls == calls + 1
        frozen.tick(2)
        gate.run(owner.fetch_none)
        assert owner.calls == calls + 2


def test_override_cache_bypasses_the_pause():
    owner = _Owner()
    gate = fetch_gate.FetchGate(owner, "stamp")
    with freeze_time("2026-10-23 12:00:00"):
        gate.run(owner.fetch_none)
        gate.run(owner.fetch_none)
        assert owner.calls == 1  # paused
        owner.override_cache = True
        gate.run(owner.fetch_none)
        gate.run(owner.fetch_none)
        assert owner.calls == 3


def test_waiters_served_from_cache_do_not_count_as_failures():
    owner = _Owner()
    gate = fetch_gate.FetchGate(owner, "stamp")
    results = _in_threads(
        lambda: gate.run(owner.fetch_ok), lambda: gate.run(owner.fetch_ok)
    )
    assert results == ["document", "document"]
    assert owner.calls == 1
    assert gate._failed_at is None
    assert gate._failures == 0


def test_a_shorter_update_interval_shortens_a_running_pause():
    owner = _Owner()
    owner.cache_seconds = 3599
    gate = fetch_gate.FetchGate(owner, "stamp")
    with freeze_time("2026-10-23 12:00:00") as frozen:
        gate.run(owner.fetch_none)
        frozen.tick(60)
        gate.run(owner.fetch_none)
        frozen.tick(120)
        gate.run(owner.fetch_none)  # the third failure: pause 240
        assert owner.calls == 3
        owner.cache_seconds = 0  # auto-update switched off: the pause is 60 now
        frozen.tick(61)
        gate.run(owner.fetch_none)
        assert owner.calls == 4


def test_the_pause_runs_on_the_monotonic_clock():
    owner = _Owner()
    gate = fetch_gate.FetchGate(owner, "stamp")
    clock = [5000.0]
    # No freezegun here: only ``time.monotonic`` moves, the wall clock does not.
    with patch.object(time, "monotonic", lambda: clock[0]):
        gate.run(owner.fetch_none)
        clock[0] += 59
        gate.run(owner.fetch_none)
        assert owner.calls == 1
        clock[0] += 2
        gate.run(owner.fetch_none)
        assert owner.calls == 2


def test_a_replay_logs_one_debug_line_and_nothing_louder(caplog):
    owner = _Owner()
    gate = fetch_gate.FetchGate(owner, "stamp")
    with (
        freeze_time("2026-10-23 12:00:00") as frozen,
        caplog.at_level(logging.DEBUG, logger=fetch_gate.__name__),
    ):
        gate.run(owner.fetch_none)  # the real failure: the client logs it
        frozen.tick(30)
        gate.run(owner.fetch_none)  # the replay
    records = [r for r in caplog.records if r.name == fetch_gate.__name__]
    assert [r.levelno for r in records] == [logging.DEBUG]
    text = records[0].getMessage()
    assert "_Owner" in text and "stamp" in text and "30" in text


def test_failure_log_level_is_debug_for_a_replay_and_error_otherwise():
    owner = _Owner()
    owner.error = lambda: OSError("down")
    gate = fetch_gate.FetchGate(owner, "stamp")
    with freeze_time("2026-10-23 12:00:00") as frozen:
        with pytest.raises(OSError) as real:
            gate.run(owner.fetch_raise)
        frozen.tick(30)
        with pytest.raises(OSError) as replayed:
            gate.run(owner.fetch_raise)
    assert fetch_gate.failure_log_level(real.value) == logging.ERROR
    assert fetch_gate.failure_log_level(replayed.value) == logging.DEBUG
    # an exception that never went through the gate, e.g. a parse error
    assert fetch_gate.failure_log_level(ValueError("bad body")) == logging.ERROR
