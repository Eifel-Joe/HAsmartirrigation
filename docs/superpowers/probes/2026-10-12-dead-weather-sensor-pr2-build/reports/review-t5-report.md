### Spec Compliance
- Spec compliant. I compared the diff with the plan text of Task 5, Steps 3 to 6, snippet by snippet:
  - Imports: `calculation.py:20` and `:44`.
  - `_REQUIRED_SENSOR_FIELDS`: `:65`, after `BUFFER_RETENTION`.
  - `blocked=blocked` pass-through: `:679-686`.
  - Signature and docstring: `:1218`.
  - `share` block: `:1253-1263`.
  - PyETO branch: `:1297`.
  - Passthrough branch: `:1318`.
  - Day-form scaling: `:1356-1359`.
- The wording matches, including the comments. The only deviation is black's one-line signature at exactly 88 characters. It is harmless and the report names it.
- Extra / Missing / Misunderstood: none found.
- Cannot verify from the diff:
  - I did not run the suite, as instructed, so RED/GREEN rest on the report. The numbers it quotes (7 failed / 83 passed) match the brief's probe measurements.
  - The claim that the probe commit `1fc1412b` was not used cannot be checked from the diff.

### Strengths
- With `blocked=None` the behaviour is unchanged:
  - `share` stays `None`.
  - `None != 0` is True, so the PyETO condition equals the old `hourly is None`.
  - `None == 0` is False, so Passthrough falls through to the old `elif`.
  - `share is not None` is False, so there is no scaling.
  - The explanation code is untouched.
- The `share` window is the same as the gate's. `_blocked_spans_for_zone` (`calculation.py:415-446`) cuts the spans to `[watermark, now)` and returns `None` for a missing watermark or `watermark >= now`. `calculate_module` uses the same `coerce_stamp(LAST_CONSUMED)` and `coerce_stamp(now)`. Both read the same `zone` dict, with no write between them.
- Every required-field and exactness check is correct:
  - Only required fields count. `valid_share` (`sensor_liveness.py`) counts only the fields passed to it. `SOLRAD` is not in `DAILY_FORM_FIELDS` (`pyeto/__init__.py:114-120`), and `calculate_et_for_day` estimates a missing solar radiation, so it is rightly excluded.
  - A blocked field the module does without leaves `gone = 0`, so `share` is exactly `1.0` and `et_delta *= 1.0` is bit-identical.
  - Min/max temperature map to `Temperature`, and `dict.fromkeys` gives `(DEW, T, WIND, PRESS)`. `store.py:1389-1392` shows sensor groups no longer carry separate min/max fields, so this mapping is consistent.
  - Exactly 0 is reliable: `_merged` joins touching spans, so a fully covered window becomes one span `[start, end)` and `gone == length` exactly.
- No double application and no application where it is not wanted:
  - The share is applied once, in the day-form `else` branch only, to `et_delta` and not to `precip`.
  - `hourly is not None` is only possible with the hourly setting on. That is the same predicate (`hourly_calculation_enabled`) under which the gate returns `None`. So share and hourly never meet, and even if the flag flipped between the two reads the hourly branch ignores `share`.
  - `replayed_balance_applies` also requires the hourly setting, so the daily path uses the lumped balance. Drainage code, `elapsed_hours` and `hour_multiplier` are untouched.
- Share 0 consumes the window:
  - `aggregate_window` returns a dict whenever the buffer has rows, so the early return at `calculation.py:672` is not taken.
  - `calc_data` is non-None, so the watermark advances (`:700`).
  - PyETO is not asked, so it logs no warning, and rain is still booked.
  - Passthrough books 0.0 without ERROR.
  - Passthrough failing for another reason still hits `return None`, the ERROR, and an unchanged watermark.
- The tests are good in the places that matter:
  - The ERROR-absence assertion is paired with a counterpart test that asserts the same string is present, so caplog capture is proven.
  - Exact `== -4.0` pins the share-1 case.
  - The `-2.0` Static test pins that a module without required fields is never scaled.
  - The constant test pins the tuple order.

### Issues
#### Critical (Must Fix)
None.

#### Important (Should Fix)
None.

#### Minor (Nice to Have)
- `tests/test_silent_sensor_commit.py:309` (`test_with_forecast_days_the_whole_mean_is_scaled`) does not test forecast days. The stub returns a constant regardless of `forecast_days` or `forecastdata`, and the non-hourly path of `calculate_module` never reads `forecast_days`. Code path, setup and assertion are the same as the preceding test. It only pins that no branch on forecast days exists. To strengthen it, give the stub a `side_effect` that computes a mean of weather day and forecast rows, and pass real `forecastdata`.
- `tests/test_silent_sensor_commit.py:456` (`test_a_pausing_group_under_the_hourly_calculation_matches_too`) does not exercise the hourly branch of `calculate_module`. The `Mock` instance has no `_solrad_behavior == DontEstimate`, so `_hourly_et_for_zone` returns `None` and the daily form runs. The test only repeats the gate result `blocked is None` already pinned in `TestTheGate`. This is harmless because the `else` structure makes double application impossible. It should not be read as coverage of the hourly arm.
- Two float edges have no test:
  - A share strictly between 0 and the tiny positive range, for example one valid hour, where the equation is still asked.
  - Rain together with a share strictly between 0 and 1, which would pin that `precip` is not scaled. The `share == 0` rain test only catches a scaling of the sum `delta`, not scaling in the partial case.
- `calculation.py:1255-1263` derives the window `(watermark, now)` a second time, as `_blocked_spans_for_zone` does at `:437-439`. This is plan-mandated and the gate guarantees the same inputs today. The `watermark is not None` guard is unreachable through the coordinator. If someone calls `calculate_module` with a non-None `blocked` and no watermark, `share` stays `None` and the module books the full amount unscaled. This is not a defect now. If the window definition changes, both places must change together.
- `et_term` (`calculation.py:1353`), used in the Kc explanation line "Kc x et_term", stays unscaled by `share`. It is consistent with how `hour_multiplier` is treated, so it is not an error. Task 6 should check that its sentence still reads coherently with Kc != 1.

### Assessment
**Task quality:** Approved
**Reasoning:** The change matches the plan snippets exactly, leaves every `blocked=None` path and every module without required fields bit-identical, and covers the zero-share, partial-share and "reason other than silence" cases. The open points are weak or duplicate tests and a duplicated window derivation, none of which affects correctness.