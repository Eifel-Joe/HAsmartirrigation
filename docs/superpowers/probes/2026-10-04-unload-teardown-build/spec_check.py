"""Mechanical spec check for the unload-teardown build.

For every commit i on e9c79ec4..HEAD (commit i = the i-th entry of TASKS):
  * each touched source file == base blob + plan operations of commits 1..i
    (byte for byte, at blob level; a CR in a blob is reported on its own);
  * tests/test_self_closing_teardown.py == the test blocks of commits 1..i,
    joined by two blank lines, then any test-file replacements;
  * the commit touches exactly the files of the plan's `git add` line;
  * the commit message == the plan's heredoc (the model name in the
    Co-Authored-By trailer is not compared).

Block numbers are LOCAL to the task's section of the plan; the commit block is
the section's last block starting with "git add".

Usage (from anywhere): python spec_check.py [expected_commit_count]
"""

import difflib
import re
import subprocess
import sys

PLAN = r"D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\plans\2026-10-03-unload-self-closing-teardown.md"
WT = r"D:\Entwicklung\HASI\issue9-work\wt"
BASE = "e9c79ec4"
CC = "custom_components/irrigation_plus/"
TEST = "tests/test_self_closing_teardown.py"

# commit number -> (plan task label, test blocks, source operations)
# an operation is (file, "replace", old_block, new_block)
#              or (file, "insert_before", anchor_line_start, block)
TASKS = {
    1: ("1", [0], [(CC + "self_closing.py", "insert_before",
                    "    async def async_resume_self_closing_runs(self) -> None:", 1)]),
    2: ("2", [0], [(CC + "__init__.py", "replace", 1, 2)]),
    3: ("3", [0], [(CC + "master.py", "replace", 1, 2),
                   (CC + "__init__.py", "replace", 3, 4)]),
    4: ("4", [0], [(CC + "master.py", "insert_before",
                    "    def _master_note_run(self, seconds: float):", 3),
                   (TEST, "replace", 1, 2)]),
    # added during the build: a sweep without the master leaves the flag alone
    5: ("4b", [], [("tests/test_distributor.py", "replace", 0, 1),
                   (CC + "distributor.py", "replace", 2, 3)]),
    6: ("5", [0], [(CC + "run_chain.py", "replace", 1, 2),
                   (CC + "run_chain.py", "insert_before",
                    "    def _chain_teardown(self) -> None:", 3)]),
    7: ("6", [0], [(CC + "self_closing.py", "insert_before",
                    "    async def async_stop_self_closing(", 1),
                   (CC + "self_closing.py", "replace", 2, 3)]),
    8: ("7", [0], [(CC + "self_closing.py", "insert_before",
                    "    def async_teardown_self_closing_handles(self) -> None:", 1)]),
    9: ("8", [0], [(TEST, "replace", 1, 2),
                   (CC + "__init__.py", "replace", 3, 4),
                   (CC + "__init__.py", "replace", 5, 6)]),
    10: ("9", [], [("docs/configuration-my-zones.md", "replace", 0, 1)]),
    # added during the build: two docstrings (a batch resume arms no backstop)
    11: ("9a", [], [(CC + "self_closing.py", "replace", 0, 1),
                    (TEST, "replace", 2, 3),
                    (CC + "run_chain.py", "replace", 4, 5),
                    ("tests/test_chain_carries_its_plan.py", "replace", 6, 7),
                    ("docs/configuration-my-zones.md", "replace", 8, 9),
                    (CC + "__init__.py", "replace", 10, 11)]),
    # added after the final review: two pins for the abort
    12: ("9b", [], [(TEST, "replace", 0, 1),
                    (TEST, "replace", 2, 3)]),
}


def git(*args):
    return subprocess.run(
        ["git", "-C", WT, *args],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout


def blob(sha, path):
    raw = subprocess.run(
        ["git", "-C", WT, "show", f"{sha}:{path}"],
        capture_output=True, check=False,
    )
    if raw.returncode != 0:
        return None
    return raw.stdout.decode("utf-8")


plan = open(PLAN, encoding="utf-8").read().replace("\r\n", "\n")


def section_blocks(label):
    m = re.search(rf"^### Task {label}:.*?(?=^---$)", plan, re.S | re.M)
    return [b.group(2) for b in re.finditer(r"```(\w+)\n(.*?)```", m.group(0), re.S)]


SECTIONS = {spec[0]: section_blocks(spec[0]) for spec in TASKS.values()}


def commit_block(label):
    adds = [b for b in SECTIONS[label] if b.startswith("git add ")]
    return adds[-1]


def apply_op(text, label, op):
    blocks = SECTIONS[label]
    path, kind, a, b = op
    if kind == "replace":
        old, new = blocks[a], blocks[b]
        n = text.count(old)
        if n != 1:
            raise ValueError(f"{path}: replace-anchor (task {label} block {a}) found {n}x")
        return text.replace(old, new)
    anchor, new = a, blocks[b]
    starts = [m.start() for m in re.finditer("^" + re.escape(anchor), text, re.M)]
    if len(starts) != 1:
        raise ValueError(f"{path}: insert-anchor {anchor!r} found {len(starts)}x")
    i = starts[0]
    return text[:i] + new + text[i:]


def commit_message(label):
    m = re.search(r"<<'EOF'\n(.*?)\nEOF", commit_block(label), re.S)
    return m.group(1)


def files_of_add(label):
    line = commit_block(label).splitlines()[0]
    return sorted(line[len("git add "):].split())


def norm_trailer(msg):
    return re.sub(r"Co-Authored-By: Claude [^<]*<", "Co-Authored-By: Claude <", msg.strip())


def show_diff(want, got):
    for line in list(difflib.unified_diff(
            want.splitlines(), got.replace("\r\n", "\n").splitlines(),
            "expected", "commit", lineterm=""))[:60]:
        print("    " + line)


def expected_test_file(upto):
    """The test file the plan dictates after commit ``upto``."""
    tests, test_ops = [], []
    for i in range(1, upto + 1):
        label, test_idx, ops = TASKS[i]
        tests += [SECTIONS[label][t] for t in test_idx]
        test_ops += [(label, op) for op in ops if op[0] == TEST]
    text = "\n\n\n".join(t.rstrip("\n") for t in tests) + "\n"
    for lab, op in test_ops:
        text = apply_op(text, lab, op)
    return text


def main():
    expected = int(sys.argv[1]) if len(sys.argv) > 1 else None
    shas = git("rev-list", "--reverse", f"{BASE}..HEAD").split()
    bad = 0
    if expected is not None and len(shas) != expected:
        print(f"BAD commit count {len(shas)} != {expected}")
        bad += 1
    state = {}  # path -> expected text (LF)
    for i, sha in enumerate(shas, start=1):
        if i not in TASKS:
            print(f"BAD commit {i} {sha[:8]}: no entry {i} in TASKS")
            bad += 1
            continue
        label, test_idx, ops = TASKS[i]
        for op in ops:
            if op[0] == TEST:
                continue
            path = op[0]
            if path not in state:
                state[path] = blob(BASE, path)
            try:
                state[path] = apply_op(state[path], label, op)
            except ValueError as exc:
                print(f"BAD commit {i}: {exc}")
                bad += 1
        # 1) sources
        for path, want in state.items():
            got = blob(sha, path)
            if got is None:
                print(f"BAD commit {i} {sha[:8]}: {path} missing")
                bad += 1
                continue
            if "\r" in got:
                print(f"BAD commit {i} {sha[:8]}: {path} blob contains CR")
                bad += 1
            ok = got.replace("\r\n", "\n") == want
            print(f"{'OK ' if ok else 'BAD'} commit {i} {sha[:8]} {path}")
            if not ok:
                bad += 1
                show_diff(want, got)
        # 2) the test file
        try:
            want_t = expected_test_file(i)
        except ValueError as exc:
            print(f"BAD commit {i}: {exc}")
            bad += 1
            want_t = None
        if want_t is not None:
            got_t = blob(sha, TEST)
            ok = got_t is not None and "\r" not in got_t and got_t == want_t
            print(f"{'OK ' if ok else 'BAD'} commit {i} {sha[:8]} {TEST}")
            if not ok:
                bad += 1
                if got_t is not None:
                    show_diff(want_t, got_t)
        # 3) files touched
        touched = sorted(git("diff-tree", "--no-commit-id", "--name-only", "-r", sha).split())
        want_files = files_of_add(label)
        ok = touched == want_files
        print(f"{'OK ' if ok else 'BAD'} commit {i} {sha[:8]} files {touched}")
        bad += not ok
        # 4) message
        got_msg = git("log", "-1", "--format=%B", sha)
        ok = norm_trailer(got_msg) == norm_trailer(commit_message(label))
        print(f"{'OK ' if ok else 'BAD'} commit {i} {sha[:8]} message")
        if not ok:
            bad += 1
            print("    got:\n" + got_msg)
    print("SPEC CHECK:", "PASS" if not bad else f"FAIL ({bad})")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
