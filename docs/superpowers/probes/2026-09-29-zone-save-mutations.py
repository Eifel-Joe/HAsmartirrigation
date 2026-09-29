"""Apply each mutation, run the pytest files and the vitest file, record, revert.

A mutation is KILLED when it makes tests fail that pass on the unmutated
branch. Pre-existing failures are measured first and subtracted, not assumed
away. Adapted from the archived runner
(docs/superpowers/probes/2026-09-28-external-run-mutations.py); the change is
that this work also mutates TypeScript, so every mutation runs both the pytest
files (the call-site pin lives there, since CI runs pytest only) and the vitest
file (the panel's save behaviour).

Run:
    python D:/Entwicklung/HASI/issue5-work/mutate.py [worktree]
"""

import io
import json
import os
import subprocess
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else r"D:\Entwicklung\HASI\issue5-work\wt"
PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
TMP = r"D:\Entwicklung\HASI\issue5-work\tmp"
OUT = r"D:\Entwicklung\HASI\issue5-work\mutations.json"

IP = os.path.join(WT, "custom_components", "irrigation_plus")
FRONTEND = os.path.join(IP, "frontend")
WS = os.path.join(IP, "websockets.py")
STORE = os.path.join(IP, "store.py")
VIEW = os.path.join(FRONTEND, "src", "views", "zones", "view-zone-settings.ts")

# Every test named as a killer below lives in one of these. A file missing
# from here once turned a broken run into a clean-looking "0 killed".
SUITES = [
    "tests/test_zone_view_save.py",
    "tests/test_manual_bucket_assertion.py",
    "tests/test_distributor_integration.py",
]
VITEST_FILE = "src/views/zones/view-zone-settings-save.test.ts"

NEW_STRIP_ENTRIES = """            # Reset to 0 in the same write as every credit: a pre-run copy
            # undoes the days-between wait the run has just restarted.
            const.ZONE_DAYS_SINCE_IRRIGATION,
            # The calculation's outputs.
            const.ZONE_IRRIGATION_TARGET_BUCKET,
            const.ZONE_DELTA,
            const.ZONE_EXPLANATION,
            const.ZONE_CURRENT_DRAINAGE,
            const.ZONE_NUMBER_OF_DATA_POINTS,
"""

COMPLETION = """        if zone is not None and (const.ZONE_BUCKET in data) != (
            const.ZONE_MAXIMUM_BUCKET in data
        ):
            stored = coordinator.store.get_zone(zone)
            if stored is not None:
                missing = (
                    const.ZONE_MAXIMUM_BUCKET
                    if const.ZONE_BUCKET in data
                    else const.ZONE_BUCKET
                )
                data[missing] = stored.get(missing)
"""

MISSING = """                missing = (
                    const.ZONE_MAXIMUM_BUCKET
                    if const.ZONE_BUCKET in data
                    else const.ZONE_BUCKET
                )
"""
MISSING_SWAPPED = """                missing = (
                    const.ZONE_BUCKET
                    if const.ZONE_BUCKET in data
                    else const.ZONE_MAXIMUM_BUCKET
                )
"""

STORE_CLAMP_ANCHOR = (
    "            # review finding J: guard changes[ZONE_BUCKET] presence like the\n"
)
STORE_READS_MAXIMUM = (
    "            if ZONE_BUCKET in changes and ZONE_MAXIMUM_BUCKET not in changes:\n"
    "                changes[ZONE_MAXIMUM_BUCKET] = old.maximum_bucket\n"
    + STORE_CLAMP_ANCHOR
)

FIRST_CALL_SITE = (
    "this.handleEditZone(index, {\n        [ZONE_DISTRIBUTOR_ID]: null,\n"
)
FIRST_CALL_SITE_SPREAD = (
    "this.handleEditZone(index, {\n        ...zone,\n"
    "        [ZONE_DISTRIBUTOR_ID]: null,\n"
)

# (n, file, label, old, new, expected killer)
MUTATIONS = [
    (1, WS, "the six new strip entries are gone", NEW_STRIP_ENTRIES, "",
     "test_a_whole_zone_post_does_not_write_back_what_the_server_writes"),
    (2, WS, "only days_since_irrigation is gone",
     "            const.ZONE_DAYS_SINCE_IRRIGATION,\n", "",
     "test_a_whole_zone_post_does_not_write_back_what_the_server_writes"),
    (3, WS, "no pair completion", COMPLETION, "",
     "test_a_lone_bucket_is_clamped..., test_a_lowered_maximum..."),
    (4, WS, "completion when both or neither are posted",
     "(const.ZONE_BUCKET in data) != (", "(const.ZONE_BUCKET in data) == (",
     "test_a_lone_bucket_is_clamped..., test_a_lowered_maximum..."),
    (5, WS, "completion overwrites the posted value", MISSING, MISSING_SWAPPED,
     "test_a_lone_bucket_is_clamped..., test_a_lowered_maximum..."),
    (6, WS, "completion also on create (no id)",
     "if zone is not None and (const.ZONE_BUCKET in data) != (",
     "if (const.ZONE_BUCKET in data) != (",
     "test_a_new_zone_posted_with_a_bucket_and_no_maximum_is_created"),
    (7, STORE, "the store completes the pair itself",
     STORE_CLAMP_ANCHOR, STORE_READS_MAXIMUM,
     "test_a_bucket_set_through_the_store_funnel_is_not_clamped"),
    (8, VIEW, "posted without the zone id",
     "this.saveToHA({ id, ...changes } as Partial<SmartIrrigationZone>),",
     "this.saveToHA({ ...changes } as Partial<SmartIrrigationZone>),",
     "sends the zone id and the edited field..."),
    (9, VIEW, "one pending set for every zone",
     "    this._pendingEdits.set(zone.id, pending);\n",
     "    this._pendingEdits.clear();\n    this._pendingEdits.set(zone.id, pending);\n",
     "saves every zone edited inside one debounce window"),
    (10, VIEW, "an edit replaces the zone's pending edits",
     "const pending: ZoneEdit = { ...this._pendingEdits.get(zone.id) };",
     "const pending: ZoneEdit = {};",
     "merges two edits to one zone into one post"),
    (11, VIEW, "pending edits kept after posting",
     "    this._pendingEdits.clear();\n    if (!edits.length) return;\n",
     "    if (!edits.length) return;\n",
     "does not post an edit twice once it has been sent"),
    (12, VIEW, "a cleared field stays undefined",
     "= value ?? null;", "= value;",
     "sends a cleared field as null..."),
    (13, VIEW, "the change worked out against the page's copy",
     "for (const [key, value] of Object.entries(changes)) {",
     "for (const [key, value] of Object.entries(changes).filter(\n"
     "      ([k, v]) => (zone as Record<string, unknown>)[k] !== v,\n"
     "    )) {",
     "sends every field the edit set, even one the page's copy already shows"),
    (14, VIEW, "a null id selects the text 'null'",
     'return id == null ? "" : String(id);',
     'return id === undefined ? "" : String(id);',
     "shows the empty option for a cleared id..."),
    (15, VIEW, "one call site spreads the page's copy again",
     FIRST_CALL_SITE, FIRST_CALL_SITE_SPREAD,
     "test_the_panel_names_what_each_zone_edit_sets"),
]


def read_src(path):
    raw = io.open(path, "rb").read()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def write_src(path, text, crlf):
    out = text.replace("\n", "\r\n") if crlf else text
    io.open(path + ".tmp", "wb").write(out.encode("utf-8"))
    os.replace(path + ".tmp", path)


def run_pytest():
    env = dict(os.environ)
    env.update(TMPDIR=TMP, TEMP=TMP, TMP=TMP, TZ="UTC")
    proc = subprocess.run(
        [PY, "-m", "pytest", *SUITES, "-p", "_local_socket_unblock", "-q"],
        cwd=WT, env=env, capture_output=True, text=True,
    )
    names = set()
    for line in (proc.stdout + proc.stderr).splitlines():
        if line.startswith(("FAILED tests/", "ERROR tests/")):
            names.add(line.split(" - ")[0].strip())
    tail = [ln for ln in proc.stdout.splitlines() if " passed" in ln or " failed" in ln]
    return names, (tail[-1] if tail else "NO SUMMARY LINE")


def run_vitest():
    proc = subprocess.run(
        "npx vitest run " + VITEST_FILE,
        cwd=FRONTEND, capture_output=True, text=True, shell=True,
        encoding="utf-8", errors="replace",
    )
    names = set()
    for line in (proc.stdout + proc.stderr).splitlines():
        stripped = line.strip()
        if stripped.startswith("FAIL ") and ">" in stripped:
            names.add("vitest " + stripped[5:].strip())
    tail = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip().startswith("Tests ")]
    return names, (tail[-1] if tail else "NO SUMMARY LINE")


def run_all():
    py_names, py_tail = run_pytest()
    vt_names, vt_tail = run_vitest()
    return py_names | vt_names, "pytest: %s | vitest: %s" % (py_tail, vt_tail)


def main():
    os.makedirs(TMP, exist_ok=True)
    originals = {p: read_src(p) for p in {m[1] for m in MUTATIONS}}

    print("measuring the unmutated branch in %s ..." % WT, flush=True)
    reference, summary = run_all()
    print("  %s" % summary, flush=True)
    print("  pre-existing failures/errors: %d" % len(reference), flush=True)
    if "NO SUMMARY" in summary or " 0 passed" in summary:
        raise SystemExit("a run collected nothing - every result would be a lie")

    results = []
    for n, path, label, old, new, expected in MUTATIONS:
        original, crlf = originals[path]
        count = original.count(old)
        if count != 1:
            print("MUT %2d: anchor appears %d times -- SKIPPED" % (n, count))
            results.append({"n": n, "file": os.path.basename(path),
                            "mutation": label, "result": "NOT APPLIED",
                            "why": "anchor appears %d times" % count})
            continue
        write_src(path, original.replace(old, new, 1), crlf)
        try:
            after, after_summary = run_all()
        finally:
            write_src(path, original, crlf)
        extra = sorted(after - reference)
        row = {"n": n, "file": os.path.basename(path), "mutation": label,
               "expected_killer": expected,
               "result": "killed" if extra else "survived",
               "summary": after_summary}
        if extra:
            row["killed_by"] = extra
        results.append(row)
        print("MUT %2d %-50s %s%s" % (n, label, row["result"].upper(),
              (" by %d test(s)" % len(extra)) if extra else ""), flush=True)
        for name in extra:
            print("         %s" % name.split("::", 1)[-1], flush=True)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(results, indent=2))
    ok = all(read_src(p)[0] == originals[p][0] for p in originals)
    print("\nevery source restored byte-for-byte: %s" % ok)
    killed = sum(1 for r in results if r.get("result") == "killed")
    print("%d killed / %d applied / %d total" % (killed, len(results), len(MUTATIONS)))


if __name__ == "__main__":
    main()
