"""Apply each mutation, run the pytest files, record, revert (inlet gate branch).

Engine from issue5-work/mutate.py (archived as
docs/superpowers/probes/2026-09-29-zone-save-mutations.py); pytest only, because
this branch changes no TypeScript. Three guards added: the mutated sources must be
clean against HEAD before anything is applied; a run whose summary shows no
passed/failed count is reported BROKEN, never "survived"; and a run that does not
end within MUT_TIMEOUT seconds (default 300) is killed with its process tree and
reported HANG. Mutation 5 deadlocks
test_distributor_cycle.py::test_second_concurrent_cycle_rejected_by_single_flight_lock
(its second cycle waits on the first one's event), so it ends as HANG here and is
read from mut5_rerun.py, which deselects that one test. MUT_ONLY="5,9" limits a run
to the listed mutations.

Run:
    python D:/Entwicklung/HASI/issue66-work/mutate.py [worktree] [out.json]
"""

import io
import json
import os
import re
import subprocess
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else r"D:\Entwicklung\HASI\issue66-work\wt"
PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
TMP = r"D:\Entwicklung\HASI\issue66-work\tmp"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"D:\Entwicklung\HASI\issue66-work\mutations.json"
RUN_TIMEOUT = int(os.environ.get("MUT_TIMEOUT", "300"))
ONLY = {int(n) for n in os.environ.get("MUT_ONLY", "").split(",") if n.strip()}

IP = os.path.join(WT, "custom_components", "irrigation_plus")
DIST = os.path.join(IP, "distributor.py")
CONST = os.path.join(IP, "const.py")

# Every test named as a killer below lives in one of these.
SUITES = [
    "tests/test_distributor_inlet_gate.py",
    "tests/test_distributor.py",
    "tests/test_distributor_cycle.py",
    "tests/test_distributor_dispatch.py",
    "tests/test_distributor_integration.py",
]

MUTATIONS = [
    (1, CONST, "closing no longer blocks",
     '{"on", "open", "opening", "closing"}', '{"on", "open", "opening"}',
     "test_the_claim_refuses_while_the_inlet_reports_open[closing]"),
    (2, DIST, "the gate is never consulted",
     "        blocking = self._dist_inlet_reports_open(distributor)\n",
     "        blocking = None\n",
     "every refusal test"),
    (3, DIST, "a missing entity blocks",
     "        if state is None or state.state not in const.DISTRIBUTOR_INLET_OPEN_STATES:\n",
     "        if state is not None and state.state not in const.DISTRIBUTOR_INLET_OPEN_STATES:\n",
     "test_the_claim_lets_a_cycle_through_when_the_inlet_entity_does_not_exist"),
    (4, DIST, "the claim is taken before the gate",
     "        blocking = self._dist_inlet_reports_open(distributor)\n",
     "        inflight.add(dist_id)\n"
     "        blocking = self._dist_inlet_reports_open(distributor)\n",
     "test_the_claim_refuses_while_the_inlet_reports_open (id left in flight)"),
    (5, DIST, "no in-flight guard: the gate answers for our own sweep",
     "        if dist_id in inflight:\n            return False\n",
     "",
     "test_a_distributor_in_flight_is_not_reported_as_an_open_inlet"),
    (6, DIST, "the history uses the whole target, direct zones included",
     "            members = [zid for zid in members if zid in wanted]\n",
     "            members = sorted(wanted)\n",
     "test_a_refusal_records_only_the_targeted_members"),
    (7, DIST, "a test run records history",
     "        if test_run:\n            return\n        members = [",
     "        members = [",
     "test_a_refused_test_run_records_no_history"),
    (8, DIST, "the grace never ends",
     "            < const.DISTRIBUTOR_INLET_CLOSE_GRACE_SECONDS\n",
     "            < float(\"inf\")\n",
     "test_the_grace_runs_out_after_thirty_seconds"),
    (9, DIST, "the service no-op stamps too",
     "                self._dist_stamp_own_close(distributor)\n"
     "            return\n",
     "            self._dist_stamp_own_close(distributor)\n"
     "            return\n",
     "test_a_service_distributor_without_stop_service_gets_no_grace"),
    (10, DIST, "the grace is shared by every distributor",
     "        closed_at = self._dist_own_close_times().get(distributor.get(\"id\"))\n",
     "        closed_at = max(self._dist_own_close_times().values(), default=None)\n",
     "test_the_grace_belongs_to_the_distributor_that_closed"),
    (11, DIST, "the classic close is stamped before it is sent",
     "        await self._dist_domain_turn(distributor.get(\"inlet_entity\"), False)\n"
     "        self._dist_stamp_own_close(distributor)\n",
     "        self._dist_stamp_own_close(distributor)\n"
     "        await self._dist_domain_turn(distributor.get(\"inlet_entity\"), False)\n",
     "test_a_close_that_raised_starts_no_grace"),
    (12, DIST, "a forced member run recorded as schedule",
     'trigger="manual" if force_water else "schedule"',
     'trigger="schedule"',
     "test_a_refused_forced_member_run_is_recorded_as_manual"),
    (13, DIST, "the classic close is never stamped",
     "        await self._dist_domain_turn(distributor.get(\"inlet_entity\"), False)\n"
     "        self._dist_stamp_own_close(distributor)\n",
     "        await self._dist_domain_turn(distributor.get(\"inlet_entity\"), False)\n",
     "test_the_next_cycle_runs_within_the_grace_after_our_own_close"),
    (14, DIST, "the stop_service close is never stamped",
     "                await self.hass.services.async_call(domain, service, data)\n"
     "                self._dist_stamp_own_close(distributor)\n",
     "                await self.hass.services.async_call(domain, service, data)\n",
     "test_a_stop_service_close_starts_the_grace"),
    (15, DIST, "an empty inlet entity is looked up",
     "        if not entity_id:\n            return None\n        state = ",
     "        state = ",
     "test_the_claim_lets_a_cycle_through_without_an_inlet_entity"),
    (16, DIST, "the refusal sends no notification",
     "        await self._dist_notify(distributor, message)\n        if test_run:",
     "        if test_run:",
     "test_a_refusal_is_logged_and_notified, test_a_refused_test_run_records_no_history"),
    (17, DIST, "an empty member list is still recorded",
     "        if not members:\n            return\n        await self._record_skipped_run(",
     "        await self._record_skipped_run(",
     "test_a_refusal_records_nothing_when_no_member_was_targeted"),
    (18, DIST, "the eligibility predicate asks the inlet too (the rejected place)",
     "        if not members:\n            return False\n        if not require_due:",
     "        if not members:\n            return False\n"
     "        if self._dist_inlet_reports_open(distributor) is not None:\n"
     "            return False\n"
     "        if not require_due:",
     "the estimate pin of Task 5"),
    # Added after the code review of Tasks 1-2 (plan addendum A10).
    (19, DIST, "a yield between the in-flight check and inflight.add",
     "        inflight.add(dist_id)\n",
     "        await asyncio.sleep(0)\n        inflight.add(dist_id)\n",
     "test_two_claims_scheduled_together_start_exactly_one_sweep"),
    (20, DIST, "a test run skips the gate",
     "        blocking = self._dist_inlet_reports_open(distributor)\n",
     "        blocking = None if test_run else self._dist_inlet_reports_open(distributor)\n",
     "test_the_test_run_meets_the_gate, test_a_refused_test_run_records_no_history"),
    (21, DIST, "a forced member run skips the gate",
     "        blocking = self._dist_inlet_reports_open(distributor)\n",
     "        blocking = None if force_water else self._dist_inlet_reports_open(distributor)\n",
     "test_a_member_run_with_a_duration_meets_the_gate, test_a_refused_forced_member_run_is_recorded_as_manual"),
    (22, DIST, "the gate asked before the in-flight guard",
     "        if dist_id in inflight:\n"
     "            return False\n"
     "        # #181: never start over an open inlet. After the in-flight guard, because\n"
     "        # the integration's own sweep holds the inlet open and must read \"in\n"
     "        # flight\", not \"open\"; before inflight.add with no await in between, so the\n"
     "        # single-flight guarantee is unchanged.\n"
     "        # The refusal awaits only after this decision, holding nothing.\n"
     "        blocking = self._dist_inlet_reports_open(distributor)\n"
     "        if blocking is not None:\n"
     "            await self._dist_refuse_inlet_open(\n"
     "                distributor,\n"
     "                blocking,\n"
     "                test_run=test_run,\n"
     "                only_zone_ids=only_zone_ids,\n"
     "                force_water=force_water,\n"
     "            )\n"
     "            return False\n"
     "        inflight.add(dist_id)\n",
     "        blocking = self._dist_inlet_reports_open(distributor)\n"
     "        if blocking is not None:\n"
     "            await self._dist_refuse_inlet_open(\n"
     "                distributor,\n"
     "                blocking,\n"
     "                test_run=test_run,\n"
     "                only_zone_ids=only_zone_ids,\n"
     "                force_water=force_water,\n"
     "            )\n"
     "            return False\n"
     "        if dist_id in inflight:\n"
     "            return False\n"
     "        inflight.add(dist_id)\n",
     "test_a_distributor_in_flight_is_not_reported_as_an_open_inlet"),
    # Added after the code review of Task 3 and the root guard (plan addenda A11, A12).
    (23, DIST, "the optional notify forward unguarded again",
     "        try:\n"
     "            domain, service = self._dist_split_service(target)\n"
     "            if domain and service:\n"
     "                await self.hass.services.async_call(\n"
     "                    domain, service, {\"message\": message}\n"
     "                )\n"
     "        except Exception:  # noqa: BLE001 - an optional channel must not fail its caller\n"
     "            _LOGGER.exception(\n"
     "                \"Distributor '%s': could not forward the notification to %s\",\n"
     "                distributor.get(\"name\"),\n"
     "                target,\n"
     "            )\n",
     "        domain, service = self._dist_split_service(target)\n"
     "        if domain and service:\n"
     "            await self.hass.services.async_call(domain, service, {\"message\": message})\n",
     "test_notify_a_failing_target_is_logged_not_raised, test_resume_goes_on_after_a_failing_notify_target, test_a_broken_notify_target_does_not_stop_the_history"),
    (24, DIST, "the refusal notice ignores the user's language",
     "            \"panels.distributors.notify.inlet_open\", self.hass.config.language\n",
     "            \"panels.distributors.notify.inlet_open\", \"en\"\n",
     "test_a_refusal_is_notified_in_the_users_language"),
    (25, DIST, "an empty target records every member",
     "        if only_zone_ids is not None:\n            wanted = ",
     "        if only_zone_ids:\n            wanted = ",
     "test_a_refusal_with_an_empty_target_records_nothing"),
    (26, CONST, "the skip code has no catalogue key",
     "SKIP_REASON_INLET_OPEN = \"inlet_open\"",
     "SKIP_REASON_INLET_OPEN = \"inlet_gate\"",
     "test_the_skip_reason_is_a_key_every_language_localizes"),
    (27, DIST, "the members of another distributor are recorded",
     "            for m in await self._dist_members(distributor.get(\"id\"))\n",
     "            for m in await self._dist_members(None)\n",
     "test_a_refusal_records_every_member_as_an_explicit_list"),
    (28, DIST, "the notify guard widened to BaseException",
     "        except Exception:  # noqa: BLE001 - an optional channel must not fail its caller\n",
     "        except BaseException:  # noqa: BLE001 - an optional channel must not fail its caller\n",
     "test_notify_a_cancellation_still_cancels"),
    # Added after the re-review of the root guard (plan addendum A12, Task 3d).
    (29, DIST, "the notify guard narrowed to ServiceNotFound",
     "        except Exception:  # noqa: BLE001 - an optional channel must not fail its caller\n",
     "        except __import__(\"homeassistant.exceptions\").exceptions.ServiceNotFound:\n",
     "test_notify_a_failing_target_is_logged_not_raised[its_schema_rejects_the_message], test_notify_a_corrupt_target_is_logged_not_raised"),
    (30, DIST, "the notify guard narrowed to ServiceNotFound and vol.Invalid",
     "        except Exception:  # noqa: BLE001 - an optional channel must not fail its caller\n",
     "        except (\n"
     "            __import__(\"homeassistant.exceptions\").exceptions.ServiceNotFound,\n"
     "            __import__(\"voluptuous\").Invalid,\n"
     "        ):\n",
     "test_notify_a_corrupt_target_is_logged_not_raised"),
    (31, DIST, "the target split outside the notify guard",
     "        try:\n"
     "            domain, service = self._dist_split_service(target)\n",
     "        domain, service = self._dist_split_service(target)\n"
     "        try:\n",
     "test_notify_a_corrupt_target_is_logged_not_raised"),
    # Added after the code review of Task 4 (plan addendum A13, Task 4b).
    (32, DIST, "a stop_service close stamped before it is sent",
     "                await self.hass.services.async_call(domain, service, data)\n"
     "                self._dist_stamp_own_close(distributor)\n",
     "                self._dist_stamp_own_close(distributor)\n"
     "                await self.hass.services.async_call(domain, service, data)\n",
     "test_a_stop_service_that_raised_starts_no_grace"),
    (33, DIST, "the first close keeps its stamp",
     "        self._dist_own_close_times()[distributor.get(\"id\")] = self.hass.loop.time()\n",
     "        self._dist_own_close_times().setdefault(distributor.get(\"id\"), self.hass.loop.time())\n",
     "test_a_later_close_restarts_the_grace"),
    (34, DIST, "the grace still holds at exactly 30 s",
     "            < const.DISTRIBUTOR_INLET_CLOSE_GRACE_SECONDS\n",
     "            <= const.DISTRIBUTOR_INLET_CLOSE_GRACE_SECONDS\n",
     "test_the_grace_is_over_at_exactly_thirty_seconds"),
    (35, DIST, "every stamp kept under distributor 0",
     "        self._dist_own_close_times()[distributor.get(\"id\")] = self.hass.loop.time()\n",
     "        self._dist_own_close_times()[0] = self.hass.loop.time()\n",
     "test_the_grace_runs_for_a_distributor_that_is_not_number_zero"),
    # Added after the final review (plan addendum A14).
    (36, DIST, "the grace does not cover an inlet that reports closing",
     "            closed_at is not None\n",
     "            closed_at is not None\n"
     "            and state.state != \"closing\"\n",
     "test_the_next_cycle_runs_within_the_grace_after_our_own_close[closing]"),
]


def read_src(path):
    raw = io.open(path, "rb").read()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def write_src(path, text, crlf):
    out = text.replace("\n", "\r\n") if crlf else text
    io.open(path + ".tmp", "wb").write(out.encode("utf-8"))
    os.replace(path + ".tmp", path)


def run_pytest():
    env = dict(os.environ)
    env.update(TMPDIR=TMP, TEMP=TMP, TMP=TMP, TZ="UTC")
    proc = subprocess.Popen(
        [PY, "-m", "pytest", *SUITES, "-p", "_local_socket_unblock", "-q"],
        cwd=WT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        # The venv's python.exe is a launcher; pytest runs in its child, which a
        # plain kill() would leave running with the pipes open. Kill the tree.
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                       capture_output=True)
        proc.communicate()
        return set(), "HANG"
    names = set()
    for line in (stdout + stderr).splitlines():
        if line.startswith(("FAILED tests/", "ERROR tests/")):
            names.add(line.split(" - ")[0].strip())
    tail = [ln for ln in stdout.splitlines() if " passed" in ln or " failed" in ln]
    return names, (tail[-1] if tail else "NO SUMMARY LINE")


def run_all():
    return run_pytest()


def collected(summary):
    return re.search(r"\d+ (passed|failed)", summary) is not None


def main():
    os.makedirs(TMP, exist_ok=True)
    paths = sorted({m[1] for m in MUTATIONS})
    dirty = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *paths], cwd=WT
    ).returncode
    if dirty:
        raise SystemExit("a mutated source differs from HEAD - refusing to mutate over it")
    originals = {p: read_src(p) for p in paths}

    print("measuring the unmutated branch in %s ..." % WT, flush=True)
    reference, summary = run_all()
    print("  %s" % summary, flush=True)
    print("  pre-existing failures/errors: %d" % len(reference), flush=True)
    if not collected(summary) or " 0 passed" in summary:
        raise SystemExit("a run collected nothing - every result would be a lie")

    results = []
    for n, path, label, old, new, expected in MUTATIONS:
        if ONLY and n not in ONLY:
            continue
        original, crlf = originals[path]
        count = original.count(old)
        if count != 1:
            print("MUT %2d: anchor appears %d times -- SKIPPED" % (n, count))
            results.append({"n": n, "file": os.path.basename(path),
                            "mutation": label, "result": "NOT APPLIED",
                            "why": "anchor appears %d times" % count})
            continue
        write_src(path, original.replace(old, new, 1), crlf)
        try:
            after, after_summary = run_all()
        finally:
            write_src(path, original, crlf)
        extra = sorted(after - reference)
        if after_summary == "HANG":
            result = "HANG"
        elif not collected(after_summary):
            result = "BROKEN"
        else:
            result = "killed" if extra else "survived"
        row = {"n": n, "file": os.path.basename(path), "mutation": label,
               "expected_killer": expected,
               "result": result,
               "summary": after_summary}
        if extra:
            row["killed_by"] = extra
        results.append(row)
        print("MUT %2d %-50s %s%s" % (n, label, row["result"].upper(),
              (" by %d test(s)" % len(extra)) if extra else ""), flush=True)
        for name in extra:
            print("         %s" % name.split("::", 1)[-1], flush=True)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(results, indent=2))
    ok = all(read_src(p)[0] == originals[p][0] for p in originals)
    print("\nevery source restored byte-for-byte: %s" % ok)
    killed = sum(1 for r in results if r.get("result") == "killed")
    applied = sum(1 for r in results if r.get("result") != "NOT APPLIED")
    hung = [r["n"] for r in results if r.get("result") == "HANG"]
    print("%d killed / %d applied / %d total%s" % (
        killed, applied, len(MUTATIONS), ("; HANG: %s" % hung) if hung else ""))


if __name__ == "__main__":
    main()
