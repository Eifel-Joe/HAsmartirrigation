"""Classify the ERROR/FAILED names that are new against the baseline.

Usage: python classify_new_errors.py <baseline-names> <run-names> <run-output>
A new name is acceptable only if it is an ERROR whose section in the run output
is "ERROR at teardown of <Class.test>" and contains "Lingering timer".
Prints one line per new name; last line 'UNEXPECTED: <n>'.
"""

import re
import sys

base = set(open(sys.argv[1], encoding="utf-8").read().split("\n")) - {""}
run = set(open(sys.argv[2], encoding="utf-8").read().split("\n")) - {""}
text = open(sys.argv[3], "rb").read().decode("utf-8", "replace").replace("\r", "\n")

sections = {}
header = re.compile(r"^_{1,} (ERROR at (setup|teardown) of )?(\S+) _{1,}$")
cur = None
for line in text.split("\n"):
    m = header.match(line)
    if m:
        cur = (m.group(2) or "call", m.group(3))
        sections.setdefault(cur, [])
        continue
    if line.startswith("=") and "short test summary" in line:
        cur = None
    if cur:
        sections[cur].append(line)

unexpected = 0
for name in sorted(run - base):
    kind, nodeid = name.split(" ", 1)
    parts = nodeid.split("::")
    key = ".".join(parts[1:])
    ok = False
    if kind == "ERROR":
        body = sections.get(("teardown", key))
        ok = body is not None and any("Lingering timer" in ln for ln in body)
    print(("ok   " if ok else "BAD  ") + name)
    unexpected += not ok
print(f"UNEXPECTED: {unexpected}")
