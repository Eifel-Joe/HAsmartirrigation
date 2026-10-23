"""Rules the four weather clients share when they go to the network."""

import copy
import datetime
import logging
import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

_LOGGER = logging.getLogger(__name__)

# Floor for how long a fetched result is reused, even when the caller's configured
# cache window is shorter (e.g. auto-update disabled → 0s). Repeated weather
# lookups — skip-condition checks, the dashboard outlook, the intra-day estimate —
# would otherwise each hit the network (and a DNS lookup); this caps them to at
# most one call per method per minute.
MIN_CACHE_SECONDS = 60

# How long a fetch point stays shut after its first failed fetch. Every further
# failure in a row doubles it, up to the cache lifetime (see ``_pause_left``).
FIRST_PAUSE_SECONDS = 60

# Doublings after which the cache lifetime has won in any case; keeps ``2 ** n``
# small for a gate that has been failing for weeks.
_MAX_DOUBLINGS = 16

# Set on an exception the gate raises again in place of a fresh failure.
_REPLAY_ATTR = "_fetch_gate_replay"


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


def is_replay(exc: BaseException) -> bool:
    """Whether ``exc`` is a failure the gate replayed, not a fresh one."""
    return getattr(exc, _REPLAY_ATTR, False)


def _replayable_copy(exc: Exception) -> Exception | None:
    """A copy of ``exc`` marked as a replay, or None where it cannot be copied.

    A copy carries no traceback, so replaying it again and again does not grow
    one, and callers in several threads never share an instance.
    """
    try:
        again = copy.copy(exc)
        setattr(again, _REPLAY_ATTR, True)
    except Exception:  # noqa: BLE001 -- any exception class may refuse a copy
        return None
    return again


class FetchGate:
    """The door in front of one fetch point: one caller at a time goes through.

    ``owner`` is the client and ``stamp_attr`` the name of the attribute that holds
    the time of its last good fetch at this point. After a failed fetch the door
    stays shut for a while and hands the callers behind it that failure's outcome
    instead of asking the service again.
    """

    def __init__(self, owner: Any, stamp_attr: str) -> None:
        """Init."""
        self._owner = owner
        self._stamp_attr = stamp_attr
        self._lock = threading.Lock()
        self._failures = 0  # failed runs in a row
        self._failed_at: float | None = None  # time.monotonic() of the latest one
        self._outcome: tuple[bool, Any] | None = None  # (raised, value) of it
        self._retry_after = 0.0  # seconds a response asked us to wait; 0 = none

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
        #   it -- one request per document. A caller that waited behind a failed
        #   fetch finds the pause (below) and is handed that failure's outcome,
        #   so a failure is not retried once per waiter either.
        # NOT-TO-DO: no ``asyncio`` lock -- every path that reaches a gate runs
        #   in an executor thread, and an ``asyncio`` lock does not hold threads
        #   back. Not every client method stays off the event loop: live_estimate.py
        #   calls get_hourly_precipitation_forecast and get_hourly_temperature_forecast
        #   there. That is safe only because those accessors read stored
        #   documents and never reach a gate; a gate must never be reached from
        #   such an accessor, or a waiting caller would block the loop. No lock
        #   around the request alone either: the parse and the timestamp come
        #   after it, so the waiters would wake to a cache that is still empty
        #   and fetch again.
        # siehe test_weather_clients_fetch_gate.py::test_concurrent_callers_make_one_request
        #   und ::test_concurrent_callers_during_an_outage_share_one_failed_run
        with self._lock:
            owner = self._owner
            before = getattr(owner, self._stamp_attr)
            was_fresh = is_fresh(before, owner.cache_seconds, owner.override_cache)
            # ``override_cache`` means "hand out nothing stored", and a stored
            # failure is stored too: it asks the service every time.
            if not was_fresh and not owner.override_cache:
                seconds_left = self._pause_left()
                if seconds_left > 0:
                    return self._replay(seconds_left)
            try:
                result = fetch()
            except Exception as exc:
                self._settle(before, was_fresh, raised=True, value=exc)
                raise
            self._settle(before, was_fresh, raised=False, value=result)
            return result

    def _settle(self, before: Any, was_fresh: bool, raised: bool, value: Any) -> None:
        """Note how the run that has just ended went: a good fetch or a failure."""
        # Wurzel: the fetch points fail in three different ways -- an exception, a
        #   None after a non-200 status, a None after an incomplete document --
        #   and only the exception says so. What they have in common is that none
        #   of them leaves a new timestamp.
        # Fix-Logik: a run that went to the network (the entry was not fresh when
        #   it began) and left no new timestamp is a failure; a new timestamp is a
        #   success and clears the count. A run served from the cache -- a caller
        #   that waited for the one that fetched -- is neither.
        # NOT-TO-DO: no list of status codes and exception types. It would have to
        #   be kept per client, and it would miss exactly the quiet None branches
        #   that today's code already treats as "nothing fetched".
        # siehe test_weather_clients_fetch_gate.py::test_a_failed_fetch_pauses_its_gate
        #   und test_weather_fetch_gate.py::test_waiters_served_from_cache_do_not_count_as_failures
        if getattr(self._owner, self._stamp_attr) != before:
            self._failures = 0
            self._failed_at = None
            self._outcome = None
        elif not was_fresh:
            self._failures += 1
            # Wurzel: the pause measures a duration, not a time of day. A wall
            #   clock jumps when the clocks go back or the system time is set.
            # Fix-Logik: ``time.monotonic()``, called here and in ``_pause_left``
            #   at the moment it is needed.
            # NOT-TO-DO: not ``datetime.datetime.now()`` -- the freshness check
            #   keeps it because the success path must not change; two clocks in
            #   one module is the price. And never bind ``time.monotonic`` to a
            #   name or a default argument: freezegun moves it with ``tick()``
            #   only when the call goes through the ``time`` module.
            # siehe test_weather_fetch_gate.py::test_the_pause_runs_on_the_monotonic_clock
            self._failed_at = time.monotonic()
            self._outcome = (raised, value)

    def _pause_left(self) -> float:
        """Seconds the pause after the latest failure still runs; 0 where there is none."""
        if self._failed_at is None:
            return 0.0
        # Wurzel: callers come every few seconds (6-7 lookups every 10-30 s on
        #   the production install). A pause of a fixed 60 s asks 1440 times a
        #   day in an outage, ten times the 144 of normal operation at 10 min;
        #   Met Office's free tier allows 360 calls a day and has two gates.
        # Fix-Logik: 60 s, doubled with every further failure in a row, capped at
        #   the cache lifetime -- the failure path never asks more often than
        #   normal operation does. It is worked out at every check from the
        #   owner's current ``cache_seconds`` instead of being stored as a
        #   deadline, so a changed update interval takes effect at once.
        # NOT-TO-DO: no fixed 60 s (above). No pause of a whole cache window from
        #   the first failure either: one blip would then cost a full window, a
        #   whole day with daily updates.
        # siehe test_weather_fetch_gate.py::test_consecutive_failures_double_the_pause_up_to_the_cache_lifetime
        #   und ::test_a_shorter_update_interval_shortens_a_running_pause
        pause = min(
            FIRST_PAUSE_SECONDS * 2 ** min(self._failures - 1, _MAX_DOUBLINGS),
            cache_lifetime(self._owner.cache_seconds),
        )
        return max(0.0, self._failed_at + pause - time.monotonic())

    def _replay(self, seconds_left: float) -> Any:
        """Hand back the outcome of the failure that began the pause: no request."""
        raised, value = self._outcome
        _LOGGER.debug(
            "%s %s: %d failed fetch(es) in a row, no request for another %.0f s;"
            " replaying the last outcome",
            type(self._owner).__name__,
            self._stamp_attr,
            self._failures,
            seconds_left,
        )
        if not raised:
            return value
        replayed = _replayable_copy(value)
        if replayed is None:
            # An exception that cannot be copied keeps its type: mark the
            # instance itself and raise it with a clean traceback.
            setattr(value, _REPLAY_ATTR, True)
            replayed = value.with_traceback(None)
        raise replayed
