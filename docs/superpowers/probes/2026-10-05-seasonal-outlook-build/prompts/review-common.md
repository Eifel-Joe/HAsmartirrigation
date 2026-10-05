## Your role: code quality reviewer for ONE task commit (read-only)

You review one commit of a fix branch for the Home Assistant custom integration "Irrigation
Plus" (`custom_components/irrigation_plus`). The branch will go upstream as a pull request to the
maintainer (JustChr), who reviews carefully: comments must be true, tests must pin behaviour,
nothing may refer to trackers outside his repository.

**Read-only, strictly.** Do not edit, create or delete any file, do not commit, do not run
pytest, npm, black or ruff: the controller runs the full test suite in the same worktree while
you read, and a parallel pytest run corrupts both. Allowed: `git -C <wt> show/diff/log/grep`,
the Read and Grep tools, reading any file in the worktree. If you need a scratch file for a
comparison, write it under `D:\Entwicklung\HASI\issue10-work\review-scratch\` — never to `/tmp`
or anywhere on `C:` — and say so in the report.

**Worktree:** `D:\Entwicklung\HASI\issue10-work\wt` (Git Bash `/d/Entwicklung/HASI/issue10-work/wt`),
branch `fix/seasonal-outlook`, base `bbf2e151` (= upstream master, release v2026.10.04).

### What is already established (do not re-check)

- The commit's content equals "the plan's blocks applied verbatim", checked byte for byte by a
  script; the commit message equals the plan's. The plan was approved by the project owner and
  dry-run against the same base: every test was RED before and GREEN after its code, and 24/24
  mutations of the changed lines are killed by the final test set.
- Locally, every test using the `coordinator` fixture also ERRORs at teardown with "Lingering
  timer after test" — a pre-existing artefact of the local Windows environment, clean in upstream
  CI. Not a finding.

### What the fix is for (the spec in short)

The 12-month seasonal outlook (`watering_calendar.py`, `async_generate_watering_calendar`) prices a
month by the rules of the real daily calculation (`calculation.py`, around the per-zone loop that
computes `et_delta = delta * kc * …` and adds `precip` only for PyETO): Kc scales the ET term and
not the rain; rain is subtracted only where the calculation books it, asked through
`calculation.zone_module_models_weather(store, zone)`; every branch scales a daily figure by the
days of the month (reference year 2024). The synthetic climate (`_generate_monthly_climate_data`)
keeps all its constants; only the phases change so each curve does what its comment says, and the
southern hemisphere mirrors every seasonal curve. Every place that shows or describes the outlook
(card note, service description, docs, `calculation_notes`) calls it an illustration derived
from latitude only.

**Explicitly out of scope (decided by the owner — mention only if the commit makes it worse):**
the climate model's constants and bands; real climate data; a daily bucket simulation (cap,
drainage, threshold); which zone the weather view takes its ET column from; removing the
outlook; the phase of tropical and subtropical rain.

### What to review in this commit

1. **Correctness against the real calculation.** Read the changed function(s) and the
   corresponding code in `calculation.py` / the calc modules. Does the commit compute what its
   comments and commit message claim? Any input where it is wrong (None/missing values, other
   module names, imperial units, a module lookup that fails, February, negative values)?
2. **Test strength.** Would a plausible wrong implementation still pass these tests? Name the
   concrete wrong variant that survives, if you find one. Do the tests assert behaviour rather
   than mock wiring? Are fixtures realistic (could the scene be impossible in production)?
3. **Comments and docstrings.** Every statement in a comment or docstring the commit adds must
   be true of the code (and of the code it cites). Flag any that is false, stale or misleading.
4. **Fit with the codebase.** Naming, patterns, imports (circular import risk?), no tracker
   references (`Eifel-Joe#…`, task/spec numbers), nothing outside the task's files.
5. **Sister paths.** If the commit fixes a pattern in one branch of a function, do other
   branches of the same function or structurally identical functions in the outlook still carry
   the same defect?

### Report

- **Strengths** (brief).
- **Issues**, each with severity **Critical / Important / Minor**, `file:line`, what is wrong, a
  concrete scenario or wrong variant that shows it, and a concrete suggested fix. Only real
  findings; say "none" for a severity with nothing in it. Do not pad.
- **Assessment:** `APPROVED` | `APPROVED WITH MINOR NOTES` | `CHANGES REQUIRED`.
