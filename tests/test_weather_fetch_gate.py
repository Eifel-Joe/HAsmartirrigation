"""The freshness check the four weather clients share."""

import datetime
import threading
import time
from datetime import timedelta

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

    def _serve_cached(self):
        return fetch_gate.is_fresh(self.stamp, self.cache_seconds, self.override_cache)

    def fetch_ok(self):
        """Serve the cache while fresh, else make one slow request and keep it."""
        if self._serve_cached():
            return self.cached
        self.calls += 1
        time.sleep(0.2)  # long enough for the other thread to arrive meanwhile
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
        raise ValueError("boom")


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
    owner = _Owner()
    gate = fetch_gate.FetchGate(owner, "stamp")
    assert gate.run(owner.fetch_none) is None
    assert gate.run(owner.fetch_ok) == "document"


def test_run_lets_an_exception_through_and_lets_the_next_caller_in():
    owner = _Owner()
    gate = fetch_gate.FetchGate(owner, "stamp")
    with pytest.raises(ValueError, match="boom"):
        gate.run(owner.fetch_raise)
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
