"""Mechanical spec check of one task: the implementer's result against the plan's reference.

    python spec_check.py <task> [<ref-sha>]

The reference worktree (ref-wt) holds one commit per task, built by apply_task.py from the
plan's own code blocks. Both worktrees share one object store, so the implementer's HEAD and
the reference commit compare directly. Checks, each printed with PASS/FAIL:

- tree:      `git diff <ref> HEAD` in wt is empty (skipped for task 1, which commits nothing)
- task-1 file (tasks 1-4, where it is untracked): wt's copy equals ref-wt's, CR ignored
- message:   HEAD's message equals the plan's heredoc for this task; a differing
             Co-Authored-By trailer is reported, not failed
- tracker:   no fork-tracker token in the task's added lines or in the message
- status:    `git status --short` is what the task leaves
"""

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path("D:/Entwicklung/HASI/issue22-work")
WT = pathlib.Path(__import__("os").environ.get("SPEC_WT", str(ROOT / "wt")))
REF = ROOT / "ref-wt"
PLAN = pathlib.Path(
    "D:/Entwicklung/HASI/pr139-work/archive-wt/docs/superpowers/plans/"
    "2026-09-30-weather-buffer-one-frame.md"
)
T1 = "tests/test_weather_buffer_one_frame.py"
REF_T1_COMMIT = "8ee1e437"
TRACKER = re.compile(
    r"Eifel|#22\b|Rev(ision)? ?[34]|R4-|\bA[1-8]\b|\bspec\b|Task [0-9]|\b[BFM]-?[0-9]{1,2}\b"
)
RESULTS = []


def git(*args, cwd=WT):
    out = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8"
    )
    return out.stdout


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"\n{detail}" if detail else ""))


def plan_message(task):
    text = PLAN.read_text(encoding="utf-8")
    m = re.search(rf"^## Task {task}:.*?(?=^## Task {task + 1}:|\Z)", text, re.M | re.S)
    section = m.group(0)
    m2 = re.search(r"git commit -q -F - <<'EOF'\n(.*?)\nEOF\n", section, re.S)
    return m2.group(1) if m2 else None


def split_trailer(msg):
    lines = msg.rstrip("\n").split("\n")
    trailer = [ln for ln in lines if ln.startswith("Co-Authored-By:")]
    body = "\n".join(ln for ln in lines if not ln.startswith("Co-Authored-By:")).rstrip()
    return body, trailer


def main():
    task = int(sys.argv[1])
    ref = sys.argv[2] if len(sys.argv) > 2 else None

    if task >= 2:
        diff = git("diff", "--stat", ref, "HEAD")
        check(f"tree: HEAD == reference {ref}", diff.strip() == "", diff)

    if task <= 4:
        mine = (WT / T1).read_bytes().replace(b"\r\n", b"\n") if (WT / T1).exists() else None
        # The reference commits it with task 5 (d266700d); read it from the object store.
        theirs = subprocess.run(
            ["git", "show", f"{REF_T1_COMMIT}:{T1}"], cwd=REF, capture_output=True
        ).stdout.replace(b"\r\n", b"\n")
        check("task-1 file equals the reference (CR ignored)", mine == theirs,
              "" if mine == theirs else "differs or missing")

    if task >= 2:
        want = plan_message(task)
        got = git("log", "-1", "--format=%B")
        wb, wt_ = split_trailer(want)
        gb, gt_ = split_trailer(got)
        check("message body equals the plan's", wb == gb,
              "" if wb == gb else f"--- plan\n{wb}\n--- HEAD\n{gb}")
        if wt_ != gt_:
            print(f"[NOTE] trailer differs: plan {wt_} / HEAD {gt_}")
        added = [
            ln for ln in git("diff", "HEAD~1", "HEAD").splitlines()
            if ln.startswith("+") and not ln.startswith("+++")
        ]
        hits = [ln for ln in added if TRACKER.search(ln)] + [
            ln for ln in got.splitlines() if TRACKER.search(ln)
        ]
        check("tracker: no fork token in added lines or message", not hits, "\n".join(hits))

    status = git("status", "--short").strip()
    expected = f"?? {T1}" if task <= 4 else ""
    check(f"status: {expected or '(clean)'}", status == expected, status)

    print("SPEC CHECK:", "PASS" if all(RESULTS) else "FAIL")


main()
