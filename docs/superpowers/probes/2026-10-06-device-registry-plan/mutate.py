"""Mutation run for the device-registry fix (2027.8 deprecations).

Each mutation undoes or bends one changed line; the compat tests must fail
for every one of them. The file is restored after each run, also on timeout.

Usage: python mutate.py <worktree> <result.txt>
"""

import re
import subprocess
import sys
from pathlib import Path

PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
ENT = "custom_components/irrigation_plus/entity.py"
INIT = "custom_components/irrigation_plus/__init__.py"
DIST = "custom_components/irrigation_plus/distributor.py"
TESTS = ["tests/test_device_registry_compat.py"]
TIMEOUT = 300

MUTATIONS = [
    ("M01 switch always off", ENT,
     'takes_id = "via_device_id" in inspect.signature(method).parameters',
     "takes_id = False"),
    ("M02 switch always on", ENT,
     'takes_id = "via_device_id" in inspect.signature(method).parameters',
     "takes_id = True"),
    ("M03 link names the coordinator, not the hub device", ENT,
     'return {"via_device_id": hub_device_id}',
     'return {"via_device_id": cid}'),
    ("M04 recorded link ignored", ENT,
     "if isinstance(link, dict) and link:",
     "if False:"),
    ("M05 zone device keeps the fixed via_device", ENT,
     '        "model": "Irrigation zone",\n'
     '        "manufacturer": const.MANUFACTURER,\n'
     "        **hub_link(hass),\n",
     '        "model": "Irrigation zone",\n'
     '        "manufacturer": const.MANUFACTURER,\n'
     '        "via_device": (const.DOMAIN, cid),\n'),
    ("M06 distributor device keeps the fixed via_device", ENT,
     '        "model": "Gardena water distributor",\n'
     '        "manufacturer": const.MANUFACTURER,\n'
     "        **hub_link(hass),\n",
     '        "model": "Gardena water distributor",\n'
     '        "manufacturer": const.MANUFACTURER,\n'
     '        "via_device": (const.DOMAIN, cid),\n'),
    ("M07 setup records no link", INIT,
     'hass.data[const.DOMAIN]["hub_link"] = hub_link_for(',
     'hass.data[const.DOMAIN]["hub_link_unread"] = hub_link_for('),
    ("M08 setup links to the coordinator id, not the hub device", INIT,
     "        device_registry, hub.id, coordinator.id\n",
     "        device_registry, coordinator.id, coordinator.id\n"),
    ("M09 find_device asks the instance", ENT,
     'if callable(getattr(type(registry), "async_get_device_by_identifier", None)):',
     'if callable(getattr(registry, "async_get_device_by_identifier", None)):'),
    ("M10 find_device always per entry", ENT,
     'if callable(getattr(type(registry), "async_get_device_by_identifier", None)):',
     "if True:"),
    ("M11 find_device never per entry", ENT,
     'if callable(getattr(type(registry), "async_get_device_by_identifier", None)):',
     "if False:"),
    ("M12 find_device drops the entry", ENT,
     "return registry.async_get_device_by_identifier(identifier, config_entry_id)",
     "return registry.async_get_device_by_identifier(identifier, None)"),
    ("M13 zone delete keeps the old lookup", INIT,
     "        device = find_device(\n"
     "            device_registry,\n"
     '            (const.DOMAIN, f"{self.id}_zone_{zone_id}"),\n'
     '            getattr(getattr(self, "entry", None), "entry_id", None),\n'
     "        )\n",
     "        device = device_registry.async_get_device(\n"
     '            identifiers={(const.DOMAIN, f"{self.id}_zone_{zone_id}")}\n'
     "        )\n"),
    ("M14 zone delete drops the entry", INIT,
     '            (const.DOMAIN, f"{self.id}_zone_{zone_id}"),\n'
     '            getattr(getattr(self, "entry", None), "entry_id", None),\n',
     '            (const.DOMAIN, f"{self.id}_zone_{zone_id}"),\n'
     "            None,\n"),
    ("M15 distributor delete keeps the old lookup", DIST,
     "                device = find_device(\n"
     "                    registry,\n"
     '                    (const.DOMAIN, f"{self.id}_distributor_{int(did)}"),\n'
     '                    getattr(getattr(self, "entry", None), "entry_id", None),\n'
     "                )\n",
     "                device = registry.async_get_device(\n"
     '                    identifiers={(const.DOMAIN, f"{self.id}_distributor_{int(did)}")}\n'
     "                )\n"),
    ("M16 distributor delete drops the entry", DIST,
     '                    (const.DOMAIN, f"{self.id}_distributor_{int(did)}"),\n'
     '                    getattr(getattr(self, "entry", None), "entry_id", None),\n',
     '                    (const.DOMAIN, f"{self.id}_distributor_{int(did)}"),\n'
     "                    None,\n"),
]


def run_tests(worktree):
    cmd = [PY, "-m", "pytest", *TESTS, "-p", "_local_socket_unblock", "-q",
           "--no-header", "-rf"]
    proc = subprocess.Popen(cmd, cwd=worktree, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace")
    try:
        out, _ = proc.communicate(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                       capture_output=True)
        proc.communicate()
        return None, []
    killers = sorted(set(re.findall(r"^FAILED (\S+)", out, re.M)))
    summary = [ln for ln in out.splitlines() if re.search(r"\d+ (passed|failed)", ln)]
    return (summary[-1].strip() if summary else out[-300:]), killers


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    worktree = Path(sys.argv[1])
    result = Path(sys.argv[2])
    lines = []
    survived = 0
    for name, rel, old, new in MUTATIONS:
        path = worktree / rel
        original = path.read_bytes()
        text = original.decode("utf-8")
        crlf = "\r\n" in text
        plain = text.replace("\r\n", "\n")
        count = plain.count(old)
        if count != 1:
            lines.append(f"{name}: ANCHOR {count}x -- not run")
            survived += 1
            print(lines[-1])
            continue
        mutated = plain.replace(old, new)
        if crlf:
            mutated = mutated.replace("\n", "\r\n")
        path.write_bytes(mutated.encode("utf-8"))
        try:
            summary, killers = run_tests(worktree)
        finally:
            path.write_bytes(original)
        if summary is None:
            verdict = "HANG"
        elif not re.search(r"\d+ (passed|failed)", summary):
            verdict = "NOT COLLECTED"
        elif killers:
            verdict = "KILLED"
        else:
            verdict = "SURVIVED"
        if verdict != "KILLED":
            survived += 1
        lines.append(f"{name}: {verdict} | {summary}")
        for k in killers:
            lines.append(f"    {k}")
        print("\n".join(lines[-1 - len(killers):]))
    lines.append(f"TOTAL {len(MUTATIONS)}, not killed {survived}")
    print(lines[-1])
    result.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
