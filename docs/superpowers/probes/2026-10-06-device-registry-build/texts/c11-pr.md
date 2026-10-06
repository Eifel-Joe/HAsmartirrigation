## English

**PR opened: [JustChr#192](https://github.com/JustChr/HAsmartirrigation/pull/192) (2026-10-06).** Both deprecated
device-registry calls are replaced wherever Home Assistant offers the new ones (2026.8 on); below 2026.8 nothing
changes, and the 2025.5 floor stays.

- **Branch** `fix/device-registry-2027-8` on `7001c754`, 5 commits (folded from ten: the five planned tasks plus five
  follow-ups from the per-task reviews), 4 files: `entity.py` (`hub_link_for`, `hub_link`, `find_device`),
  `__init__.py` (setup records the link; zone delete), `distributor.py` (distributor delete), new
  `tests/test_device_registry_compat.py`.
- **Tests:** 22 new; 36/36 targeted mutations killed. Local full suite: unchanged apart from the new tests (the three
  new setup tests end with the known local teardown error, lingering timer).
- **Reviews:** every task reviewed and re-reviewed, then a final review of the whole branch: no defect in the code. The
  follow-ups fixed one latent bug — HA has needed Python 3.14 since 2026.3 and its registry module has had no
  `from __future__ import annotations` since 2026.6, so reading the signature could raise `NameError` and stop setup —
  and pinned the miss, the order before the platforms, the overwrite after a reload and both delete paths on both
  registry shapes. Owner decisions today: fold into five commits; text polish only (no test removals, no change to the
  fallback).
- **Live on HA-Test (2026.9.4)** with pre-release [v2026.10.06b1](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.10.06b1):
  before, both warnings (startup; deleting a zone and a distributor); after, none. The same 11 devices with the same
  parent id, no entity dropped (181 entities, the same 37 unavailable), diagnostics `hub_link` = the hub's registry id;
  a throwaway zone and distributor hang off the hub and disappear with their device when deleted, also after a reload.
- **HA-Prod not updated** (still v2026.10.05b1 for the field test of Eifel-Joe#8).
- **Side finding, not in this PR:** after a reload, the entities of existing distributors stay unavailable until a
  restart — pre-existing upstream, now Eifel-Joe#86.

## Deutsch

**PR eröffnet: [JustChr#192](https://github.com/JustChr/HAsmartirrigation/pull/192) (2026-10-06).** Beide
abgekündigten Registry-Aufrufe sind ersetzt, wo Home Assistant die neuen anbietet (ab 2026.8); unter 2026.8 ändert
sich nichts, die Untergrenze 2025.5 bleibt.

- **Branch** `fix/device-registry-2027-8` auf `7001c754`, 5 Commits (aus zehn gefaltet: die fünf geplanten Tasks plus
  fünf Nachträge aus den Reviews je Task), 4 Dateien: `entity.py` (`hub_link_for`, `hub_link`, `find_device`),
  `__init__.py` (Setup legt den Verweis ab; Zone löschen), `distributor.py` (Verteiler löschen), neu
  `tests/test_device_registry_compat.py`.
- **Tests:** 22 neue; 36/36 gezielte Mutationen getötet. Lokale volle Suite: außer den neuen Tests unverändert (die
  drei neuen Setup-Tests enden lokal mit dem bekannten teardown-Fehler, Lingering timer).
- **Reviews:** jeder Task mit Review und Nachprüfung, dann ein Abschluss-Review des ganzen Branches: kein Defekt im
  Code. Die Nachträge behoben einen latenten Fehler — HA verlangt seit 2026.3 Python 3.14, und sein Registry-Modul hat
  seit 2026.6 kein `from __future__ import annotations` mehr, also konnte das Lesen der Signatur `NameError` werfen und
  das Setup abbrechen — und pinnten den Fehlschlag, die Reihenfolge vor den Plattformen, das Überschreiben nach einem
  Reload und beide Löschpfade auf beiden Registry-Bauarten. Entscheidungen heute: auf fünf Commits falten; nur
  Textschliff (keine Tests gestrichen, Rückfall unverändert).
- **Live auf HA-Test (2026.9.4)** mit Pre-Release [v2026.10.06b1](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.10.06b1):
  vorher beide Warnungen (Start; Löschen einer Zone und eines Verteilers), nachher keine. Dieselben 11 Geräte mit
  derselben Eltern-ID, kein Entity verworfen (181 Entities, dieselben 37 unavailable), Diagnostics `hub_link` =
  Registry-ID des Hubs; eine Wegwerf-Zone und ein Wegwerf-Verteiler hängen am Hub und verschwinden beim Löschen samt
  Gerät, auch nach einem Reload.
- **HA-Prod nicht aktualisiert** (weiter v2026.10.05b1 für den Feldtest von Eifel-Joe#8).
- **Nebenbefund, nicht in diesem PR:** Nach einem Reload bleiben die Entities bestehender Verteiler unavailable, bis
  HA neu startet — vorbestehend upstream, jetzt Eifel-Joe#86.
