**Ausgangslage.** Seit #191 rechnet der Saison-Ausblick nach den Regeln der täglichen Berechnung und sagt, dass er eine Veranschaulichung ist. Das Klima darunter ist weiter synthetisch: eine feste Jahreskurve je Breitenband; aus der Höhe kommt nur der Luftdruck. Jede Anlage ab 45° Nord bekommt dasselbe Jahr — Januar 0 °C und 120 mm Regen, Juli 30 °C im Monatsmittel und 60 mm (im Süden gespiegelt) —, und alle Zonen einer Anlage bekommen dasselbe Klima. Im PR hatte ich echte Klimadaten als nächsten Schritt angeboten; du wolltest dafür zuerst ein Issue und hier die Form entscheiden. Keine Bewässerungsentscheidung liest den Ausblick; es geht nur um die Karte, den Dienst und die API.

**Ziel.** Der Ausblick rechnet mit echten Monatswerten für den Ort, wo es welche gibt, und sagt, woher sie stammen. Wo es keine gibt, bleibt die Veranschaulichung als Rückfall.

**Mögliche Quellen**

1. **Ein Klima-Archiv für die Koordinaten der Anlage**, z. B. die Historical Weather API von Open-Meteo: Reanalyse (ERA5 ab 1940), Tageswerte u. a. für Temperatur-Maximum und -Minimum, Niederschlag und FAO-56-ET0. Ohne Schlüssel für nicht-kommerzielle Nutzung, zu der Open-Meteo private Heimautomation ausdrücklich zählt; die Daten stehen unter CC BY 4.0. Einmal Monatsmittel über eine Referenzperiode bilden, speichern, selten auffrischen.
   - Dafür: sofort zwölf Monate für jede Anlage, gleich ob ihre Zonen Sensoren oder einen Wetterdienst nutzen; Open-Meteo ist schon einer der Wetterdienste der Integration.
   - Dagegen: ein neuer ausgehender Abruf mit den Koordinaten, auch bei Anlagen, die bisher keinen Dienst fragen; Gitterweite je nach Modell rund 10 bis 25 km, also kein Mikroklima; die Quelle muss genannt werden.
2. **Die Langzeitstatistik der gemappten Sensoren.** Home Assistant führt für Sensoren mit `state_class` stündliche Mittel, Minima und Maxima (bei Zählern Summen), löscht diese Tabelle nie und liefert sie auch je Monat.
   - Dafür: kein Netz, die eigenen Messwerte am eigenen Ort, und je Zuordnung — Zonen mit verschiedenen Zuordnungen bekämen ihr eigenes Klima.
   - Dagegen: nur für Sensor-Zuordnungen, nicht für Wetterdienste; jeder gemappte Sensor braucht eine `state_class` und der Regen einen Zähler; erst nach einem vollen Jahr sind alle Monate echt, bis dahin fallen fehlende Monate auf die Veranschaulichung zurück.
3. **Beides, gestaffelt:** die eigene Sensorstatistik, wo ein Monat Daten hat, sonst das Archiv, sonst die Veranschaulichung. Am vollständigsten, aber auch der meiste Code und die meisten Tests.

**Zu entscheiden**

- Welche Quelle: 1, 2 oder 3?
- Bei 1: eine Einstellung, die aus ist, bis man sie einschaltet, oder an, sobald Open-Meteo der Wetterdienst ist? Und welche Referenzperiode, z. B. die letzten zehn vollen Jahre oder 1991–2020?
- Soll die Karte je Monat zeigen, woher die Werte stammen (Archiv mit Zeitraum, eigene Sensoren, Veranschaulichung)?

Ohne Präferenz deinerseits würde ich mit 1 als Einstellung anfangen; 2 ließe sich später davorschalten. Ich baue es gern, sobald die Form steht.
