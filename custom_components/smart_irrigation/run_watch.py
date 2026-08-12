"""Observe a run that hardware owns: when it starts watering, and when it stops.

Some watering modes hand the run to a controller that owns both the queue and
the valve. Nothing about such a run may be measured from the moment it was
dispatched — a queued zone would finalise, credit its usage and release its
accounting long before its water flowed. The run is driven by an entity that is
on while that zone is actually watering, and the dispatch time is used for
exactly one thing: deciding when to give up waiting.

That lifecycle was written for OpenSprinkler stations (v2026.08.06) and is
almost entirely generic. This module is the generic part; a mode supplies the
handful of things that really differ as a :class:`WatchPolicy`:

* how the controller *acknowledges* a run it has queued, if it does at all;
* what timestamp to record as the moment watering began;
* how long to wait before writing the run off.

``OpenSprinklerMixin`` keeps its ``_os_*`` spellings as delegates onto this
engine, so its behaviour is unchanged and its tests remain the oracle for that.

Extracted for issue #88 (batch/queue dispatch), whose mode needs the same
observation lifecycle with a different dispatch and a different watch entity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.core import Event, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from . import const

_LOGGER = logging.getLogger(__name__)

# States that carry no attributes: HA drops an entity's extra_state_attributes
# while it is unavailable, so an acknowledgement reads as absent rather than as
# withdrawn. Never mistake "cannot see the controller" for "the controller
# dropped the run" — the first is transient, the second finalises the run.
NO_INFO_STATES = ("unavailable", "unknown")
# The watch entity is a binary_sensor / switch / valve; these are its "watering"
# states.
RUNNING_STATES = ("on", "open", "opening")


@dataclass
class Watcher:
    """One zone's live subscription, plus at most one pending timer.

    ``accepted`` is the reconciliation state: for a mode whose controller
    acknowledges its queue it starts False, and once the acknowledgement has
    been seen its withdrawal means the run was dropped. A mode that has no
    acknowledgement signal starts accepted (see ``WatchPolicy.acknowledges``).
    """

    entity: str
    accepted: bool = False
    unsub: object | None = None
    cancel: object | None = None


@dataclass(frozen=True)
class WatchPolicy:
    """What one watering mode contributes to the shared observation lifecycle.

    ``acknowledges`` says whether the controller reports having taken the run on
    before it runs it. OpenSprinkler does, via a non-zero program id on the
    station, and that is what distinguishes "queued behind four other zones"
    from "silently discarded". A controller handed a whole queue in one call has
    accepted it by the time the call returns and has no such signal, so the run
    starts accepted and the give-up deadline is the only backstop.

    ``give_up_problem`` is the fault code raised against a zone whose run never
    watered.
    """

    mode: str
    acknowledges: bool = False
    give_up_problem: str = const.PROBLEM_STATION_NEVER_RAN
    # Seconds to allow for an acknowledgement before writing the run off.
    accept_seconds: float = const.OPENSPRINKLER_ACCEPT_SECONDS
    # Whether a freshly armed watcher waits the whole queue-derived deadline
    # instead of ``accept_seconds``. An acknowledging mode uses the short grace
    # first and re-arms to the long one once the controller has answered; a mode
    # with no acknowledgement has nothing to wait for, so its only backstop must
    # be long enough to cover the zones queued ahead of this one.
    queue_deadline_at_start: bool = False


def is_acknowledged(state) -> bool:
    """True if this observation carries a controller acknowledgement.

    OpenSprinkler's is a non-zero program id on the station. Kept here rather
    than as a policy callable because it is the only acknowledgement shape any
    mode currently has, and a mode that does not acknowledge never asks.
    """
    return bool(state.attributes.get(const.OPENSPRINKLER_ATTR_PROGRAM_ID))


def planned_seconds(run: dict) -> float:
    """The run's planned window, clamped non-negative, never raising."""
    try:
        return max(0.0, float(run.get(const.RUN_PLANNED_SECONDS) or 0))
    except (TypeError, ValueError):
        return 0.0


def queue_deadline_seconds(runs: list, run: dict, *, mode: str | None = None) -> float:
    """Seconds after dispatch at which a run that never watered is written off.

    Derived rather than fixed, because what a queued run waits for is the runs
    ahead of it: a four-zone cycle on real deficits is around 288 minutes and a
    seven-zone one considerably longer, so any single constant is either far too
    short for a full cycle or far too long for one zone. The margin absorbs the
    controller's own inter-zone delays.

    This is only a backstop. A run a controller explicitly drops is seen within
    a poll; this bound is what ends a run whose watch entity stopped reporting
    altogether.

    ``mode`` defaults to the run's own, so the zones counted as "ahead" are the
    ones sharing its controller rather than every in-flight run.
    """
    planned = planned_seconds(run)
    want_mode = mode if mode is not None else run.get(const.RUN_MODE)
    ahead = 0.0
    for other in runs or []:
        if not isinstance(other, dict) or other is run:
            continue
        if other.get(const.RUN_MODE) != want_mode:
            continue
        if other.get(const.RUN_ZONE_ID) == run.get(const.RUN_ZONE_ID):
            continue
        ahead += planned_seconds(other)
    return (
        const.OPENSPRINKLER_ACCEPT_SECONDS
        + ahead
        + planned
        + const.OPENSPRINKLER_QUEUE_MARGIN_SECONDS
    )


class RunWatchMixin:
    """Observe hardware-owned runs. Mixed into SmartIrrigationCoordinator.

    Reuses ``SelfClosingMixin``'s persisted run record, optimistic bucket credit
    and restart contract wholesale; this adds only the part that decides *when*
    a run started and ended.
    """

    # --- registry -----------------------------------------------------------

    def _watchers(self) -> dict:
        """Lazy {zone_id: Watcher} of live subscriptions.

        A watcher owns a state subscription and at most one timer, and is the
        only thing that ends a queued run — so it must be re-created on restart
        for every persisted record or that record would block its zone until the
        deadline in the persisted list expires.
        """
        watchers = getattr(self, "_run_watchers", None)
        if watchers is None:
            watchers = self._run_watchers = {}
        return watchers

    def _watch_cancel(self, zone_id) -> None:
        """Cancel-and-pop a zone's subscription and timer (no-op if absent)."""
        watcher = self._watchers().pop(int(zone_id), None)
        if watcher is None:
            return
        unsub = watcher.unsub
        if unsub is not None:
            unsub()
        cancel = watcher.cancel
        if cancel is not None:
            cancel()

    def _watch_arm_timer(self, zone_id, delay: float, reason: str) -> None:
        """(Re)arm the watcher's single timer."""
        watcher = self._watchers().get(int(zone_id))
        if watcher is None:
            return
        cancel = watcher.cancel
        if cancel is not None:
            cancel()

        async def _expired(_now):
            await self._watch_give_up(zone_id, reason)

        watcher.cancel = async_call_later(self.hass, max(0.0, delay), _expired)

    # --- policy -------------------------------------------------------------

    def _watch_policy(self, zone_id, run: dict | None = None) -> WatchPolicy:
        """The policy for whatever mode this zone's in-flight run belongs to.

        Resolved from the RUN record first, and only then from the zone. The run
        carries the mode it was dispatched under, survives a restart, and is
        still there when the zone has been deleted or edited mid-run — all three
        cases where the zone's current mode is either absent or no longer the one
        the hardware is acting on.
        """
        if isinstance(run, dict) and run.get(const.RUN_MODE):
            return watch_policy_for(run.get(const.RUN_MODE))
        zone = self.store.get_zone(int(zone_id)) or {}
        return watch_policy_for(zone.get(const.ZONE_WATERING_MODE))

    async def _watch_observed_start_iso(self, zone_id, run: dict, entity: str) -> str:
        """When watering began, ISO-8601 UTC, for RUN_OBSERVED_START.

        The default is the moment the observation arrived. OpenSprinkler
        overrides this to prefer the controller's own reported start.
        """
        return dt_util.utcnow().isoformat()

    # --- lifecycle ----------------------------------------------------------

    async def _watch_start(
        self, zone_id, watch_entity: str, planned: float, *, accepted: bool
    ) -> None:
        """Watch an entity for a zone's run start and end.

        ``accepted`` seeds the reconciliation state: False right after dispatch
        for a mode whose controller acknowledges separately, True when resuming
        a record whose zone is already reporting a run, and True from the start
        for a mode with no acknowledgement signal.
        """
        zid = int(zone_id)
        self._watch_cancel(zid)
        watcher = Watcher(entity=watch_entity, accepted=bool(accepted))
        self._watchers()[zid] = watcher
        watcher.unsub = async_track_state_change_event(
            self.hass, [watch_entity], self._watch_state_changed
        )
        run = await self._sc_find_run(zid)
        policy = self._watch_policy(zid, run)
        # Deliberately keyed on the POLICY, not on ``accepted``. An acknowledging
        # mode arms the short grace here in both cases, including the resume path
        # — preserving the behaviour this engine was extracted from; see the
        # note on ``queue_deadline_at_start``.
        if policy.queue_deadline_at_start:
            runs = await self._sc_active_runs()
            self._watch_arm_timer(
                zid,
                queue_deadline_seconds(runs, run or {}, mode=policy.mode),
                policy.give_up_problem,
            )
        else:
            self._watch_arm_timer(zid, policy.accept_seconds, policy.give_up_problem)
        # The zone's own running sensor and the observed-watering map both derive
        # this same entity, and both may have been built before the controller
        # published it. Nudge them now that it is known to resolve.
        async_dispatcher_send(self.hass, const.DOMAIN + "_config_updated", zid)
        # The controller may already have the run queued (or even running, on an
        # empty queue) before the subscription above exists. Evaluate the current
        # state once so that run is not missed entirely.
        await self._watch_evaluate(zid, self.hass.states.get(watch_entity))

    @callback
    def _watch_state_changed(self, event: Event) -> None:
        """A watched entity changed state."""
        entity_id = event.data.get("entity_id")
        for zone_id, watcher in list(self._watchers().items()):
            if watcher.entity != entity_id:
                continue
            self.hass.async_create_task(
                self._watch_evaluate(zone_id, event.data.get("new_state"))
            )

    async def _watch_evaluate(self, zone_id, state) -> None:
        """Advance a watched run from one observation of its entity."""
        zid = int(zone_id)
        watcher = self._watchers().get(zid)
        if watcher is None:
            return
        run = await self._sc_find_run(zid)
        if run is None:
            # The run was finalised by another path (a user stop, a restart
            # reconcile). Nothing left to observe.
            self._watch_cancel(zid)
            return

        if state is None or state.state in NO_INFO_STATES:
            # No information: the controller is unreachable or the entity has not
            # been created yet. Never read this as "the run was dropped" — the
            # deadline timer is what ends a run whose entity stops reporting.
            return

        running = state.state in RUNNING_STATES
        observed_start = run.get(const.RUN_OBSERVED_START)

        if running:
            if observed_start is None:
                await self._watch_observed_start(zid, run)
            return

        if observed_start is not None:
            # The zone stopped. The controller ended the run, on time or early;
            # either way it is over now.
            await self._watch_finish(zid, run)
            return

        policy = self._watch_policy(zid, run)
        if not policy.acknowledges:
            # Nothing to reconcile against: an entity that is simply off is a run
            # still waiting its turn. Only the deadline ends it.
            return

        if not watcher.accepted:
            if is_acknowledged(state):
                # The controller has acknowledged the run. From here on its
                # acknowledgement being withdrawn is meaningful.
                watcher.accepted = True
                runs = await self._sc_active_runs()
                # Measured from this acknowledgement rather than from dispatch.
                # Downtime would otherwise be spent out of the run's budget: an
                # outage longer than the deadline leaves nothing for a zone the
                # controller is still holding, and the run is written off and its
                # credit reversed a second after the resume, for water the
                # controller then goes on to deliver. Acknowledgement is normally
                # within a poll of dispatch, so this is the same bound in
                # ordinary operation.
                self._watch_arm_timer(
                    zid,
                    queue_deadline_seconds(runs, run, mode=policy.mode),
                    policy.give_up_problem,
                )
            return

        if not is_acknowledged(state):
            # Acknowledged, then dropped without ever watering: a controller-side
            # rain delay, a water level of 0, or a stop-all. The zone was credited
            # optimistically at dispatch, so this has to unwind that credit rather
            # than wait the deadline out.
            await self._watch_give_up(zid, policy.give_up_problem)

    async def _watch_observed_start(self, zone_id, run: dict) -> None:
        """Watering began: from here the run is a normal timed run."""
        zid = int(zone_id)
        watcher = self._watchers().get(zid)
        planned = planned_seconds(run)
        zone = self.store.get_zone(zid) or {}

        entity = (watcher.entity if watcher else None) or run.get(
            const.RUN_WATCH_ENTITY
        )
        started = await self._watch_observed_start_iso(zid, run, entity)
        runs = [
            (
                dict(r, **{const.RUN_OBSERVED_START: started})
                if r.get(const.RUN_ZONE_ID) == run.get(const.RUN_ZONE_ID)
                else r
            )
            for r in await self._sc_active_runs()
        ]
        await self._sc_persist_runs(runs)

        # The suppression window taken at dispatch is measured from dispatch, so
        # for a queued run it has already expired — and observed watching is now
        # pointed at this very entity. Re-take it for the real run window so the
        # zone's own run is not also credited as external.
        self._note_si_valve(zid, planned)
        # Flow sampling deliberately starts HERE, not at dispatch: a meter seeded
        # while the zone was still queued would sample a window that mostly
        # precedes the water.
        await self._sc_start_flow_sampling(zone)
        if watcher is not None:
            cancel = watcher.cancel
            if cancel is not None:
                cancel()
            watcher.cancel = None
        # Backstop only. The entity going off is the primary finish signal; this
        # covers a missed transition.
        self._sc_schedule_cleanup(zid, planned)
        _LOGGER.info(
            "Zone %s: %s run started watering (planned %.0fs)",
            zid,
            self._watch_policy(zid, run).mode,
            planned,
        )

    async def _watch_finish(self, zone_id, run: dict) -> None:
        """Watering stopped. Settle the run against what it actually delivered."""
        zid = int(zone_id)
        self._watch_cancel(zid)
        planned = planned_seconds(run)
        elapsed = self._sc_run_elapsed(run)
        # A zone that ran its full window is a completed run; one the controller
        # cut short settles like an early stop, which reconciles the optimistic
        # credit down to what was delivered. One second of slack keeps a run that
        # ended exactly on time out of the partial path.
        if elapsed + 1 >= planned:
            await self._sc_finish_run(zid)
        else:
            await self.async_stop_self_closing(zid, close_valve=False)

    async def _watch_give_up(self, zone_id, reason: str) -> None:
        """End a run that never watered, and undo its optimistic credit."""
        zid = int(zone_id)
        self._watch_cancel(zid)
        run = await self._sc_find_run(zid)
        if run is None:
            return
        zone = self.store.get_zone(zid) or {}
        # elapsed is 0 for a run with no observed start, so this reconciles the
        # bucket all the way back to RUN_PRE_BUCKET and logs a run that delivered
        # nothing. No stop is sent: the zone never opened, and stopping would only
        # affect whatever the controller is running right now.
        await self.async_stop_self_closing(
            zid, close_valve=False, detail=const.RUN_DETAIL_STATION_NEVER_RAN
        )
        self._set_zone_fault(zid, reason)
        self._fire_zone_problem(zid, zone, zone.get(const.ZONE_LINKED_ENTITY), reason)
        _LOGGER.warning(
            "Zone %s: the controller never watered it (%s); the run was written "
            "off and its bucket credit reversed",
            zid,
            reason,
        )


# Registered by each mode's module at import time, so a mode's policy lives next
# to the mode rather than in a table here that has to be kept in step.
_POLICIES: dict[str, WatchPolicy] = {}
# Conservative on both switches: wait for an acknowledgement rather than assume
# the run is live, and keep the short grace rather than the long queue backstop.
_DEFAULT_POLICY = WatchPolicy(
    mode=const.WATERING_MODE_OPENSPRINKLER,
    acknowledges=True,
    queue_deadline_at_start=False,
)


def register_watch_policy(policy: WatchPolicy) -> None:
    """Register a mode's observation policy."""
    _POLICIES[policy.mode] = policy


def watch_policy_for(mode) -> WatchPolicy:
    """The policy for a watering mode.

    Falls back to the OpenSprinkler policy rather than raising: a run persisted
    under a mode the current build no longer knows still has to be observed to
    an end, and the acknowledging policy is the conservative one — it waits for
    a signal instead of assuming the run is live.
    """
    return _POLICIES.get(mode, _DEFAULT_POLICY)
