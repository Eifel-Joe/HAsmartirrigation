"""Apply each mutation, run the PR 3 test files, record, revert.

The engine of issue8-pr2-work/sdd/mutate-pr2b.py, unchanged: pytest only, an anchor
must appear exactly once, a run whose summary shows no passed/failed count is
BROKEN (never "survived"), a run that outlives MUT_TIMEOUT seconds is killed with
its process tree and reported HANG, a .bak copy and the sha256 of every mutated
source before anything is touched, the sha256 compared after EVERY restore, and a
final `git diff --quiet HEAD`.

Run:
    python mutate-pr3.py [worktree] [out.json]
Env:
    MUT_CHECK=1    only count the anchors (no pytest)
    MUT_ONLY="1,5" run only these mutations
    MUT_TIMEOUT    seconds per pytest run (default 300)
"""

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else r"D:\Entwicklung\HASI\issue8-pr3-work\probe-wt"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"D:\Entwicklung\HASI\issue8-pr3-work\mutations-pr3.json"
PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
PROBE = r"D:\Entwicklung\HASI\issue8-pr3-work"
TMP = os.path.join(PROBE, "tmp")
BAK = os.path.join(PROBE, "mutate-bak")
RUN_TIMEOUT = int(os.environ.get("MUT_TIMEOUT", "300"))
ONLY = {int(n) for n in os.environ.get("MUT_ONLY", "").split(",") if n.strip()}
CHECK = os.environ.get("MUT_CHECK") == "1"

IP = os.path.join(WT, "custom_components", "irrigation_plus")
LIVE = os.path.join(IP, "sensor_liveness.py")
AGG = os.path.join(IP, "weather_aggregate.py")
CALC = os.path.join(IP, "calculation.py")
EST = os.path.join(IP, "et_estimate.py")
LE = os.path.join(IP, "live_estimate.py")

# Every killer named below lives in one of these.
SUITES = [
    "tests/test_sensor_liveness_blocked.py",
    "tests/test_hourly_rows_blocked.py",
    "tests/test_substeps_blocked.py",
    "tests/test_silent_sensor_hourly_commit.py",
    "tests/test_silent_sensor_commit.py",
    "tests/test_sensor_liveness_coordinator.py",
    "tests/test_live_estimate_silent_sensor.py",
    "tests/test_live_estimate_silent_sensor_daily.py",
]

MUTATIONS = [
    # --- sensor_liveness.py
    (1, LIVE, "zone_blocked_spans: a group that keeps is cut too",
     "    if not mapping or not group_pauses(mapping):\n        return None\n    start = coerce_stamp",
     "    if not mapping:\n        return None\n    start = coerce_stamp",
     "test_a_group_that_keeps_is_not_cut"),
    (2, LIVE, "zone_blocked_spans: a rain gauge is cut too",
     "        if cuts_field(field, config)\n    }\n    return blocked or None\n",
     "    }\n    return blocked or None\n",
     "test_a_rain_gauge_is_never_cut_and_a_rain_rate_is"),
    (3, LIVE, "zone_blocked_spans: a zone without a window start is cut",
     "    if start is None or end is None:\n        return None\n",
     "    if end is None:\n        return None\n",
     "test_no_group_no_start_or_no_window_is_not_cut"),
    (4, LIVE, "the notice is plain again under the hourly calculation",
     "        return group_pauses(mapping)\n\n    def _stale_issue_key",
     "        return group_pauses(mapping) and not getattr(\n"
     "            getattr(self.store, \"config\", None), const.CONF_HOURLY_CALCULATION, False\n"
     "        )\n\n    def _stale_issue_key",
     "test_under_the_hourly_calculation_too_they_are_no_longer_used"),
    (5, LIVE, "a group that keeps refreshes the estimates too",
     "        return bool(opened or closed) and group_pauses(mapping)\n",
     "        return bool(opened or closed)\n",
     "test_a_group_that_keeps_does_not"),
    (6, LIVE, "an outage that opens refreshes nothing",
     "        if cut_changed:\n            await self._refresh_estimates_after_outage_change()\n",
     "",
     "test_an_outage_that_opens_refreshes_the_estimates"),
    (7, LIVE, "a failing refresh breaks the check",
     "        try:\n            await refresh()\n        except Exception:  # noqa: BLE001 — an estimate must not break the check\n"
     "            _LOGGER.debug(\"Live estimate refresh after an outage failed\", exc_info=True)\n",
     "        await refresh()\n",
     "test_a_refresh_that_fails_leaves_the_check_intact"),
    (8, LIVE, "every group of a check refreshes on its own",
     "                if await self._async_check_mapping_liveness(mapping, now):\n                    cut_changed = True\n",
     "                if await self._async_check_mapping_liveness(mapping, now):\n"
     "                    await self._refresh_estimates_after_outage_change()\n",
     "test_two_groups_in_one_check_refresh_once"),
    # --- calculation.py
    (9, CALC, "the commit's gate on the hourly calculation is back",
     "        return zone_blocked_spans(\n",
     "        if hourly_calculation_enabled(self.store):\n            return None\n        return zone_blocked_spans(\n",
     "test_the_hourly_calculation_is_cut_the_same"),
    (10, CALC, "the hourly form needs only the daily fields",
     "    if hourly and module_name == \"PyETO\":\n",
     "    if False:\n",
     "test_the_hourly_form_needs_temperature_humidity_wind_and_sun"),
    (11, CALC, "the share is taken with the daily fields in the hourly form",
     "            m[const.MODULE_NAME], hourly=hourly is not None\n",
     "            m[const.MODULE_NAME], hourly=False\n",
     "test_humidity_counts_in_the_hourly_form"),
    (12, CALC, "the hourly total is scaled by the share a second time",
     "            et_term = -hourly_total\n            et_delta = et_term * kc\n",
     "            et_term = -hourly_total\n            et_delta = et_term * kc\n"
     "            if share is not None:\n                et_delta *= share\n",
     "test_it_books_the_rows_once_and_names_the_share"),
    (13, CALC, "the hourly rows are not handed the spans",
     "            self._hourly_et_for_zone(zone, modinst, now=now, blocked=blocked)\n",
     "            self._hourly_et_for_zone(zone, modinst, now=now, blocked=None)\n",
     "test_it_books_the_rows_once_and_names_the_share"),
    (14, CALC, "the replay is not handed the spans",
     "            blocked=blocked,\n            required=required or (),\n",
     "            blocked=None,\n            required=required or (),\n",
     "test_it_still_replays_under_a_blocked_rain_rate"),
    # --- weather_aggregate.py / et_estimate.py
    (15, AGG, "a blocked hour keeps its readings and is priced",
     "        if _books_nothing(row):\n            # No time in this hour",
     "        if False:\n            # No time in this hour",
     "test_hours_inside_a_span_stay_as_rows_without_et"),
    (16, AGG, "an hour is charged its whole coverage",
     "                coverage if booked is None else _overlap_hours(booked, a, b)\n",
     "                coverage\n",
     "test_a_partly_blocked_hour_is_charged_its_measured_part"),
    (17, AGG, "a blocked field is held into its span",
     "            None\n            if _blocked_at(a, mask)\n",
     "            None\n            if False\n",
     "test_two_fields_silent_in_different_parts_of_one_hour"),
    (18, AGG, "a frozen reading inside a span is used",
     "    mask = spans if mask is None else mask\n    kept = sorted(\n"
     "        ((t, v) for t, v in samples if t <= start or not _blocked_at(t, spans)),\n",
     "    mask = spans if mask is None else mask\n    kept = sorted(\n"
     "        ((t, v) for t, v in samples),\n",
     "test_a_frozen_value_stamped_inside_a_span_is_not_used"),
    (19, AGG, "a required field with nothing to hold books as if measured",
     "            booked = []\n",
     "            booked = None\n",
     "test_a_field_whose_every_reading_is_inside_a_span_books_nothing"),
    (20, AGG, "frozen solar inside a span feeds the ratio",
     "                solar_samples = [\n                    (t, v)\n                    for t, v in samples\n"
     "                    if t <= start or not _blocked_at(t, spans)\n                ]\n",
     "                solar_samples = samples\n",
     "test_frozen_solar_inside_a_span_changes_no_row"),
    (21, AGG, "the ratio hold refills a blocked hour",
     "        if row[\"hour_start\"] in newest or _books_nothing(row):\n",
     "        if row[\"hour_start\"] in newest:\n",
     "test_after_the_span_the_ratio_from_before_holds"),
    (22, EST, "a row covering no time is priced",
     "        if r.get(\"coverage_h\", 1.0) <= 0:\n            out.append(0.0)\n            continue\n",
     "",
     "test_the_series_charges_such_a_row_nothing"),
    (23, AGG, "a blocked rain rate's pair counts whole",
     "            for a, b in segments:\n                lo, hi = max(a, t0), min(b, t1)\n"
     "                if hi > lo:\n"
     "                    out.append((hi, (v0 + v1) / 2 * (hi - lo).total_seconds() / 3600))\n",
     "            out.append((t1, (v0 + v1) / 2 * (t1 - t0).total_seconds() / 3600))\n",
     "test_a_blocked_rain_rate_adds_only_its_measured_rain"),
    (24, AGG, "rain lands at the next reading, not at the end of its measured part",
     "                    out.append((hi, (v0 + v1) / 2 * (hi - lo).total_seconds() / 3600))\n",
     "                    out.append((t1, (v0 + v1) / 2 * (hi - lo).total_seconds() / 3600))\n",
     "test_rain_just_before_a_span_lands_before_it"),
    (25, AGG, "the replay places ET where a required field was silent",
     "            for key in {*required, const.MAPPING_SOLRAD}\n",
     "            for key in {const.MAPPING_SOLRAD}\n",
     "test_a_required_field_silent_places_no_et_there"),
    (26, AGG, "the replay weighs the sun's own silent time",
     "            for key in {*required, const.MAPPING_SOLRAD}\n",
     "            for key in {*required}\n",
     "test_silent_sun_places_no_et_in_its_span_either"),
    (27, AGG, "a dark hour spreads its ET over its silent part too",
     "        weights = _weights_from_hourly_et(weights, hours, measured, hourly_et)\n",
     "        weights = _weights_from_hourly_et(\n            weights, hours, [dt for dt, _, _ in steps], hourly_et\n        )\n",
     "test_a_dark_hour_spreads_its_quantum_over_its_measured_time"),
    (28, AGG, "a window with no measured time is not stepped",
     "            weights = [dt for dt, _, _ in steps]\n            total = sum(weights)\n            if total <= 0:\n                return None\n",
     "            return None\n",
     "test_a_window_with_no_measured_time_still_steps"),
    # --- live_estimate.py
    (29, LE, "the carry ignores the outage record",
     "            and carry.outages == outages\n",
     "",
     "test_an_outage_that_closes_drops_the_carried_hours"),
    (30, LE, "the hourly source is not handed the spans",
     "                geometry=geometry,\n                blocked=blocked,\n            )\n            hourly_et = None\n",
     "                geometry=geometry,\n                blocked=None,\n            )\n            hourly_et = None\n",
     "test_the_hourly_source_agrees_with_the_commit"),
    (31, LE, "the live aggregate is not handed the spans",
     "            blocked=blocked,\n        )\n\n    def _observed_precip_since_mm",
     "            blocked=None,\n        )\n\n    def _observed_precip_since_mm",
     "test_it_lands_on_the_cut_bucket"),
    (32, LE, "a silent temperature is read as current",
     "        if now is not None and any(hi >= now for _, hi in spans):\n",
     "        if False:\n",
     "test_a_silent_temperature_is_not_read_as_current"),
    (33, LE, "an ended temperature span still counts as silent now",
     "        if now is not None and any(hi >= now for _, hi in spans):\n",
     "        if now is not None and bool(spans):\n",
     "test_a_silent_temperature_is_not_read_as_current"),
    (34, LE, "the mirror books the whole window",
     "            total *= share\n",
     "            total *= 1.0\n",
     "test_it_lands_on_the_cut_bucket"),
    (35, LE, "nothing measured sends the chain on",
     "                    return _DayTotal(0.0, TIER_OBSERVED)\n",
     "                    return None\n",
     "test_it_does_not_fall_back_to_a_weather_service"),
    (36, LE, "the hourly source's rain is not cut",
     "                precip_mm = self._observed_precip_since_mm(\n"
     "                    zone, anchor, now=now_local, blocked=blocked\n                )\n"
     "                method = \"hourly_sensor\"\n",
     "                precip_mm = self._observed_precip_since_mm(\n"
     "                    zone, anchor, now=now_local, blocked=None\n                )\n"
     "                method = \"hourly_sensor\"\n",
     "test_a_blocked_rain_rate_is_published_as_the_commit_books_it"),
    (37, LE, "the projection is priced off the uncut window",
     "            blocked = zone_blocked_spans(self.store, zone, anchor, now_local)\n"
     "            agg = self._aggregate_live_window(\n",
     "            blocked = None\n"
     "            agg = self._aggregate_live_window(\n",
     "test_it_is_priced_from_the_cut_window"),
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
