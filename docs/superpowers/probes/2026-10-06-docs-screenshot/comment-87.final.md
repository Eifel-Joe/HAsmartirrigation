## English

**PR open:** JustChr#194 (docs only: the image, at the same path, width and crop). Taken on the test instance with the two Static zones disabled for about four minutes so that a PyETO zone came first; both are back on `automatic`.

**What the card shows on a Static zone** (the question from JustChr's v2026.10.05 notes, answered in the PR): it takes the first zone's monthly values, and for a Static zone the ET column is the zone's rate times the days. On the test instance (Static first, no rate) it read 0.0 mm in every month. The PR offers a fix; JustChr decides whether and in what shape. If we build it, it gets a new issue.

## Deutsch

**PR offen:** JustChr#194 (nur Doku: das Bild, mit gleichem Pfad, gleicher Breite und gleichem Ausschnitt). Aufgenommen auf der Testinstanz, die beiden Static-Zonen etwa vier Minuten deaktiviert, damit eine PyETO-Zone vorn steht; beide sind wieder auf `automatic`.

**Was die Karte bei einer Static-Zone zeigt** (die Frage aus JustChrs Release-Notes v2026.10.05, im PR beantwortet): Sie nimmt die Monatswerte der ersten Zone, und bei einer Static-Zone ist die ET-Spalte der Satz der Zone mal die Tage. Auf der Testinstanz (Static vorn, ohne Satz) stand dort in jedem Monat 0.0 mm. Der PR bietet eine Korrektur an; ob und in welcher Form, entscheidet JustChr. Bauen wir sie, bekommt sie ein neues Issue.
