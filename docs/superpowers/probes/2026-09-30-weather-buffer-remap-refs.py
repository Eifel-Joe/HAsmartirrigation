"""Map every file:line reference of Revision 4 and its inventory from 1876aa03 to 0b9a71bd.

Only store.py, __init__.py and websockets.py changed between the two commits (git diff --stat).
For every reference into one of those three files: map the line through a difflib alignment of
the two versions, and check that the mapped line has the same text as the original line.
References into any other file are checked for being unchanged (same text at the same line).
Continuation references (", :123", "/:123", " and :123") inherit the file of the anchor before.
"""
import difflib
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path("D:/Entwicklung/HASI/HAsmartirrigation")
ARCHIVE = pathlib.Path("D:/Entwicklung/HASI/pr139-work/archive-wt/docs/superpowers")
DOCS = [
    ARCHIVE / "specs/2026-09-28-weather-buffer-one-frame-design.md",
    ARCHIVE / "probes/2026-09-28-weather-buffer-stamp-inventory.md",
]
OLD, NEW = "1876aa03", "0b9a71bd"
PKG = "custom_components/irrigation_plus/"
CHANGED = {"store.py", "__init__.py", "websockets.py"}


def show(sha, path):
    out = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{sha}:{path}"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if out.returncode != 0:
        return None
    return out.stdout.splitlines()


def resolve(name):
    """Resolve a bare module file name to its package path (first match wins)."""
    candidates = [PKG + name, PKG + "frontend/src/" + name, PKG + "calcmodules/pyeto/" + name]
    for c in candidates:
        if show(NEW, c) is not None:
            return c
    return None


def line_map(old, new):
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    m = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                m[i1 + k + 1] = j1 + k + 1
    return m


ANCHOR = re.compile(r"(?P<file>[A-Za-z_][\w/]*\.(?:py|ts)):(?P<a>\d+)(?:-(?P<b>\d+))?")
CONT = re.compile(r"\s*(?:,|/|and|or)\s*:(?P<a>\d+)(?:-(?P<b>\d+))?")

refs = []  # (doc, file, line)
for doc in DOCS:
    text = doc.read_text(encoding="utf-8")
    # The spec's own 2026-09-30 addendum cites 0b9a71bd; only the text above it cites 1876aa03.
    text = text.split("\n## Addendum 2026-09-30")[0]
    for m in ANCHOR.finditer(text):
        fname = m.group("file").split("/")[-1]
        lines = [int(m.group("a"))] + ([int(m.group("b"))] if m.group("b") else [])
        pos = m.end()
        while True:
            c = CONT.match(text, pos)
            if not c:
                break
            lines.append(int(c.group("a")))
            if c.group("b"):
                lines.append(int(c.group("b")))
            pos = c.end()
        for ln in lines:
            refs.append((doc.name, fname, ln))

cache = {}
maps = {}
unresolved = set()
changed_rows = []
ok_same = ok_moved = bad = 0
for doc, fname, ln in refs:
    if fname not in cache:
        path = resolve(fname)
        if path is None:
            unresolved.add(fname)
            cache[fname] = None
            continue
        cache[fname] = (path, show(OLD, path), show(NEW, path))
        if fname in CHANGED:
            maps[fname] = line_map(cache[fname][1], cache[fname][2])
    if cache[fname] is None:
        continue
    path, old, new = cache[fname]
    if ln > len(old):
        bad += 1
        changed_rows.append((doc, fname, ln, "OUT OF RANGE on " + OLD, ""))
        continue
    if fname in CHANGED:
        nl = maps[fname].get(ln)
        if nl is None:
            bad += 1
            changed_rows.append((doc, fname, ln, "LINE CHANGED (no equal match)", old[ln - 1].strip()[:70]))
        elif nl == ln:
            ok_same += 1
        else:
            ok_moved += 1
            changed_rows.append((doc, fname, ln, f"-> {nl}", old[ln - 1].strip()[:70]))
    else:
        if ln <= len(new) and old[ln - 1] == new[ln - 1]:
            ok_same += 1
        else:
            bad += 1
            changed_rows.append((doc, fname, ln, "TEXT DIFFERS", old[ln - 1].strip()[:70]))

print(f"references parsed: {len(refs)}")
print(f"unchanged: {ok_same}   moved (text identical): {ok_moved}   problems: {bad}")
print(f"unresolved file names (not in the package): {sorted(unresolved)}")
seen = set()
for doc, fname, ln, verdict, txt in sorted(changed_rows, key=lambda r: (r[1], r[2], r[0])):
    key = (fname, ln, verdict)
    if key in seen:
        continue
    seen.add(key)
    print(f"{fname}:{ln:<5} {verdict:<32} {txt}")
sys.exit(0)
