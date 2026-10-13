### Spec Compliance
- ✅ Spec compliant. Verified without running anything:
  - Both files are byte-identical to the probe commit: `git diff --stat dfd5c9a8 a9708bec` over the two files prints nothing.
  - The parent is `2621a230`, the subject matches the plan, and the trailer is `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - The diff has no references to issues or PR/task numbers.
  - The committed doc file has 0 CR bytes, so line endings are clean.
- Plan criterion, checked against the committed doc:
  - "Meanwhile the calculation keeps using" is gone.
  - "Keep the last value" appears on the list item (`docs/configuration-sensor-groups.md:60`) and in the last sentence of the three-hours paragraph (`:64`).
  - "pausing" appears at `live_estimate.py:598` and `:625`.
- Only comments and docstrings change in `live_estimate.py` (6 added lines: a docstring paragraph and one `#` line). No code is touched, so groups on *keep* and every other path are untouched.
- ⚠️ Cannot verify from the diff: nothing outstanding. Each doc claim was checked against code on the branch (table below).

**Doc claims checked against the code**

| Claim | Where it holds |
|---|---|
| Existing groups keep, new groups pause | `store.py:391` (attribute default `PAUSE`). `store.py:985-992` and `:1424` (stored group without the key, or an unknown value, becomes `KEEP`). Panel fallback `view-mappings.ts:1085`. |
| Only the daily form without the hourly calculation cuts | `calculation.py:431-434` (`group_pauses`, then `hourly_calculation_enabled` returns None). Same predicate in `sensor_liveness.py:578`, so the notice variant `weather_sensor_stale_paused` appears only where the group really cuts. |
| The live estimate does not cut | No `blocked` anywhere in `live_estimate.py`; `_aggregate_live_window` calls `aggregate_window` without it. |
| Fixed three hours | `sensor_liveness.py:190-198` (`outage.start + STALE_AFTER`, half-open, an open outage runs to `end`). `const.py:696` (`3 * 3600`). |
| Rain gauges are never cut | `calculation.py:445` and `weather_aggregate.py:525` (Delta aggregation excluded). |
| Booked share and explanation | `calculation.py:1356-1359` (ET times `share`). `:1894-1916` (silent-time sentence, share sentence). |
| Partial-day mean as a known limit | `weather_aggregate.py:643-647` (mean over valid values or segments). |
| Escape hatch for rarely reporting sensors | The `weather_sensor_stale_paused` notice in `translations/en.json:462` gives the same advice ("Keep the last value"). |
| Option and setting names | The panel (`frontend/localize/languages/en.json:469-472`) uses "When a sensor goes silent", "Keep the last value" and "Pause", identical to the doc. The notice quotes "Keep the last value". |

- No contradiction with the unchanged paragraphs of the file (`:55`, `:66`) or with `docs/usage-events.md:21`.

### Strengths
- The new section states the live-estimate asymmetry openly, both in the doc (`:62`) and next to the code (`live_estimate.py:598-601`). The docstring points at the function that does the cutting.
- Terminology matches the panel and the notice, so a user can find the setting.
- The edit stays on the plan's scope: no code changes, only two files.
- Gives the user a concrete exit for slow integrations (`:64`).

### Issues
#### Critical (Must Fix)
- None.

#### Important (Should Fix)
- None.

#### Minor (Nice to Have)
1. `docs/configuration-sensor-groups.md:59` (**plan-mandated**). The sentence "its values are no longer used, and the daily calculation books no evapotranspiration for that time" is true only for fields the module cannot do without. That is `_REQUIRED_SENSOR_FIELDS`, `calculation.py:65-77`: for PyETO dewpoint, temperature, wind speed and pressure; for Passthrough its ET field. For a silent solar radiation or humidity sensor, the full ET is still booked from the mean of the remaining hours or from the estimate (share only counts required fields, `:1259-1262`). A Static module has no sensors, so nothing is cut.
   - The error is in the user-visible direction: a reader expects zero booking and gets the full amount.
   - Suggested qualifier: "for the sensors the evapotranspiration calculation cannot do without, such as temperature, wind speed, pressure and dewpoint".
2. `live_estimate.py:590` and `:594-596` (**plan-mandated**). The summary line "reduced exactly as `_aggregate_for_zone` will" and the sentence "the two agree by construction" stay unqualified. The new paragraph below contradicts them for pausing groups. The commit message says the comments "no longer claim ... exactly", which the code does not fully back.
   - Similar unqualified claims remain at the module docstring `:15-21` ("converge on exactly what the commit will see"), `:912-915`, and `:1108` ("the same call the commit reduces the whole window with").
   - Suggested fix: add "Except for a pausing group's blocked time" to the lead sentence, or accept the paragraph below as the caveat.
3. `docs/configuration-sensor-groups.md:62`, and the panel help at `frontend/localize/languages/en.json:470` (**plan-mandated**). "The hourly calculation" is not the user-visible name. The setting is titled "Hourly evapotranspiration" with the label "Sum evapotranspiration hour by hour" (`en.json:363-365`), and it is not documented under `docs/`. A reader cannot tell which switch is meant. Suggested fix: name the setting and its tab once.
4. `docs/configuration-sensor-groups.md:64` (**plan-mandated**). "With **Pause**, set such a sensor group to **Keep the last value**" reads as contradictory. Better: "If the group is on **Pause**, switch it to **Keep the last value**".
5. `docs/configuration-sensor-groups.md:59`. "the sensor's last report" is loosely worded. The start of an outage is the device's last sign of life (`sensor_liveness.py:116`, and `:55` of the doc), not necessarily the mapped sensor's own report.
6. Outside the diff, from an earlier task: `calculation.py:423-424` ends with "that form cuts together with the live estimate". On this branch neither the hourly form nor the live estimate cuts. The sentence promises a later step without saying so. It is worth rewording or clarifying when the branch is wrapped up.

### Assessment
**Task quality:** Approved
**Reasoning:** The change is documentation and comments only, byte-identical to the probe run. Every behavioral claim in the new section checks out against the branch code (defaults, daily-form-only cut, live estimate and hourly form not cut, fixed three hours, rain gauges exempt, escape hatch), and the option names match the panel and notice. The remaining findings are Minor: one over-general sentence, some live-estimate comments still unqualified, and wording points. Most of these come from plan-dictated text.