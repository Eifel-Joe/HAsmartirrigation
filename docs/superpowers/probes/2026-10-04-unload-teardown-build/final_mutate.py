"""Mutation matrix for the unload-teardown build, against its final commit.

Each mutation is a list of (file, anchor, replacement) edits; every anchor must
occur exactly once in its (CRLF-normalised) file. The runner checks the tree is
clean, applies the edits, runs the mutation's test files, records the red tests
(the killers), and restores every file from memory. A run that collects nothing
is BROKEN, a run past the time limit is HANG (killed with taskkill /T) — neither
is a verdict. Run from the worktree root: python ../final_mutate.py [numbers]
Results also go to ../mutate-final.json.
"""

import json
import os
import re
import subprocess
import sys

PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
CC = "custom_components/irrigation_plus/"
T = "tests/test_self_closing_teardown.py"
TD = "tests/test_distributor.py"
SC, MA, RC, IN, DI = (CC + f for f in ("self_closing.py", "master.py", "run_chain.py", "__init__.py", "distributor.py"))

TEARDOWN = (
    "        meters = self._sc_meters()\n"
    "        for zone_id in list(meters):\n"
    "            meters.pop(zone_id)[1]()  # the interval's cancel handle\n"
    "        for zone_id in list(self._sc_cleanup_timers()):\n"
    "            self._sc_cancel_cleanup(zone_id)\n"
)
END_NOW_GATE = (
    "            if getattr(self, \"_master_on\", False) and getattr(\n"
    "                self._master_cfg(), const.CONF_MASTER_OFF_AFTER, False\n"
    "            ):"
)
CHAIN_GUARD = (
    "        try:\n"
    "            await self._chain_release(const.WATERING_MODE_SERVICE, reason)\n"
    "        except Exception:  # noqa: BLE001\n"
    "            _LOGGER.exception(\n"
    "                \"Could not release the service chain; its runs are not stopped\"\n"
    "            )\n"
    "            return False\n"
)
SETTLE_FALSE_WARNING = (
    "                else:\n"
    "                    _LOGGER.warning(\n"
    "                        \"Zone %s has no stop_service; its valve runs on to the \"\n"
    "                        \"end of its own countdown\",\n"
    "                        zone_id,\n"
    "                    )\n"
)
NO_MASTER_END = "_leaves_the_cycle_up\n            return\n"

# (number, label, [(file, anchor, replacement), ...], [test files])
MUTATIONS = [
    (1, "unload does not call the teardown",
     [(IN, "        self.async_teardown_self_closing_handles()\n", "")], [T]),
    (2, "teardown cancels only the samplers",
     [(SC, "        for zone_id in list(self._sc_cleanup_timers()):\n            self._sc_cancel_cleanup(zone_id)\n", "")], [T]),
    (3, "teardown cancels only the backstops",
     [(SC, "        for zone_id in list(meters):\n            meters.pop(zone_id)[1]()  # the interval's cancel handle\n", "")], [T]),
    (4, "teardown finalises the meter",
     [(SC, "            meters.pop(zone_id)[1]()  # the interval's cancel handle\n", "            self._sc_finish_flow(zone_id)\n")], [T]),
    (5, "release_all leaves the off timer armed",
     [(MA, "        self._master_hold_set().clear()\n        cancel = getattr(self, \"_master_off_cancel\", None)\n"
           "        if cancel is not None:\n            cancel()\n            self._master_off_cancel = None\n\n"
           "    async def async_master_end_cycle_now",
       "        self._master_hold_set().clear()\n\n    async def async_master_end_cycle_now")], [T]),
    (6, "abort does not release the chain before its stops",
     [(SC, CHAIN_GUARD, "")], [T]),
    (7, "disable does not release the chains",
     [(IN, "            await coordinator.async_release_all_chains(why)\n", "")], [T]),
    (8, "abort filters on == service",
     [(SC, "                if r.get(const.RUN_MODE)\n"
           "                not in (const.WATERING_MODE_OPENSPRINKLER, const.WATERING_MODE_BATCH)\n",
       "                if r.get(const.RUN_MODE) == const.WATERING_MODE_SERVICE\n")], [T]),
    (9, "a reload aborts too",
     [(IN, "            await coordinator.async_master_end_cycle_now()\n        await coordinator.async_unload()",
       "            await coordinator.async_master_end_cycle_now()\n"
       "        await coordinator.async_abort_self_closing_runs(\"reload\")\n        await coordinator.async_unload()")], [T]),
    (10, "settle=False settles anyway",
     [(SC, "                if settle:\n                    if await self.async_stop_self_closing(zone_id):",
       "                if True:\n                    if await self.async_stop_self_closing(zone_id):")], [T]),
    (11, "end-now ignores a remaining hold",
     [(MA, "            if not self._master_configured() or self._master_hold_set():\n",
       "            if not self._master_configured():\n")], [T]),
    (12, "end-now ignores _master_on",
     [(MA, END_NOW_GATE, "            if getattr(self._master_cfg(), const.CONF_MASTER_OFF_AFTER, False):")], [T]),
    (13, "end-now ignores master_off_after",
     [(MA, END_NOW_GATE, "            if getattr(self, \"_master_on\", False):")], [T]),
    (14, "removal ends the master after the delete",
     [(IN, "            await coordinator.async_master_end_cycle_now()\n            await coordinator.async_delete_config()",
       "            await coordinator.async_delete_config()\n            await coordinator.async_master_end_cycle_now()")], [T]),
    (15, "end-now lets an exception through",
     [(MA, "        except Exception:  # noqa: BLE001\n            _LOGGER.exception(\n"
           "                \"Could not end the master cycle; the master %s may still be on\",",
       "        except ZeroDivisionError:\n            _LOGGER.exception(\n"
       "                \"Could not end the master cycle; the master %s may still be on\",")], [T]),
    (16, "abort lets one run's exception through",
     [(SC, "            except Exception:  # noqa: BLE001\n                _LOGGER.exception(\n"
           "                    \"Zone %s: could not stop its self-closing run; it may still \"",
       "            except ZeroDivisionError:\n                _LOGGER.exception(\n"
       "                    \"Zone %s: could not stop its self-closing run; it may still \"")], [T]),
    (17, "release-all lets one chain's exception through",
     [(RC, "            except Exception:  # noqa: BLE001\n                _LOGGER.exception(\n"
           "                    \"Could not release the %s chain; its hold may keep the master on\",",
       "            except ZeroDivisionError:\n                _LOGGER.exception(\n"
       "                    \"Could not release the %s chain; its hold may keep the master on\",")], [T]),
    (18, "disable does not abort the service runs",
     [(IN, "            await coordinator.async_abort_self_closing_runs(why)\n", "")], [T]),
    (19, "disable does not end the master",
     [(IN, "            # The master's off timer goes with the unload, so the cycle ends here.\n"
           "            await coordinator.async_master_end_cycle_now()\n", "")], [T]),
    (20, "_chain_release ignores why",
     [(RC, "        self._chain_forfeit_queue(mode, why)\n",
       "        self._chain_forfeit_queue(mode, \"the cycle was stopped\")\n")], [T]),
    (21, "dispatch_stop ignores the zone's duration field",
     [(SC, "        field = zone.get(const.ZONE_DURATION_FIELD) or \"duration\"\n        data[field] = 0\n"
           "        await self.hass.services.async_call(domain, service, data)\n        return True\n",
       "        field = \"duration\"\n        data[field] = 0\n"
       "        await self.hass.services.async_call(domain, service, data)\n        return True\n")], [T]),
    (22, "teardown: one loop over the samplers",
     [(SC, TEARDOWN,
       "        meters = self._sc_meters()\n        for zone_id in list(meters):\n"
       "            meters.pop(zone_id)[1]()  # the interval's cancel handle\n"
       "            self._sc_cancel_cleanup(zone_id)\n")], [T]),
    (23, "teardown: one loop over the backstops",
     [(SC, TEARDOWN,
       "        meters = self._sc_meters()\n        for zone_id in list(self._sc_cleanup_timers()):\n"
       "            if zone_id in meters:\n                meters.pop(zone_id)[1]()\n"
       "            self._sc_cancel_cleanup(zone_id)\n")], [T]),
    (24, "teardown: first zone only",
     [(SC, TEARDOWN,
       "        meters = self._sc_meters()\n        for zone_id in list(meters):\n"
       "            meters.pop(zone_id)[1]()  # the interval's cancel handle\n            break\n"
       "        for zone_id in list(self._sc_cleanup_timers()):\n"
       "            self._sc_cancel_cleanup(zone_id)\n            break\n")], [T]),
    (25, "teardown in async_unload_entry ahead of the disable branch, not in async_unload",
     [(IN, "        self.async_teardown_self_closing_handles()\n", ""),
      (IN, "        if entry.disabled_by is not None:\n            why = \"the Irrigation Plus config entry is being disabled\"\n",
       "        coordinator.async_teardown_self_closing_handles()\n"
       "        if entry.disabled_by is not None:\n            why = \"the Irrigation Plus config entry is being disabled\"\n")], [T]),
    (26, "stop instruction: OpenSprinkler falls into the adapter",
     [(SC, "            await self._os_dispatch_stop(zone)\n            return True\n",
       "            await self._os_dispatch_stop(zone)\n")], [T]),
    (27, "the caller warns on every successful stop",
     [(SC, "        if close_valve and not await self._sc_dispatch_stop(zone_id, zone):\n",
       "        if close_valve and await self._sc_dispatch_stop(zone_id, zone):\n")], [T]),
    (28, "stop instruction: only None counts as no stop service",
     [(SC, "        if not stop_svc:\n            return False\n", "        if stop_svc is None:\n            return False\n")], [T]),
    (29, "stop instruction: the zone's own id instead of the run's",
     [(SC, "        data[\"zone_id\"] = zone_id\n        # A zero duration IS the stop",
       "        data[\"zone_id\"] = zone.get(const.ZONE_ID)\n        # A zero duration IS the stop")], [T]),
    (30, "disable: OpenSprinkler abort without settling",
     [(IN, "            await coordinator.async_abort_opensprinkler_runs(why)\n",
       "            await coordinator.async_abort_opensprinkler_runs(why, settle=False)\n")], [T]),
    (31, "disable: batch abort without settling",
     [(IN, "            await coordinator.async_abort_batch_runs(why)\n",
       "            await coordinator.async_abort_batch_runs(why, settle=False)\n")], [T]),
    (32, "removal: batch abort settles",
     [(IN, "            await coordinator.async_abort_batch_runs(why, settle=False)\n",
       "            await coordinator.async_abort_batch_runs(why)\n")], [T]),
    (33, "removal does not end the master cycle",
     [(IN, "            await coordinator.async_master_end_cycle_now()\n            await coordinator.async_delete_config()\n",
       "            await coordinator.async_delete_config()\n")], [T]),
    (34, "removal does not stop the service runs",
     [(IN, "            await coordinator.async_abort_self_closing_runs(why, settle=False)\n", "")], [T]),
    (35, "abort: chain release unguarded",
     [(SC, CHAIN_GUARD, "        await self._chain_release(const.WATERING_MODE_SERVICE, reason)\n")], [T]),
    (36, "abort, settle=False: a zone without a stop service counts as stopped",
     [(SC, SETTLE_FALSE_WARNING, "                else:\n                    stopped = True\n")], [T]),
    (37, "release-all releases an idle chain too (if token: -> if True:)",
     [(RC, "        if token:\n            await self.async_master_release(token)\n",
       "        if True:\n            await self.async_master_release(token)\n")], [T]),
    (38, "a sweep without the master clears the flag again",
     [(DI, NO_MASTER_END, "_leaves_the_cycle_up\n            self._master_on = False\n            return\n")], [TD]),
    (39, "async_unload does not call _master_release_all",
     [(IN, "        # with them: it reads these holds when it fires.\n        self._master_release_all()\n",
       "        # with them: it reads these holds when it fires.\n")], [T]),
    (40, "release_all cancels the timer but keeps the holds",
     [(MA, "        self._master_hold_set().clear()\n        cancel = getattr(self, \"_master_off_cancel\", None)\n",
       "        cancel = getattr(self, \"_master_off_cancel\", None)\n")], [T]),
    (41, "end-now gates on the pending timer instead of _master_on",
     [(MA, "            if getattr(self, \"_master_on\", False) and getattr(\n",
       "            if cancel is not None and getattr(\n")], [T]),
    (42, "end-now resets the deadline only when it switches off",
     [(MA, "                await self._master_turn(False)\n            self._master_on = False\n"
           "            self._master_off_deadline = None\n        except Exception:  # noqa: BLE001\n",
       "                await self._master_turn(False)\n                self._master_off_deadline = None\n"
       "            self._master_on = False\n        except Exception:  # noqa: BLE001\n")], [T]),
    (43, "end-now log loses the entity",
     [(MA, "            entity = self._master_entity()\n", "")], [T]),
    (44, "a sweep without the master sets the flag",
     [(DI, NO_MASTER_END, "_leaves_the_cycle_up\n            self._master_on = True\n            return\n")], [TD]),
    (45, "a sweep without the master clears the flag once no hold is left",
     [(DI, NO_MASTER_END, "_leaves_the_cycle_up\n            if not self._master_hold_set():\n"
                          "                self._master_on = False\n            return\n")], [TD]),
    (46, "release-all stops after the first success",
     [(RC, "                await self._chain_release(mode, why)\n            except Exception:",
       "                await self._chain_release(mode, why)\n                break\n            except Exception:")], [T]),
    (47, "release-all logs without the traceback",
     [(RC, "                _LOGGER.exception(\n                    \"Could not release the %s chain",
       "                _LOGGER.warning(\n                    \"Could not release the %s chain")], [T]),
    (48, "abort: a chain release failure still stops the runs",
     [(SC, "                \"Could not release the service chain; its runs are not stopped\"\n            )\n            return False\n",
       "                \"Could not release the service chain; its runs are not stopped\"\n            )\n")], [T]),
    (49, "abort, settle=False: says nothing about a zone without a stop service",
     [(SC, SETTLE_FALSE_WARNING, "                else:\n                    pass\n")], [T]),
    (51, "abort: a settled stop that found no run still counts",
     [(SC, "                    if await self.async_stop_self_closing(zone_id):\n"
           "                        stopped = True\n",
       "                    await self.async_stop_self_closing(zone_id)\n"
       "                    stopped = True\n")], [T]),
    (52, "abort: a run whose stop raised counts as stopped",
     [(SC, "            except Exception:  # noqa: BLE001\n                _LOGGER.exception(\n"
           "                    \"Zone %s: could not stop its self-closing run; it may still \"",
       "            except Exception:  # noqa: BLE001\n                stopped = True\n"
       "                _LOGGER.exception(\n"
       "                    \"Zone %s: could not stop its self-closing run; it may still \"")], [T]),
    (53, "abort: the line naming why a valve closed is gone",
     [(SC, "            _LOGGER.warning(\n"
           "                \"Zone %s: stopping its self-closing run because %s\", zone_id, reason\n"
           "            )\n", "")], [T]),
    (50, "teardown: a write scheduled as a task",
     [(SC, "            meters.pop(zone_id)[1]()  # the interval's cancel handle\n",
       "            meters.pop(zone_id)[1]()  # the interval's cancel handle\n"
       "            self.hass.async_create_task(self._sc_remove_run(zone_id))\n")], [T]),
]


def run_tests(files, timeout=600):
    env = dict(os.environ, TZ="UTC")
    proc = subprocess.Popen(
        [PY, "-m", "pytest", *files, "-p", "_local_socket_unblock", "-q", "--no-header",
         "-rfE", "-p", "no:cacheprovider"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
    )
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        return "HANG", []
    text = out.decode("utf-8", "replace").replace("\r", "\n")
    red = sorted({m.group(1) for m in re.finditer(r"^(?:FAILED|ERROR) (tests/\S+)", text, re.M)})
    summary = [ln for ln in text.splitlines() if re.search(r"\d+ (passed|failed)", ln)]
    return (summary[-1].strip("= ") if summary else "BROKEN"), red


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def main():
    only = {int(a) for a in sys.argv[1:]}
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
    if status.strip():
        sys.exit("tree not clean:\n" + status)
    print("unmutated:", run_tests([T])[0], "|", run_tests([TD])[0], flush=True)
    results = []
    for num, label, edits, files in MUTATIONS:
        if only and num not in only:
            continue
        originals = {}
        ok = True
        for path, anchor, repl in edits:
            if path not in originals:
                originals[path] = read(path)
            current = read(path)
            norm = current.replace("\r\n", "\n")
            if norm.count(anchor) != 1:
                ok = False
                results.append({"num": num, "label": label, "verdict": f"ANCHOR x{norm.count(anchor)}", "red": []})
                break
            mutated = norm.replace(anchor, repl)
            if norm != current:
                mutated = mutated.replace("\n", "\r\n")
            write(path, mutated)
        if ok:
            try:
                summary, red = run_tests(files)
            finally:
                for path, text in originals.items():
                    write(path, text)
            verdict = "KILLED" if red and re.search(r"\d+ failed|\d+ error", summary) else (
                summary if summary in ("HANG", "BROKEN") else "SURVIVED")
            results.append({"num": num, "label": label, "verdict": verdict, "summary": summary, "red": red})
        else:
            for path, text in originals.items():
                write(path, text)
        r = results[-1]
        print(f"{num:2d} {r['verdict']:9s} {label}  [{r.get('summary', '')}]", flush=True)
        for name in r["red"]:
            print(f"      red: {name}", flush=True)
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
    print("tree after:", "clean" if not status.strip() else status)
    killed = sum(r["verdict"] == "KILLED" for r in results)
    print(f"killed {killed}/{len(results)}")
    for r in results:
        if r["verdict"] != "KILLED":
            print(f"NOT KILLED {r['num']} {r['label']}: {r['verdict']}")
    with open(r"D:\Entwicklung\HASI\issue9-work\mutate-final.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)


if __name__ == "__main__":
    main()
