"""List or extract the fenced code blocks of the plan, by task and index.

    python plan_blocks.py list
    python plan_blocks.py get <task> <index> <out-file>

<task> is the number in "## Task N:"; <index> counts that task's blocks from 0, as
`list` prints them. The block text is written verbatim (LF), without the fences.
"""
import pathlib
import re
import sys

PLAN = pathlib.Path(
    "D:/Entwicklung/HASI/pr139-work/archive-wt/docs/superpowers/plans/"
    "2026-09-30-weather-buffer-one-frame.md"
)


def blocks():
    text = PLAN.read_text(encoding="utf-8")
    task = None
    out = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^## Task (\d+):", line)
        if m:
            task = int(m.group(1))
        fence = re.match(r"^(\s*)```(\w*)\s*$", line)
        if fence and task is not None:
            indent, lang = fence.group(1), fence.group(2)
            body = []
            i += 1
            while i < len(lines) and not re.match(r"^\s*```\s*$", lines[i]):
                body.append(lines[i][len(indent):] if lines[i].startswith(indent) else lines[i])
                i += 1
            out.append((task, lang, "\n".join(body) + "\n"))
        i += 1
    return out


def main():
    bl = blocks()
    if sys.argv[1] == "list":
        counters = {}
        for task, lang, body in bl:
            n = counters.get(task, 0)
            counters[task] = n + 1
            first = body.strip().splitlines()[0][:70] if body.strip() else ""
            print(f"Task {task:2d} #{n:2d} [{lang:8}] {len(body.splitlines()):4d} lines | {first}")
    elif sys.argv[1] == "get":
        task, index, out = int(sys.argv[2]), int(sys.argv[3]), pathlib.Path(sys.argv[4])
        mine = [b for b in bl if b[0] == task]
        out.write_text(mine[index][2], encoding="utf-8", newline="\n")
        print(f"wrote {out} ({len(mine[index][2].splitlines())} lines)")


main()
