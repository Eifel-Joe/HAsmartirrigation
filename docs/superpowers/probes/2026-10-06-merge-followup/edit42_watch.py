"""Index issue, second edit: the upstream issue for real climate data goes under "Watched, not scheduled",
and item 11 points to it. Usage: edit42_watch.py <upstream issue number> [--send]
"""

import difflib
import subprocess
import sys
from pathlib import Path

D = Path(r"D:\Entwicklung\HASI\merge-followup-work\texts")
REPO = "Eifel-Joe/HAsmartirrigation"
N = int(sys.argv[1])


def body_now() -> str:
    raw = subprocess.run(["gh", "api", f"repos/{REPO}/issues/42", "--jq", ".body"],
                         capture_output=True, check=True).stdout.decode("utf-8")
    return raw[:-1] if raw.endswith("\n") else raw  # gh --jq adds one newline


raw = body_now()
assert "\r" not in raw, "body carries CR"
(D / "i42-before-watch.md").write_bytes(raw.encode("utf-8"))

EN_11_OLD = "issue closed · screenshot item 43c · side findings items 39o–39p\n"
EN_11_NEW = f"issue closed · screenshot item 43c · real climate data `JustChr#{N}` (watched) · side findings items 39o–39p\n"
DE_11_OLD = "Issue geschlossen · Screenshot Punkt 43c · Nebenbefunde Punkte 39o–39p\n"
DE_11_NEW = (f"Issue geschlossen · Screenshot Punkt 43c · echte Klimadaten `JustChr#{N}` (beobachtet) · Nebenbefunde"
             " Punkte 39o–39p\n")
EN_BULLET = (f"- **`JustChr#{N}`** (ours): real climate data for the seasonal outlook — opened 2026-10-06 at JustChr's"
             " request after `JustChr#191`; he decides the shape there. Nothing to build until he has.\n")
DE_BULLET = (f"- **`JustChr#{N}`** (unseres): echte Klimadaten für den Saison-Ausblick — am 2026-10-06 auf JustChrs"
             " Wunsch nach `JustChr#191` eröffnet; er entscheidet dort die Form. Bis dahin nichts zu bauen.\n")
# The bullet goes at the end of each language's watched section, right before the next heading.
EN_NEXT = "\n## Keeping these current\n"
DE_NEXT = "\n### Diese Liste aktuell halten\n"

new = raw
for old, rep in ((EN_11_OLD, EN_11_NEW), (DE_11_OLD, DE_11_NEW)):
    assert new.count(old) == 1, ("item 11 anchor", new.count(old), old[:40])
    new = new.replace(old, rep)
for nxt, bullet in ((EN_NEXT, EN_BULLET), (DE_NEXT, DE_BULLET)):
    assert new.count(nxt) == 1, ("section anchor", new.count(nxt), nxt.strip())
    before = new.split(nxt)[0]
    # The section's last list line ends right before the blank line of nxt: the bullet joins that list.
    assert before.endswith("\n") and not before.endswith("\n\n"), repr(before[-40:])
    new = new.replace(nxt, bullet + nxt)

(D / "i42-after-watch.md").write_bytes(new.encode("utf-8"))
print("CR in new:", new.count("\r"))
for line in difflib.unified_diff(raw.split("\n"), new.split("\n"), lineterm="", n=1):
    if not line.startswith(("+++", "---", "@@")):
        print(line)

if "--send" in sys.argv:
    subprocess.run(["gh", "issue", "edit", "42", "--repo", REPO, "--body-file", str(D / "i42-after-watch.md")],
                   check=True)
    back = body_now()
    (D / "i42-readback-watch.md").write_bytes(back.encode("utf-8"))
    print("read back identical:", back == new)
