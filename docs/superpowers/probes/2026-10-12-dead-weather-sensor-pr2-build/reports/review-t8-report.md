### Spec Compliance
- ✅ Spec compliant. Steps 1 and 3-7 appear in the diff in full and verbatim (the controller's mechanical check agrees). Nothing is missing and nothing extra was added. The commit message and trailer match the plan, and the added lines carry no issue, task or PR references (grep over the added lines was empty).
- ⚠️ Cannot verify from diff: the two rebuilt bundles (excluded by design; the controller verified them against the probe build). I read nothing in `dist/`.
- Not run (per rules): pytest and vitest. I rely on the report's RED/GREEN evidence, whose counts match the brief's probe measurements (`1 failed, 10 passed` / `78 passed`; `1 failed | 8 passed` / `661 passed`). No new test needs an extra run.

**Named-risk checks**
- **Mapping view accepts only the two values, and omission leaves the stored value alone.**
  - `websockets.py:237-239`: `vol.Optional(MAPPING_ON_SILENT_SENSOR): vol.In(ON_SILENT_SENSOR_OPTIONS)`. The options tuple is `("keep","pause")` at `const.py:725`. The key has no default.
  - `post` (`websockets.py:255ff`) passes the key through `sanitized`, whose deny-list is only the four server-computed fields.
  - `store.async_update_mapping` applies `attr.evolve(old, **changes)` with only the keys sent, so omission leaves the value alone. The create path `MappingEntry(**data)` falls back to the `pause` default at `store.py:391`.
  - `__init__.py:1844` resyncs the notice only when the key is in `data`.
- **Panel shows the current value, and sends the setting only when it is set.**
  - `view-mappings.ts:1085` `mapping.on_silent_sensor ?? "pause"` and `?selected="${value === option}"` show a loaded `keep` as keep. A new group (no key) shows `pause`, which matches the server default.
  - `view-mappings.ts:379-386` sends the key only if `!== undefined`. The wizard (`ip-setup-wizard.ts:285`) is the only other `saveMapping` caller; it sends no key, so the server default `pause` applies.
  - The brief says "the vitest pins both" for display and save. The two new vitest cases pin only the save payload; display is not tested (see Minor 1).
- **Option labels against the notice texts.** I parsed `translations/<lang>.json` `issues.weather_sensor_stale_paused.description` and the panel `on-silent-sensor.keep` for all 8 languages.
  - The notice quotes only the `keep` option, and in each language the panel label appears verbatim, wrapped in language-typical quotes: de `„Letzten Wert behalten“`, en `"Keep the last value"`, sk `„Ponechať poslednú hodnotu“`, and so on.
  - The `pause` label is not quoted in the notice, so no mismatch is possible there.
  - The notice's other quoted label, the "Static value" source, equals the existing panel `sources.static` in all 8 languages.
- **8 language files.**
  - I compared all 32 values (title, help, keep, pause) programmatically against the brief's table: identical.
  - Key sets are identical across the languages, and none of the four values has a placeholder or NBSP. The block sits at the path `panels.mappings.cards.mapping.on-silent-sensor`.
  - The committed blobs are LF-only, with no CR and no BOM.
  - `localize()` with no arguments returns the raw string (`localize.ts:80ff`), so the apostrophe in the English help text is not parsed as ICU.
- **`types.ts` against the backend.** `async_get_mappings` returns `attr.asdict(MappingEntry)` (`store.py:1939`), so `on_silent_sensor: str` is sent (field at `store.py:391`). `types.ts:426` `on_silent_sensor?: string` matches. The other PR 1 fields (`sensor_outages`, `sensor_last_seen`) are not typed, but `saveToHA` never sends them, and that is what keeps the schema (extra keys are rejected) satisfied.
- **Other fields of the mapping card unchanged.**
  - A save without the setting is `{id, name, mappings}` as before, in the same key order. The test at `view-mappings-save.test.ts:147ff` pins this with `Object.keys(...)`, so an unconditional `{on_silent_sensor}` that leaves an `undefined` key would fail it.
  - The name input and the other handlers spread `...mapping` or `this.mappings[index]`, so they carry the new field along unchanged.
  - The card renders the new row between the name row and the settings (`:1053`), and the other rows are untouched.
  - The schema refactor is behavior-neutral: the same keys with the same validators, and the only change is the new `Optional`.

### Strengths
- The schema is a module-level constant, directly testable, and the old "server fields accepted, stripped below" comment moved with it.
- `saveToHA` keeps the explicit destructure, so server-only fields never reach the strict schema. A copy without the setting sends no empty key, which keeps untouched groups' requests byte-identical.
- The select mirrors the file's existing `?selected` and `id="…${mapping.id}"` patterns.
- The translations came from the table by script and are consistent with the notice texts.
- The commit scope is exact: 13 source and test files plus 2 bundles.

### Issues
#### Critical (Must Fix)
None.

#### Important (Should Fix)
None.

#### Minor (Nice to Have)
1. `view-mappings.ts:1085` and `:1109` (**plan-mandated**: the plan lists no render test). The display decisions are pinned by no test: `?? "pause"` for a group without the key, `value === option` for the `?selected` flag, the option order, and the `@change` handler (`:1106`).
   - The mutation `?? "keep"` would survive every test. The panel would then show "keep" for a new group that the server stores as `pause`, a display that disagrees with the stored value.
   - The brief's statement "the vitest pins both" overstates the coverage.
   - Fix if wanted: in the existing harness, call `el.renderOnSilentSensor(mapping, 0)` and assert the `selected` binding values, or assert on the rendered TemplateResult values.
2. `tests/test_silent_sensor_setting.py:105-111` (**plan-mandated**). The schema test checks acceptance of both values and rejection of `"sometimes"`, but not that omission stays omission.
   - A mutation to `vol.Optional(KEY, default="pause")` passes the test. Every save from an older panel would then overwrite a stored `keep`.
   - The store-level test `test_a_save_without_the_setting_leaves_it_alone` calls `async_update_mapping` directly and bypasses the schema.
   - Fix: add `assert MAPPING_VIEW_SCHEMA({const.MAPPING_NAME: "x"}) == {const.MAPPING_NAME: "x"}`.
3. `types.ts:426` and `view-mappings.ts:1085, 1109`. The values `"pause"`/`"keep"` are bare string literals in three places, and the type is plain `string`. A union `"keep" | "pause"` or constants would catch typos at compile time. This is polish, and the plan fixes the wording.

### Assessment
**Task quality:** Approved
**Reasoning:** The implementation matches the plan and the probe. The view accepts exactly `keep`/`pause`, the panel sends the setting only when set, and the labels in all 8 languages match the notice quotations. The remaining points are test-coverage gaps (display default, schema omission), not defects.