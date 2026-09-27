# Plan — the dry-run witness becomes evidence the sensor reported (`JustChr#174` rework)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** `JustChr#174` writes a self-closing run off as dry only when the meter
was in a position to say so: the sensor **reported** after the valve opened, the
meter **credited** at least one reading, and it **declined** none. Four measured
inputs that watered and are currently written off stop being written off; the
genuinely dry run is still written off.

**Spec:** `docs/superpowers/specs/2026-09-26-self-closing-fault-lifecycle-design.md`
§11 (§11.3 is the form, §11.2 the measured inputs, §11.4 the plumbing).

**Base:** `c5330c7f` (upstream/master). Branch
`fix-a-run-that-delivered-nothing-is-not-a-success`, worktree
`D:/Entwicklung/HASI/pr34-work/pr2`, already rebased to `9814f19b` (2 own
commits, 0 behind).

**Baseline to diff against:** `D:\Entwicklung\HASI\pr174-work\baseline-names.txt`
— 374 names, measured on `c5330c7f` in `pr174-work/base`
(7 failed / 3322 passed / 9 skipped / 367 errors).

**Test command** (from a worktree, no own `.venv`):
```
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock
```

**Tech stack:** Python 3.12, pytest + pytest-homeassistant-custom-component,
black, ruff.

---

## Task 1 — `FlowMeter.sample` takes the report time; `at` moves behind the `*`

Signature first, because `_read_flow_sample` growing a fourth element (Task 2)
would otherwise bind it to `at` at eight call sites.

- [ ] **Test** `tests/test_flow_meter.py`:
      `test_sample_takes_the_report_time_and_requires_at_by_keyword` —
      `m.sample(0.0, "L/min", None, reported_at=T, at=15.0)` is accepted, and
      `pytest.raises(TypeError)` for `m.sample(0.0, "L/min", None, 15.0)`.
- [ ] **RED:** `TypeError: sample() got an unexpected keyword argument 'reported_at'`.
- [ ] **Implement:** `def sample(self, value, unit, state_class, reported_at=None, *, at: float)`.
      Migrate the five positional `at` call sites in `tests/test_flow_meter.py`
      (the `_feed` helper at :17 and :182, :183, :415, :416) and the two in
      `custom_components/irrigation_plus/distributor.py` (:714, :737) to `at=`.
- [ ] **GREEN:** the new test passes; `tests/test_flow_meter.py`,
      `tests/test_distributor*.py` and `tests/test_self_closing.py` show no new
      failures.

## Task 2 — `_read_flow_sample` carries `state.last_reported`

- [ ] **Test** `tests/test_self_closing.py`:
      `test_the_flow_read_carries_the_states_report_time` — a state built with an
      explicit `last_reported`; assert `_read_flow_sample(...)[3]` is it.
- [ ] **RED:** `IndexError: tuple index out of range`.
- [ ] **Implement:** append `state.last_reported` to the returned tuple in
      `irrigation.py::_read_flow_sample`; extend its docstring to say the fourth
      element is the report time and why a re-read is not a report.
- [ ] **GREEN:** new test passes. The eight `meter.sample(*sample, at=…)` sites
      need no edit — verify by running `tests/test_self_closing.py`,
      `tests/test_observed_watering.py`, `tests/test_irrigation*.py`.

## Task 3 — the witness is a report, not a read

- [ ] **Test** `tests/test_flow_meter.py`, two cases:
      `test_a_state_that_is_read_again_but_never_reported_is_no_witness` (rate 0,
      the **same** `reported_at` on the seed and all four polls) → the flag is
      false; and `test_a_sensor_that_reports_anew_during_the_run_is_a_witness`
      (fresh `reported_at` per poll) → true. Both read through
      `metered_the_run()`.
- [ ] **RED:** `AttributeError: 'FlowMeter' object has no attribute 'metered_the_run'`.
- [ ] **Implement:** `_open_reported_at` / `_saw_report_after_open` in `__init__`
      and in `sample()` (baseline = first sample carrying a `reported_at`,
      evidence = strictly newer); delete `_saw_reading_after_open`,
      its `at > 0` assignment and `saw_reading_after_open()`; add
      `metered_the_run()` returning `_saw_report_after_open` only for now.
- [ ] **GREEN:** both new tests pass.

## Task 4 — `_priced` and `_declined` complete the witness

- [ ] **Test** `tests/test_flow_meter.py`, one case per §11.2 row, each with a
      fresh `reported_at` per poll so only the accounting can fail it:
      `test_a_rate_gap_the_meter_will_not_integrate_is_not_a_dry_run`
      (12 L/min live every 75 s, `max_gap_s=60`),
      `test_a_totalizer_that_fell_back_and_climbed_is_not_a_dry_run`
      (`100 → 60, 70, 80, 90`),
      `test_a_post_reset_climb_above_near_zero_is_not_a_dry_run`
      (`45 → 8, 20, 30, 40`, `saw_reset()` false — the row `saw_reset()` misses),
      and `test_a_dry_cistern_that_was_measured_is_still_a_dry_run`
      (rate 0 every poll) as the control that must stay **true**.
- [ ] **RED:** the first three report `metered_the_run() is True`.
- [ ] **Implement:** `_priced` in `_sample_rate`'s in-gap branch and
      `_sample_totalizer`'s rising branch; `_declined` in `_sample_rate`'s `else`
      and unconditionally above `_sample_totalizer`'s near-zero `if`, with the
      `NOT-TO-DO` recording that `saw_reset()` depends on that placement;
      `metered_the_run()` becomes the three-term conjunction.
- [ ] **GREEN:** all four pass; the §11.2 probe rerun prints 0 of 3 false FAILED
      verdicts with the control still written off.

## Task 5 — the guard reads the new witness

- [ ] **Test** `tests/test_self_closing.py`:
      `test_a_run_whose_sensor_never_reported_keeps_its_time_based_credit` —
      drive a full self-closing run whose flow state is never re-reported;
      assert the recorded result is `completed`, the bucket is credited and no
      `flow_never_started` fault is raised.
- [ ] **RED:** recorded `failed` with the credit reversed.
- [ ] **Implement:** the guard in `_sc_finish_flow` becomes
      `if d is not None and d <= 0 and not meter.metered_the_run():`; drop the
      `saw_reset()` term (§11.5) and rewrite the comment block above it to the
      three conditions.
- [ ] **GREEN:** new test passes.
- [ ] **Sister paths in the same file/commit:** the three existing dry tests
      (`test_a_live_but_dry_meter_reports_zero_not_nothing`,
      `test_a_sensor_that_died_after_the_open_read_is_not_a_dry_run`,
      `test_a_totalizer_that_reset_mid_run_is_not_a_dry_run`) must re-issue
      states with a fresh `last_reported` where they mean "the meter watched",
      or they pin the defect instead of the behaviour. Check each — the first
      one is the test the maintainer named.

## Task 6 — no reference to our own issues anywhere in the diff

- [ ] Strip `Eifel-Joe#…`, bare `#3`/`#4`, `spec §…`, `Task …`, `PR 1/2` and any
      branch SHA from test docstrings, code comments and `docs/usage-events.md`.
      Describe the defect in words instead. Upstream numbers (`#139`, `#173`,
      `#165`) stay — they resolve in his repository.
- [ ] **Check A (diff):** `git diff c5330c7f..HEAD | grep -nE 'Eifel-Joe|spec [0-9§]|Task [0-9]'` is empty.
- [ ] **Check B (commit messages, the one forgotten last time):**
      `git log c5330c7f..HEAD --format='%s%n%b' | grep -nE 'Eifel-Joe|spec [0-9§]|Task [0-9]'` is empty.

## Task 7 — full suite, name diff, lint

- [ ] Full suite in `pr34-work/pr2`; extract names with
      `grep -E '^(FAILED|ERROR) tests/' | sed 's/ - .*//' | sort`.
- [ ] `diff` against `pr174-work/baseline-names.txt` must be **empty**. Only the
      full run with the name diff decides; a subset decides nothing.
- [ ] `uvx black custom_components/irrigation_plus/` and
      `uvx ruff check custom_components/irrigation_plus/` clean.

## Task 8 — mutation matrix

- [ ] One mutation per new decision: each of the three terms in
      `metered_the_run()` inverted/dropped, `_priced` moved into the seed path,
      `_declined` moved below the near-zero `if`, the `reported_at >` comparison
      weakened to `>=`, the baseline taken from the last rather than the first
      report, and the guard's `<= 0` narrowed to `== 0`.
- [ ] Each mutation reverted with `git checkout -- <file>`, never by
      back-substitution. A mutation that kills nothing is investigated as a
      possibly-dead term (as `saw_reset()` turned out to be), not papered over
      with an invented test.

## Task 9 — the reply, then the push

- [ ] Draft the PR comment: the apology for the cross-repo references first,
      what changed, §11.2's table, and the deviation on his "use GitHub
      issue/PR numbers instead" — the references come out entirely rather than
      being substituted. State that the secondary point (planned volume below
      `FLOW_CAL_METER_RESOLUTION_L`) is not built.
- [ ] Show the comment text and the rewritten commit messages in chat and get
      approval **before** any `git push` or `gh` call.
- [ ] `git push --force-with-lease` (the rebase he asked for), then the comment.

## Out of scope

- The classic runner's copy of §11.2 row 3 and of the dead-after-seed case —
  pre-existing, different credit mechanics, own issue (§11.5).
- The optional secondary review point: a planned volume below
  `FLOW_CAL_METER_RESOLUTION_L`.
- `Eifel-Joe#53` inheriting this form — its own session after this lands.
- `run_chain.py`, `calculation.py`, `scheduler.py` — other PRs own them.
