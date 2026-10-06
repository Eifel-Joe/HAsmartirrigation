## English

**Merged upstream: [JustChr#192](https://github.com/JustChr/HAsmartirrigation/pull/192)** on 2026-10-06 as squash `33d0fec9`, identical in content to our branch (all 523 changed lines). It ships in JustChr's pre-release **v2026.10.05**. Closing.

**JustChr's comment after the merge** ([link](https://github.com/JustChr/HAsmartirrigation/pull/192#issuecomment-6023452397)), paraphrased:
- He traced the startup order (the hub is registered and `hub_link` recorded before any platform adds an entity), trial-merged on master (3826 passed, 9 skipped), and a mutation of his own on the entry id passed to the new lookup was caught.
- The 2025.5 floor stays, so the alternative in the PR body (raise the floor, drop the switches) is not wanted.
- Real Home Assistant 2026.8.0 is the one shape CI cannot run; a report would be welcome if we ever see it. No issue for that: there is nothing to do unless one of our instances runs 2026.8.0.

The rest:
- production v2026.10.06b1 already carries this change; the rebuild on upstream v2026.10.05 comes later. HA-Prod stays on v2026.10.05b1, without it.
- The side finding stays open as its own issue: Eifel-Joe#86 (item 39q on Eifel-Joe#42).
- Worktrees (the probe worktree too) and branches of this fix are removed; the design history is on `archive/design-history`.

## Deutsch

**Upstream gemergt: [JustChr#192](https://github.com/JustChr/HAsmartirrigation/pull/192)** am 2026-10-06 als Squash `33d0fec9`, inhaltlich identisch mit unserem Branch (alle 523 geänderten Zeilen). Er steckt in JustChrs Pre-Release **v2026.10.05**. Damit geschlossen.

**JustChrs Kommentar nach dem Merge** ([Link](https://github.com/JustChr/HAsmartirrigation/pull/192#issuecomment-6023452397)), sinngemäß:
- Er hat die Start-Reihenfolge nachverfolgt (der Hub wird registriert und `hub_link` abgelegt, bevor eine Plattform ein Entity anlegt), probeweise auf master gemergt (3826 bestanden, 9 übersprungen), und eine eigene Mutation an der Entry-ID, die der neue Lookup bekommt, wurde gefangen.
- Die Untergrenze 2025.5 bleibt; die Alternative aus dem PR-Text (Untergrenze anheben, Weichen streichen) ist also nicht gewünscht.
- Echtes Home Assistant 2026.8.0 ist die eine Bauart, die die CI nicht fahren kann; ein Bericht wäre willkommen, falls wir es je sehen. Kein Issue dafür: Es gibt nichts zu tun, solange keine unserer Instanzen 2026.8.0 fährt.

Außerdem:
- production v2026.10.06b1 enthält die Änderung schon; der Neubau auf upstream v2026.10.05 folgt später. HA-Prod bleibt auf v2026.10.05b1, also ohne sie.
- Der Nebenbefund bleibt als eigenes Issue offen: Eifel-Joe#86 (Punkt 39q in Eifel-Joe#42).
- Worktrees (auch der Probe-Worktree) und Branches dieses Fixes sind entfernt; die Design-Historie liegt auf `archive/design-history`.
