# Name the two time provenances — Implementation Plan (PR 1)

Spec: `specs/2026-09-27-name-the-two-time-provenances-design.md` (revision 3 of the
2026-09-21 design). **Nothing from the spec is repeated here.**

## The base

| | |
|---|---|
| base commit | **`1c071cf0`** = `upstream/master`, and it contains `10bb8077` and `e8a3ef8f` (both verified as ancestors), which the maintainer required |
| branch | `fix/name-the-two-time-provenances`, worktree `D:/Entwicklung/HASI/issue22-work/wt` |
| baseline | **374 non-green names** — reused from `issue53b-work/baseline-1c071cf0.txt`, same commit, same environment, measured today |
| the WIP left standing | `fix/weather-buffer-aware-time` (`c9720a72`), base `965a4f9d`, **not** rebased — see the spec for the three reasons |

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock
grep -E '^(FAILED|ERROR) tests/' <run>.txt | sed 's/ - .*//' | sort
```

## File structure

| file | what changes |
|---|---|
| `custom_components/irrigation_plus/helpers.py` | the vocabulary: two provenance constants, `coerce_stamp(value, provenance)`, the injectable `_process_timezone()` |
| `weather_aggregate.py` | `_parse` names its provenance; the three `now=None` defaults become explicit; `select_window` becomes total for aware input |
| `live_estimate.py` | `_parse_local_naive` renamed and its docstring corrected; the three forecast conversions go through the vocabulary; the live `now` is named CLIENT at its producer |
| `calculation.py` | the process clock is named STORE where it is produced; the `tz_offset_h` derivation gets the provenance note |
| `tests/test_time_provenance.py` | new |

**No writer changes. No migration. No `exc_info=True`.** Those are PR 2 and a separate
one-liner.

---

### Task 1: the vocabulary

- **Test file:** `tests/test_time_provenance.py`
- **RED:**
  - `test_the_same_instant_coerces_differently_per_provenance` — one aware instant,
    both provenances, the two naive results are the UTC offset apart. RED: no such
    function.
  - `test_a_naive_value_is_returned_unchanged_under_either_provenance` — this is what
    makes the change behaviour-preserving, so it is a test and not a claim.
  - `test_coercing_without_naming_a_provenance_is_an_error` — `TypeError`. This is the
    maintainer's actual requirement, so it gets its own test.
  - `test_an_unusable_value_is_no_stamp_rather_than_a_raise` — None / a non-date string
    → None, because this runs inside a blanket `except` whose raise means the feature
    silently goes unavailable.
- **Implementation:** `helpers.py`. `_process_timezone()` stays its own function so the
  suite can substitute it — `time.tzset()` does not exist on Windows, and a test that
  only runs on CI is one we never watch go red-to-green ourselves. (Carried over from
  the WIP; it is the one piece of it that survives.)
- **GREEN:** all four pass; full suite untouched (nothing calls it yet).

### Task 2: `select_window` and `_parse` name the store provenance

- **Test file:** `tests/test_weather_aggregate.py`
- **RED:** `test_select_window_accepts_an_aware_retrieved_at` — an aware `RETRIEVED_AT`
  and an aware watermark split the window exactly as the naive equivalent does.
  RED on today's code with `TypeError: can't compare offset-naive and offset-aware`.
- **Implementation:** `_parse` coerces with STORE and says why in one line.
- **GREEN:** the new test passes and `test_weather_aggregate.py` is otherwise unmoved —
  every existing row is naive, so nothing moves.

### Task 3: the three `now=None` defaults stop being implicit

- **Test file:** `tests/test_weather_aggregate.py`
- **RED:** `test_an_aware_now_is_read_in_the_frame_of_the_rows` — pass an aware `now`
  to `aggregate_window`; today it raises.
- **Implementation:** `aggregate_window`, `build_hourly_rows`, `build_substeps`:
  `now = now if now is not None else coerce_stamp(datetime.datetime.now(), STORE)`,
  plus the spec's E2a note on why an unnamed aware `now` is read in the rows' frame.
  **No signature change** — the 94 `now=` sites in 9 test files are the measured reason.
- **GREEN:** new test passes, name diff still empty.

### Task 4: the live estimate's two provenances are named at their producers

- **Test file:** `tests/test_live_estimate_from_buffer.py`
- **RED:** `test_a_forecast_row_is_read_in_HA_local_and_a_stored_stamp_is_not` — one
  test, both kinds, through the real reader. RED: today one rule is applied to both.
- **Implementation:**
  - `_parse_local_naive` → renamed to name the store provenance, docstring's false
    claim ("the store writes these as naive *local*") corrected to process-local.
    **Behaviour unchanged** — it keeps doing exactly what it does today.
  - the three `dt_util.as_local(when).replace(tzinfo=None)` sites (`:448`, `:488`,
    `:523`) go through `coerce_stamp(..., CLIENT)`, which is the same operation with a
    name on it.
  - `inputs["now"]` is produced with the CLIENT name at `:262`.
- **GREEN:** new test passes; `test_live_estimate*.py` otherwise unmoved.

### Task 5: the `tz_offset_h` mismatch is named, not fixed

- **Test file:** none — this task adds no behaviour.
- **Implementation:** a comment at `calculation.py:780` recording that the offset is
  HA's while the `now` in the same call is process-local, that the offset travels as a
  dict key rather than as `tzinfo` so making stamps aware does **not** fix it, and that
  PR 2 is what makes the two agree.
- **GREEN:** `black`/`ruff` clean, name diff empty. Verified by reading, not by a test —
  and said so here rather than inventing one.

### Task 6: full suite, name diff, lint

Expectation: name diff **empty**; passed = 3366 + the tests added, counted by
definition. `black` and `ruff` clean.

### Task 7: mutation matrix

At minimum: drop the provenance argument's requirement (give it a default) · coerce
STORE where CLIENT belongs and the reverse · make `coerce_stamp` return an aware value ·
make it strip a naive value to the other frame · remove the `_parse` coercion · remove
each of the three `now` defaults.

⚠️ **Verify the run collected tests before reading any verdict.** A missing path makes
pytest abort with `no tests ran`, and every mutation then reads as SURVIVED — which
happened on this branch's sibling work today and would have been read as twelve
uncovered lines.

### Task 8: the three reference checks

Chained with `;`, never `&&`. Diff **0**, messages **0**, per commit exactly **1** (the
`Author:` line). Plus a scan of the **added** lines only for `#NNN`, branch SHAs and doc
shorthand.

## After the plan

1. Review, then the live question: PR 1 changes no number, so there is nothing to
   observe on an instance. **State that rather than staging a live test that cannot
   fail** — the honest verification is the empty name diff plus the aware-input tests.
2. Archive spec + plan onto `archive/design-history` (rule P1).
3. Push / PR / issue comment — each needs chat approval. The PR body must say: no number
   changes, the provenance vocabulary is the point, `now`'s signature deliberately
   unchanged with the 94-site measurement as the reason, and that the live estimate's
   frame mismatch is made visible but **not** fixed here.

---

## Measured results (2026-09-28)

Submitted as [`JustChr#177`](https://github.com/JustChr/HAsmartirrigation/pull/177).
Six commits on `1c071cf0`, branch `fix/name-the-two-time-provenances`.

### Suite

| | base `1c071cf0` | branch |
|---|---|---|
| | 7 failed / **3366** passed / 9 skipped / 367 errors | 7 failed / **3384** passed / 9 skipped / 367 errors |
| non-green names | 374 | 374 — **`diff` empty** |

`+18` counted by definition: 6 (vocabulary) + 3 (buffer reader) + 3 (three entry points)
+ 3 (live estimate's two provenances) + 3 (through the forecast readers) + 0 (Task 5).
The empty name diff **is** the operational proof of "changes no number".
`black` clean, `ruff` clean. Files: `issue22-work/{branch-run2,branch-names2}.txt`.

### Mutation matrix — 11 mutations, 11 killed

Driver `scratchpad/mutate_tz.py`; verdicts in `issue22-work/mutations.json`.

Two are worth recording:

- **T6, rewriting a naive value instead of passing it through, kills 44 tests.** That is
  the hard evidence for behaviour-preservation. "Nothing moves" is not a claim in the PR
  body; it is 44 tests.
- **T10, swapping the forecast rows' provenance, SURVIVED the first pass.** The
  vocabulary had tests, but they exercised `coerce_stamp` **directly** — nothing drove an
  *aware* row through the three call sites, which sit behind an `if when.tzinfo is not
  None` guard that no existing fixture trips. A test that exercises the coercion proves
  the coercion and says nothing about which one the call site chose. Exactly
  `verification-must-exercise-the-change`, walked into. Closed with three tests through
  the real readers (`_hourly_forecast_precipitation`, `_hourly_forecast_temperatures`),
  after which T10 dies.

### Corrections to this plan, made while executing it

1. **Task 4's RED expectation was wrong.** It said a test asserting "a stored stamp is
   not read in HA-local" would be RED and then GREEN. It is RED today — but making it
   green **is** the behaviour change PR 1 may not make. Task 4 became a
   **characterisation**: the rename, the corrected docstring, and a test pinning today's
   reading beside what the store provenance would say, so the later inversion is a
   decision rather than drift.
2. **Task 2 was committed with a lint failure.** `ruff` reported
   `F401 parse_datetime imported but unused` and only `tail -1` of its output was read.
   Amended. Lint is now checked by grepping for `All checks passed!`, not by eyeballing
   the last line.

### Reference checks

Added lines **0**, messages **0**, per commit exactly **1** (the `Author:` line), no doc
shorthand and no SHAs in added lines. The PR body checks clean too; the only numbers in
it are `#167`/`#168`, which are the maintainer's own and which he named as the base.

### No live test, stated rather than staged

PR 1 changes no number, so there is nothing an instance could show that the empty name
diff does not. The aware-input tests are the verification. PR 2 is the one that needs a
live run, and its notes lead with the clearness-ratio radiation error.
