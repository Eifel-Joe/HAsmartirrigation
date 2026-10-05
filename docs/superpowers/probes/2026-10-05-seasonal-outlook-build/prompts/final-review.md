# Final review of the whole branch `fix/seasonal-outlook` (read-only)

You review a finished fix branch for the Home Assistant custom integration "Irrigation Plus"
(`custom_components/irrigation_plus`) before it goes as ONE pull request to the upstream maintainer
(JustChr). He reviews carefully and squashes on merge: comments must be true, tests must pin
behaviour, nothing may refer to trackers, specs, plans or branches outside his repository.

**Read-only, strictly, and commit-pinned.** Read files only as `git show <sha>:<path>` /
`git diff` / `git log` / `git grep <sha>` in `D:\Entwicklung\HASI\issue10-work\wt` (Git Bash
`/d/Entwicklung/HASI/issue10-work/wt`) — NOT the working-tree files, and do not run pytest, npm,
black or ruff (the controller may run them in that worktree). Scratch files only under
`D:\Entwicklung\HASI\issue10-work\review-scratch\`, never `/tmp` or `C:`. Small stdlib-only Python
snippets on blobs you extracted with `git show` are fine.

**Range:** base `bbf2e151` (= upstream master, release v2026.10.04) .. HEAD `88d210a8`, 9 commits.
`git -C /d/Entwicklung/HASI/issue10-work/wt log --oneline bbf2e151..88d210a8`
`git -C /d/Entwicklung/HASI/issue10-work/wt diff bbf2e151 88d210a8 -- . ':!custom_components/irrigation_plus/frontend/dist'`
(The two rebuilt bundles `irrigation-plus.js` and `irrigation-plus-card-impl.js` are minified; they
were verified byte-identical to an independent build of the same sources. Check them only via
`--stat` and by grepping for the new key/text.)

## What the branch is for

Design (German, the owner's language): `D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\specs\2026-10-05-seasonal-outlook-design.md`
— read sections "Der Defekt", "Anforderungen" (A1–A6), "Entscheidungen" (E1–E7), "Das Design",
"Ausdrücklich nicht in dieser Arbeit" (explicitly out of scope — do not report those as missing).
The approved implementation plan dictated every edit verbatim; per-task reviews then added test pins
and comment fixes, all recorded with reasons in `D:\Entwicklung\HASI\issue10-work\deviations.md`
(read it: it tells you what was already found, taken or declined — do not re-report declined items
unless you have a NEW argument).

In short: the 12-month seasonal outlook (`watering_calendar.py`) now prices a month by the rules of
the real calculation (`calculation.py`): PyETO's ET carries no rain; rain is subtracted only where
the calculation books it (`zone_module_models_weather`); Kc scales the ET term, not the rain;
Static/Passthrough daily figures scale by the month's days (reference year 2024). The synthetic
climate keeps its constants; each seasonal curve now peaks where its comment says and the southern
hemisphere mirrors every seasonal curve (tropical/subtropical rain deliberately unchanged). Every
place that shows or describes the outlook (card note, service description in 8 languages,
`calculation_notes`, docs) calls it an illustration derived from latitude.

## Already established (do not re-check)

- Each task commit was checked byte for byte against "base + plan blocks + recorded deviations";
  each had its own quality review and re-review until approved.
- Full suite locally (Windows, HA 2024.12.5): 7 failed / 3681 passed / 9 skipped / 427 errors; the
  7 failed and 415 of the errors are the pre-existing local baseline (identical names), the other 12
  errors are the new tests on the `coordinator` fixture, which end locally with a teardown ERROR
  "Lingering timer after test" (pre-existing local artefact, clean in upstream CI).
- 40 targeted mutations of the changed lines are all killed by `tests/test_watering_calendar.py`.

## What to review (the whole, not the parts)

1. **End-state truth.** Every comment, docstring, test docstring and commit message in the range:
   is it true of the code at `88d210a8`? Pay special attention to sentences written in early
   commits that describe a later state (the per-task reviews accepted some "true at the head"
   statements — verify them now), e.g. the comment in `_calculate_monthly_et_pyeto` ("only where
   the calculation books it"), the test comment "no Kc (reads as 1.0)", the class docstrings of
   `TestAMonthIsPricedByTheCalculationsRules` and `TestTheOutlookSaysWhatItIs`.
2. **The calculation, end to end.** For each module (PyETO, Static, Passthrough) follow one month
   from `_generate_monthly_climate_data` through `_calculate_monthly_watering_for_zone` and
   `_calculate_monthly_watering_volume` and compare with `calculation.py`'s per-zone code. Any
   remaining divergence that the spec counts as a defect (not "model quality", see spec)?
3. **Cross-commit consistency.** Wording of the same claim across the service description, card
   note, `calculation_notes`, docs and code comments; the same concept named the same way.
4. **Test file as a whole** (`tests/test_watering_calendar.py`): every import used (`json`, `math`,
   `pathlib`, `re`, `yaml`, `ZONE_KC`, `_ROOT`, `_module_instance`, ...), no dead helper, no test
   that is vacuous or duplicated, docstrings true, fixtures realistic.
5. **Upstream hygiene.** No tracker references anywhere in the diff or the 9 commit messages
   (`Eifel-Joe`, `#<n>` of ours, task/spec/plan names, branch names); nothing outside the intended
   files; black-clean shape; CRLF/LF sanity of added lines.
6. **The PR as one unit.** Would a maintainer reading the squashed diff understand each change from
   the code and comments alone? Anything that would make him ask "why"?

Owner-pending questions (do NOT re-report): the user-facing wording "derived from latitude only"
vs. elevation also entering (pressure, PyETO radiation); the German service-description phrasing;
the missing top margin of the card note; the outdated docs screenshot; `docs/usage-events.md` not
listing the calendar events.

## Report

- **Strengths** (brief).
- **Issues**, severity **Critical / Important / Minor**, each with `file:line` at `88d210a8`, what is
  wrong, a concrete scenario, and a concrete fix. Only real findings; "none" where empty.
- **Assessment:** `READY FOR PR` | `READY AFTER MINOR FIXES` | `NOT READY`.
