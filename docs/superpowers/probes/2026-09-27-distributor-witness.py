"""Does the witness work on the DISTRIBUTOR path as master now stands?

master (fa863aa9) carries FlowMeter.metered_the_run() from the merged self-closing
fix, whose form is

    _saw_report_after_open and _priced and not _declined

_saw_report_after_open is set only when sample() receives a reported_at NEWER than
the first one it saw. irrigation.py::_read_flow_sample supplies it as a fourth
element; distributor.py::_dist_read_flow returns a THREE-tuple and its two
sample() calls pass no report at all.

So: feed the meter exactly the way the distributor does, and ask.
Run it against any checkout of the package:

    python 2026-09-27-distributor-witness.py [path-to-checkout]

The default below is the scratch worktree it was measured in, which will not
survive a cleanup -- pass a path instead. Measured against `upstream/master` at `fa863aa9`, i.e. with the merged self-closing witness in
`flow_metering.py`.
"""

import datetime
import sys

_DEFAULT_CHECKOUT = "D:/Entwicklung/HASI/issue53-work/wt"
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_CHECKOUT)

from custom_components.irrigation_plus.flow_metering import FlowMeter  # noqa: E402

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 9, 28, 6, 0, tzinfo=UTC)

# The distributor's real constants: DISTRIBUTOR_FLOW_POLL_SECONDS 5, max_gap 5*4.
POLL = 5.0
MAX_GAP = 20.0


def run(label, readings, *, with_report):
    """readings: [(value, elapsed)] -- a rate sensor reading L/min."""
    meter = FlowMeter("lifetime", max_gap_s=MAX_GAP)
    for value, at in readings:
        if with_report:
            # what a four-tuple would supply: the sensor reports on every live poll
            meter.sample(value, "L/min", "measurement", T0 + datetime.timedelta(seconds=at), at=at)
        else:
            # what distributor.py actually does today: three values and `at`
            meter.sample(value, "L/min", "measurement", at=at)
    d = meter.delivered()
    return d, meter.metered_the_run(), label


# A genuinely dry run: the sensor is alive and reads 0 on every poll. This is the
# case the fix has to catch -- it MUST come out as "the meter measured the run".
dry = [(0.0, t) for t in (0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0)]

print(f"{'feed':38} {'delivered()':13} {'metered_the_run()':18} guard fires?")
print("-" * 92)
for with_report in (False, True):
    d, m, _ = run("x", dry, with_report=with_report)
    how = "as distributor.py does today" if not with_report else "with a report per poll"
    # #53's guard: delivered <= 0 and not metered_the_run() -> degrade to time-based
    fires = (d is not None and d <= 0) and not m
    verdict = "YES -> time-based credit (fix is a no-op)" if fires else "no  -> dry verdict stands"
    print(f"{how:38} {str(d):13} {str(m):18} {verdict}")
