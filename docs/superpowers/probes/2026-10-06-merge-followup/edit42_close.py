"""Index issue after the merges of upstream PRs 191 and 192: items 11 and 12 struck, item 43c new.

Dry run by default (writes i42-before.md / i42-after.md and prints the changed lines);
with --send it edits the body and reads it back.
"""

import difflib
import subprocess
import sys
from pathlib import Path

D = Path(r"D:\Entwicklung\HASI\merge-followup-work\texts")
REPO = "Eifel-Joe/HAsmartirrigation"


def body_now() -> str:
    raw = subprocess.run(["gh", "api", f"repos/{REPO}/issues/42", "--jq", ".body"],
                         capture_output=True, check=True).stdout.decode("utf-8")
    return raw[:-1] if raw.endswith("\n") else raw  # gh --jq adds one newline


def line_starting(body: str, prefix: str) -> str:
    hits = [ln for ln in body.split("\n") if ln.startswith(prefix)]
    assert len(hits) == 1, (prefix, len(hits))
    return hits[0] + "\n"


raw = body_now()
assert "\r" not in raw, "body carries CR"
(D / "i42-before.md").write_bytes(raw.encode("utf-8"))
body = raw

REPLACE = [
    ("11. Eifel-Joe#10 — irrigation calendar",
     "11. ~~Eifel-Joe#10 — irrigation calendar: rain added then subtracted; day read as month~~ · ✅ **`JustChr#191`"
     " merged 2026-10-06 as `7f556344`**, in the pre-release v2026.10.05 — issue closed · screenshot item 43c · side"
     " findings items 39o–39p\n"),
    ("12. Eifel-Joe#11 — `via_device` deprecation",
     "12. ~~Eifel-Joe#11 — `via_device` deprecation, deadline HA 2027.8.0~~ · ✅ **`JustChr#192` merged 2026-10-06 as"
     " `33d0fec9`**, in the pre-release v2026.10.05 — issue closed · side finding item 39q\n"),
    ("11. Eifel-Joe#10 — Bewässerungskalender",
     "11. ~~Eifel-Joe#10 — Bewässerungskalender: Regen addiert und wieder abgezogen; Tag als Monat gelesen~~ · ✅"
     " **`JustChr#191` gemergt 2026-10-06 als `7f556344`**, im Pre-Release v2026.10.05 — Issue geschlossen · Screenshot"
     " Punkt 43c · Nebenbefunde Punkte 39o–39p\n"),
    ("12. Eifel-Joe#11 — `via_device`-Deprecation",
     "12. ~~Eifel-Joe#11 — `via_device`-Deprecation, Frist HA 2027.8.0~~ · ✅ **`JustChr#192` gemergt 2026-10-06 als"
     " `33d0fec9`**, im Pre-Release v2026.10.05 — Issue geschlossen · Nebenbefund Punkt 39q\n"),
]
NEW_43C_EN = ("43c. Eifel-Joe#87 — replace the seasonal-outlook screenshot in the docs · leftover of Eifel-Joe#10;"
              " JustChr: \"yes please\" (`upstream:freigegeben`) · **new 2026-10-06**\n")

new = body
for prefix, rep in REPLACE:
    old = line_starting(new, prefix)
    new = new.replace(old, rep)

# 43b appears once per language; the English one names "defer a distributor cycle".
en43b = line_starting(new, "43b. Eifel-Joe#68 — defer a distributor cycle")
new = new.replace(en43b, en43b + NEW_43C_EN)
de43b = [ln for ln in new.split("\n") if ln.startswith("43b. Eifel-Joe#68 — ") and "defer a distributor" not in ln]
assert len(de43b) == 1, ("German 43b", len(de43b))
de_line = de43b[0] + "\n"
new = new.replace(de_line, de_line +
                  "43c. Eifel-Joe#87 — den Screenshot des Saison-Ausblicks in der Doku ersetzen · Rest von Eifel-Joe#10;"
                  " JustChr: „yes please“ (`upstream:freigegeben`) · **neu 2026-10-06**\n")

(D / "i42-after.md").write_bytes(new.encode("utf-8"))
print("CR in new:", new.count("\r"))
for line in difflib.unified_diff(body.split("\n"), new.split("\n"), lineterm="", n=0):
    if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
        print(line)

if "--send" in sys.argv:
    subprocess.run(["gh", "issue", "edit", "42", "--repo", REPO, "--body-file", str(D / "i42-after.md")], check=True)
    back = body_now()
    (D / "i42-readback.md").write_bytes(back.encode("utf-8"))
    print("read back identical:", back == new)
