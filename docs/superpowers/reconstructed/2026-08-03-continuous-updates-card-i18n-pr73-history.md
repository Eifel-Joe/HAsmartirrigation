# Translate the continuous_updates experimental card (i18n)

> ⚠️ **Reconstructed on 2026-08-08** from git commits, the pull request and project memory — this is **not** a contemporaneous design doc. It summarises, from the best available evidence, how/why this change came to be and how it was implemented.

**Feature date:** 2026-08-03  ·  **PR:** https://github.com/JustChr/HAsmartirrigation/pull/73  ·  **Branch(es):** i18n-continuous-updates-card
**Commit(s):** caca9136

## Problem / Context
Upstream PR #66 shipped the "Continuous sensor updates" card (Setup → Experimental) with English-only strings under `panels.experimental.cards.continuous_updates`. HASI's frontend ships 8 bundled languages, but only `en.json` is baked into the dist bundle; the other seven are fetched at runtime and missing keys fall back silently to English via `localize()`. Result: the card rendered in English on every non-English UI — the user noticed the untranslated German card in a screenshot. This is the mirror case of the standing project rule that new UI strings must land in all 8 languages, applied here to a string *inherited* from upstream rather than one we authored.

## Options considered
Not reconstructable — the commit and PR record only the chosen solution.

## Decision
Backfill the five card strings (`title`, `description`, `label`, `debounce_label`, `note`) into the seven non-English catalogues (de/es/fr/it/nl/no/sk), translated consistent with each file's existing terminology (e.g. Sensorgruppe, weather service, evapotranspiration). Because the seven files are served as static JSON and only `en.json` is bundled, no dist rebuild is required.

## Implementation
Purely additive edits to `custom_components/smart_irrigation/frontend/localize/languages/{de,es,fr,it,nl,no,sk}.json` — the new `continuous_updates` block inserted just before the `distributors` card block, 7 files, +49 lines total, no source or Python changes. Per memory, insertion was scripted (`json.dumps` per value for correct escaping, JSON re-validated) with one translation agent per language reading the target file for terminology.

## Evidence
- PR: https://github.com/JustChr/HAsmartirrigation/pull/73
- Commit(s): caca9136 — i18n: translate the continuous_updates experimental card (7 languages)
- Tests: —
- Memory: [[hasi-i18n-all-languages]]

## Related
[[hasi-i18n-all-languages]], [[language-german]], [[hasi-production-on-upstream]]
