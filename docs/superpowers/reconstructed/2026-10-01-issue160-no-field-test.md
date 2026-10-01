# JustChr#160 — Tiefensuche und Wahrscheinlichkeitsanalyse (2026-10-01)

Rohberichte: `2026-10-01-issue160-research/hacs-install-types.md`, `2026-10-01-issue160-research/container-tz-prevalence.md`,
`2026-10-01-issue160-research/justchr-stable-practice.md` (drei Agenten, nur lesend). Tragende Angaben von mir nachgemessen, markiert mit ✔.

## 1. These „Es gab eine HA-Variante ohne HACS“

| Variante | HACS | Beleg |
|---|---|---|
| HA OS | ja (App „Get HACS“ oder Skript) | HACS-Doku |
| **Container** | **ja, offiziell dokumentiert** (`docker exec` + `get.hacs.xyz`) | HACS-Doku ✔, Skript ohne Typprüfung ✔, HACS-Code nie mit Typprüfung (Pickaxe über ganze Historie) |
| Core, Supervised | technisch ja; HA-Support endete 2025.12, ADR-0014/0016 am 2026-04-02 zurückgezogen ✔ | HACS verlangt „supported installation“ (ADR-0012 ✔) |
| HA < 2024.4.1 / genau 2023.12.0 | nein | Skript ✔ |
| flüchtiger/read-only Container, kein GitHub | praktisch nein | Agentenbericht |

Herkunft der Erinnerung: HA-Doku-Commit `27519ec44` (2021-04-23) „Add-ons are only available if you've used the
Home Assistant Operating System or …“ ✔; heute „Apps are only available if you used the Home Assistant Operating System
installation method“ ✔ — betrifft Apps, nicht HACS. **Die These trifft auf die #160-Gruppe nicht zu.**

## 2. Wer ist betroffen (P0)

- HA Core setzt die Prozesszone nicht (`async_set_time_zone` → nur `dt_util`) ✔; offizielles Image 2026.9.4 ohne `TZ`
  in `Env` ✔ → ohne Zutun UTC. HA OS: Supervisor setzt `TZ` (`supervisor/docker/homeassistant.py:194`) ✔.
- Analytics 2026-09-29: Container 17,5 % + unsupported_container 0,7 % ✔.
- Anteil ohne passendes `TZ`: Stichprobe 3 663 öffentliche Compose-Dateien — 7,5 % weder `TZ` noch Mount (Agent,
  ungeprüft, zu sorgfältigen Nutzern verzerrt); Standard UTC bei linuxserver, TrueNAS, Helm, Umbrel (Agent).
  **Schätzung 5–15 % der Container** → ~1–3 % aller Installationen. Echte Fälle in HA-Core-Issues 2026 (Agent).
- Irrigation Plus: Stable-ZIP v2026.09.17 31 Downloads, Betas 0–3 ✔. Erwartete Beta-Nutzer mit Fehlkonfiguration
  ≈ 3 × 0,18 × 0,1 ≈ 0,05 → **P(spontaner Feldbericht) ≈ 5 %**. JustChrs Bedingung erfüllt sich von selbst praktisch nie.

## 3. Was ein Docker-Feldtest finden könnte (P1)

| Fehlerart | Beleg dagegen | Rest |
|---|---|---|
| `_process_timezone()` liest falsch | Kindprozess `TZ=EST5EDT` gepinnt ✔; Identität auf demselben Image (Prod, Test) ✔ | ~0 |
| HA-Zone beim Store-Laden noch nicht gesetzt | Identität auf Prod/Test (sonst −2 h) ✔ | ~0 |
| Arithmetik mit Versatz ≠ 0, DST | 20 Tests mit getrennten Zonen ✔, JustChrs 2 Mutationen gefangen | sehr klein |
| Store-Mechanik, Rollback unter Major-Sperre | live 2026.9.3 ✔ | sehr klein |
| musl vs glibc | gleiches Image wie Prod/Test ✔ (`builder.yml`, `machine/*`) | sehr klein |
| Unbekanntes (echte Datenformen im Container) | echte Alt-Stores migriert; Unlesbares bleibt unverändert (Test) | klein |

**Gesamt subjektiv ~1–3 %.** Schaden begrenzt: nur fehlkonfigurierte Container, ein Fenster, rückweg-sicher (Minor).
Für HA OS (~80 %) ist die Migration nachweislich die Identität.

## 4. Kommt #186 in ein Stable (P2)

- Aufnahme: #186 in `master`; 8/8 Stables enthielten die letzte Beta ihrer Linie; kein Revert seit 2026-07-25 ✔
  (einziger grep-Treffer war Mutationstext). → **≈ sicher im nächsten Stable aus `master`.**
- Zeitpunkt: JustChr will Nicht-Opt-in-Änderungen „in a beta for a week“ (#139, 2026-09-20) ✔ → frühestens ~08.10.
  Aktuelle Linie 12 Betas, 10,7 Tage (Rekord) ✔; Median erste Beta → Stable 2,4 Tage (Agent).
- Was ein Stable bisher wirklich aufhielt: 08.17 — irreversible Migration, nie auf echtem Alt-Store gelaufen
  („blocking a promotion“, #105, 2026-08-22) ✔; entsperrt durch Teilnachweis eines Beitragenden. #186 erfüllt beides
  (rückweg-sicher, auf zwei echten Alt-Stores gelaufen). Offene Bestätigungs-Issues blockierten nie (#148, #181 ✔).
- ~~Schätzung: Stable mit #186 bis 15.10. ~70–80 %, bis Ende Oktober ~90 %.~~ **Zurückgezogen (User, 2026-10-01):**
  aus früheren Releases lässt sich für diesen Fall weder wissen noch annehmen, wann JustChr ein Stable schneidet.
  Belastbar bleibt nur: #186 steht in `master`; ein Stable aus `master` enthält es mechanisch.

## Empfehlung

Kein Test. Kommentar auf JustChr#160 posten (Belegkette, keine Argumente aus früheren Releases). Proxmox-Feldtest nur, wenn JustChr
ausdrücklich darum bittet; Aufbau liegt in Memory `hasi-proxmox-test-vms`.
