# HASI — Session-Stand

> ⚠️ **2026-09-26: Diese Datei hat einen Datenverlust.** Ein fehlgeschlagenes
> Schreib-Skript (Claude) hat sie geleert; sie lag zu dem Zeitpunkt nicht in Git.
> Wiederhergestellt wurden: der Stand bis **2026-09-21 (4)** aus dem Git-Commit
> `f459ff21`, und die Einträge ab **2026-09-25** aus dem Kontext der laufenden
> Sitzung. **Es fehlt der Schluss des 2026-09-25-Eintrags und alles zwischen
> 2026-09-22 und 2026-09-24** (~250 Zeilen) — siehe die Lückenmarkierung weiter
> unten. Die betroffenen Fakten stehen zum Teil noch in den Memories, den Issues
> und `archive/design-history`.
>
> **Wenn diese Datei wieder einmal leer oder beschädigt ist — zwei Quellen:**
> 1. `D:\Entwicklung\HASI\.session-stand-backups\` — rotierende Kopien, angelegt
>    von einem `PreToolUse`-Hook vor jedem Bash-Aufruf (nur bei Inhaltsänderung,
>    zehn Stände). Der jüngste Stand, minutengenau.
> 2. `git show archive/design-history:docs/SESSION-STAND.md` — der Sitzungsstand
>    wird auf diesem Branch versioniert (er liegt außerhalb der PR-Linie, Regel P1).
>    Älter, dafür verlässlich und auch remote.
>
> **Und die Ursache, damit sie sich nicht wiederholt:** `pathlib.write_text` und
> jedes `open(…, "w")` LEEREN die Datei, bevor sie schreiben. Bricht das Kodieren
> danach ab, bleibt nichts übrig. Nie in place über eine Datei schreiben, die
> nicht in Git liegt — in eine Temp-Datei schreiben und per `os.replace`/`mv`
> darüberlegen, oder das Write-Tool nehmen.

## 2026-10-04/05 (4) — Eifel-Joe#8: PR `JustChr#190` offen (gebaut, live getestet, gefaltet, rebased); JustChr#189 gemergt → stabil v2026.10.04; production v2026.10.05b1

### Stand

- **Upstream (Runden bis 2026-10-05 ≈ 06:10 UTC):** JustChr#189 gemergt 2026-10-04 21:49 UTC (Squash `ef8cceef`,
  inhaltsgleich mit unserem Branch), Release-Commit `bbf2e151` = **v2026.10.04, stabil** (ersetzt v2026.09.17 in HACS).
  **JustChr kommentierte #189 um 06:01 UTC:** Dank; eigene Prüfung (Suite auf dem PR-Kopf, fünf tragende Zeilen gebrochen,
  Übernahme nach Neustart); Abschnitt in den Release-Notes; **Nit „nothing to do for now“:** `async_teardown_self_closing_handles`
  ruft jeden Cancel-Handle ohne try/except; zu JustChr#188 nichts weiter nötig. Der Head-Branch von JustChr#186 wurde
  2026-10-05 05:51 UTC gelöscht (nicht in dieser Sitzung).
- **PR 1 = [JustChr#190](https://github.com/JustChr/HAsmartirrigation/pull/190)** offen, an die Sitzung gebunden; Branch
  `fix/stale-weather-sensor` gepusht = vier Feature-Commits auf `bbf2e151` (`16ed6406` … `bd3b7ebd`; PR-Diff per Patch-ID
  gleich dem gefalteten Stand). Neu belegt auf der neuen Basis: Baseline `bbf2e151` 7/3667/9/415, PR 7/3783/9/415, 422 Namen
  identisch; jeder Commit für sich grün; 60/60 Mutationen, Killer gleich. Lokale Refs: `archive/stale-weather-sensor-tasks`
  (`6c9ba82a`, 41 Task-Commits), `archive/stale-weather-sensor-folded-e9c79ec4` (`1ebf4c0f`).
- **production = v2026.10.05b1** (`5a780270` = `bbf2e151` + Branding + PR 1 + Build), force-gepusht (Backup lokal
  `backup/production-pre-v2026.10.05b1` = `d8c74317`); Pre-Release mit ZIP aus dem SHA (Download byte-gleich, Tag
  remote/lokal = `5a780270`); Suite 7/3792/9/415 = 3667 + 9 + 116. Zwischendurch v2026.10.04b2 (`d8c74317`, auf HA-Test
  installiert, gleicher PR-Code). **HA-Prod unberührt** (v2026.09.30).
- **Live-Test HA-Test bestanden** (`issue8-work\livetest\L-pr1.md`): alle fünf Schritte des Ende-zu-Ende-Kriteriums, beide
  Schreibweisen, der `config_entry_id`-Zweig live (HA 2026.9.3); HA-Test aufgeräumt.
- **Reviews:** Abschluss-Review (Opus) „With fixes“ → Politur-Commit E; Review von E → Commit F; Review von F „OK“. Drei
  Review-Aussagen waren falsch und sind berichtigt. Belege: `issue8-work\deviations.md`.
- **P2 erledigt:** Kommentar auf Eifel-Joe#8; Folge-Issue **Eifel-Joe#82** (Deaktivieren/Entfernen lässt offene Hinweise
  ohne End-Event stehen); #42 Punkt 9 + neuer Punkt 39m.
- **#189-Folgen erledigt (Freigabe 7–10):** Eifel-Joe#9 mit Kommentar geschlossen (JustChrs Merge-Kommentar verlinkt,
  sinngemäß, ein Zitat); JustChrs Nit als **Eifel-Joe#83** (`typ:politur`, `schwere:niedrig`); #42 Punkt 10 durchgestrichen,
  neuer Punkt 39n; Hinweis auf JustChr#190 zum roten Check.
- **CI JustChr#190:** `lint`, `test-ha-floor`, `validate` grün; `test (3.13)` rot **nur im Codecov-Upload** (SSL-Handshake beim
  tokenlosen Fork-Upload) — der Testschritt selbst: 3790 passed, 9 skipped = JustChrs Baseline 3674 + 116.
- **P1:** Spec Revision 3, Plan (Häkchen 0–15), Live-Beleg, Abweichungsprotokoll, Review-Texte, Skripte, Namenslisten →
  `archive/design-history` (mit diesem Eintrag).
- **Worktree `issue9-work\wt` entfernt** (#189 gemergt; Belege im Archiv).

### Verworfen

- Gegenprobe zum Neustart-Test über die Task-7-Mutation: Der Ausfall-Schreibvorgang plant ein Speichern, das
  FINAL_WRITE samt Lebenszeichen schreibt; tragfähig ist „geplantes Speichern abgeschaltet“.
- Live-Aufbau „C sendet denselben Wert jede Minute“: YAML-MQTT schreibt unveränderte Werte nicht → `force_update` +
  Gerät D.
- Browser-Anmeldung für die Testgruppen (Passwort wird nie eingegeben) → `api_post` aus der HA-MCP-Sandbox.
- B3 (Kommentar zu `name=` in zwei Registry-Tests) nicht in PR 1 — reiner Test-Text, nach PR 2 verschoben.

### Fallen

- **Die Upstream-Runde veraltet in Minuten:** JustChr kommentierte #189 eine Viertelstunde nach meiner Runde; erst die
  erneute Prüfung direkt vor dem Push hat den Kommentar gefangen (und einen freigegebenen Text als überholt entlarvt).
- **Review-Begründungen vor dem Weitergeben nachprüfen**; ich hatte die M1-Begründung ungeprüft wiederholt.
- **YAML-MQTT schreibt unveränderte Werte nicht** (`last_reported` steht); nur `force_update: true` schreibt jedes Mal
  (dann rückt auch `last_changed` vor).
- **Ein Prüfgerät belegt einen Zweig nur, wenn der Zweig dort etwas entscheidet** (Gerät C: eigenes Entry = Besitzer).
- **`git status` „M“ nach frischem Bundle-Build** trotz byte-gleichem Inhalt: autocrlf, drei Bundles ohne `eol=lf`.
- **Nach einem Fix-Commit den Rebuild neu aufsetzen** (Build-Commit oben); ein übernommener Branding-Commit braucht auf neuer
  Basis eine neue Message.
- **HA-MCP:** Bestätigungsschlüssel der Best-Practice-Anleitung wechselt stündlich; `ha_config_set_helper` will bei Updates
  die `entry_id`; Sandbox (`ha_manage_custom_tool`): `api_post`/`ws_send` mit der Anmeldung des Servers,
  `delete_saved_tool` ist synchron, `call_tool` kann sich nicht selbst aufrufen.
- **`archive/design-history` ist in `pr139-work\archive-wt` ausgecheckt** — dort committen statt einen zweiten Worktree
  anlegen (ein Branch geht nur in einen Worktree).

### Nächste Schritte

1. **Upstream-Runde zuerst** (alle Autoren, seit 2026-10-05 06:30 UTC): JustChr#190 (Kommentare, Reviews, Re-Run der CI),
   JustChr#188, neue Releases.
2. **JustChr#190 beobachten:** CI meldet die App; Antwort von JustChr → bei Einwand Kommentar in Eifel-Joe#8 (in seinen
   Worten) und Fix im Worktree `issue8-work\wt`; bei Merge #8 schließen, #42 Punkt 9, production-Rebuild, Worktree weg,
   Feldtest-Frage.
3. **HA-Prod:** Update (stabil v2026.10.04 oder v2026.10.05b1 mit PR 1) nur auf Zuruf; v2026.10.05b1 startet den Feldtest,
   den JustChr vor PR 2 sehen will; erster Beet-Lauf frühestens um den 10.10.
4. **Aufräumen:** überholte Worktrees `prodrebuild-1003-work\wt`, `prodrebuild-1004b2-work\wt`, `issue8-work\base-bbf2`.

### Empfohlene Skills

- `superpowers:verification-before-completion`, `pr-workflow`; Memories `hasi-dead-weather-sensor`, `upstream-sweep-first`,
  `hasi-todo-file`, `hasi-production-on-upstream`, `no-own-issue-refs-upstream`, `preserve-design-docs-archive-branch`.

## 2026-10-04 (3) — Upstream-Runde leer; Eifel-Joe#8: Spec Revision 2 + Plan PR 1 an JustChrs Antwort angepasst, probegelaufen, freigegeben

### Stand

- **Upstream-Runde** 06:41 und 08:05 UTC, alle Autoren: leer. `master` = `e9c79ec4`, kein Release nach v2026.10.03,
  JustChr#189 offen (0 Kommentare, 0 Reviews, CI 4/4 grün, mergeable). P2-Scan: nur Eifel-Joe#8 (→ JustChr#188 offen) und
  Eifel-Joe#9 (→ JustChr#189 offen). production `4ebd458c`, 0 behind.
- **JustChr#188** hat genau eine Antwort (2026-10-03 19:13 UTC, `5972596286`); sie ist die Grundlage dieser Arbeit.
- **Spec Revision 2** `docs/superpowers/specs/2026-10-03-dead-weather-sensor-design.md`: JustChrs Bedingungen J1–J5,
  dazu die User-Entscheidungen **8** (PR 2 schneidet nur ohne Stundenrechnung; Masken als Parameter) und **9** (neue Gruppen
  pausieren, Bestand behält; Ausweg im Hinweis und in der Doku). Drei PRs samt Zwischenständen. Hinweistext PR 1 und
  Doku-Abschnitt (DE/EN) stehen in der Spec.
- **Plan PR 1 Revision 2** `docs/superpowers/plans/2026-10-03-dead-weather-sensor-common.md` (16 Tasks): kein
  Schnitt-Versprechen; JustChrs drei Hinweis-Tests (`tests/test_sensor_liveness_repair.py`, echter Store, echte
  Issue-Registry, `freezer`) in den Tasks 9/10/11; Doku-Abschnitt (Task 13); Task 15 Pre-Release + Live-Test HA-Test;
  Task 16 PR + Nachlauf.
- **Probelauf** gegen `e9c79ec4`: 75 Tests grün; Suite 7/3693/9/415 gegen Baseline 7/3618/9/415, 422 Namen identisch;
  20/20 Mutationen; jeder Plan-Block per Skript gegen den Probe-Stand geprüft. Patch
  `D:\Entwicklung\HASI\issue8-work\probe-2026-10-04.patch` (19 Dateien, +1769/−5).
- **User-Freigabe 2026-10-04:** Spec + Plan; Live-Test **Variante 1** (YAML-MQTT unter `hasi_livetest/`, ohne Discovery).
- **P1-Archiv** `e35e4c44` (Spec, Plan, `docs/superpowers/probes/2026-10-04-dead-weather-sensor-pr1/`), gepusht mit diesem
  Eintrag.
- **Aufgeräumt:** Wegwerf-Worktrees `issue8-work\probe-wt` und `issue8-work\base-wt`.
- **Memories:** `hasi-livetest-capability-boundary` (HA-Test hängt am Prod-Broker), `hasi-dead-weather-sensor`.

### Verworfen

- Die Einstellung schon in PR 1: ein Schalter ohne Wirkung, solange nichts geschnitten wird.
- PR 2 schneidet das Aggregat bei jeder Installation: im Stundenbetrieb scheitert dann der Abgleich zwischen Aggregat und
  nachgespielter Bilanz (`calculation.py:999-1008`), die Bilanz fällt still auf die Einmal-Buchung zurück.
- Live-Test per MQTT-Discovery (legte über den Prod-Broker Geräte auf HA-Prod an), per Template-Helfer ohne Gerät
  (Geräte-Pfad liefe nicht live), per eigenem Broker (nähme HA-Test die Z2M-Geräte).

### Fallen

- **HA-Test-MQTT = Broker von HA-Prod:** nie Discovery publizieren, nur ein eigenes Präfix; retained Nachrichten danach
  leeren.
- In der Runden-Tabelle auch Bezüge **vor** dem Fenster nennen, wenn sie gerade Gegenstand der Arbeit sind (User-Rückfrage
  „JustChr hat doch auf #188 geantwortet“, weil #188 in der Tabelle fehlte).
- `check_plan_blocks.py` meldet inkrementelle Blöcke (später ergänzte Importe oder dazwischengeschobene Methoden) als
  „nicht am Stück“; solche Blöcke abschnittsweise prüfen.
- Die CI prüft `tests/` nicht mit black; die Plan-Snippets sind trotzdem black-formatiert (vier angepasst).

### Nächste Schritte

1. **Upstream-Runde** seit 2026-10-04 08:05 UTC, alle Autoren. JustChr#189 ist eine Zeile der Runde: Einwand → Kommentar
   in Eifel-Joe#9, Fix im Worktree `issue9-work\wt`; Merge → #9 schließen, #42 Punkt 10, production-Rebuild, Worktree weg.
2. **Eifel-Joe#8 PR 1 umsetzen** nach dem Plan, in frischer Sitzung mit `superpowers:subagent-driven-development`:
   Tasks 0–14 im Worktree `issue8-work\wt` (Branch `fix/stale-weather-sensor`), dann Task 15 (Pre-Release + Live-Test,
   Freigaben im Chat), dann Task 16 (PR; Texte deutsch, dann englisch zur Freigabe).
3. **HA-Prod:** erster echter Lauf (Beet) frühestens um den 10.10.; ein Update nur auf Zuruf. Das Update auf ein Build mit
   PR 1 startet den Feldtest, den JustChr vor PR 2 sehen will.

### Empfohlene Skills

- `task-loop`, `superpowers:subagent-driven-development` (oder `superpowers:executing-plans`),
  `superpowers:test-driven-development`, `superpowers:requesting-code-review`, `superpowers:verification-before-completion`,
  `pr-workflow`; Memories `hasi-dead-weather-sensor`, `upstream-sweep-first`, `hasi-pr-build-recipe`,
  `hasi-production-on-upstream`, `hasi-livetest-capability-boundary`, `no-own-issue-refs-upstream`.

## 2026-10-04 (2) — Eifel-Joe#9 abgeschlossen bis auf den Merge: Live-Test RED/GREEN, Pre-Release v2026.10.04b1, PR JustChr#189, P2, Archiv; JustChr#188 beantwortet

### Ergebnis der Freigabe (User: „1–7 freigegeben“)

- **PR [JustChr#189](https://github.com/JustChr/HAsmartirrigation/pull/189)** offen, CI 4/4 grün, mergeable; Body =
  `issue9-work\texts\pr-en-body.md` (freigegebener Text + Live-Zeile), Greps vorher leer, kein Doppel-PR upstream.
- **P2:** Eifel-Joe#9 Kommentar `5977317350` + `upstream:gemeldet`; Eifel-Joe#8 Kommentar `5977329194` +
  `upstream:gemeldet` → `upstream:freigegeben`; Kommentare auf Eifel-Joe#15/#51/#67; **neu Eifel-Joe#78** (Master-Abgleich
  beim Neuladen, `groesse:M`), **#79** (Master im Zyklus geändert), **#80** (Batch-Abbruch wirft), **#81**
  (Verteiler-Pause nach Dispatch-Flag), alle `typ:fehler` + `schwere:niedrig`; #42 Punkte 9/10 + 39i–39l (Body
  byte-gleich mit Entwurf geprüft).
- **P1-Archiv** `1cf0dfc1`: Spec + Plan (Baustand), `probes/2026-10-04-unload-teardown-live/` (Belege, Rasterskripte,
  Live-Plan), `probes/2026-10-04-unload-teardown-build/` (Mutations-Treiber + Ergebnis, Spec-Check, Namenslisten, README).
- **Aufgeräumt:** `prodrebuild-1004-work` (Worktree + Branch `rebuild/v2026.10.04b1`; kleine Belege nach
  `issue9-work\rebuild-evidence\`), Worktree `issue9-work\vwt`. **Bleibt:** `issue9-work\wt` bis zum Merge;
  `prodrebuild-1003-work` (SESSION-STAND 2026-10-03 verweist auf dessen `texts\`); lokale Sicherung
  `backup/production-pre-v2026.10.04b1` (= Tag v2026.10.03). Zone 8 behält den Durchflusssensor (User: egal auf HA-Test).
- **Memories:** `hasi-unload-teardown`, `hasi-dead-weather-sensor`, `hasi-production-on-upstream`, `hasi-todo-file`
  aktualisiert, neu `ha-profiler-timer-grid`.

### Stand (vor der Freigabe)

- **Live-Test HA-Test** (Belege `D:\Entwicklung\HASI\issue9-work\livetest\`, je `L1/L2-red/green.md` + Rasterskripte):
  - L1 Neuladen: RED (`v2026.09.30b2`) — der Abtaster des alten Koordinators steht nach Laufende weiter in der
    Timer-Liste (Ticks 12/20/33/55, noch 13,7 min nach Start); GREEN (`v2026.10.04b1`) — direkt nach dem Neuladen weg.
    Buchung auf beiden Seiten genau eine, nach Zeit (12 L).
  - L2 Deaktivieren: RED — Ventil bis zum Countdown, toter Koordinator bucht `completed` 180 s/18,9 L, Pumpe +5,000 s;
    GREEN — Abbruch-Warnung, Pumpe +0,10 s, Ventil +0,17 s (Stop service), Teillauf 61 s/6,05 L gemessen.
  - Methode: Profiler `log_event_loop_scheduled` zeigt Intervall-Timer ohne Ziel → Abtaster am 15-s-Raster ab
    Laufstart erkannt (Offset Epoche−Schleife aus `_TrackPointUTCTime`-Zeilen, über den Neustart konstant).
  - Objektbestand ist **kein** Merkmal: der abgebaute Koordinator bleibt auch mit Fix einige Minuten im Speicher.
  - Aufgeräumt: Flussquelle 0. **Offen (User):** Durchflusssensor an Zone 8 wieder leeren; Profiler darf bleiben.
- **Pre-Release `v2026.10.04b1`** (freigegeben „ohne weitere Rückfrage“): production `d804bbf3` → **`4ebd458c`**
  (Backup `backup/production-pre-v2026.10.04b1`), force-with-lease; Release mit ZIP aus dem SHA (204 Einträge,
  sha256 `2b0a0e48…`, Download byte-gleich, HTTP 200); Tag lokal+remote → `4ebd458c`; HACS/hassfest/Pages grün;
  Rebuild-Suite 7/3676/9/415, Namen identisch. Auf HA-Test per HACS installiert + Neustart (angekündigt).
  **HA-Prod unberührt.**
- **Upstream-Runde 08:0x:** JustChr hat **JustChr#188 am 2026-10-03 19:13 UTC beantwortet** (nach der Runde von
  16:34 UTC): Bau freigegeben, Bedingungen: Einstellung je Gruppe (Bestand: letzten Wert behalten + melden), Design 2 in
  drei PRs (Erkennung zuerst, ohne Verhaltensänderung), drei Repair-Tests, Doku-Hinweis 6-h-Cloud-Takt. Sonst leer,
  `upstream/master` weiter `e9c79ec4`.
- **Text-Bündel zur Freigabe** in `issue9-work\texts\`: `pr-de.md`/`pr-en.md` (Live-Zeile ergänzt), `issues-en.md`
  (A–D + Kommentare #67/#51/#15), `comment-8.md`, `comment-9.md`, `issue42-edits.md`. Tracker-Greps über Diff, Messages
  und PR-Text leer.

### Fallen

- **Lange Sitzung überholt die eigene Upstream-Runde:** die Runde von 16:34 UTC lag vor JustChrs Antwort auf #188
  (19:13 UTC), gefunden erst vor dem PR. Vor jedem Außen-Schritt einer langen Sitzung die Runde wiederholen.
- **Profiler zeigt Intervall-Timer ohne Ziel** — Suche nach `_tick` findet nichts; Raster-Methode: Memory
  `ha-profiler-timer-grid`. Eine Toleranz, die mit k wächst, lässt Tages-/Stunden-Timer durch → k ≤ 60, Basis-Abzug.
- `ha_manage_hacs download`: `repository_id` als `owner/repo`-String (Zahl wird abgelehnt), vorher `update_information`.
- `--jq .body >` hängt ein `\n` an; nach `gh issue edit --body-file` ist die Remote-Fassung genau dieses Byte länger.
- Stop service wird ohne `blocking` gerufen → beim Deaktivieren geht die Pumpe ~70 ms vor dem Ventil aus (gutmütig).
- **Ein Geheimnis-Scan in einer `&&`-Kette hält sie nicht an:** `grep -c` endet auch bei Treffern mit Exit 0; der
  Archiv-Push lief über einen Treffer hinweg (zum Glück nur der Feldname `pw_api_key` in einer Warnnotiz, der
  heutige Zuwachs danach geprüft: 0 Schlüsselwerte, 0 IPs). Vor einem Push gaten: `! grep -qE '<muster>' <dateien>`.

### Nächste Schritte

1. **Upstream-Runde** (alle Autoren, seit 2026-10-04 05:50 UTC — die letzte lief gegen 05:56 UTC): JustChr#189 lesen — Einwand → Kommentar in #9 (Link +
   kurzer Satz), Fix im Worktree `issue9-work\wt`, Greps; Merge → #9 schließen, #42 Punkt 10, production-Rebuild.
2. **Eifel-Joe#8:** Spec + Plan an JustChrs Bedingungen anpassen (Einstellung je Gruppe, Design 2, drei PRs, drei
   Repair-Tests, Doku 6-h-Takt; Hinweistext von PR 1 verspricht KEINEN Schnitt) → User-Freigabe → PR 1 bauen.
3. HA-Prod: erster echter Lauf (Beet) frühestens um den 10.10.; ein HA-Prod-Update auf v2026.10.04b1 nur auf Zuruf.

### Empfohlene Skills

- `superpowers:brainstorming` (Spec-Anpassung #8), `superpowers:writing-plans`, danach `task-loop`; Memories
  `hasi-dead-weather-sensor`, `upstream-sweep-first`, `hasi-unload-teardown`.

## 2026-10-04 — Eifel-Joe#9 gebaut (12 Commits), alle Gates grün, Abschluss-Review „ready“; nichts gepusht

### Stand

- **Upstream-Runde** ab 2026-10-03 15:05 UTC, gefahren 16:34 UTC: leer. `upstream/master` weiter `e9c79ec4`,
  JustChr#188 ohne Antwort, keine offenen PRs. Keine P2-, production- oder HA-Prod-Folge.
- **Bau Eifel-Joe#9:** Worktree `D:\Entwicklung\HASI\issue9-work\wt`, Branch `fix/unload-self-closing-handles`
  (`--no-track`, kein Upstream), **12 Commits auf `e9c79ec4`, Kopf `ab3eb45f`**, 9 Dateien +1319/−67. Ablauf
  subagent-driven: kuratierte Auftragsdateien `issue9-work\prompts\tN-full.md`, Spec-Check per Skript
  (`spec_check.py`: jeder Commit blob-genau = Basis + Plan-Operationen, Testdatei = Folge der Plan-Blöcke, Message),
  Quality-Review je Task mit Re-Review, Abschluss-Review (opus) über die ganze Serie: **„ready for the pull request“**.
- **Nachträge beim Bau**, alle im Plan („Beim Bau …“ / „Nachtrag“) und in der Spec vermerkt: Tests verschärft in Task 1,
  3 (Verdrahtung, Boot-Bereinigung; die Spec-Annahme „dort steht nie ein Timer an“ war falsch), 4, 5, 6, 7 (Schutz der
  Kettenfreigabe), 8 (Reihenfolge mit Argumenten, `off_after`-Parameter, Absorption unter freezegun, Entfernen-Szene);
  **neu Task 4b** (Verteiler ohne Master löscht `_master_on` nicht mehr, upstream-Test umgekehrt), **9a** (Texte:
  Batch-Resume, „kein Service-Zwilling“, Doku-Satz, Entfernen-Kommentar), **9b** (Rückgabewert, Warnzeile).
- **User-Entscheidungen 2026-10-03/04:** Batch-Resume ohne Backstop → eigenes Issue (besteht schon: **Eifel-Joe#15**);
  Verteiler-Flag → Ursache beheben (Task 4b).
- **Gates auf `ab3eb45f`:** volle Suite 7/3667/9/415, die 422 FAILED/ERROR-Namen identisch mit der Baseline
  (+49 Tests: 45 in `tests/test_self_closing_teardown.py`, +4 netto in `tests/test_distributor.py`); Mutationsmatrix
  **53/53** mit benanntem Killer (`final_mutate.py`, `mutate-final-53.txt`); black/ruff sauber; Tracker-Greps über Diff,
  Messages und Baum leer.
- Entwürfe: PR-Text deutsch `issue9-work\texts\pr-de.md` (Live-Test-Zeile offen), Live-Test-Plan
  `issue9-work\texts\livetest-plan.md`. HA-Test gelesen: Zone 8 „Grace Test“ ist die einzige Service-Zone (ohne
  Flusssensor), Master `input_boolean.test_pumpe` mit `master_off_after`, Profiler fehlt.

### Verworfen

- Batch-Resume im selben PR fixen: kein Einzeiler (pausierte Läufe), User: eigenes Issue (#15).
- Verteiler-Flag lokal oder hinnehmen: Ursache in `distributor.py` behoben (User).
- Methode umbenennen in `async_abort_service_runs`: freigegebener Spec-Name bleibt, Docstring ist eindeutig.

### Fallen

- **`| tail -1` verschluckt den Exit-Code von `black --check`:** eine `&&`-Kette lief trotz „would reformat“ weiter,
  9b musste nachgebessert werden. Black immer ohne Pipe prüfen.
- **Bash-Heredoc frisst Backslashes:** `\\f` wurde ein Seitenvorschub im Plan (repariert). Pfade mit Backslash nur per
  Write-Tool oder `chr(92)`.
- **Amend nur auf HEAD:** Nachträge zu älteren Tasks als eigene Commits (9a/9b); `spec_check.py` mappt Commit → Task.
- **Plan-Snippets vor dem Dispatch im Wegwerf-Worktree `vwt` messen** (`verify_task.py`: Stand nach Commit N, RED-Seite,
  Mutanten) und black auf den ganzen Endstand — so fielen ein black-Umbruch und ein unbenutzter Import vorher auf.
- Reviewer-Agenten widerlegen sich gelegentlich selbst (Task 1, Task 6) — jede Behauptung messen, bevor sie in Code geht.

### Nächste Schritte

1. **PR-Text** deutsch → englisch freigeben lassen.
2. **Live-Test HA-Test vor dem PR** (User-Regel 19.09.): Profiler hinzufügen; Zone 8 Flusssensor
   `input_number.hasi_flow_probe` per Panel; RED auf installiertem `v2026.09.30b2`, GREEN auf dem Pre-Release.
3. **production/Pre-Release** (`upstream/master` + 12 Commits + Branding-Cherry-Pick, Version synchron, dist neu) —
   Push freigabepflichtig.
4. **PR** an JustChr, dann **P2**: Eifel-Joe#9 Kommentar + `upstream:gemeldet`, Eifel-Joe#15 Kommentar (Neuladen teilt die
   Lücke, kein Einzeiler, drei falsche Kommentare), #42 Punkt 10; Issue-Kandidaten aus den Reviews nach User-Wahl.
5. **P1-Archiv** (Spec, Plan, Skripte, Belege) nach `archive/design-history`.

### Empfohlene Skills

- `pr-workflow`, `superpowers:finishing-a-development-branch`; Memories `hasi-pr-build-recipe`,
  `hasi-production-on-upstream`, `hasi-livetest-capability-boundary`, `preserve-design-docs-archive-branch`.

## 2026-10-03 (2) — Upstream-Runde leer; Eifel-Joe#9: Spec + Plan freigegeben, Plan probegelaufen; Eifel-Joe#75–#77 neu

### Stand

- **Upstream-Runde** ab 2026-10-03 09:56 UTC, zweimal (10:32 und **15:05 UTC**): leer. `upstream/master` weiter
  `e9c79ec4`, keine neuen Issues, PRs, Kommentare oder Releases; **JustChr#188 ohne Antwort**. Scan-Skript: nur
  Eifel-Joe#8 trägt ein Upstream-Label (offener Bezug #188). Keine P2-, production- oder HA-Prod-Folge.
- **Eifel-Joe#9** (Punkt 10 in #42, nächster nach #8): Befund an `e9c79ec4` neu gelesen, besteht. Spec
  `docs/superpowers/specs/2026-10-03-unload-self-closing-teardown-design.md` und Plan
  `docs/superpowers/plans/2026-10-03-unload-self-closing-teardown.md` (Tasks 0–10), **beide vom User freigegeben**
  (Deutsch, untracked). User-Entscheidung: Deaktivieren stoppt und bucht Service-Läufe wie OpenSprinkler/Batch
  (Option 2), Master gleich aus; Entfernen ohne Buchung; upstream direkt als PR, Verhaltensänderung offen im Text.
  Beim Gegenlesen dazugekommen: Deaktivieren gibt zuerst **alle Ketten** frei (Ketten-Hold in einer Pause).
- **Probelauf gegen `e9c79ec4`:** 33 neue Tests, RED aus dem richtigen Grund (gelesen), dann Task für Task GREEN;
  volle Suite 7/3651/9/415, die 422 FAILED/ERROR-Namen identisch mit der Baseline 7/3618/9/415; **21/21
  Mutationen** getötet; Plantext per Skript Block für Block gegen den Probe-Stand bzw. `e9c79ec4` geprüft.
  Getesteter Endstand: `D:\Entwicklung\HASI\issue9-work\probe-2026-10-03.patch` (6 Dateien, +956/−38; bei
  Abweichung gilt der Patch). Skripte daneben: `probe_mutate.py`, `check_plan_blocks.py`. Probe-Worktree entfernt.
- **Archiv:** Spec, Plan, Patch (als `docs/superpowers/probes/2026-10-03-unload-self-closing-teardown-probe.patch`)
  und der Stand vor dem Posten nach `archive/design-history` **`31112a23`** (Push freigegeben, Blobs gleich).
- **P2 (freigegeben, gepostet, byte-gleich geprüft):** Eifel-Joe#9 Kommentar `5970929205` (Umfang: Deaktivieren,
  Entfernen, Master-Aus-Timer; Probelauf) + `groesse:S` → `groesse:M`. Neu: **Eifel-Joe#75** Master-Kick beim
  Wiederaufnehmen (`niedrig`, `prod-scharf`, `S`), **Eifel-Joe#76** Pumpe bleibt beim echten Herunterfahren an
  (`niedrig`, `M`; **User-Entscheidung: einstellbar**, jede Anlage wählt; Richtung: wer „nach Lauf aus“ nutzt, dessen
  Master auch beim Herunterfahren aus), **Eifel-Joe#77** Abo-Lecks (`niedrig`, `M`; 16 Dispatcher-Abos + der
  `core_config_updated`-Listener). #42: Punkt 10 „Spec + Plan fertig und probegelaufen, Bau als Nächstes“, neue
  Punkte 39f–39h (EN + DE). Texte + Skripte: `D:\Entwicklung\HASI\issue9-work\texts\`.

### Verworfen

- Deaktivieren wie ein Neustart (Option 1) und „nur beim Neuladen kappen“ (Option 3): Begründung in der
  Spec-Tabelle *Entscheidungen*.
- Den Master-Aus-Timer bei jedem Entladen nur kappen: Nach einem Deaktivieren schaltete heute ausgerechnet dieser
  tote Timer die Pumpe ab; deshalb „Master-Zyklus jetzt beenden“ für die Fälle ohne Nachfolger.
- Klassische Läufe beim Entladen abbrechen: kein Resume-Pfad, jeder Lauf endete bei jedem Neuladen vorzeitig.
  (Meine erste Begründung „sonst bliebe ein Ventil offen“ war falsch: ihr `finally` schließt es.)

### Fallen

- **Abschnittstitel mit Plan-Task-Nummern** in einer Testdatei, die upstream geht, sind eigene Verweise (Memory
  `no-own-issue-refs-upstream`) — beschreibende Titel; der Grep steht in Plan-Task 10.
- **Baseline-Suite im selben Worktree:** während sie läuft (~5 min) dort nichts ändern; Entwürfe ins Scratchpad.
- **Mutationen zurücknehmen:** nur gegen einen committeten Probe-Stand per `git checkout --`, sonst ist die Änderung
  weg; das Skript stellt aus dem Speicher wieder her.
- Die Lingering-Timer-Prüfung der HA-Testumgebung macht einen Test mit scharfem Timer zusätzlich zum ERROR — ein
  gutes RED-Signal für Lecks.
- HA-Test hat **keine Profiler-Integration** (für das Ende-zu-Ende-Kriterium nötig; vor dem Live-Test hinzufügen).
- **Freigegebener Wortlaut ist der gezeigte:** Die Issue-Dateien entstanden zuerst aus dem internen Entwurf und wichen
  im Deutschen leicht von der freigegebenen Chat-Fassung ab — vor dem Posten aus der gezeigten Fassung neu geschrieben.
- Der User hatte „Master-Kick beim Wiederaufnehmen“ als meinen Vorschlag gelesen („Warum willst du eine laufende
  Pumpe neu starten?“): Befunde über heutiges Verhalten ausdrücklich als „der Code tut heute …“ formulieren.

### Nächste Schritte

1. **Upstream-Runde ab 2026-10-03 15:05 UTC** (Memory `upstream-sweep-first`); JustChr#188 ist eine Zeile davon.
2. **Bau Eifel-Joe#9 in frischer Sitzung** nach Plan, Task 0 ff., `superpowers:subagent-driven-development`
   (Worktree `D:\Entwicklung\HASI\issue9-work\wt`, Branch `fix/unload-self-closing-handles`). Danach Review, PR-Text
   erst deutsch, dann englisch zur Freigabe, Live-Test auf HA-Test (Pre-Release; RED-Seite vorher), production
   sofort nach dem Bau, P2, P1 — Spec *Lieferung*.
3. **#8:** JustChrs Antwort auf #188 abwarten → Plan Teil 2 (unverändert aus dem vorigen Stand).
4. **HA-Prod:** erster echter Lauf mit #173/#174/#178/#176/#180 frühestens um den 10.10. (Beet zuerst).

### Empfohlene Skills

- `task-loop`, `superpowers:subagent-driven-development`, `superpowers:test-driven-development`,
  `superpowers:requesting-code-review`, `pr-workflow`; Memories `upstream-sweep-first`, `hasi-pr-build-recipe`,
  `no-own-issue-refs-upstream`.

## 2026-10-03 — Upstream-Runde: #160/#159/#149 zu, #187 gemergt; production v2026.10.03 nur Branding; Prod 02.10. ohne Bedarf; Eifel-Joe#8 Spec → JustChr#188

### Stand

- **Upstream-Runde** ab 2026-10-01 08:14 UTC, dreimal, zuletzt **2026-10-03 09:56 UTC** (`upstream/master` `e9c79ec4`
  = Beta v2026.10.03; die späteren Runden zeigten nur unser eigenes JustChr#188, noch ohne Antwort).
  JustChr#160 vom Konto `JustChr` geschlossen (01.10. 08:23, 28 s nach einem Bot-Kommentar; um den Docker-Lauf bat niemand).
  JustChr#159: Live-Hälfte von JustChr selbst gebaut (`faa05b0b`, Beta v2026.10.02), geschlossen. JustChr#149 (Megalos) am 02.10.
  geschlossen. JustChr#187 (clarejor) gemergt (`98859077` + Tests `4b417066`). JustChr#185: Branch `fix/distributor-inlet-open-gate`
  am 03.10. 05:43 UTC vom Konto Eifel-Joe gelöscht (lokal noch da; Spec + Plan liegen im Archiv). Keine Frage an uns, auch nicht
  in den Release-Notes.
- **P2 (freigegeben, gepostet, byte-gleich geprüft):** Eifel-Joe#59 geschlossen (`5966213613`), Eifel-Joe#61 Umfang +Live-Hälfte
  (`5966213914`), Eifel-Joe#22 Nachtrag „#160 zu“ (`5966214027`), #42: 14a/23/24/39b + Watched #149/#160 gestrichen.
  Texte + Skripte: `prodrebuild-1003-work\texts\`.
- **production `d804bbf3`** = `upstream/master` + Branding (0/1), Fork-Release
  [v2026.10.03](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.10.03) (Latest). Belege: Memory
  `hasi-production-on-upstream`. **HA-Prod bleibt auf v2026.09.30** (User: kein Update; v2026.10.03 wirkt bei der Prod-Config nicht).
- **HA-Prod Sunrise 02.10.: kein Lauf, zu Recht** — Regen am 01.10., Eimer nach der 23-Uhr-Rechnung +11,69/+11,23/+10,61; die
  Auslösung lief 07:01:04 (Sprung von `next_irrigation` auf den 03.10.), kein Ventil offen. 03.10. ebenso (`no_demand` 07:02:36).
  Die Fixes #173/#174/#178/#176/#180 haben weiter keinen echten Lauf gesehen. HA-Prod wurde am 02.10. mehrfach (07:55, 12:25–13:50)
  und am 03.10. um 04:20 und 04:56 neu gestartet — Herkunft unbekannt, dem User gemeldet; Irrigation Plus kam jedes Mal sauber hoch.
- **Aufgeräumt:** `prodrebuild-1001-work` und `issue160-work` → `_erledigt` (Worktree abgemeldet, Branch `rebuild/v2026.10.01`
  gelöscht, `45fb7dbc` hängt an Tag v2026.10.01). Neu: `prodrebuild-1003-work\` (Worktree `wt` = `rebuild/v2026.10.03` = production,
  `base` = Baseline-Worktree auf `e9c79ec4`, Suite-Ausgaben, `zip\`, `texts\`).
- **Eifel-Joe#8: Spec fertig und vom User freigegeben** →
  `docs/superpowers/specs/2026-10-03-dead-weather-sensor-design.md` (Deutsch, untracked, P1-Archiv beim Abschluss).
  Faktensammlung (Agent, Kernaussagen nachgelesen): `D:\Entwicklung\HASI\issue8-work\context-2026-10-03.md`.
  Sieben User-Entscheidungen + Schnitt-Varianten: Memory `hasi-dead-weather-sensor`. **Vorschlag als
  [JustChr#188](https://github.com/JustChr/HAsmartirrigation/issues/188) gepostet** (englisch, deutsch freigegeben);
  Eifel-Joe#8: Kommentar `5967152847`, Labels `upstream:gemeldet` + `groesse:L`; **Eifel-Joe#74 neu** (Dienst-Felder,
  `schwere:niedrig`), #42: Punkt 9 + neuer 39e. Alles byte-gleich geprüft; Texte + Skripte: `issue8-work\texts\`.
- Baseline-Worktree `prodrebuild-1003-work\base` entfernt.
- **Spec archiviert** (User-Freigabe): `archive/design-history` `d770d28a` (Spec, Faktensammlung als
  `docs/superpowers/probes/2026-10-03-dead-weather-sensor-survey.md`, Sitzungsstand).
- **#8-Plan, gemeinsamer Teil, geschrieben und probegelaufen:**
  `docs/superpowers/plans/2026-10-03-dead-weather-sensor-common.md` (15 Tasks, Deutsch). Probelauf gegen `e9c79ec4`:
  72 neue Tests grün; volle Suite 7/3690/9/415, FAILED/ERROR-Namen identisch mit der Baseline; 16/16 Mutationen
  getötet; black/ruff sauber. Getesteter Endstand: `D:\Entwicklung\HASI\issue8-work\probe-2026-10-03.patch` (bei
  Abweichung gilt der Patch). Zwei Befunde eingearbeitet (Plan + Spec): (1) Registry-Aufruf ohne offenen Ausfall
  machte 11 Mock-`hass`-Tests rot → `_retire_outages` fragt erst die Liste; (2) **Gerätetausch** (User-Anforderung):
  End-Event für jeden geleerten offenen Ausfall, Selbstheilung für nicht mehr beobachtete Entitäten, Hinweis nennt
  den Tausch. Spec-Präzisierungen 1–6. Probe-Worktree entfernt. **Plan vom User freigegeben**; Plan, Spec (Stand
  Präzisierung 6), Patch (`docs/superpowers/probes/2026-10-03-dead-weather-sensor-probe.patch`) und dieser
  Sitzungsstand nach `archive/design-history` (zweiter Push des Tages, freigegeben) → `1c197e36`, Blobs gleich.

### Verworfen

- Docker-VM für den #160-Feldtest: endgültig vom Tisch, JustChr hat ohne Feldtest geschlossen.
- #8-Varianten (User): weiterrechnen und nur melden; Ersatzwert aus den letzten Tagen; Wetterdienst-Rückfall;
  Erkennung je Entität oder per Zeilenalter; nur laufende Ausfälle; Grenze 1 h/6 h/einstellbar; neue
  Zustands-Entität; Dienst-Felder im selben Zug. Begründungen: Spec, Tabelle *Entscheidungen*.
- Erster Issue-Entwurf auf EcoWitt gestützt (User: „Andere Nutzer haben andere Stationen“) → umgeschrieben auf
  drei Erscheinungsformen je Integration; dabei den Cloud-Relay-Fleck gefunden.

### Fallen

- **Volles Lauf-Log (50) behält nur den neuesten `no_demand`** — ein fehlender Tag ist kein Befund; Auslösung über den
  `next_irrigation`-Sprung belegen.
- **Config-Entry von Irrigation Plus auf HA-Prod = `01M20YP65K7ZSZWSG1KT2RBV5T`**; die alte ID aus der Memory gibt
  `RESOURCE_NOT_FOUND`. `diagnostics_data_path` kann nicht in Listen indizieren (`zones` → `_limit`/`_offset`).
- **Suite-Namensvergleich:** Filter `^(FAILED|ERROR) tests`, sonst zählen Zeilen aus dem Captured-Log mit (425 statt 422).
- **`npm run build` schreibt dist mit LF** → Arbeitskopie zeigt `M` ohne Inhaltsdiff; per `git hash-object` gegen den Blob prüfen,
  dann `git checkout -- dist/`.

- **Ein neuer Aufruf in einem vorhandenen Pfad** (hier: Issue-Registry aus Reset/Quellwechsel) bricht dessen
  Tests mit Mock-`hass`, auch wenn die neuen Tests grün sind → Plan-Probelauf immer mit voller Suite und
  Namensvergleich; nur so fiel es auf.
- **Upstream-Texte:** erst deutscher Entwurf im Chat, dann die englische 1:1-Fassung vor dem Absenden (Memory
  `language-german`); Varianten in Nummernfolge, Präferenz nur als Vermerk (Memory `options-in-numeric-order`).

### Nächste Schritte

1. **Upstream-Runde ab 2026-10-03 09:56 UTC** (Memory `upstream-sweep-first`). JustChrs Antwort auf JustChr#188 ist
   eine Zeile davon: Einwände in seinen Worten als Kommentar auf Eifel-Joe#8; sagt er den Bau zu →
   `upstream:freigegeben`; wählt er Design 1 oder 2 → Spec-Status nachziehen.
2. **#8 nach JustChrs Antwort:** Plan Teil 2 (Schnitt nach seiner Design-Wahl, Erklärungssatz, Doku-Abschnitt
   „Wenn ein Sensor schweigt“) per `superpowers:writing-plans`, dann Umsetzung Teil 1 + 2 in einer frischen Sitzung
   (`superpowers:subagent-driven-development`, Worktree laut Plan Task 0). Ändert er die Pause-Regel oder die
   Hinweis-Form, Texte in Plan Task 12 anpassen. Teil 1 nie allein ausliefern. Plan + Patch nach P1 archivieren
   (Push freigabepflichtig).
3. **Erster echter Prod-Lauf** mit #173/#174/#178/#176/#180: aus der Abnahme des letzten Tages frühestens in rund
   einer Woche (Beet zuerst) — dann Lauf-Log, `watering_now`, Problem-Sensoren prüfen.
4. Sonst weiter nach #42 (nächster offener Punkt nach 9 ist 10, Eifel-Joe#9).

### Empfohlene Skills

- `task-loop`; bei JustChrs Antwort `superpowers:writing-plans` (Teil 2), dann `superpowers:subagent-driven-development`;
  Memories `upstream-sweep-first`, `hasi-dead-weather-sensor`.

## 2026-10-01 — #186 gemergt; production v2026.10.01 nur Branding; #22 zu; #160 per Belegkette beantwortet; Eifel-Joe#73 neu

### Stand

- **Upstream-Runde** ab 2026-09-30 21:43 UTC, zweimal, zuletzt **2026-10-01 08:14 UTC** (`upstream/master` `07891c6e`).
  JustChr#186 am 01.10. 05:26 UTC gemergt als `a503dc40`; Squash-Tree = PR-Kopf `6e061bbc` (`cfb19e35`). Beta
  v2026.10.01. Store bleibt 14.2 → die 14.3-Falle trat nicht ein, HA-Prod braucht keinen Rollback. Merge-Notiz ohne
  Einwand; seine Anmerkung zum Rollback-Test (vendort die Major-Schritte, nicht 09.17s Funktion) gegen **seinen** Tag
  v2026.09.17 (`6d9c69e6`) per AST-Vergleich nachgemessen: nur Name + 5 Zeilen `forecast_weather_entity`-Default.
  JustChr#185: Zustimmung, keine Änderung (Notes nennen das Stopp-Skript). JustChr#160 offen „bis Feldtest“.
- **production `45fb7dbc`** = `upstream/master` + Branding (0 behind / 1 ahead); Fork-Release
  [v2026.10.01](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.10.01). Belege und Schnellweg:
  Memory `hasi-production-on-upstream`. **HA-Prod bewusst nicht aktualisiert** (Code = v2026.09.30).
- **P2:** Eifel-Joe#22 geschlossen (Kommentar `5927482459`); Eifel-Joe#66 Status (`5925869524`); **Eifel-Joe#73 neu**
  (*Next irrigation* schreibt bei jeder Aktualisierung kurz eine leere Projektion: ~180 Zeilen/Zone/h auf HA-Prod,
  Wurzel `self._projection = None` vor dem `await` + HAs `_update_staged`; prod-scharf, niedrig); #42: Punkt 24
  durchgestrichen, 39d = #73, JustChr#160 unter „Watched“. Texte: `prodrebuild-1001-work\texts\`.
- **JustChr#160:** Kommentar `5927469810` — Belegkette statt Feldtest (20 Tests mit getrennten Zonen; Kindprozess
  `TZ=EST5EDT`; Identität auf Prod/Test auf demselben Image wie Container; Store unter der Major-Sperre), Schließen
  vorgeschlagen, Docker-Lauf angeboten (User: Angebot bleibt). Tiefensuche + Analyse:
  `issue160-work\analysis-2026-10-01.md`, Rohberichte `issue160-work\research\`. HACS läuft auf Container (Doku,
  Skript, Code); „nur OS/Supervised“ stammt von HAs Apps-Seite.
- **HA-Prod Sunrise 01.10.:** zu Recht ausgelassen (`skip_reasons: ["precipitation"]`, es regnete); die neuen Fixes
  wurden noch nicht ausgeübt. Für 02.10. (06:43) `will_water: true`.
- **Aufgeräumt:** `prodrebuild-work` und `issue22-work` → `_erledigt` (Worktrees abgemeldet; der unerreichbare
  Referenz-Commit `b381a7cc` „ref t6“ als `_erledigt\issue22-work\ref-t6-b381a7cc.bundle`); Branch
  `rebuild/v2026.09.30` gelöscht. Neu: `prodrebuild-1001-work\` (Worktree `wt` auf `rebuild/v2026.10.01` = production).

### Verworfen

- Docker-Feldtest auf einer Proxmox-VM (Debian, HA Container 2026.9.4, `TZ=UTC`, 09.28 → 10.01 → 09.28 → 10.01):
  User will nicht testen; nur wenn JustChr ausdrücklich darum bittet. Aufbau: Memory `hasi-proxmox-test-vms`.
- „Container kann HACS nicht“ als Schließ-Argument: widerlegt (HACS-Doku, Skript ohne Typprüfung, Code-Historie).
- Zeitprognose „Stable mit #186 bis 15.10.“: zurückgezogen — aus früheren Releases nicht ableitbar (User).
- 08.17-Präzedenz im #160-Kommentar: herausgenommen, aus demselben Grund.

### Fallen

- **Python `write_text` unter Windows schreibt CRLF** — ein so korrigierter Text wird mit CRLF gepostet (inhaltlich
  gleich). Für zu postende Dateien Bytes schreiben oder `newline=""`.
- **Bash-Tool frisst Backslashes auch in `$'\r'` und in jq-Regex** (`\.`) → CR zählen und Regex per Python.
- **Lokaler Tag `v2026.09.17` zeigt auf unseren Fork-Release `bf2b38b7`**, nicht auf JustChrs `6d9c69e6` —
  upstream-Tags per `gh api repos/JustChr/HAsmartirrigation/git/ref/tags/<tag>` auflösen.
- `git show upstream/master:.github/…` zerhackt MSYS → `MSYS_NO_PATHCONV=1` davor.
- `ha_get_history` mit `minimal_response=true` lässt reine Attribut-Updates weg → Churn nur mit `false` sichtbar.
- Agenten-Angabe „21 Stellen“ war falsch (20 Tests); Agentenzahlen vor Verwendung nachmessen.

### Nächste Schritte

1. **Upstream-Runde ab 2026-10-01 08:14 UTC.** JustChrs Antwort auf #160 ist eine Zeile davon: schließt er → in #42
   die Watched-Zeile streichen; bittet er um den Lauf → User fragen, dann neues Issue + VM.
2. **HA-Prod:** Sunrise-Lauf 02.10. (06:43) prüfen — erster echter Lauf mit #173/#174/#178/#176/#180.
3. **Weiter nach #42:** Eifel-Joe#8 (toter Sensor ohne Altersgrenze) — Spec zuerst.
4. Eifel-Joe#73 bei Gelegenheit: kleiner Fix (Projektion lokal sammeln, einmal zuweisen), upstream melden, wenn dran.

### Empfohlene Skills

- `task-loop`, `superpowers:brainstorming` (für #8); Memories `upstream-sweep-first`, `hasi-production-on-upstream`,
  `hasi-proxmox-test-vms`.

## 2026-09-30 (5) — Upstream-Runde leer; production v2026.09.30 mit JustChr#186, HA-Prod aktualisiert

### Stand

- **Upstream-Runde ab 21:07 UTC** (zweimal, zuletzt **21:43 UTC**): nur unser eigener Kommentar auf
  JustChr#185; `upstream/master` unverändert `6654a0ac` (v2026.09.28), kein neues Release, keine
  Review-Kommentare, keine Reviews auf JustChr#186. Scan-Skript: nur bekannte Bezüge. P2-Folgen: keine.
  **Letzter Upstream-Blick: 2026-09-30 21:43 UTC.**
- **Entscheidung User:** JustChr#186 (Store 14.1 → 14.2) **mit** in production, vor dem Merge — gegen
  meine Empfehlung „ohne“. Grundlage der Abwägung: HA-Prod ist HA OS 18.3 / core-2026.9.4 / Python 3.14.6
  (Major-Sperre aktiv), Prozess- und HA-Uhr gehen dort gleich (gemessen: naives `last_calculated`
  23:00:00 beim State-Wechsel 23:00:00+02:00), der Rollback 14.2 → 14.1 ist gutmütig.
- **production `06d151f3`** (Branch `rebuild/v2026.09.30`, Worktree `prodrebuild-work\wt`) =
  `upstream/master` `6654a0ac` + die 20 Commits von JustChr#186 unverändert + ein Build-/Branding-Commit;
  **0 behind / 21 ahead**. Die alte production `7ba872af` (Pre-Release v2026.09.21b1) trug 4
  Observed-Commits — alle über JustChr#162 upstream (5/5 Tests auf master), fielen raus.
  Rollback-Punkt lokal: `backup/production-pre-v2026.09.30` = `7ba872af`.
- **Branding** wie am 21.09.: feldweise in manifest/const/package; ganze Dateien nur README,
  `installation-rename.md`, `test_migrate_domain.py` (seit der Merge-Basis weder von upstream noch von
  #186 berührt) + fork-eigene `brand/` + `test_brand_assets.py`. README-Heads-up nennt JustChr#186 samt
  Rückweg 14.2 → 14.1.
- **Gates:** Versionen synchron (manifest/const `v2026.09.30`, package `2026.09.30`); dist Node 24 = nur
  die Versionszeichenkette in 4 Bundles (Hash-Vergleich nach Ersetzung); black/ruff grün; `en.json` 0 URLs;
  Suite `TZ=UTC` **7/3574/9/380**, 387 FAILED/ERROR-Namen **identisch** mit dem #186-Kopf
  (`issue22-work\measure\impl\final-names.txt`), +9 = Branding-Tests, gesammelt 3590 = 3581 + 9
  (`prodrebuild-work\measure\`). ZIP aus dem SHA: 204 Einträge, gegenüber v2026.09.20 genau 5 neu
  (`actuate.py`, 4 Frontend-Save-Tests), keine fehlt; Branding, beide Versionen, `STORAGE_MINOR_VERSION = 2`.
- **Außen (alles freigegeben):** push `--force-with-lease=production:7ba872af`; Release
  [v2026.09.30](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.09.30) (stabil,
  `--target production`), Remote- und lokaler Tag → `06d151f3`, Asset HTTP 200, Download byte-identisch
  (sha256 `bc28f448…`); CI hassfest + HACS + Pages grün. Kommentar auf Eifel-Joe#22
  (`5920240371`: Prod vor dem Merge + das 14.3-Risiko samt Abhilfe), #42 Zeilen 24 und 14a nachgezogen
  (EN + DE). Texte in `prodrebuild-work\texts\`.
- **HA-Prod:** HACS `update_information` + `download` v2026.09.30, Neustart 23:37 (freigegeben, vorher
  kein Ventil offen). Integration `loaded`, Manifest v2026.09.30 (Eifel-Joe), keine Repairs, Log nur die
  bekannte `via_device`-Deprecation. `last_calculated` vor/nach `2026-09-30 23:00:00` → die Migration hat
  nichts verschoben; neue Stempel Berliner Zeit. **Store-Minor 14.2 NICHT direkt belegt**: `.storage` liegt
  nicht auf der MCP-Leseliste, HA loggt die Migration auf INFO.
- **Prod-Konfig heute (Diagnostics):** `zone_sequencing=sequential` (nicht mehr parallel),
  `forecast_weighting_enabled=false`, observed/live_estimate/hourly an, OWM, Schedule „Sunrise“ finish −30.
- **Aufgeräumt:** `issue66-work` → `_erledigt\issue66-work`; Worktrees `wt` + `pre-wt` abgemeldet (`wt` war
  nur zeilenenden-„dirty“, `git diff` leer → `--force`). Branches `fix/distributor-inlet-open-gate` und
  `prerelease/v2026.09.30b1` stehen noch.

### Verworfen

- #186 erst nach dem Merge in production (meine Empfehlung): User entschied für die Regel „alle
  Eigenentwicklungen sofort“, auch mit Store-Migration.
- Store-Version per Log belegen (Eintrag vor dem Neustart deaktivieren wie auf HA-Test): auf Prod zu
  eingreifend für einen reinen Beleg.

### Fallen

- **HTTP 200 auf `:8123/manifest.json` heißt nicht „HA ist oben“** — kam nach 11 s, der MCP sah noch 502.
  `/api/` = 401 heißt Core-HTTP läuft; der MCP über den Supervisor-Proxy brauchte danach noch ~1 min.
- **`jq .body` hängt einen Zeilenumbruch an:** ein damit geholter Body, per `--body-file` zurückgeschrieben,
  trägt am Ende einen Umbruch mehr (#42, unsichtbar). Beim nächsten Mal den Body per Python ohne Zusatz holen.
- **Fork-Commit-Messages:** „upstream PR 186“ statt `#186`/`JustChr#186` — kein Backlink auf JustChrs PR,
  keine nackte Raute.

### Nächste Schritte

1. **Upstream-Runde** ab 2026-09-30 21:43 UTC (Memory `upstream-sweep-first`).
2. **JustChr#186:** sein Review ist eine Zeile der Runde → `pr-workflow`, `superpowers:receiving-code-review`.
   **Ändert er den Versionsplan (z. B. 14.3): HA-Prod erst auf ein 14.1-Release zurück, dann aktualisieren.**
   Nach dem Merge: Eifel-Joe#22 schließen, `issue22-work` → `_erledigt` (vorher Worktrees `wt`, `ref-wt`,
   `pre-wt` abmelden); der nächste Rebuild trägt #186 über upstream.
3. **User:** Panel auf HA-Prod mit Strg+F5 neu laden (JustChr#182).
4. **Beobachten auf HA-Prod:** der Sunrise-Lauf am 01.10. (Ende ~06:59) ist der erste mit #173/#174
   (Trockenlauf = failed), #178 (`watering_now`), #176/#180 (sequential + observed).
5. Weiter nach #42. Optional an JustChr, separat: CI-Job auf Python 3.14 / HA ≥ 2026.3 (Major-Sperre).
6. Optional: die alten Worktree-Anmeldungen unter `_erledigt` (`issue5-work\wt`, `issue5-work\pre-wt`,
   `issue22-wt-rev3`) abmelden.

### Empfohlene Skills

- `pr-workflow`, `superpowers:receiving-code-review`; Memories `upstream-sweep-first`,
  `hasi-production-on-upstream`.

## 2026-09-30 (4) — Eifel-Joe#22: umgesetzt, reviewt, live getestet; PR JustChr#186 offen

### Stand

- **Basis gewandert:** `upstream/master` `0b9a71bd` → `6654a0ac` (v2026.09.28, JustChr#183–#185). Die
  Plan-Dateien waren unverändert bis auf drei Randstellen; der Plan per `apply_task.py` auf die neue
  Basis = 28 Dateien +1194/−345 wie im Probelauf. Neue Baseline 7/3538/9/380, 387 Namen
  (`issue22-work\measure\impl\`).
- **Branch `fix/weather-buffer-one-frame`** (Worktree `issue22-work\wt`), 20 Commits auf `6654a0ac`,
  Kopf `6e061bbc`: Tasks 1–6 nach Plan (subagent-driven: je Task eine kuratierte Auftragsdatei in
  `issue22-work\prompts\`, Spec-Check per Skript gegen einen Referenz-Worktree `issue22-work\ref-wt`,
  Quality-Review je Task), dazu 11 Review-Fix-Commits. Alles steht als Nachtrag E1–E14 am Plan im Archiv.
- **Vier Review-Funde, alle vor dem PR geschlossen:** (1) die DST-Regeln von `_process_timezone` waren
  nur gepinnt, wo der Prozess selbst DST hat → Kindprozess-Test mit `TZ=EST5EDT`; (2) ein Stempel am
  Rand des Datumsbereichs warf aus der Migration → Setup-Ausfall bei jedem Start → Wächter in
  `lift_legacy_stamp`, `coerce_stamp`, `_parse_stored_as_ha_local`; (3) die Uhr-Umstellung verschob still
  die Szenen bestehender Tests (Coalescing am Wasserstand, Eimer von Hand, Solar-Nacht) → in HAs Rahmen
  neu gebaut, jede Kante per Mutation belegt; (4) die Uhrlesung des Live-Pfads war ungepinnt → das
  Kriterium nimmt `now` aus `_fetch_intraday_inputs`. Dazu Doku/Kommentare und `dt_util.naive_now()`
  (HA 2026.9: Systemzeit trotz des Namens) im Zensus.
- **Gates auf `6e061bbc`:** volle Suite 7/3565/9/380, Namen identisch (3565 = 3538 + 27 neue Tests);
  black/ruff sauber; 34 Dateien +1485/−410; Tracker-Greps über Diff und 20 Messages leer.
  Mutationsmatrix 54/54, nur die 4 unerreichbaren Defaults allein per Zensus.
- **Abschluss-Review (opus):** bereit. Wichtiger Fund: Upstream-CI fährt HA 2025.5.0 und 2026.2.3 —
  keiner hat die Major-Sperre (ab 2026.3, braucht Python ≥ 3.14.2). Spec-Satz A4 korrigiert (A9); der
  Live-Test ist der einzige Beleg der Sperre.
- **Live-Test HA-Test** (core-2026.9.3): Pre-Release `v2026.09.30b2` auf dem Fork (`fabda3c0`),
  L1 14.1→14.2, L2 Rollback auf b1 14.2→14.1 ohne `UnsupportedStorageVersionError`, L3 14.1→14.2, die
  Integration jedes Mal geladen. Methode geändert (Eintrag vor dem Neustart deaktivieren, nach
  `logger.set_level` aktivieren) und so freigegeben. HA-Test bleibt auf b2 (User-Wahl).
- **Außen:** PR `JustChr#186` offen; Kommentar auf Eifel-Joe#22, Index-Zeile in Eifel-Joe#42; Archiv
  gepusht (mit Nachtrag E1–E14, Spec-A9, Live-Protokoll, Skripten).

### Verworfen

- Die verschobenen Test-Szenen per UTC-Pin reparieren: hätte den Uhr-Pin in `test_zone_view_save`
  getötet und die Klemme nicht bewegt → Szenen in HAs Rahmen gebaut.
- Den Kindprozess-Pin in eine eigene Datei: der Mutations-Runner fährt `test_time_provenance.py` → dort.
- Die Inline-Kopien von HAs Uhr (`auto_calc.py`, `live_estimate.py`) auf `local_naive_now()` umstellen:
  Scope; stattdessen Docstring „reads this clock".
- WARNING-Log bei Überlauf in der Migration; Rollback-Hinweis in der Nutzerdoku (die Release-Notes
  tragen ihn).

### Fallen

- **Backslashes im Bash-Heredoc** (Python mit `\\n`) werden gefressen → Code per Write-Tool, dann Skript.
- **`rm -rf` auf das aktuelle Arbeitsverzeichnis** blockiert die Sicherheitsprüfung — dann läuft der
  GANZE Befehl nicht, auch ein Commit vorher in derselben Kette. Liegen geblieben:
  `issue22-work\review\t9fix\copy`, `issue22-work\review\prbase` (Scratch, vom User zu löschen).
- **Runner-Wertung:** `" error"` in der Zusammenfassung zählt als KILLED — keine Testdatei mit
  Baseline-Teardown-Fehlern in den Runner (`test_solar_ingest_clamp.py` 12, `test_manual_bucket_assertion.py` 5).
- **`git archive` schreibt hier CRLF** (`core.autocrlf=true`): Dateigröße auf HA-Test = Blob + Zeilenzahl.
- **freezegun + `hass`-Fixture:** der eingefrorene Moment ist UTC-Wandzeit, HA läuft auf US/Pacific →
  Schreiber auf HAs Uhr stempeln 7 h früher; Tests mit eigenen Stempeln im Frozen-Rahmen bleiben grün,
  verlieren aber ihre Kante. „Namen identisch" sieht das nie.
- Implementer (Sonnet) schreiben `Co-Authored-By: Claude Sonnet 5.5` — akzeptiert, upstream squasht.

### Nächste Schritte

*Am selben Abend korrigiert (Rüge des Users): Der erste Entwurf stellte „JustChrs Review abwarten“
an den Anfang und production hinter den Merge von #186. Beides war falsch, siehe Memory
`upstream-sweep-first`.*

1. **Upstream-Runde zuerst:** alles seit dem letzten Blick, also Merges, geschlossene Issues,
   Kommentare und Releases aller Autoren, und je Fund die Folge für unsere Issues (P2), production
   und HA-Prod. Werkzeug: `python D:/Entwicklung/HASI/_erledigt/issues-work/scan_upstream_refs.py`.
   Befund der Runde vom 30.09. abends: JustChr#185 war um 07:05 UTC gemergt (Squash = unser Branch,
   gleicher Tree), JustChr#181 um 08:56 zu. Eifel-Joe#66 stand trotzdem offen, #42 zeigte „#185 offen“,
   und JustChrs Merge-Notiz enthält eine Frage an uns (Service-Modus ohne `stop_service` bekommt keine
   Nachfrist). **Nach Freigabe erledigt am 30.09., 21:07 UTC:** Antwort auf JustChr#185 (Kommentar
   `5919744076`: gewollt, Abhilfe ist ein Stopp-Skript), Eifel-Joe#66 mit Kommentar geschlossen
   (Labels unverändert), #42 Zeilen 8b/43b nachgezogen. Alles gepostet == freigegeben, Texte in
   `issue66-work\texts\`. **Letzter Upstream-Blick: 2026-09-30 21:07 UTC**, dort setzt die nächste
   Runde an. Offen daraus: `issue66-work` nach `_erledigt`, vorher die Worktrees `wt`
   (`fix/distributor-inlet-open-gate`) und `pre-wt` (`prerelease/v2026.09.30b1`) entfernen.
2. **production neu, Fork-Release, HA-Prod aktualisieren.** Das wartet NICHT auf den Merge von #186
   (Reihenfolge laut Memory `hasi-befunde-vor-features`). HA-Prod hat laut HACS `v2026.09.20`, der
   production-Branch steht auf dem 21.09. und ist 34 Commits hinter upstream, darunter JustChr#182
   (Eifel-Joe#5, prod-scharf). Zu entscheiden: #186 mit seiner Store-Migration auf 14.2 gleich mit in
   production, oder erst nach dem Merge. Die Regel sagt „alle Eigenentwicklungen“, die Migration macht
   es zur Abwägung. Rezept: Memory `hasi-production-on-upstream`; HA-Prod-Neustart nur mit Ja.
3. **JustChrs Review zu #186** kommt, wann es kommt, und wird in der Runde mit gesehen; dann
   `pr-workflow` (neue Commits, Text-Freigabe). Nach dem Merge: Eifel-Joe#22 schließen,
   `issue22-work` nach `_erledigt`, Worktrees `ref-wt` und `pre-wt` entfernen. Der Branch
   `prerelease/v2026.09.30b2` bleibt als Pre-Release-Quelle.
4. Optional an JustChr, separat: ein CI-Job auf Python 3.14 / HA ≥ 2026.3, damit die Major-Sperre im CI
   läuft.

### Empfohlene Skills

- `pr-workflow`, `superpowers:receiving-code-review`; Memories `hasi-production-on-upstream`,
  `upstream-silence-is-not-consent`, `check-before-duplicating-work`.

## 2026-09-30 (3) — Eifel-Joe#22: Rev-4-Nachtrag freigegeben, Plan geschrieben und probegelaufen

### Stand

- **Basis unverändert** (`upstream/master` = `0b9a71bd`) → Baseline 7/3466/9/367 (374 Namen) aus
  `issue66-work\measure` weiterverwendet, Kopie in `issue22-work\measure\`.
- **Nachtrag zu Revision 4** (A1–A8, vom User freigegeben): B; Migration über die **Minor**-Version
  14.1 → 14.2 (`STORAGE_VERSION` bleibt 14); Split `_async_migrate_major` + dreiargumentiger Hook;
  JustChrs Zwei-Argument-Test; Inhalt des Migrationskommentars (beide Annahmen); Zeilen auf `0b9a71bd`
  (Skript: 718 Verweise, 0 Abweichungen). Archiv-Commit `8fc79c63`.
- **Plan** `docs/superpowers/plans/2026-09-30-weather-buffer-one-frame.md` (archive) — Tasks 0–11,
  **Tasks 1–8 probegelaufen** in `issue22-work\probe-wt` (Branch `probe/weather-buffer-one-frame`,
  danach samt `base-wt` entfernt; Serie als Patches in `issue22-work\measure\dry-run-series\`),
  jeder Codeblock per Skript aus dem Plan (`probe\plan_blocks.py`, `probe\apply_task.py`). Messwerte
  im Plan-Kopf; Befunde D1–D7 am Planende. Kurz: Wirkungsprobe 9 kippende Tests (3 Umkehrungen,
  6 Prozess-Uhr-Erwartungen); Matrix auf `0b9a71bd` rot als Versatz (daily Stunden 10.5–12.5 statt
  12.5–14.5, live 5,0 h statt 3,0 h, Schreiber 10:00 statt 12:00, Klemme 814,5 statt 1000 W/m²,
  Zensus 20 Stellen); volle Suite 7/3489/9/367, dieselben 374 Namen (+23 neue Tests); Mutationen
  33/33 getötet, 15 der 19 Uhrstellen auch verhaltensmäßig (Rest: 4 unerreichbare Vorgaben).
  Diff 28 Dateien, +1194/−345 (Produktion+Doku +252/−226, Tests +942/−119).
- **Neu gegenüber der Spec:** Nutzerdoku zur Container-`TZ` (`usage-troubleshooting.md`,
  `installation-download.md`) wird durch B falsch → Task 6 schreibt sie um (TZ beim Upgrade nicht
  ändern). Mit der Plan-Freigabe vorgelegt.
- **HA-Test:** core-2026.9.3, HA OS 18.3, Europe/Berlin → Major-Sperre aktiv, Live-Test L2 übt sie.
- **Kein Produktionscode** im echten Branch; der Rev-3-Worktree `issue22-work\wt` ist unverändert
  (Task 0 verschiebt ihn nach `_erledigt`).
- **Plan und Außenaktionen vom User freigegeben.** Stands-Kommentar Eifel-Joe#22 `5910516906`
  (gepostet = freigegeben, JSON-Vergleich 6083 = 6083 Zeichen; Label bleibt `upstream:freigegeben`);
  `archive/design-history` mit Nachtrag, Plan, Probe-Skripten und diesem Stand gepusht
  (`2a669c0f..0c8e13c1`). **Danach lokal `a1ce4914`, NICHT gepusht:** der Mutations-Runner tötet
  bei einem Hänger jetzt seinen eigenen Prozessbaum per PID (Plan-Befund D8; im Probelauf hing
  nichts, die Zahlen stehen). Geht mit der nächsten Archiv-Freigabe mit; die Umsetzung liest den
  Runner ohnehin aus `pr139-work\archive-wt`.

### Verworfen

- **Ein-Stunden-Szene der Matrix** (D1): `_hour_multiplier` rechnet `abs(now − watermark)`; mit
  +2 h Versatz ergibt |11 − 12| = 1 h die richtige Stunde → Tageszelle nach der Migration blind.
  Jetzt drei Stunden.
- **Zensus als einziger Wächter** (D7): 13 der 19 Uhrstellen tötete im ersten Mutationslauf nur die
  Quelltext-Suche; mit konstanten Messwerten sind Zeilenstempel für Fenster und Zeilenstunden
  unsichtbar. Jetzt treibt die Datei jeden erreichbaren Schreiber einmal an.
- Vendoring der 09.17-Migrationsfunktion in die Tests (A4).

### Fallen

- **Auto-Mode-Klassifikator fiel 5× in Folge aus** ("no verdict") → mit Lesewerkzeugen weiter, später
  wiederholt; nach 10 Ausfällen bricht der Turn ab.
- **Arbeitskopie ist CRLF**: Skripte lesen/schreiben Bytes; `sed -i` unter Git Bash schreibt LF
  (harmlos, Git normalisiert). Grep über `tests/` trifft `__pycache__` → `--include=*.py`.
- **Vordergrund-`sleep` ist gesperrt** → Hintergrund-Lauf mit `until …; do sleep …; done`.
- **Jeder Test hat `hass`** (conftest autouse) → HA auf US/Pacific überall (Memory berichtigt).
- Der Mutations-Runner darf nicht parallel zu einer Suite im **selben** Worktree laufen (er ändert
  Quellen) → zweiter Worktree auf demselben Commit.

### Nächste Schritte

1. **Umsetzung in eigener Sitzung**: Plan Task 0 → 11, `superpowers:subagent-driven-development` +
   TDD; Task 10 (Live-Test HA-Test) und Task 11 (PR) mit Freigaben. Vorher `git fetch upstream`:
   steht `upstream/master` nicht mehr auf `0b9a71bd`, zuerst Plan Task 0 Schritt 1 (Anker neu lesen,
   Baseline neu messen).
2. Danach production neu bauen mit allem Neuen (upstream + JustChr#185 + dieser PR + Branding),
   Fork-Release, HA-Prod-Update (Neustart nur mit Ja).

### Empfohlene Skills

- `superpowers:subagent-driven-development`, `superpowers:test-driven-development`, `code-doku`,
  `superpowers:requesting-code-review`, `pr-workflow` + Memory `hasi-pr-build-recipe`;
  Memories `ha-store-major-version-guard`, `hasi-local-test-env-rebuild`,
  `non-idempotent-coercion-needs-inventory`.

## 2026-09-30 (2) — Eifel-Joe#66: Live-Test L1–L5 bestanden, JustChr#185 offen, Issues + Archiv nachgezogen

### Stand

- **Basis unverändert** (`upstream/master` = `0b9a71bd`, 0 behind) → keine neue Baseline.
- **Wegwerf-Build `v2026.09.30b1`** (`7cb8d9c7` = `2c221a7a` + Versionsstring in 7 Dateien, byte-geprüft),
  Branch `prerelease/v2026.09.30b1` (origin), Pre-Release mit ZIP (Download byte-gleich), per HACS auf
  **HA-Test installiert — läuft dort weiter**. Worktree `issue66-work\pre-wt`.
- **Live L1–L5 alle wie erwartet** (Protokoll: `docs/superpowers/reconstructed/2026-09-30-distributor-inlet-open-gate-live-on-ha-test.md`,
  Abweichungen: Plan-Nachtrag A15). L3 in zwei Varianten (User-Entscheid): ungesehene Flanke → Position
  **einen zurück, `synced`**; gesehene Flanke vor Neustart → Position stimmt; Gutschrift in beiden verloren.
- **`JustChr#185` offen** (Branch `fix/distributor-inlet-open-gate`, 12 Commits, trackt jetzt `origin`;
  an die Sitzung gebunden). Body = Entwurf. CI: bei Einreichung keine Checks (Fork-PR, JustChr muss freigeben).
- **Issues:** Eifel-Joe#66 Kommentar + `upstream:gemeldet`; Eifel-Joe#69 L3-Messung + **`schwere:hoch`**;
  Eifel-Joe#42 Body (8b Status, #69 → 8c, #72 → 25e) + Kommentar. Alles gepostet = Entwurf (JSON).
- **Archiv:** `1fea6206` (Protokoll, Belege, Mutations-Runner/-Ergebnisse, Task 10, A15) + Schluss-Commit
  (Task 11, A16, dieser Eintrag). Plan hat keine offenen Kästchen mehr.
- HA-Test zurückgesetzt wie vorgefunden (Verdrahtung, `count`, Position 3, No-op-Skript gelöscht,
  `off_delay` 0, Logger `warning`, Meldung weg). Bleibt: Build + Verlauf/Gutschriften der Mitglieder.
- **Workspace aufgeräumt** (User-Wunsch): 37 erledigte Ordner/Dateien nach
  `D:\Entwicklung\HASI\_erledigt\` verschoben — **nichts gelöscht**; `_erledigt\README.md` listet sie und
  sagt, wie alte Pfade in Archiv-Docs aufzulösen sind. Die zwei `issue5-work`-Worktrees per
  `git worktree move` (weiter registriert). **Zugangsdaten** vom User nach `D:\Entwicklung\HASI\secrets\`
  umgezogen; **MCP-Client** jetzt `D:\Entwicklung\HASI\tools\mcp_test.py`, die vier Hilfsskripte in
  `issue66-work` zeigen dorthin (live getestet). Oben bleiben: Repo, Notizen, `issue66-work`,
  `issue22-work`, `pr139-work` (Archiv-Worktree), `secrets`, `tools`.

### Verworfen

- **Erster L3-Versuch** mit `sonoff_emu_valve`: `initial: false` → nach jedem Neustart `off`. Neu mit
  `grace_emu_valve` (behält den Zustand).
- **Freigaben selbst eintragen** (`update-config`): vom Auto-Mode-Klassifikator als Selbstmodifikation
  blockiert. Der User hat die Regeln selbst in `D:\Entwicklung\HASI\.claude\settings.local.json`
  eingetragen (`mcp__HA-Test`, `mcp__Claude_Browser`, `Bash(…python.exe D:/Entwicklung/HASI/issue66-work/live/live66.py:*)`).

### Fallen

- **Neue Berechtigungsregeln greifen nicht in der laufenden Sitzung** (danach trotzdem Rückfragen).
  unbestätigt: in der nächsten Sitzung wirksam.
- **`$?` hinter `$(…)` in derselben `echo`-Zeile** ist der Status der Ersetzung — meine erste
  Bundle-Prüfung meldete fälschlich „unverändert".
- **MCP-`ha_read_file` liefert UTF-8 als Latin-1** (Zeichensalat) → vor dem Vergleich `.encode("latin-1")`.
  Ebenso zeigen Benachrichtigungen über MCP `Ã¤`; im UI korrekt.
- **`ha_config_set_script` auf HA-Test verlangt `BestPracticeKey`** (Strict-Modus): erst
  `ha_get_skill_guide(skill=home-assistant-best-practices, file=SKILL.md)`, Schlüssel rotiert stündlich.
- **Verteiler mit Stop-Dienst stoppt am Zielvolumen**: bei Messfühler 10 L/min enden 61-s-Abschnitte nach 20 s.
- **`watch_mode`/Verdrahtung nur über HTTP-View** → Browser-Bereich muss bei HA-Test angemeldet sein
  (User), dann `hass.callApi("POST", "irrigation_plus/distributors", {id: 0, …})`.
- User will **weniger Freigaberunden**: Außenwirksames gebündelt in EINER Freigabe vorlegen; HA-Test ist
  Wegwerf — keine Zeitplan-Fristen dort (Memory `ha-test-no-schedule-caution`).

### Nächste Schritte (User-Entscheid 2026-09-30: „Verteiler ist für mich nicht hoch. Ich habe noch keinen.")

1. **Eifel-Joe#22 fertigstellen** (nächste Sitzung): Rev-4-Nachtrag (Minor 14.1 → 14.2, Test über den
   zweiargumentigen Migrationspfad — JustChr#160, Kommentar `5894821423`), dann Plan auf Revision 4
   (Variante B), probelaufen, umsetzen, PR. Basis neu messen: `upstream/master` ist `0b9a71bd`, die
   Rev-4-Messungen liefen auf `1876aa03`.
2. **Danach production neu bauen mit allem Neuen** (upstream + #185 + #22-PR + Branding), **neues
   Fork-Release**, **HA-Prod aktualisieren** (Neustart nur mit Ja). Stand heute: HA-Prod `v2026.09.20`,
   `origin/production` = `7ba872af`, 30 behind / 6 ahead; `STORAGE_VERSION` 14 in beiden → Rückweg offen.
3. **`JustChr#185` nebenbei begleiten:** CI lesen, sobald JustChr die Workflows freigibt; Einwände wörtlich
   in Eifel-Joe#66 (Regel P2); Nachbesserung als neuer Commit.
4. **Nach dem Merge von #185:** Eifel-Joe#66 schließen; `issue66-work\pre-wt` + `prerelease/v2026.09.30b1`
   (lokal + origin) + Release/Tag `v2026.09.30b1` löschen; `issue66-work` nach `_erledigt`. Zu
   Eifel-Joe#5 bleibt nur noch das Außen-Aufräumen (Remote-Branches, Release `v2026.09.29b1`) — Entscheidung
   des Users; die Ordner liegen schon in `_erledigt`.
5. Verteiler-Themen (Eifel-Joe#69 u. a.) sind für den User höchstens mittel (Memory
   `hasi-befunde-vor-features`); #69 wurde heute nach seiner Body-Regel auf hoch gesetzt → mit Freigabe
   zurück auf `schwere:mittel`, Index 8c → 25b (Kommentare #69 `5905029472`, #42 `5905030371`;
   gepostet = Entwurf).

### Empfohlene Skills

- `pr-workflow` + `superpowers:receiving-code-review` (JustChrs Review zu #185); für den Prod-Rebuild
  Memory `hasi-production-on-upstream`; für Eifel-Joe#69 `task-loop` + `superpowers:brainstorming`.

## 2026-09-30 — Eifel-Joe#66: Plan probegelaufen, Tasks 0–9 umgesetzt, finales Review „Yes"

### Stand

- **Probelauf** (User-Vorgabe) im Wegwerf-Worktree `issue66-work\probe-wt` (detached auf `0b9a71bd`,
  danach entfernt): Tasks 1–8, jedes RED/GREEN wie vorhergesagt; volle Suite 7/3506/9/367 mit den 374
  Baseline-Namen; Matrix 18/18. Plan: Abschnitt „This plan was run once …" + Nachtrag A1–A9, Spec-Erratum
  (Neustart-Satz) — beides freigegeben und auf `archive/design-history` `09f3d19c` gepusht.
- **Umsetzung** subagent-driven (Sonnet-Implementer, Spec-Check teils mechanisch per Skript, Quality-
  Reviews Sonnet, Final-Review Opus): Branch `fix/distributor-inlet-open-gate` in `issue66-work\wt`,
  **12 Commits, nichts gepusht**. Commits, Zahlen und alle Abweichungen: Plan, Nachtrag A10–A14 +
  „Execution record". Endstand `2c221a7a`: volle Suite 7/**3521**/9/367, Namen identisch; Matrix
  **36/36** (MUT 5 per Einzellauf, Deadlock); dist == Frischbau; Lint sauber (auch CI-Versionen).
- **User-Entscheidungen dieser Sitzung:** Planänderungen A1–A9 frei; Spec-Erratum + Archiv-Push; **A12:
  Notify-Guard an der Wurzel** (`_dist_notify`, deckt Ablehnung, Halt im Sweep, Neustart-Abgleich,
  warn-Watch) — ändert Upstream-Verhalten im Halt-Pfad, **im PR-Body benennen**.
- **Finales Review:** „Yes, ready for the PR"; Befunde in `842a4cec`/`2c221a7a` eingearbeitet. Für den
  PR-Body: A12, Upgrade-Wirkung (Einlass-Entität, die im Ruhezustand `on/open/opening/closing` meldet,
  verweigert jeden Zyklus), zwei Ursachen des 30-s-Blindfensters (Fremd-Öffnung = Trade #181; eigener
  Close, der im Hintergrund scheitert).
- **Mit Freigabe erledigt:** Archiv-Push `09f3d19c..122fd55a`; Kommentar an Eifel-Joe#71
  (`5902127893`, Folge der veralteten Kopie: Ablehnung überschreibt Halt-Meldung); **neues Issue
  Eifel-Joe#72** (Neustart-Abgleich: ein werfendes Schließen stoppt die übrigen Verteiler und das
  Entry-Setup; `typ:fehler`, `schwere:mittel`, `groesse:S`). Gepostet = Entwurf (per JSON verglichen).
  Eifel-Joe#42 kennt #72 noch nicht → mit Task 11 nachziehen.

### Verworfen

- 3b-Guard nur im Ablehnungspfad → ersetzt durch den Wurzel-Guard (A12, „ein Schutz statt zwei").
- Review-Vorschläge mit Begründung abgelehnt: Grace auch ohne `stop_service` (R6), `isinstance`-Guard
  (unerreichbar), „never claim"-Wortlaut (Restfenster steht in der Spec) — Tabellen in A10/A11/A13.

### Fallen

- **`git worktree add -b X upstream/master` setzt `upstream/master` als Tracking** → ein nacktes
  `git push` zielte auf JustChr. Sofort `git branch --unset-upstream`.
- **Bash-Tool: `\\n` in Heredoc-Python kam als echter Zeilenumbruch an** (auch `\\E` → Warnungen) →
  Blöcke mit Backslashes per Write-Tool in eine Datei, dann per Python einspleißen.
- **MUT 5 deadlockt** `test_second_concurrent_cycle_rejected_by_single_flight_lock` → Runner mit Timeout
  + `taskkill /T /F` (venv-`python.exe` ist Launcher, das Kind hält die Pipes); `pytest-timeout` unter
  Windows beendet den ganzen Lauf. Einzellauf `mut5_rerun.py` mit `--deselect`.
- Mutationsläufe nie parallel zur vollen Suite im selben Worktree; parallele pytest-Läufe können
  `WinError 10055` (socketpair) werfen — Flake, allein grün.
- `difflib.SequenceMatcher` auf den 500-KB-Einzeiler-Bundles hängt → Präfix/Suffix-Vergleich.
- Sonnet-Implementer schreiben den Trailer `Claude Sonnet 5.5` (ihre Attributionsregel) — akzeptiert,
  upstream squasht.
- Subagenten auf dem Worktree nie parallel laufen lassen, solange ein Reviewer darin Tests fährt.

### Nächste Schritte

1. (erledigt) Freigaben Archiv-Push, Kommentar #71, Issue #72.
2. **Neue Sitzung: Task 10 Live-Test auf HA-Test** (Plan Task 10, L1–L5; Wegwerf-Build
   `prerelease/v2026.09.30b1` aus `2c221a7a` — Push + Release nur mit Freigabe).
3. Danach **Task 11:** PR-Body (s. o.) zur Freigabe, Greps (A6) auch über den Body, PR, Issues
   (Eifel-Joe#66 `upstream:gemeldet`, #69 L3-Messung, #42 inkl. neuem #72); Archiv (Plan-Haken
   Task 10/11, Live-Protokoll, `mutations.json`, Runner) nach Regel P1.
4. Nebenher weiter offen: Prod-Rebuild mit JustChr#182 + Aufräumen `issue5-work`; Eifel-Joe#22.

### Empfohlene Skills

- `task-loop`; für Task 10 Memories `hasi-livetest-capability-boundary`, `verify-ha-system`,
  `hasi-sonoff-emulator-testsystem`, `ha-no-auto-restart`; für Task 11 `pr-workflow` + Memory
  `hasi-pr-build-recipe`.

## 2026-09-29 (7) — JustChr antwortet auf alle drei; 🟠-Block nachgeprüft; Eifel-Joe#66 Spec-Nachtrag + Plan freigegeben

### Stand

- **JustChr (16:56–16:58 UTC, Konto `JustChr`):**
  - `JustChr#182` gemergt als `0b9a71bd`, byte-gleich mit `34471593` → Eifel-Joe#5 geschlossen
    (Kommentar `5895128919`). Auf Prod erst mit dem nächsten Rebuild.
  - `JustChr#181` (`5894821774`): Claim als Ort angenommen, Zusatz Nachfrist nach eigenem
    Schließbefehl → wörtlich in Eifel-Joe#66 (`5895129943`).
  - `JustChr#160` (`5894821423`): Minor-Bump 14.1 → 14.2 freigegeben, Wunsch: Test über den
    zweiargumentigen Migrationspfad; Sperre ab HA **2026.3** (an den Tags gelesen, Memory
    `ha-store-major-version-guard` korrigiert) → wörtlich in Eifel-Joe#22 (`5895130590`).
- **Nachprüfung 🟠-Block** gegen `1876aa03` (`0b9a71bd` berührt die Pfade nicht), Belege in den
  Issue-Kommentaren: Eifel-Joe#8, Eifel-Joe#9, Eifel-Joe#10, Eifel-Joe#11 bestehen; Eifel-Joe#44
  besteht nur rotierend → `prod-scharf` entfernt, nach 🟡; Eifel-Joe#47 durch `JustChr#173`
  erledigt → geschlossen, Reste auf Eifel-Joe#34/Eifel-Joe#49. Eifel-Joe#57 `schwere:mittel`,
  Eifel-Joe#58 `schwere:niedrig` eingeordnet; Blockade-Vermerk Eifel-Joe#55 gestrichen.
  Eifel-Joe#42-Body + Stand-Kommentar `5895265983`. Alle Texte vorher freigegeben, gepostet =
  Entwurf (per JSON verglichen).
- **Eifel-Joe#66:** Spec-Nachtrag (R6: 30 s Nachfrist nur nach gesendetem Schließbefehl, Test 10,
  Live L5) und Plan `docs/superpowers/plans/2026-09-29-distributor-inlet-open-gate.md`
  freigegeben; beide auf `archive/design-history` `0d07e344` (gepusht). Plan **nicht
  probegelaufen**.
- Kein Code. Lese-Worktree `recheck-work\read-wt` entfernt; `D:\Entwicklung\HASI\recheck-work\`
  bleibt als Beleg (gepostete Texte, Index-Diff `texts\index42\diff.txt`, JustChr-Kopien,
  `storage.py` an den HA-Tags 2026.2.0/2026.3.0/2026.4.0).

### Verworfen

- Warten im Sweep statt Nachfrist, Stempel nur beim letzten Schließen — Begründung in der Spec
  (Optionstabelle „The grace after our own close").
- Uhr `dt_util.utcnow()`/`freezer` → `self.hass.loop.time()` (Modul-Konvention
  `distributor.py:951/978`, im Mock-Host steuerbar); Konstante `DIST_…` →
  `DISTRIBUTOR_INLET_CLOSE_GRACE_SECONDS`.

### Fallen

- `grep -c $'\r'` innerhalb `$(...)` bekommt unter Git Bash ein leeres Muster und zählt jede
  Zeile → CR per Python `bytes.count(b"\r")` prüfen.
- `gh api … --jq .body` hängt ein Zeilenende an → gepostet/lokal per JSON vergleichen, nicht per
  Datei-diff.
- Python-Ausgabe mit Emoji → `PYTHONIOENCODING=utf-8`, sonst `UnicodeEncodeError` (cp1252).
- Funktionsauszug per awk: `async def` in die Abbruchbedingung, sonst läuft er in die nächste
  Methode (Scheinabweichung beim Vergleich zu Eifel-Joe#8).
- Die Einstiegs-Tests (Dispatcher, Irrigate now, Member-Lauf, run_now) mocken alle den Claim;
  nur der Testlauf erreicht ihn echt → Pins in Task 5 des Plans.
- Der Auto-Mode-Klassifikator fiel am Sitzungsende zeitweise aus („no verdict") → betroffene
  Bash-Aufrufe später wiederholen.

### Nächste Schritte

1. **Eifel-Joe#66:** neue Sitzung → Plan zuerst im Wegwerf-Worktree **probelaufen**
   (User-Vorgabe), Messwerte in den Plan (Abschnitt „This plan has not been run yet" ersetzen,
   wie beim Plan zu Eifel-Joe#5), dann Umsetzung nach Plan.
2. **Prod-Rebuild** mit `JustChr#182` (Eifel-Joe#5 ist bis dahin auf Prod scharf) + Aufräumen
   `issue5-work` (2 Worktrees, Branch lokal + origin, `prerelease/v2026.09.29b1` samt Release) —
   eigene Sitzung, Memory `hasi-production-on-upstream`.
3. **Eifel-Joe#22:** Rev-4-Nachtrag (Minor 14.1 → 14.2, zweiargumentiger Test) + Plan — eigene
   Sitzung. Rev-3-Plan NICHT ausführen.
4. Danach nach Eifel-Joe#42: 🟠 Eifel-Joe#8 (zuerst Spec), Eifel-Joe#9, Eifel-Joe#10,
   Eifel-Joe#11.

### Empfohlene Skills

- `task-loop`; für Eifel-Joe#66 `superpowers:subagent-driven-development` bzw.
  `superpowers:executing-plans`, `superpowers:test-driven-development`,
  `superpowers:using-git-worktrees`, `code-doku`; am Ende `pr-workflow` + Memory
  `hasi-pr-build-recipe`.

## 2026-09-29 (6) — Eifel-Joe#66: Spec fertig, Vorschlag auf JustChr#181, Folge-Issues #68–#71

### Stand

- **Spec Eifel-Joe#66** geschrieben und vom User freigegeben (abschnittsweise und als Ganzes):
  `docs/superpowers/specs/2026-09-29-distributor-inlet-open-gate-design.md` (Hauptbaum, untracked) =
  `archive/design-history` `03425147` (gepusht mit Freigabe), dazu Messprotokoll
  (`reconstructed/2026-09-29-distributor-inlet-open-count-repro.md`) und Belege
  (`probes/2026-09-29-inlet-open-repro/`, vorher auf Schlüssel/IPs/URLs/Koordinaten gegrept).
  Entscheidungen stehen in der Spec, nicht hier. Der **Ort (Claim) ist nur Vorschlag an JustChr**.
- **JustChr#181:** Vorschlag `5893690481` (15:49 UTC) gepostet, inhaltsgleich (`diff -B`). User-Vorgabe:
  JustChr Zeit geben — **der Plan entsteht erst nach seiner Antwort**.
- **Fork (alle Texte vorher freigegeben, gepostet = Entwurf):** neu Eifel-Joe#68 (Aufschieben, `typ:feature`,
  `schwere:niedrig`), #69 (verpasste Flanken), #70 (Klassik-Sweep über nicht verfügbaren Einlass), #71
  (veraltete Verteiler-Kopien bei ≥ 2 Verteilern) — #69–#71 `typ:fehler`, `schwere:mittel`, nur gelesen.
  #66-Stand `5893846555`, Labels unverändert. #42-Body ersetzt (8b, 25b–25d, 43b), vorher geprüft, dass
  er seit 13:54 UTC unverändert war.
- 15:59 UTC: #160 und #181 ohne Antwort, #182 offen (CI 5/5 grün, kein Review), `upstream/master` =
  `1876aa03`. Lese-Worktree `issue66-work/read-wt` entfernt. Kein Code.

### Verworfen

- JustChrs Schweigen nach 2 h als Zustimmung zum Ort zu lesen — er antwortet am Folgemorgen (~05–06 UTC),
  und wir hatten ihm einen Vorschlag angekündigt (User-Korrektur). Memory [[upstream-silence-is-not-consent]].
- Die übrigen Alternativen (Ort `_dist_eligible_for_run`, Aufschieben, Übernehmen, Fluss-Sensor als Signal,
  `count` an der Aus-Flanke) mit Begründung in der Spec.

### Fallen

- **Python `write_text` schreibt unter Windows CRLF**, `gh … --jq .body` liefert LF → Issue-Bodies mit
  `write_bytes(text.encode("utf-8"))` bauen, sonst meldet der Diff jede Zeile. Skript:
  `issue66-work\index42\edit42.py` (Ersetzungen mit Trefferzahl-Prüfung).
- Für den Plan: `_record_skipped_run(None, …)` heißt „alle Zonen der Installation“, und der Dispatcher gibt
  dem Claim das ganze Plan-Ziel inkl. direkter Zonen (`allowed = target`, `distributor.py:482`) →
  Schnittmenge mit den Mitgliedern (Spec, Test 6).
- HA-Kern am Release-Tag lesen: 2026.9.4 überspringt nicht verfügbare Entitäten weiter, loggt aber eine
  Warnung (2024.12.5: still). Belege `issue66-work\ha-2026.9.4-{service,target}.py`.

### Nächste Schritte

1. **Eifel-Joe#66:** JustChrs Antwort auf `5893690481` abwarten (frühestens 30.09. morgens). Zustimmung →
   `superpowers:writing-plans` nach der Spec. Besteht er auf `_dist_eligible_for_run` → Spec-Abschnitt
   „Where the gate sits“ plus R1/R4 und Tests 7/8 anpassen (so in der Status-Zeile der Spec). Einwände
   wörtlich in #66 (P2).
2. Eifel-Joe#22: weiter auf JustChrs Antwort zur Minor-Version (#160, `5890113813`) warten, dann
   Rev-4-Nachtrag + Plan. Rev-3-Plan NICHT ausführen.
3. JustChr#182: Review abwarten; Einwände wörtlich in Eifel-Joe#5; nach Merge Aufräumen + Prod-Rebuild.
4. Nach Schwere weiter: #67 reproduzieren; #69 misst sich im #66-Live-Test L3 mit.

### Empfohlene Skills

- `superpowers:writing-plans` für #66 (nach JustChrs Antwort); später `pr-workflow` + Memory
  `hasi-pr-build-recipe`

## 2026-09-29 (5) — P2-Nachlauf: #62/#63/#46 geschlossen, #67 neu, Index #42 nachgezogen

### Stand

- **Geschlossen** (`completed`, EN/DE-Kommentar, alle Texte vorher freigegeben, gepostet = Entwurf):
  Eifel-Joe#62 (`JustChr#176` = `213f8d91`, v2026.09.26; JustChrs Rest — veralteter Kommentar über
  `_plan` — hat er in `41452f67` selbst bereinigt), Eifel-Joe#63 (`JustChr#178` = `d006c99e`; der rote
  `test-ha-floor` war ein uhrabhängiger Solar-Test, von JustChr in `1bfa9643` festgelegt),
  Eifel-Joe#46 (Produktfrage „zu Ende laufen lassen“ aus `JustChr#176` vom User angenommen).
- **Neu: Eifel-Joe#67** — Rest aus #46: ein zweiter rotierender Dispatch ersetzt eine laufende
  Rotation (`run_chain.py:757` an `1876aa03`). `typ:fehler`, `typ:produktentscheidung`,
  `schwere:mittel`, `groesse:M`, kein Upstream-Label. Nur gelesen; bestätigt eine Reproduktion die
  Folgen, auf `hoch` wie #62.
- **#42** in zwei Body-Ersetzungen (13:39 und 13:54 UTC), beide inhaltsgleich nachgelesen: 2a/8/8a/13a/
  43a geschlossen, 8b (#66) im 🔴-Abschnitt neu, 24 (#22) auf Wahl B + offene Minor-Frage, DE-Zeile 6
  (#5) nachgezogen, 25 (#46) geschlossen + 25a (#67) neu, „Watched“: `JustChr#148` zu (Fix war unser
  `JustChr#144`), `#149` offen.
- Scan aller offenen Fork-Issues mit Upstream-Label: nichts weiter veraltet. Skript jetzt fest unter
  `D:\Entwicklung\HASI\issues-work\scan_upstream_refs.py` (Memory `hasi-todo-file`).
- Der Chip „Catch up the HASI issue index…“ lief in dieser Sitzung; er war schon „gestartet“ und ließ
  sich nicht zurückziehen. Keine Doppelspuren auf GitHub (je ein Kommentar, kein Issue nach #67).
  Arbeitsdateien: `D:\Entwicklung\HASI\issues-work\2026-09-29-catchup\`.

### Fallen

- `gh api … --jq '.body'` hängt eine Leerzeile an → Vergleiche Entwurf/gepostet mit `diff -B`.
- Pipe-Exit-Codes: `git grep … | cut` meldet den Code von `cut` — für Ja/Nein-Prüfungen `git grep -q`.

### Nächste Schritte

- Unverändert aus (4): **Eifel-Joe#66 (hoch) zuerst** — Spec; #22 wartet auf JustChr; danach #67
  (mittel) reproduzieren und entscheiden lassen.

## 2026-09-29 (4) — Upstream-Antworten gepostet; Eifel-Joe#66 im Modus `count` reproduziert

### Stand

- **Gepostet (User-Freigabe):** Korrektur + Minor-Vorschlag auf JustChr#160
  (`5890113813`), Übernahme auf JustChr#181 (`5890114252`); beide inhaltsgleich mit den Entwürfen.
- **P2 gepostet (User-Freigabe), inhaltsgleich geprüft:** Eifel-Joe#22 `5890521160` (Label bleibt
  `upstream:freigegeben`); Eifel-Joe#66 `5890521597` + Labels `upstream:gemeldet` →
  `upstream:freigegeben` und **`schwere:mittel` → `schwere:hoch`** (User, wegen des gemessenen
  stillen Positionsversatzes); Nachmeldung mit Messwerten auf JustChr#181 `5890522697`.
  Den `ignore`-Fall lässt der User bei der Lesung.
- **Index-/Schließ-Nachlauf ausgelagert** (Chip „Catch up the HASI issue index…“, #66 jetzt in 🔴):
  Eifel-Joe#62/#63 offen trotz Merge von JustChr#176/#178 am 28.09.; #42 in sieben Zeilen veraltet,
  #66 fehlt; #46 klären.
- **Reproduktion #66, `count`, HA-Test** (`v2026.09.29b1`, auf diesem Pfad = `1876aa03`, per Diff
  belegt): Protokoll `D:\Entwicklung\HASI\issue66-work\ergebnis-repro-count-2026-09-29.md`.
  H1–H5 alle bestätigt: Vorrücken an der fremden Ein-Flanke (4 → 5); Claim 40 s nach dem Öffnen,
  keine Flanke beim Öffnen des offenen Einlasses (Recorder: ein EIN, ein AUS); Gutschrift an
  Test5 (61 s, 10,17 L), Test4 (Wasser 106 s) bekam nichts; danach gespeichert 6 gegen Modell 5,
  weiter `synced`. Auslöser `irrigation_plus/irrigate_now` mit `zone_id 6` (gleiche Methode und
  Gates wie „Alle Zonen“, ohne Grace Test).
- **HA-Test zurückgestellt:** Position 3, Logger `warning`, Ventil/Master/Sonde aus. Test5 behält
  +10,17 L (Eimer 0,0).

### Fallen

- **Test4 hat ein Bodenfeuchte-Veto** (`sensor.basilikum_soil_moisture`, 30) → als Sweep-Ziel
  unbrauchbar, der Zyklus bricht vor dem Öffnen ab. Ziel Test5.
- **Laufprotokoll ist neueste-zuerst** — nach `ts` sortieren, nicht `[-n:]`.
- **`ha_eval_template` liefert JSON-förmige Ausgabe schon als Objekt**; `ha_get_history` liegt unter
  `data.entities[]`. Helfer: `issue66-work\hasi_read.py`, `evaluate_run.py`, `repro_count.py`.
- **Kein `irrigate_now`-Dienst** — nur Websocket `irrigation_plus/irrigate_now` (über
  `pr146-work\live\mcp_test.py`); `watch_mode` nur übers Panel (HTTP-View).
- **Integrations-Eintrag auf HA-Test gibt in `options` den Wetter-API-Schlüssel mit aus** — nie
  wiedergeben; Skripte drucken nur ausgewählte Felder.

### Nächste Schritte

1. **Eifel-Joe#66 (jetzt `schwere:hoch`) zuerst:** Spec nach `superpowers:brainstorming` — Gate-Ort
   (Claim `:1195-1212` deckt alle Einstiege vs. `_dist_eligible_for_run`, das auch die
   Gesamtdauer-Schätzung speist), Signal (Live-Zustand des Einlasses; `inlet_entity` optional),
   `count`-Vorrücken bei fremder Ein-Flanke, `ignore` (nur gelesen), Fall ohne Flanke. Messprotokoll
   mit auf `archive/design-history`.
2. Eifel-Joe#22: JustChrs Antwort zur Minor-Version auf #160 abwarten, dann Rev-4-Nachtrag + Plan.
3. JustChr#181: auf JustChrs Reaktion zur Messung achten (Einwände wörtlich in Eifel-Joe#66, P2).
4. JustChr#182 wie gehabt; Index-Chip bei Gelegenheit.

### Empfohlene Skills

- `superpowers:brainstorming` für die #66-Spec; `superpowers:writing-plans` für #22

## 2026-09-29 (3) — JustChr#160: JustChr wählt selbst B, Bot-Antwort zurückgezogen; Rollback-Befund HA ≥ 2026.4; #181 gegengelesen

### Stand

- **JustChr#160:** `watchtower-justchr[bot]` (05:09 UTC, `5884061101`) antwortete, als sei A gewählt.
  JustChr zog das um 06:08 UTC **selbst** zurück (`5884685278`, Konto `JustChr`, OWNER, nicht editiert;
  „ohne seine Prüfung rausgegangen“) und wählte **B** — seine Liste deckt sich mit Rev 4 Variante B.
  Neu von ihm: die Kosten „HAs eigene Zone wechselt → bis zu einer Woche Puffer falsch“ gehören **in
  den Migrationskommentar** und in die Release-Notes (Rev 4 nennt sie nur in Tabelle R4-3).
- Seine Prüfstellen an `1876aa03` nachgelesen: `weather_aggregate.py:167`, `:319`, `helpers.py:1015`,
  `__init__.py:1429` ✓; `STORAGE_VERSION = 14` (`store.py:198`); upstream-stabil `v2026.09.17`
  (`6d9c69e6`) ohne `coerce_stamp` ✓; `dt_util.as_local` hängt einem naiven Wert nur HAs Zone an ✓.
- **Bot:** Konto angelegt 28.09. 14:39 UTC, App-Profil 404, einziger Kommentar unter 289 seit Juni,
  keine Reviews auf #175–#182. Memory [[justchr-watchtower-bot-unreviewed]].
- **Befund, widerlegt Rev 4 B.5/R4-5:** HA ≥ 2026.4 (home-assistant/core#164340) wirft
  `UnsupportedStorageVersionError` bei höherem **Major**-Stand; HASI lädt ungeschützt
  (`__init__.py:191` → `store.py:907`) → Rollback nach 14 → 15 = Setup scheitert. Der Minor-Stand wird
  nicht geprüft → **14.1 → 14.2** hält den gutmütigen Rollback. Einzige `Store`-Instanz auf
  `STORAGE_KEY`: `store.py:903`. Memory [[ha-store-major-version-guard]].
- **Entwurf an JustChr** (Korrektur + Minor-Vorschlag):
  `D:\Entwicklung\HASI\issue22-work\bot-review\draft-160-minor-version.md` — **nicht gepostet, wartet
  auf User-Freigabe.** Grep sauber (kein `Eifel`, einzige SHA `1876aa03`). Belege im selben Ordner.
- **JustChr#181** (05:37 UTC, `5884353117`): Fix = Verteiler-Gate, nicht Zonen-Prädikat; „nur count“;
  bietet uns das Issue an. Gegengelesen (Agent + eigene Stichproben an `1876aa03`): Kette stimmt;
  „nur count“ zu eng — `ignore` ist Default (`store.py:517`), ohne Listener → Sweep wässert obendrauf;
  kantenlose Öffnung (HA-Start `old_state` None, `unavailable` → on, `distributor.py:1013-1015`) in
  allen Modi unsichtbar; in `count` rückt die Position an der Ein-Flanke vor (`:954`), der Sweep
  startet dort (`:1417-1418`) → gelesen, nicht gemessen: erste Gutschrift an die Nachbarzone, danach
  Position +1 bei `synced`. Gate-Ort: `_dist_eligible_for_run` speist auch `skip_conditions.py:593`;
  `handle_distributor_run_now` (`:1896`) und der Testlauf (`:1788`) umgehen es; der Claim
  (`:1195-1212`) deckt alle Einstiege.
- **JustChr#182:** offen, CI 5/5 grün, kein Review, keine Inline-/Issue-Kommentare. `upstream/master`
  = `1876aa03`.
- Kein Code, nichts gepostet, keine Labels geändert.

### Verworfen

- Die Bot-Antwort als Wahl A werten — von JustChr selbst zurückgezogen.
- Eine A/B-Rückfrage — ist beantwortet.

### Fallen

- **Parallele Bash-Aufrufe teilen sich das Arbeitsverzeichnis:** ein `cd` im einen versetzt den
  anderen (`./.venv/…: No such file`, `sed: can't read`). Absolute Pfade nehmen.
- `gh api /apps/…` mit führendem `/` → MSYS macht `C:/Program Files/Git/apps/…` daraus; ohne `/`.
- Rev 4 prüfte HA-Verhalten nur an der lokalen HA 2024.12.5 — HA-Core-Aussagen am Release-Tag lesen.

### Nächste Schritte

1. User entscheidet: Entwurf an JustChr#160 posten? JustChr#181 übernehmen?
2. Im selben Zug (P2, Texte vorher im Chat freigeben): Stands-Kommentar Eifel-Joe#22 (Label bleibt
   `upstream:freigegeben`); Kommentar Eifel-Joe#66 mit JustChrs Einwand; bei Zusage auf #181 das Label
   `upstream:gemeldet` → `upstream:freigegeben`.
3. Eifel-Joe#22: Spec-Nachtrag zu Rev 4 auf `archive/design-history` (Entscheidung B; Delta 1
   HA-Zonen-Kosten im Migrationskommentar; Delta 2 Minor statt Major je nach JustChrs Antwort; B.5/R4-5
   berichtigen), dann `superpowers:writing-plans`. ⛔ Rev-3-Plan weiter NICHT ausführen.
4. Eifel-Joe#66: Reproduktion auf HA-Test (Sonoff-Emulator), Modus `count`, fremdes Öffnen, dann
   „Alle Zonen jetzt bewässern“ → Gutschrift und Ringposition messen; den `ignore`-Fall mitnehmen.
5. JustChr#182 wie gehabt; nach Merge Aufräumen + Prod-Rebuild. Offen: Live-Test Eifel-Joe#64.

### Empfohlene Skills

- `superpowers:writing-plans` für #22; `superpowers:systematic-debugging` für die #66-Reproduktion
- `pr-workflow` + Memory `hasi-pr-build-recipe`, sobald es upstream geht

## 2026-09-29 (2) — Eifel-Joe#5 gebaut, live belegt, als JustChr#182 eingereicht

### Stand

- **`JustChr#182` offen** (Branch `fix/zone-save-sends-what-changed`, 14 Commits auf `1876aa03`,
  gepusht; an die Sitzung gebunden). CI: bei Einreichung noch keine Checks (Fork-PR).
  Eifel-Joe#5: Kommentar + Label `upstream:gemeldet`; Eifel-Joe#42 Zeile 6 nachgezogen.
- **Umfang gewachsen (User-Entscheid):** derselbe gemeinsame Speicher-Timer auf Sensorgruppen,
  Verteiler, Modulen ist im selben PR (erst „eigenes Issue", dann „gehört zusammen").
- **Belege** (alles auf `archive/design-history` `a3d350aa`, gepusht: Plan-Nachtrag Teil 1–4,
  `reconstructed/2026-09-29-zone-save-live-on-ha-test.md`, `probes/…-mutations-branch.*`):
  Suite `TZ=UTC` 7 / 3466 / 9 / 367, Namensdiff leer; vitest 27/659; tsc/lint/Build sauber,
  `dist` frisch; Mutationen **45/45**; live RED auf `v2026.09.27b3`, GREEN auf `v2026.09.29b1`.
- 12 Review-Befunde eingearbeitet (Liste im Plan-Nachtrag), u. a. der Eimer-Reset-Dialog per ID
  (sonst Schreiben in die falsche Zone), Löschen/Verlassen verwerfen ungesendete Änderungen.
- **HA-Test läuft `v2026.09.29b1`** (Wegwerf-Prerelease, Branch `prerelease/v2026.09.29b1`).
  „Grace Test" wiederhergestellt bis auf Verbrauch (8 → 24 L) und `days_since_irrigation`.
- **JustChr#160:** `watchtower-justchr[bot]` hat am 29.09. 05:09 UTC geantwortet (beschreibt
  Weg A, keine ausdrückliche Wahl). User: erst #5 beenden, **dann die Bot-Antwort genau ansehen**.

### Verworfen

- **`Test2` als Live-Zone:** Verteiler-Mitglied, jeder Zyklus schickt `_update_frontend` → die
  Seite ist danach frisch, der RED beweist nichts. „Grace Test" (Emulator, kein Verteiler).
- **Eigenes Issue für die Spiegel-Timer:** vom User zurückgenommen.

### Fallen

- **Verborgener Browser-Bereich friert die Seite ein; HA baut das Panel beim Aufwachen neu** —
  mit frisch geladenen Zonen. Zwei Live-Läufe ungültig. Bereich sichtbar halten, Marker aufs
  View-Element, `_fetchData` zählen. Memory [[live-test-hidden-browser-pane]].
- **Browser-Werkzeuge ~0,8 s pro Schritt** — ein 500-ms-Fenster trifft man nur mit
  `input`-Events auf den Feldern der Seite (im Protokoll offengelegt).
- **`grep -rn "Eifel-Joe" custom_components/ tests/` ist auf der Basis NICHT leer** (14
  Upstream-Nennungen als Melder). Maßgeblich: hinzugefügte Zeilen + `Eifel-Joe#`.
- **Modul-API lehnt `config: null` ab**; `calcmodules/static` behandelt `{}` gleich.
- Bash-Heredoc mit langem Markdown scheiterte einmal am Parser → Write-Tool + `cat >>`.

### Nächste Schritte

1. **JustChr#160 / Bot-Antwort genau prüfen** (vereinbart), dann über Eifel-Joe#22 entscheiden.
2. JustChr#182 begleiten: Einwände wörtlich als Kommentar in Eifel-Joe#5 (P2); CI lesen.
3. Nach Merge: Eifel-Joe#5 schließen; Release/Tag/Branch `v2026.09.29b1` löschen; Worktrees
   `issue5-work\wt` und `issue5-work\pre-wt` entfernen; Prod-Rebuild.
4. Offen wie zuvor: Reproduktion zu Eifel-Joe#66; Live-Test zu Eifel-Joe#64.

### Empfohlene Skills

- `superpowers:receiving-code-review` (JustChrs Review zu #182), `pr-workflow`
- `task-loop` für #22, falls JustChr/Bot eine Richtung vorgibt

## 2026-09-29 — Eifel-Joe#5: Spec + Plan fertig und einmal komplett geprobt; #22 wartet weiter

### Stand

- **Tor Eifel-Joe#22 geschlossen, nichts gebaut.** Auf JustChr#160 ist unser `5879455421` weiter der
  letzte Kommentar, ohne Reaktion; Timeline seit 28.09. ohne Neues; keine neuen PRs aller Autoren
  (JustChr#148 zu, unabhängig: Fix war #144). `upstream/master` = **`1876aa03`** (neu gefetcht).
  Kein Kommentar in Eifel-Joe#22 — kein neuer Stand.
- **Stattdessen Eifel-Joe#5** (User: „die Liste soll auch mal kleiner werden"). Auf
  `archive/design-history` **`e511dd1a`**, gepusht:
  `specs/2026-09-29-zone-save-sends-what-changed-design.md`,
  `plans/2026-09-29-zone-save-sends-what-changed.md`, Belege `probes/2026-09-29-zone-save-*`.
- **Vom User entschieden:** Weg **B** (Panel sendet nur Geändertes, Denylist +6 Felder), geleerte
  Felder als `null`, D1 (Aufrufstellen nennen ihre Änderung), D2 (Paar-Ergänzung im View, nicht
  im Store). **Plan freigegeben.**
- **Plan einmal komplett geprobt** (Wegwerf-Worktree auf `1876aa03`, danach entfernt): Namensdiff
  leer 375 = 375, Suite 7 / 3462 / 9 / 367 (mit 7 neuen), vitest 629 → 637, tsc 0, Build ohne
  TS-Diagnose, nur `dist/irrigation-plus.js` ändert sich, Mutationen 15/15.
- **Kein Feature-Branch, kein Worktree** — Task 0 legt `issue5-work\wt` an. Die Helfer, die der
  Plan aufruft, liegen in `D:\Entwicklung\HASI\issue5-work\`: `mutate.py`,
  `drop-zone-spread.cjs`, `probe_import_origin.py`; Messungen in `measure\`.
- HA-Test läuft `v2026.09.27b3` (`6a313d7c`) und enthält JustChr#180 **nicht** (gemessen).
- Offen, unverändert: Reproduktion zu `Eifel-Joe#66`; Live-Test zu `Eifel-Joe#64` (bräuchte einen
  neuen Wegwerf-Build).

### Verworfen

- **Die Allowlist aus dem Issue-Body als Fix.** Das Formular hat ein eigenes Eimerfeld
  (`view-zone-settings.ts:1608-1627`), der Eimer stünde also auf jeder Allowlist editierter
  Felder. Sie behebt das gemeldete Symptom nicht.
- **altmenorgs Differenz-Helfer** (`11ed18d2`): eine Differenz gegen die veraltete Seitenkopie
  verschluckt gewollte Schreibungen (die Zustandsauswahl setzt `duration: 0`).
- **Die Paar-Ergänzung im Store** (altmenorgs Form): änderte jeden Trichter-Schreiber,
  `set_all_buckets` würde plötzlich geklemmt.
- **Die Quelltext-Pin in vitest:** CI fährt kein vitest; `node:`-Importe im TS-Test hätten den
  Build 12 TS2591-Warnungen ausgeben lassen.

### Fallen

- **Die Zonen-Seite erfährt von einer Gutschrift nie:** sie hört auf `_update_frontend`
  (`websockets.py:83-105`), der Lauf sendet nur `_config_updated` (`irrigation.py:2903`). Gilt
  für jede Frage „warum zeigt die Seite den alten Stand".
- **Ein Tripwire mit festem Zeichenfenster** (`[^)]{0,40}`) fand nur 23 der 35 Stellen — die
  Einrückung allein ist länger. Pins vor dem Einsatz gegen eine bekannte Zahl kalibrieren.
- **`store.get_zone(None)` wirft** (`int(None)`): jeder View-Code, der die gespeicherte Zone
  nachliest, braucht den Anlege-Fall (Assistent und „Zone hinzufügen" posten ohne `id`).
- **Lingering timer bei neuen Coordinator-Fixtures:** der Konstruktor armiert den
  Mitternachts-Tracker; `c._track_midnight_time_unsub()` im Teardown hält die Datei fehlerfrei.
- **`M` auf unberührten Card-Bundles nach `npm run build`** ist `autocrlf`; `git diff --quiet`
  entscheidet.
- **Die Memory-Warnung „im Worktree testet pytest fremden Code"** gilt für
  `D:\Entwicklung\HASI\*-work\wt` nicht — gemessen mit `probe_import_origin.py`.

### Nächste Schritte

1. `/clear`, dann den Plan ausführen, Task 0 zuerst (ist `upstream/master` noch `1876aa03`?
   Sonst Baseline neu messen und die vier Anker neu lesen, bevor eine Zeilennummer gilt).
2. Eifel-Joe#22 nur weiter, wenn JustChr auf #160 antwortet — das Tor gilt unverändert.
3. Nach dem PR: Kommentar + Label `upstream:gemeldet` in Eifel-Joe#5, Eifel-Joe#42 nachziehen
   (Plan Task 9, Texte vorher im Chat freigeben).

### Empfohlene Skills

- `superpowers:subagent-driven-development` + `superpowers:test-driven-development`
- `code-doku` — die Kommentare stehen wörtlich im Plan
- `superpowers:requesting-code-review` / `superpowers:receiving-code-review` (Task 7)
- `pr-workflow` + Memory `hasi-pr-build-recipe` (Task 9)
- `superpowers:verification-before-completion` vor jedem „fertig"

## 2026-09-28 (10) — Eifel-Joe#22: Rev-3-Plan verworfen, Revision 4 geschrieben, JustChr soll A oder B wählen

### Stand

- ⛔ **Den Plan `plans/2026-09-28-weather-buffer-aware-writers.md` NICHT ausführen.** Vor der
  ersten Codezeile gegen `1876aa03` geprobt: Task 1 macht das heute korrekte Tagesfenster
  1,0 → 3,0 h und das Live-Fenster 3,0 → 5,0 h; die Schreiber-Tasks 4–6 werfen `TypeError`
  (Prune, Merge im Sensor-Ereignispfad, `_hour_multiplier`); sein eigener Pin 2
  (`min(hours) >= 12.0`) bleibt dabei grün. Plan und Rev-3-Spec tragen im Archiv einen Banner.
- **Revision 4** auf `archive/design-history` **`2cac20e6`**, gepusht:
  `docs/superpowers/specs/2026-09-28-weather-buffer-one-frame-design.md`. Belege daneben unter
  `docs/superpowers/probes/2026-09-28-weather-buffer-*` (Proben P1–P6, Ergebnisse,
  Stempel-Inventar mit 191 gegengeprüften `file:line`). Die archivierten Proben reproduzieren
  die Ergebnisse zeilengleich. Kopien ungetrackt auch im Worktree.
- **Offene Entscheidung, bei JustChr:** Speicherform **A** (aware, exakte Lesegrenze) oder
  **B** (naiv HA-lokal + Migration 14 → 15, **von uns empfohlen**). Gefragt auf JustChr#160,
  Kommentar `5879455421`. Stand auf `Eifel-Joe#22`, Kommentar `5879470922`; Labels unverändert.
- **Vom User freigegeben, gilt für A und B:** `local_naive_now()` an 19 Stellen (13 schreibend,
  3 reine Vergleichs-`now`s inkl. Solar-Klemme `__init__.py:1429`, 3 Defaults in
  `weather_aggregate`); `_process_timezone()` → `dateutil.tz.tzlocal()`; E2E-Matrix Tages-/Live-
  Pfad × alter/frischer Store, exakt 1,0 h / `[12.5]` / 2,0, RED auf `1876aa03`.
- **Vom User freigegeben, nur B:** beide Provenienz-Namen bleiben (verhalten sich danach gleich,
  Docstring sagt warum); `_parse_stored_as_ha_local` wird korrekt, DEFECT-Pin umdrehen.
- **Baseline neu unter `TZ=UTC`:** 7 failed / 3455 passed / 9 skipped / 367 errors,
  Zusammensetzung identisch zur Berlin-Messung (0/0). Alle 367 sind `ERROR at teardown`
  „Lingering timer" (734 Zeilen = 2 je Error, gezählt). Datei:
  `D:\Entwicklung\HASI\issue22-work\measure\baseline-1876aa03-tzutc.txt`.
- Branch `fix/weather-buffer-aware-writers` steht weiter auf `1876aa03`, **kein Produktionscode
  geändert**, Worktree hat nur das ungetrackte `docs/superpowers/`.
- **Offen außerdem, unverändert:** Reproduktion zu `Eifel-Joe#66`; Live-Test zu `Eifel-Joe#64`
  auf HA-Test nie gefahren.

### Verworfen

- **Der Rev-3-Plan als Ganzes** — Belege oben und in der Spec.
- **R3-2s Rollback-Argument gegen den Versionssprung** — die Schreiber erzeugen binnen Minuten
  aware Stempel, `1876aa03` bricht darauf in der Tagesberechnung dauerhaft ab (P4). Unter B ist
  der Sprung selbst die rollback-gutmütige Form.
- **Meine eigene Vermutung „die `-q`-Datei zeigt keine Error-Gründe"** — falsch: nur die
  Summary-Zeilen haben keinen, die Traceback-Abschnitte schon. Vor dem Aufschreiben gezählt.

### Fallen

- **Eine Umrechnung, die von Identität zur Transformation wird, ist nicht mehr idempotent.**
  Dann muss jeder Wert genau einmal durch. In `weather_aggregate` rechnet nur `select_window`
  das Watermark um, und zwar lokal (`:167`); `:382/414/415/729/731` nehmen den Rohwert.
  Memory `non-idempotent-coercion-needs-inventory`.
- **Die `hass`-Fixture setzt HA auf US/Pacific**, der CI-Prozess läuft auf UTC, dieser Rechner
  auf Berlin → Zeitzonen-Deltas nur unter `TZ=UTC` messen (wirkt unter Windows, verifiziert).
  Memory `hasi-local-test-env-rebuild`.
- **`_process_timezone()` ist ein fester Offset von heute** (`helpers.py:1015`) → Altstempel
  über eine Sommerzeitgrenze hinweg 1 h daneben.
- **`async_load` wandelt nichts um** — Stempel sind nach einem Neustart `str`, nach dem nächsten
  Schreiben `datetime`. Der Kommentar `store.py:1980-1984` behauptet für Watermarks das
  Gegenteil.
- **`/tmp` für Zwischendateien** landet auf C: — Temp nach `D:\Entwicklung\…-work\`.

### Nächste Schritte

1. **JustChrs Antwort auf #160 abwarten.** Dann neu fetchen (ist `upstream/master` noch
   `1876aa03`?) und den Plan nach `superpowers:writing-plans` auf Revision 4 aufsetzen — bei B:
   Migration + 19 Stellen; bei A: Abschnitt „Variant A" der Spec + Leserliste aus dem Inventar.
2. Hat er Einwände: in seinen Worten als Kommentar in `Eifel-Joe#22` (Regel P2).
3. Unabhängig davon abrufbar: `Eifel-Joe#66`-Reproduktion (Dispatch-Zeitpunkt ohne aktiven
   Zyklus, JustChr#181), `Eifel-Joe#64`-Live-Test auf HA-Test.

### Empfohlene Skills

- `superpowers:writing-plans`, sobald JustChr entschieden hat — Grundlage ist Revision 4,
  nicht der Rev-3-Plan
- `superpowers:subagent-driven-development` + `superpowers:test-driven-development` für die
  Umsetzung; der Controller probt den Kern-Task vor dem ersten Dispatch
- `code-doku` für den Migrations-Kommentar (Annahme, verworfene Detektion, verworfene
  `DEFAULT_TIME_ZONE`-„Reparatur")
- `pr-workflow` + Memory `hasi-pr-build-recipe`, sobald es upstream geht

## 2026-09-28 (9) — Eifel-Joe#22: Spec + Plan fertig, Umsetzung noch nicht begonnen

### Stand

**Nebensache zuerst, weil abgeschlossen.** JustChrs Kommentar auf `JustChr#180` enthielt
eine Rückfrage an uns („*Water all zones* — same filter? If it does, tell me").
Beantwortet als **`JustChr#181`** (neues Issue, nicht Kommentar — `#180` ist zu):
`async_irrigate_now` engt bei `zone_id` nur die Liste ein (`irrigation.py:3361`),
`_drop_zones_already_running` läuft danach bedingungslos (`:3379`) — es ist nicht
derselbe *Filter*, es ist **dieselbe Aufrufstelle**. Einschränkung aus dem
Schwester-Pfad-Check: Member-Zonen sind bei `:3374` aus der Liste genommen und kommen
über `:3389` zum Wasser, in `distributor.py` — 0 Prädikat-Treffer. Für Member greift
der Filter also nicht.
`Eifel-Joe#66` dazu fortgeschrieben (Kommentar + Label `upstream:gemeldet`,
`beobachten` entfernt). **Sachliche Präzisierung dort:** der Verteiler-Pfad ist nicht
ungeschützt, sondern gegen das Falsche geschützt — `_dist_eligible_for_run` lehnt auf
`active_cycle` ab, fängt also einen *eigenen zweiten* Zyklus. Die im Body
vorgeschlagene Reproduktion „während des Zyklus" ist damit der teurere Weg; billiger
ist der Dispatch-Zeitpunkt ohne aktiven Zyklus.

**Hauptarbeit `Eifel-Joe#22` / `JustChr#160` — die zweite Hälfte, von ihm freigegeben.**
- Basis verifiziert: `upstream/master` = **`1876aa03`** (neu gefetcht).
- Branch **`fix/weather-buffer-aware-writers`** von `1876aa03`, Worktree
  `D:\Entwicklung\HASI\issue22-work\wt`. Der WIP `fix/weather-buffer-aware-time` ist
  unangetastet.
- **Noch keine Zeile Produktionscode geändert.** Es liegen nur Spec und Plan.
- Spec (Revision 3) und Plan auf `archive/design-history`, `6ce399f8` und `c8670a44`.
  Pfade siehe „Nächste Schritte". **Nicht** auf dem Feature-Branch.
- Zielbasis vom User entschieden: **eine interne Zone, naiv HA-lokal** — nicht aware
  durchgängig. Begründung in der Spec (R3-1).
- **Baseline neu gemessen** auf `1876aa03`: 7 failed / 3455 passed / 9 skipped /
  **367 errors**, und alle 367 sind `Failed: Lingering timer after test` — Teardown-
  Artefakt der Windows-Env, kein Sachfehler. Datei:
  `D:\Entwicklung\HASI\issue22-work\measure\baseline-1876aa03.txt`. Nur der Delta zählt.
- Umfang gezählt: **16 Writer** (`__init__.py` 7, `calculation.py` 5,
  `continuous_update.py` 3, `store.py` 1) + 3 `now`-Defaults in `weather_aggregate.py`
  + der `STAMP_FROM_STORE`-Zweig in `coerce_stamp`.

**Offen:** Plan-Tasks 1–8 alle. Reproduktion zu `Eifel-Joe#66`. Live-Test zu
`Eifel-Joe#64` auf HA-Test weiterhin nie gefahren.

### Verworfen

- **Meine Detektions-Idee (Ledger-Versatz).** Der Store hält tatsächlich aware Stempel
  neben den naiven (`irrigation.py:600/664/2861/2975`), aber ein Ledger-Eintrag entsteht
  beim Bewässern, ein Buffer-Stempel beim Poll: ihr Versatz ist *Schreibzeit-Differenz +
  Uhren-Differenz* und aus einem Paar nicht trennbar.
- **Mein Diskontinuitäts-Detektor** — widerlegt von `D4` der alten Spec: beim
  DST-Herbstübergang läuft die naive Folge eine Stunde rückwärts, byte-identisch zur
  Signatur eines Container-TZ-Fixes. Träfe jeden DST-Nutzer zweimal jährlich mit
  derselben Fehlergröße. Auch der Zukunfts-Check fällt (richtungsblind + falsch-positiv
  auf Boards ohne gepufferte RTC).
- **`STORAGE_VERSION`-Bump 14→15** (war `D3`) — revidiert. Ein Bump schreibt aware in den
  Store, ein HACS-**Rollback** liest die dann mit Code ohne Coercion → stilles Abschalten
  der Live-Schätzung. `D3`s harte Regel (Watermark + Puffer zusammen) erfüllt die
  Lesezeit-Coercion ebenfalls, weil beide durch denselben Aufruf gehen.
- **Aware Internals** (Richtung von `D1`) — der pauschale `except` macht daraus ein
  stilles Abschalten statt eines Fehlers.
- **Zwei meiner eigenen Entwurfs-Tests** — einer tautologisch (verglich den Helfer mit
  seinem eigenen Rumpf), einer zeitabhängig trotz „elapsed"-Namen. Beide im Plan ersetzt.

### Fallen

- **`nohup … &` zusammen mit `run_in_background`** koppelt den Prozess ab: Shell endet
  mit Exit 0, Ergebnisdatei bleibt **0 Bytes**. „0 Ausfälle" war ein Nicht-Lauf. Vor
  jedem Verdikt prüfen, ob der Lauf Tests GESAMMELT hat.
- **Heredoc-Terminator griff nicht** bei einem langen Dokument → die Apostrophe im Text
  wurden als Quotes gelesen, `unexpected EOF`. Für große Dokumente das Write-Tool.
- **`docs/superpowers/` ist NICHT gitignored.** Darf nie auf dem Branch gestaget werden,
  der als Upstream-PR geht (nennt `Eifel-Joe#22`). Und **nicht** in `.git/info/exclude`
  aufnehmen — dann scheitert `git add` im Archiv still, die `dist/`-Falle.
- **Es lag schon eine Spec im Archiv** (`2026-09-21-weather-buffer-aware-time-design.md`)
  mit `D1`–`D5`. Zwei ihrer Entscheidungen waren meinen überlegen. **Vor dem Entwerfen
  `archive/design-history` durchsehen**, nicht danach.
- **`tz_offset_h` bleibt in beiden Rahmen `+2.0`** — was kippt, ist `row["hour"]` (heute
  `10.5`, richtig `12.5`). Nicht den Offset pinnen, sondern das Paar. `calculation.py:796`
  warnt genau davor: ein aware-Wechsel lässt diese Arithmetik unberührt „and the suite
  green" — das ist die teure Hälfte (±23,5 % auf der Strahlung).

### Nächste Schritte

1. Plan lesen: `docs/superpowers/plans/2026-09-28-weather-buffer-aware-writers.md` auf
   `archive/design-history` (`c8670a44`). Spec daneben,
   `docs/superpowers/specs/2026-09-28-weather-buffer-aware-writers-design.md` (`6ce399f8`).
2. **Task 1** zuerst. Die zwei Ende-zu-Ende-Assertions müssen auf `1876aa03` **RED
   gesehen** werden, nicht angenommen.
3. Worktree `D:\Entwicklung\HASI\issue22-work\wt`, Interpreter absolut adressieren
   (kein eigenes `.venv` im Worktree) — Befehl steht im Plan unter „Environment".
4. Vor jedem Push: `grep -rn "Eifel-Joe" custom_components/ tests/` muss leer sein.

### Empfohlene Skills

- `superpowers:subagent-driven-development` (Tasks 4–6 sind mechanisch und unabhängig)
  oder `superpowers:executing-plans`
- `superpowers:test-driven-development` pro Task
- `code-doku` für die Kommentare in Task 7
- `pr-workflow`, sobald es upstream geht — plus Memory `hasi-pr-build-recipe`
- `superpowers:verification-before-completion` vor jedem „fertig"

## 2026-09-28 (8) — JustChrs Kommentare gesichtet; Eifel-Joe#22 ist die nächste Arbeit

### Was JustChr auf #176–#180 geschrieben hat (alle gemergt, 0 Reviews, 0 Inline-Kommentare)
- **`#177`: „Ready for the second half whenever you are."** → Das ist der Auftrag.
  `#177` war nur das BENENNEN der zwei Herkünfte; die Reparatur ist `JustChr#160`
  (Wetterpuffer OS-lokal gestempelt, HA-lokal zurückgelesen; beide naiv, also still).
  Bei uns `Eifel-Joe#22`, **offen und `upstream:freigegeben`** — Bau ist zugesagt.
- **`#179`:** „If you want to take that gap on, an issue for it would be welcome" —
  das war die Observed-Lücke, **erledigt** als `#180`.
- **`#176`:** veralteter Kommentar in `run_chain.py`, „nothing you need to do".
  Geprüft: steht **nicht mehr** auf master, er hat ihn selbst entfernt.
- **`#178` AUFGEKLÄRT** (unser Stand führte das als „ungeklärt"): der rote
  `test-ha-floor` war `test_solar_azimuth_bearing`, das `utcnow()` las und nur
  **~80 s am Tag** umfiel (05:14–05:15 UTC), wenn ein früherer Test HAs Zone
  nicht-UTC hinterlassen hatte. Gepinnt in `1bfa9643`. Unsere damalige Diagnose hatte
  die Uhr per 24-h-Sweep **verworfen** — richtige Größe gemessen, falsche Bedingung.

### Der WIP-Branch `fix/weather-buffer-aware-time` ist NICHT rebasebar — und teils überholt
- Stand `c9720a72` (+ `c17a8111`), **29 hinter** upstream. `upstream/master` ist
  inzwischen **`1876aa03`** (v2026.09.27, enthält unser `#180`) — `e42d0a69` ist schon
  wieder alt.
- ⛔ **Der Branch IST auf origin gepusht** → Projektregel „kein Rebase auf gepushten
  Branches". Nicht rebased; stattdessen **Probe-Rebase in einem Wegwerf-Worktree**
  gemessen und wieder abgebrochen. Branch ist unangetastet, `lokal == origin`.
- **Ergebnis der Probe:** Konflikt in `helpers.py` — dort stehen **zwei Entwürfe für
  dieselbe Sache**. `upstream/master` hat `coerce_stamp(value, provenance)` +
  `STAMP_FROM_STORE`/`STAMP_FROM_CLIENT` (= unser gemergtes `#177`), der WIP hat den
  älteren `as_stored_aware`. Sogar `_process_timezone()` steht in beiden — `#177` hat
  es übernommen. **Commit 1 des WIP ist also im Wesentlichen das, was als `#177` ging.**
- **Was übrig bleibt:** nur Commit 2 (`c9720a72`, +127/−93 über 10 Dateien) — der
  „aware flip" auf der Schreibseite, plus `tests/test_stored_stamp_timezone.py`.
  Er war selbst als unfertig deklariert; offen blieb die **zweite naive Herkunft**
  (Weather-Client-/Forecast-Zeilen sind **site-lokal**, nicht prozess-lokal).
- **Empfehlung: nicht rebasen, neu von `1876aa03` aufsetzen** — auf `coerce_stamp` als
  Fundament. `#177`s Docstring sagt das selbst: „this normalises to NAIVE, not to aware
  … an aware input is what the **write-side change will start producing**". Der WIP ist
  ab jetzt Ideengeber (vor allem für die zweite Herkunft), nicht Codebasis.

## 2026-09-28 (7) — PR 2 als überholt verworfen, #65 hinfällig, Worktrees aufgeräumt

- **PR 2 ist überholt, Branch gelöscht.** `fix/second-dispatch-joins-the-queue`
  (`1b3cc7d5`) wartete auf den Merge von `JustChr#165`; währenddessen ging sein Inhalt
  über den **zweiten Anlauf** (`issue2b-work`) als `JustChr#176` upstream. Geprüft statt
  angenommen: beide Testdateien liegen auf `master`, JustChrs
  `test_chain_append_on_second_dispatch.py` ist **größer** (314 statt 294 Zeilen) und
  trägt einen Test mehr; exklusiv hatte unser Branch nur noch `Eifel-Joe#…`-Verweise in
  Docstrings. `Eifel-Joe#2` war ohnehin schon zu.
  ⚠️ **Methodenfalle:** `git diff upstream/master HEAD` (zwei Punkte) gegen eine alte
  Basis sieht riesig aus (77 Dateien, 8093 „Löschungen") und sagt **nichts** — das ist
  upstreams neuere Arbeit. Aussagekräftig ist nur, was der Branch EXKLUSIV hat.
- **`Eifel-Joe#65` geschlossen, ohne etwas zu bauen** — JustChr hat den Verweis mit
  `213f8d91` selbst entfernt (hereingekommen mit `f0027213`). Gegengeprüft: auf
  `upstream/master` steht kein Verweis auf unseren Tracker mehr. Die verbliebenen
  „Eifel-Joe"-Treffer sind **Melder-Nennungen und Fork-URLs** (`#88` ist dort SEINE
  Nummer) — die dürfen bleiben. Einzeiler-PR entfällt.
- **Worktrees 24 → 2:** nur noch `HAsmartirrigation` + `pr139-work/archive-wt`.
  ~870 MB frei (1,1 GB → 258 MB). Belegt vor dem Löschen: Branches überleben
  `worktree remove`, und alle 7 uncommitteten Design-Dokumente lagen bereits im Archiv,
  zwei sogar in neuerer Fassung. Die `*-work`-Ordner mit ihren Messbelegen stehen noch.
- **Memory:** `hasi-pr2-task11-paused` gelöscht (stand falsch da), Lehre in
  `check-before-duplicating-work` eingearbeitet. Index 13,6 KB / 81 Einträge, keine
  toten Links, keine Waisen.

### Offen
- **`Eifel-Joe#66`** (Verteiler fragt das Prädikat nie) — Schwere angenommen, nicht
  gemessen; erster Schritt ist die Reproduktion.
- **Live-Test zu `#64` auf HA-Test** — nie gefahren, `custom_components/**` ist über MCP
  nur lesbar. Der Fix ist ohne Live-Beleg upstream gegangen (gemergt als `JustChr#180`).
- `pr2-work` (55 MB), `pr174-work`, `issue53b-work`, `prerelease-work` (je ~45 MB) haben
  nach dem Worktree-Abzug noch auffällig viel Inhalt — vermutlich Build-Abfall, nicht
  geprüft.

## 2026-09-28 (6) — Eifel-Joe#64 ABGESCHLOSSEN: JustChr#180 GEMERGT

- **`JustChr#180` GEMERGT**, CI **4/4 grün**, beim Merge bereits durch. Branch
  `fix-an-external-run-reaches-the-chain` gepusht, 8 Commits auf `e42d0a69`.
- **`Eifel-Joe#64` geschlossen** (Regel P2: Upstream zu → unseres zu), Label
  `upstream:gemeldet` gesetzt, Ergebnis-Kommentar mit den gemessenen Zahlen drin.
- **`Eifel-Joe#45` geschlossen** — sein `JustChr#179` ist als `dee2310f` gemergt.
- **`Eifel-Joe#66` NEU angelegt**: `distributor.py` fragt `zone_run_in_flight` nie, ein
  extern bewässertes Member ist für den Sweep unsichtbar (`typ:fehler`,
  `schwere:mittel`, `groesse:M`, `beobachten`). Schwere dort **per Analogie angenommen,
  nicht gemessen** — der erste Schritt ist die Reproduktion, wie bei `#64` das Tor.
- **`Eifel-Joe#42`** um `#64`/`#65`/`#66` fortgeschrieben.
- **Archiv gepusht:** `archive/design-history` `2959be38`, 7 Dateien.
- **MEMORY.md kompaktiert:** 22,3 KB → 13,7 KB, 82 Einträge, keine Waisen mehr
  (3 unverlinkte Dateien wieder angebunden).

### Weiterhin offen
- **`Eifel-Joe#65`** als Einzeiler-PR.
- **Live-Test auf HA-Test wurde NIE gefahren** — `custom_components/**` ist über MCP nur
  lesbar, der Branch ließ sich von hier nicht installieren. Der Fix ging ohne Live-Beleg
  upstream (Suite + Mutationsmatrix trugen die Freigabe). Nachholen, sobald deployt:
  Fremdöffnung > 300 s während eines sequenziellen Zyklus, erwartet wird die
  Drop-Logzeile und **kein** zweiter Lauf der Zone.
- **`Eifel-Joe#66`** reproduzieren und messen, bevor entworfen wird.
- Worktree `issue64-work/wt` kann weg, sobald der Live-Test nicht mehr daran hängt.

## 2026-09-28 (5) — Eifel-Joe#64 GEBAUT, alle Gates grün, nichts gepusht

### Stand (verifiziert)
- **8 Commits** auf Branch `fix-an-external-run-reaches-the-chain`, Worktree
  `issue64-work/wt`, **lokal, nicht gepusht**. Nur Code + Tests (8 Dateien,
  `+532/−29`), `docs/` bewusst untracked.
- **Basis ist gewandert:** JustChr hat `#176`–`#179` gemergt, `upstream/master` =
  **`e42d0a69`** (vorher `6acfc819`). **Mitten im Bau rebased** statt erst in Task 9 —
  sonst hätten Gates und Mutationsmatrix gegen eine tote Basis gemessen. Datei-
  Überschneidung null, Rebase sauber, `0 behind`.
- **Gates:** Volllauf `7 failed, 3455 passed, 9 skipped, 367 errors`; **Namens-Diff
  leer (374 = 374)** gegen die NEU auf `e42d0a69` gemessene Baseline
  (`issue64-work/baseline-e42d0a69.txt` — inhaltsgleich zur alten, die 6 Upstream-
  Commits änderten keinen Fehlernamen); `black --check` + `ruff` sauber;
  Referenz-Prüfungen **0/0/0** (Code, Commit-Messages, PR-Body).
- **Mutationsmatrix 16 von 16 gefangen**, Quellen byte-genau wiederhergestellt,
  Referenzlauf `collected 102 items` / 0 Vorab-Fehler (die Sammel-Prüfung ist im
  Runner verdrahtet).
- **Task 1 war ein echtes Tor und hat gehalten:** der Deckel greift. Gemessen
  `credit −13.800` → zweiter Lauf schreibt `(2, 0.0)`, `pre + depth = 6.200` →
  **6,20 mm verworfen**, und das ist exakt die Fremdgutschrift. Zuviel-Wasser ist
  damit belegt der *unsichtbare* Fehler.
- **Design-Historie archiviert** (Regel P1): `archive/design-history` **`2959be38`**,
  7 Dateien (Spec, Plan, Schwester-Pfad-Protokoll, Mutations-MD + JSON, 2 Probes).
  **Ebenfalls lokal, nicht gepusht.**

### Befunde aus dem Bau (alle gemessen, nicht gelesen)
- **Es sind ZEHN Aufrufstellen, nicht neun.** `run_chain.py:390` (`_chain_join`) kam mit
  JustChrs `#176` herein: ein zweiter Dispatch reiht eine Zone nicht mehr ein, wenn ihr
  Ventil fremd offen steht. Gewollt, deckungsgleich mit der Fenster-1-Entscheidung.
  **Nur durch den frühen Rebase + erneutes grep gefunden**, der Plan konnte es nicht
  wissen.
- **Der Selbsttreffer-Test sicherte nichts.** Er prüfte auf einen Eintrag, den er selbst
  gesetzt hatte → Mutation zurück aufs weite Prädikat überlebte die ganze Suite. Jetzt:
  *veralteten* Stempel setzen und prüfen, dass die Kante ihn überschreibt.
- **Der neue Wrapper durfte `measured_l` verschlucken** — 86 Tests grün, während eine
  flussgemessene Gutschrift still auf Zeit×Durchsatz zurückgefallen wäre. Entstanden
  beim Umhängen eines Mocks auf die neue Naht. Pin prüft jetzt den ganzen Aufruf.
- **Mutant 3 (`<` → `<=`) überlebte den ersten Lauf** — der Plan hätte ihn als
  „unbeobachtbar" durchgewinkt. Nicht abgenickt: die Grenze ist einen Augenblick breit,
  `freeze_time` fängt sie. Die beiden Linien liegen auf **entgegengesetzten** Seiten
  (Provenienz-Schwelle inklusiv, Ceiling exklusiv wie das Self-Closing-Vorbild).
- **Zwei Kommentare** begründeten ihren Code nicht mehr (Rotations-Abschreibung stützte
  sich auf ein eingefrorenes Ceiling im Run-Record, Kalkulations-Vertagung auf einen
  Anker vor Ventilöffnung — ein Fremdlauf hat beides nicht). Code richtig, Argument zu
  kurz → gefixt.

### Fallen
- ⚠️ **Baseline-Filter:** `grep -E "^(FAILED|ERROR) "` fängt auch **Logzeilen**, die mit
  `ERROR ` beginnen (eine aus `batch.py:304`) → 375 statt 374, sieht aus wie eine
  Regression. Richtig ist `^(FAILED|ERROR) tests/`.
- ⚠️ **Eine Rotation mit zwei Zonen wird von ihrer eigenen Abschreibung zerlegt:** ist
  nichts mehr mit `remaining > 0` da, läuft `_chain_release` und nullt `state.rotation`
  — `rotation.remaining[2]` ist dann nicht mehr lesbar. Beide Rotations-Tests brauchen
  eine **dritte Zone**. Kostete zwei Runden.
- ⚠️ **`_obs_coord` konfiguriert `store.get_zone` nicht** → Auto-Mock ist truthy, die
  Öffnen-Kante nimmt fälschlich den Flow-Sampler-Pfad und stirbt in `_flow_build_meter`.
  Ein `coord.store.get_zone = Mock(return_value=zone)` dazu.
- ⚠️ Eine Ergebnisdatei **nicht lesen, solange der Lauf noch läuft** — der Namens-Diff
  liest sonst eine halbe Datei und meldet 374 Phantom-Regressionen.

### Nächste Schritte (alles freigabepflichtig)
1. `git push -u origin fix-an-external-run-reaches-the-chain` + `gh pr create` gegen
   `JustChr/HAsmartirrigation` mit `issue64-work/pr-body.md` (Body im Chat freigegeben?).
2. Push von `archive/design-history` (`2959be38`).
3. `Eifel-Joe#64` kommentieren + Label `upstream:gemeldet`.
4. `Eifel-Joe#45` schließen (sein `#179` gemergt), `#42` um `#64`/`#65` ergänzen.
5. Neues Issue: `distributor.py` fragt `zone_run_in_flight` nie — Schwesterbefund,
   Beleg + Begründung in `archive/design-history` unter `…-sister-paths.md`.
6. `Eifel-Joe#65` als Einzeiler-PR — weiter offen.
7. **Live-Test auf HA-Test steht aus** — über MCP ist `custom_components/**` nur lesbar,
   der Branch lässt sich von hier nicht installieren. Braucht Deploy durch den User.

## 2026-09-28 (4) — Eifel-Joe#64: Tor entschieden, Spec + Plan freigegeben, nichts gebaut

### Stand (verifiziert)
- **Das Tor ist entschieden** (User, zwei Fragen): Form = **zwei kleine Teile** — vierte
  Quelle in `zone_run_in_flight` (Fenster 1) + Meldung an die Kette an der Schließen-Flanke
  (Fenster 2). Schwelle = Provenienz-Linie `OBSERVED_SAMPLE_MIN_RUN_SECONDS` (300 s), **nur
  für Fenster 2**; Fenster 1 ohne Schwelle. Das Prädikat bleibt **global** (ausdrücklich
  bestätigt, nachdem die Mitleser benannt waren).
- **Spec + Plan geschrieben und freigegeben**, beide **untracked** im Worktree:
  `issue64-work/wt/docs/superpowers/specs/2026-09-28-external-run-reaches-the-chain-design.md`
  und `.../plans/2026-09-28-external-run-reaches-the-chain.md` (9 Tasks, echter Test- und
  Produktionscode pro Schritt). Noch **nicht** im Archiv — das ist Plan-Task 9.
- **Worktree** `issue64-work/wt`, Branch `fix-an-external-run-reaches-the-chain`, auf
  `upstream/master` = `6acfc819` (`rev-list --count` = 0 geprüft), `_local_socket_unblock.py`
  kopiert. **Kein Produktionscode angefasst**, `git log -1` steht auf `6acfc819`.
- **Befunde beim Lesen, alle code-belegt:**
  - `_chain_drop_zone` (`run_chain.py:457`) deckt **beide** Geometrien — Queue *und*
    `rotation.remaining` *und* `planned`, Live-Marke unter `held`-Gate — und ist der Weg,
    den `async_stop_zone` nimmt. Fenster 2 braucht kein neues Werkzeug.
  - **Registrierung allein lässt die Fenster nicht zusammenfallen**, nur Registrierung +
    Finalisierung. Und die kostet: `async_resume_self_closing_runs` (`self_closing.py:1191`)
    adoptiert jeden persistierten Satz, `master.py:242` blockt den Boot-Master-Off,
    `run_chain.py:319` friert den Zyklus bei geleaktem Satz, `_record_run` schreibt doppelt.
  - **Der Überschuss wird still verworfen:** `_run_ceiling` (`irrigation.py:2789`) =
    `max(target, pre)`, und `self_closing.py:806-808` schreibt `min(ceiling, pre + depth)`.
    Damit ist Zuviel-Wasser der *unsichtbare* Fehler und Zuwenig der *sichtbare* — das hat
    die Schwellwert-Frage entschieden. **Gelesen, nicht gemessen**; Plan-Task 1 misst es und
    stoppt, wenn der Deckel nicht greift.
  - `calculation.py:510` verschiebt die Berechnung, und **alle fünf** Abholstellen sind
    Teardowns eigener Läufe (`_release_chain_zones`, `_run_valve_metered`, `_sc_finish_run`,
    `async_stop_self_closing`, `async_run_distributor_cycle`) — Observed ist keine davon.
  - `distributor.py` fragt `zone_run_in_flight` **gar nicht** → ein extern bewässertes
    Member ist für den Sweep unsichtbar. Schwesterbefund, **eigenes Issue**, nicht dieser
    Branch.
- **Prod-Evidenz per Diagnostics** (nicht aus dem Feature-Flag gefolgert): **alle drei**
  Zonen haben `observed_entity` = ihr eigenes `confirm_entity` (`valve.wasser_vorne`,
  `valve.wasser_hinten`, `valve.wasser_beet_valve_l1`), alle `service` + `automatic`,
  `maximum_duration` 3600/3600/2700. Im Run-Log stehen **sieben** Fremdläufe: 72 s, 90 s,
  718 s, 718 s, 2153 s, 10518 s, 21304 s.

### Verworfen
- **Observed als vollwertiger Lauf** (Satz in `CONF_ACTIVE_VALVE_RUNS` + normale
  Finalisierung): deckt beide Fenster aus einem Mechanismus, aber vier belegte
  Nebenwirkungen (oben). Erkennbar daran, dass jede eine eigene Absicherung bräuchte.
- **Nur die Meldung an die Kette:** lässt den wahrscheinlicheren Prod-Fall offen —
  Handöffnung während des Morgenzyklus, Zug kommt währenddessen.
- **Schmale Variante** (nur `run_chain.py:367`/`:683` fragen Observed): eine zweite,
  konkurrierende Antwort auf die Frage, die `run_state.py` laut eigener Doku genau einmal
  beantworten soll.
- **Anteilige Verrechnung:** erreicht die rotierende Geometrie nicht — `rotation.remaining`
  wird einmal bei Zyklusstart gebaut und nie aus der Zonendauer nachgelesen.
- **Neue mm-Konstante als Schwelle:** Wert nicht aus dem Bestand herleitbar, und JustChr
  fragt bei neuen Konstanten nach der Herleitung.

### Fallen
- ⚠️ **Heredoc `<<'EOF'` scheiterte am Markdown-Inhalt** (`unexpected EOF while looking for
  matching '`), Datei blieb leer. Für Markdown mit Backticks/Apostrophen das Write-Tool —
  steht auch im Kopf dieser Datei, gilt also doppelt.
- ⚠️ **Drei bestehende Tests stubben genau die Stelle, die Plan-Task 3 umbenennt:**
  `tests/test_observed_watering.py:282`, `:514`, `:630` setzen
  `coord.zone_run_in_flight = Mock(return_value=False)`. Dort muss danach
  `_si_run_in_flight` stehen, sonst läuft das echte Prädikat gegen einen Mock-Store.
- ⚠️ **`_observer_coordinator` in `test_experimental_features.py` stubbt es NICHT** — dort
  antwortet das echte Prädikat auf dem Mock-Store mit `False`. Nach der vierten Quelle kann
  sich das ändern; Plan-Task 3 Schritt 6 schaut ausdrücklich hin, statt es anzunehmen.
- ⚠️ **Zwei Plan-Tests sind auf `master` schon grün** (Deckel-Grenze, Provenienz-Gegenprobe)
  und im Plan als solche markiert. Sie tragen nur über die Matrix — Mutant 2 und Mutant 7
  sind dort an sie gebunden.
- **Diagnostics-Pfade:** `data.store.zones` ist eine **Liste**, `data.store.zones.1.feld`
  scheitert (`cannot descend into list`). Mit `diagnostics_data_limit=1` + `offset`
  paginieren; `truncate_at_bytes` unter ~9500 schneidet eine Zone mit Run-Log ab.

### Nächste Schritte
1. **Umsetzung in frischer Sitzung**, Plan-Task 1 zuerst (die Messung). Greift der Deckel
   nicht, stoppen und melden statt weiterbauen.
2. Dann Task 2–5 (je RED --> GREEN --> Commit), 6 Schwester-Pfade, 7 Gates, 8 Matrix,
   9 Live + Archiv + PR-Text zur Freigabe.
3. `JustChr#179` Review abwarten. `#176`/`#177`/`#178` weiter offen; `#178`s roter
   `test-ha-floor` unverändert ungeklärt.
4. `Eifel-Joe#65` als Einzeiler-PR — offen.
5. Tracking-Issue `Eifel-Joe#42` um `#64` und `#65` ergänzen — offen.
6. Neues Issue für den Verteiler-Schwesterbefund (`distributor.py` fragt das Prädikat nie).

### Empfohlene Skills
`superpowers:subagent-driven-development` (frischer Subagent pro Task),
`superpowers:test-driven-development` in jedem Task,
`superpowers:verification-before-completion` vor jedem „fertig", `code-doku` für die
Kommentare, `pr-workflow` für Task 9.

## 2026-09-28 (3) — Eifel-Joe#45 gebaut: JustChr#179; zwei Folge-Issues aus dem Bau

### Stand (verifiziert)
- **`JustChr#179` OFFEN, CI 4/4 GRÜN, `CLEAN`** — `fix(chain): a rotating zone watered
  elsewhere keeps no turn`, Branch `fix-a-rotating-zone-already-watered-keeps-its-turn`,
  Worktree `issue45-work/wt`, 6 Commits auf `6acfc819`, gepusht. Unser Issue
  **`Eifel-Joe#45` kommentiert + korrigiert + `upstream:gemeldet`**.
  Nebenbefund zum offenen Rätsel von `#178`: derselbe `test-ha-floor`-Job ist hier auf
  derselben Basis grün.
- **Der Fix:** `Rotation.in_flight` — die Zone, deren Slot die Rotation selbst dispatcht
  hat. Anspruch **vor** dem Dispatch-`await`; `_chain_advance` liest ihn dort, wo es
  ohnehin `last_finish` stempelt. Zwei Dateien, `+226/−0`. Spec + Plan + Mutationsmatrix:
  `archive/design-history` **`18d7e1f3`**, 0 voraus.
- **Gates:** Suite `7 failed, 3395 passed, 9 skipped, 367 errors`; **Namens-Diff leer
  (374 = 374)** gegen die auf `6acfc819` NEU gemessene Baseline
  (`issue45-work/baseline-6acfc819.txt`, identisch zur alten von `1c071cf0`);
  `black`/`ruff` sauber; Referenz-Prüfungen 0/0/0 auf hinzugefügte Zeilen UND
  Commit-Messages; **Mutationsmatrix 7 von 7 gefangen**.
- **`Eifel-Joe#64` NEU** (`schwere:hoch`, `prod-scharf`, `groesse:L`): eine extern
  bewässerte Zone ist für die Kette unsichtbar — **in beiden Geometrien**.
  `observed_watering.py` bucht über `_record_run` + `async_write_watered_bucket`,
  registriert keinen aktiven Lauf und ruft nie `_chain_advance_for_run`. Gemessen gegen
  `6acfc819`, sequenziell: Zone 2 wird mit **+6,20 mm** gutgeschrieben, bleibt in der
  Warteschlange, wird danach **volle 600 s** bewässert. Rotierend gegen den Branch MIT
  `#179`: trotzdem ein zweiter 300-s-Slot. **HA-Prod ist die betroffene Konstellation** —
  `zone_sequencing: "sequential"`, `observed_watering_enabled: true`, tägliche
  „alle Zonen"-Schedule (aus den Diagnostics gelesen, nicht angenommen).
- **`Eifel-Joe#65` NEU** (`typ:politur`, `schwere:niedrig`, `groesse:S`): `master` trägt in
  `tests/test_chain_carries_its_plan.py:1` den einzigen Querverweis auf unseren Tracker
  (`Eifel-Joe#2`), hereingekommen mit `f0027213` = `JustChr#165`. Eigener Einzeiler-PR
  vorgesehen.

### Verworfen
- **`in_flight` bei verweigertem Dispatch zu räumen.** Eine Verweigerung setzt
  `remaining = 0.0`, und nur ein frischer `Rotation`-Aufbau stellt das wieder her — der
  startet `in_flight` ohnehin auf `None`. Wäre eine Zeile ohne beobachtbare Wirkung
  gewesen; stattdessen Kommentar + Test, dass eine Verweigerung eine spätere Übernahme
  nicht verdeckt.
- **Anteilige Verrechnung des Fremdlaufs** (User-Entscheidung): der ganze Rest wird
  abgeschrieben, symmetrisch zum schon behobenen Zweig. Folge, im PR-Body benannt: ein
  `run_zone` mit `duration_minutes: 1` zum Ventil-Testen streicht die restliche
  Bewässerung dieser Zone für den Zyklus.

### Fallen
- ⚠️ **Der RED-Test, den das Issue als „fertig" verlinkte, war nicht erfüllbar.** Fall 2
  der Probe drückte die Übernahme durch `zone_run_in_flight → False` aus — die echte
  Prüfung meldet dort aber ohnehin schon `False`. Gemessen war der Zustand am
  Entscheidungspunkt **identisch** zu `test_two_zones_take_turns`, das daraus das
  Gegenteil verlangt. Vor dem Bau gegen einen gelieferten Test IMMER prüfen, ob sein
  Grün-Zustand von einer korrekten Implementierung überhaupt erreichbar ist.
- ⚠️ **Zwei Tests waren grün, weil sie nicht fallen konnten.** Die Marken-Assertion prüfte
  ins Leere (der Fremdlauf verbraucht die Marke selbst über `_run_ceiling`), und der
  Verweigerungs-Test prüfte eine Entscheidung, an der die Verweigerung keinen Anteil hatte
  (der nächste Dispatch überschrieb den Anspruch im selben Durchlauf). **Beide fand die
  Mutationsmatrix, nicht das Lesen.**
- ⚠️ **Meine eigenen „dokumentiert überlebenden" Mutanten waren beide falsch begründet** —
  der Review widerlegte sie, ich habe beide nachgemessen und beide sind tötbar. Eine davon
  (Anspruch nach dem `await`) ist der schädlichste Fehlermodus der ganzen Änderung: alle
  Zonen werden als Übernahme abgeschrieben, der Zyklus endet nach je einem Slot. Ein
  Überlebender ist zuerst ein zu schwacher Test, **dann** erst eine harmlose Mutation.
- ⚠️ **„prod-scharf" nicht aus einem eingeschalteten Feature folgern.** Ich nannte die
  Observed-Lücke prod-scharf, weil `observed` an ist — die dort beschriebene Lücke
  brauchte aber Rotation, und Prod läuft sequenziell. Die Konfiguration nachlesen, bevor
  die Schwere behauptet wird; der echte Grund war am Ende stärker, hätte aber auch
  schwächer sein können.
- **Der Bash-/Edit-Klassifizierer fiel mehrfach für mehrere Züge aus** (Lesen lief weiter).
  Nicht mehr als zwei-, dreimal nacheinander versuchen, sonst bricht der Turn ab —
  lesende Arbeit vorziehen und später wiederkommen.

### Nächste Schritte
1. **`JustChr#179`** — Review abwarten. Bei Einwänden `superpowers:receiving-code-review`,
   Einwand **in JustChrs Worten** in `Eifel-Joe#45` (Regel P2), Label mitziehen.
2. **`#176`/`#177`/`#178`** stehen weiter offen; `#178`s roter `test-ha-floor` ist
   unverändert ungeklärt (siehe Eintrag 2026-09-28 (2)).
3. **`Eifel-Joe#64`** ist der schwerste offene Punkt und prod-scharf. Vor dem Bau die Form
   entscheiden: registriert Observed seinen Lauf im aktiven Laufspeicher (dann fallen
   beide Fenster zusammen), oder bekommt die Kette eine eigene Meldung?
4. **`Eifel-Joe#65`** als Einzeiler-PR, und die Referenz-Prüfung dauerhaft verankern statt
   sie pro Sitzung neu zu tippen.
5. **Tracking-Issue `Eifel-Joe#42`** um `#64` und `#65` ergänzen; Punkt 8 (`#45`) auf
   „gebaut, `JustChr#179` offen" setzen.

### Empfohlene Skills
`superpowers:receiving-code-review`, sobald JustChr antwortet;
`superpowers:verification-before-completion` vor jedem „fertig";
`superpowers:brainstorming` für die Formfrage in `Eifel-Joe#64`.

## 2026-09-28 (2) — Live-Befund auf HA-Prod: watering_now kann bei Service-Zonen nie angehen; JustChr#178

### Stand (verifiziert)
- **✅ `JustChr#175` IST GEMERGT** (27.09. 20:42 UTC, gesquasht zu **`6acfc819`**, jetzt
  master). `git diff 6d4b9cc1 6acfc819` über `custom_components`/`tests` ist **leer** —
  byte-identisch übernommen. **`Eifel-Joe#53` ist kommentiert und GESCHLOSSEN** (Regel
  P2), mit Merge-Beleg und Verweis auf das Live-Protokoll. Kein Rest; die Zyklus-Frage
  war immer `Eifel-Joe#55`.
- **`JustChr#178` OFFEN** — `fix(sensor): a service zone shows when it is watering`,
  Branch `fix-a-service-zone-shows-when-it-is-watering`, Worktree `issue63-work/wt`,
  1 Commit auf `1c071cf0`, gepusht. Unser Issue: **`Eifel-Joe#63`**, kommentiert +
  `upstream:gemeldet`.
  🔴 **CI: `test-ha-floor` ROT**, `lint`/`test (3.13)`/`validate` grün. Gefallen ist
  `tests/test_solar_azimuth_bearing.py::test_the_repaired_schedule_fires_at_the_same_time_as_before`
  mit `assert None is not None` — eine Datei, die diese Änderung nicht berührt.
  **Was geprüft ist:** lokal 16/16 grün, im Voll-Lauf grün, **nicht** in der Baseline,
  Namens-Diff leer. **Zwei Hypothesen gemessen und BEIDE widerlegt:** (a) Tageszeit —
  Probe `issue63-work/probe_azimuth_clock.py` fährt den Referenz-Zeitpunkt über 24 h,
  **kein** Startpunkt liefert `None`, auch 05:14 UTC nicht; (b) der neue master-Commit
  `6acfc819` — das ist unser eigener `#175` und fasst nur `distributor.py` an.
  **Nicht nachstellbar hier:** der Floor-Job ist Python 3.13 + HA 2025.5.0, auf Windows
  doppelt blockiert. **Re-Run nicht möglich** (keine Admin-Rechte), `--force` ist per
  Projektregel aus. **Offen: Wurzel unbekannt** — nicht geraten. Stattdessen
  [an JustChr gefragt](https://github.com/JustChr/HAsmartirrigation/pull/178#issuecomment-5864114578)
  mit der ganzen Evidenz, Bitte um Re-Run und um den Hinweis, ob er den Test anderswo
  fallen sieht. **Eine Spur ist ausdrücklich NICHT ausgeschlossen:** der Floor-Job
  installiert seine transitiven Abhängigkeiten ungepinnt (`uv pip install` ohne Lock),
  eine Solar-Mathe-Abhängigkeit könnte sich zwischen den grünen Läufen von heute früh
  und 05:14 bewegt haben. **Das ist der erste Faden, wenn es reproduzierbar ist.**
  Probe: `issue63-work/probe_azimuth_clock.py`.
- **DREI Upstream-PRs offen** (`#175` ist gemergt): `#176` (chain second dispatch),
  `#177` (time provenances PR 1), `#178` (watering_now). Alle auf Basis `1c071cf0`,
  alle mit leerem Namens-Diff. `#176`/`#177` `CLEAN` mit je 4 SUCCESS, `#178` rot.
- **Der Befund, live auf HA-Prod gefunden (User meldete: „Bewässerung läuft, Entitäten
  zeigen es nicht"):** `binary_sensor.<zone>_watering_now` kann bei `watering_mode:
  service` / self-closing **nie** angehen. Der Sensor spiegelt `zone_watch_entity`, das
  ausschließlich `linked_entity` liest — und die ist bei einer `run_service`-Zone
  `null`. Also abonniert er nichts und `is_on` ist konstant `False`. **Strukturell,
  kein hängengebliebener Zustand.** An der gespeicherten Config belegt, nicht aus dem
  Symptom erschlossen.
  **Der Fix ist eine bestehende Regel**, angewandt auf den einen Verbraucher, dem sie
  fehlte: `observed_watering.py` macht den Rückfall auf `observed_entity` schon, und
  `store.py` kommentiert ihn am Feld selbst.
- **Messung vom 28.09. (HA-Prod, nichts verändert):** drei Zonen wässerten nacheinander,
  alle Läufe korrekt verbucht — Kirschlorbeer 04:46:14Z / 48,0 L, Kirschbaum
  04:49:07Z / 26,0 L, Beet 04:54:16Z / 15,5 L — und **alle drei `watering_now` standen
  über vier Läufe auf `off` mit `last_changed` eingefroren auf dem Boot-Zeitstempel**.
  Steuerpfad gesund, nur die Anzeige tot.
- **Gates `#178`:** 7 failed / **3370** passed / 9 skipped / 367 errors, Namens-Diff
  **leer** (374 = 374), `+4` nach Definition, `black`/`ruff` clean, Referenz-Prüfungen
  0 / 0 / je genau 1. **Mutationsmatrix 4 Mutanten, 3 getötet**, einer dokumentiert
  überlebend (`or None` — masters eigener Term, unbeobachtbar).
- **Regel P1:** `archive/design-history` **`b83c1aff`**, 0 voraus, mit
  `reconstructed/2026-09-28-service-zone-watering-now.md`.
- **Tracking-Issue `Eifel-Joe#42` nachgetragen** (beide Sprachhälften): `#62` als neuer
  Punkt **2a**, `#63` als **13a**, `#53` durchgestrichen mit Merge-Beleg (Punkt 5a),
  `#22` (Punkt **24**) auf „PR 1 eingereicht, PR 2 wartet auf dessen Merge" inklusive
  des `tz_offset_h`-Fallstricks, `#46` (Punkt **25**) mit der beantworteten
  Produktfrage. Strukturkontrolle vor dem Absetzen: 19 Überschriften unverändert,
  Einträge 96 → 100, Original gesichert in `issue63-work/issue42-body.orig.md`.
- ⚠️ **Beim Nachtragen gefunden, Punkt 8 von `#42`:** `Eifel-Joe#45` (rotierende Zone,
  zwischen ihren Zügen übernommen, wird doppelt bewässert) ist **NICHT** das, was
  `JustChr#176` behebt. Die Notiz „der fertige PR 2 kann rebasen" stand in `#42` **und**
  an `#45` selbst — gemeint war die Arbeit, die jetzt als `#176` für `Eifel-Joe#62`
  draußen ist, ein anderer Defekt. **Für `#45` ist nichts gebaut**, und der erste
  Schritt seines eigenen Kommentars („re-check whether master still carries this
  defect") ist bis heute nicht gemacht — weder gegen `c5330c7f` noch gegen `6acfc819`.
  In `#42` Punkt 8 jetzt so vermerkt, damit es niemand für abgehakt hält.
- **Die Nachprüfung IST jetzt gemacht (28.09.): master trägt `Eifel-Joe#45` noch** —
  gemessen, nicht gefolgert, und
  [am Issue kommentiert](https://github.com/Eifel-Joe/HAsmartirrigation/issues/45#issuecomment-5864595231).
  `run_chain.py` ist zwischen `1c071cf0` und `6acfc819` byte-identisch.
  **Was `JustChr#165` wirklich brachte:** einen Übernahme-Wächter in
  `_chain_rotation_advance`, der aber an `zone_run_in_flight(zone_id)` hängt — also
  daran, daß der fremde Lauf beim Zug der Zone NOCH LÄUFT. Der gemessene Fall des
  Issues ist der andere (fremder Lauf vorher fertig), dann meldet die Prüfung wieder
  `False` und der Wächter greift nie. **Defekt halbiert, nicht behoben.**
  **Messung**, rotierend, 2 Zonen, Slot 300 s, eine Variable:
  fremder Lauf läuft noch → `writing off zone 2 and its remaining 600s`, kein zweiter
  Slot; fremder Lauf fertig → `dispatched: [(1, 300.0), (2, 300.0)]`, `remaining[2]`
  600 → **300**, also zweite Eimer-Gutschrift für eine voll bewässerte Zone.
  **Warum die zweite Hälfte strukturell ist:** `Rotation` trägt `slot, absorption,
  order, remaining, last_finish, cursor` — **keinen Vermerk, wer in dieser Runde schon
  bewässert hat**. `last_finish` merkt sich WANN, nicht WER.
  **Probe = fertiger RED-Test:** `issue63-work/probe_45.py` (Scratch, zum Ausführen
  nach `tests/` kopieren; ihr erster Fall ist die Kontrolle gegen einen Rückfall der
  schon behobenen Hälfte). Der Worktree wurde danach wieder sauber hinterlassen.

### Verworfen
- **`confirm_entity` als zweiten Rückfall mitzunehmen** (User-Entscheidung 28.09.):
  es bedeutet „das Ventil hat das Öffnen bestätigt", nicht „es fließt Wasser" — eine
  neue Zusage statt der bestehenden Regel konsistent angewandt.
- **Den Rückfall in `zone_watch_entity` selbst zu legen.** Observed-Watering setzt die
  zwei selbst zusammen und der OpenSprinkler-Pfad löst aus `linked_entity` einen
  Running-Sensor auf; den Accessor zu verbreitern hätte beide ohne Grund erreicht.

### Fallen
- ⚠️ **`is_on` prüft `self.hass`, nicht den an `__init__` übergebenen `hass`.** HA setzt
  das erst beim Hinzufügen zur Plattform. Ein im Test direkt gebauter Sensor meldet
  deshalb `False`, **egal was er spiegelt** — der erste grüne Lauf war aus dem falschen
  Grund grün, alle vier Zusagen wären gegen eine kaputte Implementierung durchgegangen.
  Der Helfer setzt jetzt `sensor.hass = hass`, wie die Plattform es tut.
- ⚠️ **Ein einmal geführter RED-Beleg gilt nicht mehr, wenn der Test sich danach
  ändert.** Nach der Fixture-Korrektur neu geführt: Quelle per `git checkout --` auf
  master, `assert None == 'valve.…'`, dann zurück, 4 passed. Das ist
  `verification-must-exercise-the-change` eine Ebene höher.
- **Ein gemeldetes Symptom kann zwei Sachen sein.** Der User nannte Kirschbaum als
  offen; Kirschbaum war zu und verbucht, offen war das Beet (nächste Zone der Kette).
  Erst die Ventile mit Zeitstempeln lesen, dann urteilen — und das Beet von offen bis
  zur Verbuchung durchbeobachten, statt „schließt sich schon" zu sagen.
- **Das Tuya-Beet-Ventil rundet auf Minuten auf.** 273 s berechnet → 300 s offen. Wer
  auf die berechnete Dauer wartet, hält es fälschlich für hängend.

### Nächste Schritte
1. **`#178`s roten Floor-Job verfolgen** (JustChrs Antwort abwarten), und CI/Review von
   `#176` und `#177` lesen, bevor etwas Neues beginnt. Bei Einwänden
   `superpowers:receiving-code-review`, Einwand **in JustChrs Worten** ins jeweilige
   Issue (Regel P2).
2. ⛔ **`Eifel-Joe#52` ist ERLEDIGT und GESCHLOSSEN — nicht nochmal bauen.** Der frühere
   Eintrag hier („wartet als eigener Einzeiler") war falsch: `exc_info=True` steht seit
   `JustChr#171` (`59a3da8c`) in master, geprüft an `live_estimate.py:1533`. Der Rest —
   erster Fehlschlag pro Refresh auf WARNING — ist **`Eifel-Joe#56`** und braucht zuerst
   eine Entscheidung über den Reset-Scope (pro Refresh / pro Zone / pro Prozess),
   `typ:produktentscheidung`.
3. **`Eifel-Joe#22` PR 2** erst nach `#177`s Merge (Schreiber, Migration, Fixtures).
4. **Triage:** `Eifel-Joe#57`, `#58`, `#61`.
5. **HA-Prod:** `flow_calibration_advised` steht auf Kirschbaum — **nicht übernehmen**,
   der Schlauch ist defekt (`hasi-kirschbaum-hose-defect`). Prod läuft v2026.09.20, der
   nächste Produktiv-Build zieht alle vier PRs plus die zwei gemergten mit.
6. **HA-Test:** `Gardena1`s Durchflusssensor-Feld zeigt noch auf die Sonde — laut User
   egal, kein Handlungsbedarf.

### Empfohlene Skills
`superpowers:receiving-code-review`, sobald JustChr antwortet;
`superpowers:verification-before-completion` vor jedem „fertig".

---

## 2026-09-28 — Drei PRs offen: JustChr#175, #176, #177; Eifel-Joe#22 PR 1 gebaut, Chain-PR 2 eingereicht

### Stand (verifiziert)
- **Drei Upstream-PRs offen, alle auf Basis `1c071cf0`:**
  - **`JustChr#175`** — `fix(distributor): a dry member run is not a delivery`
    (`Eifel-Joe#53`). Beim Absetzen **CI 4 passing / 0 failing, MERGEABLE/CLEAN**.
  - **`JustChr#176`** — `fix(chain): a second dispatch joins the running cycle instead
    of replacing it` (`Eifel-Joe#62` neu, `Eifel-Joe#46` mitbetroffen).
  - **`JustChr#177`** — `refactor(time): name the two things a naive timestamp can mean`
    (`Eifel-Joe#22`, PR 1 von zwei).
  **CI aller drei am 28.09. nachgemessen: je 4 SUCCESS**, #176 und #177
  `MERGEABLE`/`CLEAN`, #175 `UNKNOWN` (GitHubs transienter Rechenzustand, vorher
  `CLEAN`). **Review-Stand aber noch von keinem** — beim Lesen dieses Eintrags zuerst
  nachsehen, nicht annehmen.
- **`Eifel-Joe#22` PR 1 gebaut und eingereicht.** Branch
  `fix/name-the-two-time-provenances`, Worktree `D:/Entwicklung/HASI/issue22-work/wt`,
  **6 Commits**, gepusht. Voll-Lauf **7 failed / 3384 passed / 9 skipped / 367 errors**,
  **Namens-Diff leer** (374 = 374), `+18` nach Definition. `black`/`ruff` clean.
  **Mutationsmatrix 11/11.** Referenz-Prüfungen: hinzugefügte Zeilen 0, Messages 0,
  je Commit genau 1.
  **Der WIP `fix/weather-buffer-aware-time` (`c9720a72`) wurde NICHT fortgesetzt** — er
  ist vom 21.09., JustChrs Schnitt-Antwort vom 23.09., und er macht den Flip (= PR 2).
  `as_stored_aware` erfüllt seine Bedingung nicht (kein Pflicht-Argument). Er bleibt als
  Ideengeber stehen; `_process_timezone()` ist das eine übernommene Stück.
- **Chain-PR 2 neu gebaut** (der alte Commit trug drei Tracker-Verweise im *Inhalt*,
  Historie deshalb neu). Branch `fix-a-second-dispatch-joins-the-running-cycle`,
  Worktree `issue2b-work/wt`, **1 Commit**. Voll-Lauf **3386 passed**, Namens-Diff leer,
  `+20` nach Definition, **Mutationsmatrix 12/12**.
  `JustChr#165` hatte unseren ersten Halbteil **byte-identisch** übernommen, der Rebase
  war deshalb ein Cherry-pick.
- **Regel P2 nachgezogen:** `Eifel-Joe#53` kommentiert + `upstream:gemeldet`;
  `Eifel-Joe#59` kommentiert (JustChrs Festlegung im Zitat) + `upstream:gemeldet`;
  **`Eifel-Joe#62` NEU angelegt** (weil `#2` geschlossen ist — Rest → neues Issue),
  5 Labels; `Eifel-Joe#46` kommentiert + `upstream:gemeldet`.
- **Regel P1 erledigt und remote verifiziert:** `archive/design-history` **`d1f5401e`**,
  0 voraus. Neu darin: `#53`-Plan + Live-Protokoll, `#22`-Spec-Revision 3 + Plan,
  und `reconstructed/2026-09-28-chain-second-dispatch-pr2.md`.
- **Live-Test `#53` bestanden**, beide Richtungen, auf Wegwerf-Build `v2026.09.27b3`.
  Details im Archiv-Protokoll, nicht hier doppeln.

### Verworfen
- **Den `#22`-WIP zu rebasen.** Falscher Schnitt (macht PR 2), 19 Commits hinter master,
  und die zwei clarejor-Merges haben `live_estimate.py` um +499/−34 umgeschrieben —
  genau die Datei, die der WIP um 60 Zeilen ändert.
- **Ein Pflicht-`now_provenance=` an den vier Eintrittspunkten.** **Gemessen:** `now=`
  steht **94×** in **9** Testdateien. Das wären ~94 Test-Änderungen in dem PR, dessen
  ganzer Punkt ist, dass er keine Zahl bewegt.
- **PR 1 etwas aware machen zu lassen.** „Accepts both kinds" heißt, ein aware Wert darf
  nicht mehr werfen — die naive Form bleibt. Aware würde genau dort werfen, wo der Spec
  222 verschluckte `TypeError` gemessen hat.
- **Einen Live-Test für `#22` PR 1 zu inszenieren.** Er ändert keine Zahl; der leere
  Namens-Diff ist der Beleg. Steht so im Plan, statt einen Test zu bauen, der nicht
  fehlschlagen kann.

### Fallen
- ⚠️ **Eine Mutationsmatrix, die nichts gesammelt hat, meldet „alles überlebt".** Die
  Chain-Matrix sagte zuerst `0 killed, 12 survived` — Ursache war
  `tests/test_rotation.py` in der Liste, die es nicht gibt; pytest bricht auf dem
  fehlenden Pfad ab, jeder Lauf `no tests ran in 0.01s`. **Als Verdikt gelesen wären das
  zwölf ungedeckte Zeilen gewesen.** Die Treiber im Scratchpad prüfen das jetzt
  (`BROKEN` statt `SURVIVED`) und die Liste wird einmal un-mutiert vorab gefahren.
  Memory `mutation-survivor-suspects-the-test` erweitert.
- ⚠️ **Ein Test, der den Helfer direkt prüft, belegt nicht die Aufrufstelle.** `#22`s
  T10 (Vorhersage-Zeilen mit der falschen Herkunft) überlebte, weil mein Test
  `coerce_stamp` direkt aufrief. Die drei Stellen sitzen hinter
  `if when.tzinfo is not None:`, das kein Fixture auslöst. Memory
  `verification-must-exercise-the-change`, hineingelaufen.
- ⚠️ **`uvx ruff check … | tail -1` verschluckt den Befund.** Task 2 ging mit
  `F401 imported but unused` durch. Jetzt: `| grep -c "All checks passed!"`.
- **Eine Commit-Message aus einer Memory-Formulierung abschreiben.** „One existing test
  is inverted" stand in der Chain-PR-2-Message — auf master gibt es keinen solchen Test.
  Wirklich passiert war ein **neu gebautes Fixture**, weil der alte Weg unerreichbar
  wurde. Vor dem Push geprüft und korrigiert.
- **`sed -i` unter MSYS zieht CRLF auf LF.** Die Patch-Helfer im Scratchpad
  (`patch.py`, `replace_block.py`) lesen Text-Modus und schreiben `newline="\r\n"`.
- **`git commit --amend` braucht einen sauberen Baum, bevor eine Matrix läuft** — der
  Treiber bricht sonst korrekt ab, aber erst nach dem ersten Mutanten.

### Nächste Schritte
1. **CI und Review der drei PRs lesen**, bevor etwas Neues beginnt — `#176` und `#177`
   sind ungeprüft. Bei Einwänden `superpowers:receiving-code-review`, und JustChrs
   Einwand **in seinen Worten** in das jeweilige Issue (Regel P2).
2. **`Eifel-Joe#22` PR 2** ist die Fortsetzung: Schreiber auf `dt_util.now()`, die
   Migration (`STORAGE_VERSION` 14 → 15), die Fixtures neu einsortiert. Erst **nach**
   `#177`s Merge, weil PR 2 dessen Vokabular nur noch benutzt. Die Release-Notes führen
   mit dem Clearness-Ratio-Strahlungsfehler (+23,5 % / −16 %), nicht mit dem
   Elapsed-Window-Drift — so von JustChr verlangt.
   ⚠️ **`tz_offset_h` reist als float, nicht als tzinfo** — aware Stempel beheben die
   Solarkorrektur NICHT. Steht als `NOT-TO-DO` an `calculation.py`.
3. **`Eifel-Joe#52`** (`exc_info=True` auf `_intraday_for_zone`) ist separat freigegeben
   und wartet als eigener Einzeiler. Der „erster Fehlschlag auf WARNING"-Teil ist
   `Eifel-Joe#56`, uns überlassen.
4. **HA-Test zurückstellen:** `Gardena1`s Feld „Durchflusssensor (optional)" zeigt noch
   auf `input_number.hasi_flow_probe` (alter Wert `sensor.wasser_3_flow`). **Nur im
   Panel, also Sache des Users.** Die Sonde bleibt absichtlich stehen.
5. **Triage:** `Eifel-Joe#57`, `#58`, `#61` (Schwere/Größe/`prod-scharf`).
6. **Aufräumen:** Hilfsmarken `issue21-*`, Worktree `issue21-work/base`,
   Branch `prerelease/v2026.09.27b3`. **Vorher die `*-work/`-Ordner ansehen** —
   `issue21-work/`, `issue53-work/`, `issue53b-work/`, `issue2-work/`, `issue2b-work/`,
   `issue22-work/` tragen Baselines, Voll-Läufe, `mutations.json` und PR-Texte.

### Empfohlene Skills
`superpowers:receiving-code-review`, sobald JustChr auf einen der drei PRs antwortet;
`superpowers:verification-before-completion` vor jedem „fertig"; `pr-workflow` für
weitere Pushes.

---

## 2026-09-27 (4) — Eifel-Joe#53 neu auf master gebaut, live belegt, als JustChr#175 eingereicht

### Stand (verifiziert)
- **`JustChr#175` IST OFFEN** — [PR](https://github.com/JustChr/HAsmartirrigation/pull/175),
  Titel `fix(distributor): a dry member run is not a delivery`, Head
  `Eifel-Joe:fix-a-dry-member-run-is-not-a-delivery`, Basis `master`. **CI beim Absetzen
  noch nicht gestartet** (0/0/0) — der PR-Monitor der App ist gebunden und meldet.
  ⚠️ Beim Lesen dieses Eintrags also **zuerst CI und Review prüfen**, nicht annehmen.
- **Historie NEU entstanden, nicht rebasiert.** Der alte Branch heißt jetzt
  `issue53-granular` (Tip `dc56b1fb`, Worktree `issue53-work/wt` folgte mit), sein
  Inhalt ist unangetastet. Neu: **9 Commits auf Basis `1c071cf0`**, Worktree
  `D:/Entwicklung/HASI/issue53b-work/wt`, Kopf **`6d4b9cc1`**, gepusht.
  Grund: 20 der 21 alten Commit-Messages trugen unsere Nummern, und zwei trugen sie
  im *Inhalt* — ein Reparatur-Commit hätte Prüfung 3 weiter gerissen.
- **Basis-Korrektur:** `upstream/master` war beim Start nicht `5ebffa76`, sondern
  **`1c071cf0`** (`build: release v2026.09.25`). Baseline darauf **374 nicht-grüne
  Namen**, `diff` gegen `issue21-work/baseline-fa863aa9.txt` **leer** — der
  Release-Commit bewegt keinen Test. Datei: `issue53b-work/baseline-1c071cf0.txt`.
- **Der `flow_metering.py`-Teil (+41 Zeilen) ist ganz entfallen**, master trägt den
  Accessor. Der Textkonflikt aus Spec §4.3 existiert nicht.
- **Voll-Lauf:** 7 failed / **3388** passed / 9 skipped / 367 errors, **Namens-Diff
  leer** (374 = 374). `+22` **nach Definition gezählt**, nicht aus der Differenz
  geschlossen. `black` 69 unverändert, `ruff` clean.
- **Mutationsmatrix: 17 Mutationen, 16 getötet, 1 dokumentierter Überlebender**
  (`M6`, das `<= 0` des Fenster-Guards — dort provabel unerreichbar als Negativ, der
  Vergleich trägt eine Ebene höher im Sweep, wo `M7` ihn tötet). Verdikte in
  `issue53b-work/mutations.json`, Treiber im Scratchpad (`mutate.py`).
- **Drei Referenz-Prüfungen bestanden**, mit `;` verkettet: Diff **0**,
  Commit-Messages **0**, je Commit **genau 1** = die `Author:`-Zeile. Zusatz-Scan nur
  über die *hinzugefügten* Zeilen auf `#NNN`, Branch-SHAs, Doku-Kürzel: nichts.
  Auch der PR-Body selbst geprüft: 0, einzige Nummer `#174` (JustChrs eigener).
- **Live-Test bestanden, beide Richtungen** — Protokoll
  `archive/design-history:docs/superpowers/reconstructed/2026-09-27-dry-distributor-member-live-on-master.md`.
  Build `v2026.09.27b3` (Branch `prerelease/v2026.09.27b3`, `6a313d7c`), HACS-Install,
  HA-Test-Neustart, `installed_version` **und** Config-Entry `loaded` geprüft.
  Zwei Läufe auf `Test2`, gleiche Zone/Sensor/Messwert/Fenster, **eine Variable**:
  Sonde spricht → `failed`/`flow_never_started`, alle vier Werte unverändert, Warnung
  einmal; Sonde stumm → `completed`, 3,0 L, Eimer −5,0 → −4,4, Gesamt → 1197,3.
- **Regel P1 erledigt und remote verifiziert:** `archive/design-history` **`ccc669f1`**,
  0 voraus. Darin der Phase-M-Plan mit allen Messergebnissen und das Live-Protokoll —
  und damit ist auch der vorher lokale `d1508e4a` draußen.
- **Regel P2 erledigt:** `Eifel-Joe#53` kommentiert
  ([Kommentar](https://github.com/Eifel-Joe/HAsmartirrigation/issues/53#issuecomment-5858890932)),
  Label **`upstream:gemeldet`** im selben Zug gesetzt. Issue bleibt **OFFEN** bis
  JustChrs Entscheidung zu `#175`.

### Verworfen
- **Das 4-Tupel als eigener kleiner PR davor** (User-Entscheidung, mit Korrektur der
  Prämisse): der Diff wächst um **keine** Datei — `_dist_read_flow` hat genau drei
  Referenzen im Paket, alle in `distributor.py`, und sein einziger Teststub liegt in
  `test_distributor_dispatch.py`, das die Guard-Tests schon anfassen. Allein wäre der
  PR verhaltensneutral und nur durch noch nicht eingereichte Arbeit zu rechtfertigen.
- **Das alte Live-Protokoll als Beleg weiterzuverwenden.** Es schrieb einen Lauf mit
  `sensor.wasser_3_flow` ab und begründete das mit „`metered_the_run()` ist true" —
  das galt für die **Zwei**-Bedingungs-Form. Masters dritte Bedingung lehnt genau
  diesen Sensor ab, weil er während eines Laufs nicht meldet. Das alte Protokoll
  bleibt gültig für die alte Form, nicht für die gelandete.
- **Die Sonde nach dem Test zu löschen.** Beim Schwester-Test wurde
  `input_number.hasi_flow_probe` gelöscht und musste heute neu gebaut werden.
  Sie bleibt jetzt stehen.

### Fallen
- ⚠️ **Das MCP-`ha_get_state` liefert `last_reported` FALSCH** — es gibt
  `last_changed` zurück (für die Sonde 20:12:38, HAs Template-Engine sagte 20:17:16).
  Bei *jeder* Entität ist `last_reported == last_changed`. **Jede Timing-Aussage muss
  per Template-Render** (`states.<entity>.last_reported`) gelesen werden, sonst ist sie
  kein Beleg. Hat mich hier eine falsche Zwischenbehauptung gekostet.
- **Ein gezielter Member-Lauf rückt zuerst den Ring vor.** `current_outlet` 3 → Ausgang
  2 auf einem 6er-Ring = 5 Skip-Pulse à 15 s, das Messfenster öffnete **150 s** nach
  dem Service-Aufruf. Mein erstes Treiber-Skript mit 90 s wäre vor dem Fenster
  verstummt und hätte den Zeugen ausgehungert — vor dem Lauf auf 270 s verlängert.
- **Das Verteiler-Feld heißt anders als das Zonen-Feld:** „Durchflusssensor
  (optional)" (`de.json:877`), nicht „Durchflussmesser-Sensor (optional)" (`:380`).
  Aus `de.json` gelesen, nicht aus der Memory übernommen.
- **`ha_get_integration(include_diagnostics=True)` gibt die Config-Entry-`options`
  immer mit aus** — inklusive `pw_api_key` im Klartext, auch bei engem
  `diagnostics_data_path`. Nicht vermeidbar, also: nie in Datei, Issue oder Commit.
- **Der Run-Log liegt auf der Zone** (`ZONE_RUN_LOG`, 50 Einträge), nicht in einem
  eigenen Store und nicht als Entity. Lesbar nur über
  `diagnostics_data_path=data.store.zones` mit `limit/offset` — **keine Listenindizes**
  im Pfad. `Test2` (id 3) steht auf **offset 3**, `Test1` (id 2) auf offset 2.
- **`sed -i` unter MSYS zieht CRLF-Dateien auf LF.** Das Repo hat
  `core.autocrlf=true`, git normalisiert beim Commit, aber der Baum wird inkonsistent.
  Patch-Helfer im Scratchpad (`patch.py`, `replace_block.py`) lesen Text-Modus und
  schreiben `newline="\r\n"` zurück.
- **`grep -c` mit null Treffern liefert Exit 1** und bricht eine `&&`-Kette ab.
  Prüfungen mit `;` verketten.

### Nächste Schritte
1. **`JustChr#175`: CI und Review lesen**, bevor irgendetwas anderes beginnt. Bei
   Einwänden `superpowers:receiving-code-review`, und JustChrs Einwand **in seinen
   Worten** als Kommentar in `Eifel-Joe#53` nachtragen (Regel P2).
2. **HA-Test zurückstellen:** `Gardena1`s Feld „Durchflusssensor (optional)" zeigt noch
   auf `input_number.hasi_flow_probe`, alter Wert `sensor.wasser_3_flow`. **Nur im
   Panel änderbar, also Sache des Users.** `Test2` steht jetzt auf Eimer −4,4 und
   1197,3 L, `last_irrigation` 20:33:09. Wegwerf-Release `v2026.09.27b3` und der
   Branch `prerelease/v2026.09.27b3` können nach Belieben weg.
3. **`JustChr#159` ist absichtlich offen** und `Eifel-Joe#59` trägt jetzt JustChrs
   Festlegung im Zitat plus `upstream:gemeldet`
   ([Kommentar](https://github.com/Eifel-Joe/HAsmartirrigation/issues/59#issuecomment-5859138730)).
   Aufteilung: Defekt-Hälfte = `#172`, gemergt, `Eifel-Joe#21` zu. Design-Hälfte
   (greift die Gewichtung auf dem Live-Estimate-Pfad überhaupt?) = `Eifel-Joe#59`,
   eigener PR gewünscht, **Produktentscheidung fehlt**. `upstream:freigegeben` bewusst
   NICHT gesetzt — seine Bau-Zusage vom 21.09. galt vor der Aufteilung.
4. **`JustChr#160` / `Eifel-Joe#22` (`upstream:freigegeben`): angefangen, unfertig.**
   Branch `fix/weather-buffer-aware-time` im HAUPTBAUM, 2 Commits, Basis `965a4f9d`,
   **19 hinter master**. Fertig ist `helpers.as_stored_aware` + `_process_timezone()`
   (eigene Funktion, weil `time.tzset()` auf Windows fehlt), angewandt in
   `calculation.py`, `live_estimate.py` (3×), `weather_aggregate.py`, plus
   `tests/test_stored_stamp_timezone.py`. **Unaufgelöst laut eigener Commit-Message:**
   die zweite naive Herkunft (Wetter-Client- und Vorhersage-Zeilen sind **site**-lokal,
   Store-Stempel **prozess**-lokal — entgegengesetzt, ein Helfer kann nicht beide
   bedienen, siehe Memory `enumerate-provenances-before-reformat`).
   ⚠️ **Und eine Stelle, die der Helfer-Docstring als ersetzt BESCHREIBT, ist es nicht:**
   `sensor._to_aware_datetime` (`sensor.py:603/620`) macht weiter
   `replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)`, gerufen an `:822`, `:887`, `:1102`.
   Der Docstring sagt „It **was** in sensor._to_aware_datetime", der Code widerspricht.
   Vor Weiterarbeit: **Rebase auf `1c071cf0`** (`#172` hat `calculation.py` angefasst,
   eine der geänderten Dateien) und **neue Baseline** — die alte gilt für `965a4f9d`.
5. **Triage fehlt weiter:** `Eifel-Joe#57`, `#58` (Schwere/Größe/`prod-scharf`) und
   `#61` (`schwere:`).
6. **`Eifel-Joe#61`** ist die eigene Verifikationslücke (Vorhersage-Gewichtung nie
   gegen einen antwortenden Wetter-Client gelaufen) — braucht Open-Meteo auf HA-Test,
   eine Zone mit und eine ohne Zeitplan, Berechnung aus einem Dispatch unter
   `autocalcmode: before_run`.
7. **`Eifel-Joe#59`** braucht eine Produktentscheidung, `#60` ist `schwere:niedrig`.
8. **Aufräumen, jetzt gefahrlos:** Hilfsmarken `issue21-granular`,
   `issue21-prereshape`, `issue21-resolver-only`, Worktree `issue21-work/base`.
   **Vorher `issue21-work/` ansehen** — Baselines und Voll-Läufe liegen dort, nur die
   Proben sind im Archiv. Neu dazu: `issue53-work/` (dort liegen die alten Baselines
   und PR-Texte) und `issue53b-work/` (Baseline `1c071cf0`, beide Voll-Läufe,
   `mutations.json`, PR- und Issue-Texte) — **nicht blind löschen.**

### Empfohlene Skills
`superpowers:receiving-code-review`, sobald JustChr auf `#175` antwortet;
`superpowers:verification-before-completion` vor jedem „fertig"; `pr-workflow` für
weitere Pushes.

---

## 2026-09-27 (3) — JustChr#174 UND JustChr#172 gemergt; P2 und P1 nachgezogen; Eifel-Joe#53 entblockt und teurer

### Stand (verifiziert)
- **`Eifel-Joe#53` ist vertagt, bewusst.** Drei Wege standen zur Wahl (auf `#174`s Branch
  stapeln / auf master mit mitgebrachtem `flow_metering` / warten). **User-Entscheidung:
  warten, bis `JustChr#174` gemergt ist**, dann erbt `#53` die Zeugen-Form aus master und
  der `flow_metering.py`-Teil entfällt ganz. Nichts an `#53` angefasst — Branch
  `fix-a-dry-member-run-is-not-a-delivery`, Worktree `issue53-work/wt`, Kopf `dc56b1fb`,
  Basis weiter das veraltete `418ab8a0`.
  **Neu gemessen und für `#53` relevant:** `#174` trägt die zwei `distributor.py`-`at=`-
  Umstellungen (Z. 714/737) **schon**; das ist nicht mehr `#53`s Arbeit.
- **✅ `JustChr#172` IST GEMERGT** (27.09. 16:02 UTC, gesquasht zu **`5ebffa76`**, jetzt
  master). `git diff 341fa1e7 5ebffa76` ist **leer** — byte-identisch übernommen. Er mergte
  **ohne zweite Review**, `reviewDecision` steht deshalb weiter auf `CHANGES_REQUESTED` an
  einem gemergten PR; das ist sein Zustand, kein Formfehler von uns.
  CI war 4 passing / 0 failing. [Antwort](https://github.com/JustChr/HAsmartirrigation/pull/172#issuecomment-5857410010).
- **Beide Stränge dieser Sitzung sind upstream:** `JustChr#174` (`d1f3c292`) und
  `JustChr#172` (`5ebffa76`), beide byte-identisch, beide geprüft statt angenommen.
- **Regel P2 vollständig nachgezogen.** `Eifel-Joe#4` kommentiert + **geschlossen**
  (Upstream-Bezug gemergt), `Eifel-Joe#21` kommentiert + **geschlossen**, `Eifel-Joe#53`
  kommentiert (entblockt + ausgehungerter Zeuge). Tracking-Issue **`Eifel-Joe#42`**
  aktualisiert: Einträge 5, 5a und 23 umgeschrieben, 14a/39b/39c ergänzt, beide Sprachen
  gespiegelt. Labels geprüft und bewusst **nicht** verändert — ein Label für „gemergt"
  existiert nicht, und ich erfinde keines.
- **Drei neue Issues für die Reste von `Eifel-Joe#21`** (Regel P2: Rest → neues Issue, kein
  wiedereröffnetes): **`Eifel-Joe#59`** Live-Pfad (`typ:produktentscheidung`),
  **`Eifel-Joe#60`** End-Ankerung (`schwere:niedrig`, `typ:fehler`), **`Eifel-Joe#61`**
  Verifikationslücke (`prod-scharf`, **kein `typ:`** — keiner der vier paßt, das ist eine
  Verifikationsaufgabe). `JustChr#159` bleibt oben offen, weil der PR nur die Defekt-Hälfte
  schloss. ⚠️ **`#61` hat keine `schwere:`** — ich hatte keine vorgeschlagen, Triage offen.
- **Regel P1 erledigt und remote verifiziert:** `archive/design-history` `5459399a`. Darin
  Spec §9–§9.12, Plan Phase R (52 Checkboxen), `#53`-Spec §10/§10.1, der Sitzungsstand —
  **und neu die zwei Proben selbst**, unter `docs/superpowers/probes/`. Abweichung von der
  Konvention, mit Absicht: bisher verweisen Specs nur per absolutem Scratch-Pfad auf ihre
  Proben, was Memory `scratch-dirs-hold-irreproducible-evidence` genau als Falle benennt
  (`pr174-work/probe_174_guard.py` und `mutate.py` sind so schon Verweise ins Leere, sobald
  aufgeräumt wird). Die archivierten Proben nehmen den **Checkout als Argument** und wurden
  in dieser Form gegen `issue21-work/base` laufen gelassen — sie reproduzieren die Tabelle.
- **`JustChr#174` IST GEMERGT** (27.09. 14:17 UTC, gesquasht zu `d1f3c292`; master jetzt
  **`fa863aa9`** + Release v2026.09.24). `git diff 3e372042 d1f3c292` ist **leer** — JustChr
  hat nichts geändert. Die Zeugen-Form auf master ist wörtlich unsere.
- **`JustChr#172` Phase R ist GEPUSHT, PR-Body aktualisiert, Review beantwortet.** Branch
  `fix-forecast-weighting-from-run-start`, Worktree `D:/Entwicklung/HASI/issue21-work/pr`,
  Kopf **`341fa1e7`**, Basis **`fa863aa9`**, **0 hinter upstream**. Drei Commits.
  **CI 4 passing / 0 failing**, `MERGEABLE`/`CLEAN`; `reviewDecision` bleibt
  `CHANGES_REQUESTED`, bis JustChr neu reviewt.
  [Kommentar](https://github.com/JustChr/HAsmartirrigation/pull/172#issuecomment-5857410010).
- **Acht Mutationen, alle auf `fa863aa9` gemessen, alle getötet** (je `git checkout --`
  zurück, Baum vorher sauber): vier neue für Anker und Fallback, vier alte **neu gefahren
  statt übernommen** — zwei Zeilen der alten Tabelle mutierten Code, der sich bewegt hat,
  darunter die Abstinenz, die jetzt ein Fallback ist.
  ⚠️ **Regelverstoß, offengelegt:** der neue PR-Body ging raus, bevor der User die neue
  Mutations-Tabelle gesehen hatte — seine Freigabe lag VOR dem Fund. Text-Freigabe gilt
  auch für Korrekturen. Der Kommentar wurde daraufhin zurückgehalten und erst nach
  erneuter Freigabe gesendet.
  - **Voll-Lauf auf `fa863aa9`: 7 failed / 3366 passed / 9 skipped / 367 errors.
    Namens-Diff gegen die NEUE Baseline LEER** (374 = 374). Dateien:
    `issue21-work/{baseline-fa863aa9,branch-names-fa863aa9,base-run,branch-run}.txt`.
    Baseline selbst: 7 / **3344** / 9 / 367. `+22` = die 22 hinzugefügten Tests, **nach
    Definition gezählt** (12+6+3+1), nicht aus der Differenz geschlossen.
    Lint: `black` 69 Dateien unverändert, `ruff` clean.
  - **Nebenbefund:** `c5330c7f` und `fa863aa9` tragen dieselben 374 nicht-grünen Namen.
    `#174` brachte 22 grüne Tests und keinen neuen Fehler — nichts hier ist geerbter Schaden.
    ⛔ `pr174-work/baseline-names.txt` gilt nur noch für `c5330c7f`; maßgeblich ist
    `issue21-work/baseline-fa863aa9.txt`.
  - **Umform-Diff gegen `issue21-prereshape` LEER** — die drei Commits sind inhaltsgleich
    mit der granularen Historie.
  - **Drei Referenz-Prüfungen bestanden**, inkl. der pro-Commit-Inhaltsprüfung: genau
    **1 Treffer je Commit, und das ist die Author-Zeile**.
- **Was JustChrs Review verlangte, und was daraus wurde** (voller Argumentationsgang:
  Spec §9, **nicht hier doppeln**):
  - **Befund 1 (Uhr nicht gepinnt) bestätigt, reproduziert:** 3 Tests rot am 27.09.,
    Ist-Werte 490/269/365 gegen 360/0/300 — alle **über** dem Soll, also wässert es
    *mehr*. Gefixt durch `NOW` als einzige Literale, alles andere davon abgeleitet.
    **Der Pin ist als tragend belegt:** Auswertung 3 Tage hinter den Lauf geschoben -->
    4 Tests fallen, alle auf `600` (= Abstinenz). Die zwei Abstinenz-Tests bleiben dabei
    grün — genau die stille-Grün-Klasse, weshalb die Arithmetik-Tests die Unterscheider
    sind.
  - **Befund 2 (`before_run`-Anker) bestätigt und gemessen**, Probe
    `issue21-work/probe_before_run_anchor.py`: **+1 Tag** in beiden Mechanismen (A:
    fired-occurrence-Guard, B: strikt-nach-jetzt). Gefixt durch einen keyword-only
    `run_start` von `_execute_schedule` bis `calculate_module`.
  - **🔴 Sein Vorschlag (ii) ist nachweislich unzureichend** („Resolver gibt eine
    innerhalb `SAME_OCCURRENCE` gefeuerte Gelegenheit zurück"): bei einem einfachen
    Startzeit-Plan vermerkt **niemand** eine gefeuerte Gelegenheit, es gibt also nichts
    zurückzugeben — Mechanismus B allein, Zeile B2 der Probe. Nur (i) trägt beide.
    **Muss in die Antwort, mit der Probe-Zeile als Beleg.**
  - **🔴 Der Defekt ist eine Stelle breiter als seine Review sagt.**
    `_decide_and_run_start_pinned` (`scheduler.py:1820`) committet laut **eigenem
    Docstring** „at the moment the schedule actually fires", nicht am Entscheidungspunkt;
    er hatte sie unter die unbedenklichen `pre_committed=True`-Pfade sortiert. Gefunden
    durch den Schwester-Pfad-Check. Die dritte Stelle (`_decide_and_arm(commit=True)`,
    `:1969`) ist **belegt unangetastet** — echter Entscheidungspunkt.
  - **Frage 3 (Zonen ohne Zeitplan): Fallback angenommen** (User, 27.09.). Beleg war
    nicht sein Einwand, sondern die Schwesterhälfte: `skip_conditions.py:235` ankert
    schon bei `now`, wenn kein Lauf-Start genannt ist. **Grenze mitgeliefert und
    getestet:** ohne Stundenreihe bleibt `first_24h_covered` falsch, der Fallback erreicht
    also nur Zonen, deren Client eine Stundenreihe liefert.
  - **Referenzen:** `Eifel-Joe#21`/`#22` --> `#159`/`#160` (seine eigenen Issues, von uns
    dort gemeldet — Titel deckungsgleich), plus Branch-SHA `10bb8077` aus einem Docstring
    raus.
- **Design-Historie:** Spec §9 und Plan Phase R (Tasks 10–17, 52 Checkboxen abgehakt)
  liegen in `issue21-work/pr/docs/superpowers/` — **noch NICHT archiviert**, Regel P1
  offen.

### Verworfen
- **Die Referenzen mit einem Commit obendrauf zu reparieren.** Sie steckten als
  *hinzugefügte* Zeilen im Inhalt von zwei Commits, `git show <sha> | grep` hätte weiter
  getroffen. Historie neu entstehen lassen war nötig — dieselbe Lehre wie bei `#174`.
- **Den Lauf-Start als Dict-Schlüssel durch `ATTR_CALCULATE` zu führen.** Dessen Schlüssel
  sind als Websocket-Felder schema-validiert (`websockets.py:295-296`); er wäre Teil einer
  externen API geworden. Keyword-only *neben* dem Dict ist für alle acht Aufrufer unsichtbar.
- **Eine transiente Coordinator-Eigenschaft für die Dauer des Commits.** Der Commit
  awaitet durchgehend, eine dazwischenliegende Fixzeit-Berechnung hätte den fremden Anker
  gelesen.
- **`run_start` verpflichtend zu machen**, um Vergessen unmöglich zu machen: ein
  Produktiv-Aufrufer, aber zwölf Test-Aufrufstellen in fünf Dateien. `_execute_schedule`s
  `now` ist schon Pflicht, der Produktivpfad kann es also nicht vergessen.
- **`freezegun`** für den Uhr-Pin: ersetzt die ganze Prozess-Uhr. Nur `dt_util.utcnow`
  umbiegen ist die einzige Uhr-Lesung auf dem Pfad.

### Fallen
- **`grep -E '^(FAILED|ERROR)'` ist zu weit für den Namens-Diff.** `batch.py`s eigene
  Log-Zeilen beginnen mit `ERROR` und zogen sechs Zeilen mit; ein korrekter Lauf sah wie
  neun neue Fehler aus. Die Baseline enthält **nur** `^(FAILED|ERROR) tests/` (geprüft,
  null Ausnahmen) — der Filter muss darauf ankern. Steht jetzt im Plan.
- **`_perform_scheduled_irrigation` hat kein `now`.** Nur `_execute_schedule` trägt es und
  ruft ohne es nach unten; `run_start=now` an der Commit-Stelle wäre ein `NameError`
  gewesen. Beim Plan-Schreiben gefunden, nicht beim Bauen.
- **`_entries_behind` verwirft eine Tagesspalte, die GENAU am Ende der Stundenreihe
  beginnt** (eigener Docstring). Ein Fixture, das Stundenreihe und Tagesspalten aneinander
  stößt, lässt den Block unbedeckt und die Gewichtung enthalten — es sieht wie ein
  Design-Fehler aus. Die Stundenreihe muss den ersten Block **ganz** decken (24 Stempel).
- **`git diff c5330c7f..HEAD` sieht uncommittete Referenz-Fixes nicht.** Für die
  Zwischenprüfung `git diff c5330c7f` ohne `..HEAD` nehmen.
- **`grep -c` mit null Treffern liefert Exit 1** und bricht eine `&&`-Kette ab. Prüfungen
  mit `;` verketten, nicht mit `&&`.
- **Eine Plan-Erwartung war falsch:** der Test, der die *Grenze* des Fallbacks pinnt,
  konnte nicht vorab grün sein — der alte Code erreicht die `first_24h_covered`-Prüfung bei
  `run_start is None` nie. Der Test war richtig, die Erwartung nicht.

### Nächste Schritte
1. **`Eifel-Joe#53`** ist die nächste Aufgabe und **teurer als sein Design sagt**. Auf master
   (`5ebffa76`) rebasen, `flow_metering.py`-Teil streichen — **und `_dist_read_flow` auf ein
   4-Tupel ziehen**, sonst ist `metered_the_run()` dort konstant `False` und der Fix ein
   No-Op (gemessen, Probe im Archiv). Jeder Trocken-Test braucht fortschreitende Reports.
   Basis `418ab8a0` veraltet, 20 Commit-Messages tragen unsere Nummern → Historie neu.
   Baseline auf `5ebffa76` **neu messen**; `issue21-work/baseline-fa863aa9.txt` gilt nur für
   `fa863aa9`.
2. **Triage:** `Eifel-Joe#57`, `#58` (Schwere/Größe/`prod-scharf` fehlen) und `#61`
   (`schwere:` fehlt).
3. **`Eifel-Joe#61` schließen heißt Live-Test** der Gewichtung — braucht einen antwortenden
   Wetter-Client auf HA-Test (**Open-Meteo ohne Schlüssel**), eine Zone **mit** und eine
   **ohne** Zeitplan, und eine Berechnung aus einem Dispatch heraus unter `before_run`.
   Das ist der Punkt, um den JustChrs Review ging, und er ist bisher nur in einer Probe
   gemessen.
4. **`Eifel-Joe#59`** braucht eine Produktentscheidung, keinen Fix (drei Formen im Body,
   Variante 3 widerspricht einer schon getroffenen Entscheidung).
5. **Aufräumen, jetzt gefahrlos:** Hilfsmarken `issue21-granular`, `issue21-prereshape`,
   `issue21-resolver-only` und der Worktree `issue21-work/base`. **Vorher** `issue21-work/`
   ansehen — dort liegen die Baselines, die Voll-Läufe und die PR-Texte; die Proben sind
   inzwischen im Archiv, die Baselines nicht.
6. **Produktiv-Rebuild** zieht jetzt beide Fixes mit. `Eifel-Joe#61` sagt, was daran
   unbeobachtet ist — das vor dem Release lesen, nicht danach.

### Live-Test — bewusst NICHT gemacht, mit Grund
Die Gewichtung läuft nur, wenn der Wetterdienst antwortet, und **PirateWeather antwortet
auf HA-Test mit 429**. `calculate_zone` liefert dort nichts, und `run_zone duration:` —
der wetterunabhängige Weg, mit dem `#174` live belegt wurde — **rechnet nicht neu** und
kann diesen Pfad gar nicht auslösen. Das `#174`-Rezept ist also nicht übertragbar.
Verifiziert wurde stattdessen an: leerem Namens-Diff, vier Tests durch das **echte**
`_advance_past_fired_occurrence`/`_next_governing_time`, und dem als tragend belegten
Uhr-Pin. **Wenn ein Live-Lauf gewünscht ist, braucht er einen antwortenden Client**
(Open-Meteo kommt ohne Schlüssel) — eigene Aufgabe, eigene Entscheidung.
HA-Test läuft unverändert `v2026.09.27b2`, nichts angefasst. HA-Prod nicht berührt.

### Empfohlene Skills
`superpowers:verification-before-completion` vor jedem „fertig"; `pr-workflow` für Push
und PR-Text; `superpowers:receiving-code-review` erneut, wenn JustChr auf `#172` oder
`#174` antwortet.

---

## 2026-09-27 (2) — JustChr#174 nachgebessert, live belegt, gepusht; zwei Geschwister-Pfade als Issues

### Stand (verifiziert)
- **`JustChr#174` ist nachgebessert, gepusht und kommentiert.** Branch
  `fix-a-run-that-delivered-nothing-is-not-a-success`, Worktree
  `D:/Entwicklung/HASI/pr34-work/pr2`, Kopf **`3e372042`**, Basis `c5330c7f`,
  **0 hinter upstream**. PR-Status: `DIRTY` --> **`MERGEABLE` / `CLEAN`**,
  **CI 4 passing / 0 failing**. `reviewDecision` steht weiter auf
  `CHANGES_REQUESTED`, bis JustChr neu reviewt.
  [Kommentar](https://github.com/JustChr/HAsmartirrigation/pull/174#issuecomment-5855700205)
  — **mit der Entschuldigung an erster Stelle**.
- **Die Zeugen-Form, die gelandet ist:**
  `metered_the_run() == _saw_report_after_open and _priced and not _declined`.
  `_read_flow_sample` trägt `State.last_reported`, `FlowMeter.sample` nimmt es im
  vierten Positions-Slot, `at` ist hinter das `*` gewandert. `saw_reading_after_open()`
  ist ersatzlos weg, `saw_reset()` aus dem Guard raus (beweisbar redundant).
  Volle Begründung: Spec §11 (siehe unten), **nicht hier doppeln**.
- **Der Umfang wurde erweitert, und zwar auf Beleg:** JustChrs Fall war einer von
  vier. Die drei aus Spec §4 des `#53`-Designs habe ich gegen `#174`s *eingereichten*
  Guard nachgemessen — alle drei wurden als `failed` abgeschrieben, obwohl Wasser floss.
  Probe: `D:\Entwicklung\HASI\pr174-work\probe_174_guard.py`, Gegenprobe auf dem
  neuen Stand `probe_new_guard.py` (7 von 7 richtig).
- **Voll-Lauf:** Baseline **neu** auf `c5330c7f` in eigenem Worktree
  (`pr174-work/base`): 7 failed / **3322** passed / 9 skipped / 367 errors = 374 Namen.
  Branch: 7 failed / **3344** passed / 9 skipped / 367 errors — **Namens-Diff LEER**.
  Dateien: `pr174-work/{baseline,after}-names*.txt`. Lint grün.
- **Mutationsmatrix 13/13 getötet** (`pr174-work/mutate.py`, Ergebnis `mutate-run2.txt`).
  Erster Durchlauf hatte **fünf Überlebende** — jeder war ein zu schwacher Test, kein
  redundanter Term. Details in Spec §11.10.
- **🧪 Live belegt auf HA-Test, drei Läufe, eine Variable.** Wegwerf-Build
  `v2026.09.27b2` (`2a1ee093`), Zone `Grace Test`, Flussquelle
  `input_number.hasi_flow_probe` konstant `0.0`, je `run_zone duration: 1`:
  stumm --> `completed` + 4,0 L zeitbasiert · meldend --> **`failed` /
  `flow_never_started`**, Eimer/Verbrauch/`last_irrigation` unberührt · stumm -->
  `completed` und **der Fehler wird geklärt**.
  Volles Protokoll: `archive/design-history`,
  `docs/superpowers/reconstructed/2026-09-27-dry-run-witness-live.md`.
- **Der Angelpunkt wurde vorher gemessen, nicht angenommen:** `input_number.set_value`
  mit **unverändertem** Wert rückte `last_reported` um 244 s vor, `last_changed` stand.
  Und generell auf HA-Test: **42 von 348 Sensoren** haben `last_reported` strikt nach
  `last_changed`.
- **Regel P2 nachgezogen:** `Eifel-Joe#4` kommentiert (JustChrs Einwand in seinen Worten
  + Live-Tabelle + Querverweis), `#53` kommentiert (erbt die Form, Live-Test muss
  wiederholt werden). **Neu: `#57`** (observed watering, umgekehrter Vertrag) und
  **`#58`** (klassischer Runner, Umleitung im Sampling-Loop) — beide aus dem
  Schwester-Pfad-Check, beide `typ:fehler`. 48 Issues offen.
  **Schwere/Größe/`prod-scharf` auf `#57`/`#58` absichtlich NICHT gesetzt** — das ist
  Triage und gehört dir.
- **Branch-Form:** in die **zwei** Commits umgeformt, die JustChr erwartet, weil die drei
  Falschreferenzen auch im *Inhalt* des alten Fix-Commits steckten. Beweis: **leerer
  `git diff`** gegen die granulare Historie, die als **`pr174-granular`** (`a1dfabc7`)
  lokal erhalten ist. Skript: `pr174-work/reshape.sh`.
- **Drei Referenz-Checks liefen vor dem Push, nicht zwei:** Diff, Commit-Messages **und
  pro-Commit-Inhalt**. Alle leer (einziger Treffer: die eigene Author-Zeile).

### Verworfen
- **Nur JustChrs Punkt zu fixen.** Die drei weiteren Eingaben sind gemessen; `#174` wäre
  mit drei bekannten Falsch-Abschreibungen rausgegangen.
- **`metered_the_run()` allein als Zeuge** (die `#53`-Form). Ein abgestandener Sensor bei
  `0` besteht `_priced` — eine Rate von 0 bepreist jedes Intervall mit 0 L.
- **`last_reported` allein als Zeuge.** Die drei §4-Eingaben melden frisch, wann immer sie
  live sind; nur `_declined` lehnt sie ab.
- **Template-Sensor als Live-Flussquelle.** Ein zustandsbasierter Template-Sensor rendert
  bei unverändertem Wert möglicherweise nicht neu — darauf durfte der Beweis nicht stehen.
  `input_number` geht durch `async_write_ha_state` und damit immer.

### Fallen
- **Der Voll-Lauf mit Namens-Diff ist nicht ersetzbar.** Nach Task 2 waren
  `test_flow_meter`, `test_self_closing`, `test_observed_watering`, `test_metered_run`
  und alle Verteiler-Dateien grün — und `tests/test_valve_verification.py` rot, eine
  Datei, die ich nie einzeln gefahren hatte. Ursache: ein `SimpleNamespace`-Double ohne
  `last_reported`.
- **Eine Mutation, die nichts tötet, ist zuerst ein Verdacht gegen den Test.** Fünf
  Überlebende, fünf zu schwache Tests. Der schärfste: der Guard gegen unsortierbare
  Report-Zeiten war mit einem Fixture gepinnt, dessen **erster** Report schon `None` war
  — die Basislinie wurde nie ein `datetime`, die geschützte Vergleichszeile nie erreicht.
  Der Test hätte jede Guard-Variante bestätigt.
- **`git add dist/` scheitert still.** `dist/` ist als *Verzeichnis* gitignored, obwohl
  die Dateien getrackt sind; `git check-ignore` auf die *Dateien* meldet nichts. Ohne
  `-f` bricht das `git add` ab, das `&&` verschluckt den Commit, und `git log` sieht
  unverändert aus. Und: es sind **4** Bundles, die Projekt-`CLAUDE.md` sagt 3.
- **Der Feldname im Panel heißt „Durchflussmesser-Sensor (optional)"**, nicht
  „Flusssensor" — ich hatte ihn erfunden und der User fand ihn nicht. Beschriftungen
  aus `frontend/localize/languages/de.json` holen, nicht aus dem Key raten.
- **Der Aufräum-Check hat korrekt verweigert** und war trotzdem irreführend: „the matrix
  left the tree dirty" — der Dreck waren meine eigenen uncommitteten Tests, nicht ein
  Mutant. Die Matrix-Ziele waren sauber.
- **HTTP 200 nach einem HA-Neustart heißt nichts.** Der Port antwortete nach 5 s; der
  belastbare Beleg ist `update.smart_irrigation_update` mit
  `installed_version = v2026.09.27b2` plus Config-Entry `loaded`.

### Stand auf HA-Test (aufräumen oder bewusst so lassen)
- Läuft **`v2026.09.27b2`** = upstream `c5330c7f` + die zwei `#174`-Commits.
  **Keine Eigenentwicklungen** des Forks in diesem Build.
- **Dessen Release und Tag sind gelöscht**, HACS kann die Version also nicht neu ziehen
  oder prüfen. Die Dateien sind intakt. Zurück auf einen HACS-bekannten Build:
  `v2026.09.27b1` (upstream ohne den Fix) oder `v2026.09.22b1` (letzter mit der
  Ventil-Sicherheit). Der Build selbst bleibt reproduzierbar: **lokaler** Branch
  `prerelease/v2026.09.27b2` (`2a1ee093`) im Worktree `pr174-work/prerel`.
- **Aufgeräumt:** `Grace Test`s Feld „Durchflussmesser-Sensor (optional)" ist wieder
  **leer** (war vor dem Test auch leer), `input_number.hasi_flow_probe` ist **gelöscht**.
  Nachgeprüft: `problem=off`, `watering_now=off`, keine Zone bewässert.
- `Grace Test`s Eimer steht nach drei Testläufen auf **−2,5317** (vorher −3,3317),
  `Wasserverbrauch` auf **8,0 L** (vorher 0,0), Fehler-Sensor `off`. Zwei der drei
  Läufe haben je 4 L gutgeschrieben.
- `Gardena1` trägt weiter `flow_sensor: sensor.wasser_3_flow` (der stumme Sensor).
- `Test2`s Eimer steht weiter von Hand auf −5.
- PirateWeather antwortet auf dieser Instanz mit **429** — `calculate_zone` liefert
  nichts, `run_zone duration:` ist der wetterunabhängige Weg.

### Nächste Schritte
1. **Auf JustChrs Re-Review von `#174` warten.** Kommt ein Einwand: als Kommentar in
   `Eifel-Joe#4`, in seinen Worten.
2. **`Eifel-Joe#53` auf die gelandete Form ziehen** — `metered_the_run()` erbt
   `_saw_report_after_open`, der `flow_metering.py`-Teil des Branches entfällt, die zwei
   `distributor.py`-Aufrufe brauchen `at=`. Danach Live-Test **mit meldendem Sensor**
   (`input_number`-Rezept steht im Protokoll). Branch
   `fix-a-dry-member-run-is-not-a-delivery`, Worktree `issue53-work/wt`, Kopf `dc56b1fb`,
   Basis `418ab8a0` — **Basis ist veraltet, neu rebasen und neu baselinen.**
   ⛔ Dessen 20 Commit-Messages tragen weiter `Eifel-Joe#53`/`#4`.
3. **`JustChr#172`** — Uhr in den Tests pinnen, `before_run`-Anker, seine Frage zu Zonen
   ohne Zeitplan.
4. **PR 2 / Task 11 (`Eifel-Joe#45`)** rebasen; vorher prüfen, ob `c5330c7f` den Defekt
   noch trägt.
5. **`Eifel-Joe#22` PR 1** ist entblockt.
6. Aufräumen, wenn `#174` durch ist: Worktrees `pr34-work/pr1`, `prerelease-work/wt`,
   `issue53-work/base`, `pr174-work/base`, die Branches `prerelease/v2026.09.22b1` und
   `prerelease/v2026.09.27b1` samt Release. Vorher die kleinen Ordner ansehen
   (Memory `scratch-dirs-hold-irreproducible-evidence`) — in `pr174-work` liegen die
   beiden Proben, die Matrix und die Baselines.

### Empfohlene Skills
`superpowers:receiving-code-review` für JustChrs Re-Review, `pr-workflow` für `#53`/`#172`,
`superpowers:verification-before-completion` vor jedem „fertig" — diese Sitzung hat einen
Regress in einer Datei gefunden, die kein Teil-Lauf berührte, und fünf Tests, die eine
Mutation überleben ließen.

---

## 2026-09-27 — Eifel-Joe#53 gebaut und live gefahren, aber von JustChrs Review gestoppt; fünf PRs gemergt; P2 nachgezogen

### Stand (verifiziert)
- **`Eifel-Joe#53` ist GEBAUT, NICHT eingereicht, und nicht fertig.** Branch
  `fix-a-dry-member-run-is-not-a-delivery`, Worktree `D:/Entwicklung/HASI/issue53-work/wt`,
  Kopf **`dc56b1fb`**, Basis `418ab8a0` (inzwischen 5 Commits hinter upstream).
  - Voll-Suite **7 failed / 3274 passed / 9 skipped / 349 errors**, Basis war 3254 → **+20**.
    Die 356 nicht-grünen Namen sind `diff`-IDENTISCH zur Baseline auf demselben
    Basis-Commit (`issue53-work/baseline-names.txt`). Lint grün.
  - **14 Mutationen, 13 getötet**, M3a überlebt konstruktionsbedingt. Treiber
    `issue53-work/mutate3.py` — er nimmt jede Mutation per `git checkout --` zurück und
    **bricht ab**, wenn der Baum vorher nicht sauber ist (hat einmal korrekt verweigert).
  - Diff: `distributor.py +169`, `flow_metering.py +41`, 4 Testdateien. `self_closing.py`,
    `run_chain.py`, `live_estimate.py`, `calculation.py`, `irrigation.py` unberührt.
- **🔴 Der Fix ist so nicht richtig, und der Befund kommt von JustChr an `JustChr#174`:**
  ein erneut gelesener **unveränderter** State setzt den Zeugen ebenfalls. Ein Sensor, der
  seltener meldet als der Lauf dauert (cloud-gepollt, Zähler der alle paar Minuten meldet,
  Zähler der erst nach dem Schließen meldet), ist damit von einem trockenen nicht zu
  unterscheiden — und sein Lauf wird als `failed` abgeschrieben, die Gutschrift
  zurückgedreht. Sein Vorschlag: **`State.last_reported`**, nur ein Bericht *nach* dem
  Ventil-Öffnen ist Evidenz (ab HA 2025.5 verfügbar, unser Boden).
  Gilt für `#174` **und** `#53` gleichermaßen.
- **🧪 Live-Test auf HA-Test: Mechanik belegt, Richtigkeit NICHT.** Pre-Release
  [`v2026.09.27b1`](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.09.27b1)
  (Commit `560fe52e`, Branch `prerelease/v2026.09.27b1`), per HACS installiert, HA-Test neu
  gestartet. `production` NICHT angefasst.
  - Drei Läufe auf `Test2`, Verteiler `Gardena1`, Sensor `sensor.wasser_3_flow` auf `0`:
    09:58 `completed` 3,05 L · 10:15 `completed` 3,0 L (beide alter Build) · **10:26
    `failed` / `flow_never_started` 0 L** (neuer Build). Eimer, `water_used_total` und
    `last_irrigation` blieben unberührt, die neue WARNING steht im Log.
  - **Aber:** der Sensor hatte `last_reported = 10:20:16`, das Fenster lief 10:25:30–10:26:30.
    Er hat während des Laufs **nicht gemeldet** — genau der Fall, in dem der Lauf seine
    zeitbasierte Gutschrift hätte behalten müssen. Der Test zeigt also, dass die Kette
    durchläuft, nicht dass sie richtig urteilt. **Muss mit einem meldenden Sensor wiederholt
    werden.**
  - Was steht: auf dem Build **ohne** Fix bekamen in einem Zyklus **vier** Member-Zonen je
    3,05 L gutgeschrieben, Sensor durchgehend 0 — **12,2 L als geliefert verbucht**, alle
    vier Eimer von Defizit auf 0, alle Problem-Sensoren `off`.
  - Volles Protokoll: `archive/design-history`,
    `docs/superpowers/reconstructed/2026-09-27-dry-distributor-member-live.md`.
- **Drei Zeugen-Entwürfe, zwei davon als Regression GEMESSEN**, bevor der dritte hielt.
  Das ist die Substanz dieser Sitzung und steht in Spec §4:
  1. `last_live` (Poll-Zeitpunkte) — drei Eingaben lieferten `0.0` für Läufe mit echtem
     Wasser, wo `418ab8a0` `None` gab;
  2. `priced_anything()` — rastete beim *ersten* verbuchten Intervall ein, zwei gewöhnliche
     Reads davor hoben die Wirkung auf;
  3. `metered_the_run()` = verbucht **und** nichts verworfen — hält gegen alle sechs
     Eingaben und alle vier Trocken-Kontrollen.
  Zweimal war die Wurzel dieselbe wie bei `#174`s Critical: Schwester-Pfad-Check eine Ebene
  zu früh abgebrochen.
- **Die Matrix hat einen toten Term gefunden:** `saw_reset()` im Guard tötete nichts.
  Beweisbar redundant — `_saw_reset` wird an genau einer Stelle gesetzt, *innerhalb* des
  near-zero-Zweigs, `_declined` unbedingt darüber. Term entfernt (`bd7930f6`) statt einen
  Test dafür zu erfinden.
- **🔴 upstream/master = `c5330c7f`, fünf PRs gemergt:** `#165` (`f0027213`), `#168`
  (`e8a3ef8f`), `#169` (`85e54468`), `#171` (`59a3da8c`), `#173` (`c5330c7f`).
  Beide noch offenen PRs stehen auf **`CHANGES_REQUESTED`**: `#174` (zusätzlich `DIRTY`,
  weil `#173` darunter gemergt wurde) und `#172`.
  - `#172`: (1) die Tests hängen am Kalender und **fielen auf seiner Uhr um**, drei
    Fehlschläge — dieselbe Klasse, die wir selbst als `JustChr#141` gemeldet haben;
    (2) bei `autocalcmode: before_run` bepreist der Resolver den **nächsten** Lauf, weil der
    Fire-Callback `_armed_runs` vor `_execute_schedule` leert; (3) offene Frage zu Zonen ohne
    eigenen Zeitplan, er tendiert zum `evaluated_at`-Fallback.
- **⚠️ Der nächste Text an JustChr MUSS sich für die Falschreferenzierungen entschuldigen**
  (User-Anweisung 2026-09-27). Er hat sie in beiden Reviews gerügt: „Nobody reading this
  repository can follow those."
- **Konvention korrigiert:** wir verweisen **nur auf das, was es bei JustChr schon gibt** —
  es werden **keine** Issues angelegt, nur um zitieren zu können (User-Anweisung). Für `#53`
  existiert upstream keins, also stehen dort **keine** Verweise; der Kommentar beschreibt den
  Defekt. Umgesetzt in `dc56b1fb`: 21 Präfixe und 2 `spec D2` entfernt, Endkontrolle am Diff
  ist leer.
- **P2 nachgezogen** (alles freigegeben, alles gesendet): `Eifel-Joe#3`, `#2`, `#43`, `#6`,
  `#52` kommentiert und **geschlossen**; `#4`, `#21`, `#22`, `#45`, `#53` kommentiert und
  offen; **`#56` neu** (Reset-Umfang aus `#52` Teil 2); `#42` Body in beiden Sprachhälften
  aktualisiert. 46 Issues offen.
- **Regel P1 erfüllt:** Spec, Plan und Live-Protokoll auf `archive/design-history` =
  **`82612625`, gepusht**.

### Verworfen
- **`last_live` als Zeuge** (Tasks 2–4). Gemessen gegen `418ab8a0`: Rate 12 L/min mit
  Lücken > `max_gap_s`, Totalizer `100→60,70,80,90`, Totalizer `45→8,20,30,40` — alle drei
  auf HEAD `0.0`, auf der Basis `None`.
- **`priced_anything()`** (Task 4b). Zwei gewöhnliche Reads vor jeder dieser Eingaben
  rasten den Flag ein und schreiben den Rest des Fensters ab.
- **`saw_reset()` als zweiter Guard-Term** — redundant, siehe oben.
- **`set_bucket` + `calculate_zone`, um eine Member-Zone wieder fällig zu machen.**
  `set_bucket` schreibt den Store direkt (auf `handle_set_zone` registriert) und rechnet die
  Dauer **nicht** neu; `calculate_zone` konnte auch keine liefern, weil PirateWeather mit
  **429** antwortete. Ersetzt durch `run_zone` auf der Member-Zone, das über
  `_dispatch_distributor_cycles(..., duration_override=...)` läuft und die Fälligkeit umgeht.

### Fallen
- **🔴 Surrogat-Escapes, zum zweiten Mal.** `\ud83d\udc41\ufe0f` für 👁️ ist ein halbes
  Surrogatpaar, kein Emoji — der Anker fand nichts. Richtig: `\U0001F441\uFE0F`. Nur die
  `assert count == 1` hat den Fehlgriff gefangen.
- **🔴 Ein `<<'PYEOF'`-Heredoc frisst eine Backslash-Ebene.** `\\n` in einem Python-String
  landete als echter Zeilenumbruch in der Datei und riss das Skript. Zweimal passiert.
  **Mehrzeilige Skripte mit dem Write-Tool schreiben und per absolutem Pfad aufrufen**, nie
  per Heredoc.
- **Ein `sed`-Muster, dessen eigene Verifikation den Fehler nicht zeigen kann.** Plan-Task 5
  verbreiterte 8 Stubs, `numstat` sagte `8 8` und `grep -c` sagte `8` — beide bestätigten nur,
  dass der `sed` tat was er sagte, nicht dass das Muster alle Stellen traf. Drei weitere
  Stubs benutzen `w` statt `s` als Parameternamen.
- **Ein Test, der VOR dem Fix grün ist.** Plan-Task 8 benutzte `_dist(...)` ohne
  `watering_mode`; der Default `CLASSIC` macht `can_stop` unbedingt wahr und schließt das
  Gate kurz, das der Test prüfen sollte. Fixture auf `WATERING_MODE_SERVICE`, dann echtes RED.
- **`irrigation_plus.set_bucket` auf den *Eimer*-Sensor gibt HTTP 500** statt das Ziel
  abzulehnen. Richtiges Ziel ist der Zonen-Sensor (`sensor.irrigation_plus_test2`).
- **Verteiler- und Zonenfelder sind per MCP nur lesbar** — der Flusssensor am Verteiler musste
  im Panel gesetzt werden. `set_bucket`, `run_zone`, `calculate_zone`,
  `distributor_run_now` gehen dagegen per Service.
- **Die Integrations-Diagnostics geben den Pirate-Weather-Schlüssel im Klartext aus.** Nicht
  in Dateien, Issues oder Commits kopieren; er gehört zu Memory `hasi-pirate-weather-api-key`.

### Stand auf HA-Test (aufräumen oder bewusst so lassen)
- Läuft **`v2026.09.27b1`** — dieser Build enthält `#3`/`#4` **nicht**. Wer die
  Ventil-Sicherheit dort zurück will, installiert `v2026.09.22b1`.
- `Gardena1` trägt jetzt `flow_sensor: sensor.wasser_3_flow`.
- `Test2`s Eimer steht von Hand auf **−5 mm**, kein echtes Defizit. `Test3`, `Test5`, `Test6`
  wurden nach dem ersten Zyklus auf −0,61 zurückgesetzt.
- Grace Test trägt weiter `flow_sensor` + `throughput 4`.

### Nächste Schritte
0. **⛔ DER `#53`-BRANCH DARF SO NICHT GEPUSHT WERDEN.** 20 seiner Commit-Messages tragen
   noch `Eifel-Joe#53` / `Eifel-Joe#4`. Code- und Test-Kommentare sind bereinigt (`dc56b1fb`),
   die Messages NICHT — derselbe halbe Schritt, für den die Rüge kam. **User-Entscheidung
   2026-09-27: wird nicht separat repariert, sondern beim Umbau auf die `last_reported`-Form
   (Schritt 1–2) neu geschrieben.** Vor jedem Push beide Checks aus Memory
   `no-own-issue-refs-upstream` fahren — Diff **und** Commit-Messages.
1. **`JustChr#174` zuerst** — er legt die Zeugen-Form fest, die `#53` erbt. Nötig:
   `State.last_reported` als Evidenz, Rebase auf `c5330c7f`, Testkommentare von unseren
   Nummern befreien, **und die Entschuldigung**. Sein sekundärer Punkt (geplantes Volumen
   unter `FLOW_CAL_METER_RESOLUTION_L`) ist ausdrücklich optional.
2. **`#53` auf dieselbe Form ziehen**, dann **Live-Test wiederholen** mit einem Sensor, der
   während des Laufs wirklich meldet (Sonoff-Emulator oder ein `input_number` als Flussquelle).
3. **`JustChr#172`** — Uhr in den Tests pinnen, den `before_run`-Anker korrigieren (Test durch
   das echte `_advance_past_fired_occurrence`), seine Frage zu Zonen ohne Zeitplan beantworten,
   rebasen, `#159`/`#160` zitieren.
4. **PR 2 / Task 11 (`Eifel-Joe#45`)** ist entblockt: `#165` gemergt, also rebasen —
   er squasht, der Basis-Commit wurde umgeschrieben. **Vorher prüfen, ob `c5330c7f` den
   Defekt noch trägt** (`#165` Punkt 8 behob die sequenzielle Warteschlange, Punkt 6 gab dem
   rotierenden Zweig nur Marker und Logging).
5. **`Eifel-Joe#22` PR 1** ist entblockt (`#168` gemergt), wird auf aktuellem master gebaut.
6. Aufräumen, wenn `#173`/`#174` durch sind: Worktrees `pr34-work/{pr1,pr2}`,
   `prerelease-work/wt`, `issue53-work/base`, und der Wegwerf-Branch
   `prerelease/v2026.09.27b1` samt Release. Vorher die kleinen Ordner ansehen
   (Memory `scratch-dirs-hold-irreproducible-evidence`).

### Empfohlene Skills
`pr-workflow` für `#174`/`#172`, `superpowers:receiving-code-review` für JustChrs Befunde
(er hat zweimal recht gehabt, wo ein eigenes Review nichts fand),
`superpowers:verification-before-completion` vor jedem „fertig" — diese Sitzung hat einen
Live-Test als Beweis gelesen, der keiner war.

---

## 2026-09-26 (2) — Eifel-Joe#3 + #4: gebaut, reviewt, LIVE BELEGT, als JustChr#173/#174 upstream

### Stand (verifiziert)
- **FERTIG BIS UPSTREAM.** Zwei PRs offen, beide live belegt, Historie archiviert,
  drei Folge-Issues angelegt, `Eifel-Joe#42` nachgezogen. Nichts hängt im Chat.
  - **[`JustChr#173`](https://github.com/JustChr/HAsmartirrigation/pull/173)**
    (`Eifel-Joe#3`) — Branch `fix-zone-fault-is-paired-and-cleared`, Kopf
    `b549de3f`, +152/−2 in 14 Dateien. Suite isoliert 3258 passed (Baseline +4),
    356 Namen `diff`-identisch, Lint grün, 5 Mutanten getroffen.
  - **[`JustChr#174`](https://github.com/JustChr/HAsmartirrigation/pull/174)**
    (`Eifel-Joe#4`) — Branch `fix-a-run-that-delivered-nothing-is-not-a-success`,
    Kopf `c9619727`, gestapelt auf #173. Suite isoliert 3266 passed (Baseline +12),
    356 Namen identisch, Lint grün, 8 Mutanten getroffen.
  - **Beweis der Zusammensetzung:** PR1 + PR2 ergeben einen **leeren Diff** gegen
    `4880aa99`, den live getesteten Stand. Was JustChr bekommt, ist genau das, was
    auf HA-Test lief.
  - Beide Issues kommentiert (Regel P2) und auf `upstream:gemeldet`.
- **Arbeitsbranch** `fix/self-closing-fault-lifecycle`, Worktree
  `D:/Entwicklung/HASI/issue3-work/wt`, Basis `418ab8a0`, Kopf **`4880aa99`**,
  **nicht gepusht** — er trägt die Entwicklungshistorie samt `docs/superpowers`.
  - Voll-Suite **7 failed / 3266 passed / 9 skipped / 349 errors**, 356 Namen
    `diff`-IDENTISCH zur Baseline auf DEMSELBEN Basis-Commit
    (`issue3-work/baseline-names.txt`). Rechnung: 3254 + 4 (Plan 1) + 7 (Plan 2)
    + 2 (C-1) − 1 (gestrichener Test) = 3266.
  - `uvx black --check` 69 Dateien unverändert, `uvx ruff check` sauber,
    **629 Frontend-Tests** grün (vitest).
  - **13 Mutanten in den Plan-Matrizen, alle getroffen** (5 Plan 1, 8 Plan 2),
    Treiber `issue3-work/matrix1.py` / `matrix2.py`.
  - Diff: `self_closing.py +191`, `flow_metering.py +27`, 8 Sprachdateien je +1,
    2 dist-Bundles, `docs/usage-events.md`, 3 Testdateien. **`distributor.py`
    unberührt** (Schwester-Pfad bewusst vertagt).
- Dokumente (Regel P1, noch NICHT archiviert):
  `docs/superpowers/specs/2026-09-26-self-closing-fault-lifecycle-design.md`,
  `docs/superpowers/plans/2026-09-26-fault-pairing-and-clearing.md`,
  `docs/superpowers/plans/2026-09-26-dry-run-is-not-a-success.md`.
  Beide Pläne tragen die **gemessenen** Zahlen samt der Vorhersagen, die danebenlagen.
- **🔴 Der Review fand einen Critical, der `#4` ins Gegenteil verkehrt hätte** —
  `_flow_build_meter` füttert den Ventil-Öffnungs-Read IN den Meter, also ist
  `_have_reading` ab Sekunde 0 wahr und `delivered()` gibt nie mehr `None`.
  **Gemessen: 45 L real geliefert, `delivered() == 0.0`, `saw_reset() == True`**
  — der Lauf wäre als FAILED verbucht und die Gutschrift zurückgedreht worden.
  Der klassische Läufer leitet genau das vorher ab (`irrigation.py:1536`) und
  pinnt es mit `test_metered_zone_auto_hold_until_reset_credits_timed_not_fault`.
  **Ich hatte seinen Dry-Zweig gespiegelt, aber nicht seine Vorbedingung** — der
  Schwester-Pfad-Check eine Ebene zu früh abgebrochen.
  Fix: `FlowMeter.saw_reading_after_open()` + `saw_reset`-Guard in
  `_sc_finish_flow`. `delivered()` blieb unangetastet.
- **Drei weitere Review-Befunde eingearbeitet:** der `no_anchor`-Zweig ist
  **gestrichen** (unerreichbar — beide Record-Schreiber setzen `RUN_PRE_BUCKET` —
  und wo er zündete inkohärent: `_stamp_run_finalized` nullte die Dauer auf der
  nicht zurückgedrehten Gutschrift); `valve_did_not_open` in **allen 8 Sprachen**
  nachgetragen (fehlte komplett, Chip fiel auf `generic`); zwei Event-Verträge in
  `docs/usage-events.md` nachgezogen.
- **Spec §10 trägt den ganzen Review-Durchgang**, samt der zwei Punkte, in denen
  ich dem Reviewer mit Beleg widersprochen habe (`<= 0` statt `== 0` ist richtig;
  die Früh-Stopp-Insulation kann keinen Volllauf verschlucken).
- **🧪 LIVE-TEST AUF HA-TEST: BEIDE BESTANDEN.** Pre-Release
  [`v2026.09.22b1`](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.09.22b1)
  (Commit `45682c0b`, Branch `prerelease/v2026.09.22b1`) gebaut, per HACS installiert,
  HA-Test neu gestartet; geladene Integration meldet `v2026.09.22b1`.
  **`production` wurde NICHT angefasst** — bewusster Wegwerf-Testbau, damit ein
  Befund nur von den zwei Fixes kommen kann.
  - **`#3`:** Fehler gesetzt 22:43:32 (`valve_did_not_open`, Hub-Sensor an), guter
    60-s-Lauf löschte ihn 22:45:54. Auf master passiert beides nicht.
  - **`#4`:** Protokoll `failed`/`flow_never_started`, Eimer von −2,32 zurück auf
    −2,72, `water_used_total` unberührt bei 0,0, `last_irrigation` nicht gestempelt.
    Eimer-Buchführung zeigt beide Richtungen: `+0,4 mm` / `−0,4 mm`.
  - Volles Protokoll: `archive/design-history`,
    `docs/superpowers/reconstructed/2026-09-26-valve-safety-live-*.md`.
  - **Offen auf HA-Test:** Grace Test trägt weiter `flow_sensor` + `throughput 4` und
    steht auf Fehler. Jeder Lauf dort bleibt trocken, solange der Sensor 0 meldet —
    Flusssensor-Feld im Panel leeren, dann löscht der nächste gute Lauf den Fehler.
- **Drei Folge-Issues angelegt:** `Eifel-Joe#53` (derselbe `0.0`-Kollaps in
  `distributor.py`, hoch/prod-scharf), `Eifel-Joe#54` (klassischer Läufer,
  blinder Fleck nach dem Open-Read, Bestandsdefekt), `Eifel-Joe#55` (Zyklus-Abbruch
  bei trockener Zisterne, Produktentscheidung, durch `run_chain.py` blockiert).
- **Regel P1 erfüllt:** Spec, beide Pläne und die zwei Live-Protokolle auf
  `archive/design-history` = **`ccde19f6`, gepusht**.
- **HA-Test-Kontext:** Irrigation Plus läuft dort (145
  Entitäten, u.a. `binary_sensor.irrigation_plus_beet_problem` — der Sensor aus
  dem `#3`-Kriterium), drei numerische Flusssensoren `sensor.wasser_*_flow` stehen
  auf 0 (der `#4`-Leitfall, nicht simuliert sondern vorhanden), Sonoff-Emulator
  vollständig. **OFFEN: wie der Build nach HA-Test kommt** — `custom_components/**`
  ist per MCP nur lesbar.
- **🔴 Die Basis ist WEITERGEWANDERT: `upstream/master` = `418ab8a0` (v2026.09.23)**,
  nicht mehr `10bb8077`. Dazwischen zwei Commits von JustChr selbst:
  `90187eed` (valve.\* per `open_valve` statt `turn_on`, **neues Modul `actuate.py`**)
  und `c70a8438` (metered run schließt sein Ventil, was auch immer nach dem Open wirft).
  Beide **nicht** in unseren Dateien. Kollisionsfrei.
- **Doppelarbeits-Check über alle vier Achsen durch**, nichts kollidiert: offene PRs bei
  JustChr sind `#172`/`#171` (unsere) und `#169`/`#168` (clarejor); **master trägt beide
  Defekte noch** — am Code belegt.

### Verworfen
- **Ein drittes `dry`-Element im Rückgabe-Tupel von `_sc_finish_flow`** (erster Entwurf).
  Gemessen: **22 Test-Stellen in 9 Dateien** stubben die Methode als 2-Tupel, und
  **kein Test pinnt den Kollaps**. Ersetzt durch: den Kollaps ersatzlos streichen.
- **Zentrales Löschen in `_record_run`** — hätte auch bei `OBSERVED` und `SKIPPED` gefeuert.
- **Die Sampler-Markierung aus `Eifel-Joe#4`s Body.** Statt Markierung: Pin-Test
  (Plan 2 Task 5), der bei `dry = not measured` rot wird.
- **Der `no_anchor`-Zweig** (war in der Spec, gebaut, nach Review gestrichen).

### Fallen
- **🔴 Fehlerzahlen hängen an der TEST-AUSWAHL, nicht nur am Code.** Dieselben drei
  Dateien geben 51 Fehler als Teilmenge und 13 im Voll-Lauf — auf dem unveränderten
  Basis-Commit identisch reproduziert. **Nur der Voll-Lauf mit Namens-`diff`
  entscheidet** — er fand `test_master.py::..._does_not_strand_the_pump`, das keine
  Teilmenge der vier Tasks enthielt.
- **Mutationen NIE per Rück-Ersetzung zurücknehmen, immer `git checkout -- <datei>`.**
  M1s Anker (`self._fire_zone_problem(`) kommt zweimal in der Datei vor; der Revert
  lehnte korrekt ab — aber M1 blieb aktiv und verfälschte M2 und M3 still.
- **Eine Mutation, die nichts tötet, kann die FALSCHE Mutation sein.** Plan 1 Task 4
  wollte das Löschen innerhalb von `async_stop_self_closing` verschieben; das kann
  die Reihenfolge gegenüber einem späteren Aufrufer prinzipiell nicht ändern. Erst
  die Mutation in `run_watch.py` traf.
- **`_flow_build_meter` impft den Meter beim Ventil-Öffnen.** Wer `delivered() == 0.0`
  als „trocken" liest, liest auch „Sensor nach dem Open-Read gestorben" und
  „Totalizer-Reset, den der Meter nicht bepreisen kann" als trocken.
- **Der i18n-Katalog für Fault-Gründe liegt in
  `frontend/localize/languages/*.json`, NICHT in `custom_components/*/translations/`.**
  Nur `en.json` wird gebündelt (Rest zur Laufzeit geladen) → `en`-Änderungen
  brauchen `npm run build` + `git add -f` der betroffenen dist-Bundles.
- **🔴 `pathlib.write_text` leert die Datei, BEVOR es kodiert.** Ein Surrogat im
  Python-Quelltext (`\ud83d\udd34` statt `\U0001F534`) hat so diese Datei
  vernichtet. Für nicht versionierte Dateien: in eine Temp-Datei schreiben und
  umbenennen, oder das Write-Tool nehmen — nie direkt über das Original.
- **Die MSYS-Heredoc-Falle** (`"""` im Python-Text bricht `python - <<'EOF'`):
  Skript mit dem Write-Tool nach `D:/Entwicklung/HASI/issue3-work/*.py` schreiben
  und per absolutem `D:`-Pfad aufrufen. Dasselbe für mehrzeilige Commit-Messages.

### Nächste Schritte
1. **`JustChr#173` und `#174` Review abwarten.** Bei Änderungswünschen: neuer Commit
   auf denselben Branch, kein amend, kein Force-Push (pr-workflow §6).
2. **Aufräumen, wenn die PRs durch sind:** Worktrees `issue3-work/{base,wt}`,
   `pr34-work/{pr1,pr2}`, `prerelease-work/wt` und ihre Branches. Vorher prüfen, ob
   in den `*-work/`-Ordnern noch etwas Einmaliges liegt (Memory
   `scratch-dirs-hold-irreproducible-evidence`) — die Live-Protokolle sind bereits
   im Archiv, die Suite-Ausgaben und `baseline-names.txt` sind reproduzierbar.
3. **HA-Test säubern:** Flusssensor-Feld an Grace Test leeren, dann guter Lauf.
4. **Frei und unblockiert:** `Eifel-Joe#5` (hoch, M, prod-scharf, `websockets.py`,
   Denylist gegen Allowlist) und `Eifel-Joe#53` (hoch, M, prod-scharf, Verteiler).
   `#54` und `#55` danach.
5. Weiter offen und unverändert: `JustChr#165` Re-Review → dann PR 2 / Task 11
   rebasen; `JustChr#171`, `JustChr#172`; `Eifel-Joe#22` nach `JustChr#168`;
   `Eifel-Joe#52` Teil 2 entscheiden.

### Empfohlene Skills
`superpowers:verification-before-completion` vor jedem „fertig", `pr-workflow` für
die PRs.

---

## 2026-09-26 — clarejor deckt unser #6 ab, #52 ist upstream

### Stand (verifiziert)
- **`Eifel-Joe#6` auf `beobachten`** (bleibt offen, schließt mit dem PR): clarejors
  **`JustChr#169`** deckt den Befund vollständig ab und findet **zusätzlich** den
  Spitzen-statt-Mittelwind, den wir nicht hatten (Open-Meteo war der einzige Client,
  der PyETO eine Spitze lieferte). Kommentar + Label gesetzt,
  [issuecomment-5845498055](https://github.com/Eifel-Joe/HAsmartirrigation/issues/6#issuecomment-5845498055).
- **Wir haben `JustChr#169` reviewt statt nachgebaut** (User-Entscheidung),
  [issuecomment-5845398134](https://github.com/JustChr/HAsmartirrigation/pull/169#issuecomment-5845398134).
  **Kein Defekt.** Drei Dinge gegen die **Live-API** geprüft, die seine Tests nicht
  erreichen können, weil sie die Antwort mocken:
  1. Der Abruf mit seiner neuen `daily=`-Liste antwortet **200**, alle drei Variablen
     gefüllt. Ein falscher Variablenname wäre durch jeden Mock gerutscht und hätte jede
     Open-Meteo-Installation beim ersten echten Abruf zerlegt.
  2. Die **API-Tagesmittel SIND die Mittel der eigenen Stundenreihe** — größte Abweichung
     über 7 Tage 0,05 °C / 0,05 hPa / 0,005 m/s, also Rundung. Damit ist **unsere
     `#6`-Fixform überholt**: wir wollten aus der Stundenreihe mitteln
     (`MetOfficeClient` als Vorbild), seine Variante nimmt die Aggregate — gleiche Zahl,
     weniger Code.
  3. **Keine Nulls** in `wind_speed_10m_mean`/`_max`, `dew_point_2m_mean`,
     `pressure_msl_mean` über 16 Tage an vier bewusst verschiedenen Orten
     (Berlin, Sydney, Reykjavík, Singapur).
  Punkt 3 **widerlegt** den Befund, den ich gesucht hatte (Null beim Mittelwind verwirft
  den Tag samt Regen, weil Wind im harten `continue` steckt, Taupunkt und Druck aber
  optional gesetzt werden). Als Frage gepostet, nicht als Befund — die Asymmetrie ist
  nirgends begründet, schadet aber nachweislich nicht.
- **`Eifel-Joe#52` gebaut und upstream: [`JustChr#171`](https://github.com/JustChr/HAsmartirrigation/pull/171)**
  (`1ddab319`, Branch `fix/intraday-estimate-leaves-a-traceback` von `10bb8077`).
  `exc_info=True` auf `_intraday_for_zone`s DEBUG-Zeile. Gates: RED belegt, Mutation
  (`exc_info` weg → nur der neue Test rot), Voll-Suite 7/3236/349, Lint grün.
  Label `upstream:gemeldet` neben `freigegeben`.
  **Teil 2 bleibt offen** (erster Fehlschlag pro Refresh auf WARNING): der Reset-Umfang
  ist zu entscheiden — pro Refresh, pro Zone, pro Prozess. Steht so im PR-Text.
- **`Eifel-Joe#22` PR 1 WARTET** (User-Entscheidung): clarejors **`JustChr#168`**
  schreibt `live_estimate.py` mit +499/−34 um, also genau die Einstiegspunkte, die PR 1
  herkunfts-total machen soll. Vorher bauen heißt, PR 1 darauf zu rebasen.
- `Eifel-Joe#42` in beiden Sprachhälften nachgezogen (Positionen 7, 24, 39).
- **PR 2 (Task 11) unverändert fertig und ungepusht** — siehe Eintrag vom 25.09.

### Eifel-Joe#21: UMGESETZT, upstream als `JustChr#172`
- Worktree `D:/Entwicklung/HASI/issue21-work/wt`, Branch
  `fix/forecast-weighting-from-run-start` von `10bb8077`.
  **Spec `c755813f`, Plan `e74ce7e4`** — kein Produktionscode.
  Spec: `docs/superpowers/specs/2026-09-26-forecast-weighting-from-run-start-design.md`,
  Plan: `docs/superpowers/plans/2026-09-26-forecast-weighting-from-run-start.md` (9 Tasks).
- **Gemessen vor jedem Entwurf** (Wegwerf-Repro `tests/test_zz_repro_issue21.py`, grün
  auf `10bb8077`): Zone 10 mm Defizit, Vorausschau 1 Tag, morgen trocken, übermorgen 8 mm,
  Lauf übermorgen 06:00 → master wässert **10,00 mm**, das Fenster ab Laufbeginn würde
  **4,00 mm** wässern. **6 mm zu viel**, in der Nacht vor 8 mm Regen.
- **Drei Entscheidungen des Users (26.09.):** schmaler eimer-freier Resolver im Scheduler
  statt der Projektion; armierter `start_utc` zuerst, sonst der maßgebliche Zeitpunkt;
  kein auflösbarer Laufbeginn heißt nicht gewichten.
- **Warum die Projektion nicht geht:** `async_get_next_run_projection` dimensioniert
  „from each zone's bucket AT THE DECISION POINT" — Zyklus. Und bei Ende-Verankerung ist
  selbst der Start nicht eimer-frei (`target − _estimate_duration` →
  `get_total_irrigation_duration`). Daher Task 4: Zyklus-Pin als Test.
- **Befund gegen den eigenen Entwurf, rechtzeitig:** ein Repro mit zwei Vorhersagetagen
  lässt `first_24h_covered` `False` werden, der Fix hätte sich im eigenen Zielfall
  enthalten. Ab 3 Tagen deckt es, echte Clients liefern 7+. Steht als Falle in Spec §7 und
  im Plan-Vorspann.
- **Umsetzung durch, PR offen: [`JustChr#172`](https://github.com/JustChr/HAsmartirrigation/pull/172).**
  PR-Kandidat isoliert auf `fix-forecast-weighting-from-run-start` von `10bb8077`
  (Worktree `issue21-work/pr`), 8 Commits, **5 Dateien, keine `docs/`**. Voll-Suite
  7 failed / **3251** passed / 349 errors, 356 Fehlernamen `diff`-identisch zur auf
  DEMSELBEN Basis-Commit gemessenen Baseline; `+16` = genau die 16 neuen Tests.
  Lint grün. **5 Mutanten, jeder tötet genau seine Tests.** Wächter unberührt
  (`skip_conditions.py`/`forecast_window.py` nicht im Diff, 56 Tests grün).
- **Spec + Plan archiviert:** `archive/design-history` = **`33072668`**, gepusht,
  byte-identisch geprüft. Regel P1 erfüllt. Arbeitsbranch und sein Worktree danach
  entfernt — nur Spec und Plan waren dort einmalig, und beide liegen im Archiv.
- `Eifel-Joe#21` kommentiert (issuecomment-5846331687), Label `upstream:gemeldet`
  gesetzt, `Eifel-Joe#42` Position 23 nachgezogen. Issue bleibt **offen**: die
  Live-Pfad-Hälfte ist noch nicht entschieden.
- **Drei Plan-Korrekturen gegen die Messung**, im archivierten Plan nachgetragen:
  die „frühester gewinnt"-Mutation tötete EINEN Test statt zwei (sie kürzt nur bei
  einem Nicht-`None`-Ergebnis ab — eine zweite Mutation deckt beide Pins); der
  Fixture-Laufbeginn auf 06:00 brach DREI der vier Bestandstests statt einem
  (18/24 + 6/24 über zwei Einträge, Mitternacht deckt sie); und eine vorhergesagte
  Fehlerzahl war falsch gerechnet.
- `calculate_module`s `now` ist ein **nacktes naives** `datetime.now()` (`calculation.py:883`)
  — die `#22`-Naht. Die Gewichtung nimmt `dt_util.utcnow()`, damit `#21` und `#22`
  einander nicht blockieren.

### Aufgeraeumt (2026-09-26, Ende)
- **Drei PRs warten auf JustChr:** `JustChr#165` (Einengung geliefert, Re-Review offen),
  `JustChr#171` (`exc_info`-Einzeiler), `JustChr#172` (`Eifel-Joe#21`).
  **PR 2 zu Task 11** liegt fertig und **ungepusht** in `issue2-work/pr2` (`1b3cc7d5`),
  bis `#165` mergt — JustChr squasht, der Basis-Commit wird umgeschrieben.
- **Worktrees entfernt:** `issue21-work/wt` samt Branch (nur Spec+Plan waren dort
  einmalig, beide byte-identisch im Archiv), und `pr139-work/dry2` samt Branch
  `dry7/backstop-grace`. Letzterer war am **Inhalt** geprüft, nicht an der Ahnenreihe:
  14 Commits fehlen upstream als Vorfahren, weil JustChr squasht, aber
  `run_finish_grace_seconds` und `latency_margin_help` stehen in master.
- **`pr139-work` von 156 MB auf 2,5 MB**, nur `archive-wt` bleibt. Dabei zwei nicht
  reproduzierbare Live-Test-Protokolle (HA-Test + HA-Prod, 20.09.) gerettet nach
  `docs/superpowers/reconstructed/2026-09-20-backstop-grace-live-results.md` und ein
  hängender absoluter Pfad in der `#139`-Spec entschärft. Lehre als Memory
  `scratch-dirs-hold-irreproducible-evidence`.
- **`archive/design-history` = `e1d6fdf7` GEPUSHT** (Fern-Stand geprüft, gleich dem lokalen).
  Nichts mehr offen, das nur im Chat lag.
- `befunde-work/base` ist ein Worktree auf detached HEAD `c9e84d72` ohne erkennbaren
  Zweck — absichtlich liegen gelassen, Herkunft unklar.

### Frei und unblockiert (nach Schwere, alle prod-scharf)
Keiner berührt `run_chain.py` (PR 2), `live_estimate.py` (`#22`/clarejors `#168`) oder
`calculation.py` (`#172`):
- **`Eifel-Joe#3`** (hoch, S) Ventil-Sicherheit 1 — **ERLEDIGT, siehe 2026-09-26 (2)**
- **`Eifel-Joe#4`** (hoch, M) Ventil-Sicherheit 2 — **ERLEDIGT, siehe 2026-09-26 (2)**
- **`Eifel-Joe#5`** (hoch, M) veralteter Panel-Speichern dreht Eimer-Gutschrift zurück,
  Denylist gegen Allowlist tauschen — `websockets.py`
`Eifel-Joe#45` ist durch PR 2 blockiert (`run_chain.py`), `#6` ist `beobachten`.

### Fallen
- **`reviewDecision` leer heißt NICHT „kein Review".** Ein `COMMENTED`-Review setzt das
  Feld nicht, und Inline-Kommentare am Diff sind keine Issue-Kommentare. Vor jedem
  Review/Nachbau **drei Achsen** prüfen: `pulls/N/reviews`, `pulls/N/comments`,
  `issues/N/comments`. Und die vierte: **trägt master den Defekt überhaupt noch** —
  JustChr fixte bei `#134` die Hälfte parallel selbst. Memory
  `check-before-duplicating-work`.
- **🔴 Die alte Baseline gilt nicht, wenn sich der Basis-Commit bewegt hat.** Die Suite
  meldete **349** Errors, wo `baseline-names.txt` (auf `965a4f9d`) 320 hat — die 29 mehr
  bringt clarejors `#167` mit. Statt die Lücke wegzuerklären: zweiter Worktree auf dem
  unveränderten Basis-Commit, dort durchlaufen, DANN vergleichen. Memory
  `rebaseline-when-the-base-moves`.
- **Heredocs mit `'''` und `"""` im Python-Text zerbrechen unter MSYS** („unexpected EOF
  while looking for matching `''"). Skript mit dem Write-Tool in den Scratchpad schreiben
  und per Pfad aufrufen.
- **MSYS-`/tmp` ist für Windows-Python nicht sichtbar.** `curl -o /tmp/x.json` plus
  `python -c "open('/tmp/x.json')"` gibt `FileNotFoundError`. Ausgabedatei unter `D:` ablegen.
- **`subprocess` in Windows-Python nimmt keinen MSYS-Pfad** (`/d/...`) als Executable →
  `WinError 2`. `D:/...` schreiben.

### Nächste Schritte (offen)
1. `JustChr#165` Re-Review abwarten → dann PR 2 rebasen, Zahlen neu messen, Body entwerfen.
2. `JustChr#171` Review abwarten.
3. `Eifel-Joe#21` (Vorhersage-Gewichtung) — erledigt, siehe oben.
4. `Eifel-Joe#22` PR 1 erst nach `JustChr#168`.
5. `Eifel-Joe#52` Teil 2 entscheiden (Reset-Umfang der WARNING-Drosselung).

---

## 2026-09-25 — JustChrs Reviews eingearbeitet, Issue-Liste nachgezogen

> ⚠️ **Dieser Eintrag ist UNVOLLSTÄNDIG** (Datenverlust 2026-09-26, siehe Kopf der
> Datei). Erhalten ist, was in der Sitzung vom 26.09. gelesen worden war; der Rest
> des Eintrags fehlt.

### Stand (verifiziert, alles am 23./24.09. von JustChr)
- **Drei PRs GEMERGT**, alle in der Beta
  [v2026.09.22](https://github.com/JustChr/HAsmartirrigation/releases/tag/v2026.09.22):
  `JustChr#162` (`244a8425`) → unser `Eifel-Joe#1`; `JustChr#163` (`11f19689`) →
  unser `Eifel-Joe#23`; `JustChr#164` (`8d50194a`) = Doku-Hälfte von `Eifel-Joe#22`.
  Er hat jeweils selbst nachgemessen und die Mutation gefahren.
- **`JustChr#165` = CHANGES_REQUESTED.** Suite bei ihm 3236 (mit #161–#164 getrimmergt
  3248), Mutation bestätigt. Er akzeptiert alles bis auf **einen** Punkt, ausdrücklich
  „about scope rather than correctness": **das Überlagern der geplanten Dauer nur noch
  bei `plan.live`**. Begründung: eine Nachrechnung mitten in der Kette kann eine
  gespeicherte Dauer realistisch nur senken, also ist eine auf 120 s/0 s umgeschriebene
  wartende Zone in der Praxis eine beregnete; und die eingefrorene Dauer wäre gegen den
  Zyklus-Start-Eimer gepreist, während `pre_bucket` der frische ist.
- **Entscheidung des Users (2026-09-24): Einengung annehmen.** Beide gemessenen Defekte
  sind `live=True`, der Fix übersteht es unversehrt; Installationen ohne Live-Estimate
  bleiben bei der Dauer byte-identisch zu master. Das volle Einfrieren bleibt als eigene
  Entscheidung verfügbar, wir haben keinen Fall dafür.
- **`JustChr#160` beantwortet: zwei PRs** in der von uns vorgeschlagenen Reihenfolge.
  Neue verbindliche Auflage: die **zwei Herkünfte im Code benennen** (ein Helfer je
  Herkunft, oder einer mit Pflicht-Argument) — PR 1 trägt das Vokabular, PR 2 benutzt es
  nur. `exc_info=True` auf `_intraday_for_zone` als eigener Einzeiler freigegeben.
  **Basis verschoben:** clarejors `JustChr#167` ist gemergt (`10bb8077`), PR 1 muss auf
  aktuellem master aufsetzen — die neue Zeilenquelle (`_resolve_hourly_forecast`,
  `_read_hourly_forecast`) ist naive HA-local, also zweite Herkunft.

### Einengung von `JustChr#165` gebaut (2026-09-25)
- **`f1c8c937`** auf `fix/chain-carries-zone-snapshots`, **gepusht**; Kommentar auf
  `JustChr#165` ([issuecomment-5827760976](https://github.com/JustChr/HAsmartirrigation/pull/165#issuecomment-5827760976))
  und auf `Eifel-Joe#2` ([issuecomment-5827777112](https://github.com/Eifel-Joe/HAsmartirrigation/issues/2#issuecomment-5827777112)).
  Eine Bedingung (`if plan is not None` --> `... and plan.live`), drei Docstrings,
  vier Tests. PR wartet auf Re-Review.
- **Gates:** RED 2 failed (beide Nicht-live-Tests gaben `(2, 600.0)` statt 120/0);
  Voll-Suite **7 failed / 3231 passed / 9 skipped / 320 errors**, 327 Fehlernamen
  `diff`-identisch zur Baseline, `+40` = 38 (PR 1) + 2 neue; black 68 unverändert,
  ruff sauber; **5 Mutanten alle gefangen** (Einengung zurück --> 3, Overlay weg --> 6,
  `live=True` --> 5, `live=False` --> 8, Marker-Restore weg --> 1).
- **Der eine dünne Pin wurde gegengeprüft, nicht vermutet:** dieselbe Mutation auf dem
  Vorgänger-Commit machte ebenfalls genau 1 rot. Nicht von uns geschwächt.
- **Vier eigene Fixtures modellierten Unerreichbares** — drei bauten die live-Kopie ohne
  `_live_run_zones` (`_apply_live_durations` setzt beides im selben Zweig,
  `irrigation.py:2315`/`:2327`), eine behauptete einen live-Plan von 0, den
  `_zone_run_decision` bei `live <= 0` verhindert (`:2404`). JustChr hatte zwei
  betroffene Tests vorhergesagt. Lehre als Memory
  `narrowing-exposes-impossible-fixtures` festgehalten.
- **Nebenbefund im Code vermerkt:** Overlay-Bedingung und Marker-Wiederherstellung sind
  jetzt textgleich, dürfen aber NICHT zusammengefasst werden — das Overlay muss vor die
  Dauerprüfung, die Markierung erst dahinter. Kommentar an der zweiten Stelle.

### Issue-Liste (ausgeführt)
- `Eifel-Joe#1` und `Eifel-Joe#23` **geschlossen** mit Kommentar (Regel P2).
- Kommentar auf `Eifel-Joe#2`, `#43`, `#22` — sein Einwand jeweils **in seinen Worten**
  […] *(hier bricht die gerettete Fassung ab)*

---

> ⚠️ **LÜCKE: hier fehlen rund 250 Zeilen** — der Schluss des 2026-09-25-Eintrags
> und sämtliche Einträge vom **2026-09-22 bis 2026-09-24**. Vernichtet am 2026-09-26
> durch ein fehlgeschlagenes Schreib-Skript; nicht in Git und nicht aus
> Sitzungs-Transkripten rekonstruierbar. Was dort stand, lässt sich zum Teil aus den
> Memories, aus `Eifel-Joe#42` und aus der Commit-Historie von
> `archive/design-history` zurückholen, falls es gebraucht wird.

---

## 2026-09-21 (4) — Eifel-Joe#22 Wetterpuffer-Zeitzone: Spec + Plan, Doku-PR raus

### Stand (verifiziert)
- **Spec + Plan geschrieben und archiviert.** `docs/superpowers/specs/2026-09-21-weather-buffer-aware-time-design.md`
  und `docs/superpowers/plans/2026-09-21-weather-buffer-aware-time.md`, beide auf
  `archive/design-history` = **`b085791f`** (per `git ls-remote` bestaetigt). Regel P1 erfuellt.
  Im Hauptbaum liegen sie untracked — sie gehoeren nicht in den Upstream-PR.
- **`JustChr#164`** (Doku `TZ=`) eroeffnet aus `docs/container-timezone` auf `upstream/master`
  = `965a4f9d`. **Rein additiv, 2 Dateien, +34/-0**, CRLF erhalten (`file` geprueft).
  `lint` und `validate` gruen; `test (3.13)` + `test-ha-floor` liefen bei Sitzungsende noch.
- **`Eifel-Joe#22` kommentiert:** [issuecomment-5765927213](https://github.com/Eifel-Joe/HAsmartirrigation/issues/22#issuecomment-5765927213).
  Label `upstream:freigegeben` bleibt richtig (spaeterer Stand als `upstream:gemeldet`).
- **Branch `fix/weather-buffer-aware-time`** von `upstream/master` = `965a4f9d` steht bereit,
  **noch kein Code** — die Umsetzung faengt frisch mit dem Plan an.
- **Der Bug ist numerisch belegt**, nicht nur gelesen: Prozess-TZ UTC + HA Europe/Berlin laesst
  eine echte Stunde als drei messen (Fehler == UTC-Offset, konstant). Rechnung steht im Spec.

### Entscheidungen dieser Sitzung
- **A+B ein PR** (Schreiber+Migration+Leser), **C** (Laufzeit-Check Prozess- vs. HA-Offset) und
  **D** (Doku) getrennt; D zuerst, weil JustChr ausdruecklich darum bat.
- **Ein gemeinsamer Coerce-Helfer** `helpers.as_stored_aware` statt vier verstreuter naiv-Annahmen.
- **Prozess-Zone injizierbar** (`helpers._process_timezone`), weil `time.tzset()` unter Windows
  fehlt und ein nur-in-CI-Test nie selbst rot-gruen gesehen wird.
- **Keine Detektion** des geaenderten Prozess-TZ — Begruendung im Spec unter D4.
  **Die Antwort an JustChr geht bewusst erst mit dem Code-PR** auf `JustChr#160` raus, nicht vorab.

### Verworfen
- **Zukunfts-Clamp auf migrierte Stempel:** richtungsblind. JustChrs eigenes Szenario (UTC -->
  echte Zone) erhoeht den Offset, die Stempel landen in der *Vergangenheit*, Trefferquote 0 %.
  Zusaetzlich falsch-positiv auf Boards ohne gepufferte RTC (Migration laeuft vor NTP-Konvergenz).
- **Paarung naiver gegen aware Stempel** zur Offset-Rekonstruktion: Rauschen = Signal, und eine
  frisch eingerichtete Installation hat gar keine aware Stempel.
- **Jede datenbasierte Heuristik:** der DST-Ruecksprung im Herbst ist byte-identisch zu einem
  Container-TZ-Fix.

### Fallen
- **Der Spec war an einer Stelle falsch und ist korrigiert.** Ich hatte angenommen, die
  Solargeometrie repariere sich durch das Aware-Machen von selbst. Falsch: `et_estimate.py:140`
  und `weather_aggregate.py:725` lesen den Offset aus dem **Schluessel** `row["tz_offset_h"]`,
  gefuellt nur an `weather_aggregate.py:970` mit `tz.utcoffset(hour_start)`. Ohne Aenderung genau
  dieser Zeile bliebe die teuerste Haelfte des Bugs offen — **und die Suite haette es nicht
  gemerkt**. Jetzt Task 6 mit `hour_start.utcoffset()`.
- **Heredoc mit `<<'EOF'` scheitert unter MSYS an Anfuehrungszeichen im Text** (`unexpected EOF`).
  Fuer laengere Markdown-Dateien das Write-Tool nehmen, nicht `cat >`.
- **Zeilenenden:** `docs/*.md` ist CRLF. Einfuegen per Python mit `\r\n`-Join, sonst reisst der
  Diff die ganze Datei auf.
- **Worktree-Kollision:** `archive/design-history` haengt bereits in
  `D:/Entwicklung/HASI/pr139-work/archive-wt`. Kein zweiter Worktree moeglich — den vorhandenen
  per `fetch` + `reset --hard FETCH_HEAD` aktualisieren und nutzen.
- **Die Verifikationsstufe des Analyse-Workflows hat mehrere „garantierter Crash"-Befunde der
  ersten Stufe widerlegt** (beide Seiten sind heute naiv, es kracht nichts). Erste-Stufe-Befunde
  eines Fan-outs nicht ungeprueft in einen Spec uebernehmen.

### Naechste Schritte
1. **`/clear`, dann Umsetzung** streng nach `docs/superpowers/plans/2026-09-21-weather-buffer-aware-time.md`
   auf Branch `fix/weather-buffer-aware-time`. Tasks 1–8, TDD, ein Commit pro gruenem Task.
   Task 3 ist absichtlich gross (ein Vergleichsraum, sonst `TypeError` zwischen den Commits).
2. **`JustChr#164` beobachten** — bei Reviewwunsch nachziehen; die Zeile in
   `installation-download.md` ist im PR-Body ausdruecklich zum Streichen angeboten.
3. **Nach A+B:** Detektionsantwort auf `JustChr#160` (Text-Rohfassung:
   `D:/Entwicklung/HASI/issue22-work/comment-issue22.md`, Detektionsteil wurde herausgenommen —
   die lange Fassung steht im Spec unter D4 und in der Workflow-Auswertung).
4. **Danach (C):** eigener PR, Laufzeit-Check `datetime.now().astimezone().utcoffset()` gegen
   `dt_util.now().utcoffset()`.
5. **Offen aus frueheren Sitzungen:** `JustChr#162` + `JustChr#163` warten auf Review.

### Revision — Umsetzungsversuch gelaufen, auf JustChr wartend

- **Task 1 committet und gruen** (`c17a8111`): `helpers.as_stored_aware` + `_process_timezone`,
  5 Tests. **Pin aus Task 2 gruen** (`TypeError` --> `1/24`).
- **Task 3 NICHT fertig**, liegt als ausdruecklich markierter WIP (`c9720a72`). Tasks 4-8 offen.
- **Der Plan war unvollstaendig: es gibt ZWEI naive Herkuenfte**, mit entgegengesetzter
  richtiger Deutung. Store-Stempel = prozess-lokal; Wetter-Client-/Forecast-Zeilen
  (`_rows_since` :880, `_projected_extremes` :599) = HA-lokal. Details in Spec Revision 2.
- **Warum es lange nach Testalterung aussah:** `_intraday_for_zone` verschluckt jede Exception
  (`live_estimate.py:1213-1218`, DEBUG + `REASON_FAILED`). **222 verschluckte `TypeError` in
  einer Testdatei**, gemeldet als `Obtained: None`. Diagnose nur mit `exc_info=True`.
- **Umfangszahl war zur Haelfte mein Rechner:** 193 neue Fehlschlaege mit Prozess auf MESZ,
  **98** mit auf UTC gezwungener Prozesszone. Baseline `upstream/master`: 7 failed / 3191 passed
  / 320 errors (Windows, vorbestehend). 72 der 98 in drei `live_estimate`-Dateien.
- **Befund an JustChr gemeldet**, mit Schnitt-Frage:
  [issuecomment-5766722593](https://github.com/JustChr/HAsmartirrigation/issues/160#issuecomment-5766722593).
  Empfehlung: erst ein verhaltensneutraler PR, der die Eingaenge total macht, dann der Flip.
  **Antwort steht aus — vor ihr wird nicht weitergebaut.**
- **`JustChr#164` (Doku) ist CI-gruen**, alle vier Checks.
- Spec Revision 2 archiviert: `archive/design-history` = `e44792f7`.
- Baseline-Worktree wieder entfernt.

### Empfohlene Skills
- `superpowers:executing-plans` bzw. `superpowers:subagent-driven-development`,
  `superpowers:test-driven-development`, `superpowers:verification-before-completion`
- Fuer den PR: `pr-workflow`, Memory `hasi-pr-build-recipe`; Kommentierung: Regel P2
- Test-Env: Memory `hasi-local-test-env-rebuild`

---


## 2026-09-21 (3) — zwei Upstream-PRs offen, Querverweis-Panne bereinigt

### Stand (verifiziert)
- **`JustChr#162`** (PR A, Observed-Doppelgutschrift) eroeffnet, CI 4/4 gruen, noch kein Review.
  Unser Issue dazu: `Eifel-Joe#1`.
- **`JustChr#163`** (Observed-Sperre nach Neustart) eroeffnet aus `fix/observed-lock-after-restart`,
  vier Commits auf `upstream/master` = `965a4f9d`, **PR-Diff 6 Dateien, +232/-1**, kein `docs/`,
  kein Frontend. Unser Issue dazu: `Eifel-Joe#23`, bleibt offen bis der PR schliesst.
  Belege: Suite 3191 --> **3196 passed** bei `diff`-identischen 327 FAILED-/ERROR-Namen;
  `black --check` 68 unveraendert, `ruff` gruen; **Mutationsproben 5 / 5 gefangen / 0 ueberlebt**.
  Spec, Plan und Nachtrag: `archive/design-history` @ `05c43936` (gepusht).
- **Nachmessung zu `Eifel-Joe#23` gefahren** und dabei das eigene Messinstrument widerlegt: das Skript
  aus dem Issue baut den Zustand von Hand und ruft den Resume-Pfad nie, meldet also auch gegen den
  gefixten Stand "weiter offen". Ersetzt durch den Ende-zu-Ende-Test
  `test_after_a_resume_the_observer_stays_silent_in_the_old_gap`. Spec Abschnitt 7 korrigiert.
- **Querverweise aus altmenorgs `altmen#161` entfernt** (User-Auftrag). Ein Verweis laesst sich nur
  durch Loeschen der Quelle tilgen — Editieren des Bodies reicht nicht, auf 5-->4 am eigenen Repo
  nachgewiesen. `Eifel-Joe#12` geloescht, das Tracking-Issue neu als **`Eifel-Joe#42`** angelegt,
  12 Dateiverweise + 1 Issue-Body nachgezogen. Ergebnis: **0 Verweise von uns** auf `altmen#161`.
  Die drei Verweise auf `JustChr#159/#160/#162` bleiben stehen (User-Entscheidung).

### Verworfen
- **Die Schliessen-Flanke als Ort des PR-A-Fixes.** Das Praedikat ist in **beide** Richtungen falsch,
  je nachdem ob das Ventil vor oder nach `dispatch + run_seconds + 30` schliesst.
- **`_watch_start` als einziger Fixpunkt fuer `Eifel-Joe#23`.** Die Signatur kennt `elapsed` nicht, und
  sie laeuft auch auf dem Normalpfad, wo der Marker bereits korrekt steht.
- **`max(0.0, planned - elapsed)`.** Ueberdehnt das Fenster um bis zu 35 s; Mutationsprobe M3 faengt es.

### Fallen
- **`git stash -- <datei>` bewirkt nichts, wenn der Fix committet ist.** Der erste RED-Versuch fuer den
  Ende-zu-Ende-Test lief deshalb gruen und waere beinahe als Beleg durchgegangen.
- **`npm_config_cache` mit Windows-Pfad wird unter MSYS als relativ gelesen** — 33 MB landeten in
  `frontend/EntwicklungHASIprA-npm-cache/`. Untracked, nie committet, entfernt.
- **`gh release create --target` nimmt keinen Kurz-SHA**, nur die vollen 40 Zeichen.
- **Zahlen aus dem eigenen Nachtrag gegenlesen:** dort stand `+179/-1`, gemessen sind `+232/-1`.
- **Das Label zum Upstream-PR vergessen.** `upstream:gemeldet` fehlte auf `Eifel-Joe#23`, der User
  fand es. Nachgesetzt; Pflicht jetzt in Regel P2 und im Memory `hasi-todo-file`. Vollpruefung
  ueber alle 41 Issues: sonst nichts offen. Ohne `groesse:` sind `Eifel-Joe#24`-`#31` — die
  Quellzeilen `➂`-`➈` hatten nie eine, **bewusst so gelassen** (User 21.09.). Ohne `schwere:`
  sind die Feature-Issues `#34`-`#40`, folgerichtig. Bei JustChr haben wir kein Label-Recht.

### Naechste Schritte
- Reviews abwarten: `JustChr#162` und `JustChr#163`.
- `Eifel-Joe#21` (`JustChr#159`, Prognose-Gewichtung) und `Eifel-Joe#22` (`JustChr#160`, Zeitzonen-Naht)
  — beide "yours to build"; bei `#160` wartet JustChr auf **unser Urteil** zur TZ-Wechsel-Annahme.
- Aufraeumen: lokale Branches `dry2`–`dry7`, `tmp/*`, `rebuild/v2026.09.18b2`, `backup/*`,
  11 gemergte `fix/*`, Worktree `pr139-work/dry2`.
- HA-Test laeuft auf Pre-Release **v2026.09.21b1**; `observed_watering_enabled` bewusst **an**,
  Zaehler Zone 1 bei 55,28 L (Reset abgelehnt, weil der Knopf auch den Verlauf loescht).

### Empfohlene Skills
- `superpowers:receiving-code-review` sobald JustChr antwortet.
- `task-loop` fuer `Eifel-Joe#21` / `Eifel-Joe#22`.


## 2026-09-21 (2) — PR A gebaut, Fehler auf HA-Test feldbelegt, nichts gepusht

### Stand (verifiziert)
- **PR A ist fertig gebaut**, Branch `fix/observed-credit-si-takeover` von `upstream/master` = `965a4f9d`,
  vier Commits: `d1e6c9d6` (Marker verwerfen), `42dc9edb` (Sampler abbrechen), `a85aaccb` (Docstring),
  `582a0e02` (Test-Nachtrag aus der Mutationsprobe). **PR-Diff = 3 Dateien**, kein `docs/`, kein Frontend,
  kein `dist`. Spec und Plan: `docs/superpowers/specs/` bzw. `plans/2026-09-21-observed-double-credit.md`.
- **Belege:** Suite 3191 → **3196 passed** bei `diff`-identischen 327 FAILED-/ERROR-Namen
  (`prA-work/baseline-names.txt` gegen `final-names.txt`); `black --check` 68 unverändert, `ruff` grün;
  Mutationsproben **5 / 4 gefangen / 1 äquivalent / 0 unerklärt** (`prA-work/mutations.md`).
- **✅ Vorher-Messung auf HA-Test gefahren — der Fehler ist reproduziert.** Zone 1 „Beet", Fenster 214,14 s:
  Verbrauchszähler 33,0 → **51,27598833 L**, echtes Wasser 14,27598833 L, Differenz **exakt 4,000000 L** =
  die 60 s des SI-Laufs doppelt. Zwei Verlaufseinträge (`manual` 60 s/4 L, `observed` 214 s/14,28 L), dazu
  die Observer-Logzeile. Vollständig in der Spec, Abschnitt 9 — hier nicht doppeln.
- **Design-Historie lokal** auf `archive/design-history` @ `b73b6bb6` (zwei Commits). **Nicht gepusht.**
- **PR-Body fertig** in `prA-work/pr-body.md`. **Nicht freigegeben, nicht gepusht, kein PR eröffnet.**
- **HA-Test hinterlassen:** `observed_watering_enabled` bleibt **an** (für die Nachher-Messung), Log-Pegel
  zurück auf `warning`, Ventil und Master-Pumpe aus. Zone 1 steht auf 51,28 L — **Reset-Entscheidung offen**.

### Die Aufgabenliste ist umgezogen (21.09., User-Entscheidung)

**Kanonisch sind ab jetzt die Issues in `Eifel-Joe/HAsmartirrigation`** — 40 Stück, Einstiegspunkt das
angepinnte **`Eifel-Joe#42`** (Reihenfolge, Abhängigkeiten, Konventionen). Grund: die ToDo war nur über
Claude lesbar, und die Inventur vom 21.09. brauchte sieben Agenten, um überhaupt festzustellen, was offen
ist — sie fand zwei längst erledigte und zwei falsch einsortierte Punkte.

- **Form:** Englisch oben, Deutsch darunter (nicht eingeklappt). **Titel bleiben englisch** (User-Entscheidung):
  zweisprachige Titel lägen bei 170–200 Zeichen und machten die Liste zwei- bis dreizeilig pro Eintrag; der
  deutsche Überblick läuft einzeilig über `Eifel-Joe#42`.
- **Jeder Body nennt die frühere Bezeichnung** (`PR A`–`T`, `N1`–`N7`, `Befund 1`–`9`, `F1`–`F5`, `➀`–`⑪`),
  sonst wären `SESSION-STAND.md`, die Memories und `archive/design-history` nicht mehr auflösbar.
- **Zitierkonvention:** immer `Eifel-Joe#4` bzw. `JustChr#162`, nie eine nackte Raute — unser Zähler beginnt
  bei 1 und wächst in JustChrs Bereich hinein.
- **Pflegepflicht** (der Zweck der Umstellung): JustChrs Einwände am verlinkten PR/Issue kommen als
  Kommentar ins zugehörige Issue, in seinen Worten; schließt der Upstream-Bezug, schließt unseres mit;
  Reste bekommen ein **neues** Issue. Steht in `Eifel-Joe#42`, in der Projekt-`CLAUDE.md` als **Regel P2**
  und im Memory `hasi-todo-file`.
- `ToDo.md` ist von 386 auf 301 Zeilen geschrumpft und trägt nur noch Sitzungsstände; Sicherung der alten
  Fassung: `prA-work/ToDo.md.bak-vor-issues`.
- **Qualitätssicherung der Migration:** die 26 Bodies der Welle 2 entstanden per Workflow und wurden
  **mechanisch** geprüft — jeder Backtick-Bezeichner und jede `datei:zeile` aus der Quelle muss in beiden
  Sprachen vorkommen. 1 Beanstandung von 26. Vom Gegenprüfer gemeldete acht wurden einzeln geprüft, vier
  zurückgewiesen (er hielt ein Datum für erfunden, das in der Abschnittsüberschrift stand).

### Verworfen
- **Prädikat an der Schließen-Flanke.** In beide Richtungen falsch, getrennt davon, ob das Ventil vor oder
  nach `dispatch + run_seconds + 30` zugeht. Begründung mit Zahlen in der Spec, Abschnitt 3, Option 1.
- **Neu-Scharfstellen am Laufende.** Fünf Laufende-Stellen, braucht beide Hälften der Öffnen-Flanke, offene
  Frage zur Verlaufslogik → bewusst raus, als ToDo ➉ gewichtet vermerkt.
- **Der Eimer als Messwert der Feldmessung.** Hätte „kein Fehler" gemeldet — siehe Fallen.
- **Der Panel-Knopf „Jetzt bewässern" als Test-Trigger.** Filtert auf `ZONE_DURATION > 0`, und dieses Feld
  setzt die wetterabhängige Rechnung. Auf HA-Test standen die geplanten Läufe durchgehend auf
  `skipped/precipitation` bei Eimer 0.

### Fallen
- **Der Eimer maskiert Doppelgutschriften.** Jeder Gutschriftpfad schreibt ihn **absolut**
  (`async_write_watered_bucket`), der zuletzt schreibende gewinnt; am 21.09. nahm der Läufer die
  Observed-Gutschrift 8 ms später wieder zurück. Additiv und ungeklemmt ist nur `water_used_total`.
- **`custom_components/**` ist per MCP nur LESBAR.** Ein Fix lässt sich auf HA-Test nicht einspielen; auch
  `observed_watering_enabled` und `observed_entity` gehen nur über die HTTP-Views des Panels. Details im
  Memory `hasi-livetest-capability-boundary`.
- **`button.*_reset_usage` leert auch den kompletten Verlauf der Zone**, nicht nur den Zähler.
- **HA-Test hinkt upstream hinterher.** Installierter Stand vom 2026-09-20 vormittags, also **vor** #153
  und #157. Einzelne Dateien zwischen Branch und Instanz zu kopieren ist deshalb nicht sicher — die
  Importe passen nicht mehr zusammen.
- ⚠️ **Der Diagnostics-/Options-Dump enthält den Wetter-API-Schlüssel im Klartext.** Nicht in Issues,
  Logs oder Anhänge kopieren. (Wert absichtlich hier nicht genannt.)
- **Agenten-Zeilenangaben nachlesen.** Über beide Workflows 149 Urteile, 0 kassierte Aussagen, aber **19
  teilweise** — fast durchweg Zeilenversatz von 1 bis 13 Zeilen. Drei aus der ersten Runde übernommene
  Verweise waren in der Spec falsch und wurden korrigiert.
- **Dingbat-Codepoints:** ➈ ist U+2788, ➉ ist U+2789. Eine Ersetzung mit U+2789 für ➈ greift stillschweigend
  nicht (der Assert fing es ab).
- **`docs/superpowers/` und `docs/SESSION-STAND.md` sind untracked UND nicht gitignored** und liegen im
  Jekyll-`docs/`-Ordner, der nach upstream geht. Gezielt stagen, nie `git add .`.

### Nächste Schritte

**Reihenfolge: erst Live-Test auf HA-Test, dann PR.** So lief es bei #139 und #146, und `task-loop` stellt
den Live-Test vor „fertig". Eine frühere Notiz dieser Sitzung schlug die umgekehrte Reihenfolge vor — die
ist zurückgezogen.

✅ **Schritte 1–3 sind am 21.09. erledigt:** Zähler bleibt stehen (User-Entscheidung, der Reset-Knopf
hätte den Verlauf mitgelöscht); `production` auf `upstream/master` neu gebaut (**0 behind**, der frühere
Stand war 1 behind — vom User bemerkt), Pre-Release **v2026.09.21b1** gepusht und per HACS auf HA-Test
installiert, Neustart, Manifest verifiziert; **Nachher-Messung gefahren und grün** (Spec, Abschnitt 9.2).
Offen ist nur noch der Upstream-PR.

1. ~~Zähler-Reset entscheiden~~ — erledigt, bleibt stehen.
2. **Fix auf HA-Test bringen.** Per MCP geht es **nicht** (`custom_components/**` nur lesbar). Zwei Wege,
   beide freigabepflichtig, danach jeweils HA-Neustart (Memory `ha-no-auto-restart`):
   (a) **Pre-Release auf `production` bauen und per HACS ziehen** — das Rezept von #146, Memory
   `hasi-production-on-upstream`; kostet einen `--force-with-lease`-Push und ein GitHub-Release.
   (b) **Den GANZEN Ordner** `custom_components/irrigation_plus/` vom PR-Branch kopieren.
   ⛔ **NICHT nur `irrigation.py` kopieren.** Am 21.09. geprüft: HA-Test läuft einen Stand vom 20.09.
   vormittags, dessen `run_window.py` `zone_confirm_seconds` definiert, aber **kein**
   `zone_non_water_seconds` (das kam mit #157 am 20.09. abends). Der PR-Branch importiert genau dieses
   Symbol → `ImportError` beim Laden, Integration tot.
3. **Nachher-Messung**, identischer Ablauf zur Vorher-Messung (Spec, Abschnitt 9). Erwartung:
   `water_used_total` **+14,28 L statt +18,28 L** und **ein** Verlaufseintrag statt zwei. Ergebnis in den
   PR-Body, der Absatz „I have not yet measured the fixed build" wird dadurch ersetzt.
4. ~~ToDo-Punkt ➀ nachmessen~~ — ✅ **erledigt 21.09., Ergebnis: WEITER OFFEN** (`Eifel-Joe#23`, [Kommentar](https://github.com/Eifel-Joe/HAsmartirrigation/issues/23#issuecomment-5762950614)). Gegen den gefixten Branch gemessen: der Fix hängt am Dispatch, hier findet keiner statt. Restdifferenz `30 − grace` wie vorhergesagt — **+21 s** bei Vorgabewerten, +25 s bei Marge 0, **+30 s** ohne `confirm_entity`, 0 s bei Marge 25, −5 s bei Marge 30. Erreichbarkeit reproduziert: Datensatz `planned + 10 s` alt → `zone_run_in_flight` False, beide Marker leer, Beobachter stellt sich scharf, Schließen-Flanke plant die Gutschrift. Fix wäre ein Einzeiler im Resume-Pfad.
5. ~~PR eröffnen~~ — ✅ **erledigt 21.09.: [JustChr#162](https://github.com/JustChr/HAsmartirrigation/pull/162)**,
   MERGEABLE, 3 Dateien, +157/−11. Branch und `archive/design-history` (@ `afca8ef9`) sind gepusht.
   PR-Body trägt beide Messungen. **Jetzt: JustChrs Review abwarten.** Nachbesserungen als neue Commits,
   **kein Rebase** auf dem gepushten Branch.
   ⚠️ Im PR-Body steht bewusst **keine Fork-Versionsnummer** (User-Entscheidung 21.09.): der Testbuild wird
   nur funktional benannt („a pre-release built from this branch on top of `upstream/master`"), weil unser
   `vYYYY.MM.NN` mit JustChrs identischem Schema kollidiert und mit dem Fix nichts zu tun hat.
6. Danach **PR B** (Kette F1+F4+F3) aus der Arbeitsreihenfolge, `ToDo.md` ab Zeile 59.

### Empfohlene Skills
- `pr-workflow` + Memory `hasi-pr-build-recipe` für Push und PR.
- `superpowers:verification-before-completion` vor jedem „fertig".
- Für PR B wieder `superpowers:brainstorming` → `writing-plans` → `test-driven-development`.


## 2026-09-21 — Befunde geprüft, drei gemeldet, #149 diagnostiziert, v2026.09.20 released, Liste neu sortiert

### Stand (verifiziert)
- **Release [v2026.09.20](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.09.20) draußen.**
  `production` = `40163afc`, **0 behind / 1 ahead** auf upstream v2026.09.21. **Fork-Delta erstmals wieder
  NUR Branding.** Belege und Rezept-Fallen stehen in Memory `hasi-production-on-upstream` — hier nicht doppeln.
  ⚠️ **HA-Prod-Update macht der User selbst** (ausdrücklich, 21.09.). Der Release bringt der Anlage vor
  allem `78f9ce2c` (#149), das war in keinem bisherigen Build.
- **Fünf eigene PRs gemergt** (#153/#154/#155/#156/#157). Patch-Vergleich gemacht: JustChr hat an unserer
  Arbeit nichts geändert. **#147 ist zu — der Feature-Stopp ist aufgehoben.**
- **Drei Meldungen offen:** [#158](https://github.com/JustChr/HAsmartirrigation/issues/158) Solrad-Default,
  [#159](https://github.com/JustChr/HAsmartirrigation/issues/159) Vorhersage-Gewichtung,
  [#160](https://github.com/JustChr/HAsmartirrigation/issues/160) Zeitzonen-Naht. Noch keine Antwort.
- **[#149](https://github.com/JustChr/HAsmartirrigation/issues/149) beantwortet** — Formel selbst
  nachgerechnet (`gutgeschrieben = echter Regen + Σ Zählerstand vor jedem Reset`), Gegenprobe auf HA-Prod
  gemessen. Offen: Megalos' Gegenprobe an seinem Graphen.
- **Die Aufgabenliste ist neu gebaut.** `ToDo.md` ab Zeile 59, Abschnitt **„🎯 Arbeitsreihenfolge —
  verbindlich ab 2026-09-21"**: 18 Arbeitseinheiten A–R plus Politur und Features, nach Schwere, mit
  Abhängigkeiten. **Das ist der Einstiegspunkt der Folgesitzung.** Grundlage: Inventur aller 35 offenen
  Punkte (2 erledigt, 1 teilweise) und eine Bündel-Prüfung (8 vorgeschlagen, **5 gefallen**, 3 halten).

### Verworfen
- **Verdacht gegen unser eigenes `78f9ce2c`** (Regression durch den Strip): vom Gegenprüfer kassiert —
  `tests/test_source_leak.py:111-118` nagelt „unlesbare Quelle → Feld fehlt" als **gewolltes** Ergebnis fest.
  Wäre eine Fehlmeldung über einen gerade veröffentlichten Release gewesen.
- **`store.py:1255` (`Current Precipitation` bekommt `{}`)** als Leck-Pfad: korrektes Verhalten, leeres Dict
  heißt „nie konfiguriert", dann IST der Wetterdienst die legitime Quelle.
- **Vier `manual_*`-Felder in `Config`** als „verlorene Einstellungen": es sind **tote Felder**. Die
  Koordinaten leben in den Config-Entry-Options (`__init__.py:850-855`). In die Ladeliste aufnehmen wäre
  **schädlich** (zweite konkurrierende Wahrheit) → löschen.
- **Fünf Bündel-Vorschläge**, jeder mit dem Alternativschnitt in der ToDo dokumentiert.

### Fallen
- **`docs/SESSION-STAND.md` ist untracked UND nicht gitignored**, im Jekyll-`docs/`-Ordner, der nach
  upstream geht. `git add .` trägt die Notizen in einen Upstream-PR. Gezielt stagen.
- **Heredocs fressen eine Backslash-Ebene.** `python - <<'EOF'` mit `D:\\…` kam als `D:\…` an, `\b` wurde
  zum Backspace-Steuerzeichen und landete in der Datei. Für Pfade in Heredocs **Vorwärtsschrägstriche**
  nehmen; lange Texte lieber per Write-Tool in eine Datei und dann splicen.
- **Agentenzahlen nie ungeprüft übernehmen** (bestätigt Memory `workflow-agent-hygiene`): die ET-Zahlen zu
  #158 wichen ~3 Prozentpunkte von der eigenen Messung ab. Belastbarer Anker war der analytisch
  herleitbare Gleichstand bei dT = 16,5 K.
- **Die Gegenprüfer-Linse zahlt sich aus.** In dieser Sitzung hat sie drei Fehlmeldungen verhindert und
  fünf von acht Bündeln gekippt — darunter drei, deren tragende Belege am Code schlicht falsch waren.
- **Branch-Diffs gegen einen späteren master-Commit sind wertlos** (verschiedene Basen). Für den
  Squash-Vergleich beide Patches gegen ihre eigene `merge-base` erzeugen und die Patches diffen.
- **Hauptbaum steht auf `rebuild/v2026.09.20`**, nicht auf `production` (gleicher Commit `40163afc`).

### Nächste Schritte
1. **PR A — Observed-Doppelgutschrift** (hoch, M, auf Prod scharf). Fixort geklärt: `_note_si_valve`
   (`irrigation.py:115-131`) verwirft `_observed_on_since[zone_id]` und ruft `_observed_cancel_meter` —
   deckt alle acht Dispatch-Pfade. **Zwei Fallen** stehen in der ToDo-Tabelle (Prädikat nicht kopieren;
   SI-Lauf kann früher enden als das externe Ventil). Danach Punkt ➀ **nachmessen**, nicht abhaken.
2. Dann B (Kette F1+F4+F3), C1 → C2, D, E — Reihenfolge und Fallen in der ToDo-Tabelle.
3. Offen aus #98: Frontend-Warnung („still yours if you want it") und zwei Feldmessungen.
4. **Aufräumen, wenn die #139-Historie nicht mehr gegengelesen wird:** Worktrees `befunde-work/base`,
   `pr139-work/dry2`, `pr139-work/archive-wt`; Branches `dry2`–`dry7`, `backup/*`, die gemergten `fix/*`.

### Empfohlene Skills
- `superpowers:brainstorming` → `superpowers:writing-plans` → `superpowers:test-driven-development` für PR A.
- `pr-workflow` + Memory `hasi-pr-build-recipe` für den Upstream-PR; Regel P1 (Design-Historie) beachten.


## 2026-09-20 — #139: PR #150 offen, live nachgemessen, zwei Folge-Issues

### Stand (verifiziert)
- **[PR #150](https://github.com/JustChr/HAsmartirrigation/pull/150)** offen, Branch `fix/backstop-grace`,
  17 Commits, `29 files changed, +4178/-842`. Nach dem Merge von `upstream/master` (v2026.09.17):
  **MERGEABLE / CLEAN**, alle fünf CI-Checks grün (build, lint, validate, test 3.13, test-ha-floor).
- **Umfang** wie am 19.09. vereinbart; T3b auf JustChrs Antwort vom 19.09. ebenfalls gestrichen.
  Sechs Nacharbeiten aus dem eigenen Review als C1–C6 im PR (C3/C5 = Raten-Fluss-Schnitt am Aus-Bericht,
  ein Loch, das erst der Zuschlag öffnet).
- **Belege:** Suite `7 failed, 3121 passed, 9 skipped, 320 errors` (3137 gesammelt; Namen identisch mit
  master), 111 neue Testfunktionen (eine über 5 Fälle parametrisiert = 115 Items), vitest 616 → 624,
  `dist` reproduzierbar. **Mutationsproben 155 / 150 gefangen / 5 äquivalent / 0 Überlebende**; ohne
  tötende Probe nur der i18n-Hilfetext-Pin (gewollt).
- **Faktenprüfung vor dem PR** (8 Gruppen gegen den Branch, jeder Verdacht von 3 Skeptikern gegengelesen):
  1 bestätigter Fund (Katalogzahl im Kommentarentwurf), 5 abgewiesen. Selbst gefunden und korrigiert:
  die 4-s-Vorgabe behauptete 1,1 s Reserve, real sind es **0,78 s** (Nachmessung 3,22 s liegt über der
  Zehn-Tage-Spanne 2,08–2,90 s).
- **Live:** HA-Test 9 Szenarien gegen `grace_emu_*`, getrieben von einem Skript **auf der Instanz**;
  HA-Prod je ein kurzer Handlauf: Kirschlorbeer 60,001 s offen → Abschluss +5,009 s → `actual_s` 60;
  Beet 63,222 s offen → +5,004 s → **`actual_s` 63** (vorher 60). Der Wächterpfad war auf dieser Anlage
  vorher unerreichbar. **Nicht belegt auf Prod:** der Raten-Fluss-Schnitt (Kirschlorbeer zählt `per_run`,
  Beet hat keinen Sensor) — im PR benannt.
- **Zwei Folge-Issues angelegt:** [#151](https://github.com/JustChr/HAsmartirrigation/issues/151)
  Fensterbepreisung (mit den drei Selbstkorrekturen meiner 15.09.-Beschreibung),
  [#152](https://github.com/JustChr/HAsmartirrigation/issues/152) Master-Lücke nach Neustart
  (vorbestehend, vom PR unverändert) — beide auf #150 verlinkt.
- **JustChr 20.09.:** hat seine Zusage vom 19.09. widerrufen und **v2026.09.17 ohne diesen PR als Stable**
  ausgeliefert; der PR eröffnet die nächste Beta-Kette. Nichts soll gehetzt werden. Sein Heads-up nannte
  „sixteen catalogue files" — im #139-Kommentar auf **acht** korrigiert (Backend-Katalog hat keinen
  Zonenfeld-Abschnitt, sein eigener Befund vom 15.09.; #125 hat exakt dieselben acht angefasst).
- **Design-Historie gepusht** (Regel P1): `origin/archive/design-history` @ `f6b7e595`, 6 Commits, inkl.
  Umsetzungsnachtrag im Plan und beider Review-Runden in der Spec.

### Nächste Schritte
1. CI auf #150 und JustChrs Review abwarten.
2. Nach einem Merge: Produktiv-Rebuild auf upstream, Pre-Release-Stand ablösen.
3. Aufräumen: `dry2`–`dry7`, `tmp/*`, `rebuild/v2026.09.18b2`, `backup/fix-backstop-grace-premerge`,
   Worktrees `pr139-work/dry2` und `pr139-work/archive-wt` — erst wenn die Historie nicht mehr
   gegengelesen wird (Archiv zitiert die `dry`-SHAs).

### Fallen
- Der Merge-Commit-Konflikt kam **nur** von der Versionszeichenkette in den vier `dist`-Bundles.
  Generierte Dateien nicht von Hand mergen: neu bauen und stagen (`git add -f`).
- Kein Rebase auf dem schon gepushten PR-Branch — Merge, JustChr squasht beim Merge ohnehin.


## 2026-09-19 — #139: JustChrs Umfangsantwort verarbeitet, Probelauf der Änderungen

### Stand (verifiziert)
- **JustChrs Antwort** vom 16.09. ([issuecomment-5692654650](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5692654650)), Regel: Ein Commit gehört in den Fix, wenn er eine Lücke schließt, die erst die Wartezeit öffnet. DRIN: Start ab Ein-Meldung + Toleranz max(1 s, Marge), In-flight (T9), T3b, T7. RAUS: T6 (Backstop mit gespeicherter Aus-Meldung), T10 (Zeitfenster-Preis, eigenes Issue nach stable). Marge 4 s angenommen.
- **Workflow `wf_969540fa-c34`** (Ergebnis `pr139-work\wf-scope-answer.json`): T6+T10 in `dry2` gestrichen → Branch `tmp/drop-6-10` @ `361b52f7`; black/ruff grün; 7 Service-Suiten `222 passed, 1 error`; volle Suite `7 failed, 2987 passed, 320 errors` (zweimal), FAILED/ERROR-Namen identisch mit `baseline-0b418644.txt`. Schwester-Pfad-Prüfung (10 Funde, je 2 Gegenprüfer) und Mutationsprüfung In-flight (überlebt: Anker `RUN_VALVE_ON`, `<` → `<=`; kein Test für den zweiten Dispatch in der Wartezeit).
- **User-Entscheidungen 19.09.** (alle Empfehlungen): (a) Neustart nach der Wartezeit mit gespeicherter Aus-Meldung → `planned_s`; (b) Fensterregel nur mit gespeicherter Aus-Meldung, sonst Basis-Regel (ändert E4); (c) Stopp vor dem Planende ignoriert die gespeicherte Aus-Meldung; (d) Stopp in der Wartezeit rechnet nach der Watcher-Regel ab (completed innerhalb der Toleranz); (e) T3b mit T9 überflüssig → JustChr korrigieren, Streichen vorschlagen; (f) Neustart in der Wartezeit holt den Master nicht neu (upstream gibt beim überfälligen Neustart schon heute ohne Holen frei, `master.py` `async_master_release`).
- **Gepostet (Freigabe „mach weiter“ 19.09.):** [issuecomment-5740280769](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5740280769) aus `pr139-work\comment-139-answer.md` — kündigt a–d, f und die T9-Tests an, schlägt das Streichen von T3b vor, korrigiert die Zahlen zu Punkt 1.
- **Probelauf läuft:** Workflow `wf_ec3b95ac-161`, `dry2` Branch `dry3/backstop-grace` (von `tmp/drop-6-10`), je Task ein Agent, der den Task-Commit an seiner Position ändert (`pr139-work\seqedit.py`), Belege in `pr139-work\dry3-logs\`. Reihenfolge: Texte → T5 (b) → T7 (c, d) → T8 (a, f, Test auf +602) → T9 (Dispatch-Tests) → Schluss (volle Suite, Einzelcommit-Prüfung, range-diff, Eventualfall „T3b gestrichen“).

- **JustChr 19.09. 07:55** ([issuecomment-5740329987](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5740329987)): T3b RAUS (PR-Text: Lücke unter einer Sekunde zwischen In-flight-Ende und Backstop als bekannt nennen), a–d, f, T9-Tests DRIN, Test „Master nicht angefordert“ ausdrücklich; der nächste stable wartet nur auf #139; **Nachmessung beider Zonen VOR dem Merge**. #146 gemergt 07:44 (`2b2c403b`).
- **Probelauf fertig:** `wf_ec3b95ac-161` (Ergebnis `pr139-work\wf-dry3.json`, Belege `pr139-work\dry3-logs\`), danach T3b gestrichen + Helfer eingefaltet (`dry4`), Rebase auf `2b2c403b` → **Referenzbranch `dry5/backstop-grace` @ `58d6b7b5`** (Worktree `pr139-work\dry2`). Basis 7/3006/320 (3022), dry5 7/3097/320 (3113), Namen identisch; vitest 616 → 624; black/ruff je Commit grün; dist byte-gleich reproduziert; Änderungszeilen identisch mit dem Stand auf 0b418644.
- **User 19.09.:** Umsetzung als **Nachvollzug** der dry5-Commits (je Task erst Tests → Rot, dann Code → Grün, gleiche Nachricht); Plan = kompakte Revision 3. Live-Test: HA-Test mit Emulator `grace_emu_*` (angelegt, belegt; voller HA-Test-Zugriff freigegeben; Testskript auf HA-Test statt MCP-Takt), dann Pre-Release auf HA-Prod + je Zone ein kurzer `run_zone` durch den User.
- **Spec/Plan Revision 3** wird geschrieben: Workflow `wf_9b839069-b13`, Ausgabe `pr139-work\rev3\` (spec.md, plan-*.md, evidence.md, pr-body-draft.md, issue-window-pricing.md).
- **Rev 3 fertig:** Referenzbranch `dry6/backstop-grace` @ `70dc0c18` (Worktree `pr139-work\dry2`; T3 Real-Timer-Test verpasster Schluss, T5 Pin späte Meldung → `planned_s`); volle Suite 7/3099/320 (3115), Namen = Basis `2b2c403b`; vitest 624; jede der 101 neuen Test-Items fällt an ≥ 1 Probe. Spec + Plan Revision 3 lokal auf `archive/design-history` @ `5658ef72` (4 Commits vor origin, nicht gepusht); Teile in `pr139-work
ev3\`, PR-Entwurf `rev3\pr-body-draft.md`, Issue-Entwurf `rev3\issue-window-pricing.md`. **Wartet auf Plan-Freigabe.**
### Nächste Schritte
1. (erledigt) Probelauf auswerten; dann Spec + Plan überarbeiten (Regel P1, `pr139-work\archive-wt`, lokal): T6/T10 als gestrichen markieren, T2/T3b/T5/T7/T8/T9/T13/T14 und Kopf neu, E3/E4 + neue Entscheidungen, PR-Text-Abschnitte („bewusst unverändert“ mit beiden Auslösern, Reichweite ergänzt, kein `actual_s <= planned_s`), Schritt für das Issue Zeitfenster-Preis (`pr139-work\issue-window-pricing.md`, Korrekturen aus dem Kommentar einarbeiten).
2. Plan-Freigabe durch den User, dann Umsetzung ab Task 0 auf `fix/backstop-grace`.
3. JustChrs Antwort zu T3b abwarten; streicht er, gilt der Eventualfall aus dem Probelauf.

### Fallen
- Mehrere Agenten im selben Worktree: Prüfer lasen `dry2`, während ein anderer mutierte (Zwischenzustand gesehen). Zahlen aus solchen Läufen vor Übernahme nachmessen (z. B. die +602/+604-Werte aus der Gegenprüfung).


## 2026-09-16 — #146 auf rollierendes 24-h-Fenster umgebaut, gepusht und beantwortet

### Stand (verifiziert)
- **Branch** `fix/rain-guard-run-date` @ `a205ce96`, **gepusht** (`30e48419..a205ce96`, Freigabe 16.09.). PR danach MERGEABLE. Über `upstream/master` (`0b418644`): PR-2-Commits + 2 Merges (`a4395b13`, `ef1ff65f`) + 15 Umbau-Commits (`13a9f501` … `a205ce96`).
- **Merge-Falle:** `f14ebbdd` ≠ `upstream/master` (Release-Commit `0b418644` bumpt Versionen + dist). Gelöst: `merge -s ours 8dbc0223`, dann normaler Merge `upstream/master` (konfliktfrei). JustChrs Rezept `-s ours origin/master` hätte den Versionsbump verloren → im Kommentar erwähnt.
- **Belege Endstand:** Suite 7 failed / **3006 passed** / 320 errors (master 2906), FAILED/ERROR-Namen identisch (`pr146-work\after-final.txt`); vitest 616; black/ruff grün; dist byte-identisch reproduziert (seit `e70184e5` kein Frontend-Commit mehr).
- **Mutationssatz auf `a205ce96`** (`pr146-work\mutate.py`, Ergebnisse `mutation-results.json`, Log `mutation-run.log`): 44/45 beißen; der eine Überlebende (Temperatur-Ziel hinter beiden Reichweiten) war schlecht gestellt, die schärfere Fassung beißt (`mutation-temperature.json`); „Kalendertage zurück" (JustChrs Wunsch) → 25 Tests fallen (`mutation-calendar.json`). Frontend-Proben (en-Revert → vitest, de-Kopie → i18n-Test) in Task 8.
- **Messungen Live-API 16.09.** (Schlüssel `pr146-work\secrets\`, außerhalb des Repos): Pirate Default ⌊F⌋+47 h, `extend=hourly` ⌊F⌋+167 h, 30 986 → 85 602 Byte; Tagesblock = Ortsmitternacht, 86400 s; Σ Stundenraten = `precipAccumulation×10`; Open-Meteo F−32 h … F+159 h. Rohdokumente `pr146-work\pirate-*.json`, `openmeteo.json`.
- **Abgesendet (Freigabe 16.09.):** PR-Titel „Examine rain from the run's start, not from the day after it", Body aus `pr146-work\pr-body-new.md`, [Kommentar](https://github.com/JustChr/HAsmartirrigation/pull/146#issuecomment-5701002859) aus `pr146-work\comment-146.md`. Alter Body gesichert `pr-body-old.md`.
- **Design-Historie gesichert** (User: nur #146): #146-Commit auf `origin/archive/design-history` umgesetzt + Umsetzungs-Nachtrag, gepusht `fca77ee5..8abfa6ca`. Lokaler Archiv-Branch (Worktree `pr139-work\archive-wt`) neu aufgebaut: origin + drei #139-Commits `0280abb5`/`0ddd8cb6`/`fbb535a5` (vorher `22dfaa12`/`895c9c7d`/`6421499e`), weiter ungepusht; der alte #146-Commit `3e76cf09` wurde nach Patch-ID-Gleichheit übersprungen.
- **Live-Test HA-Test ✅ (16.–19.09.):** Pre-Release [v2026.09.18b1](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.09.18b1) = `production` @ `d8eeb21b` (force-with-lease, Backup lokal `production-backup-v2026.09.17`). Galway, Pirate Weather: Abend-Dispatch 20:03 Fenster 1 → 3,17 mm übersprungen (alt 1,00 → gegossen), = Branch-Rechnung; 3 weitere Dispatches übersprungen; Fenster 3 → 2,41 mm vollständig, keine „covers only part"-Zeile; Gegenprobe Fenster 7 → Zeile da. Protokoll `D:\Entwicklung\HASI\pr146-work\live\ergebnis-livetest.md`. Debug-Logging zurückgesetzt. Ergebnis auf #146 gepostet ([issuecomment-5739763518](https://github.com/JustChr/HAsmartirrigation/pull/146#issuecomment-5739763518)). HA-Test zurückgestellt und geprüft (Heimkoordinaten, Fenster 1, Vorschau 0,00 mm; Wächter an, Pre-Release bleibt). Lokaler Rebuild-Zweig gelöscht (= production).

### Entscheidungen (User, 2026-09-16)
- Beide Härtungen: Pirate `extend=hourly` + Met-Office-Dokumentwahl per `covering_until` (JustChrs Wortlaut „when the hourly series ends before the window does").
- JustChrs Real-Client-Testdatei umgeformt übernommen (Pirate aus aufgezeichneter Antwort, `berlin`-Fixture lokal).
- Plan freigegeben, subagent-getrieben ausgeführt; Modelle gestaffelt (Memory `agent-model-tiering`).

### Verworfen
- Anteiliges Auffüllen / „Rest"-Variante: bricht `test_owm_s_last_day_starting_at_the_series_end_is_not_counted_again` (6,0 statt 3,0; falsch datierter Slot).
- Toleranz auf der Abdeckung: Lücke ist ein Band, Größe wäre geraten.
- Met-Office-Dokumente verschmelzen: `_hourly_segments` nimmt den kleinsten Abstand → Dreistundenwerte deckten nur 1 h.
- Mutationsläufe im Worktree: dort gewinnt `custom_components` aus `pytest_homeassistant_custom_component/testing_config` → Worktree-Code wird nicht importiert. Läufe im Hauptbaum (alles committet, Rücksetzen per Hash geprüft).

### Fallen
- Subagent läuft nur die Tests, die man nennt: Task 5 brach `test_hourly_temperature_forecast.py::…hourly_block` (URL-Schwanz nach `exclude=`), erst die volle Suite fand es → volle Suite gehört in JEDEN Task-Auftrag.
- Zwei Agenten starben mitten in Mutationsproben (Session-Limit, 401). Einer hinterließ eine **aktive Mutation** im Baum → vor Weiterarbeit immer `git diff` + `mut\*.bak`/`.sha` prüfen.
- Zwischenstand-Lesen: den Baum nicht lesen, während ein Agent mutiert (Fehlalarm „2 Tests rot").
- Prüfer-Agenten behaupten gern „Test läuft lokal nicht" — `.E` heißt: bestanden, Teardown-Fehler (Lingering timer, Vorbestand).
- Messbehauptungen: eine Nachstellung mit präpariertem Dokument ist keine Messung (Docstring korrigiert, `a205ce96`).

### Nächste Schritte
1. CI und JustChrs Review von #146 abwarten (PR an die Sitzung gebunden, Auto-Fix aus). Nachbesserungen als neue Commits, kein Rebase. Bei Änderungen am Code den Mutationssatz (`pr146-work\mutate.py`) im Hauptbaum erneut fahren.
2. #139-Commits auf dem Archiv-Branch bleiben lokal, bis #139 freigegeben ist; vor dem Löschen von `fix/backstop-grace` sichern (Regel P1).
3. Live-Test HA-Test (Open-Meteo, prüft nur die Fensterform) — eigene Freigabe.
4. Vorbestehende Befunde (ToDo.md, „Befunde aus dem #146-Umbau") nach JustChrs Antwort als Issues anbieten.
5. #139 bleibt zurückgestellt bis zur Antwort auf die Umfangsfrage.

---

## 2026-09-15/16 — #139 Backstop-Wartezeit: Spec + Plan (mit Probelauf), JustChr-Stand

### Stand (verifiziert)
- **Spec** `docs/superpowers/specs/2026-09-15-backstop-grace-design.md` und **Plan** `docs/superpowers/plans/2026-09-15-backstop-grace.md` liegen lokal auf `archive/design-history` (Worktree `D:\Entwicklung\HASI\pr139-work\archive-wt`), **nicht gepusht** (Push erst in Plan Task 14, Freigabe). Entscheidungen E1–E7 und alle Begründungen stehen in der Spec, nicht hier.
- **Arbeitsbranch** `fix/backstop-grace` = `upstream/master` `0b418644` (v2026.09.16), keine eigenen Commits. Arbeitsbaum: nur `?? docs/SESSION-STAND.md`.
- **Probelauf** (Wegwerf, lokal): `D:\Entwicklung\HASI\pr139-work\dry2`, Branch `dry2/backstop-grace` @ `67301a8b`, 13 Commits (T01–T12 + T03b). Suite gegen Basis `0b418644`: 7 failed / 2906 → **2993 passed** / 320 errors, FAILED/ERROR-Namen identisch (+87 Items); vitest 614 → 622; 109 Mutationsproben (101 gefangen, 8 äquivalent); Tasks 3b/6/7/10 einzeln und gemeinsam streichbar (konfliktfrei, grün). Messdateien `pr139-work\baseline-0b418644.txt`, `after-polish.txt`.
- **Kommentar auf #139** gepostet (Umfangsfrage, 4 abtrennbare Zusätze): [issuecomment-5685683675](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5685683675) — Antwort steht aus (Stand 16.09. Nacht).
- **Upstream:** #144/#145 gemergt, Beta v2026.09.16; #146 bekommt Umbau-Wunsch (rollierendes 24-h-Fenster + 48-h-Abdeckung), Issue #147 „nur Fixes“ — Details in `D:\Entwicklung\HASI\ToDo.md` „Stand 2026-09-16“.
- **HA-Test** Sonoff-Emulator vorhanden (MCP gelesen 15.09.). Pre-Release-Weg: `production` + `fix/backstop-grace` (bringt #144/#145 mit), #146 eigenes Pre-Release.
- Aufgeräumt: erster Probelauf (`dry-backend`, `dry-frontend`, Branches `dry/*`) entfernt; `dry2` bleibt bis zur Umsetzung als Referenz.

### Verworfen
- `actual_s` ab `RUN_STARTED` mit 1 s Toleranz: normale Kirschlorbeer-Enden würden Teil-Läufe (Recorder 13.09.).
- `RUN_VALVE_OFF` aus jedem Subscription-Ereignis: `unavailable → off` nach Neustart stempelt die Wiederkehr (Plan-Kritik, Major) → E6.
- Pre-Release „nur production + #139“: mit neuer Basis nur per Rückport-Variante möglich → #144/#145 mitnehmen.

### Fallen
- **C: voll** (29 MB): Temp/npm-Cache in allen Plan-Befehlsblöcken nach `D:\Entwicklung\HASI\pr139-work\tmp` / `npm-cache` umgeleitet. Ohne Platz können Windows/HA-Werkzeuge trotzdem scheitern.
- Commit-Nachrichten: Zeilen, die mit `#` beginnen (z. B. „#139 gives …“), löscht git beim Rebase/Fixup still als Kommentar → „Issue #139 …“.
- freezegun friert auch die Loop-Uhr: echte `async_call_later` nur im selben `freeze_time`-Block armieren und vorstellen.
- Worktree-Dateien sind CRLF: Mutationsproben mit Backup + SHA-256-Vergleich zurücksetzen; `git status` allein beweist nichts.
- #146-Merge: `merge -s ours upstream/master` würde die Release-Version zurückdrehen; `-s ours 8dbc0223`, dann normal mergen.

### Nächste Schritte
1. **#139 ist zurückgestellt** (User, 2026-09-16): keine Umsetzung, kein Push, keine Freigabe des Plans, bis JustChr auf die Umfangsfrage antwortet. Plan und Spec liegen fertig lokal auf `archive/design-history` (`6421499e`, `895c9c7d`).
2. **#146-Umbau ist der nächste Arbeitsschritt** (neue Sitzung): JustChrs zwei Kommentare vom 15.09. auf #146, Spec/Plan-Revision nach Regel P1 (`archive/design-history`: `…/2026-09-13-rain-guard-run-date*`), Merge wie unter Fallen.
3. JustChrs Antwort auf #139 abwarten; streicht er Zusätze, vor Plan Task 14 die Commits mit den geprüften Befehlen aus Task 13 Step 8 droppen.
4. **#139-Umsetzung** nach Plan (`superpowers:subagent-driven-development`), ab Task 0; Probelauf `dry2` als Referenz, danach aufräumen (Task 14 Step 8).
5. Danach Befunde aus `D:\Entwicklung\HASI\ToDo.md`.

### Empfohlene Skills
- #146: `superpowers:receiving-code-review`, `superpowers:writing-plans` (Revision), `superpowers:test-driven-development`, `pr-workflow` §6
- #139: `superpowers:subagent-driven-development`, `code-doku`, `superpowers:verification-before-completion`, `superpowers:finishing-a-development-branch`, `pr-workflow`

---

## 2026-09-15 (Fortsetzung) — PR 2 Umsetzung läuft

### Stand (Zwischenstand)

- vitest-Basis gemessen: 22 Dateien / 614 passed (`D:\Entwicklung\HASI\baseline-pr2-vitest.txt`), Node v24.15.0.
- Tasks 1–9 committed, jeweils mit Spec- und Qualitätsprüfung abgenommen, alle Mutationsproben gefangen. SHAs nach Autosquash (Met-Office-Docstring in Task 3):
  - `29bfa268` T1, `5522f5ad` T2, `214cd55c` T3, `b291a3d5` T4, `090b59dd` T5, `d36b7333` T6, `ad70a322` T7, `49a71895` T9
  - Beleg Autosquash 1: `git diff 9e2d1a9b 106b04e6` zeigt nur den neuen Met-Office-Docstring-Punkt; `test_forecast_window.py` 27 passed.
  - Beleg Autosquash 2: `git diff 106b04e6 49a71895` zeigt nur den `const.py`-Kommentar zur Gewichtung („Shares the look-ahead setting … counts it from the day after the calculation“).
- Schlussprüfung als Workflow `wf_f11fb27f-815` (6 Linsen, Dedupe, je 2 Gegenprüfer; nur lesend) läuft.
- Task 10 (am 2026-09-15 gegen `9e2d1a9b`): black/ruff grün; Suite 7 failed / 2906 → **2959 passed** / 320 errors, FAILED-Namen identisch; vitest 614 → 616; dist in sync; Geschwister-Checks wie erwartet; keine SHAs.
- Abweichungen vom Plan (Review-Fixes), erklären die +53 statt +49:
  - T2: Test „negativ/NaN“ geteilt (negative Rate war vom Loch nicht unterscheidbar) — +1
  - T3: Pin für leere Intervallliste (`bool(intervals)`-Wächter ungetestet) — +1
  - T6: **Verhaltensänderung über den Plan hinaus:** Entscheidung auf dem gerundeten Wert (`observed = round(mm, 2)`, `would_skip = observed >= threshold`). Grund: sekundenweise Integration ergab 10 h × 0,2 mm = 1,9999999999999998 → Chip „2,0 von 2,0 mm“, aber bewässert. Test parametrisiert — +2

### Entscheidungen (User, 2026-09-15 Fortsetzung)

- **Basis:** PR 2 wird auf #145 gestapelt geöffnet (gehört zusammen). `--base master`, im Text die neuen Commits benennen.
- **Met-Office-Hinweis** (angeschnittener letzter Tag) kommt in den Modul-Docstring von `forecast_window.py`, als Fixup in den Task-3-Commit (Autosquash, Branch ungepusht).
- Bis zum fertigen PR durchziehen; PR-Text und #137-Kommentar vor dem Absenden vorlegen.
- **Schlussprüfung** (`wf_f11fb27f-815`, 6 Linsen, 16 Befunde, je 2 Gegenprüfer): 9 bestätigt (alle klein: Ausblick nennt laufenden Lauf mit vergangenem Start, 5 Testlücken, 2 Doku-Formulierungen, Test-Docstring „checked on the install“), 2 User-Entscheidungen, 5 strittig/widerlegt (Rundung imperial ≤0,005 mm, überlappende Tageseinträge, Off-Grid-Stempel, 1-s-Toleranz, Teardown-Timer vorbestehend). Fixes laufen als Workflow `wf_384a26b0-657` (Fixup-Commits auf T3/T6/T7/T9).
- **Met Office Dokumentwahl (User):** Toleranz auf `min(Lebensdauer, 3 h)` deckeln. Grund: bei Tages-/Zweitages-Update gewann ein bis 24/48 h älteres Stundendokument, dessen 48-h-Reihe vor dem Laufdatum endet → Wächter entscheidet nicht, obwohl das Dreistundendokument abdeckt. Fixup auf T5 mit Tests (Grenze, cache_seconds, fehlender Zeitstempel, neueres Stundendokument).
- **48-h-Reichweite (User):** Pirate Weather und Met Office (Stundendokument) lassen bei Fenster ≥3 den letzten Fenstertag großteils unbedeckt (Beispiel 6,57 → 4,67 mm). Nur benennen: Docstring, PR-Text, #137. Kein `extend=hourly`.
- **JustChrs Bitte** (Pirate-Weather-Tages-`time` als „aus der API übernommen, nicht gemessen“ in den Docstring) war im Code nicht erfüllt → im Fix-Workflow (T3-Fixup).
- **Fix-Runde 1 fertig** (alle 4 Jobs geprüft und abgenommen, noch NICHT autosquasht): `747d856d` fixup T7 (Ausblick überspringt laufenden Lauf via `not_before`, Dispatch-Pin, exakte Jetzt-Pins; ein Alt-Test lief nach realem Datum → `freeze_time`), `03f3d7e4` fixup T6 (Teilfenster-Test 4,58 mm, DEBUG-Pin, Docstring ohne „install“/„HA-Prod“), `40cc97db` fixup T3 (Ein-Messwert-Pin, „nicht überlappend“, Pirate-Weather-Hinweis), `41ddeb5a` fixup T9 (Doku „starting with the day of the run“, „reaches or exceeds“).
- **Fix-Runde 2 läuft** (`wf_b3fd0755-89d`): Met Office 3-h-Deckel (fixup T5), 48-h-Grenze + älterer Pirate-Kommentar entschärft (fixup T3), `general_precipitation_threshold` „reaches or exceeds“ in 8 Sprachen + Pin + dist (fixup T9).
- **Fix-Runde 2 fertig** (3 Jobs abgenommen): Met Office `tolerance = min(lifetime, 3 h)` + 14 Tests, 48-h-Grenze im Docstring (präzisiert: am Laufdatum Tag 3, Vorschau am Vorabend ein paar Stunden von Tag 2), älterer Pirate-Kommentar entschärft, `general_precipitation_threshold` „reaches or exceeds“ in 8 Sprachen + Pytest-Pin (Schlüssel wird im Panel derzeit nirgends gerendert) + dist.
- **Endstand `30e48419`** (8 Commits nach Autosquash, `git diff` vorher/nachher jeweils leer): `29bfa268` T1, `5522f5ad` T2, `2851f25a` T3, `9c2d4175` T4, `766f8f12` T5, `58476c9c` T6, `4fdcca19` T7, `30e48419` T9.
- **Belege Endstand (2026-09-15):** Suite gegen `a8cb8167` (unterscheidet sich vom Endstand nur im 48-h-Docstring-Absatz): 7 failed / 2906 → **2976 passed** / 320 errors, FAILED-Namen identisch; +70 = 28+17+14+8+2+1 gesammelte Items. vitest 614 → 616. `npm run build` reproduziert dist. black/ruff grün. Keine privaten Verweise/SHAs in hinzugefügten Zeilen. `test_forecast_window.py` am Endstand 28 passed.
- **Abgesendet (User-Freigabe 2026-09-15):** Branch gepusht (`origin/fix/rain-guard-run-date` @ `30e48419`), [PR #146](https://github.com/JustChr/HAsmartirrigation/pull/146) geöffnet (gestapelt auf #145/#144, `--base master`), [Kommentar auf #137](https://github.com/JustChr/HAsmartirrigation/issues/137#issuecomment-5678306428) gepostet, Design-Historie `archive/design-history` @ `fca77ee5` gepusht (Spec-Nachtrag „Umsetzung und Schlussprüfung“, Plan-Kopf). Archiv-Worktree entfernt, keine `worktree-*`-Branches.

### Nächste Schritte

1. CI und Review von #146 abwarten (PR ist an die Sitzung gebunden, Auto-Fix aktiv). Nachbesserungen als neue Commits, kein Rebase (`pr-workflow` §6) — der Branch ist jetzt gepusht.
2. Nach dem Merge von #144 und #145: master in `fix/dated-daily-forecast` und danach in `fix/rain-guard-run-date` mergen, kein Rebase.
3. **Task 12 Live-Test** braucht eigene Freigabe: HA-Test (Open-Meteo) mit dem Branch bespielen oder bis zum Produktiv-Release warten; Kriterien im Plan (Hilfetext je Modus, Chip = Summe der Open-Meteo-Stundenwerte des Laufdatums ab Abfragezeit ±0,05 mm, keine Exception).
4. Danach #139 (Backstop-Marge, Spec + Plan nötig), dann die restlichen Befunde aus `D:\Entwicklung\HASI\ToDo.md`.

### Fallen dieser Runde

- **Fixup + Autosquash** funktioniert sauber, solange der Branch ungepusht ist; Beleg jedes Mal `git diff <vorher> <nachher>` leer. Bundle-Dateien können nach `npm run build` als ` M` erscheinen, obwohl bytegleich (veralteter Index-Stempel) → Rebase bricht sonst ab; SHA-256 vergleichen, dann `git restore --source=HEAD`.
- **Tests mit fest verdrahtetem Datum** kippen, sobald Code „vergangene“ Zeitpunkte filtert (`not_before`): `freeze_time` setzen.
- **Workflow-Prüfer liefern Zeilennummern aus älteren Ständen** — Befunde am Code nachprüfen (drei Fälle diese Runde).
- **Mutationsproben parallel zu anderen Agenten** im selben Baum verboten; Schlussprüfer nur lesend, Experimente unter `pr2-work/review/`.

### Gesammelte Nebenbefunde (minor, noch nicht entschieden)

- `day_projection.forecast_rain_mm` (Schwester-Pfad, vorbestehend): streckt Raten über Lücken bis `_MAX_FORECAST_GAP_H`, NaN geht in die Summe, Duplikat behält die niedrigere Rate.
- Met Office: angeschnittener letzter Tag hinter der Stundenreihe zählt als voll abgedeckt mit zu kleiner Summe — im Spec als „im Code benannt“ gefordert, im Modul-Docstring von `forecast_window.py` fehlt der Punkt.
- Met Office `_forecast_document`: bei Auto-Update aus ist `cache_seconds`=0 → Lebensdauer 60 s; naive Fetch-Stempel über DST-Wechsel ±1 h (vorbestehendes Muster wie `_is_fresh`).

---

## 2026-09-15 — PR 2 zu #137: Plan geprüft, probegelaufen, freigegeben

### Stand

**Verifiziert:**
- [PR #144](https://github.com/JustChr/HAsmartirrigation/pull/144) und [PR #145](https://github.com/JustChr/HAsmartirrigation/pull/145): offen, ohne Review und ohne Kommentar. CI von #145 4/4 grün.
- Branch `fix/rain-guard-run-date` @ `f14ebbdd`:
  - entspricht #145, noch kein eigener Commit
  - Arbeitsbaum sauber bis auf diese Datei
- Basis-Suite `D:\Entwicklung\HASI\baseline-pr2.txt`: 7 failed / 2906 passed / 320 errors, gleiche FAILED-Namen wie bei PR 1.
- vitest-Basis: im Probelauf 22 Dateien / 614 passed. Im echten Lauf noch messen (Task 0 Step 3).
- **Plan und Spec, Revision 2026-09-15, vom User freigegeben**, auf `archive/design-history` @ `2f5fcc6e`:
  - `docs/superpowers/plans/2026-09-13-rain-guard-run-date.md`
  - `docs/superpowers/specs/2026-09-13-rain-guard-run-date-design.md` mit Nachtrag 2026-09-15
- **Geprüft wurde der Plan dreimal:**
  1. 22 Agenten gegen den Code nach #144/#145
  2. Probelauf der Tasks 1–7 und 9 in Wegwerf-Worktrees
  3. Nachtest der danach geänderten Stellen: 47 von 48 Aussagen gehalten; zwei Formatierungs-Kleinigkeiten eingearbeitet
- Alle `worktree-*`-Branches und `.claude/worktrees` entfernt.
- HA-Prod-Zeitzone per MCP geprüft: `Europe/Berlin`.
- Arbeitsordner `D:\Entwicklung\HASI\pr2-work\` außerhalb des Repos angelegt. Darin `mut/` für Mutations-Backups; der Plan verweist auf diesen Ordner.

### Entscheidungen (User, 2026-09-15)

- **Abendläufe:** Die Form „Datum des Laufs“ wird gebaut, per Test festgenagelt und im PR sowie auf #137 offengelegt. Mit Fenster 1 sieht ein Lauf um 21:00 nur noch drei Stunden.
- **Hilfetext** getrennt je Modus (`lookahead_help.{skip,water_less}`), in 8 Sprachen und in der Doku.
- **Met-Office-Dokumentwahl** kommt als eigener Commit in PR 2.
- Alle weiteren Festlegungen samt Begründung stehen im Spec-Nachtrag vom 2026-09-15.

### Verworfen

- **Plan vom 13.09. unverändert ausführen:** wäre an drei Stellen gescheitert:
  - `tests/test_init.py::TestPrecipitationLookAhead`
  - der Testzeitzone US/Pacific
  - einer wirkungslosen Mutationsprobe am 25-Stunden-Tag
- **Panel-Regel (Tagesmitte) für den Wächter:** freigegeben ist die Überlappung. Gemeinsam genutzt wird nur `day_span`, damit ist die offene Frage vom 14.09. beantwortet.
- **Tageseinträge „ab Reihenende oder später“:** OWMs 00Z-Slot würde doppelt gezählt, deshalb strikt „nach dem Reihenende“.
- **Met Office „der zuletzt abgerufene gewinnt“ ohne Toleranz:** würde nach jeder Berechnung das Stundenprodukt aus der Live-Schätzung werfen. Toleranz ist deshalb eine Cache-Lebensdauer.
- **INFO-Log an `run_start is None` ohne weitere Maßnahme:** der Ausblick ohne geplanten Lauf hätte bei jedem Refresh geloggt. Deshalb nennen Vorschauen immer einen Zeitpunkt.

### Fallen

- **Testzeitzone:** Das autouse-`hass` setzt US/Pacific für JEDEN Test. Eine Zone nur über ein per Namen angefordertes Fixture setzen, mit `set_default_time_zone` und Rücksetzen in `finally`.
- **NaN:** `max(0.0, nan)` ergibt 0.0. `math.isfinite` gehört vor jedes `max`.
- **Lint:** ruff wählt `B` (B905: `zip` ohne `strict=`) und `I`. `npm run build` ist lint + rollup: eine prettier-Beanstandung bricht den Build, und vitest bemerkt sie nicht.
- **Workflow-Worktrees** starten auf `6e11d112`, nicht auf HEAD. Im Prompt detachen lassen. Die Isolations-Sperre verweigert git- und pytest-Befehle mit Shell-Variablen.
- **Python-Heredoc mit Windows-Pfaden:** `\U` in normalen Strings ist ein Unicode-Escape. Raw-Strings verwenden oder das Skript als Datei schreiben.
- **Workflow-Ergebnisse** stehen als JSON unter `result` in `…/tasks/<id>.output`, sonst in `journal.jsonl`.

### Nächste Schritte

1. **Umsetzung (nach `/clear`):**
   - Plan vom Archiv lesen: `MSYS_NO_PATHCONV=1 git show origin/archive/design-history:docs/superpowers/plans/2026-09-13-rain-guard-run-date.md`
   - Mit `superpowers:subagent-driven-development` ausführen, ab Task 0 Step 3. Der Branch steht schon.
2. **Freigaben:** Task 11 (PR-Text, #137-Kommentar, Basis: auf #145 stapeln oder Merge abwarten) und Task 12 (Live-Test) brauchen je eine eigene.
3. **Nebenher:** Reviews von #144/#145 beobachten. Nach dem Squash-Merge von #144 master in `fix/dated-daily-forecast` mergen (kein Rebase), dann den PR-2-Branch nachziehen.
4. **Danach:** #139, dann die restlichen Befunde aus `D:\Entwicklung\HASI\ToDo.md`.

### Empfohlene Skills

- `superpowers:subagent-driven-development`, je Task `superpowers:test-driven-development`
- `code-doku`, `superpowers:verification-before-completion`
- am Ende `superpowers:requesting-code-review` und `superpowers:finishing-a-development-branch`
- `pr-workflow` für Task 11

---

## 2026-09-14 spät — PR 1 zu #137 (Tagesspanne) als #145, gestapelt auf #144

### Stand

**Verifiziert:**
- [PR #144](https://github.com/JustChr/HAsmartirrigation/pull/144): offen, CI 4/4 grün, MERGEABLE, noch kein Review und kein Kommentar.
- [PR #145](https://github.com/JustChr/HAsmartirrigation/pull/145) offen.
  - Branch `fix/dated-daily-forecast` @ `f14ebbdd`, gestapelt auf #144 (`d0e7cb6c`). User-Entscheidung: PR ohne Merge von #144, weil die Open-Meteo-Spanne laut JustChr in PR 1 gehört und in #144 nicht enthalten ist.
  - 5 Commits: OWM `2a52a6d0` (mit den Konstanten), Met Office `f509ba19`, Open-Meteo-Spanne `7c855cd3`, Pirate Weather `ac45c24f`, Panel `f14ebbdd`.
- Lokale Suite am selben Tag gemessen:
  - Basis auf `d0e7cb6c`: 7 failed / 2890 passed / 320 errors.
  - Branch: 7 / 2906 / 320, identische FAILED-Namen. +16 entspricht den neuen Test-Items (13 Funktionen).
  - Lint grün. 17 Mutanten unabhängig nachgefahren, alle gefangen.
- Design-Historie gepusht, `archive/design-history` @ `774f047a`:
  - Plan: Task 3 aufgeteilt, Stapelung auf #144 vermerkt.
  - Plan Task 5 und Spec: Regel „Tagesmitte“ fürs Panel statt Tagesbeginn.
- Aufgeräumt: Worktrees `base-pr1` und `archive-wt` entfernt, Messdateien `baseline-pr1.txt` und `after-pr1.txt` gelöscht, keine `worktree-*`-Branches.

### Entscheidungen

- **Panel** beschriftet nach dem Ortsdatum der Tagesmitte, und nur wenn Beginn UND Ende gesetzt sind; sonst gilt die Position.
  - Beginn: westlich von UTC einen Tag zu früh, weil OWM und Met Office UTC-Tage liefern.
  - Ende: östlich von UTC einen Tag zu spät.
  - Bei genau UTC+12 gewinnt das spätere Datum, per Test festgenagelt.

### Verworfen

- **Panel nach Tagesbeginn** (so stand es im Plan): Tag zu früh westlich von UTC. Gefunden hat das die Qualitätsprüfung am Beispiel Los Angeles.
- **Rückfall `end or start`:** bringt denselben Fehler zurück, wenn nur der Beginn da ist.
- **Pirate-Weather-Block ohne `time` abfangen:** die API liefert `time` immer, und die Nachbarfelder werden genauso streng gelesen.

### Fallen

- **HA-Zeitzone der Testumgebung ist US/Pacific**, nicht UTC. Zeitzonen-Mutanten brauchen explizit gesetzte Zonen, mit Wiederherstellung in `finally`.
- **Ein Test, dessen erwartete Tage mit der Positionszählung zusammenfallen, beweist die Datenherkunft nicht.** Er braucht eine Fixture mit Lücke oder übersprungenem Tag. Das betraf OWM, Met Office und Open-Meteo, alle drei nachgezogen.
- **`==` auf zeitzonenbehafteten datetimes** vergleicht nur den Zeitpunkt. `utcoffset() == 0` muss eigens festgenagelt werden.
- **`Etc/GMT-12` ist UTC+12**, das POSIX-Vorzeichen ist umgekehrt.
- **Die Ausgabedatei eines Workflows ist kein reines JSON.** Ergebnisse aus `journal.jsonl` im Transcript-Ordner lesen.
- **Fixups auf Task-Commits, die nicht HEAD sind:** `git commit --fixup=<sha>`, dann `GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash <basis>`. Nur solange der Branch nicht gepusht ist.

### Nächste Schritte

1. CI von #145 prüfen, Reviews von #144 und #145 abwarten. Nachbesserungen als neue Commits, kein amend (`pr-workflow` §6).
2. Nach dem Squash-Merge von #144:
   - `git fetch upstream`, dann master in `fix/dated-daily-forecast` mergen, kein Rebase.
   - Ein Konflikt in `OpenMeteoClient.py` ist wahrscheinlich.
   - Push nur nach Freigabe.
3. PR 2 (Wächter am Laufdatum) nach Plan `2026-09-13-rain-guard-run-date.md`.
   - Die Regel „welcher Ortstag ist dieser Eintrag“ aus `websocket_get_weather_forecast` in einen geteilten Helfer ziehen, nicht neu herleiten.
   - Basis klären: auf #145 stapeln oder den Merge abwarten.
4. Danach #139 (Spec und Plan nötig), dann die restlichen Befunde aus der ToDo.

### Empfohlene Skills

- `pr-workflow` (§6 Nachbesserung)
- `superpowers:writing-plans` zum Abgleich des PR-2-Plans, dann `superpowers:subagent-driven-development`
- `superpowers:verification-before-completion`

---

## 2026-09-14 abends — #140/#141 gemergt, Issues #142/#143, PR #144 (Open-Meteo), sequential-Test

### Stand

**Verifiziert:**
- #140 (`4e53caf`) und #141 (`368a149`) von JustChr gemergt. `production` (`bf2b38b7`) ist inhaltlich upstream/master + Branding, steht aber 2 hinter den Squash-Commits → Rebuild erst mit der nächsten Upstream-Änderung.
- #137 entschieden (issuecomment-5667633763): PR 0 Open-Meteo zuerst, dann PR 1 Tagesspanne, dann PR 2 Wächter am Laufdatum. #139 entschieden (issuecomment-5667625952): Backstop-Zuschlag mit Latenz-Marge je Zone, wir bauen.
- Issues angelegt: [#142](https://github.com/JustChr/HAsmartirrigation/issues/142) Pirate-Weather-Tagesmittel, [#143](https://github.com/JustChr/HAsmartirrigation/issues/143) `live_estimate`-Fallback `forecast[0]`.
- [PR #144](https://github.com/JustChr/HAsmartirrigation/pull/144) offen: Branch `fix/open-meteo-forecast-starts-tomorrow` @ `d0e7cb6c` (Datumsfilter + `get_data`-Stundenfehler). CI beim Anlegen 1 grün / 3 laufend. Lokale Suite gegen master am selben Tag: 7 failed / 2883 → 2890 passed / 320 errors, identische FAILED-Liste. Design-Eintrag auf `archive/design-history` (`2ec66189`).
- HA-Prod: `zone_sequencing: sequential` (User). Alle drei Zonen im Überschuss, Sunrise am 15.09. bewässert nichts; der #98-Kettentest wartet auf natürlichen Bedarf (Memory `hasi-sequential-test-98`).
- HA-MCP war nach PC-Neustart weg, per /mcp neu verbunden (Diagnose-Rezept: Memory `verify-ha-system`).

**Offen:** Reihenfolge (User): PR 0 → PR 1 → PR 2 → #139 → restliche Befunde. Details in `D:\Entwicklung\HASI\ToDo.md`.

### Fallen

- **Mutationsskripte:** Backup auf die Platte, `try/finally`, absoluter venv-Pfad. Ein relativer Pfad `.venv/Scripts/python.exe` scheitert in `subprocess` unter Windows; der erste Lauf hinterließ die Datei mutiert.
- **Python-Hilfsskripte nicht im Ordner `irrigation_plus` starten:** dessen `datetime.py` verdeckt das Standardmodul.
- **Gegenprobe auf master im Worktree:** `_local_socket_unblock.py` ist untracked und muss in den Worktree kopiert werden.
- **„Jetzt bewässern“ / „Alle Zonen bewässern“** schreibt einen Überschuss-Bucket auf das Ziel herunter (kein `_mark_manual_run`) — nicht für Tests auf Prod benutzen.
- **Konfig-Ausgaben** vollständig maskieren (homarr trägt einen `ApiKey`-Header).

### Nächste Schritte

1. CI und Review von #144 abwarten (`ccd_pr get_status`).
2. PR 1 nach Plan `2026-09-13-dated-daily-forecast.md` ohne Task 3 (steckt in #144); Open-Meteo-Spanne auf dem #144-Stand aufsetzen, Branch erst nach dem Merge von #144 von upstream/master.
3. Danach PR 2, dann #139 (Spec + Plan nötig), dann die restlichen Befunde aus der ToDo.

---

## 2026-09-14 — Arm-Schranke (#140), PyETO-Tag (#141), Prod auf v2026.09.17

### Stand

**Verifiziert:**
- [PR #140](https://github.com/JustChr/HAsmartirrigation/pull/140) offen, Branch `fix/bound-wall-clock-hardware-window` @ `21f55808`. CI rot ausschließlich durch den master-Datumsfehler; erklärt im [Kommentar auf #140](https://github.com/JustChr/HAsmartirrigation/pull/140#issuecomment-5665561795).
- [PR #141](https://github.com/JustChr/HAsmartirrigation/pull/141) offen, Branch `fix/pyeto-day-of-year` @ `c6596478`, CI 4/4 grün, mergebar.
- [Issue #137](https://github.com/JustChr/HAsmartirrigation/issues/137): Zwei-PR-Vorschlag kommentiert, Antwort von JustChr steht aus. [Issue #139](https://github.com/JustChr/HAsmartirrigation/issues/139): wartet auf Formwahl.
- Fork: `production` = `bf2b38b7` = [Release v2026.09.17](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.09.17) (upstream `437042a7` + #141 + #140 + Branding), hassfest und HACS grün. Rollback: Tag `v2026.09.16`.
- HA-Prod: v2026.09.17 nach Neustart am 14.09. geladen (Manifest geprüft), keine Integrations-Issues. Keine Automation, kein Skript, kein Dashboard ruft Dienste von Irrigation Plus auf.
- Design-Historie gepusht auf `archive/design-history` (`b61e18f2`): `docs/superpowers/specs/2026-09-13-bound-wall-clock-hardware-window-design.md`, `docs/superpowers/plans/2026-09-13-bound-wall-clock-hardware-window.md`, `docs/superpowers/specs/2026-09-14-pyeto-day-of-year-design.md`, `docs/superpowers/plans/2026-09-14-pyeto-day-of-year.md`, dazu die zwei Regen-Pläne `docs/superpowers/plans/2026-09-13-dated-daily-forecast.md` und `…-rain-guard-run-date.md`.
- Hauptbaum auf `production`, sauber bis auf diese Datei. Gelöschte lokale Branches (Wiederherstellung per SHA): `fix/inlet-and-anchor-hardware-window` `52e450c9`, `fix/flow-cal-litre-floor` `93fe524f`, `fix/manual-bucket-assertion` `c0d368f1`, `backup/production-pre-v2026.09.17` `4d4ee13d`, `rebuild/v2026.09.17` `bf2b38b7`, `rebuild/v2026.09.17-pre141` `5bbc09d7`. Termin-Lauf „Regen-Beleg #137“ gestoppt.

**Offen:** alles Weitere steht in `D:\Entwicklung\HASI\ToDo.md`, Abschnitt „Jetzt dran“ (Status-Eintrag vom 14.09. und Block „Befunde aus der Arbeit an #137, #140 und #141“) sowie „Feature-Backlog“.

### Verworfen

- **PyETO-Fix in #140 bündeln:** zwei fremde Themen, JustChr squasht beides unter den Titel von #140. User hat zweimal den eigenen PR gewählt.
- **Tag im Wetterdatensatz, Pflichtparameter, nur den Test festnageln, Fensterende statt Fensterbeginn:** Begründungen im Spec `2026-09-14-pyeto-day-of-year-design.md`, Abschnitt „Verworfen“. Das Fensterende ist zusätzlich per Mutation M10 im PR #141 widerlegt.
- **„Tageszeit-Flake“ als Erklärung des roten Tests:** falsch. Mit eingefrorener Uhr ist er datumsabhängig (13.09. grün, 14.09. rot zu jeder Uhrzeit).

### Fallen

- **Datumsabhängige Tests:** Basis und Branch immer am selben Tag messen, sonst sieht ein Vorbestandsfehler wie eine Regression aus. Bisektieren mit dem freezegun-Plugin aus Plan `2026-09-14-pyeto-day-of-year.md`, Task 5 Step 1.
- **Plan-Erwartungen veralten**, sobald Reviews nachbessern (Testzahlen, Code-Schreibweise). Prüf-Tasks gegen den Endstand beurteilen, nicht wörtlich.
- **Von Agenten entworfene PR-Texte** tragen Zahlen aus Zwischenständen. Vor der Freigabe nachmessen: zwei Mutationszahlen in #141 waren falsch.
- **Ganzzahliger Pin prüft keinen Rundungszweig** — dritter Fall, jetzt 263,6 im Kreuz-Pin.
- **Workflow mit `isolation: worktree`** hinterlässt `worktree-*`-Branches und `.claude/worktrees/` im Repo. Nach jedem solchen Lauf aufräumen.
- **Workflow-Skript per Python unter Windows editiert** bekommt CRLF und wird als „control characters“ abgelehnt. Bytes mit LF schreiben.
- **Langes Markdown per Bash-Heredoc** scheiterte am Quoting; dafür das Write-Tool nehmen.
- **HACS sieht ein neues Fork-Release** erst nach `update_information` für `Eifel-Joe/HAsmartirrigation`.

### Nächste Schritte

1. Reaktionen von JustChr prüfen: `gh pr view 140 141 --repo JustChr/HAsmartirrigation`, `gh issue view 137 139 --repo JustChr/HAsmartirrigation`.
2. Nach dem Merge von #141: `git fetch upstream`, `master` in `fix/bound-wall-clock-hardware-window` mergen (kein Rebase), Push nur mit Freigabe, dann CI von #140 prüfen.
3. Sobald #140 und #141 upstream sind: Prod-Rebuild nach Memory `hasi-production-on-upstream` (Fork-Delta dann nur Branding).
4. Nach JustChrs Antwort auf #137: die zwei Regen-Pläne auf `archive/design-history` an seine Antwort anpassen und ausführen.

### Empfohlene Skills

- `superpowers:systematic-debugging` zuerst, falls die CI von #140 nach dem Merge nicht grün wird.
- `pr-workflow` für Push und PR-Schritte an JustChr.
- Für die Regen-PRs: `superpowers:writing-plans` (Plan-Abgleich), dann `superpowers:subagent-driven-development`, `superpowers:verification-before-completion`, `superpowers:finishing-a-development-branch`.

---

## 2026-09-12 — Upstream kam parallel; zwei PRs und ein Issue offen

**Der Tag in einem Satz:** JustChr hat die Minuten-Aufrundung morgens um 08:41 selbst
gefixt (`e9f2da51`, aus unserem #88-Messbericht, sechs Stunden bevor unser PR aufging).
Der eigene Branch wurde weggeworfen und auf seinem Stand neu aufgesetzt.

### Offen bei JustChr

| | Inhalt | Stand |
|---|---|---|
| [PR #135](https://github.com/JustChr/HAsmartirrigation/pull/135) | Verteiler-Einlass, Finish-Anker, Rundungsregeln zusammengelegt (`hardware_window` + `opensprinkler_window`) | CI grün, CLEAN |
| [PR #136](https://github.com/JustChr/HAsmartirrigation/pull/136) | Kalibrier-Schwelle in Litern statt Sekunden (`FLOW_CAL_MIN_SAMPLE_L`) | CI grün, CLEAN |
| [Issue #137](https://github.com/JustChr/HAsmartirrigation/issues/137) | Regen-Wächter prüft nie den Bewässerungstag selbst | wartet auf seine Formwahl |

[PR #134](https://github.com/JustChr/HAsmartirrigation/pull/134) geschlossen als überholt,
mit Kommentar zur Parallelität. Design-Historie für #135 und #136 liegt auf
`archive/design-history` und ist gepusht.

### Entscheidungen, die Bestand haben

- **OpenSprinkler wird umgerechnet**, nicht ausgeschlossen. `run_station` rundet wirklich
  (Decke auf ganze Sekunden, Untergrenze 1). JustChrs Variante war besser; unser alter Pin
  wurde umgedreht.
- **Nicht bauen, bevor JustChr die Form gewählt hat.** Er hat sie an einem Tag zweimal
  bestimmt und beide Male besser als der eigene Vorschlag. Vorbauen kostete heute neun Commits.
- **Regen: Issue statt Branch.** Die zwei Lösungswege unterscheiden sich im Umfang um vier
  Wetterquellen; auf den falschen zu setzen heißt wegwerfen, nicht nachbessern.

### Befunde, die noch niemand gefixt hat

- **Der Finish-Backstop hat keinen Zuschlag.** `async_call_later(planned_seconds)`, ohne
  Marge. Nach `e9f2da51` feuert er auf Beet 1,4 s vor der Schlussmeldung statt 38 s — das
  Vorzeichen kippt nicht, `_watch_finish` bleibt auf BEIDEN Zonen unerreichbar (Kirschlorbeer
  aus einem zweiten Grund: Ventil 0,567 s zu früh, Entprellung wird vom Backstop kassiert).
  JustChrs Vorhersage auf #88 trifft damit nicht zu. Auf #88 als Angebot formuliert.
- **`bound_wall_clock`** rechnet nicht um; braucht ein `duration_unit`-Feld auf `ZoneRun`.
  In #135 als Folge-Arbeit angeboten.
- **Millimeterzahl im Verlaufseintrag ist KEIN Dreizeiler.** `detail` ist ein übersetzter
  Gründe-Code, exakt verglichen in `_skip_logged_today` und gegen `_EVICTABLE_SKIP_DETAILS`.
  Braucht ein eigenes Feld plus Frontend.

### Fallen dieser Runde

- 🔴 **Ein Pin auf einer GANZEN Zahl prüft den Rundungszweig nicht.** Die alten
  OpenSprinkler-Pins blieben grün, als das Verhalten umgedreht wurde, weil sie bei 263,0
  standen. Neu bei 263,4. Zweites Vorkommen derselben Falle in zwei Tagen.
- Beet hat **keinen Flusssensor** — `_sc_finish_flow` gibt `None`, die Kalibrierprüfung steigt
  sofort aus. JustChrs Aussage über „überhöhte Beet-Proben" geht ins Leere; auf #88 korrigiert.
- Lokale Suite: **immer gegen den Elternstand messen**. Basis `upstream/master` = 7 failed /
  2788 passed / 307 errors.

### Termin

Einmaliger Termin `hasi-regen-beleg-137` am 13.09. um 11:00: prüft, ob wie vorhergesagt
bewässert wurde, obwohl am selben Tag Regen fällt. Legt einen Kommentarentwurf vor,
schickt ihn NICHT ab.

---

## 2026-09-11/12 — Minuten-Aufrundung: Spec, Plan, Serie abgeschlossen, 6 Commits

Nicht hier wiederholt, per Pfad referenziert: Spec und Plan liegen auf `archive/design-history`
unter `docs/superpowers/specs/2026-09-11-hardware-duration-accounting-design.md` und
`docs/superpowers/plans/2026-09-11-hardware-duration-accounting.md`. **Der Plan ist die
Wahrheit, nicht ein Chatverlauf.**

### Stand (nur Verifiziertes)

- **Der Befund**, live gemessen auf HA-Prod: ein Ventil, dessen Schluss der Hardware gehört
  und das nur ganze Minuten nimmt, bekommt aufgerundet und läuft auch so lange; gebucht wurde
  die ungerundete Zahl. Beet: 502 s --> 540 --> 542,8 gemessen (+7,6 %); 265 --> 300 --> 302,3
  (+13,2 %); 263 --> 300 --> 302,1 (+14,1 %). Drei von drei Läufen.
- **Arbeitsbranch `local/minute-rounding`**, von `upstream/master` = `72406c8d` (v2026.09.14).
  Vier Commits, 6 Dateien, +357/−7:
  - `f8b82a20` `hardware_window(seconds, unit) -> tuple[int, float]` in `duration_math.py`
  - `b06231b4` `_sc_convert` wird Weiterleitung darauf
  - `402adb72` der self-closing-Lauf verbucht die wirksame Dauer
  - `8464b3b0` der Batch-Plan und seine Buchhaltung nennen dieselbe Dauer
  - `c413f937` Verteiler-Einlass: `_dist_convert` gelöscht, `_dist_open_inlet` gibt die
    wirksame Dauer zurück, der Zyklus nimmt sie; dazu die Zusicherung, dass die
    Rundungsregel genau einmal existiert
  - `ebf08529` Mess-Obergrenze, Master-Frist und Zyklus-Schätzung an dasselbe Fenster
    gebunden — reines `_dist_inlet_instruction` aus dem Öffnen herausgelöst, einmal VOR
    `cap = window` gerufen; `InletInstruction`-NamedTuple, damit ein Vertauschen der beiden
    Hälften nicht mehr formulierbar ist (CI hat keinen Typprüfer)
- **Schluss-Nachweis auf `ebf08529`:** Regel genau 1× im Baum, Lint grün, volle Suite gegen
  `upstream/master` gemessen — **7 failed / 2783 passed / 306 errors vorher, 7 failed / 2808 passed / 308 nachher,
  identische Fehlernamen, +25 Tests.** Die zwei neuen Errors sind Teardown-Artefakte der
  neuen Batch-Tests.
- 🔴 **OFFENE ENTSCHEIDUNG, blockiert den PR** — siehe Nächste Schritte, Punkt 1.
- **Alle fünf durch Spec- UND Qualitätsprüfung abgenommen.** Die Tests wurden nicht nur grün
  gesehen, sondern durch Mutation als beißend nachgewiesen.
- **Lint grün** (`black`, `ruff`). Fehlerzahlen der Suite gegen den jeweiligen Elternstand
  gemessen, nicht angenommen: 7 failed / 306 errors vorher, identische Fehlernamen nachher,
  die zwei neuen Errors sind die Teardown-Artefakte der zwei neuen Batch-Tests.
- **⚠️ Der Hauptbaum steht auf `local/minute-rounding`, nicht auf `production`.** Vor
  Produktiv-Arbeit zurückstellen.
- **Worktree** für die Design-Historie liegt im Scratchpad unter `archive-wt`, Branch
  `archive/design-history`, vier Commits, noch **nicht gepusht**.

### Verworfen

- **Abrunden statt aufrunden** (die Hardware folgt den Büchern). Harter Rand: eine gerechnete
  Dauer unter einer Minute ergäbe null, man bräuchte doch eine Untergrenze und hätte dort
  wieder aufgerundet. Dazu der Grundsatz des Betreibers: lieber etwas überwässern als zu wenig.
- **Die Umrechnung aus `_sc_dispatch_open` zurückgeben** (die elegantere Form). Scheitert an
  der Reihenfolge: das Observed-Sperrfenster muss VOR dem Öffnen armiert werden, die Korrektur
  muss also vor dem Absenden stehen.
- **OpenSprinkler mitnehmen.** Erfüllt die Bedingung nicht — `run_station` nimmt ganze
  Sekunden, es gibt dort keine Einheiten-Umrechnung. Durch einen eigenen Pin gesichert.

### Fallen

- **🔴 Ein grüner Test ist kein beißender Test.** Zwei Zusicherungen bestanden auch mit
  revertiertem Fix: eine rechnete auf einem Literal statt den Produktionspfad zu beobachten,
  die andere nagelte mit einer GANZEN Zahl einen Zweig fest, in dem die Umrechnung ein No-op
  ist. Beide gefunden, beide ersetzt. **Mutations-Gegenprobe ist Pflicht.**
- **🔴 Der Ceiling-Clamp frisst den Beweis.** Eine Testzone ohne Defizit bucht `min(0.0, ...)`
  = 0,0 — die naheliegende Gutschrift-Assertion wäre wertlos gewesen. Die Fixture trägt jetzt
  `ZONE_BUCKET: -10.0`.
- **`git stash` revertiert nichts, was schon committet ist.** Ein Gegenbeweis kam deshalb
  falsch-negativ zurück. Den Hunk direkt entfernen und danach per Hash-Vergleich
  wiederherstellen.
- **Name-Shadowing:** `planned_seconds` ist in `batch.py` eine importierte Funktion. Eine
  lokale Variable so zu nennen verdeckt sie für die ganze Funktion; der Nächste, der
  `planned_seconds(run)` ergänzt, bekommt einen TypeError. Lokal heißt es `planned`.
- **Kommentare nach `code-doku` brauchen alle drei Teile.** Wurzel, Fix-Logik und NOT-TO-DO.
  Zweimal fehlten Teile, beide Male in der Prüfung gefangen.
- Die lokale Suite ist unter Windows unvollständig. **Immer gegen den Elternstand vergleichen**,
  nie gegen null.

### Nächste Schritte

1. 🔴 **ENTSCHEIDUNG EINHOLEN, bevor irgendetwas rausgeht: die Mess-Obergrenze `cap`.**
   `cap = window` bindet in `distributor.py` VOR der Neuzuweisung, die Master-Abschaltfrist
   wird daraus berechnet. Unser Fix verlängert das Fenster, das diese Frist überdauern muss,
   um bis zu 59 s, ohne die Frist mitzuziehen. Im Review durchgerechnet: bei kurzer Pause deckt
   die Frist 291 s, während die Schleife 310 s verbraucht — **die Pumpe kann mitten im Fenster
   abschalten, was vor diesem Commit nicht möglich war.** Gleiches Muster: die Zyklus-
   Dauerschätzung summiert weiter gepreiste Werte, stimmte vorher mit der Schleife überein,
   jetzt nicht mehr. **Drausssenlassen ist also NICHT neutral.**
   Drei Wege: (a) mitnehmen — den reinen Rechenteil aus `_dist_open_inlet` herauslösen
   (`_dist_inlet_instruction(distributor, seconds) -> (hw, seconds)`, ohne Nebenwirkung) und
   EINMAL vor `cap = window` rufen, dann nehmen Obergrenze, Frist, Schlafdauer und Gutschrift
   dieselbe Zahl aus derselben Quelle, ohne zweite Kopie der Regel; (b) den Verteiler-Commit aus
   dem PR nehmen, dann geht ein vollständiger PR über self-closing + Batch raus; (c) so lassen
   und beschreiben. **Empfehlung: (a).**
2. Danach: `_sc_convert`-Shim entfernen — nur noch ein Aufrufer, `_sc_dispatch_open`.
3. Upstream-PR nach Skill `pr-workflow`. **Text vorher im Chat freigeben** (Projektregel).
   Branch von `upstream/master`, NUR Fix+Test.
4. Regel P1: Spec und Plan liegen auf `archive/design-history` (4 Commits), **noch nicht
   gepusht**.
5. ⚠️ **Hauptbaum steht auf `local/minute-rounding`, nicht auf `production`** — vor
   Produktiv-Arbeit zurückstellen. Zwei Worktrees im Scratchpad: `archive-wt`, `base-wt`.
### Für den PR-Text vorgemerkt

Der Fix heilt drei Dinge gratis mit, im Review nachgewiesen: `async_stop_self_closing` rechnete
`min(elapsed/planned, 1.0)` und gab einem Stopp bei t=280 auf einem echten 300-s-Ventil **volle**
Gutschrift für 93 % des Wassers; der Neustart-Abgleich hielt einen Lauf für beendet, während das
Ventil noch 30 s offen war; `_watch_finish` entscheidet an derselben Zahl. **Nicht** hineinschreiben:
die beiden Wiederarmierungen in `run_watch.py` erben zwar formal, sind für diesen Modus aber
unerreichbar. Für die Release-Notes: ein manueller Lauf „2,5 Minuten" bucht künftig 180 s statt 150.

### Empfohlene Skills

`superpowers:subagent-driven-development` (läuft), pro Task
`superpowers:test-driven-development`, am Ende `superpowers:finishing-a-development-branch`
und `pr-workflow`.

---

## 2026-09-08/09 — Domain-Umzug auf `irrigation_plus`, Prod + Test + 2 PRs

### Stand (nur Verifiziertes)
- **HA-Prod ist umgezogen.** `smart_irrigation` → `irrigation_plus`, neuer Entry
  `01M20YP65K7ZSZWSG1KT2RBV5T`, installiert **v2026.09.14**, Update auf v2026.09.15
  sichtbar (HACS aufgefrischt, `pending_update: true`). Alte Integration entfernt,
  Ordner gelöscht, 0 Reste außer `update.smart_irrigation_update` (gehört HACS).
- **Import verlustfrei belegt**, nicht behauptet: Konfiguration 20/20 Felder identisch,
  Zeitplan „Sunrise" feldweise, Zone Beet 25 Felder + 50 Run-Log-Einträge inkl.
  Ventil-Verdrahtung, Kirschlorbeer 7,24/5162,53 und Kirschbaum 7,95/1077,28 exakt.
  Entitäten: 63 alt = 51 neu + 12 Diagnose-Sensoren (danach wieder aktiviert).
- **API-Schlüssel überlebt.** Lag im ALTEN Slot `weather_service_api_key` (Entry von
  2025-06-13), beide Slots nach dem Import da, erzwungener `update_all_zones` ohne
  Authentifizierungsfehler. Dieser Pfad war auf HA-Test NICHT probebar (dort Open-Meteo).
- **Erster Lauf unter neuem Namen (09.09., 06:26):** Beet, 502 s, 25,94 L,
  `self_closing`/`completed`, Zähler exakt +25,94, Bucket −0,85 → +0,23. Keine Fehler.
- **Nacharbeiten auf Prod fertig:** `config/influx.yaml`-Glob auf `sensor.irrigation_plus_*`,
  beide Dashboards umgestellt (inkl. `card_mod`-Jinja und Bucket-Unterknöpfe),
  `automation.irrigation` + 4 Template-Helfer gelöscht, 12 Diagnose-Sensoren reaktiviert.
- **HA-Test** ebenfalls umgezogen (Generalprobe), Entry `01M20AD0AWZJ15ZXSF1ECVJZN3`.
- **Fork:** `production` = `b5f47f27` = **v2026.09.15**, **0 behind** upstream
  (`8d219884` = deren v2026.09.13), CI komplett grün inkl. HACS Action.
  Backups: `backup/production-pre-v2026.09.13` / `-14` / `-15`.
- **Upstream:** Issues #129 und #130 **geschlossen**, #128 offen. PRs
  [#131](https://github.com/JustChr/HAsmartirrigation/pull/131) (Wortlaut, 8 Sprachen) und
  [#132](https://github.com/JustChr/HAsmartirrigation/pull/132) (Marker) **gemergt**.
  Sein Folge-Fix `db603d88` korrigiert einen Fehler in unserem #132 (s. Fallen).

### Fallen (haben Zeit gekostet oder hätten Schaden angerichtet)
- **🔴 Parallelbetrieb = zwei Bewässerungssteuerungen auf denselben Ventilen.** Kein
  domänenübergreifender Guard. Gegenmittel und Belege: Memory
  `hasi-migration-dual-run-hazard`. Die Regenverzögerung VOR dem Hinzufügen ist der
  eine Hebel, der beide Kopien anhält — auf Prod durchgemessen, sie wandert mit der
  rohen Store-Kopie und armiert nach dem Aufheben wieder.
- **🔴 Fremdgelieferte Werte brauchen exakten Vergleich.** Ich stellte in #132 die
  Marker von einer Konstante auf das Fork-Manifest um und ließ den Teilstring-Vergleich
  stehen — `@org` trifft `altmenorg`. Erkannt, in den Docstring geschrieben und
  weggeredet. Memory `supplied-values-need-stricter-matching`.
- **Pins, die aus dem falschen Grund grün sind.** Zweimal an einem Tag: `irrig` steckt im
  Produktnamen (→ `irrigazion`), und der Bewässerungs-Stamm steckt in sechs Katalogen
  schon in „irrigation history" (→ Import-Schritt auf das Wort für *Ventil* gepinnt).
  **Mutations-Gegenprobe ist Pflicht, grün allein beweist nichts.**
- **Reparatur-Dialoge sind per MCP NICHT auslösbar** (REST-Flow, MCP kann nur einmalige
  WS-Kommandos). Der Nutzer muss klicken. Nachbauen würde `async_cleanup_is_safe` umgehen.
- **`.storage/*` ist über `ha_read_file` nicht lesbar** (Allowlist). Für Soll-Ist-Vergleiche
  den Diagnostics-Dump nehmen, mit `diagnostics_data_path` (z. B. `data.store.config`)
  gegen die Kontext-Grenze.
- **Nach jedem HA-Neustart liefert das MCP-Add-on ~1 Minute lang 502**, obwohl die
  Weboberfläche schon 200 antwortet. Nicht als Fehlschlag deuten, warten.
- **Der lokale `brand/`-Ordner erreicht die HACS-Kachel nicht** — HACS schreibt die
  CDN-Adresse fest ins `entity_picture`. Details in `hasi-domain-migration-rehearsal`.
  **User-Entscheidung: liegt bei JustChr, nichts unternehmen.**
- **Auto-Merges sind gefährlicher als Konflikte.** `migrate_domain.py` mergte konfliktfrei
  und hätte still unseren überholten Marker-Ansatz weitergeführt.
- **Ein bewusstes Fork-Delta unter UPSTREAMS Namen belassen.** Die Zusicherung
  `test_this_repository_derives_exactly_the_upstream_marker` ist bei uns
  `("eifel-joe","justchr")`, bei upstream `("justchr",)` — gleicher Testname, damit der
  nächste Merge darauf kollidiert statt still eine Seite zu nehmen. Hat funktioniert.

### Nächste Schritte (offen)
1. **Vier Grafana-Views** im Dashboard „Garten" (`grafana-uberblick/-effektivitaet/-wetter/-bilanz`)
   fragen InfluxDB weiter unter `sensor.smart_irrigation_*` ab. Altdaten bleiben, ab
   2026-09-08 abends schreibt HA unter dem neuen Namen → Kurven brechen ab. **Außerhalb
   von HA, braucht den User.** Angeboten: angepasste Flux-Abfragen formulieren.
2. **#128** wartet auf JustChrs Schließung.
3. Optional: Prod von v2026.09.14 auf v2026.09.15 (exakter Marker-Vergleich; für diese
   Anlage folgenlos, Neustart nötig).
4. Weiter offen aus früheren Sitzungen: Regen-Skip-Issue (war bis nach dem Umzug vertagt),
   Mid-Run-Ventil-Messung + `sequential`-Test für JustChr (witterungsabhängig),
   Durchsatz-Frage Kirschbaum, Hochbeet-Bodensonde tot seit 04.09.

### Werkzeuge / Befehle
- Tests: `./.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock`
- Lint: `uvx black --check custom_components/irrigation_plus/` und `uvx ruff check …`
  (**`ruff` ist nicht im PATH**, `uvx` nötig — die Palette nennt es ohne Präfix)
- Frontend: `cd custom_components/irrigation_plus/frontend && npm ci && npm run build`,
  danach `git add -f …/dist/`
- **Bekannt-roter Test unter Windows:** `test_panel.py::test_async_register_panel_static_path_config`
  (Pfadtrenner) — fällt auf unverändertem upstream/master genauso, kein Regress.
- **Im Scratchpad und nach `/clear` WEG:** `fingerprint.py` (zwei Diagnostics-Dumps rein,
  feldweiser Diff der Zonen/Config/Zeitpläne raus) und `prod_before.json`. In ~10 min
  neu schreibbar; nur nötig, wenn wieder ein Umzug verglichen wird.

---

## 2026-09-02 — Produktiv-Rebuild v2026.09.01 + PR #114-Nachlese

### Stand (nur Verifiziertes)
- **production = `8fe9be15` = Fork-[v2026.09.01](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.09.01)**,
  **0 behind** upstream/master (`388b02fa` = v2026.09.02). Fork-Delta **LEER** (nur
  Eifel-Joe-Branding: manifest owner/links, README-Heads-up, en.json-URL-Patch).
  CI grün (hassfest 26s + HACS Action 46s), Release + ZIP-Asset Download **200**.
  Backup lokal `backup/production-pre-v2026.09.01` = `9b2746ab`.
- **Rebuild-Rezept sauber durchgezogen** (Memory `hasi-production-on-upstream`, neuer
  v09.01-Eintrag): von upstream/master gebaut, Branding via
  `git checkout production -- README.md manifest.json`, Versionen SYNCHRON v2026.09.01
  (manifest+const mit `v`, package ohne), en.json 4→0 github-URLs, dist Node-24
  (nur Versions-String). Alle Gates belegt: black ✓, ruff ✓, 0-behind ✓, dist=09.01 ✓.
- **PR [#114](https://github.com/JustChr/HAsmartirrigation/pull/114) (i18n flow-advisory) GEMERGT** (`6e25eeed`, upstream v09.02).
  JustChr bat VOR dem Merge um einen Regressions-Pin, den wir **nicht** lieferten →
  er schrieb ihn selbst (`60e15ecd`, beide Strings, mutation-getestet). Entschuldigung +
  Live-Test-Zusage auf #114 gepostet ([issuecomment-5516439077](https://github.com/JustChr/HAsmartirrigation/pull/114#issuecomment-5516439077)).
- **Prozess-Schutz gegen genau diese Lücke verankert:** Skill `pr-workflow` §3a
  (Regressions-Pin-Check vor `gh pr create`) + §6 (Reviewer-Test-Bitte vor Merge liefern)
  + Memory `regression-pin-on-removals`.
- **Design-Historie:** observed-flow-credit Spec+Plan verifiziert **bereits** in
  `archive/design-history` (`d0730a6f`, inhaltsgleich, nur CRLF). Untracked-Reste +
  überholte alte SESSION-STAND.md aufgeräumt. Arbeitsbaum sauber, auf Branch `production`.

### Fallen (haben Zeit gekostet)
- **🔴 Tag-Kollision:** JustChr hat `v2026.09.01` UND `v2026.09.02` als eigene Tags.
  `git fetch upstream` zieht sie → lokaler Tag `v2026.09.01` zeigt auf JustChrs Commit,
  nicht auf production. **ZIP IMMER aus dem SHA** `git archive 8fe9be15:…`, Release via
  `gh release create --target production`, lokalen Tag danach `git tag -f v2026.09.01 8fe9be15`.
  ZIP VOR Upload verifiziert: **en.json 0 URLs = eindeutiger Fork-Beleg** (JustChrs Tag hätte 4).
- **`ruff` nicht im PATH** → `uvx ruff check custom_components/smart_irrigation/` (wie black via uvx).
- **MSYS:** Process-Substitution (`<(…)`) scheitert (`/proc/…/fd`), `grep -c` == 0 bricht
  `&&`-Ketten ab. Für Diffs Temp-Dateien nutzen, `diff --strip-trailing-cr` gegen CRLF-Rauschen.
- **Cloud-Monitoring nicht möglich:** die `schedule`-Skill erzeugt Cloud-Agenten ohne Route
  ins LAN → erreichen HA-Prod (LAN-Adresse: Projekt-`CLAUDE.md`) nicht, HA-MCP ist lokal (kein claude.ai-Connector).
  → Kirschlorbeer-Überwachung bleibt ToDo/Memory-basiert.

### Nächste Schritte (offen)
1. **User:** HA-Prod auf **v2026.09.01** updaten (HACS) + Neustart (Freigabe nötig,
   Memory `ha-no-auto-restart`) → bringt #111 (measured-flow/Ceiling) + #114 live.
2. **Kirschlorbeer Flow-Cal Live-Test** (Zusage an JustChr #114, Memory
   `hasi-kirschlorbeer-flow-cal-livetest`): **BLOCKER Witterung** — seit >1 Woche keine
   Bewässerung (Stand 2026-09-02). Sobald wieder Läufe kommen: ≥3 Läufe mit Flussmessung
   sammeln → prüfen (a) bleibt der Kalibrier-Hinweis auf korrekt konfigurierter Zone still,
   (b) reale Rate vs 300 s-Short-Run-Schwelle (`OBSERVED_FLOW_CAL_MIN_SECONDS`) → Ergebnis
   auf #114 zurückmelden. Voraussetzung: Schritt 1 (Prod muss v09.01-Code tragen).
3. **Regel P1** für neue Features weiterhin beachten: Spec+Plan ENTSTEHEN lassen und
   VOR Branch-Löschung nach `archive/design-history` schieben (Memory `preserve-design-docs-archive-branch`).

### Kontext
- upstream v2026.09.02 ist bei JustChr ein **Pre-Release/Beta**; unser Fork-Release v09.01
  ist ein **volles** Release (Fork-Versionsschema folgt dem Kalender, unabhängig von upstream).
- Fork-Delta leer — alle Eigenentwicklungen sind upstream (#47/#54/#59/#60/#70/#71/#73/#79/#95/#111/#114).

### Empfohlene Skills (Folgesitzung)
- `task-loop`, `pr-workflow`, `superpowers:requesting-code-review`
- Produktiv-Rebuild: Memory `hasi-production-on-upstream`; Test-Env: `hasi-local-test-env-rebuild`
- Live: MCP-Präfixe `mcp__HA-Test__` / `mcp__HA-Prod__`, Memory `verify-ha-system`
