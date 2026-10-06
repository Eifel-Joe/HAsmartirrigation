"""Mechanical spec check of one implemented plan task in issue11-work/wt.

The plan dictates every block verbatim and was probe-run task by task
(probe commits below). Task 1b (review follow-up of task 1) was probed on top
of task 5 (51e2a6da); its own change is delta-1b.patch. A task is
spec-compliant when:
  1. the worktree HEAD is the expected number of commits on top of the base,
  2. the tree equals the probe commit of the same task -- from 1b on, with
     the 1b blocks applied to it by the same tool, byte for byte; after task 5
     the tree equals the probe end state 51e2a6da outright,
  3. the commit touches exactly the files of the plan's `git add` line,
  4. the commit message equals the plan's heredoc message byte for byte,
  5. message and added lines carry no own reference (Eifel-Joe, JustChr#, ...),
  6. the worktree is clean (ignored files aside).

Usage: python spec_check.py <task>      (task: 1, 1b, 2, 3, 4, 5)
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WT = r"D:\Entwicklung\HASI\issue11-work\wt"
APPLY = r"D:\Entwicklung\HASI\issue11-work\apply_plan_task.py"
FILES_1B = ["custom_components/irrigation_plus/entity.py", "custom_components/irrigation_plus/__init__.py",
            "custom_components/irrigation_plus/distributor.py", "tests/test_device_registry_compat.py"]
BASE = "7001c754"
ORDER = ["1", "1b", "2", "2b", "3", "3b", "4", "4b", "5", "5b", "6b"]
# Review follow-ups, applied by the tool on top of the probe commit of a task.
EXTRAS = ["1b", "2b", "3b", "4b", "5b", "6b"]
PROBE = {"1": "a34becea", "1b": "a34becea", "2": "5a90d023", "2b": "5a90d023",
         "3": "403fc2b2", "3b": "403fc2b2", "4": "2bd0f689", "4b": "2bd0f689", "5": "290892af", "5b": "290892af", "6b": "290892af"}
PROBE_END = "84f9c5c9"
PROMPTS = Path(r"D:\Entwicklung\HASI\issue11-work\prompts")
OWN_REF = re.compile(r"Eifel-Joe|JustChr#|spec D[0-9]|spec §|Task [0-9]|M[0-9][a-z]?:|PR [A-T]\b")


def git_bytes(*args):
    out = subprocess.run(["git", "-C", WT, *args], capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {out.stderr.decode()}")
    return out.stdout


def git(*args):
    return git_bytes(*args).decode("utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    n = sys.argv[1]
    plan = (PROMPTS / f"t{n}-plan.md").read_bytes().decode("utf-8").replace("\r\n", "\n")
    ok = True

    def check(cond, label, detail=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + label + (f"\n{detail}" if detail and not cond else ""))
        ok = ok and cond

    head = git("rev-parse", "HEAD").strip()
    parent = git("rev-parse", "HEAD~1").strip()
    want_count = ORDER.index(n) + 1
    count = int(git("rev-list", "--count", f"{BASE}..HEAD").strip())
    check(count == want_count, f"1 commits on top of {BASE}: {count} (expected {want_count})")

    if n == "1":
        diff = git("diff", "--name-only", PROBE[n], "HEAD")
        check(diff.strip() == "", f"2 tree == probe commit {PROBE[n]}", diff)
    else:
        # Exact: the probe commit's two 1b files with the 1b blocks applied by
        # the same tool must equal HEAD byte for byte (LF), and nothing else may
        # differ from the probe commit. (A line-order comparison of diffs fails
        # here for nothing: git places the inserted blank line differently at the
        # end of a file than in its middle.)
        others = set(git("diff", "--name-only", PROBE[n], "HEAD").split()) - set(FILES_1B)
        check(not others, f"2a nothing but the 1b files differs from probe commit {PROBE[n]}", str(others))
        tmp = Path(tempfile.mkdtemp(prefix="speccheck-", dir=r"D:\Entwicklung\HASI\issue11-work"))
        try:
            for rel in FILES_1B:
                dst = tmp / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(git_bytes("show", f"{PROBE[n]}:{rel}"))
            extras = [x for x in EXTRAS if ORDER.index(x) <= ORDER.index(n)]
            for extra in extras:
                for which in ("tests", "code"):
                    run = subprocess.run([sys.executable, APPLY, str(tmp), extra, which], capture_output=True)
                    check(run.returncode == 0, f"2b {extra} {which} blocks apply on probe commit {PROBE[n]}",
                          run.stdout.decode() + run.stderr.decode())
            for rel in FILES_1B:
                want = (tmp / rel).read_bytes().replace(b"\r\n", b"\n")
                got = git_bytes("show", f"HEAD:{rel}").replace(b"\r\n", b"\n")
                check(got == want, f"2c {rel} == probe commit {PROBE[n]} + {'+'.join(extras)} blocks")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    if n == ORDER[-1]:
        diff = git("diff", "--name-only", PROBE_END, "HEAD")
        check(diff.strip() == "", f"2b tree == probe end state {PROBE_END}", diff)

    m = re.search(r"^git add (.+)$", plan, re.M)
    want_files = sorted(m.group(1).split())
    got_files = sorted(git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").split())
    check(got_files == want_files, f"3 files of the commit == plan's git add {want_files}", str(got_files))

    m = re.search(r"git commit -F - <<'EOF'\n(.*?)\nEOF\n", plan, re.S)
    want_msg = m.group(1) + "\n"
    got_msg = git("log", "-1", "--format=%B", "HEAD").rstrip("\n") + "\n"
    check(got_msg == want_msg, "4 commit message == plan's message",
          f"--- want\n{want_msg}--- got\n{got_msg}")

    added = [l for l in git("diff", "HEAD~1", "HEAD").split("\n") if l.startswith("+")]
    hits = [l for l in added + got_msg.split("\n") if OWN_REF.search(l)]
    check(not hits, "5 no own references in added lines or message", "\n".join(hits))

    status = git("status", "--porcelain")
    check(status.strip() == "", "6 worktree clean", status)

    print("SPEC CHECK", "OK" if ok else "FAILED", f"(task {n}, HEAD {head[:8]}, parent {parent[:8]})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
