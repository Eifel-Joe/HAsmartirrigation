# Sister paths — what the wider answer changed at every call site

Task 6 of `2026-09-28-external-run-reaches-the-chain.md`. The predicate
`zone_run_in_flight` gained a fourth source, so **every** reader of it now sees a
different answer while an external valve is open. Only two readers were the target.
This is the record of judging the rest.

Measured on the branch after the rebase onto `upstream/master` = `e42d0a69`, with

```bash
grep -rn "zone_run_in_flight\|_si_run_in_flight" custom_components/irrigation_plus/*.py
```

## The plan said nine sites. There are ten.

The plan was written against `6acfc819`. JustChr then merged four PRs and the base moved
to `e42d0a69`. `run_chain.py` was restructured by `#176` ("a second dispatch joins the
running cycle instead of replacing it"), which **added a call site** and moved the other
two. Re-running the grep on the real base rather than trusting the plan's line numbers is
what found it.

| site | what the wider answer does there | wanted? |
|---|---|---|
| `batch.py:226` | the zone is left out of the batch plan | yes — single-flight backstop, wants the wide answer |
| `calculation.py:510` | a calculation during an external run is deferred | yes — and the deferral now has an owner on the external path |
| `irrigation.py:1092` (scheduled dispatch) | a zone whose valve is open externally is skipped | yes — this is the defect being fixed |
| `irrigation.py:3413` (`run_zone` / Irrigate-now) | refused while the valve is open externally | yes, but **user-visible** — see below |
| `observed_watering.py:142` | asks the NARROW question | the split itself |
| **`run_chain.py:390` (`_chain_join`)** | **NEW SITE.** A second dispatch does not queue a zone whose valve is open externally | yes — see below |
| `run_chain.py:504` (sequential, at the turn) | the zone is dropped from the cycle | yes — target |
| `run_chain.py:838` (rotating, at the turn) | the remainder is written off | yes — target |
| `run_state.py:245` | a deferred calculation stays deferred while the valve is open | yes — bounded by the ceiling, so it cannot park for ever |
| `self_closing.py:695` | a second self-closing dispatch is refused | yes — single-flight backstop |

## The new site, judged

`_chain_join` appends zones to a **live** queue when a second dispatch arrives mid-cycle.
Its own docstring already says the quiet part: *"A zone whose valve is open right now is
not queued behind itself — and `state.zones` no longer mentions it, because a sequential
cycle pops a zone before dispatching it, so `zone_run_in_flight` is the only thing that
can tell."*

That sentence is still true and now simply covers more: "open right now" has come to
include an open nobody in here drove. A second dispatch arriving while a zone is being
watered externally leaves that zone out, which is the same judgement the two target sites
make. No change needed — the docstring was written generally enough to survive.

One asymmetry to be aware of, deliberate rather than overlooked: this site has **no
provenance gate**, so a brief hand-open that happens to coincide with a second dispatch
omits the zone from that dispatch. That matches the decision taken for the open window as
a whole (global, no threshold); only the close edge is gated at the provenance line. The
reasoning is in the design doc: while the valve is actually open, dispatching onto it is
the defect, whatever the open's provenance.

## The one that is user-visible

`irrigation.py:3413` is `run_zone`, the documented manual service — and the one used for
weather-independent live testing. It now refuses while the zone's valve is open
externally, with an INFO log and nothing else, for up to `maximum_duration + 30 s`. That
is consistent with the refusal that already existed for the integration's own runs, and
dispatching onto an open valve is exactly the defect. But a user who does not connect the
refusal to the tap they just opened will find it surprising, so it belongs in the pull
request body rather than being discovered.

## Two comments whose reasoning stopped short

Not code defects — the code is right at both — but this codebase's house style is that a
comment carries the argument, and these two arguments no longer reach the case the fourth
source made reachable. Both fixed in `fix(chain): name the external run in the two
comments that reason about runs`.

1. **`run_chain.py`, the rotation write-off.** It justified handing the live-estimate
   marker back with *"a run's ceiling is decided once, at its own dispatch, and frozen
   into its record"*. An external run has **no record and no frozen ceiling**, so the
   argument was silent about the trigger that now fires it. The action is still safe, for
   a different reason: what is handed back is the rotation's own leftover, which belongs
   to a run that will not happen.

2. **`calculation.py`, the deferral.** It justified giving way with *"Every run path
   settles the bucket from an anchor captured before the valve opened"*. The observed path
   does not: it credits a **delta** read at the close (`old_bucket + applied_native`). The
   real hazard there is the mirror image — the calculation's own bucket write is absolute,
   so a calculation that read the zone before an external credit landed and wrote
   afterwards would erase it. The twin of this comment in `run_state.py` was corrected
   when the deferral got its owner; this is its sister.

## The subsystem that never asks — out of scope, own issue

```bash
grep -rn "zone_run_in_flight" custom_components/irrigation_plus/distributor.py
```

No output. The distributor sweep never asks the question at all, so an externally watered
**member** zone is invisible to it — the same defect one subsystem over, untouched by this
work because the sweep iterates a member snapshot rather than consulting the predicate.

Deliberately **not** widened here: it needs its own design decision (the sweep's snapshot
is taken at cycle start, so there is no single turn at which to ask), and widening it
would double the size of a pull request that is already two mechanisms. Recorded for a
separate issue, with the empty grep as the evidence.
