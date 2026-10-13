"""Apply each mutation, run the PR 2 test files, record, revert.

Engine from issue66-work/mutate.py (the archived copy in _erledigt/issue66-work):
pytest only, anchor must appear exactly once, a run whose summary shows no
passed/failed count is BROKEN (never "survived"), a run that outlives MUT_TIMEOUT
seconds is killed with its process tree and reported HANG. Added for this run: a
.bak copy and the sha256 of every mutated source before anything is touched, the
sha256 compared after EVERY restore, and a final `git diff --quiet HEAD`.

Run:
    python mutate-pr2.py [worktree] [out.json]
Env:
    MUT_CHECK=1   only count the anchors (no pytest)
    MUT_ONLY="1,5" run only these mutations
    MUT_TIMEOUT   seconds per pytest run (default 300)
"""

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else r"D:\Entwicklung\HASI\issue8-pr2-work\wt"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"D:\Entwicklung\HASI\issue8-pr2-work\sdd\mutations-pr2.json"
PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
PROBE = r"D:\Entwicklung\HASI\issue8-pr2-work\sdd"
TMP = os.path.join(PROBE, "tmp")
BAK = os.path.join(PROBE, "mutate-bak")
RUN_TIMEOUT = int(os.environ.get("MUT_TIMEOUT", "300"))
ONLY = {int(n) for n in os.environ.get("MUT_ONLY", "").split(",") if n.strip()}
CHECK = os.environ.get("MUT_CHECK") == "1"

IP = os.path.join(WT, "custom_components", "irrigation_plus")
LIVE = os.path.join(IP, "sensor_liveness.py")
AGG = os.path.join(IP, "weather_aggregate.py")
CALC = os.path.join(IP, "calculation.py")
STORE = os.path.join(IP, "store.py")
INIT = os.path.join(IP, "__init__.py")
WS = os.path.join(IP, "websockets.py")

# Every killer named below lives in one of these.
SUITES = [
    "tests/test_sensor_liveness_blocked.py",
    "tests/test_silent_sensor_setting.py",
    "tests/test_weather_aggregate_blocked.py",
    "tests/test_silent_sensor_commit.py",
    "tests/test_sensor_liveness_coordinator.py",
]

MUTATIONS = [
    (1, LIVE, "blocked_spans: no bridging of the first three hours",
     "        lo = max(outage.start + STALE_AFTER, start)\n",
     "        lo = max(outage.start, start)\n",
     "test_the_first_three_hours_are_bridged"),
    (2, LIVE, "blocked_spans: an outage of exactly three hours blocks a zero-length span",
     "        if hi <= lo:\n            continue\n",
     "        if hi < lo:\n            continue\n",
     "test_an_outage_of_three_hours_or_less_blocks_nothing"),
    (3, LIVE, "valid_share: the largest single blocked share instead of the union",
     "    spans = _merged([span for field in fields for span in blocked.get(field, ())])\n"
     "    gone = sum((hi - lo).total_seconds() for lo, hi in spans)\n",
     "    gone = max(\n"
     "        (\n"
     "            sum((hi - lo).total_seconds() for lo, hi in _merged(blocked.get(f, ())))\n"
     "            for f in fields\n"
     "        ),\n"
     "        default=0.0,\n"
     "    )\n",
     "test_two_fields_silent_at_different_hours_leave_their_intersection"),
    (4, LIVE, "group_pauses: case-insensitive comparison",
     "    return mapping.get(const.MAPPING_ON_SILENT_SENSOR) == const.ON_SILENT_SENSOR_PAUSE\n",
     "    return (\n"
     "        str(mapping.get(const.MAPPING_ON_SILENT_SENSOR)).lower()\n"
     "        == const.ON_SILENT_SENSOR_PAUSE\n"
     "    )\n",
     "test_only_a_stored_pause_pauses"),
    (5, AGG, "_blocked_at: closed interval, the span end is blocked too",
     "    return any(lo <= stamp < hi for lo, hi in spans)\n",
     "    return any(lo <= stamp <= hi for lo, hi in spans)\n",
     "test_the_reading_of_the_return_counts"),
    (6, AGG, "the boundary row is dropped when it lies in a span",
     "    kept = [(t, v) for t, v in stamped if t <= start or not _blocked_at(t, spans)]\n",
     "    kept = [(t, v) for t, v in stamped if not _blocked_at(t, spans)]\n",
     "test_a_window_that_starts_blocked_holds_the_boundary_after_the_span"),
    (7, AGG, "_segment_weighted_mean: each segment opens with the first value, not the held one",
     "        values = [_held(kept, a)] + [v for _, v in inner]\n",
     "        values = [kept[0][1]] + [v for _, v in inner]\n",
     "test_a_value_is_not_held_into_a_span_and_holds_again_after_it"),
    (8, AGG, "_riemann_over: the whole pair counts, not its valid part",
     "        valid = sum(\n"
     "            max(0.0, (min(b, t1) - max(a, t0)).total_seconds()) for a, b in segments\n"
     "        )\n",
     "        valid = (t1 - t0).total_seconds()\n",
     "test_a_rain_rate_is_integrated_over_its_valid_time_only"),
    (9, AGG, "a field without valid time is no longer left out",
     "    segments = _valid_segments(spans, start, end)\n    if not segments:\n        return\n",
     "    segments = _valid_segments(spans, start, end)\n",
     "test_a_field_blocked_throughout_is_left_out_and_not_filled"),
    (10, AGG, "a rain gauge (delta) is cut too",
     "            if aggregate != const.MAPPING_CONF_AGGREGATE_DELTA:\n",
     "            if True:\n",
     "test_a_rain_gauge_is_never_cut_even_if_asked"),
    (11, CALC, "the gate ignores the hourly calculation",
     "        if hourly_calculation_enabled(self.store):\n"
     "            return None\n"
     "        watermark = coerce_stamp(zone.get(const.ZONE_LAST_CONSUMED), STAMP_FROM_STORE)\n",
     "        watermark = coerce_stamp(zone.get(const.ZONE_LAST_CONSUMED), STAMP_FROM_STORE)\n",
     "test_with_the_hourly_calculation_nothing_is_cut"),
    (12, CALC, "the gate also cuts a rain gauge (no delta filter)",
     "            if effective_aggregate(field, config) != const.MAPPING_CONF_AGGREGATE_DELTA\n",
     "",
     "test_a_rain_gauge_is_never_cut_and_a_rain_rate_is"),
    (13, CALC, "PyETO is asked even when share is 0",
     "            if hourly is None and share != 0:\n",
     "            if hourly is None:\n",
     "test_pyeto_without_a_measured_required_field_books_the_rain_only"),
    (14, CALC, "Passthrough: share 0 no longer consumes quietly",
     "            if share == 0:\n                # Its ET sensor was silent",
     "            if False:\n                # Its ET sensor was silent",
     "test_passthrough_with_its_et_blocked_throughout_consumes_quietly"),
    (15, CALC, "the share does not scale the booking",
     "            if share is not None:\n"
     "                # Only the measured part of the window books; the forecast days\n"
     "                # the module averaged in are part of that mean.\n"
     "                et_delta *= share\n",
     "",
     "test_pyeto_books_the_share_in_which_its_fields_were_measured"),
    (16, CALC, "the amplitude record ignores a blocked temperature",
     "        if blocked and const.MAPPING_TEMPERATURE in blocked:\n            return\n",
     "",
     "test_no_amplitude_is_recorded_when_the_temperature_was_blocked"),
    (17, CALC, "the radiation record skips on any blocked field",
     "        if blocked and const.MAPPING_SOLRAD in blocked:\n",
     "        if blocked:\n",
     "test_no_radiation_pair_is_recorded_when_the_sun_was_blocked"),
    (18, CALC, "the share sentence also appears at a share of 1",
     "        if share is not None and share < 1:\n",
     "        if share is not None and share <= 1:\n",
     "test_a_field_the_module_does_without_gets_no_share_sentence"),
    (19, STORE, "an unknown stored setting pauses instead of keeping",
     "    return value if value in ON_SILENT_SENSOR_OPTIONS else ON_SILENT_SENSOR_KEEP\n",
     "    return value if value in ON_SILENT_SENSOR_OPTIONS else ON_SILENT_SENSOR_PAUSE\n",
     "test_a_stored_group_without_a_valid_setting_keeps"),
    (20, LIVE, "the notice always has the PR 1 key",
     "        if self._group_cuts(mapping):\n"
     "            return const.ISSUE_WEATHER_SENSOR_STALE_PAUSED\n",
     "        if False:\n"
     "            return const.ISSUE_WEATHER_SENSOR_STALE_PAUSED\n",
     "test_a_pausing_group_says_its_values_are_no_longer_used"),
    (21, INIT, "no re-sync of the notice when the hourly calculation is switched",
     "        if const.CONF_HOURLY_CALCULATION in data:\n"
     "            # A pausing group's notice says whether its values are left out,\n"
     "            # and only the daily form leaves them out.\n"
     "            for mapping in await self.store.async_get_mappings():\n"
     "                self.async_resync_stale_issue(mapping)\n",
     "",
     "test_switching_the_hourly_calculation_rewrites_open_notices"),
    (22, WS, "the mapping view accepts any string for the setting",
     "        vol.Optional(const.MAPPING_ON_SILENT_SENSOR): vol.In(\n"
     "            const.ON_SILENT_SENSOR_OPTIONS\n"
     "        ),\n",
     "        vol.Optional(const.MAPPING_ON_SILENT_SENSOR): cv.string,\n",
     "test_the_mapping_view_takes_the_setting_and_only_its_two_values"),
]


def read_bytes(path):
    with io.open(path, "rb") as f:
        return f.read()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def decode(raw):
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def encode(text, crlf):
    return (text.replace("\n", "\r\n") if crlf else text).encode("utf-8")


def run_pytest():
    env = dict(os.environ)
    env.update(TMPDIR=TMP, TEMP=TMP, TMP=TMP, TZ="UTC")
    proc = subprocess.Popen(
        [PY, "-m", "pytest", *SUITES, "-p", "_local_socket_unblock", "-q", "--no-header", "-rfE"],
        cwd=WT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace",
    )
    try:
        stdout, stderr = proc.communicate(timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        # The venv's python.exe is a launcher; pytest runs in its child, which a
        # plain kill() would leave running with the pipes open. Kill the tree.
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        proc.communicate()
        return set(), "HANG"
    names = set()
    for line in (stdout + stderr).replace("\r", "\n").splitlines():
        if line.startswith(("FAILED tests/", "ERROR tests/")):
            names.add(line.split(" - ")[0].strip())
    tail = [ln for ln in stdout.replace("\r", "\n").splitlines() if " passed" in ln or " failed" in ln]
    return names, (tail[-1].strip("= ") if tail else "NO SUMMARY LINE")


def collected(summary):
    return re.search(r"\d+ (passed|failed)", summary) is not None


def main():
    os.makedirs(TMP, exist_ok=True)
    os.makedirs(BAK, exist_ok=True)
    paths = sorted({m[1] for m in MUTATIONS})
    originals = {}
    for p in paths:
        raw = read_bytes(p)
        originals[p] = raw
        shutil.copyfile(p, os.path.join(BAK, os.path.basename(p) + ".bak"))
    shas = {p: sha(b) for p, b in originals.items()}
    print("sha256 before: " + ", ".join("%s=%s" % (os.path.basename(p), s[:12]) for p, s in shas.items()), flush=True)
    dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *paths], cwd=WT).returncode
    if dirty:
        raise SystemExit("a mutated source differs from HEAD - refusing to mutate over it")

    if CHECK:
        for n, path, label, old, new, expected in MUTATIONS:
            text, _ = decode(originals[path])
            print("MUT %2d anchor count %d  (%s)" % (n, text.count(old), os.path.basename(path)))
        return

    print("measuring the unmutated branch in %s ..." % WT, flush=True)
    reference, summary = run_pytest()
    print("  %s" % summary, flush=True)
    print("  pre-existing failures/errors: %d" % len(reference), flush=True)
    if not collected(summary) or " 0 passed" in summary:
        raise SystemExit("a run collected nothing - every result would be a lie")
    ref_failed = sorted(n for n in reference if n.startswith("FAILED"))
    if ref_failed:
        raise SystemExit("unmutated run has FAILED tests: %s" % ref_failed)

    results = []
    restored_ok = True
    for n, path, label, old, new, expected in MUTATIONS:
        if ONLY and n not in ONLY:
            continue
        text, crlf = decode(originals[path])
        count = text.count(old)
        if count != 1:
            print("MUT %2d: anchor appears %d times -- NOT APPLIED" % (n, count))
            results.append({"n": n, "file": os.path.basename(path), "mutation": label,
                            "result": "NOT APPLIED", "why": "anchor appears %d times" % count})
            continue
        with io.open(path, "wb") as f:
            f.write(encode(text.replace(old, new, 1), crlf))
        try:
            after, after_summary = run_pytest()
        finally:
            with io.open(path, "wb") as f:
                f.write(originals[path])
            ok = sha(read_bytes(path)) == shas[path]
            restored_ok = restored_ok and ok
            if not ok:
                print("!!! restore of %s differs from the original sha256" % path, flush=True)
        extra = sorted(after - reference)
        if after_summary == "HANG":
            result = "HANG"
        elif not collected(after_summary):
            result = "BROKEN"
        else:
            result = "KILLED" if extra else "SURVIVED"
        killers = [e.split("::", 1)[-1] for e in extra]
        hit = any(expected.split("[")[0] in k for k in killers)
        row = {"n": n, "file": os.path.basename(path), "mutation": label,
               "expected_killer": expected, "result": result, "summary": after_summary,
               "expected_killer_among_killers": hit, "killed_by": killers,
               "restored_sha256_ok": ok}
        results.append(row)
        print("MUT %2d %-8s %-72s %s" % (n, result, label[:72], after_summary), flush=True)
        for k in killers:
            print("           killer: %s" % k, flush=True)
        if result == "KILLED" and not hit:
            print("           (expected killer %s is NOT among them)" % expected, flush=True)

    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(results, indent=2))
    final_ok = all(sha(read_bytes(p)) == shas[p] for p in paths)
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *paths], cwd=WT).returncode == 0
    print("\nevery source restored byte-for-byte (sha256): %s; git diff --quiet HEAD: %s" % (final_ok and restored_ok, clean))
    killed = sum(1 for r in results if r.get("result") == "KILLED")
    applied = sum(1 for r in results if r.get("result") != "NOT APPLIED")
    print("%d killed / %d applied / %d total" % (killed, applied, len(MUTATIONS)))
    print("survived: %s; hang: %s; broken: %s; not applied: %s" % (
        [r["n"] for r in results if r.get("result") == "SURVIVED"],
        [r["n"] for r in results if r.get("result") == "HANG"],
        [r["n"] for r in results if r.get("result") == "BROKEN"],
        [r["n"] for r in results if r.get("result") == "NOT APPLIED"]))


if __name__ == "__main__":
    main()
