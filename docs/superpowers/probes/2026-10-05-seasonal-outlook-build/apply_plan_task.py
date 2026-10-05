"""Apply the verbatim blocks of one plan task to the issue10 worktree.

The plan dictates every edit as "Ersetze in `F`: <old> durch: <new>" or
"Hänge an `F` an: <block>". This applies the test edits or the code edits of
one task, exactly as written, and refuses if an anchor is not found exactly
once (that means the base is not what the plan was written against: STOP).

Usage:
  python apply_plan_task.py <task> tests       # edits of files under tests/
  python apply_plan_task.py <task> code        # every other edit of the task
  python apply_plan_task.py <task> deviations  # the task's blocks in deviations.md (review fixes)
"""

import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from probe_plan import parse  # noqa: E402

PLAN = Path(r"D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\plans\2026-10-05-seasonal-outlook.md")
DEVIATIONS = HERE / "deviations.md"
WT = HERE / "wt"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    task = int(sys.argv[1])
    which = sys.argv[2]
    if which not in ("tests", "code", "deviations"):
        raise SystemExit("second argument: tests | code | deviations")
    if which == "deviations":
        chosen = parse(DEVIATIONS.read_text(encoding="utf-8")).get(task, [])
        # "--from K": only the task's deviation blocks K.. (1-based), for a later
        # review round whose earlier blocks are already committed.
        if len(sys.argv) > 4 and sys.argv[3] == "--from":
            chosen = chosen[int(sys.argv[4]) - 1 :]
    else:
        edits = parse(PLAN.read_text(encoding="utf-8")).get(task, [])
        chosen = [e for e in edits if e[1].startswith("tests/") == (which == "tests")]
    if not chosen:
        print(f"Task {task}: no {which} edits in the plan")
        return

    # Check every anchor first, so a mismatch leaves the tree untouched.
    for kind, rel, old, _new in chosen:
        if kind == "replace":
            text = (WT / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")
            count = text.count(old)
            if count != 1:
                raise SystemExit(f"STOP: anchor in {rel} found {count}x (expected 1):\n{old}")

    for kind, rel, a, b in chosen:
        path = WT / rel
        raw = path.read_bytes().decode("utf-8")
        crlf = "\r\n" in raw
        text = raw.replace("\r\n", "\n")
        if kind == "replace":
            text = text.replace(a, b)
        else:
            if not text.endswith("\n"):
                text += "\n"
            text += a
        if crlf:
            text = text.replace("\n", "\r\n")
        path.write_bytes(text.encode("utf-8"))
        label = "replaced (anchor 1x)" if kind == "replace" else f"appended {a.count(chr(10))} lines"
        print(f"Task {task} {which}: {rel}: {label}")


if __name__ == "__main__":
    main()
