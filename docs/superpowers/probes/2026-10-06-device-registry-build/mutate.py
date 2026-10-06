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
    # Added with the review follow-up of the first task (unreadable signature,
    # 2026.8.0's own shape, the record guard, the copy).
    ("M17 an unreadable signature escapes", ENT,
     "    except Exception:  # noqa: BLE001 - unreadable means the identifier form\n",
     "    except (TypeError, ValueError):\n"),
    ("M18 any **kwargs means the id form", ENT,
     'takes_id = "via_device_id" in inspect.signature(method).parameters',
     "takes_id = any(p.kind is p.VAR_KEYWORD"
     " for p in inspect.signature(method).parameters.values())"),
    ("M19 a missing via_device means the id form", ENT,
     'takes_id = "via_device_id" in inspect.signature(method).parameters',
     'takes_id = "via_device" not in inspect.signature(method).parameters'),
    ("M20 the record guard drops the dict check", ENT,
     "    if isinstance(link, dict) and link:\n",
     "    if link:\n"),
    ("M21 an empty record counts as a link", ENT,
     "    if isinstance(link, dict) and link:\n",
     "    if isinstance(link, dict):\n"),
    ("M22 hub_link hands out the record itself", ENT,
     "        return dict(link)\n",
     "        return link\n"),
    ("M23 hub_link tolerates only a missing domain", ENT,
     '        link = hass.data[const.DOMAIN].get("hub_link")\n'
     "    except (KeyError, AttributeError, RuntimeError):\n",
     '        link = hass.data[const.DOMAIN].get("hub_link")\n'
     "    except KeyError:\n"),
    # Added with the review follow-up of the second task (a miss).
    ("M24 a miss falls back to the deprecated lookup", ENT,
     "        return registry.async_get_device_by_identifier(identifier, config_entry_id)\n",
     "        return registry.async_get_device_by_identifier(identifier, config_entry_id)"
     " or registry.async_get_device(identifiers={identifier})\n"),
    ("M25 no entry id means the old lookup", ENT,
     '    if callable(getattr(type(registry), "async_get_device_by_identifier", None)):\n',
     '    if config_entry_id is not None and callable(getattr(type(registry),'
     ' "async_get_device_by_identifier", None)):\n'),
    ("M26 a miss is reported as False", ENT,
     "        return registry.async_get_device_by_identifier(identifier, config_entry_id)\n",
     "        return registry.async_get_device_by_identifier(identifier, config_entry_id)"
     " or False\n"),
    # Added with the review follow-up of the third task (order, overwrite).
    ("M27 the link is recorded after the platforms", INIT,
     ('    hass.data[const.DOMAIN]["hub_link"] = hub_link_for(\n'
      "        device_registry, hub.id, coordinator.id\n"
      "    )\n",
      '    _LOGGER.info("Finished calling async_forward_entry_setups")\n'),
     ("    late_link = hub_link_for(device_registry, hub.id, coordinator.id)\n",
      '    _LOGGER.info("Finished calling async_forward_entry_setups")\n'
      '    hass.data[const.DOMAIN]["hub_link"] = late_link\n')),
    ("M28 setup keeps a stale link", INIT,
     '    hass.data[const.DOMAIN]["hub_link"] = hub_link_for(\n'
     "        device_registry, hub.id, coordinator.id\n"
     "    )\n",
     '    hass.data[const.DOMAIN].setdefault("hub_link", hub_link_for(\n'
     "        device_registry, hub.id, coordinator.id\n"
     "    ))\n"),
    # Added with the review follow-up of the fourth task (zone delete call site).
    ("M29 zone delete reads the entry strictly", INIT,
     '            (const.DOMAIN, f"{self.id}_zone_{zone_id}"),\n'
     '            getattr(getattr(self, "entry", None), "entry_id", None),\n',
     '            (const.DOMAIN, f"{self.id}_zone_{zone_id}"),\n'
     "            self.entry.entry_id,\n"),
    ("M30 zone delete without the guard", INIT,
     "        if device:\n"
     "            device_registry.async_remove_device(device.id)\n",
     "        device_registry.async_remove_device(device.id)\n"),
    ("M31 zone delete calls the per-entry lookup directly", INIT,
     "        device = find_device(\n"
     "            device_registry,\n"
     '            (const.DOMAIN, f"{self.id}_zone_{zone_id}"),\n',
     "        device = device_registry.async_get_device_by_identifier(\n"
     '            (const.DOMAIN, f"{self.id}_zone_{zone_id}"),\n'),
    ("M32 zone delete falls back on a miss", INIT,
     '            getattr(getattr(self, "entry", None), "entry_id", None),\n'
     "        )\n"
     "        if device:\n",
     '            getattr(getattr(self, "entry", None), "entry_id", None),\n'
     "        ) or device_registry.async_get_device(\n"
     '            identifiers={(const.DOMAIN, f"{self.id}_zone_{zone_id}")}\n'
     "        )\n"
     "        if device:\n"),
    # Added with the review follow-up of the fifth task (the distributor mirror).
    ("M33 distributor delete reads the entry strictly", DIST,
     '                    (const.DOMAIN, f"{self.id}_distributor_{int(did)}"),\n'
     '                    getattr(getattr(self, "entry", None), "entry_id", None),\n',
     '                    (const.DOMAIN, f"{self.id}_distributor_{int(did)}"),\n'
     "                    self.entry.entry_id,\n"),
    ("M34 distributor delete without the guard", DIST,
     "                if device:\n"
     "                    registry.async_remove_device(device.id)\n",
     "                registry.async_remove_device(device.id)\n"),
    ("M35 distributor delete calls the per-entry lookup directly", DIST,
     "                device = find_device(\n"
     "                    registry,\n"
     '                    (const.DOMAIN, f"{self.id}_distributor_{int(did)}"),\n',
     "                device = registry.async_get_device_by_identifier(\n"
     '                    (const.DOMAIN, f"{self.id}_distributor_{int(did)}"),\n'),
    ("M36 distributor delete falls back on a miss", DIST,
     '                    getattr(getattr(self, "entry", None), "entry_id", None),\n'
     "                )\n"
     "                if device:\n",
     '                    getattr(getattr(self, "entry", None), "entry_id", None),\n'
     "                ) or registry.async_get_device(\n"
     '                    identifiers={(const.DOMAIN, f"{self.id}_distributor_{int(did)}")}\n'
     "                )\n"
     "                if device:\n"),
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
        # A mutation may be several edits in a row (old and new as tuples);
        # every anchor must occur exactly once in the text it is applied to.
        edits = list(zip(old, new)) if isinstance(old, tuple) else [(old, new)]
        mutated = plain
        bad = None
        for o, n in edits:
            count = mutated.count(o)
            if count != 1:
                bad = count
                break
            mutated = mutated.replace(o, n)
        if bad is not None:
            lines.append(f"{name}: ANCHOR {bad}x -- not run")
            survived += 1
            print(lines[-1])
            continue
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
