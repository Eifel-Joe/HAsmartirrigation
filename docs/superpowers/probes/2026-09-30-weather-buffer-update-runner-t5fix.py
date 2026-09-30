"""Add the mutants from the review of Task 5 to mutate-impl.py (M31-M33). Aborts without
writing unless the anchor occurs exactly once."""

import pathlib

p = pathlib.Path(__file__).with_name("mutate-impl.py")
t = p.read_text(encoding="utf-8")

ADD = '''    # From the review of Task 5: the live refresh's own clock read, and the two writers
    # whose stamp the matrix could not tell from the zone's creation stamp.
    ("M31", "the live refresh reads the process clock", [
        (L, "        now = dt_util.now()\\n        offset = now.utcoffset()\\n",
            "        now = datetime.datetime.now()\\n        offset = now.utcoffset()\\n")]),
    ("M32", "clearing the weather data does not stamp the watermark", [
        (PKG + "calculation.py", "                {\\n                    const.ZONE_LAST_CONSUMED: now,\\n",
            "                {\\n")]),
    ("M33", "a sensor group switching its source does not stamp the watermark", [
        (PKG + "__init__.py",
            "                        {\\n                            const.ZONE_LAST_CONSUMED: now,\\n",
            "                        {\\n")]),
'''
ANCHOR = "    # From the re-review of Task 3: the weather-entity reader"

if t.count(ANCHOR) != 1:
    raise SystemExit("anchor not found once")
t = t.replace(ANCHOR, ADD + ANCHOR)
p.write_bytes(t.encode("utf-8"))
print("mutate-impl.py updated")
