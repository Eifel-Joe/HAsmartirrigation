# Mutation matrix — an external run reaches the chain

Task 8 of `2026-09-28-external-run-reaches-the-chain.md`. Every line this branch added
must have a test that dies without it. Two of the plan's tests were known to be green on
the base, so the matrix is the only thing that shows they carry weight.

Runner: `docs/superpowers/probes/2026-09-28-external-run-mutations.py`
Result data: `mutations.json` (same run).
Branch: `fix-an-external-run-reaches-the-chain` on `upstream/master` = `e42d0a69`.

**Result: 16 applied, 16 killed, 0 survived.** Every source restored byte-for-byte.

## The run was real

A matrix is worthless if the run collected nothing — a file missing from the suite list
once turned a broken run into a clean-looking "0 killed, 12 survived". Two guards, both
checked this time:

- the suite list was verified against `grep -rl "def <test>" tests/` for **every** test
  named as a killer below, before any result was trusted;
- the runner prints the collection line and refuses to continue on `collected 0`. The
  reference run reported `collected 102 items` and **0 pre-existing failures**, so every
  "killed" below is a test that genuinely flipped from green to red.

Kills are measured as a set difference against that reference, so a pre-existing failure
can never be miscounted as a kill.

## The matrix

| # | file | mutation | result | killed by |
|---|---|---|---|---|
| 1 | `run_state.py` | the fourth source always answers `False` | **killed** | both open-window chain tests, `test_an_open_external_run_counts`, `test_the_narrow_question_ignores_an_external_run` |
| 2 | `run_state.py` | drop the ceiling comparison (`return started is not None`) | **killed** | `test_an_external_run_past_its_ceiling_does_not_count`, `..._exactly_at_its_ceiling_...` |
| 3 | `run_state.py` | ceiling `<` becomes `<=` | **killed** | `test_an_external_run_exactly_at_its_ceiling_does_not_count` |
| 4 | `run_state.py` | the wide answer drops the fourth source | **killed** | both open-window chain tests + both predicate tests |
| 5 | `observed_watering.py` | the open edge asks the WIDE question again | **killed** | `test_the_open_edge_tracks_a_second_external_open_of_the_same_zone` |
| 6 | `run_state.py` | the narrow answer drops the distributor source | **killed** | `test_distributor_cycle_counts_for_its_members` (pre-existing) |
| 7 | `observed_watering.py` | drop the provenance gate (always drop the zone) | **killed** | `test_a_few_seconds_of_hand_testing_keeps_the_zones_turn` |
| 8 | `observed_watering.py` | invert the provenance gate | **killed** | both closed-window chain tests + the counter-case |
| 9 | `observed_watering.py` | never tell the chain at all | **killed** | both closed-window chain tests |
| 10 | `observed_watering.py` | `finally:` becomes a plain trailing `await` | **killed** | `test_the_calculation_is_picked_up_even_if_the_credit_raises` |
| 11 | `observed_watering.py` | ceiling returns `maximum_duration` without the margin | **killed** | 11 tests |
| 12 | `observed_watering.py` | `substituted` is always `False` | **killed** | 10 tests |
| 13 | `observed_watering.py` | the wrapper drops the measured volume | **killed** | `test_the_finish_hands_the_credit_everything_the_close_edge_measured` |
| 14 | `observed_watering.py` | the wrapper drops `sensor_present` | **killed** | as 13 |
| 15 | `observed_watering.py` | un-harden the ceiling read (no `float` coercion) | **killed** | the two non-numeric maximum tests |
| 16 | `observed_watering.py` | the close edge drops the measured volume | **killed** | `test_close_edge_credits_measured_flow_end_to_end` |

## What the matrix actually caught

The plan listed twelve mutations. Four more (13–16) were added because the work itself
created the seams they test, and two of those found real holes **before** the matrix ran:

- **Mutant 5 survived the first time it was tried.** The test written to guard the
  narrow/wide split at the open edge asserted that `_observed_on_since` held an entry —
  an entry the test had seeded itself. It held in the broken state too, so the whole
  suite stayed green with the defect restored. Rewritten to seed a **stale** stamp and
  assert this open refreshed it, which is the only observable difference between "the
  edge stamped this open" and "the edge bailed out".
- **Mutants 13/14 came out of a fixture retarget.** When the close-edge test moved its
  mock from `_credit_observed_watering` to the new wrapper, nothing was left watching what
  the wrapper passes *onward*. Measured: dropping `measured_l` inside the wrapper left 86
  tests green, while silently turning a flow-measured credit into a time-based estimate.
  Pinned by asserting the whole forwarded call, so all four arguments are covered.

Both were found by mutating rather than by reading. Neither would have been caught by the
plan's original twelve.

## Mutant 3, the one that had to be earned

The plan predicted nothing would catch `<` → `<=` and allowed the boundary to be
documented as unobservable. It survived the first run, as predicted.

That was not accepted, for the project's reason: a survivor is a weak test before it is a
harmless mutation, and an argument is not a measurement. The boundary **is** observable —
it is one instant wide, so it needs a stopped clock, not a different design. Pinned with
`freeze_time` at exactly `maximum_duration + margin`.

Worth the test rather than a paragraph, because the two lines this work added fall on
**opposite** sides and nothing else says so:

- the provenance gate is **inclusive** (`seconds >= 300`) — a run of exactly five minutes
  is watering, and its other direction was already pinned in the observed suite;
- the run ceiling is **exclusive** (`elapsed < ceiling`) — a run that has reached the
  longest plausible length for its zone has reached the point where the report stops being
  evidence of water. This matches `_self_closing_run_in_flight`, which the bound is
  modelled on and which uses `<` for the same reason.

An asymmetry that deliberate should not rest on nobody having tried the other value.
