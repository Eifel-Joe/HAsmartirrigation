"""For each new ERROR name, find its section in the pytest output and report phase and reason.

Usage: python -I t12_error_reasons.py <suite-output> <new-names-file>
A section starts with a line like "____ ERROR at teardown of TestX.test_y ____" and runs to the
next such header (or the short summary). Prints one line per name, then a count of names whose
section is a teardown that says "Lingering timer".
"""

import re
import sys

out_path, names_path = sys.argv[1], sys.argv[2]
text = open(out_path, encoding="utf-8", errors="replace").read().replace("\r", "\n")
header = re.compile(r"^_+ (ERROR at (setup|teardown) of|[^ ]+) (.+?) _+$", re.M)

sections = {}
heads = list(header.finditer(text))
for i, m in enumerate(heads):
    end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
    if not m.group(1).startswith("ERROR"):
        continue
    sections.setdefault(m.group(3), []).append((m.group(2), text[m.end() : end]))

ok = 0
names = [l.strip()[len("ERROR ") :] for l in open(names_path) if l.startswith("ERROR")]
for node in names:
    # section titles use "Class.test" (or "test" for module-level), not the node id
    parts = node.split("::")[1:]
    title = ".".join(parts)
    found = sections.get(title, [])
    phases = [p for p, _ in found]
    lingering = any("Lingering timer" in body for p, body in found if p == "teardown")
    ok += lingering and phases == ["teardown"]
    print(f"{'OK ' if lingering and phases == ['teardown'] else 'BAD'} {phases} {node}")
print(f"{ok} of {len(names)} new ERRORs are a teardown 'Lingering timer' and nothing else")
