"""Build one curated instruction file per plan task: prompts/tN-full.md.

common.md (context and ground rules) + the plan's task text verbatim + the
binding run order + what the dry run measured. The implementer reads only its
own file, never the whole plan.
"""

import re
from pathlib import Path

HERE = Path(__file__).parent
PLAN = Path(r"D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\plans\2026-10-05-seasonal-outlook.md")
PY = "/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe"
WT = "/d/Entwicklung/HASI/issue10-work/wt"

# Measured in the dry run (probe-run-2.txt), except where marked "computed".
# (k-expression, RED summary, RED E-lines, GREEN summary, calendar file computed, three files measured)
MEASURED = {
    1: ("carries_no_rain or subtracted_once",
        "2 failed, 11 deselected, 2 errors",
        ["E   assert 112.0 == 62.0 ± 6.2e-05", "E   assert 122.0 == 62.0 ± 6.2e-05"],
        "2 passed, 11 deselected, 2 errors", "13 passed, 13 errors", "84 passed, 13 errors"),
    2: ("kc_scales or kc_is_none or module_without_rain",
        "2 failed, 1 passed, 13 deselected, 3 errors",
        ["E   assert 420.0 == 110.0 ± 1.1e-04", "E   assert 330.0 == 930.0 ± 9.3e-04"],
        "3 passed, 13 deselected, 3 errors", "16 passed, 16 errors", "87 passed, 16 errors"),
    3: ("static_demand or static_surplus",
        "2 failed, 16 deselected, 2 errors",
        ["E   assert -3.0 == 93.0 ± 9.3e-05", "E   assert 2.0 == 0.0"],
        "2 passed, 16 deselected, 2 errors", "18 passed, 18 errors", "89 passed, 18 errors"),
    4: ("own_number_of_days",
        "1 failed, 18 deselected, 1 error",
        ["E   assert 8.04 == 7.77 ± 7.8e-06"],
        "1 passed, 18 deselected, 1 error", "19 passed, 19 errors", "90 passed, 19 errors"),
    5: ("TestTheClimateCurves",
        "2 failed, 1 passed, 19 deselected, 3 errors",
        ["E   assert 50.0 == 80.0 ± 8.0e-05", "E   assert 0.0 > 4.0"],
        "3 passed, 19 deselected, 3 errors", "22 passed, 22 errors", "93 passed, 22 errors"),
    6: ("comes_from_latitude",
        "1 failed, 22 deselected, 1 error",
        ["E   AssertionError: ['Based on typical January climate patterns', 'Based on typical "
         "February climate patterns', …", "E   assert False"],
        "1 passed, 22 deselected, 1 error", "23 passed, 23 errors", "94 passed, 23 errors"),
    7: ("service_description",
        "1 failed, 23 deselected",
        ["E   AssertionError: assert 'latitude' in 'Generate a 12-month watering calendar for "
         "irrigation zones based on representative climate data'"],
        "1 passed, 23 deselected", "24 passed, 23 errors", "95 passed, 23 errors"),
    8: ("illustration_note",
        "1 failed, 24 deselected",
        ["E   AssertionError: assert 'panels.setup.weather_data.seasonal_note' in "
         "'private _renderSeasonal(): TemplateResult {\\n    if (!this.hass) return html`…"],
        "1 passed, 24 deselected", "25 passed, 23 errors", "96 passed, 23 errors"),
    9: (None, None, None, None, "25 passed, 23 errors", "96 passed, 23 errors"),
}

EXTRA = {
    7: "- After staging: `git diff --cached --name-only | wc -l` printed `10` "
       "(services.yaml, eight `translations/*.json`, the test file).\n",
    8: "- Frontend build: `npm ci` + `npm run build` (eslint + rollup) exit 0, `npx tsc --noEmit -p .` "
       "no output. The `for … git diff --quiet` loop printed `CHANGED` for exactly "
       "`dist/irrigation-plus.js` (+4/−1 lines) and `dist/irrigation-plus-card-impl.js` (+1/−1); "
       "`irrigation-plus-card.js` and `irrigation-plus-card-legacy.js` printed `same`. If `git status` "
       "still shows those two as `M`, that is autocrlf only: `git checkout -- <bundle>` for exactly "
       "those two, then confirm `git status --short` lists no other bundle.\n"
       "- After staging (with `git add -f` for the two bundles): `git diff --cached --name-only | wc -l` "
       "printed `12` (the view, eight catalogues, the test file, two bundles).\n",
    9: "- No tests change in this task. The plan's `git grep` printed nothing and `exit 1` "
       "(nothing found is the wanted result).\n",
}


def task_sections(plan_text):
    parts = re.split(r"(?m)^(?=### Task \d+:)", plan_text)
    out = {}
    for part in parts:
        m = re.match(r"### Task (\d+):", part)
        if m:
            text = part.rstrip()
            text = re.sub(r"\n---\s*$", "", text).rstrip()
            out[int(m.group(1))] = text
    return out


def run_order(n, meas):
    k, red, _e, green, _cal, _three = meas
    steps = [
        f"1. **Precondition:** `git -C {WT} status --porcelain` prints nothing and "
        f"`git -C {WT} rev-list --count bbf2e151..HEAD` prints `{n - 1}`. Otherwise STOP.",
    ]
    if k:
        steps += [
            f"2. **Failing tests:** `cd /d/Entwicklung/HASI/issue10-work && {PY} apply_plan_task.py {n} tests`",
            f"3. **RED:** `cd {WT} && {PY} -m pytest tests/test_watering_calendar.py -k \"{k}\" "
            f"-p _local_socket_unblock -q` — expected `{red}` (see below).",
            f"4. **Implementation:** `cd /d/Entwicklung/HASI/issue10-work && {PY} apply_plan_task.py {n} code`",
            f"5. **GREEN:** the RED command again — expected `{green}`.",
        ]
    else:
        steps += [
            f"2. **Implementation:** `cd /d/Entwicklung/HASI/issue10-work && {PY} apply_plan_task.py {n} code`",
        ]
    steps += [
        f"{len(steps) + 1}. **Whole files:** `cd {WT} && {PY} -m pytest tests/test_watering_calendar.py "
        f"tests/test_watering_calendar_api.py tests/test_i18n_completeness.py -p _local_socket_unblock -q` "
        f"— no `failed`, every ERROR a teardown `Lingering timer` one.",
    ]
    if n == 8:
        steps.append(f"{len(steps) + 1}. **Frontend build and bundle check:** exactly the two commands of the "
                     f"task's Schritt 6, from the worktree root `{WT}`.")
    if n == 9:
        steps.append(f"{len(steps) + 1}. **Docs check:** the task's `git grep` line, from the worktree root.")
    steps.append(f"{len(steps) + 1}. **Lint:** the lint command from the ground rules.")
    steps.append(f"{len(steps) + 1}. **Stage and commit:** the task's `git add` line(s) (from the worktree root), "
                 f"then the count check if the task gives one, then the task's `git commit -F - <<'EOF' … EOF` "
                 f"verbatim.")
    steps.append(f"{len(steps) + 1}. **Report** as described in the ground rules. Do not run anything after the commit.")
    return "\n".join(steps)


def measured(n, meas):
    k, red, elines, green, cal, three = meas
    lines = []
    if k:
        lines.append(f"- RED (measured): `{red}`; teardown ERRORs = the `errors` count, each `Lingering timer`.")
        lines.append("- RED `E ` lines (measured):")
        lines += [f"  - `{e}`" for e in elines]
        lines.append(f"- GREEN (measured): `{green}`.")
    lines.append(f"- Whole files, the three-file run (measured): `{three}`. "
                 f"The calendar file alone would read `{cal}` (computed).")
    text = "\n".join(lines) + "\n"
    return text + EXTRA.get(n, "")


def main():
    plan = PLAN.read_text(encoding="utf-8")
    common = (HERE / "prompts" / "common.md").read_text(encoding="utf-8")
    sections = task_sections(plan)
    for n in range(1, 10):
        meas = MEASURED[n]
        title = sections[n].split("\n", 1)[0].replace("### ", "")
        body = (
            f"# {title}\n\n"
            f"You implement exactly this one task of the plan. The plan is written in German; the code, "
            f"tests and commit messages in it are English and final.\n\n"
            f"{common}\n"
            f"## Your task — the plan's text, verbatim\n\n"
            f"Read it to understand what the edits do and why. The edits themselves are applied by "
            f"`apply_plan_task.py` (see the ground rules), not typed by you. Where the task text and the "
            f"run order below differ in how a command is spelled, the run order wins; the expected results "
            f"are the same.\n\n"
            f"{sections[n]}\n\n"
            f"## Run order (binding)\n\n{run_order(n, meas)}\n\n"
            f"## Measured in the dry run\n\n{measured(n, meas)}"
        )
        out = HERE / "prompts" / f"t{n}-full.md"
        out.write_bytes(body.replace("\r\n", "\n").encode("utf-8"))
        print(f"{out.name}: {len(body.splitlines())} lines")


if __name__ == "__main__":
    main()
