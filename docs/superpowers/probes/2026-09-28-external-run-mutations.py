"""Apply each mutation, run the four suites, record, revert.

A mutation is KILLED when it makes tests fail that pass on the unmutated branch.
Pre-existing failures are measured first and subtracted, not assumed away.

Adapted from the runner used on the previous branch. The change here is that
mutations target THREE different files, so each row names its own file.

Run from the worktree:
    python /d/Entwicklung/HASI/issue64-work/mutate.py
"""

import io
import json
import os
import subprocess

WT = r"D:\Entwicklung\HASI\issue64-work\wt"
PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
TMP = r"D:\Entwicklung\HASI\issue64-work\tmp"

RUN_STATE = os.path.join(WT, "custom_components", "irrigation_plus", "run_state.py")
OBSERVED = os.path.join(
    WT, "custom_components", "irrigation_plus", "observed_watering.py"
)

# Every test named as a killer below was checked to live in one of these files
# before this list was trusted. A file missing from here once turned a broken
# run into a clean-looking "0 killed".
SUITES = [
    "tests/test_chain_sees_external_runs.py",
    "tests/test_run_in_flight.py",
    "tests/test_observed_watering.py",
    "tests/test_experimental_features.py",
]

IN_FLIGHT_HEAD = '''        since = getattr(self, "_observed_on_since", None)
        if not isinstance(since, dict):
            return False
'''

CEILING_COMPARE = (
    "        return (dt_util.utcnow() - started).total_seconds() < ceiling\n"
)

WRAPPER_BODY = """        try:
            await self._credit_observed_watering(
                zone_id,
                seconds,
                measured_l=measured_l,
                sensor_present=sensor_present,
            )
        finally:
            await self.async_run_deferred_calculation(zone_id)
"""

WRAPPER_NO_FINALLY = """        await self._credit_observed_watering(
            zone_id,
            seconds,
            measured_l=measured_l,
            sensor_present=sensor_present,
        )
        await self.async_run_deferred_calculation(zone_id)
"""

COERCE = """        try:
            max_dur = float(max_dur)
        except (TypeError, ValueError):
"""

GATE_AND_DROP = """            if seconds >= const.OBSERVED_SAMPLE_MIN_RUN_SECONDS:
                self._chain_drop_zone(zone_id)
"""

# (n, file, label, old, new, expected killer)
MUTATIONS = [
    (
        1,
        RUN_STATE,
        "the fourth source always answers False",
        IN_FLIGHT_HEAD,
        "        return False\n" + IN_FLIGHT_HEAD,
        "the two open-window chain tests + test_an_open_external_run_counts",
    ),
    (
        2,
        RUN_STATE,
        "drop the ceiling comparison",
        CEILING_COMPARE,
        "        return started is not None\n",
        "test_an_external_run_past_its_ceiling_does_not_count",
    ),
    (
        3,
        RUN_STATE,
        "ceiling < becomes <=",
        CEILING_COMPARE,
        "        return (dt_util.utcnow() - started).total_seconds() <= ceiling\n",
        "nothing expected - boundary is one microsecond wide",
    ),
    (
        4,
        RUN_STATE,
        "the wide answer drops the fourth source",
        "        return self._si_run_in_flight(zid) or self._observed_run_in_flight(zid)\n",
        "        return self._si_run_in_flight(zid)\n",
        "the two open-window chain tests",
    ),
    (
        5,
        OBSERVED,
        "the open edge asks the WIDE question again",
        "            if self._si_run_in_flight(zone_id) or self.hass.loop.time() < (\n",
        "            if self.zone_run_in_flight(zone_id) or self.hass.loop.time() < (\n",
        "test_the_open_edge_tracks_a_second_external_open_of_the_same_zone",
    ),
    (
        6,
        RUN_STATE,
        "the narrow answer drops the distributor source",
        "            or self._distributor_run_in_flight(zid)\n",
        "",
        "test_distributor_cycle_counts_for_its_members",
    ),
    (
        7,
        OBSERVED,
        "drop the provenance gate (always drop the zone)",
        GATE_AND_DROP,
        "            self._chain_drop_zone(zone_id)\n",
        "test_a_few_seconds_of_hand_testing_keeps_the_zones_turn",
    ),
    (
        8,
        OBSERVED,
        "invert the provenance gate",
        "            if seconds >= const.OBSERVED_SAMPLE_MIN_RUN_SECONDS:\n",
        "            if seconds < const.OBSERVED_SAMPLE_MIN_RUN_SECONDS:\n",
        "the two closed-window chain tests",
    ),
    (
        9,
        OBSERVED,
        "never tell the chain at all",
        GATE_AND_DROP,
        "",
        "the two closed-window chain tests",
    ),
    (
        10,
        OBSERVED,
        "finally becomes a plain trailing await",
        WRAPPER_BODY,
        WRAPPER_NO_FINALLY,
        "test_the_calculation_is_picked_up_even_if_the_credit_raises",
    ),
    (
        11,
        OBSERVED,
        "ceiling returns maximum_duration without the margin",
        "        return float(max_dur) + const.OBSERVED_CAP_MARGIN_SECONDS, substituted\n",
        "        return float(max_dur), substituted\n",
        "the two ceiling tests",
    ),
    (
        12,
        OBSERVED,
        "substituted is always False",
        "        substituted = not max_dur or max_dur < 0\n",
        "        substituted = False\n",
        "the default-ceiling test",
    ),
    (
        13,
        OBSERVED,
        "the wrapper drops the measured volume",
        "                measured_l=measured_l,\n",
        "                measured_l=None,\n",
        "test_the_finish_hands_the_credit_everything_the_close_edge_measured",
    ),
    (
        14,
        OBSERVED,
        "the wrapper drops sensor_present",
        "                sensor_present=sensor_present,\n",
        "                sensor_present=False,\n",
        "test_the_finish_hands_the_credit_everything_the_close_edge_measured",
    ),
    (
        15,
        OBSERVED,
        "un-harden the ceiling read (no float coercion)",
        COERCE,
        "        try:\n            pass\n        except (TypeError, ValueError):\n",
        "the non-numeric maximum tests",
    ),
    (
        16,
        OBSERVED,
        "the close edge drops the measured volume",
        "                    zone_id, seconds, measured_l=measured, sensor_present=sensor_present\n",
        "                    zone_id, seconds, measured_l=None, sensor_present=sensor_present\n",
        "test_close_edge_credits_measured_flow_end_to_end",
    ),
]


def read_src(path):
    raw = io.open(path, "rb").read()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def write_src(path, text, crlf):
    out = text.replace("\n", "\r\n") if crlf else text
    io.open(path + ".tmp", "wb").write(out.encode("utf-8"))
    os.replace(path + ".tmp", path)


def run_suites():
    """Return the set of 'FAILED/ERROR tests/...' names."""
    env = dict(os.environ)
    env.update(TMPDIR=TMP, TEMP=TMP, TMP=TMP)
    proc = subprocess.run(
        [PY, "-m", "pytest", *SUITES, "-p", "_local_socket_unblock", "-q"],
        cwd=WT,
        env=env,
        capture_output=True,
        text=True,
    )
    names = set()
    for line in (proc.stdout + proc.stderr).splitlines():
        if line.startswith(("FAILED tests/", "ERROR tests/")):
            names.add(line.split(" - ")[0].strip())
    collected = [ln for ln in proc.stdout.splitlines() if "collected" in ln]
    return names, (collected[0] if collected else "NO COLLECTION LINE")


def main():
    os.makedirs(TMP, exist_ok=True)
    originals = {p: read_src(p) for p in {m[1] for m in MUTATIONS}}

    print("measuring the unmutated branch ...", flush=True)
    reference, collected = run_suites()
    print("  %s" % collected, flush=True)
    print("  pre-existing failures/errors: %d" % len(reference), flush=True)
    if "collected 0" in collected or "NO COLLECTION" in collected:
        raise SystemExit("the run collected nothing - every result would be a lie")

    results = []
    for n, path, label, old, new, expected in MUTATIONS:
        original, crlf = originals[path]
        count = original.count(old)
        if count != 1:
            print("MUT %2d: anchor appears %d times -- SKIPPED" % (n, count))
            results.append(
                {
                    "n": n,
                    "file": os.path.basename(path),
                    "mutation": label,
                    "result": "NOT APPLIED",
                    "why": "anchor appears %d times" % count,
                }
            )
            continue
        write_src(path, original.replace(old, new, 1), crlf)
        try:
            after, after_collected = run_suites()
        finally:
            write_src(path, original, crlf)
        extra = sorted(after - reference)
        row = {
            "n": n,
            "file": os.path.basename(path),
            "mutation": label,
            "expected_killer": expected,
            "result": "killed" if extra else "survived",
            "collected": after_collected,
        }
        if extra:
            row["killed_by"] = extra
        results.append(row)
        print(
            "MUT %2d %-52s %s%s"
            % (
                n,
                label,
                row["result"].upper(),
                (" by %d test(s)" % len(extra)) if extra else "",
            ),
            flush=True,
        )
        for name in extra:
            print("         %s" % name.split("::", 1)[-1], flush=True)

    io.open(
        r"D:\Entwicklung\HASI\issue64-work\mutations.json", "w", encoding="utf-8"
    ).write(json.dumps(results, indent=2))

    ok = all(read_src(p)[0] == originals[p][0] for p in originals)
    print("\nevery source restored byte-for-byte: %s" % ok)
    killed = sum(1 for r in results if r.get("result") == "killed")
    print("%d killed / %d applied / %d total" % (killed, len(results), len(MUTATIONS)))


if __name__ == "__main__":
    main()
