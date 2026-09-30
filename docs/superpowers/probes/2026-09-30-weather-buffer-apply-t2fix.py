"""Apply the Task 2 review fixes (prompts/adj-t2fix.md) to a worktree, from that file's blocks.

    APPLY_WT=<worktree> python apply_t2fix.py A|B

A: the imports, the child-process test, the siehe on _process_timezone. B: local_naive_now's
docstring. Every anchor must match exactly once; files keep their line endings.
"""

import os
import pathlib
import re
import sys

WT = pathlib.Path(os.environ["APPLY_WT"])
SRC = pathlib.Path("D:/Entwicklung/HASI/issue22-work/prompts/adj-t2fix.md")
H = "custom_components/irrigation_plus/helpers.py"
T = "tests/test_time_provenance.py"

blocks = re.findall(r"^```python\n(.*?)^```\n", SRC.read_text(encoding="utf-8"), re.M | re.S)
assert len(blocks) == 7, len(blocks)
imp_old, imp_new, test_block, a5_old, a5_new, b1_old, b1_new = blocks


def edit(rel, old, new):
    path = WT / rel
    raw = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    n = text.count(old)
    if n != 1:
        sys.exit(f"APPLY FAILED: {rel}: expected 1x, found {n}x: {old[:60]!r}")
    text = text.replace(old, new)
    path.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


if sys.argv[1] == "A":
    edit(T, imp_old, imp_new)
    anchor = "def test_coercing_without_naming_a_provenance_is_an_error():\n"
    edit(T, anchor, test_block + "\n\n" + anchor)
    edit(H, a5_old, a5_new)
elif sys.argv[1] == "B":
    edit(H, b1_old, b1_new)
print("applied", sys.argv[1])
