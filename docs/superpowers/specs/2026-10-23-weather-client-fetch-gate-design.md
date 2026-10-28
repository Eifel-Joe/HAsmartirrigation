# Wetter-Clients: ein gemeinsamer Abruf, eine Pause nach dem Fehlschlag

Design für `Eifel-Joe#89` (gleichzeitige Aufrufer verfehlen den Zwischenspeicher, Fehlschläge werden sofort
wiederholt) zusammen mit `Eifel-Joe#20` (`_is_fresh` dreifach byte-gleich). Upstream-Bezug: `JustChr#196`, Bau
zugesagt am 2026-10-20. JustChrs Vorgabe vom 2026-10-15
([Kommentar](https://github.com/JustChr/HAsmartirrigation/issues/196#issuecomment-6200451585)), sinngemäß:

1. ein gemeinsamer Abruf je Client, gleichzeitige Aufrufer warten auf dieselbe Antwort (ein gemeinsamer
   `_is_fresh`-/Abruf-Helfer ist in Ordnung);
2. eine kurze, gespeicherte Pause nach einem Fehlschlag, die `Retry-After` beachtet;
3. eine Pause zwischen den Wiederholungen von Pirate Weather;
4. Tests: gleichzeitige Aufrufer lösen genau eine Anfrage aus; einer für die Pause nach einem Fehlschlag;
5. das Zwischenspeichern auf dem Erfolgsweg bleibt, wie es heute ist.

Basis: `upstream/master` `c46c41fc` (= v2026.10.07). Zeilenangaben beziehen sich auf diesen Commit und auf
`custom_components/irrigation_plus/`, sofern nicht anders angegeben; am 2026-10-23 per `grep -n` auf der Lese-Kopie
`D:\Entwicklung\HASI\issue89-work\read-wt` bestätigt.

**Status: vom User freigegeben am 2026-10-23** („freigegeben“). A1 hat der User entschieden. C1–C13 sind
Entscheidungen von Claude; der User hat sie übertragen („Mach du. Aber begründe deine Entscheidungen auch sehr gut.“).
Vor der Freigabe hat ein unabhängiger Prüfer die Spec aus Sicht des Planenden gelesen; sein einziger Befund (Logs der
Zugriffe von Open-Meteo und Met Office in der Pause) ist in C4 eingearbeitet. Nächster Schritt: Plan
(`superpowers:writing-plans`).

**Abschluss 2026-10-28:** umgesetzt (10 Commits, Kopf `9455f2f5`), live belegt auf HA-Test, PR
[JustChr#199](https://github.com/JustChr/HAsmartirrigation/pull/199). Aus dem Live-Test präzisiert: C5 (Pause ab Beginn
des gescheiterten Laufs, `Retry-After` ab der Antwort). Verlauf im Plan und im Ledger
(`docs/superpowers/probes/2026-10-23-weather-fetch-gate-build/sdd/progress.md`).

## Ziel in einem Satz

Ein Wetter-Client stellt je Dokument höchstens **eine** Anfrage zur selben Zeit, und nach einem Fehlschlag fragt er
eine Weile **gar nicht** — ohne dass sich für irgendeinen Aufrufer etwas daran ändert, was er bei Erfolg oder bei
Fehlschlag zurückbekommt.

## 1. Ausgangslage (gemessen und nachgelesen)

### 1.1 Was gemessen ist (aus `Eifel-Joe#89`)

- **HA-Test** (Pirate Weather, 10 min, 9 Zonen × 2 Zeitpläne): ein Aktualisierungszyklus = 1 echter `get_data` und
  **18** echte `get_forecast_data` in 0,6 s; Zeitplan speichern = **30** echte Abrufe in 0,8 s.
- **HA-Test, 46 h `429`:** 5 505 Fehler in `get_forecast_data`, 552 in `get_data`, jeder mit drei Versuchen.
- **HA-Prod** (OWM, 10 min, 3 × 1): eine Erneuerung brauchte 1 echten Abruf, die nächste **3 innerhalb von 24 ms**.
  Daneben 6–7 Zwischenspeicher-Treffer alle 10–30 s.

### 1.2 Wo heute abgerufen wird — sieben Stellen, je ein Zeitstempel

| Client | Stelle | Zeitstempel (gesetzt in Zeile) | So scheitert sie heute |
|---|---|---|---|
| OWM | `get_data` (:104) | `_cached_data_at` (:155) | **Ausnahme**: `OSError` bei `cod` ≠ 200 (`raiseHTTPError`, :330-334); jeder andere Fehler wird geloggt und weitergeworfen (:157-159) |
| OWM | `get_forecast_data` (:240) | `_cached_forecast_at` (:320) | **`None`** bei Netz- oder JSON-Fehler (:322-323) und bei leerer Liste; **`OSError`** bei `cod` ≠ 200 |
| Pirate Weather | `get_data` (:339) | `_cached_data_at` (:437) | **`None`** bei Nicht-200 nach den Versuchen und bei fehlenden Schlüsseln; andere Fehler geloggt und weitergeworfen (:445-447) |
| Pirate Weather | `get_forecast_data` (:233) | `_cached_forecast_at` (:321) | **`None`** bei Nicht-200 nach den Versuchen, Netz- oder JSON-Fehler (:328-333), fehlendem `daily` |
| Open-Meteo | `_fetch` (:88) | `_cached_doc_at` (:107) | **Ausnahme** (`raise_for_status` :104, Netz, JSON); die drei Zugriffe fangen sie (:195, :305, :471) |
| Met Office | `_fetch_hourly` (:230) | `_cached_hourly_at` (:235) | **Ausnahme** aus `_request` (:136-145); `get_data` fängt und gibt `None` (:459-467) |
| Met Office | `_fetch_three_hourly` (:238) | `_cached_three_hourly_at` (:243) | **Ausnahme** aus `_request`; `get_forecast_data` fängt und gibt `None` (:562-570) |

Die Art des Fehlschlags ist für Aufrufer **bedeutsam**: `__init__.py:1484-1489` und `:1607-1612` fangen bei
`get_data` gezielt `OSError` (einmal als `SmartIrrigationError`, einmal „loggen und überspringen“).

Die Frische-Prüfung ist dreimal byte-gleich (`OWMClient.py:85-90`, `PirateWeatherClient.py:138-143`,
`MetOfficeClient.py:129-134`), Open-Meteo prüft dasselbe inline (`OpenMeteoClient.py:96-102`), und Met Office
rechnet die Lebensdauer in `_forecast_document` noch einmal selbst (`MetOfficeClient.py:321-323`). Jedes der vier
Module hat seine eigene Konstante `_MIN_CACHE_SECONDS = 60` (OWM :37, Pirate :39, Open-Meteo :39, Met Office :62).

Pirate Weather wiederholt bis zu dreimal **ohne Pause** und nur bei einer Nicht-200-Antwort
(`RETRY_TIMES = 3` :71, Schleifen :237-241 und :343-347); eine Netz-Ausnahme bricht die Schleife ab und wird nicht
wiederholt. `Retry-After` liest kein Client.

### 1.3 Wer aufruft — alle über den Executor

Jede der sieben Stellen wird nur über `hass.async_add_executor_job` erreicht, also in einem **Thread** des
Executors, nie in der Ereignisschleife: `calculation.py:581-583`, `:1127-1131`, `:1153-1155`;
`skip_conditions.py:224`, `:245-248`, `:399-401`, `:431-433`, `:471-473`, `:480-482`; `live_estimate.py:328-330`,
`:338-340`; `__init__.py:1484-1486`, `:1607-1609`, `:2116-2118`; `websockets.py:1129`. Die Stundenreihen-Zugriffe, die `live_estimate.py:534` und `:572`
direkt in der Ereignisschleife rufen, lesen nur schon geholte Dokumente und erreichen keine der sieben Stellen
(nachgeprüft: `_SESSION.get`, `_fetch`, `_request` und `_fetch_*` werden nur von den Methoden der Tabelle erreicht).
`validate_key` (Einrichtungsdialog, `helpers.py:862-900`) baut einen eigenen Client und ruft direkt ab.

`override_cache` setzt im Integrationscode niemand (`const.py:437` `ATTR_OVERRIDE_CACHE` hat keinen Nutzer);
nur `tests/test_weather_modules.py:296-304` prüft, dass damit jeder Aufruf abruft.

### 1.4 Was die Dienste bei einer Überschreitung tun

| Dienst | Grenze im kostenlosen Tarif | `429` heißt | `Retry-After` |
|---|---|---|---|
| OWM | 60 je Minute, 1 000 000 je Monat ([Preise](https://openweathermap.org/price)) | mehr als 60 je Minute oder Tages-/Monatsgrenze; Sperre „a couple of hours to several days“ ([FAQ](https://openweathermap.org/faq)) | nicht dokumentiert |
| Pirate Weather | Kontingent je Monat | „your API key has hit the quota for the month“; Kopfzeilen `Ratelimit-Limit`, `Ratelimit-Remaining`, `Ratelimit-Reset`, `X-Forecast-API-Calls` ([Doku](https://docs.pirateweather.net/en/latest/API/alerts-flags-errors/)) | nicht dokumentiert |
| Met Office (Global Spot) | 360 je Tag ([Preise](https://datahub.metoffice.gov.uk/pricing/site-specific)) | Tagesgrenze erreicht ([FAQ](https://datahub.metoffice.gov.uk/support/faqs)) | nicht dokumentiert |
| Open-Meteo | unter 10 000 je Tag, 5 000 je Stunde, 600 je Minute ([Bedingungen](https://open-meteo.com/en/terms)) | — | nicht gefunden |

**Folge für dieses Design:** Kein Dienst sagt nachweislich, wann man wiederkommen soll. `Retry-After` zu beachten ist
Vorsorge (Gateways, Proxys, künftige Antworten); **was die Anlage wirklich schützt, ist die Pause selbst**. Die
Überschreitungen dauern bei allen vier Diensten Stunden bis Wochen, nicht Sekunden.

## 2. Entscheidungen

| # | Frage | Entscheidung | Verworfen |
|---|---|---|---|
| A1 (User) | Was erleben die Aufrufer in der Pause? | **Genau das, was sie heute bei einem Fehlschlag erleben, nur ohne Anfrage.** Keine alten Werte aus dem Zwischenspeicher | alte Werte weiterreichen (neue Ausfall-Regel, Thema von `Eifel-Joe#74`) |
| C1 | Wo sitzt das Tor? | **An jeder der sieben Stellen aus 1.2**, je Zeitstempel ein Tor | ein Tor je Client; Bündelung auf der Aufruferseite |
| C2 | Womit warten gleichzeitige Aufrufer? | **Eine Thread-Sperre je Tor**; die Frische-Prüfung läuft innerhalb der Sperre | `asyncio`-Sperre; Sperre nur um die Anfrage |
| C3 | Was ist ein Fehlschlag? | **Jeder Lauf, der abruft und danach keinen neuen Zeitstempel hinterlässt** | Liste von Status-Codes und Ausnahmetypen |
| C4 | Was gibt die Pause zurück, was loggt sie? | **Das Ergebnis des auslösenden Fehlschlags:** derselbe Rückgabewert, oder eine Ausnahme desselben Typs mit derselben Meldung. **Keine Zeile in `weathermodules/` loggt einen wiedergegebenen Fehlschlag über DEBUG**, auch nicht die Zugriffe von Open-Meteo und Met Office über dem Tor. Die Logs der Aufrufer außerhalb von `weathermodules/` bleiben, wie sie sind | Fehler bei jedem Aufruf erneut loggen; nur bei OWM und Pirate leise |
| C5 | Wie lang ist die Pause? | **60 s, verdoppelt mit jedem weiteren Fehlschlag in Folge, höchstens das normale Cache-Fenster** `max(cache_seconds, 60)`; ein Erfolg setzt zurück | feste 60 s; Pause = Cache-Fenster |
| C6 | Wie zählt `Retry-After`? | **Sekunden oder HTTP-Datum; gilt, wo es länger ist als die Pause aus C5; höchstens 24 h;** unlesbar oder in der Vergangenheit = nicht vorhanden | `Retry-After` statt C5; ohne Deckel |
| C7 | Welche Uhr misst die Pause? | **Eine monotone Uhr.** Die Frische-Prüfung bleibt bei `datetime.datetime.now()` | beides auf der heutigen Uhr; beides monoton |
| C8 | Pirate Weather: wie wiederholen? | **1 s, dann 2 s Pause zwischen den Versuchen.** Eine `429` oder ein `Retry-After` beendet die Versuche sofort. Sonst wie heute | feste Pause; `Retry-After` zwischen den Versuchen abwarten |
| C9 | Wo sitzt der gemeinsame Helfer (`Eifel-Joe#20`)? | **Neues Modul `weathermodules/fetch_gate.py`:** Untergrenze, Lebensdauer, Frische-Prüfung und das Tor. Die vier Kopien weichen | Basisklasse für alle Clients; Helfer in `helpers.py` |
| C10 | `override_cache` | Umgeht wie heute den Zwischenspeicher **und auch die Pause** | Pause auch bei `override_cache` |
| C11 | `validate_key` | **Bleibt außerhalb** des Tors | durch das Tor schicken |
| C12 | Pirate Weathers `Ratelimit-Reset` | **Wird nicht gelesen** | als zweite Quelle neben `Retry-After` |
| C13 | Sperrtyp, Codeform | dem Bauenden überlassen, mit den Leitplanken aus Abschnitt 4 | — |

### Begründungen

**A1 (User).** Bleibt auch der Fehlerweg für jeden Aufrufer gleich, ändert der PR nur die Zahl der Anfragen. Das ist
mit JustChrs Vorgabe 5 vereinbar, lässt sich vollständig testen und braucht keine Aussage darüber, wie alt ein Wert
werden darf. Diese Frage hat ein eigenes Issue (`Eifel-Joe#74`) und gehört nicht in einen PR, der „seltener
anfragen“ heißt.

**C1 — sieben Tore, eins je Zeitstempel.** Jeder Zeitstempel steht heute für genau ein Dokument, das einzeln geholt
und einzeln zwischengespeichert wird. Ein Tor genau dort fasst gleichzeitige Aufrufer desselben Dokuments zusammen und
lässt verschiedene Dokumente unabhängig: OWM holt aktuelle Werte und Vorhersage von zwei Adressen, Met Office zwei
Produkte.
*Ein Tor je Client* brächte kein Zusammenlegen mehr: Pirate Weather holt bei `get_data` und `get_forecast_data`
zwar dieselbe Adresse, speichert aber in zwei Fächern. Es ließe nur einen Abruf auf einen fremden warten — bis zu 60 s
Zeitlimit, bei Pirate dreimal. *Bündelung auf der Aufruferseite* (ein `asyncio`-Helfer, der gleiche Executor-Aufträge
zusammenlegt) müsste die fünfzehn Aufrufstellen aus 1.3 in fünf Modulen umstellen und schützte keinen künftigen
Aufrufer, der den Helfer nicht kennt. JustChr hat ausdrücklich „one shared fetch per client“ verlangt.

**C2 — Thread-Sperre, Frische innerhalb.** Die Clients sind synchron (`requests`) und laufen ausschließlich in
Executor-Threads (1.3). Eine `asyncio`-Sperre wirkt über Threads hinweg nicht. Wer an der Sperre wartet, prüft nach
dem Eintritt die Frische erneut und bekommt den eben gefüllten Zwischenspeicher: Das ist der „eine gemeinsame Abruf“.
Eine Sperre *nur um die Anfrage* reichte nicht, weil das Parsen und das Setzen des Zeitstempels danach kommen: Der
Wartende sähe noch den alten Stempel und fragte selbst. Kosten: Wartende belegen einen Executor-Thread so lange wie der
Abruf dauert. Das tun sie heute auch, nur mit eigener Anfrage. In der Ereignisschleife wird keine der Sperren je
genommen (1.3), sie kann also nicht blockieren.

**C3 — Fehlschlag = kein neuer Zeitstempel.** Die sieben Stellen scheitern auf drei Arten: Ausnahme, `None` nach einem
Nicht-200-Status, `None` nach einem unvollständigen Dokument (1.2). Gemeinsam ist ihnen nur eines: Der Zeitstempel
bleibt stehen. Diese Regel deckt alle drei ohne Aufzählung ab, folgt dem, was der Code heute schon als Erfolg
behandelt, und bleibt richtig, wenn ein Client einen neuen Fehlerzweig bekommt. Eine *Liste von Codes und Typen*
müsste je Client gepflegt werden und übersähe genau die stillen `None`-Zweige.

**C4 — dasselbe Ergebnis, leise.** Das ist A1 wörtlich: Der Aufrufer bekommt, was der Fehlschlag ihm gab, und sein
eigener Umgang damit (Rückfall, Überspringen, `SmartIrrigationError`) läuft unverändert. Der Typ der Ausnahme muss
erhalten bleiben, weil `__init__.py` gezielt `OSError` fängt (1.2). Geloggt wird der Fehlschlag einmal, so wie heute,
beim echten Versuch; in der Pause gibt es keinen neuen Versuch und damit keinen neuen Fehler zu melden. Regel dahinter:
**Eine ERROR-Zeile eines Wetter-Clients heißt: Es gab eine echte Anfrage, und sie ist gescheitert.** Eine Zeile
„Met Office get_data error: …“ ohne Anfrage dahinter ließe eine Pause im Log wie eine Serie frischer Fehlschläge
aussehen, also genau das Bild, das dieser PR beseitigt. Bei OWM und Pirate Weather umschließt das Tor die ganze Methode
samt ihrem `except`; dort folgt die Regel von selbst. Bei Open-Meteo und Met Office sitzt es in `_fetch`,
`_fetch_hourly` und `_fetch_three_hourly`, und die Zugriffe darüber loggen jede gefangene Ausnahme auf ERROR
(`OpenMeteoClient.py:201`, `:311`, `:478`; `MetOfficeClient.py:466`, `:569`). Diese fünf Stellen müssen eine
wiedergegebene Ausnahme erkennen und auf DEBUG loggen, bei unverändertem Rückgabewert (gefunden in der Prüfung der
Spec). Die Logs der Aufrufer außerhalb von `weathermodules/` (etwa `__init__.py:1610`) gehören zu deren eigenem Umgang
mit dem Fehlschlag und bleiben nach A1 unverändert. Die 46-Stunden-Lage vom Oktober hätte statt 6 057 ERROR-Zeilen des
Clients eine je Pause ergeben.

**C5 — 60 s, verdoppelt, gedeckelt auf das normale Fenster.** Drei Maßstäbe:

- *Die Häufung fangen.* Die gemessenen Bursts dauern 0,6–0,8 s (1.1). Schon 60 s legen sie vollständig zusammen.
- *Kurze Störungen schnell überwinden.* Ein einzelner Fehlschlag kostet höchstens 60 s, dann wird wieder gefragt. 60 s
  ist dieselbe Zahl wie die vorhandene Untergrenze `_MIN_CACHE_SECONDS`, deren Kommentar „at most one call per
  method per minute“ verspricht (`OWMClient.py:32-37`). Auf dem Fehlerweg gilt dieses Versprechen heute nicht; mit der
  Pause gilt es auch dort.
- *Im langen Ausfall nie mehr fragen als im Normalbetrieb.* Das entscheidet zwischen den Varianten. Die Aufrufer
  kommen alle paar Sekunden (Prod: 6–7 Abfragen alle 10–30 s, 1.1). Bei *festen 60 s* fragt ein Tor im Ausfall
  1 440-mal am Tag, zehnmal so oft wie im Normalbetrieb bei 10 min (144). Met Office erlaubt kostenlos 360 Abrufe am
  Tag und hat zwei Tore: Normalbetrieb 288, mit festen 60 s im Ausfall bis zu 2 880. Ob fehlgeschlagene Abrufe dort
  mitzählen, ist nicht dokumentiert. Zählen sie mit, verbraucht ein mehrstündiger Serverausfall das Tageskontingent,
  und die Anlage bleibt auch nach der Erholung bis Mitternacht ohne Daten. Mit dem *Deckel auf das normale Fenster*
  fragt ein Tor im Ausfall nie öfter als im Normalbetrieb. Wer im Normalbetrieb ins Kontingent passt, passt auch im
  Ausfall hinein.

Verdoppeln statt gleich das ganze Fenster: *Pause = Cache-Fenster* wäre am billigsten, ließe aber jeden kurzen
Aussetzer ein ganzes Fenster lang wirken, bei täglicher Aktualisierung einen Tag. Die Folge 60, 120, 240, 480 s,
dann das Fenster (bei 10 min: 599 s) erreicht den Deckel mit dem fünften Fehlschlag, also nach 15 Minuten Ausfall.
Bei täglicher Aktualisierung (Fenster 86 399 s, `__init__.py:1356-1358`) wächst die Pause bis zu einem Tag. Das ist
derselbe Abstand, den diese Anlage im Normalbetrieb ohnehin zwischen zwei Abrufen hinnimmt. Ein Erfolg setzt die
Folge zurück. Gelesen wird `cache_seconds` bei jeder Prüfung der Pause, nicht nur beim Fehlschlag, weil
`__init__.py` es nach dem Bau des Clients setzt und später ändert: Eine Intervall-Änderung wirkt so auch auf eine schon
laufende Pause (Präzisierung aus der Umsetzung, Plan Task 3). **Gezählt wird die Verdopplung ab dem Beginn des
gescheiterten Laufs**, so wie der Zyklus von Beginn zu Beginn zählt; `Retry-After` dagegen ab der Antwort, die es
verlangt hat (C6). Präzisierung aus dem Live-Test vom 2026-10-23: Ab dem Ende gezählt, ließen Pirate Weathers gut 3 s
Wiederholungen den nächsten Zyklus am Deckel noch 2 s in die Pause fallen, und ein dauerhaft gestörtes Tor fragte nur
jeden zweiten Zyklus.

**C6 — `Retry-After` als Untergrenze, 24 h als Deckel.** RFC 9110 §10.2.3 erlaubt Sekunden oder ein HTTP-Datum;
beides wird gelesen. „Beachten“ heißt, nicht *früher* wiederzukommen; später ist erlaubt. Deshalb gilt das Längere aus
`Retry-After` und C5, und ein kurzes `Retry-After` hebelt den Ausfallschutz aus C5 nicht aus. Der Deckel von 24 h
schützt vor unsinnigen oder falsch gelesenen Werten. Die Tagesgrenzen von Met Office, OWM und Open-Meteo laufen nach
höchstens einem Tag ab. Am Deckel kostet ein Tor eine Anfrage am Tag; ohne Deckel könnte ein einzelner fehlerhafter
Kopf einen längst wieder erreichbaren Dienst wochenlang stummschalten. Weil kein Dienst `Retry-After` nachweislich
sendet (1.4), wird es nur im Test belegt, nicht live.

**C7 — monotone Uhr für die Pause.** Die Pause misst eine Dauer, keine Uhrzeit. Eine monotone Uhr springt weder bei
der Umstellung auf Winterzeit noch beim Stellen der Systemuhr. Die Frische-Prüfung bleibt auf
`datetime.datetime.now()`, weil JustChr den Erfolgsweg unverändert haben will (Vorgabe 5). Zwei Uhren in einem Modul
sind der Preis dafür; der Code nennt den Grund an der Stelle. Vorbild im selben Code: Der Planer misst seinen
Projektions-Cache schon mit `time.monotonic()` (`scheduler.py:1245`).

**C8 — Pirate Weather: 1 s, dann 2 s; `429` beendet.** Die Werte sind nicht gemessen, sondern der übliche Beginn eines
exponentiellen Rückzugs: Eine kurze Gateway-Störung hat danach Zeit, sich zu legen, und der fehlschlagende Aufruf
dauert höchstens 3 s länger. Das ist klein gegen das Zeitlimit von 60 s je Versuch. Nach dem letzten Versuch wird
nicht gewartet. Eine **`429`** heißt bei Pirate Weather „Monatskontingent erschöpft“ (1.4); ein zweiter Versuch nach
1–2 s kann nicht gelingen und ist eine weitere Anfrage auf einen schon erschöpften Schlüssel. Bei einem
**`Retry-After`** hat der Dienst den Zeitpunkt genannt, und ein Versuch nach 1 s missachtete ihn. Beide beenden die
Versuche und starten die Pause aus C5/C6. Alles andere bleibt wie heute: drei Versuche, wiederholt nur bei
Nicht-200-Status, Netz-Ausnahmen nicht wiederholt. Darum hat JustChr nicht gebeten, und mit der Pause kostet auch ein
`401` nur drei Anfragen je Pause. *`Retry-After` zwischen den Versuchen abwarten* hieße, einen Executor-Thread unter
der Sperre bis zu 24 h schlafen zu lassen. Das ist Aufgabe der Pause, nicht der Schleife.

**C9 — eigenes Modul `weathermodules/fetch_gate.py`.** Darin: die Untergrenze (60 s), die Lebensdauer
`max(cache_seconds, Untergrenze)`, die Frische-Prüfung und das Tor. Die drei `_is_fresh`-Kopien, die Inline-Prüfung
von Open-Meteo, die eigene Lebensdauer-Rechnung in `_forecast_document` und die vier `_MIN_CACHE_SECONDS` greifen
darauf zurück (`Eifel-Joe#20`). Das Modul gehört neben die Clients, die es nutzen; `helpers.py` ist Integrationscode
und baut seinerseits Clients (`helpers.py:870-889`). Eine *Basisklasse* würde die vier Clients umbauen, die
heute unabhängig sind, und wäre mehr Eingriff als die Entdopplung braucht. Die Modulvariable `_SESSION` bleibt in
jedem Client: Vier Testdateien patchen sie dort (`test_weather_modules.py`, `test_pirateweather_daily.py`,
`test_precipitation_guard.py`, `test_precipitation_guard_real_clients.py`).

**C10 — `override_cache` umgeht auch die Pause.** Der Schalter heißt heute: nichts Gespeichertes ausliefern. Ein
gespeicherter Fehlschlag ist auch etwas Gespeichertes. Praktisch ist es folgenlos, weil kein Integrationscode den
Schalter setzt (1.3). Der vorhandene Test bleibt unverändert grün.

**C11 — `validate_key` bleibt außerhalb.** Die Schlüsselprüfung ist eine Handlung des Users im Einrichtungsdialog, auf
einem eigenen Client-Objekt. Sie muss immer wirklich fragen, sonst bekäme ein frisch korrigierter Schlüssel die Pause
des alten.

**C12 — `Ratelimit-Reset` wird nicht gelesen.** JustChr hat `Retry-After` genannt. Pirate Weathers `Ratelimit-Reset`
zählt bis zum Monatswechsel, nicht bis zur nächsten sinnvollen Anfrage. Mit dem Deckel aus C6 brächte es eine Anfrage
am Tag statt einer je Cache-Fenster, und das auf einem schon erschöpften Schlüssel. Der PR-Text bietet es an; baut es
JustChr ein, ist es ein Einzeiler im Tor.

## 3. Verhalten im Einzelnen

**Erfolgsweg** — byte-gleich wie heute: Frische, Untergrenze, Zeitstempel, Rückgabewerte, Log-Zeilen. Neu ist nur,
dass der zweite gleichzeitige Aufrufer auf die Sperre wartet und dann aus dem Zwischenspeicher bedient wird, statt
selbst abzurufen. Die vorhandenen Cache-Tests bleiben ohne Änderung grün (`test_weather_modules.py:287-313`, `:657-664`,
`:879-889`).

**Fehlschlag** — der erste Lauf verhält sich wie heute (dieselben Versuche, dieselbe Log-Zeile, derselbe Rückgabewert
oder dieselbe Ausnahme). Danach hält das Tor fest: Ergebnis, Zahl der Fehlschläge in Folge, Ende der Pause.

**In der Pause** — kein Netzverkehr. Rückgabe wie der auslösende Fehlschlag (C4), eine DEBUG-Zeile mit dem Ende der
Pause, keine ERROR- oder WARNING-Zeile aus `weathermodules/`. Ist der Zwischenspeicher aus einem früheren Erfolg noch frisch, kommt es nicht dazu: Ein frischer Eintrag wird
wie heute ausgeliefert; die Pause greift nur, wo der Client heute abrufen würde.

**Nach der Pause** — der nächste Aufrufer ruft ab. Erfolg → Zähler auf null, Pause gelöscht. Fehlschlag → nächste
Pause nach C5/C6.

Beispiel, 10-min-Aktualisierung (Fenster 599 s), Dienst fällt um 0 s aus und kommt um 1 000 s zurück, Aufrufer
alle paar Sekunden: Abrufe bei 0, 60, 180, 420, 900 s (alle scheitern), dann 1 499 s (gelingt). Fünf Fehlschläge in
25 Minuten statt mehrerer Hundert.

## 4. Dem Bauenden überlassen — mit Leitplanken

- **Codeform des Tors** (Decorator, Kontextmanager, Hilfsmethode) und **Sperrtyp**. Geprüft: Keine der sieben Stellen
  ruft eine andere derselben Client-Instanz mit demselben Tor auf; eine einfache Sperre verklemmt sich nicht. Eine
  reentrante wäre ebenso zulässig.
- **Wie die Antwort zum Tor kommt**, damit es `Retry-After` lesen kann. OWM und Pirate Weather geben bei einem
  Nicht-200-Status `None` zurück, ohne die Antwort herauszureichen; diese Stellen müssen sie dem Tor melden. Bei
  Open-Meteo und Met Office trägt die `HTTPError` aus `raise_for_status` die Antwort.
- **Ausnahmen wiederholt werfen:** Wird dieselbe Instanz in der Pause immer wieder geworfen, wächst ihr Traceback mit
  jedem Wurf, und mehrere Threads werfen sie gleichzeitig. Eine frische Ausnahme desselben Typs mit derselben Meldung
  (oder eine Kopie ohne Traceback) vermeidet beides.
- **Wiedergabe erkennbar machen** (C4): Die fünf Zugriffe von Open-Meteo und Met Office müssen eine wiedergegebene
  Ausnahme von einer frischen unterscheiden, ohne dass sich ihr Typ ändert: Die `except`-Klauseln dort und
  `__init__.py` fangen nach Typ. Ein Merkmal an der Ausnahme und ein kleiner Helfer in `fetch_gate.py`, der die
  Log-Stufe liefert, genügen; die Form wählt der Bauende.
- **Attributnamen bleiben:** Tests setzen `_cached_*`, `_cached_*_at`, `_cached_doc` und `cache_seconds` direkt.
  Namen und Typen dieser Attribute bleiben, wie sie sind; das Tor liest den Zeitstempel aus genau diesen Attributen
  (C3).
- **Die Uhr in den Tests:** Frische (`datetime.now()`) und Pause (monoton) müssen sich steuern lassen. Ob
  `freeze_time(...).tick()` `time.monotonic` mitbewegt, prüft der Plan per Probe; sonst bekommt das Tor eine
  injizierbare Uhr.
- **Die Schleife von Pirate Weather** behält ihre Form; neu sind nur die Pause (`time.sleep`, im Test gestubbt) und der
  Abbruch bei `429` oder `Retry-After`. Der tote Ausdruck `i = i + 1` (:241, :347) darf dabei weg.
- **Kommentare** an der Sperre, an C3, C5, C7 und C8 nach Skill `code-doku` (Wurzel, Fix-Logik, NOT-TO-DO).

## 5. Tests

1. **Gleichzeitige Aufrufer → genau eine Anfrage** (JustChrs erste Bitte), für **jedes der sieben Tore**: Die
   gestubbte Anfrage blockiert, bis mehrere Threads den Aufruf begonnen haben; danach `call_count == 1`, und alle
   bekommen dasselbe Ergebnis. Rot auf `c46c41fc`.
2. **Pause nach dem Fehlschlag** (JustChrs zweite Bitte), je Art (Rückgabe `None`; Ausnahme, Typ und Meldung gleich):
   in der Pause keine Anfrage, dasselbe Ergebnis; nach Ablauf eine neue Anfrage.
3. **Folge und Deckel:** 60 → 120 → 240 s; Deckel bei `max(cache_seconds, 60)`; `cache_seconds = 0` → feste 60 s;
   ein Erfolg setzt zurück.
4. **`Retry-After`:** Sekunden; HTTP-Datum; länger als C5 → gilt; kürzer → C5 gilt; über 24 h → 24 h; unlesbar oder
   vergangen → ohne Wirkung.
5. **Pirate Weather:** zwischen drei Nicht-200-Versuchen `sleep(1)` und `sleep(2)`, nach dem letzten keiner;
   `429` → ein Versuch; `Retry-After` → ein Versuch; Netz-Ausnahme → ein Versuch (wie heute).
6. **Erfolgsweg unverändert:** die vorhandenen Cache-Tests ohne Änderung grün; `override_cache` ruft wie heute bei jedem
   Aufruf ab und umgeht auch eine Pause (C10).
7. **Logs in der Pause** (C4), für jedes der sieben Tore: Der wiedergegebene Fehlschlag erzeugt keine Zeile über
   DEBUG aus `weathermodules/`, auch nicht aus den Zugriffen von Open-Meteo und Met Office; der erste, echte
   Fehlschlag loggt wie heute.
8. **Unabhängige Tore:** Eine Pause auf der Vorhersage hält den Abruf der aktuellen Werte desselben Clients nicht auf
   (OWM, Met Office).
9. **Entdopplung (`Eifel-Joe#20`):** keine Verhaltensänderung, gedeckt durch 6; dazu eine Zusicherung, dass die vier
   Clients dieselbe Frische-Prüfung benutzen.

Volle Suite gegen die Basis-Messung auf `c46c41fc`, gleiche FAILED-/ERROR-Namen wie dort (lokale Vorbestände:
Memory `hasi-local-test-env-rebuild`). Mutationsproben am Tor (Sperre weg, Frische außerhalb der Sperre, Pause nicht
gespeichert, keine Verdopplung, kein Deckel, `Retry-After` als Obergrenze statt Untergrenze, `429` wiederholt, Wiedergabe loggt auf ERROR):
Jede muss mindestens einen Test rot machen.

## 6. Ende-zu-Ende-Kriterium (HA-Test)

Fork-Vorabversion mit diesem Branch auf HA-Test, Pirate Weather, Aktualisierung vorübergehend auf 10 min, DEBUG nur
für `…weathermodules.PirateWeatherClient`; gezählt wie am 2026-10-11 aus den Köpfen der Log-Zeilen.

- **(a) Zyklus:** In einem Aktualisierungszyklus genau **1** echter `get_forecast_data`-Abruf (vorher 18) und
  höchstens 1 `get_data` (vorher 1).
- **(b) Zeitplan speichern:** höchstens **1** echter Abruf je Zugriffsart (vorher 30).
- **(c) Fehlschlag:** Dienst gezielt scheitern lassen (Weg legt der Plan fest, z. B. ungültiger Schlüssel): beim
  ersten Lauf drei Versuche im Abstand von etwa 1 s und 2 s; danach Fehlschlag-Läufe nur im Abstand
  60/120/240/480/599 s, je Lauf eine ERROR-Zeile des Clients. In 30 Minuten höchstens **6** Läufe je Tor. Danach Aktualisierung
  und Schlüssel zurück, HA-Test geprüft wie vorher.
- **Nicht live belegbar:** `Retry-After` (kein Dienst sendet es nachweislich) und die Erholung *innerhalb* einer Pause
  (ein Schlüsselwechsel lädt den Eintrag neu und baut einen frischen Client). Beides deckt nur der Test; der PR sagt
  das so.
- **HA-Prod (optional, eigene Freigabe, nach dem Release):** die Messung vom 2026-10-11 wiederholen (OWM): je
  Erneuerung 1 echter Abruf statt 1 bzw. 3.

## 7. Lieferung

Ein PR an JustChr, Branch von `upstream/master`, nur Code und Tests: kein Frontend, kein `dist/`, keine Übersetzungen.
Ob die Doku Abrufe oder Wiederholungen beschreibt, prüft der Plan; wenn ja, wird sie mitgezogen. Commits in der
Reihenfolge: (1) gemeinsamer Helfer und Entdopplung ohne Verhaltensänderung, (2) gemeinsamer Abruf, (3) Pause nach
dem Fehlschlag mit `Retry-After`, (4) Pausen zwischen den Wiederholungen von Pirate Weather. PR-Text erst deutsch zur
Freigabe, dann englisch; keine Verweise auf unsere Issues (Memory `no-own-issue-refs-upstream`). Danach P2: Kommentar
auf `Eifel-Joe#89` und `#20`, `#42`; Spec und Plan auf `archive/design-history` (P1).

## 8. Ausdrücklich nicht in diesem PR

- Alte Werte in der Pause, Altersgrenzen für Dienstwerte (`Eifel-Joe#74`).
- Met Office' zwei Zeitstempel in `_forecast_document` (`Eifel-Joe#26`); nur die Lebensdauer-Rechnung dort nutzt den
  gemeinsamen Helfer.
- Den Projektions-Cache im Planer (`scheduler.py:84`, `:195`, `:1237-1260`), der die Aufrufer vervielfacht.
- Das Zusammenlegen von Pirate Weathers `get_data` und `get_forecast_data` auf ein Dokument.
- `Ratelimit-Reset` (C12); Wiederholungen bei Netz-Ausnahmen; andere Zeitlimits; Umbau auf `async`/`aiohttp`.
- `validate_key` (C11); die Stundenreihen-Zugriffe, die nur gespeicherte Dokumente lesen.
- Die Uhr der Frische-Prüfung (C7).

## 9. Nebenbefunde (anbieten, nicht bauen)

- **N1 Pirate Weather holt dasselbe Dokument zweimal.** `get_data` und `get_forecast_data` rufen dieselbe Adresse
  (`self.url`, :238 und :344) und speichern getrennt; je Erneuerung zwei Anfragen, wo eine reichte (Open-Meteo macht
  es mit einem Dokument, `OpenMeteoClient.py:88-108`). Ändert den Erfolgsweg, daher eigener Vorschlag.
- **N2 Der Projektions-Cache vervielfacht die Aufrufer.** Nach diesem PR sind die 18 Aufrufe je Zyklus
  Zwischenspeicher-Treffer ohne Netzverkehr, aber weiterhin Executor-Aufträge.
- **N3 `override_cache` ohne Nutzer.** `ATTR_OVERRIDE_CACHE` (`const.py:437`) wird nirgends gelesen, der Parameter
  nirgends gesetzt.
- **N4 Uhr der Frische-Prüfung.** `datetime.datetime.now()` ist naive Prozesszeit. Läuft der Prozess in einer Zone mit
  Sommerzeit, gilt ein Eintrag beim Zurückstellen eine Stunde zu lange als frisch. *Unbestätigt*, hängt von der
  Zeitzone des HA-Prozesses ab.

## Betroffene Stellen

`weathermodules/fetch_gate.py` (neu); `weathermodules/OWMClient.py`, `PirateWeatherClient.py`, `OpenMeteoClient.py`,
`MetOfficeClient.py`; Tests neu, z. B. `tests/test_weather_fetch_gate.py`. Keine Änderung an Aufrufern,
`__init__.py`, `const.py`, Frontend oder Übersetzungen.
