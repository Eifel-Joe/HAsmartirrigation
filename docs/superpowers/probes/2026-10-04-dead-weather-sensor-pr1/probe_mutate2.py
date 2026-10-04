"""Plan revision 2 (2026-10-04): the Task-14 mutations against the probe worktree.

M1-M16 as on 2026-10-03; M17-M20 guard JustChr's three repair-issue tests (recovery,
restart, deletion) and the ledger's reload. Every mutation runs against ALL four
liveness test files, so the verdict names every killer, not just the expected one.
A run that collected nothing or broke on import is reported as such, never as a
kill. Every file is restored afterwards, also on a hang.

Usage: python probe_mutate2.py <worktree root>
"""

import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1])
IP = ROOT / "custom_components" / "irrigation_plus"
PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
TESTS = [
    "tests/test_sensor_liveness.py",
    "tests/test_sensor_liveness_store.py",
    "tests/test_sensor_liveness_coordinator.py",
    "tests/test_sensor_liveness_repair.py",
]
SL = IP / "sensor_liveness.py"
INIT = IP / "__init__.py"

MUTATIONS = [
    (1, SL, "        candidates.extend(s.reported for s in siblings if s.valid)\n", ""),
    (2, SL, "    if own is not None and own.valid:\n", "    if own is not None:\n"),
    (
        3,
        SL,
        "        if now - seen.last > stale_after:\n",
        "        if now - seen.last >= stale_after:\n",
    ),
    (
        4,
        SL,
        "            if now - outage.end <= retention:\n",
        "            if now - outage.end < retention:\n",
    ),
    (
        5,
        SL,
        "            end = back if back is not None and back > outage.start else seen.last\n",
        "            end = seen.last\n",
    ),
    (
        6,
        IP / "const.py",
        'SENSOR_LIVENESS_EXEMPT_DOMAINS = ("input_number",)\n',
        "SENSOR_LIVENESS_EXEMPT_DOMAINS = ()\n",
    ),
    (
        7,
        SL,
        "    return dt_util.as_local(stamp).replace(tzinfo=None)\n",
        "    return stamp.replace(tzinfo=None)\n",
    ),
    (
        8,
        SL,
        "        if armed_at is not None and local_naive_now() < armed_at:\n            return\n",
        "",
    ),
    (
        9,
        SL,
        "            if last is None:\n"
        "                # Never seen and nothing remembered: count the limit from this first\n"
        "                # look, not from never.\n"
        "                last = now\n",
        "",
    ),
    (10, INIT, "                self._retire_outages(before)\n", ""),
    (
        11,
        IP / "calculation.py",
        "                    # Outages describe readings that no longer exist.\n"
        "                    const.MAPPING_SENSOR_OUTAGES: [],\n"
        "                    const.MAPPING_SENSOR_LAST_SEEN: {},\n",
        "",
    ),
    (
        12,
        IP / "store.py",
        "        self.mappings[mapping_id] = attr.evolve(entry, sensor_last_seen=dict(seen))\n",
        "        self.mappings[mapping_id] = attr.evolve(entry, sensor_last_seen=dict(seen))\n"
        "        self.async_schedule_save()\n",
    ),
    (
        13,
        SL,
        "            try:\n"
        "                await self._async_check_mapping_liveness(mapping, now)\n"
        "            except Exception:\n"
        "                # A periodic check: one broken group must not stop the others,\n"
        "                # every five minutes, for good.\n"
        "                _LOGGER.exception(\n"
        '                    "Sensor liveness check failed for sensor group %s",\n'
        "                    mapping.get(const.MAPPING_ID),\n"
        "                )\n",
        "            await self._async_check_mapping_liveness(mapping, now)\n",
    ),
    (14, SL, "        if not silent:\n            return\n", ""),
    (
        15,
        SL,
        "        if seen is None:\n"
        "            ended = replace(outage, end=now)\n"
        "            kept.append(ended)\n"
        "            closed.append(ended)\n"
        "            continue\n"
        "        if seen.last is not None and seen.last > outage.start:\n",
        "        if seen is not None and seen.last is not None and seen.last > outage.start:\n",
    ),
    (
        16,
        SL,
        "        for outage in silent:\n"
        "            self._fire_weather_stale(mapping_id, name, replace(outage, end=now))\n",
        "",
    ),
    # --- revision 2: JustChr's three repair-issue tests ---------------------------
    (
        17,  # recovery: a closing outage no longer clears the notice
        SL,
        "        if opened or closed:\n",
        "        if opened:\n",
    ),
    (
        18,  # restart: setup no longer shows what the ledger holds open
        SL,
        "            mapping_id = mapping[const.MAPPING_ID]\n"
        "            self._sync_stale_issue(\n"
        "                mapping_id, mapping.get(const.MAPPING_NAME) or str(mapping_id), outages\n"
        "            )\n",
        "",
    ),
    (19, INIT, "            self._retire_outages(res)\n", ""),  # deletion
    (
        20,  # restart: the ledger is not read back from the store
        IP / "store.py",
        "                        sensor_outages=mapping.get(MAPPING_SENSOR_OUTAGES) or [],\n",
        "",
    ),
]

SUMMARY = re.compile(r"(\d+ (?:failed|passed|errors?)[^=]*)")


def run_tests():
    proc = subprocess.Popen(
        [PY, "-m", "pytest", *TESTS, "-p", "_local_socket_unblock", "-q", "--no-header", "-rfE"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "TZ": "UTC"},
    )
    try:
        out, _ = proc.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        # A mutation can deadlock a test; take the whole tree down (Windows).
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        proc.communicate()
        return None, "HANG", []
    lines = out.splitlines()
    summary = next((m.group(1) for line in reversed(lines) if (m := SUMMARY.search(line))), "?")
    killers = sorted(
        {
            line.split(" ")[1].split(" - ")[0].split("::", 1)[-1]
            for line in lines
            if line.startswith(("FAILED ", "ERROR "))
        }
    )
    return proc.returncode, summary, killers


results = []
for number, path, old, new in MUTATIONS:
    original = path.read_bytes()
    crlf = b"\r\n" in original
    text = original.decode("utf-8").replace("\r\n", "\n")
    count = text.count(old)
    if count != 1:
        results.append((number, f"ANCHOR {count}x", []))
        continue
    mutated = text.replace(old, new)
    if crlf:
        mutated = mutated.replace("\n", "\r\n")
    path.write_bytes(mutated.encode("utf-8"))
    try:
        code, summary, killers = run_tests()
    finally:
        path.write_bytes(original)
    if code is None:
        verdict = "HANG"
    elif "passed" not in summary and "failed" not in summary:
        verdict = "NO-COLLECT"  # import/collection broke: not a kill
    elif code != 0 and killers:
        verdict = "KILLED"
    else:
        verdict = "SURVIVED"
    results.append((number, f"{verdict} | {summary}", killers))

for number, verdict, killers in results:
    print(f"M{number:02d}: {verdict}")
    for name in killers:
        print(f"        {name}")
