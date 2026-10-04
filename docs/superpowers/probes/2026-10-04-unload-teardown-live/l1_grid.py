"""L1 (reload mid-run) on HA-Test: find the self-closing sampler in the profiler dumps.

The profiler prints an interval timer only as `_TrackTimeInterval._interval_listener()`,
without its target. The sampler is told apart by its grid: period 15 s
(FLOW_POLL_INTERVAL), phase = the run's start. Loop time -> epoch via the offset that the
`_TrackPointUTCTime` lines carry (`when` next to `expected_fire_timestamp`).
"""

from datetime import datetime, timezone, timedelta

# epoch - loop, from three _TrackPointUTCTime lines of the 07:42:34 dump
OFFSETS = [
    1791151200.458185 - 1180018.0768153667,
    1791138171.0 - 1166988.6186289787,
    1791096840.169695 - 1125657.7883255482,
]
C = sum(OFFSETS) / len(OFFSETS)

DUMPS = {
    "D0 07:35:26.835 (vor dem Lauf)": [
        1173942.516369549, 1173945.489467832, 1121743.958822581, 1130745.502905785,
        1173945.4896246758, 1121745.840822206, 1121144.817260234, 1121742.78655945,
        1123546.54452065, 1121229.398184993, 1121229.398128895, 1121744.382994739,
        1130745.50280031, 1121142.960517845, 1121143.520329232, 1121145.953806691,
        1121144.185152439, 1121146.98028877, 1121144.604407056, 1120945.816402781,
    ],
    "D1 07:39:46.212 (Lauf, vor dem Neuladen)": [
        1123546.54452065, 1121744.185531367, 1173942.516369549, 1173945.489467832,
        1121229.398184993, 1121743.958822581, 1130745.50280031, 1121745.954490741,
        1173945.4896246758, 1121443.521619704, 1130745.502905785, 1121745.840822206,
        1121229.398128895, 1121742.961612152, 1121444.81788717, 1121444.604683178,
        1121744.382994739, 1121742.78655945, 1121205.877478585, 1121209.671477604,
        1121446.980841971,
    ],
    "D2 07:42:34.984 (nach dem Neuladen, Lauf noch an)": [
        1121745.840822206, 1130745.502905785, 1121443.521619704, 1121742.961612152,
        1121744.382994739, 1173945.4896246758, 1130745.50280031, 1121742.78655945,
        1121444.81788717, 1121745.954490741, 1173942.516369549, 1121444.604683178,
        1121963.853799816, 1121744.185531367, 1173945.489467832, 1123546.54452065,
        1121963.852223214, 1121743.958822581, 1121446.980841971, 1121375.91494302,
        1121374.678846516,
    ],
    "D3 07:44:23.625 (nach Laufende und Buchung)": [
        1121494.684301919, 1130745.50280031, 1121744.818870223, 1173945.4896246758,
        1121745.954490741, 1173942.516369549, 1121963.853799816, 1130745.502905785,
        1173945.489467832, 1121745.840822206, 1121746.982051508, 1121742.961612152,
        1121743.958822581, 1121742.78655945, 1121744.185531367, 1121744.605555973,
        1121743.522087896, 1123546.54452065, 1121963.852223214, 1121744.382994739,
        1121485.937101023,
    ],
    "D4 07:47:49.760 (5 min nach Laufende)": [
        1121742.961612152, 1121746.982051508, 1130745.50280031, 1173945.4896246758,
        1173942.516369549, 1130745.502905785, 1173945.489467832, 1121690.982190462,
        1121743.958822581, 1121744.818870223, 1121744.185531367, 1121745.954490741,
        1121963.853799816, 1121745.840822206, 1123546.54452065, 1121963.852223214,
        1121742.78655945, 1121744.605555973, 1121743.522087896, 1121744.382994739,
        1121689.695349194,
    ],
}

RUN_START = datetime(2026, 10, 4, 5, 39, 37, 53010, tzinfo=timezone.utc)  # pending event ts
PERIOD = 15.0
TOL = 0.05  # 50 ms: drift of a few hundred microseconds per tick


def wall(loop_t: float) -> str:
    t = datetime.fromtimestamp(loop_t + C, tz=timezone.utc) + timedelta(hours=2)
    return t.strftime("%H:%M:%S.%f")[:-3]


def main() -> None:
    spread = max(OFFSETS) - min(OFFSETS)
    print(f"offset epoch-loop = {C:.6f} (spread {spread * 1e6:.1f} us)")
    start_loop = RUN_START.timestamp() - C
    print(f"run start 07:39:37.053 -> loop {start_loop:.4f}")
    for name, whens in DUMPS.items():
        hits = []
        for w in whens:
            ticks = (w - start_loop) / PERIOD
            k = round(ticks)
            # k capped at 15 min: a timer an hour or more ahead can land on any 15 s grid
            if 1 <= k <= 60 and abs(w - (start_loop + k * PERIOD)) < TOL + k * 0.001:
                hits.append((w, k, (w - start_loop) / k))
        print(f"\n{name}: {len(whens)} interval timers")
        if not hits:
            print("  no timer on the sampler grid")
        for w, k, per in hits:
            print(f"  when={w:.6f} -> {wall(w)}  tick {k:2d}  mean period {per:.6f} s")


if __name__ == "__main__":
    main()
