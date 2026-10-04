"""Write the plan's state after commit N into a scratch worktree, run a test
selection there, and optionally measure mutants (restored from memory).

Usage: python verify_task.py N SELECTION [--base-of PATH ...] [--mutants SET]
  --base-of PATH : write PATH at the state BEFORE commit N (the RED side)
The scratch worktree D:/Entwicklung/HASI/issue9-work/vwt must exist (detached).
"""

import argparse
import importlib.util
import os
import re
import subprocess

VWT = r"D:\Entwicklung\HASI\issue9-work\vwt"
PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"

spec = importlib.util.spec_from_file_location("sc", r"D:\Entwicklung\HASI\issue9-work\spec_check.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

CC = sc.CC

MUTANTS = {
    "t3": [
        ("M5 release_all leaves the off timer", CC + "master.py",
         "        self._master_hold_set().clear()\n"
         "        cancel = getattr(self, \"_master_off_cancel\", None)\n"
         "        if cancel is not None:\n"
         "            cancel()\n"
         "            self._master_off_cancel = None\n",
         "        self._master_hold_set().clear()\n"),
        ("unload does not call _master_release_all", CC + "__init__.py",
         "        # with them: it reads these holds when it fires.\n"
         "        self._master_release_all()\n",
         "        # with them: it reads these holds when it fires.\n"),
        ("release_all cancels but keeps the holds", CC + "master.py",
         "        self._master_hold_set().clear()\n"
         "        cancel = getattr(self, \"_master_off_cancel\", None)\n",
         "        cancel = getattr(self, \"_master_off_cancel\", None)\n"),
    ],
    "t4": [
        ("end-now gates on the pending timer instead of _master_on", CC + "master.py",
         "            if getattr(self, \"_master_on\", False) and getattr(\n",
         "            if cancel is not None and getattr(\n"),
        ("end-now resets the deadline only when it switches off", CC + "master.py",
         "                await self._master_turn(False)\n"
         "            self._master_on = False\n"
         "            self._master_off_deadline = None\n"
         "        except Exception:  # noqa: BLE001\n"
         "            _LOGGER.exception(\n"
         "                \"Could not end the master cycle; the master %s may still be on\",\n",
         "                await self._master_turn(False)\n"
         "                self._master_off_deadline = None\n"
         "            self._master_on = False\n"
         "        except Exception:  # noqa: BLE001\n"
         "            _LOGGER.exception(\n"
         "                \"Could not end the master cycle; the master %s may still be on\",\n"),
        ("end-now catches RuntimeError only", CC + "master.py",
         "        except Exception:  # noqa: BLE001\n"
         "            _LOGGER.exception(\n"
         "                \"Could not end the master cycle; the master %s may still be on\",\n",
         "        except RuntimeError:  # noqa: BLE001\n"
         "            _LOGGER.exception(\n"
         "                \"Could not end the master cycle; the master %s may still be on\",\n"),
        ("end-now log loses the entity", CC + "master.py",
         "            entity = self._master_entity()\n", ""),
    ],
    "t5": [
        ("release_all releases on an idle chain too (if token: -> if True:)", CC + "run_chain.py",
         "        if token:\n            await self.async_master_release(token)\n",
         "        if True:\n            await self.async_master_release(token)\n"),
        ("release_all stops after the first success", CC + "run_chain.py",
         "                await self._chain_release(mode, why)\n            except Exception:",
         "                await self._chain_release(mode, why)\n                break\n            except Exception:"),
        ("release_all logs without the traceback", CC + "run_chain.py",
         "                _LOGGER.exception(\n                    \"Could not release the %s chain",
         "                _LOGGER.warning(\n                    \"Could not release the %s chain"),
        ("release_all forgets why", CC + "run_chain.py",
         "                await self._chain_release(mode, why)\n",
         "                await self._chain_release(mode)\n"),
    ],
    "t6": [
        ("U1 OpenSprinkler falls into the adapter (return True dropped)", CC + "self_closing.py",
         "            await self._os_dispatch_stop(zone)\n            return True\n",
         "            await self._os_dispatch_stop(zone)\n"),
        ("U3 only None counts as no stop_service", CC + "self_closing.py",
         "        if not stop_svc:\n            return False\n",
         "        if stop_svc is None:\n            return False\n"),
        ("U4 the zone's own id instead of the run's", CC + "self_closing.py",
         "        data[\"zone_id\"] = zone_id\n        # A zero duration IS the stop",
         "        data[\"zone_id\"] = zone.get(const.ZONE_ID)\n        # A zero duration IS the stop"),
    ],
    "t7": [
        ("settle=False counts a zone without a stop service as stopped", CC + "self_closing.py",
         "                else:\n                    _LOGGER.warning(\n"
         "                        \"Zone %s has no stop_service; its valve runs on to the \"\n"
         "                        \"end of its own countdown\",\n                        zone_id,\n"
         "                    )\n",
         "                else:\n                    stopped = True\n"),
        ("settle=False says nothing about a zone without a stop service", CC + "self_closing.py",
         "                else:\n                    _LOGGER.warning(\n"
         "                        \"Zone %s has no stop_service; its valve runs on to the \"\n"
         "                        \"end of its own countdown\",\n                        zone_id,\n"
         "                    )\n",
         "                else:\n                    pass\n"),
        ("chain release unguarded", CC + "self_closing.py",
         "        try:\n            await self._chain_release(const.WATERING_MODE_SERVICE, reason)\n"
         "        except Exception:  # noqa: BLE001\n            _LOGGER.exception(\n"
         "                \"Could not release the service chain; its runs are not stopped\"\n"
         "            )\n            return False\n",
         "        await self._chain_release(const.WATERING_MODE_SERVICE, reason)\n"),
        ("chain release failure still stops the runs", CC + "self_closing.py",
         "                \"Could not release the service chain; its runs are not stopped\"\n"
         "            )\n            return False\n",
         "                \"Could not release the service chain; its runs are not stopped\"\n"
         "            )\n"),
    ],
    "t8": [
        ("M1 disable: OpenSprinkler abort without settling", CC + "__init__.py",
         "            await coordinator.async_abort_opensprinkler_runs(why)\n",
         "            await coordinator.async_abort_opensprinkler_runs(why, settle=False)\n"),
        ("M2 disable: batch abort without settling", CC + "__init__.py",
         "            await coordinator.async_abort_batch_runs(why)\n",
         "            await coordinator.async_abort_batch_runs(why, settle=False)\n"),
        ("M3 removal: batch abort settles", CC + "__init__.py",
         "            await coordinator.async_abort_batch_runs(why, settle=False)\n",
         "            await coordinator.async_abort_batch_runs(why)\n"),
        ("removal does not end the master cycle", CC + "__init__.py",
         "            await coordinator.async_master_end_cycle_now()\n"
         "            await coordinator.async_delete_config()\n",
         "            await coordinator.async_delete_config()\n"),
        ("removal does not stop the service runs", CC + "__init__.py",
         "            await coordinator.async_abort_self_closing_runs(why, settle=False)\n", ""),
        ("disable does not end the master cycle", CC + "__init__.py",
         "            # The master's off timer goes with the unload, so the cycle ends here.\n"
         "            await coordinator.async_master_end_cycle_now()\n", ""),
    ],
    "t7u2": [
        ("U2 the warning on every successful stop (and not await -> and await)", CC + "self_closing.py",
         "        if close_valve and not await self._sc_dispatch_stop(zone_id, zone):\n",
         "        if close_valve and await self._sc_dispatch_stop(zone_id, zone):\n"),
    ],
    "t4b": [
        ("no-master end clears the flag again", CC + "distributor.py",
         "_leaves_the_cycle_up\n            return\n",
         "_leaves_the_cycle_up\n            self._master_on = False\n            return\n"),
        ("U1 no-master end sets the flag", CC + "distributor.py",
         "_leaves_the_cycle_up\n            return\n",
         "_leaves_the_cycle_up\n            self._master_on = True\n            return\n"),
        ("K3 clears only once no hold is left", CC + "distributor.py",
         "_leaves_the_cycle_up\n            return\n",
         "_leaves_the_cycle_up\n            if not self._master_hold_set():\n"
         "                self._master_on = False\n            return\n"),
    ],
}


def state_after(n):
    """{path: text} for every source path the plan touches, after commit n."""
    state = {}
    for i in range(1, n + 1):
        label, _tests, ops = sc.TASKS[i]
        for op in ops:
            if op[0] == sc.TEST:
                continue
            if op[0] not in state:
                state[op[0]] = sc.blob(sc.BASE, op[0])
            state[op[0]] = sc.apply_op(state[op[0]], label, op)
    return state


def write(path, text):
    full = os.path.join(VWT, path)
    with open(full, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def run(selection):
    env = dict(os.environ, TZ="UTC")
    proc = subprocess.run(
        [PY, "-m", "pytest", *selection, "-p", "_local_socket_unblock", "-q",
         "--no-header", "-rfE", "-p", "no:cacheprovider"],
        cwd=VWT, capture_output=True, env=env, timeout=600,
    )
    text = proc.stdout.decode("utf-8", "replace").replace("\r", "\n")
    red = sorted({m.group(1) for m in re.finditer(r"^((?:FAILED|ERROR) tests/\S+(?: - .{0,160})?)", text, re.M)})
    summary = [ln for ln in text.splitlines() if re.search(r"\d+ (passed|failed)", ln)]
    return (summary[-1].strip("= ") if summary else "BROKEN (nothing collected?)"), red


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("selection", nargs="+")
    ap.add_argument("--base-of", nargs="*", default=[])
    ap.add_argument("--mutants")
    args = ap.parse_args()
    after = state_after(args.n)
    before = state_after(args.n - 1)
    for path, text in after.items():
        write(path, text)
    write(sc.TEST, sc.expected_test_file(args.n))
    print("plan state after commit", args.n, ":", run(args.selection)[0])
    if args.base_of:
        for path in args.base_of:
            write(path, before.get(path) or sc.blob(sc.BASE, path))
        summary, red = run(args.selection)
        print("RED side (", ", ".join(args.base_of), "before the commit):", summary)
        for r in red:
            print("    " + r)
        for path in args.base_of:
            write(path, after[path])
    for label, path, anchor, repl in MUTANTS.get(args.mutants or "", []):
        text = after[path]
        n = text.count(anchor)
        if n != 1:
            print(f"{label}: ANCHOR x{n}")
            continue
        write(path, text.replace(anchor, repl))
        summary, red = run(args.selection)
        write(path, text)
        print(f"{label}: {summary}")
        for r in red:
            print("    " + r)


if __name__ == "__main__":
    main()
