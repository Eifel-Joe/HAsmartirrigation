"""Mutation matrix for the unload-teardown probe.

Each mutation replaces an anchor that must occur exactly once, runs the named
test file, records which tests went red, and restores the file from memory.
Run from the probe worktree root.
"""

import os
import re
import subprocess
import sys

PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
CC = "custom_components/irrigation_plus/"
T = "tests/test_self_closing_teardown.py"

MUTATIONS = [
    (1, CC + "__init__.py",
     "        self.async_teardown_self_closing_handles()\n", "",
     "unload does not call the teardown"),
    (2, CC + "self_closing.py",
     "        for zone_id in list(self._sc_cleanup_timers()):\n            self._sc_cancel_cleanup(zone_id)\n", "",
     "teardown cancels only the samplers"),
    (3, CC + "self_closing.py",
     "        for zone_id in list(meters):\n            meters.pop(zone_id)[1]()  # the interval's cancel handle\n", "",
     "teardown cancels only the backstops"),
    (4, CC + "self_closing.py",
     "            meters.pop(zone_id)[1]()  # the interval's cancel handle\n",
     "            self._sc_finish_flow(zone_id)\n",
     "teardown finalises the meter"),
    (5, CC + "master.py",
     "        self._master_hold_set().clear()\n        cancel = getattr(self, \"_master_off_cancel\", None)\n        if cancel is not None:\n            cancel()\n            self._master_off_cancel = None\n\n    async def async_master_end_cycle_now",
     "        self._master_hold_set().clear()\n\n    async def async_master_end_cycle_now",
     "release_all leaves the off timer armed"),
    (6, CC + "self_closing.py",
     "        await self._chain_release(const.WATERING_MODE_SERVICE, reason)\n\n        stopped = False\n",
     "        stopped = False\n",
     "abort does not release the chain before its stops"),
    (7, CC + "__init__.py",
     "            await coordinator.async_release_all_chains(why)\n", "",
     "disable does not release the chains"),
    (8, CC + "self_closing.py",
     "            if r.get(const.RUN_MODE)\n            not in (const.WATERING_MODE_OPENSPRINKLER, const.WATERING_MODE_BATCH)\n",
     "            if r.get(const.RUN_MODE) == const.WATERING_MODE_SERVICE\n",
     "abort filters on == service"),
    (9, CC + "__init__.py",
     "            await coordinator.async_master_end_cycle_now()\n        await coordinator.async_unload()",
     "            await coordinator.async_master_end_cycle_now()\n        await coordinator.async_abort_self_closing_runs(\"reload\")\n        await coordinator.async_unload()",
     "a reload aborts too"),
    (10, CC + "self_closing.py",
     "                if settle:\n                    if await self.async_stop_self_closing(zone_id):",
     "                if True:\n                    if await self.async_stop_self_closing(zone_id):",
     "settle=False settles anyway"),
    (11, CC + "master.py",
     "            if not self._master_configured() or self._master_hold_set():\n",
     "            if not self._master_configured():\n",
     "end-now ignores a remaining hold"),
    (12, CC + "master.py",
     "            if getattr(self, \"_master_on\", False) and getattr(\n                self._master_cfg(), const.CONF_MASTER_OFF_AFTER, False\n            ):",
     "            if getattr(self._master_cfg(), const.CONF_MASTER_OFF_AFTER, False):",
     "end-now ignores _master_on"),
    (13, CC + "master.py",
     "            if getattr(self, \"_master_on\", False) and getattr(\n                self._master_cfg(), const.CONF_MASTER_OFF_AFTER, False\n            ):",
     "            if getattr(self, \"_master_on\", False):",
     "end-now ignores master_off_after"),
    (14, CC + "__init__.py",
     "            await coordinator.async_master_end_cycle_now()\n            await coordinator.async_delete_config()",
     "            await coordinator.async_delete_config()\n            await coordinator.async_master_end_cycle_now()",
     "removal ends the master after the delete"),
    (15, CC + "master.py",
     "        except Exception:  # noqa: BLE001\n            _LOGGER.exception(\"Could not end the master cycle\")\n",
     "        except ZeroDivisionError:\n            _LOGGER.exception(\"Could not end the master cycle\")\n",
     "end-now lets an exception through"),
    (16, CC + "self_closing.py",
     "            except Exception:  # noqa: BLE001\n                _LOGGER.exception(\n                    \"Zone %s: could not stop its self-closing run; it may still \"",
     "            except ZeroDivisionError:\n                _LOGGER.exception(\n                    \"Zone %s: could not stop its self-closing run; it may still \"",
     "abort lets one run's exception through"),
    (17, CC + "run_chain.py",
     "            except Exception:  # noqa: BLE001\n                _LOGGER.exception(\"Could not release the %s chain\", mode)\n",
     "            except ZeroDivisionError:\n                _LOGGER.exception(\"Could not release the %s chain\", mode)\n",
     "release-all lets one chain's exception through"),
    (18, CC + "__init__.py",
     "            await coordinator.async_abort_self_closing_runs(why)\n", "",
     "disable does not abort the service runs"),
    (19, CC + "__init__.py",
     "            # Its off timer goes with the unload, so the cycle ends here.\n            await coordinator.async_master_end_cycle_now()\n", "",
     "disable does not end the master"),
    (20, CC + "run_chain.py",
     "        self._chain_forfeit_queue(mode, why)\n",
     "        self._chain_forfeit_queue(mode, \"the cycle was stopped\")\n",
     "_chain_release ignores why"),
    (21, CC + "self_closing.py",
     "        field = zone.get(const.ZONE_DURATION_FIELD) or \"duration\"\n        data[field] = 0\n        await self.hass.services.async_call(domain, service, data)\n        return True\n",
     "        field = \"duration\"\n        data[field] = 0\n        await self.hass.services.async_call(domain, service, data)\n        return True\n",
     "dispatch_stop ignores the zone's duration field"),
]


def run_tests(timeout=600):
    env = dict(os.environ, TZ="UTC")
    proc = subprocess.Popen(
        [PY, "-m", "pytest", T, "-p", "_local_socket_unblock", "-q", "--no-header",
         "-rfE", "-p", "no:cacheprovider"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
    )
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                       capture_output=True)
        return "HANG", []
    text = out.decode("utf-8", "replace").replace("\r", "\n")
    red = sorted({
        m.group(1)
        for m in re.finditer(r"^(?:FAILED|ERROR) tests/test_self_closing_teardown\.py::(\S+)", text, re.M)
    })
    summary = [ln for ln in text.splitlines() if re.search(r"\d+ (passed|failed)", ln)]
    return (summary[-1].strip("= ") if summary else "?"), red


def main():
    only = {int(a) for a in sys.argv[1:]}
    results = []
    for num, path, anchor, replacement, label in MUTATIONS:
        if only and num not in only:
            continue
        with open(path, encoding="utf-8", newline="") as fh:
            original = fh.read()
        norm = original.replace("\r\n", "\n")
        crlf = norm != original
        count = norm.count(anchor)
        if count != 1:
            results.append((num, label, f"ANCHOR x{count}", []))
            continue
        mutated = norm.replace(anchor, replacement)
        if crlf:
            mutated = mutated.replace("\n", "\r\n")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(mutated)
        try:
            summary, red = run_tests()
        finally:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(original)
        results.append((num, label, summary, red))
        print(f"{num:2d} {label}: {summary}", flush=True)
        for r in red:
            print(f"     red: {r}", flush=True)
    print()
    survivors = [r for r in results if not r[3]]
    print(f"killed {len(results) - len(survivors)}/{len(results)}")
    for num, label, summary, _ in survivors:
        print(f"SURVIVOR {num} {label}: {summary}")


if __name__ == "__main__":
    main()
