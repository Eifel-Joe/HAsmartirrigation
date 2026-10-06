"""Fold the device-registry branch from ten commits (plus the 6b text polish) into five.

Folded commit i has the tree of the last original commit of its group (task N
plus its review follow-up Nb) with the 6b blocks applied by the plan tool, and
the message fold/msg<i>.txt. Built with plumbing (no interactive rebase); the
branch moves only if every check passes, and a local backup branch keeps the
unfolded history.

Usage: python fold.py            (dry run: compute and check, change nothing)
       python fold.py --apply    (also create the commits and move the branch)
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WT = r"D:\Entwicklung\HASI\issue11-work\wt"
APPLY = r"D:\Entwicklung\HASI\issue11-work\apply_plan_task.py"
FOLD = Path(r"D:\Entwicklung\HASI\issue11-work\fold")
BASE = "7001c754"
BRANCH = "fix/device-registry-2027-8"
BACKUP = "backup/device-registry-unfolded"
EXPECTED = ["19975bca", "347c7477", "e83cb848", "4f3536e4", "d982b0fd", "f34afa6b",
            "3db00e2d", "a4978d13", "e8cbd7bb", "08e5c576", "16b443e4"]
GROUPS = [("347c7477", "msg1.txt"), ("4f3536e4", "msg2.txt"), ("f34afa6b", "msg3.txt"),
          ("a4978d13", "msg4.txt"), ("08e5c576", "msg5.txt")]
FILES_6B = ["custom_components/irrigation_plus/entity.py", "tests/test_device_registry_compat.py"]


def git(*args, env=None, raw=False):
    r = subprocess.run(["git", "-C", WT, *args], capture_output=True, env=env)
    if r.returncode != 0:
        raise SystemExit(f"STOP: git {' '.join(args)} failed:\n{r.stderr.decode()}")
    return r.stdout if raw else r.stdout.decode("utf-8").strip()


def tree_with_6b(orig, tmp):
    """The tree of ``orig`` with the 6b blocks applied to its two files."""
    work = tmp / f"files-{orig}"
    for rel in FILES_6B:
        dst = work / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(git("show", f"{orig}:{rel}", raw=True))
    for which in ("tests", "code"):
        r = subprocess.run([sys.executable, APPLY, str(work), "6b", which], capture_output=True)
        if r.returncode != 0:
            raise SystemExit(f"STOP: 6b {which} on {orig}:\n{r.stdout.decode()}{r.stderr.decode()}")
    env = dict(os.environ, GIT_INDEX_FILE=str(tmp / f"index-{orig}"))
    git("read-tree", orig, env=env)
    for rel in FILES_6B:
        data = (work / rel).read_bytes()
        if b"\r" in data:
            raise SystemExit(f"STOP: CR in {rel} for {orig}")
        mode = git("ls-tree", orig, rel).split()[0]
        blob = git("hash-object", "-w", "--no-filters", str(work / rel))
        git("update-index", "--cacheinfo", f"{mode},{blob},{rel}", env=env)
    return git("write-tree", env=env)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    apply = "--apply" in sys.argv
    head = git("rev-parse", "HEAD")
    if git("rev-parse", "--abbrev-ref", "HEAD") != BRANCH:
        raise SystemExit("STOP: worktree is not on the branch")
    if git("status", "--porcelain"):
        raise SystemExit("STOP: worktree not clean")
    seq = git("rev-list", "--reverse", f"{BASE}..HEAD").split()
    if len(seq) != len(EXPECTED) or not all(s.startswith(e) for s, e in zip(seq, EXPECTED)):
        raise SystemExit(f"STOP: unexpected history:\n{seq}")
    for _orig, msg in GROUPS:
        if b"\r" in (FOLD / msg).read_bytes():
            raise SystemExit(f"STOP: CR in {msg}")

    tmp = Path(tempfile.mkdtemp(prefix="fold-", dir=r"D:\Entwicklung\HASI\issue11-work"))
    try:
        trees = [tree_with_6b(orig, tmp) for orig, _msg in GROUPS]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    head_tree = git("rev-parse", "HEAD^{tree}")
    print("last folded tree == head tree:", trees[-1] == head_tree)
    if trees[-1] != head_tree:
        raise SystemExit("STOP: the last folded tree differs from the head tree")
    for (orig, msg), tree in zip(GROUPS, trees):
        stat = git("diff", "--shortstat", orig, tree)
        print(f"{orig} + 6b -> tree {tree[:8]}  ({msg}; vs {orig}: {stat or 'identical'})")
    if not apply:
        print("dry run: nothing changed")
        return

    parent = git("rev-parse", BASE)
    new = []
    for (_orig, msg), tree in zip(GROUPS, trees):
        parent = git("commit-tree", tree, "-p", parent, "-F", str(FOLD / msg))
        new.append(parent)
    if git("branch", "--list", BACKUP):
        raise SystemExit(f"STOP: {BACKUP} exists already")
    git("branch", BACKUP, head)
    git("update-ref", f"refs/heads/{BRANCH}", new[-1], head)
    print("backup:", BACKUP, "->", head[:8])
    for c in new:
        print("new commit", c[:8], git("log", "-1", "--format=%s", c))
    print("status after:", repr(git("status", "--porcelain")))


if __name__ == "__main__":
    main()
