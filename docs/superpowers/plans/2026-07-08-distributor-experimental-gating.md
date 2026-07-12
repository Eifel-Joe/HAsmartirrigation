# Distributor experimental gating Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the Gardena distributor feature behind an opt-in experimental flag (`distributors_enabled`, default off) surfaced on Setup → Experimental, gating the Distributors tab, the zone-side distributor selector, and adding an experimental banner — shipped as pre-release b28.

**Architecture:** A single backend config flag (`distributors_enabled`, attrs Config field, default False) round-trips through the existing `attr.asdict` / `attr.fields_dict` machinery. The frontend reads it via `fetchConfig` and gates four UI surfaces. No coordinator/engine change — the flag is a UI-visibility gate only.

**Tech Stack:** Python (Home Assistant custom integration, `attrs` store); Lit + TypeScript frontend; vitest; JSON i18n (8 languages).

**Spec:** `docs/superpowers/specs/2026-07-08-distributor-experimental-gating-design.md`

---

## Test env
- Backend: `PYTHONPATH="$NEW" "$PY" -m pytest tests/ -p _local_socket_unblock -k "<sel>" -q` (see `[[hasi-local-test-env-rebuild]]`; `$PY` = the rebuilt 3.12 venv python, `$NEW` = current scratchpad root).
- Frontend: `cd custom_components/smart_irrigation/frontend && npm test` (vitest; resolves EN via the static `en.json` import).

## File structure
- `custom_components/smart_irrigation/const.py` — new `CONF_DISTRIBUTORS_ENABLED` + default.
- `custom_components/smart_irrigation/store.py` — Config `attr.ib` + `async_load` deserialize.
- `custom_components/smart_irrigation/websockets.py` — config-update schema key.
- `custom_components/smart_irrigation/frontend/src/const.ts` — `CONF_DISTRIBUTORS_ENABLED`.
- `custom_components/smart_irrigation/frontend/src/types.ts` — `SmartIrrigationConfig.distributors_enabled`.
- `.../frontend/localize/languages/*.json` (8) — experimental toggle + page banner strings.
- `.../frontend/src/views/experimental/view-experimental.ts` — 3rd toggle card.
- `.../frontend/src/views/setup/view-setup.ts` — config fetch + hide Distributors tab.
- `.../frontend/src/views/zones/view-zone-settings.ts` — gate `_renderDistributorSelector`.
- `.../frontend/src/views/setup/view-distributor-settings.ts` — experimental banner in `_renderAdvisories`.
- Tests: `tests/test_store.py`; new `view-experimental.test.ts`, `view-setup.test.ts`, `view-zone-settings-distributor-gate.test.ts`; extend `view-distributor-settings.test.ts`.

---

## Task 1: Backend flag `distributors_enabled`

**Files:** Modify `const.py`, `store.py`, `websockets.py`; Test `tests/test_store.py`

- [ ] **Step 1: Write the failing test** — add to the `TestSmartIrrigationStorage` class in `tests/test_store.py` (after `test_config_get_and_update`, ~line 37):
```python
    async def test_distributors_enabled_config_roundtrip(self, hass) -> None:
        reg = await async_get_registry(hass)
        cfg = await reg.async_get_config()
        # New experimental flag is present and defaults off.
        assert cfg.get(const.CONF_DISTRIBUTORS_ENABLED) is False
        # A partial update round-trips without clobbering other settings.
        updated = await reg.async_update_config(
            {const.CONF_DISTRIBUTORS_ENABLED: True}
        )
        assert updated[const.CONF_DISTRIBUTORS_ENABLED] is True
        assert const.CONF_USE_WEATHER_SERVICE in updated
```

- [ ] **Step 2: Run to verify failure**
```
PYTHONPATH="$NEW" "$PY" -m pytest tests/test_store.py -p _local_socket_unblock -k distributors_enabled_config_roundtrip -q
```
Expected: FAIL — `AttributeError: ... has no attribute 'CONF_DISTRIBUTORS_ENABLED'` (or KeyError once the const exists but the attr doesn't).

- [ ] **Step 3a: const.py** — in the "Experimental features" block, immediately after the `CONF_LIVE_ESTIMATE_ENABLED` / default pair (after line 76), add:
```python
# Mechanical water distributors (Gardena-style indexing distributor): opt-in,
# experimental. Off by default. UI-visibility gate only — the distributor engine
# is already inert unless distributors are configured, so this flag never stops an
# existing cycle; it just hides the Distributors tab + the zone-side selector.
CONF_DISTRIBUTORS_ENABLED = "distributors_enabled"
CONF_DEFAULT_DISTRIBUTORS_ENABLED = False
```

- [ ] **Step 3b: store.py imports** — add `CONF_DEFAULT_DISTRIBUTORS_ENABLED` and `CONF_DISTRIBUTORS_ENABLED` to the `from .const import (...)` block (alongside the existing `CONF_DEFAULT_OBSERVED_WATERING_ENABLED` / `CONF_OBSERVED_WATERING_ENABLED` imports near lines 40–69).

- [ ] **Step 3c: store.py Config attr** — after the `live_estimate_enabled` attr.ib (line 311–313), add:
```python
    distributors_enabled = attr.ib(
        type=bool, default=CONF_DEFAULT_DISTRIBUTORS_ENABLED
    )
```

- [ ] **Step 3d: store.py async_load deserialize** — after the `live_estimate_enabled=...` block that ends at line 679, add (still inside the Config(...) construction):
```python
                distributors_enabled=data["config"].get(
                    CONF_DISTRIBUTORS_ENABLED,
                    CONF_DEFAULT_DISTRIBUTORS_ENABLED,
                ),
```

- [ ] **Step 3e: websockets.py schema** — after the `vol.Optional(const.CONF_LIVE_ESTIMATE_ENABLED): cv.boolean,` line (116), add:
```python
                vol.Optional(const.CONF_DISTRIBUTORS_ENABLED): cv.boolean,
```

- [ ] **Step 4: Run the test to green**
```
PYTHONPATH="$NEW" "$PY" -m pytest tests/test_store.py -p _local_socket_unblock -k distributors_enabled_config_roundtrip -q
```
Expected: PASS.

- [ ] **Step 5: Commit**
```
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/store.py custom_components/smart_irrigation/websockets.py tests/test_store.py
git commit -F - <<'MSG'
feat(distributor): add distributors_enabled experimental flag (backend, default off)

Config field + default + async_load deserialize + websocket config schema. Round-trips
through attr.asdict/fields_dict like the other experimental flags. UI-visibility gate only;
no engine change.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

## Task 2: Frontend flag plumbing (const.ts + types.ts)

**Files:** Modify `frontend/src/const.ts`, `frontend/src/types.ts`

- [ ] **Step 1: const.ts** — after `export const CONF_LIVE_ESTIMATE_ENABLED = "live_estimate_enabled";` (line 44), add:
```ts
export const CONF_DISTRIBUTORS_ENABLED = "distributors_enabled";
```

- [ ] **Step 2: types.ts field** — in the `SmartIrrigationConfig` interface, after `live_estimate_enabled: boolean;` (line 89), add:
```ts
  distributors_enabled: boolean;
```

- [ ] **Step 3: types.ts default** — in the class constructor that initialises defaults, after `this.live_estimate_enabled = false;` (line 134), add:
```ts
    this.distributors_enabled = false;
```

- [ ] **Step 4: Type-check**
```
cd custom_components/smart_irrigation/frontend && npx tsc --noEmit
```
Expected: no new errors.

- [ ] **Step 5: Commit**
```
git add custom_components/smart_irrigation/frontend/src/const.ts custom_components/smart_irrigation/frontend/src/types.ts
git commit -m "feat(distributor): frontend config plumbing for distributors_enabled

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: i18n — experimental toggle + page banner (8 languages)

**Files:** Modify `frontend/localize/languages/{en,de,nl,fr,es,it,no,sk}.json`

Two additions per language:
1. Under `panels.experimental` (after the `live_estimate` object, en.json line 258), a new `distributors` object with `title`/`description`/`label`/`note`.
2. Under `panels.distributors.hints` (en.json line 771 block), a new `experimental` key.

- [ ] **Step 1: en.json** — add to `panels.experimental` (after `live_estimate` closes at line 258; add a comma after the `}` then the new object):
```json
      "distributors": {
        "title": "Mechanical water distributors",
        "description": "Drive a mechanical pressure-distributor — for example a Gardena Water Distributor — that splits one supply into several outlets and advances on water on/off pulses. Assign zones to a distributor's outlets and Smart Irrigation waters them in sequence, tracks the position, and coordinates a master valve or pump. This is a new feature that could not be fully hardware-tested, so treat it as a beta.",
        "label": "Enable mechanical water distributors",
        "note": "Watch the first days of use closely and keep the device's manual override handy. You can switch it back off at any time — existing zone watering is unaffected."
      }
```
And to `panels.distributors.hints` (add after `master_off_after`, line 778):
```json
        "experimental": "Experimental feature — still being refined and not fully hardware-tested. Watch the first days of use closely and keep the device's manual override within reach."
```

- [ ] **Step 2: de.json** — same two additions, German:
```json
      "distributors": {
        "title": "Mechanische Wasserverteiler",
        "description": "Steuert einen mechanischen Druck-Verteiler — z. B. einen Gardena Wasserverteiler — der eine Zuleitung auf mehrere Abgänge aufteilt und durch An-/Aus-Impulse des Wassers weiterschaltet. Ordne Zonen den Abgängen eines Verteilers zu; Smart Irrigation bewässert sie der Reihe nach, verfolgt die Position und koordiniert ein Master-Ventil bzw. eine Pumpe. Das ist eine neue Funktion, die nicht vollständig an Hardware getestet werden konnte — behandle sie als Beta.",
        "label": "Mechanische Wasserverteiler aktivieren",
        "note": "Beobachte die ersten Tage der Nutzung genau und halte die manuelle Übersteuerung des Geräts bereit. Du kannst sie jederzeit wieder ausschalten — die bestehende Zonen-Bewässerung bleibt unberührt."
      }
```
hints:
```json
        "experimental": "Experimentelle Funktion — noch in Verfeinerung und nicht vollständig an Hardware getestet. Beobachte die ersten Tage der Nutzung genau und halte die manuelle Übersteuerung des Geräts griffbereit."
```

- [ ] **Step 3: nl, fr, es, it, no, sk** — add the SAME two structures (`panels.experimental.distributors` object + `panels.distributors.hints.experimental` string) to each, translated to match the tone of that file's existing neighbouring `observed_watering` / `live_estimate` entries and its existing `hints.*` strings. Preserve UTF-8 exactly. Each `distributors` object must have all four keys (`title`, `description`, `label`, `note`); each file gets exactly one new `hints.experimental` string. Keep the JSON valid (comma placement).

- [ ] **Step 4: Validate all 8 parse**
```
cd custom_components/smart_irrigation/frontend
node -e "for (const l of ['en','de','nl','fr','es','it','no','sk']) { const j=JSON.parse(require('fs').readFileSync('localize/languages/'+l+'.json','utf8')); if(!j.panels.experimental.distributors?.title||!j.panels.distributors.hints.experimental) throw new Error('missing keys in '+l); } console.log('all 8 have both new keys + parse OK')"
```
Expected: `all 8 have both new keys + parse OK`.

- [ ] **Step 5: Commit**
```
git add custom_components/smart_irrigation/frontend/localize/languages
git commit -m "i18n(distributor): experimental toggle + page banner strings (8 languages)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Experimental toggle card (view-experimental.ts)

**Files:** Modify `frontend/src/views/experimental/view-experimental.ts`; Create `frontend/src/views/experimental/view-experimental.test.ts`

- [ ] **Step 1: Write the failing test** — create `view-experimental.test.ts`:
```ts
import { describe, it, expect, beforeAll } from "vitest";

beforeAll(() => {
  (globalThis as any).HTMLElement = class {};
  (globalThis as any).customElements = {
    define() {},
    get() {
      return undefined;
    },
    whenDefined: () => Promise.resolve(),
  };
  (globalThis as any).window = globalThis;
});

type ViewModule = typeof import("./view-experimental");
let View: ViewModule["SmartIrrigationViewExperimental"];
beforeAll(async () => {
  ({ SmartIrrigationViewExperimental: View } = await import(
    "./view-experimental"
  ));
});

function flatten(node: any): string {
  let text = "";
  const walk = (n: any) => {
    if (n == null || typeof n === "boolean") return;
    if (Array.isArray(n)) return n.forEach(walk);
    if (n && Array.isArray(n.strings) && "values" in n) {
      text += n.strings.join("");
      return walk(n.values);
    }
    if (typeof n === "function") return;
    text += String(n);
  };
  walk(node);
  return text;
}

function make(config: any) {
  const el: any = new View();
  el.hass = { language: "en" };
  el.config = config;
  return el;
}

describe("view-experimental distributors toggle", () => {
  it("renders the distributors toggle card", () => {
    const el = make({
      observed_watering_enabled: false,
      live_estimate_enabled: false,
      distributors_enabled: false,
    });
    const text = flatten(el.render());
    expect(text).toContain("Mechanical water distributors");
    expect(text).toContain("Enable mechanical water distributors");
    // The "watch the first days" advisory is present.
    expect(text).toContain("Watch the first days of use closely");
  });
});
```

- [ ] **Step 2: Run to verify failure**
```
cd custom_components/smart_irrigation/frontend && npm test -- view-experimental 2>&1 | tail -20
```
Expected: FAIL — the distributors card is not rendered yet.

- [ ] **Step 3a: extend the flag union** — in `view-experimental.ts`, add `CONF_DISTRIBUTORS_ENABLED` to the import from `"../../const"` (line 12–16) and to the `ExperimentalFlag` union (line 21–23):
```ts
type ExperimentalFlag =
  | typeof CONF_OBSERVED_WATERING_ENABLED
  | typeof CONF_LIVE_ESTIMATE_ENABLED
  | typeof CONF_DISTRIBUTORS_ENABLED;
```

- [ ] **Step 3b: render the 3rd card** — in `render()` (after the `live_estimate` toggle card, line 107), add:
```ts
      ${this._renderToggleCard(
        "distributors",
        CONF_DISTRIBUTORS_ENABLED,
        this.config.distributors_enabled,
      )}
```
No other change — `_renderToggleCard` already resolves `panels.experimental.distributors.{title,description,label,note}`.

- [ ] **Step 4: Run the test to green**
```
cd custom_components/smart_irrigation/frontend && npm test -- view-experimental 2>&1 | tail -20
```
Expected: PASS.

- [ ] **Step 5: Commit**
```
git add custom_components/smart_irrigation/frontend/src/views/experimental/view-experimental.ts custom_components/smart_irrigation/frontend/src/views/experimental/view-experimental.test.ts
git commit -m "feat(experimental): distributors opt-in toggle card

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Gate the Distributors tab (view-setup.ts)

**Files:** Modify `frontend/src/views/setup/view-setup.ts`; Create `frontend/src/views/setup/view-setup.test.ts`

- [ ] **Step 1: Write the failing test** — create `view-setup.test.ts`:
```ts
import { describe, it, expect, beforeAll } from "vitest";

beforeAll(() => {
  (globalThis as any).HTMLElement = class {};
  (globalThis as any).customElements = {
    define() {},
    get() {
      return undefined;
    },
    whenDefined: () => Promise.resolve(),
  };
  (globalThis as any).window = globalThis;
});

type ViewModule = typeof import("./view-setup");
let View: ViewModule["SmartIrrigationViewSetup"];
beforeAll(async () => {
  ({ SmartIrrigationViewSetup: View } = await import("./view-setup"));
});

function flatten(node: any): string {
  let text = "";
  const walk = (n: any) => {
    if (n == null || typeof n === "boolean") return;
    if (Array.isArray(n)) return n.forEach(walk);
    if (n && Array.isArray(n.strings) && "values" in n) {
      text += n.strings.join("");
      return walk(n.values);
    }
    if (typeof n === "function") return;
    text += String(n);
  };
  walk(node);
  return text;
}

function make(distributorsEnabled: boolean | undefined) {
  const el: any = new View();
  el.hass = { language: "en" };
  el.config =
    distributorsEnabled === undefined
      ? undefined
      : { distributors_enabled: distributorsEnabled };
  return el;
}

describe("view-setup distributors tab gating", () => {
  it("hides the Distributors nav tab when the flag is off", () => {
    const text = flatten(make(false).render());
    expect(text).not.toContain("Distributors");
  });

  it("shows the Distributors nav tab when the flag is on", () => {
    const text = flatten(make(true).render());
    expect(text).toContain("Distributors");
  });

  it("hides the tab while config is still loading (flag unknown)", () => {
    const text = flatten(make(undefined).render());
    expect(text).not.toContain("Distributors");
  });
});
```

- [ ] **Step 2: Run to verify failure**
```
cd custom_components/smart_irrigation/frontend && npm test -- view-setup 2>&1 | tail -20
```
Expected: FAIL — the Distributors tab renders unconditionally today, so the "hides" cases fail.

- [ ] **Step 3a: imports + config state** — in `view-setup.ts`, change the class to fetch config like `view-experimental` does. Update the imports at the top: add
```ts
import { UnsubscribeFunc } from "home-assistant-js-websocket";
import { fetchConfig } from "../../data/websockets";
import { SubscribeMixin } from "../../subscribe-mixin";
import { SmartIrrigationConfig } from "../../types";
import { DOMAIN } from "../../const";
```
(keep the existing imports). Change the class declaration and add the state + subscription:
```ts
@customElement("smart-irrigation-view-setup")
export class SmartIrrigationViewSetup extends SubscribeMixin(LitElement) {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property({ type: Boolean }) public narrow!: boolean;
  @property({ attribute: false }) public path?: Path;

  @state() private _config?: SmartIrrigationConfig;

  public hassSubscribe(): Promise<UnsubscribeFunc>[] {
    this._fetchConfig();
    return [
      this.hass!.connection.subscribeMessage(() => this._fetchConfig(), {
        type: DOMAIN + "_config_updated",
      }),
    ];
  }

  private async _fetchConfig(): Promise<void> {
    if (!this.hass) return;
    try {
      this._config = await fetchConfig(this.hass);
    } catch (error) {
      console.error("Failed to fetch setup config:", error);
    }
  }

  private get _distributorsEnabled(): boolean {
    return this._config?.distributors_enabled ?? false;
  }
```
Add `state` to the `lit/decorators.js` import (`import { property, customElement, state } from "lit/decorators.js";`).

- [ ] **Step 3b: gate nav + content** — replace the `render()` body's `activeTab` line and the nav `.map` so the Distributors tab is filtered out and a stale deep-link falls back. In `render()`:
```ts
  render() {
    if (!this.hass) return html``;

    const enabled = this._distributorsEnabled;
    const tabs = (Object.values(ESetupTab) as ESetupTab[]).filter(
      (t) => t !== ESetupTab.Distributors || enabled,
    );
    let activeTab = this._activeTab;
    if (activeTab === ESetupTab.Distributors && !enabled) {
      activeTab = ESetupTab.WeatherLocation;
    }
    return html`
      <div class="setup-container">
        <nav class="setup-nav">
          ${tabs.map(
            (tab) => html`
              <button
                class="setup-nav-btn ${activeTab === tab ? "active" : ""}"
                @click="${() => this._selectTab(tab)}"
              >
                ${localize(SETUP_TAB_LABELS[tab], this.hass.language)}
              </button>
            `,
          )}
          <button
            class="setup-nav-btn wizard-btn"
            @click="${this._openWizard}"
            title="${localize("wizard.title", this.hass.language)}"
          >
            <ha-icon icon="mdi:creation"></ha-icon>
            ${localize("wizard.open_button", this.hass.language)}
          </button>
        </nav>
        <div class="setup-content">${this._renderContent(activeTab)}</div>
      </div>
    `;
  }
```
(No change to `_renderContent`, `_activeTab`, `_selectTab`, styles.)

- [ ] **Step 4: Run test + type-check**
```
cd custom_components/smart_irrigation/frontend && npm test -- view-setup 2>&1 | tail -20 && npx tsc --noEmit
```
Expected: 3 tests PASS; no type errors.

- [ ] **Step 5: Commit**
```
git add custom_components/smart_irrigation/frontend/src/views/setup/view-setup.ts custom_components/smart_irrigation/frontend/src/views/setup/view-setup.test.ts
git commit -m "feat(setup): hide the Distributors tab unless the experimental flag is on

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Gate the zone-side distributor selector (view-zone-settings.ts)

**Files:** Modify `frontend/src/views/zones/view-zone-settings.ts`; Create `frontend/src/views/zones/view-zone-settings-distributor-gate.test.ts`

- [ ] **Step 1: Write the failing test** — create `view-zone-settings-distributor-gate.test.ts`:
```ts
import { describe, it, expect, beforeAll } from "vitest";

beforeAll(() => {
  (globalThis as any).HTMLElement = class {};
  (globalThis as any).customElements = {
    define() {},
    get() {
      return undefined;
    },
    whenDefined: () => Promise.resolve(),
  };
  (globalThis as any).window = globalThis;
});

type ViewModule = typeof import("./view-zone-settings");
let View: ViewModule["SmartIrrigationViewZoneSettings"];
beforeAll(async () => {
  ({ SmartIrrigationViewZoneSettings: View } = await import(
    "./view-zone-settings"
  ));
});

function flatten(node: any): string {
  let text = "";
  const walk = (n: any) => {
    if (n == null || typeof n === "boolean") return;
    if (Array.isArray(n)) return n.forEach(walk);
    if (n && Array.isArray(n.strings) && "values" in n) {
      text += n.strings.join("");
      return walk(n.values);
    }
    if (typeof n === "function") return;
    text += String(n);
  };
  walk(node);
  return text;
}

function make(distributorsEnabled: boolean) {
  const el: any = new View();
  el.hass = { language: "en" };
  el.config = { distributors_enabled: distributorsEnabled };
  el.distributors = [];
  return el;
}

const ZONE = { id: 1, name: "Lawn", distributor_id: null };

describe("view-zone-settings distributor selector gating", () => {
  it("hides the distributor selector when the feature is off", () => {
    const el = make(false);
    const text = flatten(el._renderDistributorSelector(ZONE, 0));
    expect(text).not.toContain("Water distributor");
  });

  it("shows the distributor selector when the feature is on", () => {
    const el = make(true);
    const text = flatten(el._renderDistributorSelector(ZONE, 0));
    expect(text).toContain("Water distributor");
  });
});
```

- [ ] **Step 2: Run to verify failure**
```
cd custom_components/smart_irrigation/frontend && npm test -- view-zone-settings-distributor-gate 2>&1 | tail -20
```
Expected: FAIL — the "off" case still contains "Water distributor" (selector renders unconditionally today).

- [ ] **Step 3: Gate the selector** — in `view-zone-settings.ts`, at the very top of `_renderDistributorSelector` (line 482–486), after the existing `if (!this.hass) return html``;` guard, add:
```ts
    // Distributor membership is an opt-in experimental feature — hide the whole
    // selector when it is off so zones show only their standalone controls.
    if (!this.config?.distributors_enabled) return html``;
```
(Everything below is unchanged. The call site at line 982 stays `${this._renderDistributorSelector(zone, index)}`; the `distributor_managed` note at 983–989 is only reached when a zone already has `distributor_id != null`, which cannot happen on a fresh install where the feature was never enabled.)

- [ ] **Step 4: Run test + type-check**
```
cd custom_components/smart_irrigation/frontend && npm test -- view-zone-settings-distributor-gate 2>&1 | tail -20 && npx tsc --noEmit
```
Expected: both tests PASS; no type errors.

- [ ] **Step 5: Commit**
```
git add custom_components/smart_irrigation/frontend/src/views/zones/view-zone-settings.ts custom_components/smart_irrigation/frontend/src/views/zones/view-zone-settings-distributor-gate.test.ts
git commit -m "feat(zones): hide the distributor selector unless the experimental flag is on

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Experimental banner on the distributor page (view-distributor-settings.ts)

**Files:** Modify `frontend/src/views/setup/view-distributor-settings.ts`; Test `frontend/src/views/setup/view-distributor-settings.test.ts`

- [ ] **Step 1: Write the failing test** — add to `view-distributor-settings.test.ts` (a new `describe` block; the `flatten` helper + shim already exist in that file):
```ts
describe("view-distributor-settings experimental banner", () => {
  it("renders the experimental advisory at the top of the advisories", () => {
    const el: any = new SmartIrrigationViewDistributorSettings();
    el.hass = { language: "en" };
    el.config = {};
    const text = flatten(el._renderAdvisories()).text;
    expect(text).toContain("not fully hardware-tested");
    expect(text).toContain("Watch the first days of use closely");
  });
});
```

- [ ] **Step 2: Run to verify failure**
```
cd custom_components/smart_irrigation/frontend && npm test -- view-distributor-settings 2>&1 | tail -20
```
Expected: the new test FAILS (banner not rendered); the existing set-outlet tests still pass.

- [ ] **Step 3: Add the banner** — in `_renderAdvisories()` (line 667), add the experimental advisory as the FIRST child of `<div class="advisories">`, before the `pressure` advisory (line 678). The returned template becomes:
```ts
    return html`
      <div class="advisories">
        <div class="advisory">
          <ha-icon icon="mdi:flask-outline"></ha-icon>
          <span
            >${localize("panels.distributors.hints.experimental", lang)}</span
          >
        </div>
        <div class="advisory">
          <ha-icon icon="mdi:water-alert-outline"></ha-icon>
          <span>${localize("panels.distributors.hints.pressure", lang)}</span>
        </div>
        ${parallel
          ? html`<div class="advisory">
```
(the rest of the method is unchanged).

- [ ] **Step 4: Run tests + type-check**
```
cd custom_components/smart_irrigation/frontend && npm test -- view-distributor-settings 2>&1 | tail -20 && npx tsc --noEmit
```
Expected: new test + existing set-outlet tests PASS; no type errors.

- [ ] **Step 5: Commit**
```
git add custom_components/smart_irrigation/frontend/src/views/setup/view-distributor-settings.ts custom_components/smart_irrigation/frontend/src/views/setup/view-distributor-settings.test.ts
git commit -m "feat(distributor): experimental advisory banner on the distributor page

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Regression + build + b28 release

- [ ] **Step 1: Full frontend suite**
```
cd custom_components/smart_irrigation/frontend && npm test 2>&1 | tail -8
```
Expected: all vitest tests pass (existing + the 4 new/extended files).

- [ ] **Step 2: Backend distributor + store regression** (no engine change, but confirm nothing broke)
```
PYTHONPATH="$NEW" "$PY" -m pytest tests/test_store.py tests/test_store_distributor.py tests/test_distributor_integration.py -p _local_socket_unblock -q
```
Expected: green (baseline pre-existing failures, if any, unchanged — none in store/distributor per `[[hasi-local-test-env-rebuild]]`).

- [ ] **Step 3: Version bump b27 → b28** in `const.py`, `manifest.json`, `frontend/package.json`; then `cd frontend && npm run build`; verify the new EN strings are baked:
```
grep -c "Mechanical water distributors" dist/smart-irrigation.js
grep -c "not fully hardware-tested" dist/smart-irrigation.js
```
Expected: both `1`.

- [ ] **Step 4: Commit build + version**, then **release** — show notes for approval (REGEL 5), push `origin feature/gardena-distributor`, then `gh release create v2026.07.11b28 --repo Eifel-Joe/HAsmartirrigation --prerelease --target feature/gardena-distributor` (after explicit user go).

- [ ] **Step 5: Update memory** — `hasi-distributor-fix-roadmap` (experimental gating shipped in b28) + note the pending docs + upstream-PR steps.

---

## Self-review

- **Spec coverage:** backend flag (Task 1) ✓; frontend plumbing (Task 2) ✓; experimental toggle card (Task 4) ✓; Setup tab gate + deep-link guard (Task 5) ✓; zone selector gate (Task 6) ✓; distributor page banner (Task 7) ✓; i18n 8 langs both keys (Task 3) ✓; `view-zones.ts` intentionally untouched (spec: naturally inert) ✓; engine unchanged ✓; b28 release (Task 8) ✓. Docs explicitly out of scope (separate follow-up) — matches spec.
- **Ordering:** i18n (Task 3) precedes the frontend view tests (Tasks 4–7) so their render assertions resolve real EN strings from the static `en.json` import.
- **Type/name consistency:** `distributors_enabled` (snake) everywhere backend + config; `CONF_DISTRIBUTORS_ENABLED` const in both `const.py` and `const.ts`; `SmartIrrigationConfig.distributors_enabled`; `_distributorsEnabled` getter; i18n keys `panels.experimental.distributors.*` + `panels.distributors.hints.experimental` used identically in code and JSON.
- **Placeholders:** none — every code step shows the exact code. Task 3 step 3 (6 languages) is a defined translation task with EN+DE as the source of truth and the neighbouring experimental entries as the tone reference, verified by a spec-review; not a code placeholder.
- **Edge case (accepted):** zone pre-assigned then flag turned off — selector hidden, membership persists; unreachable on fresh upstream. Documented in spec.
