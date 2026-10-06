"""Check every code block of the plan against the tested probe state.

* python blocks that are test code must appear verbatim in the probe test file;
* a block introduced by "ersetze" must appear verbatim in the BASE source
  (e9c79ec4) and must be gone from the probe source;
* every other python/markdown block must appear verbatim in the probe source
  (the "durch" and "einfügen" blocks).
Run from D:/Entwicklung/HASI/issue9-work.
"""

import re
import subprocess
import sys

PLAN = r"D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\plans\2026-10-03-unload-self-closing-teardown.md"
PROBE = r"D:\Entwicklung\HASI\issue9-work\probe"
FILES = [
    "custom_components/irrigation_plus/__init__.py",
    "custom_components/irrigation_plus/master.py",
    "custom_components/irrigation_plus/run_chain.py",
    "custom_components/irrigation_plus/self_closing.py",
    "docs/configuration-my-zones.md",
]


def norm(text):
    return text.replace("\r\n", "\n")


def read_probe(rel):
    with open(f"{PROBE}/{rel}", encoding="utf-8") as fh:
        return norm(fh.read())


def read_base(rel):
    out = subprocess.run(
        ["git", "-C", PROBE, "show", f"e9c79ec4:{rel}"],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    return norm(out)


plan = norm(open(PLAN, encoding="utf-8").read())
test_file = read_probe("tests/test_self_closing_teardown.py")
probe_src = {f: read_probe(f) for f in FILES}
base_src = {f: read_base(f) for f in FILES}

blocks = list(re.finditer(r"```(python|markdown)\n(.*?)```", plan, re.S))
bad = 0
for m in blocks:
    lang, body = m.group(1), m.group(2)
    lead = plan[max(0, m.start() - 200):m.start()]
    is_replace_old = bool(re.search(r"ersetze(?: in [^\n]*)?\s*$", lead.strip().splitlines()[-1] if lead.strip() else ""))
    if lang == "python" and (body.startswith("# ----") or body.startswith('"""What an unload')):
        ok = body.rstrip("\n") in test_file
        kind = "test"
    elif is_replace_old:
        ok = any(body.rstrip("\n") in s for s in base_src.values()) and not any(
            body.rstrip("\n") in s for s in probe_src.values()
        )
        kind = "old"
    else:
        ok = any(body.rstrip("\n") in s for s in probe_src.values())
        kind = "new"
    first = body.splitlines()[0][:70] if body else ""
    print(f"{'OK ' if ok else 'BAD'} {kind:4s} {first}")
    bad += not ok

# the test file must be exactly the concatenation of the test blocks
tests = [m.group(2) for m in blocks if m.group(1) == "python" and (m.group(2).startswith("# ----") or m.group(2).startswith('"""What an unload'))]
joined = "\n\n\n".join(t.rstrip("\n") for t in tests) + "\n"
print("test file == concatenated test blocks:", joined == test_file)
if joined != test_file:
    import difflib
    for line in list(difflib.unified_diff(test_file.splitlines(), joined.splitlines(), lineterm=""))[:40]:
        print(line)
sys.exit(1 if bad or joined != test_file else 0)
