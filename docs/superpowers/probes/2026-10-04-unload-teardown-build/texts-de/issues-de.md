# Neue Issues aus dem Bau von Eifel-Joe#9 — deutsche Entwürfe zur Freigabe

Alle: **Frühere Bezeichnungen:** keine — am 2026-10-04 beim Bau von Eifel-Joe#9 gefunden (Reviews). Zeilen beziehen
sich auf `upstream/master` `e9c79ec4`. Gelesen, nicht gemessen. Labels: `typ:fehler`, `schwere:niedrig`; Größe je Issue.

---

## A — Beim Neuladen schaltet der Master-Abgleich eine Pumpe ab, unter der ein klassischer Lauf weiterläuft

**Was falsch ist**
- Ein klassischer Lauf läuft als Task (`irrigation.py:1155-1169`), nicht an den Eintrag gebunden; ein Neuladen bricht ihn
  bewusst nicht ab. Sein Master-Hold lag im alten Koordinator und wird beim Entladen von `_master_release_all` verworfen.
- Der neue Koordinator ruft beim Start `async_reconcile_master_after_restart` (`master.py:210-249`). Der Abgleich wartet
  nur auf gespeicherte Self-Closing-Läufe und einen Verteiler-Zyklus; einen klassischen Lauf sieht er nicht.
- Mit `master_off_after` schaltet er deshalb die Pumpe ab, während das Ventil des klassischen Laufs offen bleibt. Der
  Lauf wird trotzdem nach Zeit gebucht: Gutschrift ohne Wasser.

**Relevanz** Auf HA-Prod nicht scharf (`master_off_after = false`). Trifft nur ein Neuladen während eines klassischen Laufs.

**Form des Fixes (offen)** Der Abgleich bräuchte ein Wissen über laufende klassische Läufe über das Neuladen hinweg,
oder der klassische Lauf nimmt seinen Hold beim Nachfolger neu. Größe `groesse:M`.

**Messen** HA-Test: Test-Master mit „nach Lauf aus“, klassische Zone 3 min, mitten im Lauf neu laden → Test-Pumpe geht aus,
Ventil bleibt an.

---

## B — Wird der Master während eines Zyklus geändert oder geleert, bleiben Holds und Zyklus-Flag stehen

**Was falsch ist**
- Die Master-Einstellung wird live gespeichert, ohne Neuladen (`websockets.py:179`, `store.py:1677-1688`); `_master_cfg()`
  liest sie bei jedem Aufruf neu.
- Ist kein Master mehr eingetragen, kehrt `async_master_release` vor dem Verwerfen des Holds zurück (`master.py:132-133`):
  Die Holds bleiben, `_fire` läuft nie, `_master_on` bleibt gesetzt.
- Wird danach wieder ein Master eingetragen, überspringt jeder neue Verbraucher den Zyklusbeginn (`master.py:64`): HASI
  schaltet den neuen Master nicht ein, bis zum Neuladen oder Neustart; bei „nach Lauf aus“ auch nie aus.

**Relevanz** Nur bei einer Master-Änderung mitten in einem Zyklus. Auf HA-Prod nicht scharf.

**Form des Fixes (offen)** Bei einer Änderung der Master-Einstellung den Master-Zustand (Holds, Flag, Timer) verwerfen
oder den Eintrag neu laden. Größe `groesse:S`.

**Messen** HA-Test: Zone starten, im Lauf den Master leeren, danach wieder setzen, neuen Lauf starten → Test-Pumpe bleibt aus.

---

## C — `async_abort_batch_runs` kann werfen, dann läuft der Rest eines Deaktivierens nicht

**Was falsch ist**
- `async_abort_batch_runs` (`batch.py:672-699`) ruft `_sc_active_runs` und `_batch_dispatch_stop` ungeschützt auf.
- Wirft das Stopp-Skript (etwa `ServiceNotFound`, nachdem es umbenannt wurde), verlässt die Ausnahme `async_unload_entry`:
  Was danach kommt, läuft nicht — das Entladen ohnehin schon heute, mit dem Fix für Eifel-Joe#9 auch der Service-Abbruch
  und das Master-Ende. Der Eintrag bleibt geladen (`failed_unload`).

**Relevanz** Nur im Batch-Modus mit fehlendem oder kaputtem Stopp-Skript. Auf HA-Prod nicht scharf.

**Form des Fixes** Wie die OpenSprinkler- und Service-Abbrüche: lesen und stoppen je in `try/except` mit Log, nie werfen.
Größe `groesse:S`.

**Messen** Unit-Test mit werfendem Batch-Stopp.

---

## D — Die Pause eines Verteilers schaltet die Pumpe unter einer Zone ab, die nach dem Start dazukam

**Was falsch ist**
- `_dist_master_window_off` / `_dist_master_window_on` (`distributor.py:321-342`) entscheiden nach dem Flag `concurrent`,
  das beim Dispatch festgelegt wird (`distributor.py:581`, `:2083`; verwendet `:1926`, `:1929`).
- Startet ein Verteiler allein und kommt danach eine pumpengespeiste Zone dazu, schaltet seine nächste Pause die Pumpe unter
  dieser Zone ab (`pause_seconds`, Standard 300 s).

**Relevanz** Verteiler mit Master und „nach Lauf aus“ plus eine Zone, die mitten im Durchlauf startet. Auf HA-Prod gibt es
keinen Verteiler.

**Form des Fixes (offen)** In der Pause nach den lebenden Holds entscheiden (`_dist_foreign_master_holds`) statt nach dem
Flag vom Dispatch. Größe `groesse:S`.

---

# Kommentare auf bestehende Issues

## Eifel-Joe#67 (zweiter Rotations-Dispatch ersetzt eine laufende Rotation) — verwandter Fund
Die Rotationsschleife behält ihre lokale `rotation` über das Await des Dispatch (`run_chain.py` um `:826`, `:906-923`).
Landet währenddessen eine Freigabe (Deaktivieren, OpenSprinkler-Abbruch) oder beim Neuladen der Abbau, und wird der Slot
danach abgelehnt, macht die Schleife mit der verwaisten Rotation weiter: nächste fällige Zone oder neuer Absorptions-Timer
auf der freigegebenen Kette. Abhilfe etwa `if state.rotation is not rotation: return` nach dem Await. Die sequenzielle
Schleife ist sicher, sie liest `state.zones` neu.

## Eifel-Joe#51 (vier Awaits zwischen Dispatch-Entscheidung und Datensatz) — eine weitere Folge
Steckt ein Dispatch beim Entladen noch in diesen Awaits (Bestätigungs-Poll bis 30 s), läuft er auf dem toten Koordinator
weiter: Er schreibt danach seinen Datensatz und stellt Backstop und Watcher dort. Der Resume des Nachfolgers lief vor dem
Datensatz; der Lauf wird über den toten Koordinator nach Zeit gebucht. Mit dem Fix für Eifel-Joe#9 unverändert.

## Eifel-Joe#15 (Batch-Lauf nach Neustart ohne Backstop) — Stand
- Mit dem Fix für Eifel-Joe#9 gilt die Lücke auch nach einem Neuladen: Der Backstop des alten Koordinators wird jetzt
  gekündigt. Bisher buchte er den Lauf pünktlich, ließ aber den Master-Hold des Nachfolgers stehen; jetzt bucht der Watcher
  des Nachfolgers, bei verpasster Aus-Meldung erst mit der nächsten (gemessen).
- Kein Einzeiler wie im Body vermutet: Ein pausierter Lauf (Segment zu) darf keinen Backstop bekommen. Vor dem Watcher
  gestellt, kündigt eine bei dessen erster Auswertung erkannte Pause ihn wieder (`_watch_pause` → `_sc_cancel_cleanup`);
  dazu Tests Neustart/Neuladen × offen/pausiert.
- Drei Kommentare behaupten einen Backstop, den der Resume nicht stellt: `batch.py:73-76`, `run_watch.py:631-634`,
  `tests/test_batch.py:859`. Mit dem Fix richtigstellen, ebenso den Satz im Docstring von
  `async_teardown_self_closing_handles`, den der PR für Eifel-Joe#9 einführt.
