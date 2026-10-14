"""Mechanical spec check for one task of the PR-3 plan.

The probe run of 2026-10-14 committed Tasks 1-9 on the same base (6fa424e8) as
one commit per task (probe-wt, head 8bd004a9); the plan's code and test blocks
were generated from that chain, and its range diff equals
probe-2026-10-14.patch byte for byte (cmp, 2026-10-14). For task N this script
compares the implementer's range BASE..HEAD with the probe's range
P[N-1]..P[N]:

  1. per-file diff of the two ranges must be identical (index/@@ lines are
     normalised away, so earlier reviewed deviations that only shift line
     numbers do not count),
  2. the set of touched files must be identical,
  3. commit messages: first subject equals the plan's dictated subject, every
     body ends with the Opus 5.5 trailer, no issue refs (Eifel-Joe#, JustChr#),
  4. the added lines carry no own-reference markers.

Usage: python spec_check.py N BASE HEAD
Exit 0 = PASS, 1 = FAIL (details printed).
"""

import re
import subprocess
import sys

PROBE = {
    0: "6fa424e8",
    1: "d4817574",
    2: "9233cf6b",
    3: "71276b0d",
    4: "27e7b551",
    5: "3333f841",
    6: "c7677cf1",
    7: "b36bc93d",
    8: "76de3372",
    9: "8bd004a9",
}
SUBJECT = {
    1: "refactor(liveness): one function cuts a zone's window for every caller",
    2: "feat(weather): hourly rows charge each hour only for its measured time",
    3: "feat(weather): the replayed balance places a pausing group's ET in measured time",
    4: "feat(calculation): the hourly form books a pausing group's measured time",
    5: "feat(liveness): a pausing group is cut under the hourly calculation too",
    6: "feat(live): the live estimate leaves out a pausing group's silent time",
    7: "feat(live): the daily mirror books the share the commit books",
    8: "feat(live): the projection to the decision point is priced off measured time",
    9: "feat(liveness): an outage of a pausing group refreshes the live estimate",
}
TRAILER = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
OWN_REF = re.compile(
    r"Eifel-Joe|spec D[0-9]|spec §|Task [0-9]|\bG[0-9]{1,2}\b|PR [123]\b|PR [A-T]\b"
)
WT = "D:/Entwicklung/HASI/issue8-pr3-work/wt"


def git(*args):
    return subprocess.run(
        ["git", "-C", WT, *args], capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout


def per_file(a, b):
    out = {}
    raw = git("diff", "--no-color", "--no-ext-diff", a, b)
    cur = None
    for line in raw.splitlines():
        if line.startswith("diff --git "):
            cur = line.split(" b/", 1)[1]
            out[cur] = []
            continue
        if cur is None or line.startswith("index ") or line.startswith("@@"):
            continue
        out[cur].append(line)
    return out


def main():
    n, base, head = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    ok = True
    mine = per_file(base, head)
    ref = per_file(PROBE[n - 1], PROBE[n])

    if set(mine) != set(ref):
        ok = False
        print("FILES differ:")
        for f in sorted(set(mine) - set(ref)):
            print("  only in task range:", f)
        for f in sorted(set(ref) - set(mine)):
            print("  only in probe range:", f)
    for f in sorted(set(mine) & set(ref)):
        if mine[f] != ref[f]:
            ok = False
            print(f"CONTENT differs: {f}")
            a, b = mine[f], ref[f]
            for i in range(max(len(a), len(b))):
                x = a[i] if i < len(a) else "<none>"
                y = b[i] if i < len(b) else "<none>"
                if x != y:
                    print(f"  first difference at diff line {i}:")
                    print(f"    task : {x[:160]}")
                    print(f"    probe: {y[:160]}")
                    break
    tree_same = git("rev-parse", f"{head}^{{tree}}").strip() == git(
        "rev-parse", f"{PROBE[n]}^{{tree}}"
    ).strip()
    print(f"tree(HEAD) == tree(probe task {n}): {tree_same}")

    shas = git("rev-list", "--reverse", f"{base}..{head}").split()
    print(f"commits in range: {len(shas)}")
    if not shas:
        ok = False
        print("NO COMMITS in range")
    for i, sha in enumerate(shas):
        body = git("log", "-1", "--format=%B", sha)
        subject = body.splitlines()[0] if body else ""
        lines = [ln for ln in body.rstrip().splitlines()]
        if i == 0 and subject != SUBJECT[n]:
            ok = False
            print(f"SUBJECT differs: {subject!r} vs plan {SUBJECT[n]!r}")
        if not lines or lines[-1] != TRAILER:
            ok = False
            print(f"TRAILER wrong in {sha[:8]}: {lines[-1] if lines else ''!r}")
        if re.search(r"Eifel-Joe#|JustChr#", body):
            ok = False
            print(f"OWN/UPSTREAM ISSUE REF in message {sha[:8]}")

    added = [
        ln
        for f, ls in mine.items()
        if f.startswith(("custom_components/", "tests/", "docs/"))
        and not f.startswith("custom_components/irrigation_plus/frontend/dist/")
        for ln in ls
        if ln.startswith("+") and not ln.startswith("+++")
    ]
    hits = [ln for ln in added if OWN_REF.search(ln)]
    if hits:
        ok = False
        print("OWN-REF markers in added lines:")
        for h in hits[:10]:
            print("  ", h[:160])

    print("SPEC CHECK:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
