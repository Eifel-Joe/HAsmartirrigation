**Titel:** fix(unload): die Self-Closing-Timer gehen mit dem Koordinator, und Deaktivieren stoppt, was niemand mehr betreut

## Problem

Ein Self-Closing-Lauf besitzt je Zone zwei Timer auf dem Koordinator: den Durchfluss-Abtaster (alle 15 s) und den Backstop. `async_unload` kündigte keinen von beiden; beide blieben gegen den abgebauten Koordinator scharf.

- **Neuladen mitten im Lauf** (jedes Speichern in den Optionen lädt neu): Der neue Koordinator übernimmt den Lauf aus dem Store (`async_resume_self_closing_runs`) und bucht ihn. Der alte Backstop findet dann keinen Datensatz mehr und kehrt zurück, bevor er seinen Abtaster beendet. Der Abtaster tickt bis zum nächsten Neustart von Home Assistant weiter und hält den ganzen alten Koordinator im Speicher. Endet der Lauf, während das Neuladen noch läuft, bucht ihn der tote Koordinator (Eimer, Lauf-Log, Kette, Master).
- **Master-Aus-Timer:** `_master_release_all` leerte die Holds, ließ den anstehenden Aus-Timer aber scharf. Nach einem Neuladen las er die geleerten Holds des toten Koordinators als „nichts läuft“ und schaltete bei `master_off_after` den Master ab, auch unter einem Lauf, den der neue Koordinator gerade gestartet hatte.

## Fix

1. `async_unload` ruft `async_teardown_self_closing_handles()`. Es kündigt jeden Abtaster und Backstop, ohne Schlusslesung und ohne Buchung; der Nachfolger übernimmt den Lauf wie nach einem Neustart.
2. `_master_release_all` kündigt auch den Aus-Timer. Bei ihrem zweiten Aufrufer, der Bereinigung beim Start, schaltete ein solcher Timer die Pumpe nur ein zweites Mal aus, rund 5 s später; das entfällt.
3. **Deaktivieren.** Mit Punkt 1 fiele weg, was bisher, eher zufällig, einen Service-Lauf nach dem Deaktivieren noch buchte und seinen Master freigab: der Backstop des toten Koordinators, bei `master_off_after` gefolgt von dessen Aus-Timer, der die Pumpe abschaltete. Das Deaktivieren behandelt Service-Läufe deshalb jetzt so, wie es OpenSprinkler- und Batch-Läufe schon behandelt:
   - zuerst alle Ketten freigeben (`async_release_all_chains`). Eine Kette hält den Master auch in der Pause zwischen zwei Läufen, wenn kein Lauf da ist, den ein Abbruch fände;
   - die Service-Läufe stoppen und buchen (`async_abort_self_closing_runs`, das Gegenstück zu `async_abort_opensprinkler_runs`): Stopp über den Stop service, gebucht wird, was gelaufen ist, gemessen, wo die Zone einen Durchflusssensor hat;
   - den Master-Zyklus sofort beenden (`async_master_end_cycle_now`): Master aus nur bei `master_off_after`, nur wenn ein Zyklus der Integration lief und kein Hold mehr besteht.
4. **Entfernen:** Die Service-Läufe bekommen den Stopp ohne Buchung, und der Master-Zyklus endet vor dem Löschen des Stores.
5. **Verteiler ohne Master** (`use_master = false`): `_dist_master_end` löschte am Ende des Durchlaufs das Flag `_master_on`, obwohl dieser Durchlauf den Master nie hochgefahren hat (`_dist_master_start` kehrt unter demselben Tor früh zurück). Lief daneben eine pumpengespeiste Zone, startete der nächste Verbraucher den Zyklus unter der laufenden Pumpe neu, mit Kick (aus und wieder an) und Settle, und das Master-Ende aus Punkt 3 hätte keinen Zyklus mehr gesehen. Der Zweig lässt das Flag jetzt stehen. Deshalb ist `test_master_end_clears_flag_immediately_when_not_using_master` umgekehrt und heißt jetzt `test_master_end_leaves_the_flag_alone_when_not_using_master`.

## Verhaltensänderung

- **Deaktivieren mitten im Lauf:** Service-Läufe werden über ihren Stop service geschlossen und als Teillauf gebucht. Service- und OpenSprinkler-Ketten geben ihre Warteschlange auf, auch in einer Pause zwischen zwei Läufen. Bei `master_off_after` geht der Master sofort aus. Bisher liefen die Ventile bis zum Ende ihres Hardware-Countdowns, ein Timer des abgebauten Koordinators buchte den Lauf als vollständig, und die Pumpe ging rund 5 s später aus; eine Kette, die in einer Pause erwischt wurde, ließ die Pumpe bis zum Wiedereinschalten an.
- **Entfernen mitten im Lauf:** Stop service ohne Buchung, denn der Store wird gleich gelöscht. Bei `master_off_after` geht der Master vor dem Löschen aus.
- **Zonen ohne Stop service:** Beim Deaktivieren wird nur bis zum Deaktivieren gebucht, während das Ventil bis zu seinem Countdown weiterläuft, wie heute schon bei einem manuellen Stopp. Die nächste Berechnung kann den Rest einmal nachwässern. Die Doku sagt das jetzt (`docs/configuration-my-zones.md`, Stop service).
- **Neuladen:** Was gebucht wird, bleibt gleich. Weg sind der Abtaster, der bis zum nächsten Neustart tickte und den alten Koordinator im Speicher hielt, Buchungen über den toten Koordinator und ein verirrtes Master-Aus unter dem Lauf des neuen. Liter, die vor dem Neuladen gemessen wurden, gehen weiter verloren (der Lauf wird nach Zeit gebucht), wie über einen Neustart.
- **Batch-Läufe über ein Neuladen:** Ein schon wässernder Batch-Lauf bekommt beim Resume keinen Backstop (`_batch_resume_run`), anders als Service und OpenSprinkler; nach einem Neustart ist das heute schon so. Bisher buchte nach einem Neuladen der tote Backstop den Lauf pünktlich, ließ aber den Master-Hold des Nachfolgers stehen. Jetzt bucht ihn der Watcher des Nachfolgers, bei verpasster Aus-Meldung erst mit der nächsten.

## Tests

- Neue Datei `tests/test_self_closing_teardown.py` (45 Tests). Die Szenen laufen auf der echten `hass`, weil ein Timer, der feuert, genau der Defekt ist:
  - Neuladen mitten in einem gemessenen Lauf: genau eine Buchung, vom Nachfolger; der alte Abtaster tickt nicht mehr. Ein Lauf, der während des Neuladens endet, wartet auf den Nachfolger.
  - Deaktivieren mitten im Lauf: Stopp über den Stop service, ein Teillauf mit dem gemessenen Volumen (50 L, nicht die 1 L nach Zeit und nicht die 100 L des Plans), die wartende Zone startet nicht, genau ein Pumpen-Aus mit `master_off_after` und keins ohne.
  - Deaktivieren in der Absorptionspause einer Rotation: Die Pumpe geht aus, kein zweiter Slot.
  - Entfernen mitten im Lauf, in der Reihenfolge von Home Assistant (erst Entladen, dann Entfernen): Stopp, keine Buchung, Pumpen-Aus nach dem Stopp und vor dem Löschen.
  - Dazu Einheitentests je Baustein und die Reihenfolge der Schritte samt Argumenten.
- `tests/test_distributor.py`: der umgekehrte Test (für beide Flag-Zustände) und drei neue.
- Volle Suite lokal ohne neue Fehlschläge gegenüber `master` (49 neue Tests).
- Mutationstests: 53 Varianten der Änderung, jede von einem benannten Test getötet.
- Live auf einer Testinstanz, jede Szene erst auf dem alten Stand, dann mit dem Fix (Service-Zone mit Bestätigungs-Entität und Durchflusssensor, Master mit `master_off_after`):
  - Neuladen mitten im Lauf: Auf dem alten Stand stand der Abtaster des alten Koordinators nach dem Laufende weiter in der Timer-Liste der Event-Loop (Profiler), noch 13 min nach seinem Start. Mit dem Fix ist er direkt nach dem Neuladen weg. Gebucht wurde auf beiden Seiten genau einmal, nach Zeit. Das Objekt des alten Koordinators stand auf beiden Seiten noch einige Minuten im Speicher; Maßstab ist deshalb die Timer-Liste.
  - Deaktivieren mitten im Lauf: Auf dem alten Stand lief das Ventil bis zum Ende seines Countdowns, ein Timer des abgebauten Koordinators buchte den Lauf als vollständig (180 s), und die Pumpe ging 5 s danach aus. Mit dem Fix schlossen Stop service und Master-Ende Ventil und Pumpe binnen 0,2 s, gebucht wurde ein Teillauf mit dem gemessenen Volumen (61 s, 6,05 L).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
