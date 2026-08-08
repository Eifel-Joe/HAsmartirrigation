# Open help-page links in a new tab

> ⚠️ **Reconstructed on 2026-08-08** from git commits, the pull request and project memory — this is **not** a contemporaneous design doc. It summarises, from the best available evidence, how/why this change came to be and how it was implemented.

**Feature date:** 2026-07-12  ·  **PR:** —  ·  **Branch(es):** feature/help-links-new-tab
**Commit(s):** 1bc109e7, 871c3df4

## Problem / Context
On the Setup → Help card, the "How to get help" links (the wiki/docs, the Home Assistant community forum thread, and the GitHub issues tracker) opened in the same browser tab. Following any of them navigated away from the Smart Irrigation panel, forcing the user back and losing their place in the config UI.

## Options considered
Not reconstructable — the commit and PR record only the chosen solution.

## Decision
Make each help link open in a new tab via `target="_blank"`, paired with `rel="noopener noreferrer"` so the opened page cannot access the opener window (`window.opener`) and to suppress referrer leakage — the standard safe pattern for external links.

## Implementation
Single source change in `custom_components/smart_irrigation/frontend/src/views/setup/view-setup.ts`: the three `<a>` tags in the help card (`DOCS_URL`, the hard-coded community-forum URL, and `ISSUES_URL`) each gained `target="_blank" rel="noopener noreferrer"`. Commit 871c3df4 rebuilt the generated `frontend/dist/smart-irrigation.js` bundle to carry the change into the shipped frontend.

## Evidence
- PR: —
- Commit(s): 1bc109e7 — fix(frontend): open help-page links in a new tab; 871c3df4 — build(frontend): rebuild dist with help links opening in a new tab
- Tests: —
- Memory: —

## Related
—
