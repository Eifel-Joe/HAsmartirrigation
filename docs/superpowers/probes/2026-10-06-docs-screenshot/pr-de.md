**Titel:** docs: Screenshot von Weather & Location erneuert

## Problem

Der Screenshot in `docs/configuration-weather-location.md` ist vom Juni. Der Karte „Seasonal outlook“ darin fehlt die Hinweiszeile, die ihre Werte eine Veranschaulichung nennt, und sie zeigt die Zahlen von vor #191: die ET mit dem Monatsregen darin, den Regengipfel im Juli.

## Änderung

Nur das Bild `docs/assets/images/configuration-weather-location-1.png`, mit gleichem Pfad, gleicher Breite (2288 px) und gleichem Ausschnitt: Forecast, Weather Records und Seasonal outlook samt Hinweiszeile. Die Testinstanz hat zwei Sensorgruppen, daher stehen zwei Tabellen darin. Den Text der Seite habe ich nicht geändert, er beschreibt die Karte schon so, wie sie jetzt ist.

## Prüfung

Aufgenommen auf meiner Testinstanz, die denselben Integrationscode wie v2026.10.05 fährt: englische Oberfläche, helles Design, doppelte Pixeldichte. Die zwölf Zeilen der Karte stimmen mit der Antwort von `irrigation_plus/watering_calendar` überein, auf eine Nachkommastelle gerundet. Die PNG-Datei trägt keine Metadaten und ist mit 222 kB kleiner als die alte (288 kB).

## Die Karte bei einer Static-Zone

Darum hattest du in den Release-Notes zu v2026.10.05 gebeten. Die Karte nimmt die Monatswerte der ersten Zone im Kalender, also der aktiven Zone mit der kleinsten ID (`view-weather-data.ts`: „the climate columns are identical across zones, so take the first zone's monthly estimates“). Für Regen und Temperatur stimmt das. Die ET-Spalte hängt dagegen vom Modul dieser Zone ab: PyETO liefert die Referenz-ET, Static den Satz der Zone mal die Tage des Monats, Passthrough `average_daily_et` mal die Tage (eine einfache Jahreskurve von 2 bis 4 mm am Tag).

Auf meiner Testinstanz ist die erste Zone eine Static-Zone ohne Satz. Die Karte zeigte dort in allen zwölf Monaten **ET 0.0 mm**, Regen und Temperatur wie im Screenshot. Für die Aufnahme habe ich die beiden Static-Zonen ein paar Minuten deaktiviert, damit eine PyETO-Zone vorn steht, und sie danach wieder eingeschaltet. Eine Passthrough-Zone hat die Instanz nicht; den Passthrough-Fall habe ich nur im Code gelesen, nicht angesehen. Zur Südhalbkugel kann ich nichts beitragen.

Seite und Hinweiszeile nennen die Werte aus dem Breitengrad abgeleitet. Steht eine Static-Zone vorn, gilt das für die ET-Spalte nicht. Soll ich einen kleinen PR schicken, damit die Spalte nicht davon abhängt, welche Zone vorn steht? Die Form überlasse ich dir, etwa die erste PyETO-Zone oder eine ET-Reihe, die von keiner Zone abhängt.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
