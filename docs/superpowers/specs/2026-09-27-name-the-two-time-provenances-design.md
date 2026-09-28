# Name the two time provenances (PR 1 of the weather-buffer timezone work)

Revision 3 of `specs/2026-09-21-weather-buffer-aware-time-design.md`. That document's
R2-4 asked the maintainer how to cut the work. **He answered on 2026-09-23** and the
answer is binding, so this document exists to record PR 1's own scope rather than let
it be inferred from a spec written before the answer.

Everything R2-1 through R2-3 of the old spec measured still stands and is **not
repeated here**.

## What the maintainer decided (2026-09-23, his words)

> **Two PRs, please, in the order you proposed.**
>
> 1. **First, the behaviour-preserving one:** every entry point (`select_window`,
>    `aggregate_window`, `build_hourly_rows`, `build_substeps`, the live estimate's
>    `now`) accepts both kinds and coerces each by its own provenance. It stands on
>    its own as a robustness fix, it changes no number, and it is reviewable in
>    isolation. It is also what makes the second PR's diff honest.
> 2. **Then the switch-over:** writers to `dt_util.now()`, the migration, and the
>    fixtures reclassified.

and the requirement that was **not** in the old plan:

> So the distinction should be **named in the code**, not just moved: a helper per
> provenance (or one helper with a required provenance argument), so that a future
> reader cannot coerce a forecast row as if it were a buffer stamp. Please make PR 1
> carry that vocabulary, so PR 2 only has to use it.

## Why the started work is not continued

The WIP branch `fix/weather-buffer-aware-time` (`c17a8111`, `c9720a72`) was built on
**2026-09-21, 21:07 and 21:45** — before that answer. It does the **flip**: writers,
migration and readers together, which is PR 2. Its own second commit message says the
second provenance is unresolved.

Three reasons it is left standing as a source of ideas rather than rebased:

1. **It is the wrong cut.** PR 1 must change no number; the WIP changes writers.
2. **`as_stored_aware` does not satisfy the requirement.** It is one helper whose
   provenance is *implied by its name* — no argument, nothing forcing a caller to say
   which kind of stamp it holds. That is precisely the shape the maintainer ruled out.
   The injectable `_process_timezone()` inside it is worth keeping.
3. **Its base is 19 commits behind**, and two of those merges (`10bb8077`, `e8a3ef8f`)
   rewrote `live_estimate.py` by +499/−34 — the file the WIP edits by 60 lines.

## The inventory, measured on `1c071cf0`

This is the part the old spec called for and did not finish. Every entry point, every
input, and the provenance that input actually has.

### The finding: one parameter, both provenances, and nothing says so

`now=` on `aggregate_window` / `build_hourly_rows` / `build_substeps` carries
**opposite** meanings depending on the caller — and not merely per file. Inside
`live_estimate.py` alone, one function is called both ways:

| call site | what `now` is | provenance |
|---|---|---|
| `calculation.py:337` (`aggregate_window`), `:844` (`build_substeps`) | `datetime.now()` (`:267`, `:432`, `:498`, `:911`) | **process**-local naive |
| `live_estimate.py:1300`, `:1742` → `_aggregate_live_window(now=now_local)` → `:578` | `inputs["now"]` = `dt_util.now().replace(tzinfo=None)` (`:251`, `:262`) | **HA**-local naive |
| `live_estimate.py:616` → `_aggregate_live_window(zone, anchor)` — **no `now` passed** | falls through to the default `datetime.datetime.now()` (`weather_aggregate.py:337`) | **process**-local naive |

The third row is the one that shows this cannot be fixed by convention: the same file,
the same helper, and the provenance depends on whether an optional argument was passed.

### Per entry point

| entry point | input | provenance today |
|---|---|---|
| `select_window` (`weather_aggregate.py:130`) | each row's `RETRIEVED_AT`, via `_parse` (`:102`) | **store** — `_parse` coerces nothing, naive stays naive |
| | `watermark` (zone `last_consumed_at`) | **store** |
| `aggregate_window` (`:308`) | `now` | **both**, see above |
| `build_hourly_rows` (`:835`) | `now` | **both** (`calculation.py:787` via `hourly_eto_priced`; `live_estimate._buffer_hourly_et`) |
| `build_substeps` (`:1033`) | `now` | **both** |
| the live estimate's `now` (`live_estimate.py:251/262`) | `dt_util.now()` stripped to naive | **HA**-local |
| `_parse_local_naive` (`:192`) | stored `last_calculated` / `last_updated` | **store** (process-local) — but the function is *named and written* for HA-local, and converts an aware value with `dt_util.as_local`. This is the defect in one function. |
| `_resolve_hourly_forecast` (`:303`), `_read_hourly_forecast` (`:407`) | row times at `:448`, `:488`, `:523`: `dt_util.as_local(when).replace(tzinfo=None)` | **client / HA**-local — correct today, and must stay so |

### The third thing, which is not a stamp at all

`calculation.py:780-781` derives

```python
offset = dt_util.now().utcoffset()
tz_offset_h = offset.total_seconds() / 3600.0 if offset else 0.0
```

and hands it to `SiteGeometry(..., tz_offset_h, tz)` in the same call whose `now` is
`datetime.now()` — **process**-local. So the solar-time correction reads a
process-local stamp against HA's offset. That is the +23.5 % / −16 % radiation error
the old spec measured, and it is the expensive half.

**It cannot be fixed by making stamps aware**, because the offset does not travel as
`tzinfo`: it travels as the dict key `tz_offset_h` / `row["tz_offset_h"]`. A stamp that
becomes aware leaves this arithmetic untouched and the suite green. PR 1 therefore has
to name this input's provenance too, even though PR 1 does not change its value.

## The direction of the coercion, which is what makes PR 1 behaviour-preserving

"Accepts both kinds" does **not** mean "makes everything aware". Today every stamp on
these paths is naive and every comparison is naive-against-naive; turning any of them
aware would raise `TypeError: can't compare offset-naive and offset-aware datetimes`
in the very code the old spec measured 222 swallowed instances of. That is a number
change in the worst way — a silently disabled feature.

So PR 1 normalises **to the naive form each path already uses**, per provenance:

| input is | store provenance | client / HA provenance |
|---|---|---|
| naive | unchanged | unchanged |
| aware | converted to the **process** zone, then stripped | `dt_util.as_local(...)`, then stripped — which is literally what `live_estimate.py:448/488/523` already do |

For all existing data the naive row is the only one taken, so **nothing moves**. What
changes is that an aware value no longer detonates — and an aware value is exactly
what PR 2 starts writing. That is the whole reason the maintainer wants this first:
after it, PR 2's writers can flip without every reader becoming a test change.

The inverse asymmetry is the point of naming the provenances: stripping a stored stamp
to process-local and a forecast row to HA-local are different operations, and doing
either one to the other kind is the defect.

## Decisions

| # | Decision | Rejected |
|---|---|---|
| E1 | **Two named provenances as an enum-like vocabulary**, and one coercion function that takes it as a **required** positional argument. `coerce_stamp(value, provenance)` with no default, normalising in the direction above. | Two separate helpers. Rejected because the call sites that need *both* (the `now=` parameter) would have to choose at the call site anyway, and one function with a required argument makes the omission a `TypeError` at import-time-adjacent call sites rather than a silent default. Also: a single function is one place to put the reasoning. |
| E2 | **The provenance is named where the value is PRODUCED, not where it is consumed.** The four entry points keep their signatures exactly. Each coerces the inputs whose provenance it *owns* (row `RETRIEVED_AT` and `watermark` are always store; forecast row times are always client). `now` is coerced by its caller, which is the only place that knows: `calculation.py` with STORE (it is the process clock), `live_estimate.py` with CLIENT. The entry points' own `now=None` default becomes an explicit `coerce_stamp(datetime.now(), STORE)`. | **A required `now_provenance=` keyword on the four entry points.** Measured before rejecting: `now=` appears **94 times across 9 test files** (78 call sites to these functions). A required keyword is ~94 test edits in the PR whose whole point is that it changes no number and reviews in isolation — the maintainer expected the *second* PR to be "large only in tests". The guarantee he asked for is delivered by the required argument on `coerce_stamp` plus every naive-producing site naming its kind, not by a fifth parameter. |
| E2a | **An aware `now` that arrives unnamed is normalised to the frame of the rows it will be compared against** (store), with that reasoning in the code. This is what makes the entry point total without a new parameter. | Raising on it. Rejected: the caller that would raise is the live estimate, whose blanket `except` turns a raise into the feature silently going unavailable — the exact failure mode the old spec measured 222 instances of. |
| E3 | **`tz_offset_h` is documented as a provenance-bearing input and left numerically alone.** PR 1 records that it must agree with the stamp it is applied to; PR 2 makes them agree. | Correcting it in PR 1. Rejected: it changes a number, which PR 1 may not. |
| E4 | **Behaviour-preserving means measured, not asserted:** the gate is an empty name diff on the full suite against the `1c071cf0` baseline, plus the existing numeric assertions untouched. | Trusting review. |
| E5 | `_parse_local_naive` is **renamed** to say which provenance it serves, and its docstring's false claim ("The store writes these as naive *local* datetimes") is corrected to "process-local". No behaviour change: it keeps doing exactly what it does today. | Fixing its behaviour in PR 1. That is PR 2 — this one only stops the name and the comment lying. |

## What PR 1 explicitly does NOT do

- **No writer changes.** No `datetime.now()` becomes `dt_util.now()`.
- **No migration**, no `STORAGE_VERSION` bump.
- **No fixture reclassification** beyond what a signature change forces.
- **No `exc_info=True`** on `_intraday_for_zone` — greenlit separately as its own
  one-liner and tracked on its own issue, deliberately kept out of this diff.
- **No number changes anywhere**, including `tz_offset_h`.

## End-to-end criterion

A test that feeds the **same** aware instant into both provenances and asserts the two
naive results are the UTC offset apart — failing on today's code, which has no
vocabulary to express the difference. Plus an entry-point test that hands
`select_window` an aware `RETRIEVED_AT` and an aware watermark: today that raises
`TypeError`, afterwards it splits the window exactly as the naive equivalent does.

And the operational gate for "changes no number": the full suite's name diff against
the `1c071cf0` baseline is **empty**, and the passed count rises by exactly the number
of tests added, counted by definition.

## A latent defect this PR deliberately does NOT fix, and must not hide

The live estimate passes an **HA**-local `now` into `aggregate_window` while the rows it
is compared against carry **process**-local `RETRIEVED_AT`. On a container without `TZ=`
those two frames are the whole UTC offset apart *today* — this is the elapsed-window
error the original report describes, and it is live on master.

PR 1 makes that mismatch **visible in the code** (two named provenances meeting in one
comparison) without changing which frame either side uses. PR 2 is what removes it, by
making both ends aware. Stating this here so that a reader of PR 1 does not mistake
"the provenances are now named" for "the frames now agree".
