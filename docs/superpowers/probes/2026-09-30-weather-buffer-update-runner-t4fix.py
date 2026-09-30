"""Update mutate-impl.py for the review fix after Task 4: new anchors for M03-M06 (the
conversion moved inside a try), and M23-M30. Aborts without writing unless every old text
occurs exactly once."""

import pathlib

p = pathlib.Path(__file__).with_name("mutate-impl.py")
t = p.read_text(encoding="utf-8")

repl = [
    (
        '        (H, "    if parsed.tzinfo is None:\\n        return parsed\\n"\n'
        '            "    return dt_util.as_local(parsed).replace(tzinfo=None)\\n",\n'
        '            "    if parsed.tzinfo is None:\\n        return parsed\\n"\n'
        '            "    if provenance == STAMP_FROM_STORE:\\n"\n'
        '            "        return parsed.astimezone(_process_timezone()).replace(tzinfo=None)\\n"\n'
        '            "    return dt_util.as_local(parsed).replace(tzinfo=None)\\n")]),\n',
        '        (H, "    if parsed.tzinfo is None:\\n        return parsed\\n"\n'
        '            "    try:\\n        return dt_util.as_local(parsed).replace(tzinfo=None)\\n",\n'
        '            "    if parsed.tzinfo is None:\\n        return parsed\\n"\n'
        '            "    if provenance == STAMP_FROM_STORE:\\n"\n'
        '            "        return parsed.astimezone(_process_timezone()).replace(tzinfo=None)\\n"\n'
        '            "    try:\\n        return dt_util.as_local(parsed).replace(tzinfo=None)\\n")]),\n',
    ),
    (
        '        (H, "        parsed = parsed.replace(tzinfo=_process_timezone())\\n",\n'
        '            "        return value\\n")]),\n',
        '        (H, "            parsed = parsed.replace(tzinfo=_process_timezone())\\n",\n'
        '            "            return value\\n")]),\n',
    ),
    (
        '        (H, "        parsed = parsed.replace(tzinfo=_process_timezone())\\n",\n'
        '            "        parsed = parsed.astimezone(_process_timezone())\\n")]),\n',
        '        (H, "            parsed = parsed.replace(tzinfo=_process_timezone())\\n",\n'
        '            "            parsed = parsed.astimezone(_process_timezone())\\n")]),\n',
    ),
    (
        '        (H, "    return dt_util.as_local(parsed).replace(tzinfo=None).isoformat()\\n",\n'
        '            "    return dt_util.as_local(parsed).replace(tzinfo=None)\\n")]),\n',
        '        (H, "        return dt_util.as_local(parsed).replace(tzinfo=None).isoformat()\\n",\n'
        '            "        return dt_util.as_local(parsed).replace(tzinfo=None)\\n")]),\n',
    ),
]

ADD = '''    # From the review of Task 4: the aware branch, the microseconds, a later major, the
    # dict guards, and a conversion that must not raise out of the store's load.
    ("M23", "lift_legacy_stamp re-reads an aware stamp in the process zone", [
        (H, "        if parsed.tzinfo is None:\\n"
            "            parsed = parsed.replace(tzinfo=_process_timezone())\\n",
            "        if True:\\n"
            "            parsed = parsed.replace(tzinfo=_process_timezone())\\n")]),
    ("M24", "lift_legacy_stamp drops the microseconds", [
        (H, "        return dt_util.as_local(parsed).replace(tzinfo=None).isoformat()\\n",
            "        return dt_util.as_local(parsed).replace(tzinfo=None)"
            ".isoformat(timespec=\\"seconds\\")\\n")]),
    ("M25", "the stamp step checks the minor only", [
        (S, "        if (old_major_version, old_minor_version) < (14, 2):\\n",
            "        if old_minor_version < 2:\\n")]),
    ("M26", "no dict guard for a zone in the stamp step", [
        (S, "    for zone in data.get(\\"zones\\") or []:\\n        if not isinstance(zone, dict):\\n"
            "            continue\\n",
            "    for zone in data.get(\\"zones\\") or []:\\n")]),
    ("M27", "no dict guard for a mapping in the stamp step", [
        (S, "    for mapping in data.get(\\"mappings\\") or []:\\n"
            "        if not isinstance(mapping, dict):\\n            continue\\n",
            "    for mapping in data.get(\\"mappings\\") or []:\\n")]),
    ("M28", "lift_legacy_stamp lets an out-of-range conversion raise", [
        (H, "    except (ValueError, OverflowError, OSError):\\n        return value\\n",
            "    except ValueError:\\n        return value\\n")]),
    ("M29", "coerce_stamp lets an out-of-range conversion raise", [
        (H, "    try:\\n        return dt_util.as_local(parsed).replace(tzinfo=None)\\n"
            "    except OverflowError:\\n",
            "    if True:\\n        return dt_util.as_local(parsed).replace(tzinfo=None)\\n"
            "    if False:\\n")]),
    ("M30", "_parse_stored_as_ha_local lets an out-of-range conversion raise", [
        (L, "            try:\\n                return dt_util.as_local(value).replace(tzinfo=None)\\n"
            "            except OverflowError:\\n",
            "            if True:\\n                return dt_util.as_local(value).replace(tzinfo=None)\\n"
            "            if False:\\n")]),
'''
ANCHOR = "    # From the re-review of Task 3: the weather-entity reader"

for old, new in repl:
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"{n}x: {old[:90]!r}")
    t = t.replace(old, new)
if t.count(ANCHOR) != 1:
    raise SystemExit("anchor for the additions not found once")
t = t.replace(ANCHOR, ADD + ANCHOR)
p.write_bytes(t.encode("utf-8"))
print("mutate-impl.py updated")
