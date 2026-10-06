"""Apply the verbatim blocks of one plan task to an issue11 worktree.

The plan dictates every edit as "Lege `F` an:" <block>, "Ersetze in `F`:" <old>
"durch:" <new>, or "Hänge an `F` an:" <block>. This applies the test edits or
the code edits of one task, exactly as written, and refuses if an anchor is not
found exactly once or a file to create already exists (either means the base is
not what the plan was written against: STOP).

Usage:
  python apply_plan_task.py <worktree> <task> tests   # edits of files under tests/
  python apply_plan_task.py <worktree> <task> code    # every other edit of the task
"""

import re
import sys
from pathlib import Path

PLAN = Path(
    r"D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\plans"
    r"\2026-10-06-device-registry-2027-8.md"
)

TASK_RE = re.compile(r"^### Task (\d+):")
CREATE_RE = re.compile(r"^\*\*Lege `([^`]+)` an:\*\*\s*$")
REPLACE_RE = re.compile(r"^\*\*Ersetze in `([^`]+)`:\*\*\s*$")
WITH_RE = re.compile(r"^\*\*durch:\*\*\s*$")
APPEND_RE = re.compile(r"^\*\*Hänge an `([^`]+)` an:\*\*\s*$")
FENCE_RE = re.compile(r"^```")


def read_block(lines, i):
    """Return (content, next index) of the fenced block starting at or after i."""
    while not FENCE_RE.match(lines[i]):
        if lines[i].strip():
            raise SystemExit(f"expected a fence at plan line {i + 1}, got {lines[i]!r}")
        i += 1
    i += 1
    body = []
    while not FENCE_RE.match(lines[i]):
        body.append(lines[i])
        i += 1
    return "\n".join(body) + "\n", i + 1


def parse(plan_text):
    lines = plan_text.replace("\r\n", "\n").split("\n")
    tasks = {}
    task = None
    i = 0
    while i < len(lines):
        m = TASK_RE.match(lines[i])
        if m:
            task = int(m.group(1))
            tasks.setdefault(task, [])
            i += 1
            continue
        m = CREATE_RE.match(lines[i])
        if m:
            body, i = read_block(lines, i + 1)
            tasks[task].append(("create", m.group(1), body, None))
            continue
        m = REPLACE_RE.match(lines[i])
        if m:
            old, i = read_block(lines, i + 1)
            while not WITH_RE.match(lines[i]):
                if lines[i].strip():
                    raise SystemExit(f"expected **durch:** at plan line {i + 1}")
                i += 1
            new, i = read_block(lines, i + 1)
            tasks[task].append(("replace", m.group(1), old, new))
            continue
        m = APPEND_RE.match(lines[i])
        if m:
            body, i = read_block(lines, i + 1)
            tasks[task].append(("append", m.group(1), body, None))
            continue
        i += 1
    return tasks


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    wt = Path(sys.argv[1])
    task = int(sys.argv[2])
    which = sys.argv[3]
    if which not in ("tests", "code"):
        raise SystemExit("third argument: tests | code")
    edits = parse(PLAN.read_text(encoding="utf-8")).get(task, [])
    chosen = [e for e in edits if e[1].startswith("tests/") == (which == "tests")]
    if not chosen:
        print(f"Task {task}: no {which} edits in the plan")
        return

    # Check every anchor first, so a mismatch leaves the tree untouched.
    for kind, rel, old, _new in chosen:
        path = wt / rel
        if kind == "create" and path.exists():
            raise SystemExit(f"STOP: {rel} already exists")
        if kind == "replace":
            text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
            count = text.count(old)
            if count != 1:
                raise SystemExit(f"STOP: anchor in {rel} found {count}x (expected 1):\n{old}")

    for kind, rel, a, b in chosen:
        path = wt / rel
        if kind == "create":
            path.write_bytes(a.encode("utf-8"))
            print(f"Task {task} {which}: {rel}: created {a.count(chr(10))} lines")
            continue
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
