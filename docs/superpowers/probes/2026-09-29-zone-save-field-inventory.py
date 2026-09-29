"""Classify every ZoneEntry field for the zone-save design (Eifel-Joe#5).

Usage:
    python 2026-09-29-zone-save-field-inventory.py <path to custom_components/irrigation_plus>

Reads, does not import: store.py (ZoneEntry fields), const.py (ZONE_* names), the
panel's const.ts, view-zone-settings.ts (keys the form writes through
handleEditZone) and websockets.py (the zone view's server-owned strip list).

"Form-edited" means: the key appears in the object literal of a
``this.handleEditZone(index, {...})`` call, or is assigned into the ``next``
object the plant-type handler spreads into one. Nothing else in the form writes
an existing zone.
"""

import os
import re
import sys


def read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as fh:
        return fh.read()


def main(root):
    store = read(root, "store.py")
    const = read(root, "const.py")
    tsconst = read(root, "frontend/src/const.ts")
    form = read(root, "frontend/src/views/zones/view-zone-settings.ts")
    ws = read(root, "websockets.py")

    start = store.index("class ZoneEntry")
    end = store.index("\nclass ", start + 10)
    fields = re.findall(r"^\s{4}([a-z_0-9]+)\s*=\s*attr\.ib", store[start:end], re.M)

    py = {
        m.group(1): m.group(2)
        for m in re.finditer(r'^(ZONE_[A-Z0-9_]+)\s*=\s*"([^"]+)"', const, re.M)
    }
    ts = {
        m.group(1): m.group(2)
        for m in re.finditer(r'export const (ZONE_[A-Z0-9_]+)\s*=\s*"([^"]+)"', tsconst)
    }

    edited = set()
    calls = 0
    for m in re.finditer(r"this\.handleEditZone\(\s*index\s*,\s*\{", form):
        calls += 1
        i, depth = m.end(), 1
        while depth and i < len(form):
            depth += (form[i] == "{") - (form[i] == "}")
            i += 1
        body = form[m.end() : i - 1]
        for key in re.findall(r"\[(ZONE_[A-Z0-9_]+)\]\s*:", body):
            edited.add(ts[key])
    for key in re.findall(r"next\[(ZONE_[A-Z0-9_]+)\]\s*=", form):
        edited.add(ts[key])
    for key in re.findall(
        r"const next: Partial<SmartIrrigationZone> = \{\s*\[(ZONE_[A-Z0-9_]+)\]", form
    ):
        edited.add(ts[key])

    s2 = ws.index("for _server_owned in (")
    e2 = ws.index("):", s2)
    deny = {py[n] for n in re.findall(r"const\.(ZONE_[A-Z0-9_]+)", ws[s2:e2])}

    print(f"handleEditZone calls:          {calls}")
    print(f"ZoneEntry fields:              {len(fields)}")
    print(f"form-edited (in ZoneEntry):    {len(edited & set(fields))}")
    print(f"strip list (websockets.py):    {len(deny)}")
    print(f"form-edited AND stripped:      {sorted(edited & deny)}")
    print(f"form-edited, not in ZoneEntry: {sorted(edited - set(fields))}")
    print("neither form-edited nor stripped:")
    for f in fields:
        if f not in edited and f not in deny:
            print(f"    {f}")
    print("form-edited fields:")
    for f in fields:
        if f in edited:
            print(f"    {f}")
    print("stripped fields:")
    for f in fields:
        if f in deny:
            print(f"    {f}")


if __name__ == "__main__":
    main(sys.argv[1])
