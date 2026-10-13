"""Mechanical spec check for one task of the PR-2 plan.

The probe run of 2026-10-12 committed Tasks 1-9 verbatim from the plan on the
same base (6a40e083) as one commit per task; that chain is the tested state
(its range diff equals probe-2026-10-12.patch byte for byte). For task N this
script compares the implementer's range BASE..HEAD with the probe's range
P[N-1]..P[N]:

  1. per-file diff of the two ranges must be identical (index/@@ lines are
     normalised away, so earlier reviewed deviations that only shift line
     numbers do not count),
  2. the set of touched files must be identical,
  3. commit messages: subject equals the probe's subject, body ends with the
     Opus 5.5 trailer, no own issue refs (Eifel-Joe#, JustChr#),
  4. the added lines carry no own-reference markers.

Usage: python spec_check.py N BASE HEAD
Exit 0 = PASS, 1 = FAIL (details printed).
"""

import re
import subprocess
import sys

PROBE = {
    0: "6a40e083",
    1: "3426f5f0",
    2: "21cd6cdd",
    3: "55339274",
    4: "6035e583",
    5: "1fc1412b",
    6: "c5f36693",
    7: "146d306e",
    8: "acb8409c",
    9: "dfd5c9a8",
}
TRAILER = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
OWN_REF = re.compile(r"Eifel-Joe|spec D[0-9]|spec §|Task [0-9]|PR [123]\b|PR [A-T]\b")
WT = "D:/Entwicklung/HASI/issue8-pr2-work/wt"


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

    probe_subject = git("log", "-1", "--format=%s", PROBE[n]).strip()
    shas = git("rev-list", "--reverse", f"{base}..{head}").split()
    print(f"commits in range: {len(shas)}")
    if not shas:
        ok = False
        print("NO COMMITS in range")
    for i, sha in enumerate(shas):
        body = git("log", "-1", "--format=%B", sha)
        subject = body.splitlines()[0] if body else ""
        lines = [ln for ln in body.rstrip().splitlines()]
        if i == 0 and subject != probe_subject:
            ok = False
            print(f"SUBJECT differs: {subject!r} vs probe {probe_subject!r}")
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
