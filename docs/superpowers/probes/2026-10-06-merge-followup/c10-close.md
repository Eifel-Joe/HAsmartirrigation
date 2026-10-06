## English

**Merged upstream: [JustChr#191](https://github.com/JustChr/HAsmartirrigation/pull/191)** on 2026-10-06 as squash `7f556344`, identical in content to our branch (all 486 changed lines). It ships in JustChr's pre-release **v2026.10.05**, together with JustChr#190 and JustChr#192. Closing.

**JustChr's comment after the merge** ([link](https://github.com/JustChr/HAsmartirrigation/pull/191#issuecomment-6021768425)), paraphrased except for the quote:
- He read the `watering_calendar.py` changes against `calculation.py` and trial-merged on master (3804 passed, 9 skipped); the new rules match.
- On the refreshed screenshot in `docs/configuration-weather-location.md`: "yes please". → Eifel-Joe#87
- Real climate data would be a new feature; he wants an issue for it first and will decide its shape there. → we open it upstream next; Eifel-Joe#42 then lists it under "Watched, not scheduled".

The rest:
- production v2026.10.06b1 already carries this change (the same files; the two bundles differ only in the version string); the rebuild on upstream v2026.10.05 comes later. HA-Prod stays on v2026.10.05b1, without it, for the field test of Eifel-Joe#8.
- The side findings stay open as their own issues (items 39o–39p on Eifel-Joe#42).
- Worktree and branches of this fix are removed; the design history is on `archive/design-history`.

## Deutsch

**Upstream gemergt: [JustChr#191](https://github.com/JustChr/HAsmartirrigation/pull/191)** am 2026-10-06 als Squash `7f556344`, inhaltlich identisch mit unserem Branch (alle 486 geänderten Zeilen). Er steckt in JustChrs Pre-Release **v2026.10.05**, zusammen mit JustChr#190 und JustChr#192. Damit geschlossen.

**JustChrs Kommentar nach dem Merge** ([Link](https://github.com/JustChr/HAsmartirrigation/pull/191#issuecomment-6021768425)), bis auf das Zitat sinngemäß:
- Er hat die Änderungen an `watering_calendar.py` gegen `calculation.py` gelesen und probeweise auf master gemergt (3804 bestanden, 9 übersprungen); die neuen Regeln stimmen überein.
- Zum erneuerten Screenshot in `docs/configuration-weather-location.md`: „yes please“. → Eifel-Joe#87
- Echte Klimadaten wären ein neues Feature; dafür will er zuerst ein Issue und dort die Form entscheiden. → eröffnen wir als Nächstes upstream; Eifel-Joe#42 führt es dann unter „Beobachtet, nicht eingeplant“.

Außerdem:
- production v2026.10.06b1 enthält die Änderung schon (dieselben Dateien; die zwei Bundles unterscheiden sich nur in der Versionsnummer); der Neubau auf upstream v2026.10.05 folgt später. HA-Prod bleibt für den Feldtest von Eifel-Joe#8 auf v2026.10.05b1, also ohne sie.
- Die Nebenbefunde bleiben als eigene Issues offen (Punkte 39o–39p in Eifel-Joe#42).
- Worktree und Branches dieses Fixes sind entfernt; die Design-Historie liegt auf `archive/design-history`.
