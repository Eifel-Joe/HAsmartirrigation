"""Check every code block of the plan (revision 2) against the tested probe state.

A python / json / markdown / unlabelled block passes when it appears verbatim in a
probe file (code, tests, translations, docs). A block that is the OLD text of a
replacement passes when it appears in the clean base (e9c79ec4) and no longer in
the probe. Anything else is reported. bash / yaml / js blocks are commands or live-
test material, not tree content, and are skipped.

Run from anywhere: python check_plan_blocks.py
"""

import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
PLAN = pathlib.Path(
    r"D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\plans"
    r"\2026-10-03-dead-weather-sensor-common.md"
)
PROBE = pathlib.Path(r"D:\Entwicklung\HASI\issue8-work\probe-wt")
BASE = pathlib.Path(r"D:\Entwicklung\HASI\issue8-work\base-wt")
GLOBS = [
    "custom_components/irrigation_plus/*.py",
    "custom_components/irrigation_plus/translations/*.json",
    "tests/test_sensor_liveness*.py",
    "docs/*.md",
]


def norm(text):
    return text.replace("\r\n", "\n")


def corpus(root):
    out = {}
    for pattern in GLOBS:
        for path in root.glob(pattern):
            out[str(path.relative_to(root))] = norm(path.read_text(encoding="utf-8"))
    return out


probe = corpus(PROBE)
base = corpus(BASE)
plan = norm(PLAN.read_text(encoding="utf-8"))

checked = bad = 0
for match in re.finditer(r"```([a-z]*)\n(.*?)```", plan, re.S):
    lang, body = match.group(1), match.group(2)
    if lang in ("bash", "yaml", "js"):
        continue
    body = body.strip("\n")
    if not body.strip():
        continue
    checked += 1
    in_probe = [name for name, text in probe.items() if body in text]
    if in_probe:
        continue
    in_base = [name for name, text in base.items() if body in text]
    line = plan.count("\n", 0, match.start()) + 1
    if in_base:
        print(f"OLD  plan:{line} ({lang or '-'}) only in base: {in_base[0]}")
        continue
    bad += 1
    print(f"MISS plan:{line} ({lang or '-'}): {body.splitlines()[0][:90]!r}")

print(f"{checked} blocks checked, {bad} missing")
sys.exit(1 if bad else 0)
