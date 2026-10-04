"""GREEN side (v2026.10.04b1) on HA-Test: the sampler grid in the profiler dumps.

Same method as l1_grid.py: interval timers carry no target in the profiler output, the
sampler is told apart by its 15 s grid from the run start. The offset epoch-loop is the
same after the restart (host monotonic clock): checked on two _TrackPointUTCTime lines of
the 07:57:53 dump (1791138171.0 - 1166988.6186301708, 1791147600.222086 - 1176417.8407166004).
"""

import sys
from datetime import datetime, timezone, timedelta

C = 1789971182.381370
PERIOD = 15.0


def wall(loop_t: float) -> str:
    t = datetime.fromtimestamp(loop_t + C, tz=timezone.utc) + timedelta(hours=2)
    return t.strftime("%H:%M:%S.%f")[:-3]


def grid_hits(start: datetime, whens):
    s = start.timestamp() - C
    out = []
    for w in whens:
        k = round((w - s) / PERIOD)
        if 1 <= k <= 60 and abs(w - (s + k * PERIOD)) < 0.05 + k * 0.001:
            out.append((w, k))
    return out


def report(title: str, starts: dict, dumps: dict) -> None:
    print(title)
    for name, whens in dumps.items():
        print(f"\n{name}: {len(whens)} interval timers")
        for run, st in starts.items():
            hits = grid_hits(st, whens)
            text = ", ".join(f"when={w:.6f} -> {wall(w)} tick {k}" for w, k in hits)
            print(f"  grid of {run}: {text or 'no timer'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
