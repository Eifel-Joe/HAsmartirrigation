# Distributor inlet-entity form UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hide the distributor `watch_mode` row unless an `inlet_entity` is set, and extend the inlet-entity help text (optional + purpose) in all 8 languages.

**Architecture:** Frontend-only. `_renderInletWatchRows` in `si-distributor-form.ts` gates the second `ha-settings-row` on `d.inlet_entity`. Two i18n help keys (`inlet_entity_help`, `inlet_entity_help_service`) get extended copy in 8 JSONs. Vitest tests read `en.json` statically, so EN copy + visibility are unit-tested; the other 7 languages just need to parse.

**Tech Stack:** Lit + TypeScript, vitest; JSON i18n (8 languages).

**Spec:** `docs/superpowers/specs/2026-07-08-distributor-inlet-form-ux-design.md`

---

## Test env
```bash
cd custom_components/smart_irrigation/frontend
npm test            # vitest run
```
The vitest suite resolves `localize` against the statically-imported `en.json`, so EN help changes and the render output are exercised directly.

## File structure
- `custom_components/smart_irrigation/frontend/src/components/si-distributor-form.ts` — `_renderInletWatchRows` conditional.
- `custom_components/smart_irrigation/frontend/src/components/si-distributor-form.test.ts` — new visibility test + fixture updates.
- `custom_components/smart_irrigation/frontend/localize/languages/{en,de,nl,fr,es,it,no,sk}.json` — `inlet_entity_help` + `inlet_entity_help_service`.

---

## Task 1: Gate the watch_mode row on `inlet_entity`

**Files:** Modify `si-distributor-form.ts` (`_renderInletWatchRows`, `:167-216`); Test `si-distributor-form.test.ts`

- [ ] **Step 1: Write the failing visibility test**

Add to `si-distributor-form.test.ts` inside the `describe("si-distributor-form inlet-watch section", …)` block (the `makeForm`/`flatten` helpers already exist):
```ts
  it("hides the watch_mode row until an inlet_entity is set", () => {
    // No inlet_entity -> nothing to watch -> the watch_mode row must be absent.
    const bare = makeForm({ name: "d", watering_mode: "service" });
    // NB: the form has other <select>s (watering_mode, duration_unit), so assert
    // on watch_mode-SPECIFIC markers, not on "<select" presence.
    const bareText = flatten(bare.el.render()).text;
    expect(bareText).not.toContain("On a manual inlet pulse");
    expect(bareText).not.toContain("Count it (advance the position)");
    // The inlet_entity picker itself still renders.
    expect(bareText).toContain("ha-entity-picker");

    // With an inlet_entity set, the watch_mode row appears.
    const withInlet = makeForm({
      name: "d",
      watering_mode: "service",
      inlet_entity: "switch.ring",
      watch_mode: "warn",
    });
    const withText = flatten(withInlet.el.render()).text;
    expect(withText).toContain("On a manual inlet pulse");
    expect(withText).toContain("Count it (advance the position)");
  });
```

- [ ] **Step 2: Run to verify failure**
```bash
cd custom_components/smart_irrigation/frontend
npm test 2>&1 | tail -20
```
Expected: the new test FAILS (the watch_mode row currently renders even with no `inlet_entity`, so `bareText` contains `"On a manual inlet pulse"`).

- [ ] **Step 3: Gate the watch_mode row**

In `si-distributor-form.ts`, `_renderInletWatchRows`, wrap the SECOND `ha-settings-row` (the `watch_mode` one, currently at `:190-214`) in a `d.inlet_entity` conditional. Replace the returned template's second row:
```ts
      <ha-settings-row>
        <span slot="heading"
          >${localize("panels.distributors.labels.watch_mode", lang)}</span
        >
        …
      </ha-settings-row>
    `;
```
so the whole `watch_mode` row becomes:
```ts
      ${d.inlet_entity
        ? html`
            <ha-settings-row>
              <span slot="heading"
                >${localize("panels.distributors.labels.watch_mode", lang)}</span
              >
              <span slot="description"
                >${localize(
                  "panels.distributors.labels.watch_mode_help",
                  lang,
                )}</span
              >
              <select
                class="settings-input"
                .value="${live(mode)}"
                @change="${(e: Event) =>
                  this._emit({
                    [DISTRIBUTOR_WATCH_MODE]: (e.target as HTMLSelectElement)
                      .value as SmartIrrigationDistributor["watch_mode"],
                  })}"
              >
                ${DISTRIBUTOR_WATCH_MODES.map(
                  (m) => html`
                    <option value="${m}" ?selected="${mode === m}">
                      ${localize(
                        `panels.distributors.labels.watch_mode_${m}`,
                        lang,
                      )}
                    </option>
                  `,
                )}
              </select>
            </ha-settings-row>
          `
        : ""}
    `;
```
The `inlet_entity` picker row above it and all the `const` setup (`isService`, `inletHelpKey`, `mode`) are unchanged.

- [ ] **Step 4: Update the existing fixtures that assert the watch_mode row**

The following tests build fixtures WITHOUT `inlet_entity`, so they now hide the row and would fail. Add `inlet_entity: "switch.ring",` to each fixture object:
- `"renders inlet_entity + watch_mode select in SERVICE mode …"` (`:83-87`)
- `"renders the inlet-watch section in CLASSIC mode …"` (`:101-105`)
- `"offers exactly three watch_mode options …"` (`:115-119`)
- `"emits watch_mode (not watch_inlet) when the select changes"` (`:132-136`)
- `"defaults the select value to 'ignore' when watch_mode is unset"` (`:160`)

E.g. the first becomes:
```ts
    const { el } = makeForm({
      name: "d",
      watering_mode: "service",
      inlet_entity: "switch.ring",
      watch_mode: "warn",
    });
```
and the default-ignore fixture becomes `makeForm({ name: "d", watering_mode: "classic", inlet_entity: "switch.ring" })`. Their assertions are otherwise unchanged.

- [ ] **Step 5: Run the form tests to green**
```bash
cd custom_components/smart_irrigation/frontend
npm test 2>&1 | tail -20
```
Expected: PASS (new visibility test + all updated existing tests).

- [ ] **Step 6: Commit**
```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/smart_irrigation/frontend/src/components/si-distributor-form.ts custom_components/smart_irrigation/frontend/src/components/si-distributor-form.test.ts
git commit -F - <<'EOF'
feat(distributor-form): show the watch_mode row only when an inlet_entity is set

Without an inlet valve there is nothing to watch, so the "On a manual inlet pulse"
(watch_mode) row is meaningless — gate it on d.inlet_entity in _renderInletWatchRows.
The existing watch_mode render tests get inlet_entity added to their fixtures so they
still exercise the gated row; a new test asserts hidden-without / shown-with.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 2: Extend the inlet-entity help text (8 languages)

**Files:** Modify `frontend/localize/languages/{en,de,nl,fr,es,it,no,sk}.json`; Test `si-distributor-form.test.ts`

- [ ] **Step 1: Lock the new EN copy with a failing assertion**

In `si-distributor-form.test.ts`, extend the SERVICE-mode render test (`"renders inlet_entity + watch_mode select in SERVICE mode …"`) with two assertions on the new service help copy (keep the existing `only read` / `NOT the flow/confirm sensor` assertions):
```ts
    // Service help now states it is optional + how to disable it.
    expect(text).toContain("Optional");
    expect(text).toContain("Leave empty to disable inlet watching");
```

- [ ] **Step 2: Run to verify failure**
```bash
cd custom_components/smart_irrigation/frontend
npm test 2>&1 | tail -20
```
Expected: FAIL (en.json does not yet contain "Optional" / "Leave empty to disable inlet watching").

- [ ] **Step 3: Update the two help keys in all 8 language JSONs**

In each `frontend/localize/languages/<lang>.json`, replace `inlet_entity_help` and `inlet_entity_help_service` with the extended copy below. Keep the KEY names; only change the values. (EN preserves the substrings the tests assert: `opens the water supply into the distributor`, `only read`, `NOT the flow/confirm sensor`.)

**en.json**
```json
        "inlet_entity_help": "The switch or valve entity that opens the water supply into the distributor. It is also watched for foreign pulses — the setting below controls the reaction.",
        "inlet_entity_help_service": "Optional. The ring valve Home Assistant watches for foreign pulses to keep the outlet position in sync (e.g. when the valve is opened manually or by an automation outside a HASI run — the setting below controls the reaction). Actuation is via the run/stop service; this field is only read, and is NOT the flow/confirm sensor. Leave empty to disable inlet watching.",
```
**de.json**
```json
        "inlet_entity_help": "Die Schalter- oder Ventil-Entität, die die Wasserzufuhr in den Verteiler öffnet. Sie wird zugleich auf Fremd-Pulse beobachtet — die Reaktion steuert die Einstellung darunter.",
        "inlet_entity_help_service": "Optional. Das Ring-Ventil, das Home Assistant auf Fremd-Pulse beobachtet, um die Ausgangs-Position synchron zu halten (z. B. wenn das Ventil manuell oder per Automation außerhalb eines HASI-Laufs geöffnet wird — die Reaktion steuert die Einstellung darunter). Geschaltet wird über den Run/Stop-Service; dieses Feld wird nur gelesen und ist NICHT der Fluss-/Bestätigungssensor. Leer lassen, um die Beobachtung zu deaktivieren.",
```
**nl.json**
```json
        "inlet_entity_help": "De schakelaar- of klep-entiteit die de watertoevoer naar de verdeler opent. Deze wordt tevens bewaakt op vreemde pulsen — de instelling hieronder bepaalt de reactie.",
        "inlet_entity_help_service": "Optioneel. De ringklep die Home Assistant bewaakt op vreemde pulsen om de uitgangspositie synchroon te houden (bijv. wanneer de klep handmatig of door een automatisering buiten een HASI-run wordt geopend — de instelling hieronder bepaalt de reactie). Aansturing gebeurt via het start/stop-script; dit veld wordt alleen gelezen en is NIET de stromings-/bevestigingssensor. Laat leeg om de bewaking uit te schakelen.",
```
**fr.json**
```json
        "inlet_entity_help": "L'entité interrupteur ou vanne qui ouvre l'alimentation en eau du distributeur. Elle est aussi surveillée pour les impulsions externes — le réglage ci-dessous contrôle la réaction.",
        "inlet_entity_help_service": "Facultatif. La vanne d'anneau que Home Assistant surveille pour les impulsions externes afin de garder la position de sortie synchronisée (p. ex. lorsque la vanne est ouverte manuellement ou par une automatisation en dehors d'un cycle HASI — le réglage ci-dessous contrôle la réaction). L'actionnement se fait via le script de démarrage/arrêt ; ce champ est uniquement lu et n'est PAS le capteur de débit/confirmation. Laisser vide pour désactiver la surveillance.",
```
**es.json**
```json
        "inlet_entity_help": "La entidad de interruptor o válvula que abre el suministro de agua al distribuidor. También se vigila en busca de pulsos externos — el ajuste de abajo controla la reacción.",
        "inlet_entity_help_service": "Opcional. La válvula de anillo que Home Assistant vigila en busca de pulsos externos para mantener sincronizada la posición de salida (p. ej. cuando la válvula se abre manualmente o mediante una automatización fuera de una ejecución de HASI — el ajuste de abajo controla la reacción). El accionamiento se realiza mediante el script de inicio/parada; este campo solo se lee y NO es el sensor de flujo/confirmación. Déjelo vacío para desactivar la vigilancia.",
```
**it.json**
```json
        "inlet_entity_help": "L'entità interruttore o valvola che apre l'alimentazione dell'acqua al distributore. Viene inoltre sorvegliata per gli impulsi esterni — l'impostazione sotto controlla la reazione.",
        "inlet_entity_help_service": "Facoltativo. La valvola ad anello che Home Assistant sorveglia per gli impulsi esterni per mantenere sincronizzata la posizione dell'uscita (es. quando la valvola viene aperta manualmente o da un'automazione al di fuori di un ciclo HASI — l'impostazione sotto controlla la reazione). L'attuazione avviene tramite lo script di avvio/arresto; questo campo viene solo letto e NON è il sensore di flusso/conferma. Lascia vuoto per disattivare la sorveglianza.",
```
**no.json**
```json
        "inlet_entity_help": "Bryter- eller ventil-entiteten som åpner vanntilførselen til fordeleren. Den overvåkes også for fremmede pulser — innstillingen nedenfor styrer reaksjonen.",
        "inlet_entity_help_service": "Valgfritt. Ringventilen Home Assistant overvåker for fremmede pulser for å holde utgangsposisjonen synkronisert (f.eks. når ventilen åpnes manuelt eller av en automasjon utenfor en HASI-kjøring — innstillingen nedenfor styrer reaksjonen). Aktivering skjer via start/stopp-skriptet; dette feltet blir bare lest og er IKKE flyt-/bekreftelsessensoren. La stå tomt for å deaktivere overvåkingen.",
```
**sk.json**
```json
        "inlet_entity_help": "Entita spínača alebo ventilu, ktorá otvára prívod vody do rozvádzača. Zároveň sa sleduje kvôli cudzím impulzom — reakciu riadi nastavenie nižšie.",
        "inlet_entity_help_service": "Voliteľné. Kruhový ventil, ktorý Home Assistant sleduje kvôli cudzím impulzom, aby udržal pozíciu výstupu synchronizovanú (napr. keď sa ventil otvorí manuálne alebo automatizáciou mimo behu HASI — reakciu riadi nastavenie nižšie). Ovládanie prebieha cez skript spustenia/zastavenia; toto pole sa iba číta a NIE je snímačom prietoku/potvrdenia. Nechajte prázdne na vypnutie sledovania.",
```

- [ ] **Step 4: Run tests + validate all 8 parse**
```bash
cd custom_components/smart_irrigation/frontend
npm test 2>&1 | tail -20
node -e "for (const l of ['en','de','nl','fr','es','it','no','sk']) JSON.parse(require('fs').readFileSync('localize/languages/'+l+'.json','utf8')); console.log('all 8 parse OK')"
```
Expected: form tests PASS (the new EN assertions now match), all 8 JSON parse.

- [ ] **Step 5: Commit**
```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/smart_irrigation/frontend/localize/languages custom_components/smart_irrigation/frontend/src/components/si-distributor-form.test.ts
git commit -F - <<'EOF'
i18n(distributor): inlet_entity help now states it is optional + its purpose (8 languages)

Service help: optional, watch-only for foreign-pulse position sync, leave empty to
disable. Classic help: the actuated valve, also watched. All 8 languages; the EN copy is
locked by the service-render test.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## Task 3: Build + release (b26)

- [ ] **Step 1: Full frontend test suite green.**
```bash
cd custom_components/smart_irrigation/frontend
npm test 2>&1 | tail -5
```
Expected: all vitest tests pass (no regressions beyond the touched suite).

- [ ] **Step 2: Version bump b25 -> b26** (const.py, manifest.json, frontend/package.json) + `npm run build` (bakes b26 + the new help copy into the bundle). Same recipe as prior betas.

- [ ] **Step 3: Release** — show notes for approval (REGEL 5), then push + `gh release create v2026.07.11b26 --repo Eifel-Joe/HAsmartirrigation --prerelease --target feature/gardena-distributor`.

- [ ] **Step 4: Update memory** — `hasi-distributor-fix-roadmap` (inlet-form UX shipped in b26). User verifies visually in the panel (Strg+F5 refresh drill).

---

## Self-review

- **Spec coverage:** conditional watch_mode row → Task 1 Step 3 + gate test; extended help (8 langs, both keys, optional/purpose) → Task 2 Step 3; phrase-preservation → Task 2 (EN keeps the asserted substrings) + the existing tests staying green; fixture updates for the now-gated row → Task 1 Step 4; build/release → Task 3. All spec sections mapped.
- **Placeholders:** none — full conditional code, all 16 strings, exact fixture edits, exact commands.
- **Type/name consistency:** `_renderInletWatchRows`, `d.inlet_entity`, `DISTRIBUTOR_WATCH_MODE`, `DISTRIBUTOR_WATCH_MODES`, `watch_mode_help`, `inlet_entity_help`/`_service`, `makeForm`/`flatten` all match the current code/tests.
