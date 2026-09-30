"""Mutation matrix for the weather-buffer-on-one-clock change (Task 8 of the plan).

    python mutate.py <worktree>            # every mutation
    MUT_ONLY=M02 python mutate.py <wt>     # one mutation (comma list allowed)

Each mutation: apply (exact match, line endings kept), run the test subset under
TZ=UTC with a timeout, record KILLED/SURVIVED/HANG and the failing test names, restore
the touched files byte for byte. At the end every source file's sha256 is compared with
the snapshot taken before the first mutation.
"""
import ast
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

WT = pathlib.Path(sys.argv[1]).resolve()
PKG = "custom_components/irrigation_plus/"
PY = "D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe"
TIMEOUT = int(os.environ.get("MUT_TIMEOUT", "300"))
TESTS = [
    "tests/test_weather_buffer_one_frame.py",
    "tests/test_store_stamp_migration.py",
    "tests/test_time_provenance.py",
    "tests/test_live_estimate_time_provenance.py",
    "tests/test_weather_aggregate.py",
    "tests/test_continuous_update.py",
    "tests/test_store_operations.py",
    "tests/test_zone_view_save.py",
]


def read(rel):
    raw = (WT / rel).read_bytes().decode("utf-8")
    return raw.replace("\r\n", "\n"), "\r\n" in raw


def write(rel, text, crlf):
    (WT / rel).write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def sha(rel):
    return hashlib.sha256((WT / rel).read_bytes()).hexdigest()


# --- the hand-written mutations ------------------------------------------------------
H, S, W = PKG + "helpers.py", PKG + "store.py", PKG + "weather_aggregate.py"
NOW_LINE = "    now = coerce_stamp(now, STAMP_FROM_STORE) if now is not None else local_naive_now()\n"
NOW_STRIPPED = "    now = now.replace(tzinfo=None) if now is not None else local_naive_now()\n"
L = PKG + "live_estimate.py"
CLIENT_LINE = "                when = coerce_stamp(when, STAMP_FROM_CLIENT)\n"
MUTATIONS = [
    ("M01", "local_naive_now returns the process clock", [
        (H, "    return dt_util.now().replace(tzinfo=None)\n",
            "    return datetime.now()\n")]),
    ("M02", "_process_timezone back to today's fixed offset (needs a DST zone)", [
        (H, "    return dateutil_tz.tzlocal()\n",
            "    return datetime.now().astimezone().tzinfo\n")]),
    # From the review of Task 2: fixed offsets a UTC process cannot tell from tzlocal() in
    # process; the child-process test in test_time_provenance.py is what sees them.
    ("M02b", "_process_timezone returns UTC", [
        (H, "    return dateutil_tz.tzlocal()\n",
            "    return dateutil_tz.tzutc()\n")]),
    ("M02c", "_process_timezone returns a fixed standard offset", [
        (H, "    return dateutil_tz.tzlocal()\n",
            "    return dateutil_tz.tzoffset(None, -__import__(\"time\").timezone)\n")]),
    ("M03", "coerce_stamp: an aware stored stamp on the process's clock again", [
        (H, "    if parsed.tzinfo is None:\n        return parsed\n"
            "    try:\n        return dt_util.as_local(parsed).replace(tzinfo=None)\n",
            "    if parsed.tzinfo is None:\n        return parsed\n"
            "    if provenance == STAMP_FROM_STORE:\n"
            "        return parsed.astimezone(_process_timezone()).replace(tzinfo=None)\n"
            "    try:\n        return dt_util.as_local(parsed).replace(tzinfo=None)\n")]),
    ("M04", "lift_legacy_stamp leaves a naive stamp as it is", [
        (H, "            parsed = parsed.replace(tzinfo=_process_timezone())\n",
            "            return value\n")]),
    ("M05", "lift_legacy_stamp reads a naive stamp in the machine's zone, not the seam", [
        (H, "            parsed = parsed.replace(tzinfo=_process_timezone())\n",
            "            parsed = parsed.astimezone(_process_timezone())\n")]),
    ("M06", "lift_legacy_stamp returns a datetime, not a string", [
        (H, "        return dt_util.as_local(parsed).replace(tzinfo=None).isoformat()\n",
            "        return dt_util.as_local(parsed).replace(tzinfo=None)\n")]),
    ("M07", "the stamp step keyed on 14.1 instead of 14.2", [
        (S, "        if (old_major_version, old_minor_version) < (14, 2):\n",
            "        if (old_major_version, old_minor_version) < (14, 1):\n")]),
    ("M08", "the stamp step on every load, 14.2 included", [
        (S, "        if (old_major_version, old_minor_version) < (14, 2):\n",
            "        if True:\n")]),
    ("M09", "STORAGE_MINOR_VERSION stays 1", [
        (S, "STORAGE_MINOR_VERSION = 2\n", "STORAGE_MINOR_VERSION = 1\n")]),
    ("M10", "a MAJOR bump instead (STORAGE_VERSION 15)", [
        (S, "STORAGE_VERSION = 14\n", "STORAGE_VERSION = 15\n")]),
    ("M11", "the buffer rows are not moved", [
        (S, "                    row[RETRIEVED_AT] = lift_legacy_stamp(row[RETRIEVED_AT])\n",
            "                    pass\n")]),
    ("M12", "data_last_updated is not moved", [
        (S, "            mapping[MAPPING_DATA_LAST_UPDATED] = lift_legacy_stamp(\n"
            "                mapping[MAPPING_DATA_LAST_UPDATED]\n            )\n",
            "            pass\n")]),
    ("M13", "last_calculated is not moved", [
        (S, "        for key in (ZONE_LAST_CALCULATED, ZONE_LAST_CONSUMED, ZONE_LAST_UPDATED):\n",
            "        for key in (ZONE_LAST_CONSUMED, ZONE_LAST_UPDATED):\n")]),
    ("M14", "the hook never runs the stamp step", [
        (S, "        data = await self._async_migrate_major(old_major_version, data)\n",
            "        return await self._async_migrate_major(old_major_version, data)\n")]),
    # From the review of Task 3: the call sites convert an aware value; dropping its zone
    # instead passed while every aware twin was written in HA's own zone.
    ("M15", "select_window drops an aware watermark's zone instead of reading it", [
        (W, "    watermark = coerce_stamp(watermark, STAMP_FROM_STORE)\n",
            "    watermark = (watermark.replace(tzinfo=None) if isinstance(watermark, "
            "datetime.datetime) else coerce_stamp(watermark, STAMP_FROM_STORE))\n")]),
    ("M16", "aggregate_window drops an aware now's zone instead of reading it", [
        (W, NOW_LINE, NOW_STRIPPED, 0)]),
    ("M17", "build_hourly_rows drops an aware now's zone instead of reading it", [
        (W, NOW_LINE, NOW_STRIPPED, 1)]),
    ("M18", "build_substeps drops an aware now's zone instead of reading it", [
        (W, NOW_LINE, NOW_STRIPPED, 2)]),
    # From the review of Task 4: the aware branch, the microseconds, a later major, the
    # dict guards, and a conversion that must not raise out of the store's load.
    ("M23", "lift_legacy_stamp re-reads an aware stamp in the process zone", [
        (H, "        if parsed.tzinfo is None:\n"
            "            parsed = parsed.replace(tzinfo=_process_timezone())\n",
            "        if True:\n"
            "            parsed = parsed.replace(tzinfo=_process_timezone())\n")]),
    ("M24", "lift_legacy_stamp drops the microseconds", [
        (H, "        return dt_util.as_local(parsed).replace(tzinfo=None).isoformat()\n",
            "        return dt_util.as_local(parsed).replace(tzinfo=None)"
            ".isoformat(timespec=\"seconds\")\n")]),
    ("M25", "the stamp step checks the minor only", [
        (S, "        if (old_major_version, old_minor_version) < (14, 2):\n",
            "        if old_minor_version < 2:\n")]),
    ("M26", "no dict guard for a zone in the stamp step", [
        (S, "    for zone in data.get(\"zones\") or []:\n        if not isinstance(zone, dict):\n"
            "            continue\n",
            "    for zone in data.get(\"zones\") or []:\n")]),
    ("M27", "no dict guard for a mapping in the stamp step", [
        (S, "    for mapping in data.get(\"mappings\") or []:\n"
            "        if not isinstance(mapping, dict):\n            continue\n",
            "    for mapping in data.get(\"mappings\") or []:\n")]),
    ("M28", "lift_legacy_stamp lets an out-of-range conversion raise", [
        (H, "    except (ValueError, OverflowError, OSError):\n        return value\n",
            "    except ValueError:\n        return value\n")]),
    ("M29", "coerce_stamp lets an out-of-range conversion raise", [
        (H, "    try:\n        return dt_util.as_local(parsed).replace(tzinfo=None)\n"
            "    except OverflowError:\n",
            "    if True:\n        return dt_util.as_local(parsed).replace(tzinfo=None)\n"
            "    if False:\n")]),
    ("M30", "_parse_stored_as_ha_local lets an out-of-range conversion raise", [
        (L, "            try:\n                return dt_util.as_local(value).replace(tzinfo=None)\n"
            "            except OverflowError:\n",
            "            if True:\n                return dt_util.as_local(value).replace(tzinfo=None)\n"
            "            if False:\n")]),
    # From the review of Task 5: the live refresh's own clock read, and the two writers
    # whose stamp the matrix could not tell from the zone's creation stamp.
    ("M31", "the live refresh reads the process clock", [
        (L, "        now = dt_util.now()\n        offset = now.utcoffset()\n",
            "        now = datetime.datetime.now()\n        offset = now.utcoffset()\n")]),
    ("M32", "clearing the weather data does not stamp the watermark", [
        (PKG + "calculation.py", "                {\n                    const.ZONE_LAST_CONSUMED: now,\n",
            "                {\n")]),
    ("M33", "a sensor group switching its source does not stamp the watermark", [
        (PKG + "__init__.py",
            "                        {\n                            const.ZONE_LAST_CONSUMED: now,\n",
            "                        {\n")]),
    # From the re-review of Task 3: the weather-entity reader, the first of the three
    # identical client conversions in live_estimate.py, was pinned by nothing.
    ("M20", "the weather-entity reader drops an aware row's zone", [
        (L, CLIENT_LINE, "                when = when.replace(tzinfo=None)\n", 0)]),
    ("M21", "the weather-entity reader reads an aware row at UTC wall time", [
        (L, CLIENT_LINE, "                when = dt_util.as_utc(when).replace(tzinfo=None)\n", 0)]),
    ("M22", "the weather-entity reader leaves an aware row aware", [
        (L, CLIENT_LINE, "                when = when\n", 0)]),
    ("M19", "coerce_stamp returns None before refusing an unknown provenance", [
        (H, "    if provenance not in (STAMP_FROM_STORE, STAMP_FROM_CLIENT):\n"
            "        raise ValueError(f\"unknown timestamp provenance: {provenance!r}\")\n"
            "    if value is None:\n        return None\n",
            "    if value is None:\n        return None\n"
            "    if provenance not in (STAMP_FROM_STORE, STAMP_FROM_CLIENT):\n"
            "        raise ValueError(f\"unknown timestamp provenance: {provenance!r}\")\n")]),
]


# --- the 19 clock sites, each reverted on its own --------------------------------------
# A realistic regression: the stdlib clock imported and called by its usual name, which
# is what the census looks for.
IMPORT_FOR = {
    PKG + "calculation.py": ("from datetime import timedelta\n",
                             "from datetime import datetime, timedelta\n", "datetime.now()"),
    PKG + "continuous_update.py": ("from datetime import timedelta\n",
                                   "from datetime import datetime, timedelta\n", "datetime.now()"),
    PKG + "__init__.py": ("from datetime import timedelta\n",
                          "from datetime import datetime as dt_datetime\nfrom datetime import timedelta\n",
                          "dt_datetime.now()"),
    PKG + "store.py": (None, None, "datetime.datetime.now()"),
    PKG + "weather_aggregate.py": (None, None, "datetime.datetime.now()"),
}


def clock_sites():
    sites = []
    for rel, (imp_old, imp_new, call) in IMPORT_FOR.items():
        text, _ = read(rel)
        tree = ast.parse(text)
        calls = sorted(
            (n.lineno, n.col_offset)
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "local_naive_now"
        )
        for lineno, col in calls:
            sites.append((rel, lineno, col, imp_old, imp_new, call))
    return sites


def apply_site(site):
    rel, lineno, col, imp_old, imp_new, call = site
    text, crlf = read(rel)
    lines = text.split("\n")
    line = lines[lineno - 1]
    assert line[col:].startswith("local_naive_now()"), (rel, lineno, line)
    lines[lineno - 1] = line[:col] + call + line[col + len("local_naive_now()"):]
    text = "\n".join(lines)
    if imp_old:
        if text.count(imp_old) != 1:
            raise SystemExit(f"{rel}: import anchor {imp_old!r} not unique")
        text = text.replace(imp_old, imp_new)
    write(rel, text, crlf)


def apply_mutation(edits):
    """Each edit is (file, old, new) -- old must be unique -- or (file, old, new, n): the
    n-th occurrence (from 0) of an old text that occurs several times."""
    for rel, old, new, *nth in edits:
        text, crlf = read(rel)
        count = text.count(old)
        if not nth:
            if count != 1:
                raise SystemExit(f"{rel}: {count}x {old[:60]!r}")
            write(rel, text.replace(old, new), crlf)
            continue
        if nth[0] >= count:
            raise SystemExit(f"{rel}: occurrence {nth[0]} of {count} {old[:60]!r}")
        at = -1
        for _ in range(nth[0] + 1):
            at = text.index(old, at + 1)
        write(rel, text[:at] + new + text[at + len(old):], crlf)


def run_with_timeout(cmd, env, cwd=None, timeout=None):
    """stdout of ``cmd``, or None when it outlives the timeout (a mutation can deadlock a test).

    The venv's ``python.exe`` on Windows is only a launcher: pytest runs in a child process.
    ``kill()`` would stop the launcher and leave pytest running with our pipes open, so the
    whole tree of THIS process id is killed -- nothing is matched by name.
    """
    proc = subprocess.Popen(cmd, cwd=cwd or WT, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace")
    try:
        out, _ = proc.communicate(timeout=timeout or TIMEOUT)
        return out
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        proc.communicate()
        return None


def run_tests(tz_utc=True):
    env = dict(os.environ)
    if tz_utc:
        env["TZ"] = "UTC"
    else:
        env.pop("TZ", None)
    cmd = [PY, "-m", "pytest", *TESTS, "-p", "_local_socket_unblock", "-q", "--no-header",
           "--tb=no", "-rf", "-p", "no:cacheprovider"]
    stdout = run_with_timeout(cmd, env)
    if stdout is None:
        return "HANG", [], ""
    summary = [line for line in stdout.splitlines() if re.match(r"^=+ .* in [\d.]+s", line)]
    failed = sorted({m.group(1) for m in re.finditer(r"^FAILED (\S+)", stdout, re.M)})
    collected = bool(summary) and "no tests ran" not in summary[-1]
    if not collected:
        return "NOT-RUN", failed, summary[-1] if summary else stdout[-300:]
    return ("KILLED" if failed or " error" in summary[-1] else "SURVIVED"), failed, summary[-1]


def main():
    if os.environ.get("MUT_SELFTEST_TIMEOUT"):
        # Exercise the timeout path alone: a child that sleeps past a short timeout.
        started = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.count("python")
        out = run_with_timeout([PY, "-c", "import time; time.sleep(60)"], dict(os.environ),
                               cwd=pathlib.Path.cwd(), timeout=3)
        after = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.count("python")
        print(f"timeout path returned {'HANG' if out is None else 'OUTPUT'}; "
              f"python processes before {started}, after {after}")
        quick = run_with_timeout([PY, "-c", "print('collected fine')"], dict(os.environ),
                                 cwd=pathlib.Path.cwd(), timeout=30)
        print(f"normal path returned {quick!r}")
        return
    only = set(filter(None, os.environ.get("MUT_ONLY", "").split(",")))
    sources = [p.relative_to(WT).as_posix() for p in (WT / PKG).rglob("*.py")]
    snapshot = {rel: sha(rel) for rel in sources}
    results = []
    sites = clock_sites()
    jobs = [(mid, desc, ("edits", edits)) for mid, desc, edits in MUTATIONS]
    for i, site in enumerate(sites, start=1):
        rel, lineno = site[0], site[1]
        jobs.append((f"S{i:02d}", f"{rel.split('/')[-1]}:{lineno} back on the process clock",
                     ("site", site)))
    for mid, desc, (kind, payload) in jobs:
        if only and mid not in only:
            continue
        touched = [payload[0]] if kind == "site" else sorted({e[0] for e in payload})
        backup = {rel: (WT / rel).read_bytes() for rel in touched}
        try:
            apply_site(payload) if kind == "site" else apply_mutation(payload)
            verdict, failed, summary = run_tests(tz_utc=True)
            if mid == "M02":  # only a DST process zone shows a fixed offset
                v2, f2, s2 = run_tests(tz_utc=False)
                verdict, failed, summary = (
                    f"UTC:{verdict} / no-TZ:{v2}", sorted(set(failed) | set(f2)), s2
                )
        finally:
            for rel, data in backup.items():
                (WT / rel).write_bytes(data)
        restored = all(sha(rel) == snapshot[rel] for rel in touched)
        results.append({"id": mid, "what": desc, "verdict": verdict, "restored": restored,
                        "killed_by": failed, "summary": summary})
        print(f"{mid} {verdict:24} restored={restored} | {desc} | {len(failed)} failing")
        sys.stdout.flush()
    all_back = all(sha(rel) == h for rel, h in snapshot.items())
    print(f"every source restored byte-for-byte: {all_back}")
    out = pathlib.Path(__file__).with_name("mutations-result-impl.json")
    out.write_text(json.dumps({"results": results, "all_restored": all_back}, indent=2),
                   encoding="utf-8")


main()
