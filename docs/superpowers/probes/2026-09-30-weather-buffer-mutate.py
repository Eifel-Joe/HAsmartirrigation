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
H, S = PKG + "helpers.py", PKG + "store.py"
MUTATIONS = [
    ("M01", "local_naive_now returns the process clock", [
        (H, "    return dt_util.now().replace(tzinfo=None)\n",
            "    return datetime.now()\n")]),
    ("M02", "_process_timezone back to today's fixed offset (needs a DST zone)", [
        (H, "    return dateutil_tz.tzlocal()\n",
            "    return datetime.now().astimezone().tzinfo\n")]),
    ("M03", "coerce_stamp: an aware stored stamp on the process's clock again", [
        (H, "    if parsed.tzinfo is None:\n        return parsed\n"
            "    return dt_util.as_local(parsed).replace(tzinfo=None)\n",
            "    if parsed.tzinfo is None:\n        return parsed\n"
            "    if provenance == STAMP_FROM_STORE:\n"
            "        return parsed.astimezone(_process_timezone()).replace(tzinfo=None)\n"
            "    return dt_util.as_local(parsed).replace(tzinfo=None)\n")]),
    ("M04", "lift_legacy_stamp leaves a naive stamp as it is", [
        (H, "        parsed = parsed.replace(tzinfo=_process_timezone())\n",
            "        return value\n")]),
    ("M05", "lift_legacy_stamp reads a naive stamp in the machine's zone, not the seam", [
        (H, "        parsed = parsed.replace(tzinfo=_process_timezone())\n",
            "        parsed = parsed.astimezone(_process_timezone())\n")]),
    ("M06", "lift_legacy_stamp returns a datetime, not a string", [
        (H, "    return dt_util.as_local(parsed).replace(tzinfo=None).isoformat()\n",
            "    return dt_util.as_local(parsed).replace(tzinfo=None)\n")]),
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
    for rel, old, new in edits:
        text, crlf = read(rel)
        if text.count(old) != 1:
            raise SystemExit(f"{rel}: {text.count(old)}x {old[:60]!r}")
        write(rel, text.replace(old, new), crlf)


def run_tests(tz_utc=True):
    env = dict(os.environ)
    if tz_utc:
        env["TZ"] = "UTC"
    else:
        env.pop("TZ", None)
    cmd = [PY, "-m", "pytest", *TESTS, "-p", "_local_socket_unblock", "-q", "--no-header",
           "--tb=no", "-rf", "-p", "no:cacheprovider"]
    try:
        out = subprocess.run(cmd, cwd=WT, env=env, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        # subprocess.run kills its own child on the timeout; nothing else is touched.
        return "HANG", [], ""
    summary = [line for line in out.stdout.splitlines() if re.match(r"^=+ .* in [\d.]+s", line)]
    failed = sorted({m.group(1) for m in re.finditer(r"^FAILED (\S+)", out.stdout, re.M)})
    collected = bool(summary) and "no tests ran" not in summary[-1]
    if not collected:
        return "NOT-RUN", failed, summary[-1] if summary else out.stdout[-300:]
    return ("KILLED" if failed or " error" in summary[-1] else "SURVIVED"), failed, summary[-1]


def main():
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
    out = pathlib.Path(__file__).with_name("mutations-result.json")
    out.write_text(json.dumps({"results": results, "all_restored": all_back}, indent=2),
                   encoding="utf-8")


main()
