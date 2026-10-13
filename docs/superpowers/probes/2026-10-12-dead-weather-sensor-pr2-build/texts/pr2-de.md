Titel: feat(liveness): a sensor group can pause a silent sensor in the daily calculation

## Problem

Seit #190 merkt die Integration, wenn ein Sensor einer Sensorgruppe verstummt, und meldet es. Gerechnet wird aber weiter mit seinem letzten Wert, so lange der Ausfall dauert (#188). Das ist der zweite der drei PRs, um die du auf #188 gebeten hast: der Schnitt im Tagespfad.

## Fix

- **Einstellung je Sensorgruppe** „Wenn ein Sensor verstummt“: *Pausieren* oder *Letzten Wert behalten*. Wie du es wolltest: Jede bestehende Gruppe lädt als *behalten* und rechnet und erklärt byte-identisch wie bisher; nur neu angelegte Gruppen (Panel und Ersteinrichtung) pausieren. Ein fehlender oder unbekannter gespeicherter Wert gilt als *behalten*. Kein Wechsel der Speicherversion; ein älteres Panel, das den Schlüssel nicht schickt, lässt die Einstellung stehen.
- **Der Schnitt, nur im Tagespfad und nur ohne „Stündliche Verdunstung“.** Für eine pausierende Gruppe sperrt der Commit jedes Feld von Ausfallbeginn + 3 h bis zum Ende (halboffen; ein offener Ausfall bis zum `now` des Commits) und liest dafür nur die Ausfall-Liste aus #190, keine eigene Prüfung. Das Aggregat reduziert ein gesperrtes Feld nur über seine gültige Zeit: eine eingefrorene Zeile in der Sperre zählt nicht, ein Wert wird nicht in eine Sperre hinein gehalten, danach gilt der Wert von davor wieder. Ein kumulativer Regenzähler (`delta`) wird nie gesperrt, eine Regenrate schon.
- **Gebucht wird nur der gemessene Anteil.** Das Modul nennt seine Pflichtfelder (PyETO in der Tagesform: Temperatur, Taupunkt, Wind, Druck; Passthrough: sein ET-Sensor). Die ET wird mit dem Anteil des Fensters multipliziert, in dem alle Pflichtfelder zusammen gültig waren. Ist ein Pflichtfeld das ganze Fenster gesperrt, wird das Modul nicht gefragt: 0 ET, kein „missing“-WARNING, kein Passthrough-ERROR, und das Fenster gilt als verbraucht. Regen wird weiter voll gebucht. Ein stummes Feld, das das Modul nicht braucht (Feuchte, Sonne), ändert den Anteil nicht.
- **Was der Nutzer sieht:**
  - Die Erklärung der Zone nennt die stumme Zeit („Keine Werte von Taupunkt, Luftdruck … von … bis … (Sensor stumm).“) und den gebuchten Anteil in ganzen Prozent, zwischen 1 und 99, solange er nicht genau 0 oder 1 ist.
  - Der Reparaturhinweis aus #190 hat eine Variante für eine Gruppe, die wirklich schneidet: pausierend, ohne Stundenrechnung, und ein offener Ausfall mit einem Feld, das geschnitten wird. Sie sagt, dass die Werte nicht mehr verwendet werden und dass dort, wo die Rechnung ohne sie nicht auskommt, keine ET gebucht wird. Jede andere Gruppe behält den Text aus #190. Der Hinweis wird neu abgeglichen, wenn sich die Einstellung, die Stundenrechnung oder die Zuordnung der Gruppe ändert; das WARNING beim Öffnen folgt derselben Regel.
  - Panel: eine Auswahl in der Karte der Sensorgruppe, alle Texte in 8 Sprachen. Die Doku-Seite zu Sensorgruppen erklärt beide Einstellungen und warnt, dass ein gerätloser Sensor, der nur bei Wertänderung meldet (etwa die Wind-Vorlage auf derselben Seite), bei *Pausieren* in einer windstillen Nacht ausgelassen wird.
- Die zwei Aufzeichnungen (`_record_window_amplitude`, `_record_window_radiation`) lassen ein Fenster aus, in dem ihr Feld gesperrt war.

**Wo der Bau von meinem Vorschlag auf #188 abweicht:**

1. **Die Erklärung** hat zwei Sätze statt einem: die Sperre und der gebuchte Anteil.
2. **Ganzes Mittel × Anteil.** In der Tagesform wird das Mittel aus Wetter- und Prognosetagen als Ganzes mit dem Anteil multipliziert, nicht nur der Wetteranteil.
3. **Teiltage sind eine bekannte Grenze.** Die Tagesform mittelt ein pausiertes Feld über die Stunden, in denen es gemeldet hat; welcher Teil des Tages fehlte, verschiebt das Ergebnis. Ohne diese Grenze ist die Stundenform, die mit dem dritten PR ebenfalls schneidet. Die Doku nennt es.
4. **Stundenform und Live-Schätzung schneiden noch nicht** (dritter PR). Mit eingeschalteter Stundenrechnung bleibt alles wie heute, auch der Hinweistext. Die Live-Schätzung kann einen Lauf während eines Ausfalls deshalb auf mehr ET bemessen, als der Commit danach bucht; das steht in der Doku und am Code.
5. **Zurück auf einen älteren Build:** Ein gesetztes *Pausieren* geht verloren (der ältere Build schreibt die Gruppe ohne den Schlüssel), nach erneutem Update gilt *behalten*. Daten gehen nicht verloren.

## Testing

- 106 neue pytest-Fälle: 94 in vier neuen Testdateien, 12 in `tests/test_sensor_liveness_coordinator.py`; dazu 2 vitest-Fälle für das Speichern im Panel. Darunter: Byte-Identität von Rechnung und Erklärung einer *behalten*-Gruppe, Offset-Stempel in der Ausfall-Liste, Pufferzeilen hinter `now`, eine Static-Zone in einer pausierenden Gruppe, eine Zone ohne oder mit gelöschter Gruppe, ein Regenzähler allein, die Rundung des Anteils.
- 37 Mutationen der tragenden Prüfungen, jede gegen alle fünf Testdateien: jede von mindestens einem Test gefangen.
- Volle Suite lokal (Python 3.12, HA 2024.12): die fehlschlagenden Tests sind namensgleich mit `master`, passed 3819 → 3925. Dazu kommen 36 Teardown-ERRORs „Lingering timer“ neuer Tests, die einen echten Koordinator bauen; dasselbe lokale Muster zeigen 430 bestehende Tests, die CI nicht. `black` sauber; `ruff` (0.16.10, die Version deines letzten CI-Laufs) sauber.
- PR 1 lief auf meiner eigenen Installation (eine EcoWitt-Station, 8 Sensoren) vom 5. bis 12. Oktober ohne einen einzigen Fehlalarm, auch an Tagen mit 95–99 % Feuchte und über einen Neustart.
- Live auf einer Testinstanz (HA 2026.10.0) mit MQTT-Sensoren, die wir steuern: ein Gerät mit Temperatur, Taupunkt, Wind und Druck, ein Regenzähler auf einem zweiten Gerät; drei Gruppen (pausieren, behalten, und pausieren mit nur dem Regenzähler), 3½ h Stille.
  - Nach 3 h: die pausierende Gruppe zeigt die neue Hinweis-Variante und das WARNING mit dem Schnitt-Text; die behaltende Gruppe und die pausierende Gruppe, deren einziger stummer Sensor der Regenzähler ist, zeigen den Text aus #190.
  - „Stündliche Verdunstung“ an: auch die pausierende Gruppe zeigt den Text aus #190, und eine Rechnung ihrer Zone hat keinen Satz; wieder aus: die Variante kommt zurück.
  - Nach der Rückkehr bucht die Zone der pausierenden Gruppe 84 % der ET — genau den vorab aus den gespeicherten Zeiten gerechneten Anteil (Fenster 3 h 42 min, gesperrt 36½ min) —, die Zone der behaltenden Gruppe bucht voll und hat keinen Satz.
  - Dabei gefunden: Die Felder eines Geräts kommen Millisekunden nacheinander zurück, also endet jeder Ausfall zu einem eigenen Zeitpunkt, und die Erklärung schrieb vier gleich lautende Sätze statt eines. Sie gruppiert jetzt nach der Sperre, wie der Satz sie zeigt (eigener Commit, mit Tests für diesen Fall und die Reihenfolge der Sätze).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
