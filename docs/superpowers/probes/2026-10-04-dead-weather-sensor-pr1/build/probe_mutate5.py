"""Build of PR 1 (2026-10-04): the Task-14 mutations, M1-M20 from the plan plus
M21+ from the per-task quality reviews and M49+ from the fix rounds, against the
build worktree. Anchors as of the end of fix round C; M60 from the review of the
polish commit (the mapped entity's own integration on a shared device).

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
            "                # Never seen and nothing remembered: an open outage keeps its start;\n"
            "                # otherwise count the limit from this first look, not from never.\n"
            "                last = open_start.get(entity_id, now)\n",
            "",
        ),
    (10, INIT, "                self._retire_outages(before)\n", ""),
    (11, IP / "calculation.py", '                    const.MAPPING_SENSOR_OUTAGES: [],\n                },\n', '                },\n'),
    (12, IP / "store.py", '        self.mappings[mapping_id] = attr.evolve(entry, sensor_last_seen=fresh)\n', '        self.mappings[mapping_id] = attr.evolve(entry, sensor_last_seen=fresh)\n        self.async_schedule_save()\n'),
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
    (16, SL, '            self._fire_weather_stale(mapping_id, name, replace(outage, end=now))\n', ''),
    (
            17,  # recovery: a closing outage no longer clears the notice
            SL,
            "        if opened or closed:\n",
            "        if opened:\n",
        ),
    (
            18,  # restart: setup no longer shows what the ledger holds open
            SL,
            "                mapping_id = mapping[const.MAPPING_ID]\n"
            "                self._sync_stale_issue(\n"
            "                    mapping_id,\n"
            "                    mapping.get(const.MAPPING_NAME) or str(mapping_id),\n"
            "                    outages,\n"
            "                )\n",
            "",
        ),
    (19, INIT, "            self._retire_outages(res)\n", ""),
    (
            20,  # restart: the ledger is not read back from the store
            IP / "store.py",
            "                        sensor_outages=mapping.get(MAPPING_SENSOR_OUTAGES) or [],\n",
            "",
        ),
    (
            21,  # the documented limit: 3 h
            IP / "const.py",
            "SENSOR_STALE_AFTER_SECONDS = 3 * 3600\n",
            "SENSOR_STALE_AFTER_SECONDS = 4 * 3600\n",
        ),
    (
            22,  # the documented cadence: 5 min
            IP / "const.py",
            "SENSOR_LIVENESS_INTERVAL_SECONDS = 300\n",
            "SENSOR_LIVENESS_INTERVAL_SECONDS = 600\n",
        ),
    (
            23,  # the startup grace: 10 min
            IP / "const.py",
            "SENSOR_LIVENESS_STARTUP_GRACE_SECONDS = 600\n",
            "SENSOR_LIVENESS_STARTUP_GRACE_SECONDS = 300\n",
        ),
    (
            24,  # only sensor fields are watched (R7)
            SL,
            "        if cfg.get(const.MAPPING_CONF_SOURCE) != const.MAPPING_CONF_SOURCE_SENSOR:\n"
            "            continue\n",
            "",
        ),
    (
            25,  # only the input_number DOMAIN is exempt, not a name containing it
            SL,
            '        if entity_id.split(".", 1)[0] in const.SENSOR_LIVENESS_EXEMPT_DOMAINS:\n',
            "        if any(d in entity_id for d in const.SENSOR_LIVENESS_EXEMPT_DOMAINS):\n",
        ),
    (26, SL, '    stamps = [s.changed for s in siblings if s.valid and s.changed > start]\n', '    stamps = [s.changed for s in siblings if s.changed > start]\n'),
    (
            27,  # a missing entity would let its device vouch
            SL,
            "    if own is not None and own.valid:\n"
            "        candidates.append(own.reported)\n"
            "        candidates.extend(s.reported for s in siblings if s.valid)\n",
            "    if own is None or own.valid:\n"
            "        if own is not None:\n"
            "            candidates.append(own.reported)\n"
            "        candidates.extend(s.reported for s in siblings if s.valid)\n",
        ),
    (28, SL, '    stamps = [s.changed for s in siblings if s.valid and s.changed > start]\n', '    stamps = [s.changed for s in siblings if s.valid and s.changed >= start]\n'),
    (29, SL, '    if own is not None and own.valid and own.changed > start:\n', '    if False:\n'),
    (
            30,  # a ledger that is not a list would raise
            SL,
            "    if not isinstance(stored, list):\n        return []\n",
            "",
        ),
    (
            31,  # unreadable records would come through as None
            SL,
            "    return [outage for raw in stored if (outage := Outage.from_store(raw)) is not None]\n",
            "    return [Outage.from_store(raw) for raw in stored]\n",
        ),
    (
            32,  # fields that are not strings would be read
            SL,
            "        if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):\n",
            "        if not isinstance(fields, list):\n",
        ),
    (
            33,  # a closed record with an unreadable end would come back open
            SL,
            '        if end is None and raw.get("end") is not None:\n'
            "            return None  # a closed record must not come back open\n",
            "",
        ),
    (
            34,  # a record without its optional keys would raise
            SL,
            '        fields = raw.get("fields") or []\n',
            '        fields = raw["fields"] or []\n',
        ),
    (
            35,  # a list that mixes names with anything else would be read
            SL,
            "        if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):\n",
            "        if not isinstance(fields, list) or not any(isinstance(f, str) for f in fields):\n",
        ),
    (
            36,  # a record with fields: None would be dropped
            SL,
            '        fields = raw.get("fields") or []\n',
            '        fields = raw.get("fields", [])\n',
        ),
    (
            37,  # a closed record would block the next outage of its entity
            SL,
            "            if now - outage.end <= retention:\n"
            "                kept.append(outage)\n"
            "            continue\n",
            "            if now - outage.end <= retention:\n"
            "                kept.append(outage)\n"
            "            still_open.add(outage.entity_id)\n"
            "            continue\n",
        ),
    (
            38,  # a kept closed record would be reported as closing again
            SL,
            "            if now - outage.end <= retention:\n"
            "                kept.append(outage)\n"
            "            continue\n",
            "            if now - outage.end <= retention:\n"
            "                kept.append(outage)\n"
            "                closed.append(outage)\n"
            "            continue\n",
        ),
    (
            39,  # a dated return alone would end a silent field
            SL,
            "        if seen.last is not None and seen.last > outage.start:\n",
            "        if (seen.last is not None and seen.last > outage.start) or (\n"
            "            seen.recovered is not None and seen.recovered > outage.start\n"
            "        ):\n",
        ),
    (
            40,  # the event's stamps would lose Home Assistant's offset
            SL,
            '        "since": dt_util.as_local(outage.start).isoformat(),\n',
            '        "since": outage.start.isoformat(),\n',
        ),
    (
            41,  # entities that fell silent together would follow the input order
            SL,
            "        (o for o in outages if o.end is None), key=lambda o: (o.start, o.entity_id)\n",
            "        (o for o in outages if o.end is None), key=lambda o: o.start\n",
        ),
    (
            42,  # an open outage without a remembered sign would end now
            SL,
            "                last = open_start.get(entity_id, now)\n",
            "                last = now\n",
        ),
    (
            43,  # the start of the next outage would be announced before the end
            SL,
            "        for outage in closed:\n"
            "            _LOGGER.info(\n"
            '                "Sensor group %s: the outage of %s is over (silent from %s to %s)",\n'
            "                name,\n"
            "                outage.entity_id,\n"
            "                outage.start,\n"
            "                outage.end,\n"
            "            )\n"
            "            self._fire_weather_stale(mapping_id, name, outage)\n"
            "        for outage in opened:\n",
            "        for outage in opened:\n"
            "            self._fire_weather_stale(mapping_id, name, outage)\n"
            "        for outage in closed:\n"
            "            self._fire_weather_stale(mapping_id, name, outage)\n"
            "        for outage in []:\n",
        ),
    (
            44,  # one broken group would stop the setup
            SL,
            "            except Exception:\n"
            "                # Only a notice: it must not keep the integration from setting up.\n",
            "            except KeyError:\n"
            "                # Only a notice: it must not keep the integration from setting up.\n",
        ),
    (
            45,  # a clean stop would lose the refreshed signs of life
            IP / "store.py",
            "        if fresh != entry.sensor_last_seen:\n"
            "            self._last_seen_dirty = True\n",
            "",
        ),
    (
            46,  # unchanged signs would queue a shutdown write anyway
            IP / "store.py",
            "        if fresh != entry.sensor_last_seen:\n"
            "            self._last_seen_dirty = True\n",
            "        self._last_seen_dirty = True\n",
        ),
    (
            47,  # a deleted configuration would be written back for the signs
            IP / "store.py",
            "        self._buffers_dirty = False\n"
            "        self._last_seen_dirty = False\n"
            "        # self.config = Config()\n",
            "        self._buffers_dirty = False\n"
            "        # self.config = Config()\n",
        ),
    (
            48,  # signs that are not a mapping would load as they are
            IP / "store.py",
            "    return value if isinstance(value, dict) else {}\n",
            "    return value or {}\n",
        ),
    (49, SL, '    if own is not None and own.valid and own.changed > start:\n        return own.changed\n    stamps = [s.changed for s in siblings if s.valid and s.changed > start]\n', '    states = ([own] if own is not None else []) + list(siblings)\n    stamps = [s.changed for s in states if s.valid and s.changed > start]\n'),
    (50, SL, '    if own is not None and own.valid and own.changed > start:\n', '    if own is not None and own.valid and own.changed >= start:\n'),
    (51, SL, '        and sibling.config_entry_id in vouching\n', ''),
    (52, SL, '    vouching = {entry.config_entry_id, owner} - {None}\n', '    vouching = {entry.config_entry_id}\n'),
    (53, SL, '        and sibling.entity_id.split(".", 1)[0] in const.SENSOR_LIVENESS_SIBLING_DOMAINS\n', ''),
    (54, IP / "calculation.py", '                    const.MAPPING_SENSOR_OUTAGES: [],\n                },\n', '                    const.MAPPING_SENSOR_OUTAGES: [],\n                    const.MAPPING_SENSOR_LAST_SEEN: {},\n                },\n'),
    (55, SL, '                _LOGGER.exception(\n                    "Sensor liveness check failed for sensor group %s",\n                    mapping.get(const.MAPPING_ID),\n                )\n', '                pass\n'),
    (56, SL, '        await self.async_check_sensor_liveness()\n', '        await self.async_check_sensor_liveness(now=_now)\n'),
    (57, SL, '        self.async_teardown_sensor_liveness()\n        self._sensor_liveness_armed_at = local_naive_now() + timedelta(\n', '        self._sensor_liveness_armed_at = local_naive_now() + timedelta(\n'),
    (58, SL, '        silent = [o for o in outages_of(mapping or {}) if o.end is None]\n', '        silent = outages_of(mapping or {})\n'),
    (59, INIT, '                self._retire_outages(before)\n', '                self._retire_outages(self.store.get_mapping(mapping_id))\n'),
    (60, SL, '    vouching = {entry.config_entry_id, owner} - {None}\n', '    vouching = ({entry.config_entry_id} if owner is None else {owner}) - {None}\n'),
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
