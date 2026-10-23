"""Rules the four weather clients share when they go to the network."""

import datetime

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
