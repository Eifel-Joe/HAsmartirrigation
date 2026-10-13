### Spec Compliance
- ✅ Spec compliant. All steps 3-8 of the brief are in the diff. Signatures, import placement (ruff `I` order `.localize` < `.sensor_liveness` < `.weather_aggregate`), the gate body (calculation.py:396-428), the `blocked=blocked` pass-through at :473, the `async_calculate_zone` change (:647-652, :671-672), the two record skips (:713-714, :753-754) and the `_FakeStore.get_mapping` addition all match the plan text. Commit message and trailer match. No fork/spec/PR references in code or tests, except the oblique sentence noted under Minor.
- ⚠️ Cannot verify from the diff (other tasks): `calculate_module` does not receive `blocked` after this task (`calculation.py:660`). The plan assigns that to Task 5 (`calculate_module(..., blocked=None)`, plan line 1421), so it is not a gap here. The reviewer brief's "reaches ... the module calculation" is therefore only half-true at this commit: the module gets the cut aggregate but not the spans, and books the full-window multiplier until Task 5.
- ⚠️ Cross-task: after this commit the comments in `live_estimate.py:590-619` ("reduced exactly as `_aggregate_for_zone` will", "commit runs this same call") are untrue for pausing groups. Task 9 Step 2 fixes exactly those lines. The controller should make sure Task 9 stays in the sequence.

### Named risks, with evidence
- **Gate returns None in every listed case.**
  - `keep`: `group_pauses` False (:412). Legacy groups without the key also keep, per the `group_pauses` docstring (`sensor_liveness.py:176-182`). Test `test_a_group_that_keeps_is_not_cut`.
  - Hourly on: :414. Test `test_with_the_hourly_calculation_nothing_is_cut`. The gate's flag is the same `hourly_calculation_enabled` that `replayed_balance_applies` reads (calculation.py:151). The replay reconciliation in `_substeps_for_zone` (:1068-1075) can therefore only fire when the gate is already None.
  - No sensor group: :409-410. Group deleted: `get_mapping` returns None and the gate returns None at :412. Both covered by `test_a_zone_without_its_group_is_not_cut`.
  - No watermark: `coerce_stamp(None)` returns None (:416, :418). Tested with `watermark=None`. An unparsable watermark takes the same path, because `coerce_stamp` catches ValueError/TypeError and checks `isinstance` (helpers.py:1046-1051). Untested, but the path is the same.
  - `watermark >= now`: :418. Untested, and behaviourally redundant. `blocked_spans` already yields `hi <= lo` -> `{}` -> `blocked or None` -> None for an empty or inverted window, so the guard is a cheap duplicate. A mutation of it would survive; it is equivalent, not a hole.
  - Empty result: `blocked or None` (:428). Pinned by `test_a_window_no_outage_reaches_is_not_cut`, whose two outages stay outside the window or inside the 3 h bridge.
- **Rain gauge vs rain rate.** The filter at :426 uses `effective_aggregate`, the same resolver `_aggregate` and the backfill guard use (weather_aggregate.py:420-447). A sensor-sourced precip defaults to DELTA and is removed; a `riemannsum` override stays. `test_a_rain_gauge_is_never_cut_and_a_rain_rate_is` asserts both sides. Flipping `!=` or dropping the filter fails it. `_aggregate` has its own DELTA guard (weather_aggregate.py:525), so the double exclusion is harmless defence in depth.
- **Offset-aware outage stamps.**
  - Mechanism: `Outage.from_store` coerces start and end through `coerce_stamp(..., STAMP_FROM_STORE)` (sensor_liveness.py:153-156). The gate coerces watermark and `now` the same way (:416-417). After that, `blocked_spans` compares only naive values, so "can't compare offset-naive and offset-aware" cannot arise in the gate. `test_outage_stamps_with_an_offset_are_read_on_has_clock` asserts the same cut as the naive case.
  - Coverage gap: the test builds its offset from `dt_util.get_default_time_zone()`, which is HA's own zone. It therefore cannot tell "convert to HA's clock" from "drop tzinfo" (see Minor 2).
- **No own liveness check in the commit.** The gate reads only `outages_of(mapping)` (:424). There is no `advance_outages`, no `hass.states` access and no await. Open outages are cut up to the commit's `now`, and an outage opened since the last check is not seen, which is the intended behaviour.
- **`blocked` reaches the aggregate and both records on the only commit path.**
  - The only production caller of `_aggregate_for_zone` and both `_record_window_*` is `async_calculate_zone` (grep over `custom_components/`).
  - `test_the_aggregate_and_both_records_are_cut` checks the kwargs of both records and the arithmetic of the cut mean: (276-35)/19, so the spans really reach `aggregate_window`.
- **Other callers behave as before.**
  - `blocked` is keyword-only with default None. About 25 existing test call sites of `_aggregate_for_zone`, `_record_window_amplitude` and `_record_window_radiation` pass no `blocked`.
  - With None, `_aggregate` takes `spans = None` and the old path (weather_aggregate.py:522-541). The records' `blocked and ...` guards are inert.
  - `test_a_group_that_keeps_aggregates_as_before` pins T == 11.5 and `blocked is None`.
  - The only added work for a keep group is one more `store.get_mapping`, a read of the same entry `_aggregate_for_zone` reads next.
- **Record skips fire only on the relevant field.** `blocked and MAPPING_TEMPERATURE in blocked` (:713) and `blocked and MAPPING_SOLRAD in blocked` (:753). Each test runs two calls: relevant field blocked -> nothing recorded; another field blocked (dewpoint, temperature) -> recorded. A None or `{}` argument skips nothing.
- **Exceptions in the gate.**
  - Nothing in the gate raises on stored shapes: `outages_of` and `Outage.from_store` never raise, `coerce_stamp` never raises, and `effective_aggregate` is the same resolver `aggregate_window` already runs per commit.
  - `get_mapping` with `int(mapping_id)` could raise on a non-numeric id, but `_aggregate_for_zone` calls it a few lines later anyway, so the behaviour is unchanged.
  - `_async_calculate_all` isolates a zone's exception (calculation.py:573-590). Only the direct `__init__.py:2125` call path has no wrapper, and nothing new can fail there.

### Strengths
- The code is the plan's text, byte-identical to the probe. The gate does the one thing asked and keeps all decisions in one place: setting, form, window, gauge.
- The `{}` -> None normalisation keeps "nothing to cut" a single representation for the records, for Task 5's share and for `aggregate_window`.
- The tests are real: real store, real coordinator, real `aggregate_window`. Only `calculate_module` and the records are stubbed, for the kwargs assertions. The expected value of the cut mean is derived arithmetically, not copied from the output.
- The `_FakeStore` fix is minimal and was found by running the neighbours.

### Issues
#### Critical (Must Fix)
none

#### Important (Should Fix)
none

#### Minor (Nice to Have)
1. tests/test_silent_sensor_commit.py (`TestTheGate`): no gate-level test with an open outage (`end=None`). The Global Constraint "offener Eintrag bis `now` des Commits" depends on the gate passing the coerced `now` as window end (calculation.py:424). A mutation to a different window end would pass every closed-outage test. Suggestion: `_outage(2)` and `assert _gate(...) == {T: ((W + 5 * H, NOW),)}`.
2. tests/test_silent_sensor_commit.py:452-464 (`test_outage_stamps_with_an_offset_...`): the offset used is HA's own zone, so the test also passes if the code merely stripped tzinfo. A UTC or +x stamp (e.g. `(W + zone offset).replace(tzinfo=timezone.utc)`) would prove the conversion. The conversion itself is Task 1 code, covered by the time-provenance tests. Same for an aware watermark or `now` through the gate: not tested.
3. calculation.py:401-403 (gate docstring, plan-dictated wording): "that form cuts together with the live estimate" reads as a present-tense fact. In this branch neither the hourly form nor the live estimate is cut (Task 9's doc text says so explicitly). Wording like "a change that cut that form would have to cut the live estimate with it" would be accurate. This is a plan text; the human decides.
4. calculation.py:418: `watermark >= now` is redundant with `blocked_spans` (see above). Harmless as a readable early exit; no action needed unless mutation testing in Task 10 lists it, in which case it is an equivalent mutant.

### Assessment
**Task quality:** Approved
**Reasoning:** The code matches the plan and the probe byte for byte, and keeps groups that do not pause on exactly the old path (`blocked=None` end to end). Every named risk checks out in the code. The gate has no raising path beyond what the commit already had. The gaps are test-strength points (open outage, conversion vs stripping of offsets) plus one forward-looking docstring sentence.