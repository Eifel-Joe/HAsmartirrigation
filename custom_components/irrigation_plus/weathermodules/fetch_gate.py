"""Rules the four weather clients share when they go to the network."""

import datetime
import threading
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

# Floor for how long a fetched result is reused, even when the caller's configured
# cache window is shorter (e.g. auto-update disabled → 0s). Repeated weather
# lookups — skip-condition checks, the dashboard outlook, the intra-day estimate —
# would otherwise each hit the network (and a DNS lookup); this caps them to at
# most one call per method per minute.
MIN_CACHE_SECONDS = 60


def cache_lifetime(cache_seconds: float) -> float:
    """How long a fetched result is reused: the configured window, but at least the floor."""
    return max(cache_seconds, MIN_CACHE_SECONDS)


def is_fresh(
    fetched_at: datetime.datetime | None, cache_seconds: float, override_cache: bool
) -> bool:
    """Whether a result fetched at ``fetched_at`` may still be served cached."""
    if fetched_at is None or override_cache:
        return False
    return datetime.datetime.now() < fetched_at + datetime.timedelta(
        seconds=cache_lifetime(cache_seconds)
    )


class FetchGate:
    """The door in front of one fetch point: one caller at a time goes through.

    ``owner`` is the client and ``stamp_attr`` the name of the attribute that holds
    the time of its last good fetch at this point.
    """

    def __init__(self, owner: Any, stamp_attr: str) -> None:
        """Init."""
        self._owner = owner
        self._stamp_attr = stamp_attr
        self._lock = threading.Lock()

    def run(self, fetch: Callable[[], T]) -> T:
        """Run ``fetch`` with every other caller of this gate held back."""
        # Wurzel: the clients are called from several executor threads at once --
        #   every sensor refresh, skip check and outlook asks for the same
        #   document. Each caller checked the cache, found it empty and went to
        #   the network itself: on the test install 1 get_data and 18
        #   get_forecast_data requests left within 0.6 s, on a metered key.
        # Fix-Logik: one lock per fetch point. ``fetch`` begins with its own
        #   freshness check, and that check now runs inside the lock, so a caller
        #   that waited finds the entry the first one stored and is served from
        #   it -- one request per document.
        # NOT-TO-DO: no ``asyncio`` lock -- the clients run only in executor
        #   threads, never on the event loop, and an ``asyncio`` lock does not
        #   hold threads back. No lock around the request alone either: the parse
        #   and the timestamp come after it, so the waiters would wake to a cache
        #   that is still empty and fetch again.
        # siehe test_weather_clients_fetch_gate.py::test_concurrent_callers_make_one_request
        with self._lock:
            return fetch()
