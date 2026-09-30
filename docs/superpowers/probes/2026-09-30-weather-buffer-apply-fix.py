"""Apply one group of a review-fix file's edits to a worktree, from that file's own blocks.

    APPLY_WT=<worktree> python apply_fix.py <fix.md> <group>

A fix file marks each edit with a line ``<!-- edit <group>: <path> -->`` followed by two
fenced ``python`` blocks: the text as it stands (it must occur exactly once), then its
replacement. Files keep their line endings. Nothing is written unless every edit matches.
"""

import os
import pathlib
import re
import sys

WT = pathlib.Path(os.environ["APPLY_WT"])
SRC = pathlib.Path(sys.argv[1])
GROUP = sys.argv[2]

text = SRC.read_text(encoding="utf-8")
pattern = re.compile(
    r"^<!-- edit (\S+): (\S+?)(?: x(\d+))? -->\n```python\n(.*?)^```\n\s*```python\n(.*?)^```\n",
    re.M | re.S,
)
# `<!-- edit G: path x3 -->` replaces all of exactly three occurrences.
edits = [
    (p, int(times or 1), old, new)
    for g, p, times, old, new in pattern.findall(text)
    if g == GROUP
]
if not edits:
    sys.exit(f"no edits for group {GROUP!r}")

files = {}
for rel, times, old, new in edits:
    if rel not in files:
        raw = (WT / rel).read_bytes().decode("utf-8")
        files[rel] = [raw.replace("\r\n", "\n"), "\r\n" in raw]
    body = files[rel][0]
    n = body.count(old)
    if n != times:
        sys.exit(f"APPLY FAILED: {rel}: expected {times}x, found {n}x: {old[:70]!r}")
    files[rel][0] = body.replace(old, new)

for rel, (body, crlf) in files.items():
    (WT / rel).write_bytes((body.replace("\n", "\r\n") if crlf else body).encode("utf-8"))
print(f"applied group {GROUP}: {len(edits)} edits in {len(files)} files")
