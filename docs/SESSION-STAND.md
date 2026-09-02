# HASI — Session-Stand

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
  ins LAN → erreichen HA-Prod (192.168.20.2) nicht, HA-MCP ist lokal (kein claude.ai-Connector).
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
