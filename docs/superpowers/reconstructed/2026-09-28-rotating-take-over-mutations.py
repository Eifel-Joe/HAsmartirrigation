"""Task 7: apply each mutation, run the two chain suites, record, revert.

A mutation is KILLED when it makes tests fail that pass on the unmutated branch.
Pre-existing baseline errors are therefore measured first and subtracted, not
assumed away.

Run from the worktree:
    python /d/Entwicklung/HASI/issue45-work/mutate.py
"""

import io
import json
import os
import subprocess
import sys

WT = r"D:\Entwicklung\HASI\issue45-work\wt"
SRC = os.path.join(WT, "custom_components", "irrigation_plus", "run_chain.py")
PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
SUITES = ["tests/test_service_chain.py", "tests/test_chain_carries_its_plan.py"]

DISPATCH_CLAIM = "            rotation.in_flight = zone_id\n"
DISPATCH_CALL = """            if await self.async_run_self_closing(
                dict(zone, **{const.ZONE_DURATION: slot}), trigger=state.trigger
            ):
                return
"""

ELIF_BLOCK = """                elif rotation.remaining[zid] > 0:
                    # Some other run watered a zone this rotation still holds and
                    # has now ended, so its remainder goes the way a zone taken
                    # over while the rotation waited already does. This is the
                    # only moment it can be caught: the run record a guard would
                    # read is removed before this call, so by the zone's own turn
                    # there is nothing left to see. Written off here rather than
                    # remembered for the turn, so a stop landing in between does
                    # not report an already-watered zone as abandoned.
                    policy = chain_policy_for(mode)
                    _LOGGER.info(
                        "%s rotation: writing off zone %s and its remaining "
                        "%.0fs, another run watered it before its turn",
                        policy.label if policy else mode,
                        zid,
                        rotation.remaining[zid],
                    )
                    rotation.remaining[zid] = 0.0
                    # Safe although that run has been and gone: a run's ceiling is
                    # decided at its own dispatch and frozen into its record, so
                    # the marker it used is long consumed. What goes back is the
                    # rotation's own leftover.
                    self._drop_live_run_marker(zid)
"""

MUTATIONS = [
    (
        1,
        "drop the claim at the dispatch",
        DISPATCH_CLAIM,
        "",
    ),
    (
        2,
        "in_flight != zid instead of == zid",
        "                if rotation.in_flight == zid:\n",
        "                if rotation.in_flight != zid:\n",
    ),
    (
        3,
        "drop the take-over branch entirely",
        ELIF_BLOCK,
        "",
    ),
    (
        4,
        "remaining >= 0 instead of > 0",
        "                elif rotation.remaining[zid] > 0:\n",
        "                elif rotation.remaining[zid] >= 0:\n",
    ),
    (
        5,
        "claim the slot AFTER the await instead of before",
        DISPATCH_CLAIM + DISPATCH_CALL,
        DISPATCH_CALL.replace("                return\n", "")
        + "                rotation.in_flight = zone_id\n"
        + "                return\n",
    ),
    (
        6,
        "drop the live-marker hand-back",
        "                    self._drop_live_run_marker(zid)\n",
        "",
    ),
    (
        7,
        "reuse the sibling branch's wording",
        '%.0fs, another run watered it before its turn",\n',
        '%.0fs, another run took it over while it waited",\n',
    ),
]


def read_src():
    raw = io.open(SRC, "rb").read()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def write_src(text, crlf):
    out = text.replace("\n", "\r\n") if crlf else text
    io.open(SRC + ".tmp", "wb").write(out.encode("utf-8"))
    os.replace(SRC + ".tmp", SRC)


def run_suites():
    """Return the set of 'FAILED/ERROR tests/...' names."""
    env = dict(os.environ)
    env.update(
        TMPDIR=r"D:\Entwicklung\HASI\issue45-work\tmp",
        TEMP=r"D:\Entwicklung\HASI\issue45-work\tmp",
        TMP=r"D:\Entwicklung\HASI\issue45-work\tmp",
    )
    proc = subprocess.run(
        [PY, "-m", "pytest", *SUITES, "-p", "_local_socket_unblock", "-q"],
        cwd=WT,
        env=env,
        capture_output=True,
        text=True,
    )
    names = set()
    for line in (proc.stdout + proc.stderr).splitlines():
        if line.startswith(("FAILED tests/", "ERROR tests/")):
            names.add(line.split(" - ")[0].strip())
    return names


def main():
    original, crlf = read_src()
    print("measuring the unmutated branch ...", flush=True)
    reference = run_suites()
    print("  pre-existing failures/errors: %d" % len(reference), flush=True)

    results = []
    for n, label, old, new in MUTATIONS:
        if original.count(old) != 1:
            print("MUT %d: anchor not unique (%d) -- SKIPPED" % (n, original.count(old)))
            results.append(
                {"n": n, "mutation": label, "result": "not applied", "why": "anchor"}
            )
            continue
        write_src(original.replace(old, new, 1), crlf)
        try:
            after = run_suites()
        finally:
            write_src(original, crlf)
        extra = sorted(after - reference)
        row = {
            "n": n,
            "mutation": label,
            "result": "killed" if extra else "survived",
        }
        if extra:
            row["killed_by"] = extra
        results.append(row)
        print(
            "MUT %d %-45s %s%s"
            % (
                n,
                label,
                row["result"].upper(),
                (" by %d test(s)" % len(extra)) if extra else "",
            ),
            flush=True,
        )
        for name in extra:
            print("        %s" % name.split("::", 1)[-1], flush=True)

    io.open(
        r"D:\Entwicklung\HASI\issue45-work\mutations.json", "w", encoding="utf-8"
    ).write(json.dumps(results, indent=2))

    now, _ = read_src()
    print("\nsource restored byte-for-byte: %s" % (now == original))
    killed = sum(1 for r in results if r["result"] == "killed")
    print("%d of %d killed" % (killed, len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
