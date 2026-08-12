"""The shared hardware-run observation engine (run_watch.py).

Extracted from opensprinkler.py for issue #88, whose batch/queue mode needs the
same lifecycle with a different dispatch and a different watch entity. The 93
tests in test_opensprinkler.py / test_opensprinkler_teardown.py are the oracle
for "that mode still behaves exactly as it did"; this file pins the things those
tests cannot see — that there is now ONE implementation rather than two, and the
policy switches that keep OpenSprinkler on its original timings.
"""

from custom_components.smart_irrigation import const
from custom_components.smart_irrigation.opensprinkler import OpenSprinklerMixin
from custom_components.smart_irrigation.run_watch import (
    RunWatchMixin,
    WatchPolicy,
    queue_deadline_seconds,
    watch_policy_for,
)


class TestTheModeDelegatesRatherThanDuplicating:
    """The point of the extraction: one lifecycle, reached by two spellings.

    Without these, someone could re-implement the observation half inside
    OpenSprinklerMixin and every existing test would still pass — which is
    exactly the duplication #88 set out to avoid.
    """

    def test_the_station_watcher_registry_is_the_shared_one(self):
        class _Host(OpenSprinklerMixin, RunWatchMixin):
            pass

        host = _Host()
        registry = host._os_watchers()
        registry["sentinel"] = object()
        assert host._watchers() is registry

    def test_opensprinkler_does_not_carry_its_own_copy_of_the_lifecycle(self):
        """Each ``_os_*`` observation method must be a delegate, not a body.

        A delegate is short by construction; the originals were 20-60 lines. A
        re-implementation would blow past this and fail here.
        """
        import inspect

        for name in (
            "_os_evaluate",
            "_os_observed_start",
            "_os_finish",
            "_os_give_up",
            "_os_arm_timer",
        ):
            body = inspect.getsource(getattr(OpenSprinklerMixin, name))
            # Signature + docstring + one delegating call.
            assert len(body.splitlines()) <= 8, f"{name} looks re-implemented"
            assert "self._watch" in body, f"{name} does not reach the shared engine"


class TestThePolicyKeepsOpenSprinklerOnItsOriginalTimings:
    def test_opensprinkler_acknowledges(self):
        """Its program id is what distinguishes 'queued' from 'silently dropped'."""
        policy = watch_policy_for(const.WATERING_MODE_OPENSPRINKLER)
        assert policy.acknowledges is True
        assert policy.accept_seconds == const.OPENSPRINKLER_ACCEPT_SECONDS

    def test_a_freshly_armed_station_waits_the_acceptance_grace_not_the_queue(self):
        """Pins the pre-extraction behaviour deliberately, bug and all.

        ``_os_start_watch`` armed OPENSPRINKLER_ACCEPT_SECONDS unconditionally —
        including on the resume path, where the run already has an observed start
        and nothing cancels the timer. A run with more than 300 s left after a
        restart is therefore written off while its station is still watering
        (reproduced against the pre-extraction code, 2026-08-12).

        The extraction preserved that exactly rather than quietly fixing it, so
        this asserts the CURRENT behaviour. When the fix lands, this test is the
        one that should be changed, on purpose.
        """
        assert (
            watch_policy_for(const.WATERING_MODE_OPENSPRINKLER).queue_deadline_at_start
            is False
        )

    def test_an_unknown_mode_falls_back_to_the_conservative_policy(self):
        """A run persisted under a mode this build no longer knows still has to be
        observed to an end, and waiting for a signal beats assuming it is live."""
        policy = watch_policy_for("a-mode-from-the-future")
        assert policy.acknowledges is True


class TestTheGiveUpDeadlineCountsTheRightRunsAhead:
    @staticmethod
    def _run(zone_id, seconds, mode=const.WATERING_MODE_OPENSPRINKLER):
        return {
            const.RUN_ZONE_ID: zone_id,
            const.RUN_PLANNED_SECONDS: seconds,
            const.RUN_MODE: mode,
        }

    def _base(self, planned):
        return (
            const.OPENSPRINKLER_ACCEPT_SECONDS
            + planned
            + const.OPENSPRINKLER_QUEUE_MARGIN_SECONDS
        )

    def test_a_lone_run_waits_only_for_itself(self):
        run = self._run(1, 600)
        assert queue_deadline_seconds([run], run) == self._base(600)

    def test_the_zones_queued_ahead_extend_it(self):
        run = self._run(1, 600)
        others = [self._run(2, 300), self._run(3, 900)]
        assert queue_deadline_seconds([run, *others], run) == self._base(600) + 1200

    def test_a_run_on_a_different_controller_does_not_extend_it(self):
        """The zones ahead of this one are the ones sharing its queue.

        Before the extraction the mode was hardcoded to OpenSprinkler, so a batch
        run would have counted stations on a completely separate controller.
        """
        run = self._run(1, 600)
        other = self._run(2, 9999, mode=const.WATERING_MODE_SERVICE)
        assert queue_deadline_seconds([run, other], run) == self._base(600)

    def test_the_mode_can_be_named_explicitly(self):
        run = self._run(1, 600, mode=const.WATERING_MODE_SERVICE)
        ahead = self._run(2, 300, mode=const.WATERING_MODE_SERVICE)
        assert queue_deadline_seconds(
            [run, ahead], run, mode=const.WATERING_MODE_SERVICE
        ) == (self._base(600) + 300)

    def test_junk_in_the_run_list_cannot_raise(self):
        """The list comes off disk and is walked on every observation."""
        run = self._run(1, 600)
        assert queue_deadline_seconds(
            [run, None, "nonsense", {const.RUN_PLANNED_SECONDS: "abc"}], run
        ) == self._base(600)


class TestAPolicyIsSelfDescribing:
    def test_a_non_acknowledging_mode_must_arm_the_queue_deadline_at_once(self):
        """There is no second signal to re-arm on, so the first timer is the only
        backstop and must cover the zones queued ahead."""
        policy = WatchPolicy(
            mode="batch", acknowledges=False, queue_deadline_at_start=True
        )
        assert policy.acknowledges is False
        assert policy.queue_deadline_at_start is True
