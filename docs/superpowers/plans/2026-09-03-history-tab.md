# History Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the per-zone run history out of the zone settings card into its own top-level "Verlauf" (History) tab with a zone selector.

**Architecture:** Extract the existing history render into a standalone presentational component `si-zone-history`; a new `view-history` view renders a zone dropdown plus `si-zone-history` for the selected zone; register a new `history` tab; remove the history from `view-zone-settings`.

**Tech Stack:** Lit + TypeScript, Vitest, the panel's own `localize` catalogue (`frontend/localize/languages/*.json`).

Run all commands from `custom_components/smart_irrigation/frontend/`.

---

## File Structure

- **Create** `src/components/si-zone-history.ts` — presentational history for ONE zone (usage total + runs table). Props: `hass`, `zone`, `config`. No data fetching.
- **Create** `src/components/si-zone-history.test.ts` — unit tests.
- **Create** `src/views/history/view-history.ts` — the History tab: zone dropdown + `si-zone-history`. Self-fetches zones/config via `SubscribeMixin`.
- **Create** `src/views/history/view-history.test.ts` — unit tests.
- **Modify** `src/smart-irrigation.ts` — add `EMenuItems.History` and a `getView` case.
- **Modify** `src/views/zones/view-zone-settings.ts` — remove the history call, the two render methods, and the history-only CSS.
- **Modify** `localize/languages/{en,de,es,fr,it,nl,no,sk}.json` — add `panels.history.{title,select_zone,no_zones}`.

Import-path note: `src/components/*` mirrors `si-schedule-dialog.ts` (`../types`, `../../localize/localize`, `../common/units`, `../common/datetime`, `../styles/global-style`, `../const`). `src/views/history/*` mirrors `src/views/zones/*` (`../../types`, `../../../localize/localize`, `../../subscribe-mixin`, `../../data/websockets`, `../../common/navigation`).

---

## Task 1: `si-zone-history` component

**Files:**
- Create: `src/components/si-zone-history.ts`
- Test: `src/components/si-zone-history.test.ts`
- Source to move from: `src/views/zones/view-zone-settings.ts` — `_renderRunHistory` (~1826-1869), `_renderRunLogRow` (~1871-1921), and the `.history-*` CSS (~2237-2288).

- [ ] **Step 1: Write the failing test**

Create `src/components/si-zone-history.test.ts`:

```ts
import { describe, it, expect, beforeAll } from "vitest";

// DOM-free shim, same as si-schedule-dialog.test.ts: define + instantiate the
// LitElement subclass without a real registry, call render() and introspect
// the returned template tree.
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

type Mod = typeof import("./si-zone-history");
let SiZoneHistory: Mod["SiZoneHistory"];

beforeAll(async () => {
  ({ SiZoneHistory } = await import("./si-zone-history"));
});

// Flatten a lit TemplateResult tree into concatenated static HTML plus values,
// mirroring si-schedule-dialog.test.ts's helper.
function flatten(node: any): { text: string; values: any[] } {
  const out = { text: "", values: [] as any[] };
  const walk = (n: any) => {
    if (n == null || typeof n === "boolean") return;
    if (Array.isArray(n)) return n.forEach(walk);
    if (n && Array.isArray(n.strings) && "values" in n) {
      out.text += n.strings.join("");
      return walk(n.values);
    }
    out.values.push(n);
    out.text += String(n);
  };
  walk(node);
  return out;
}

function makeEl(zone: any, config: any = { units: "metric" }) {
  const el: any = new SiZoneHistory();
  el.hass = { language: "en" };
  el.zone = zone;
  el.config = config;
  return el;
}

describe("si-zone-history", () => {
  it("renders the cumulative usage and a runs table for a zone with runs", () => {
    const el = makeEl({
      id: 1,
      name: "Front",
      water_used_total: 42,
      run_log: [
        { ts: 1000, result: "completed", volume_l: 12, detail: "" },
      ],
    });
    const { text, values } = flatten(el.render());
    expect(text).toContain('class="history-usage"');
    expect(text).toContain('class="history-table"');
    // The result token is interpolated, so flatten() appends it to `values`
    // rather than inline in `text` (same convention as si-schedule-dialog.test.ts).
    expect(text).toContain('class="history-chip history-');
    expect(values).toContain("completed");
    expect(text).not.toContain('class="weather-note"');
  });

  it("renders the empty note and no table when the run log is empty", () => {
    const el = makeEl({ id: 1, name: "Front", water_used_total: 0, run_log: [] });
    const { text } = flatten(el.render());
    expect(text).toContain('class="weather-note"');
    expect(text).not.toContain('class="history-table"');
  });

  it("renders one row per log entry", () => {
    const el = makeEl({
      id: 1,
      name: "Front",
      water_used_total: 5,
      run_log: [
        { ts: 1000, result: "watered", volume_l: 3, detail: "" },
        { ts: 2000, result: "skipped", volume_l: 0, detail: "rain" },
      ],
    });
    const chips = (flatten(el.render()).text.match(/history-chip/g) || []).length;
    expect(chips).toBe(2);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/components/si-zone-history.test.ts`
Expected: FAIL — cannot resolve `./si-zone-history` (module does not exist yet).

- [ ] **Step 3: Create the component**

Create `src/components/si-zone-history.ts`. The `render`/`_renderRow` bodies are `_renderRunHistory` and `_renderRunLogRow` moved verbatim, minus the wrapping `ha-expansion-panel` and `card-content` (inside its own tab the history is not collapsible), reading `this.zone`/`this.config` instead of parameters:

```ts
import { LitElement, html, css, CSSResultGroup, TemplateResult } from "lit";
import { property, customElement } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import {
  HomeAssistant,
  SmartIrrigationConfig,
  SmartIrrigationZone,
  RunLogEntry,
} from "../types";
import { localize } from "../../localize/localize";
import { formatVolume } from "../common/units";
import { formatDateTime } from "../common/datetime";
import { globalStyle } from "../styles/global-style";
import { CONF_METRIC } from "../const";

/** Cumulative water usage + a bounded "Recent runs" list for ONE zone.
 * Pure presentation: extracted from view-zone-settings so it can live on the
 * History tab. Reuses the existing panels.zones.history.* strings. */
@customElement("si-zone-history")
export class SiZoneHistory extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) zone!: SmartIrrigationZone;
  @property({ attribute: false }) config?: SmartIrrigationConfig;

  render(): TemplateResult {
    if (!this.hass || !this.zone) return html``;
    const metric = this.config?.units === CONF_METRIC;
    const log = this.zone.run_log ?? [];
    const lang = this.hass.language;

    return html`
      <div class="history-usage">
        <span class="history-usage-label"
          >${localize("panels.zones.history.total_used", lang)}</span
        >
        <span class="history-usage-value"
          >${formatVolume(this.zone.water_used_total ?? 0, metric)}</span
        >
      </div>
      ${log.length === 0
        ? html`<div class="weather-note">
            ${localize("panels.zones.history.empty", lang)}
          </div>`
        : html`
            <table class="history-table">
              <thead>
                <tr>
                  <th>${localize("panels.zones.history.when", lang)}</th>
                  <th>${localize("panels.zones.history.result", lang)}</th>
                  <th class="num">
                    ${localize("panels.zones.history.volume", lang)}
                  </th>
                  <th>${localize("panels.zones.history.detail", lang)}</th>
                </tr>
              </thead>
              <tbody>
                ${log.map((entry) => this._renderRow(entry, metric))}
              </tbody>
            </table>
          `}
    `;
  }

  private _renderRow(entry: RunLogEntry, metric: boolean): TemplateResult {
    const lang = this.hass.language;
    const resultLabel = localize(
      `panels.zones.history.results.${entry.result}`,
      lang,
    );
    let detail = "";
    if (entry.detail) {
      if (entry.result === "skipped") {
        detail = entry.detail
          .split(",")
          .map((r) => localize(`panels.zones.outlook.checks.${r}`, lang) || r)
          .join(", ");
      } else if (/^[A-Za-z0-9_-]+$/.test(entry.detail)) {
        detail =
          localize(`panels.zones.fault.${entry.detail}`, lang) || entry.detail;
      } else {
        detail = entry.detail;
      }
    }
    return html`
      <tr>
        <td>${formatDateTime(entry.ts)}</td>
        <td>
          <span class="history-chip history-${entry.result}"
            >${resultLabel || entry.result}</span
          >
        </td>
        <td class="num">
          ${entry.volume_l > 0 ? formatVolume(entry.volume_l, metric) : "-"}
        </td>
        <td class="history-detail">${unsafeHTML(detail)}</td>
      </tr>
    `;
  }

  static get styles(): CSSResultGroup {
    return [
      globalStyle,
      css`
        /* Moved verbatim from view-zone-settings.ts (lines 2237-2292). The
           empty-state .weather-note rule is NOT copied: it lives in
           globalStyle, which is already included above. */
        .history-usage {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          margin-bottom: 12px;
        }
        .history-usage-value {
          font-size: 1.25rem;
          font-weight: 600;
        }
        .history-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.875rem;
        }
        .history-table th,
        .history-table td {
          text-align: left;
          padding: 4px 8px;
          border-bottom: 1px solid var(--divider-color);
          vertical-align: top;
        }
        .history-table th.num,
        .history-table td.num {
          text-align: right;
          white-space: nowrap;
        }
        .history-detail {
          color: var(--secondary-text-color);
        }
        .history-chip {
          display: inline-block;
          padding: 1px 8px;
          border-radius: 10px;
          font-size: 0.75rem;
          font-weight: 600;
          white-space: nowrap;
          color: #fff;
          background: var(--secondary-text-color);
        }
        .history-completed {
          background: var(--success-color, #2e7d32);
        }
        .history-partial {
          background: var(--warning-color, #f9a825);
        }
        .history-failed {
          background: var(--error-color, #c62828);
        }
        .history-skipped {
          background: var(--info-color, #0277bd);
        }
        .history-observed {
          background: #00897b;
        }
      `,
    ];
  }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx vitest run src/components/si-zone-history.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/components/si-zone-history.ts src/components/si-zone-history.test.ts
git commit -m "feat(history): extract si-zone-history presentational component"
```

---

## Task 2: History tab i18n strings (all 8 languages)

**Files:**
- Modify: `localize/languages/en.json`, `de.json`, `es.json`, `fr.json`, `it.json`, `nl.json`, `no.json`, `sk.json`

Add a new `history` object under the existing top-level `panels` object (a sibling of `panels.zones` / `panels.setup`), with these three keys. Values per language:

| lang | title | select_zone | no_zones |
|---|---|---|---|
| en | History | Select zone | No zones configured yet. |
| de | Verlauf | Zone auswählen | Noch keine Zonen konfiguriert. |
| es | Historial | Seleccionar zona | Aún no hay zonas configuradas. |
| fr | Historique | Sélectionner une zone | Aucune zone configurée pour le moment. |
| it | Cronologia | Seleziona zona | Nessuna zona configurata. |
| nl | Geschiedenis | Zone selecteren | Nog geen zones geconfigureerd. |
| no | Historikk | Velg sone | Ingen soner konfigurert ennå. |
| sk | História | Vybrať zónu | Zatiaľ nie sú nakonfigurované žiadne zóny. |

- [ ] **Step 1: Write the failing test**

Add to `src/components/si-zone-history.test.ts` a new describe block (the localize catalogue is bundled, so this loads the real en.json):

```ts
import { localize } from "../../localize/localize";

describe("history tab strings exist", () => {
  it("has the tab title, selector label and no-zones note in English", () => {
    expect(localize("panels.history.title", "en")).toBe("History");
    expect(localize("panels.history.select_zone", "en")).toBe("Select zone");
    expect(localize("panels.history.no_zones", "en")).toBe(
      "No zones configured yet.",
    );
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/components/si-zone-history.test.ts -t "history tab strings"`
Expected: FAIL — the keys are missing, so `localize` returns the key or "".

- [ ] **Step 3: Add the keys to all eight language files**

In each `localize/languages/<lang>.json`, inside the `"panels"` object, add:

```json
"history": {
  "title": "<title from table>",
  "select_zone": "<select_zone from table>",
  "no_zones": "<no_zones from table>"
},
```

Place it after the `"zones"` entry (JSON key order is irrelevant to lookup; consistent placement keeps diffs readable). Keep each file valid JSON (mind the trailing comma).

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx vitest run src/components/si-zone-history.test.ts -t "history tab strings"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add localize/languages/*.json src/components/si-zone-history.test.ts
git commit -m "i18n(history): add History tab strings in all 8 languages"
```

---

## Task 3: `view-history` view (zone selector + history)

**Files:**
- Create: `src/views/history/view-history.ts`
- Test: `src/views/history/view-history.test.ts`
- Reference pattern: `src/views/zones/view-zone-settings.ts` (SubscribeMixin, `fetchZones`, `fetchConfig`, `hassSubscribe`).

- [ ] **Step 1: Write the failing test**

Create `src/views/history/view-history.test.ts`:

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

type Mod = typeof import("./view-history");
let SmartIrrigationViewHistory: Mod["SmartIrrigationViewHistory"];

beforeAll(async () => {
  ({ SmartIrrigationViewHistory } = await import("./view-history"));
});

function flatten(node: any): { text: string; values: any[] } {
  const out = { text: "", values: [] as any[] };
  const walk = (n: any) => {
    if (n == null || typeof n === "boolean") return;
    if (Array.isArray(n)) return n.forEach(walk);
    if (n && Array.isArray(n.strings) && "values" in n) {
      out.text += n.strings.join("");
      return walk(n.values);
    }
    out.values.push(n);
    out.text += String(n);
  };
  walk(node);
  return out;
}

function makeView(zones: any[]) {
  const el: any = new SmartIrrigationViewHistory();
  el.hass = { language: "en" };
  el._config = { units: "metric" };
  el._zones = zones;
  return el;
}

describe("view-history", () => {
  it("defaults the selected zone to the first zone and renders its history", () => {
    const el = makeView([
      { id: 1, name: "Front", run_log: [], water_used_total: 0 },
      { id: 2, name: "Back", run_log: [], water_used_total: 0 },
    ]);
    // No selection made yet -> the effective selection is the first zone.
    expect(el._effectiveZone().id).toBe(1);
    const { text } = flatten(el.render());
    expect(text).toContain("<si-zone-history");
    expect(text).toContain("<select");
  });

  it("renders the chosen zone after the selector changes", () => {
    const el = makeView([
      { id: 1, name: "Front", run_log: [], water_used_total: 0 },
      { id: 2, name: "Back", run_log: [], water_used_total: 0 },
    ]);
    el._selectedZoneId = 2;
    expect(el._effectiveZone().id).toBe(2);
  });

  it("falls back to the first zone when the selected zone no longer exists", () => {
    const el = makeView([
      { id: 1, name: "Front", run_log: [], water_used_total: 0 },
      { id: 2, name: "Back", run_log: [], water_used_total: 0 },
    ]);
    el._selectedZoneId = 999; // a zone that was deleted
    expect(el._effectiveZone().id).toBe(1);
  });

  it("shows the no-zones note when there are no zones", () => {
    const el = makeView([]);
    const { text } = flatten(el.render());
    expect(text).toContain("No zones configured yet.");
    expect(text).not.toContain("<si-zone-history");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/views/history/view-history.test.ts`
Expected: FAIL — cannot resolve `./view-history`.

- [ ] **Step 3: Create the view**

Create `src/views/history/view-history.ts`. Model the data loading on `view-zone-settings.ts`'s `hassSubscribe` (fetch zones + config; re-fetch on the domain's state-changed event). Keep it minimal — this view only reads.

```ts
import { LitElement, html, css, CSSResultGroup, TemplateResult } from "lit";
import { property, state, customElement } from "lit/decorators.js";
import { UnsubscribeFunc } from "home-assistant-js-websocket";
import { HomeAssistant, SmartIrrigationConfig, SmartIrrigationZone } from "../../types";
import { SubscribeMixin } from "../../subscribe-mixin";
import { fetchConfig, fetchZones } from "../../data/websockets";
import { Path } from "../../common/navigation";
import { DOMAIN } from "../../const";
import { globalStyle } from "../../styles/global-style";
import { localize } from "../../../localize/localize";
import "../../components/si-zone-history";

@customElement("smart-irrigation-view-history")
export class SmartIrrigationViewHistory extends SubscribeMixin(LitElement) {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property({ type: Boolean }) public narrow!: boolean;
  @property({ attribute: false }) public path?: Path;

  @state() private _zones: SmartIrrigationZone[] = [];
  @state() private _config?: SmartIrrigationConfig;
  @state() private _selectedZoneId?: number;

  // Same self-fetch pattern as view-zone-settings.ts (hassSubscribe ~line 252):
  // fetch on connect and re-fetch on the domain's config-updated message.
  public hassSubscribe(): Promise<UnsubscribeFunc>[] {
    this._fetchData().catch(() => {});
    return [
      this.hass!.connection.subscribeMessage(
        () => this._fetchData().catch(() => {}),
        { type: DOMAIN + "_config_updated" },
      ),
    ];
  }

  private async _fetchData(): Promise<void> {
    if (!this.hass) return;
    const [config, zones] = await Promise.all([
      fetchConfig(this.hass),
      fetchZones(this.hass),
    ]);
    this._config = config;
    this._zones = zones;
  }

  /** The zone whose history is shown: the explicit selection if it still
   * exists, otherwise the first zone. */
  private _effectiveZone(): SmartIrrigationZone | undefined {
    if (!this._zones.length) return undefined;
    return (
      this._zones.find((z) => z.id === this._selectedZoneId) ?? this._zones[0]
    );
  }

  render(): TemplateResult {
    if (!this.hass) return html``;
    const lang = this.hass.language;

    if (!this._zones.length) {
      return html`
        <ha-card header="${localize("panels.history.title", lang)}">
          <div class="card-content">
            <div class="weather-note">
              ${localize("panels.history.no_zones", lang)}
            </div>
          </div>
        </ha-card>
      `;
    }

    const zone = this._effectiveZone()!;
    return html`
      <ha-card header="${localize("panels.history.title", lang)}">
        <div class="card-content">
          <div class="zone-picker">
            <label for="zone-select"
              >${localize("panels.history.select_zone", lang)}</label
            >
            <select
              id="zone-select"
              @change=${(e: Event) => {
                this._selectedZoneId = Number(
                  (e.target as HTMLSelectElement).value,
                );
              }}
            >
              ${this._zones.map(
                (z) => html`
                  <option value="${z.id}" ?selected=${z.id === zone.id}>
                    ${z.name}
                  </option>
                `,
              )}
            </select>
          </div>
          <si-zone-history
            .hass=${this.hass}
            .zone=${zone}
            .config=${this._config}
          ></si-zone-history>
        </div>
      </ha-card>
    `;
  }

  static get styles(): CSSResultGroup {
    return [
      globalStyle,
      css`
        .zone-picker {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 16px;
        }
        .zone-picker select {
          flex: 1;
        }
      `,
    ];
  }
}
```

The subscribe pattern above matches `view-zone-settings.ts` (`hassSubscribe` at ~line 252: `subscribeMessage(..., { type: DOMAIN + "_config_updated" })`, `_fetchData` doing `Promise.all([fetchConfig, fetchZones])`). Keep them in sync.

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx vitest run src/views/history/view-history.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/views/history/view-history.ts src/views/history/view-history.test.ts
git commit -m "feat(history): add the History tab view with a zone selector"
```

---

## Task 4: Register the History tab

**Files:**
- Modify: `src/smart-irrigation.ts` (`EMenuItems` enum ~line 22-25; `getView` switch ~line 189+)

- [ ] **Step 1: Add the enum value (tab order Zonen | Verlauf | Einrichtung)**

Change:

```ts
enum EMenuItems {
  Zones = "zones",
  Setup = "setup",
}
```

to:

```ts
enum EMenuItems {
  Zones = "zones",
  History = "history",
  Setup = "setup",
}
```

- [ ] **Step 2: Add the getView case + import**

At the top of `smart-irrigation.ts`, add the view import alongside the other view imports:

```ts
import "./views/history/view-history";
```

In `getView`, add a case (mirroring the `zones`/`setup` cases):

```ts
      case "history":
        return html`
          <smart-irrigation-view-history
            .hass=${this.hass}
            .narrow=${this.narrow}
            .path=${path}
          ></smart-irrigation-view-history>
        `;
```

(If the file imports views by side-effect elsewhere, match that style. Confirm whether `smart-irrigation-view-zones` is imported explicitly or bundled and follow the same convention.)

- [ ] **Step 3: Build to verify it compiles and the tab renders**

Run: `npm run build`
Expected: lint + rollup succeed with no errors.

- [ ] **Step 4: Commit**

```bash
git add src/smart-irrigation.ts
git commit -m "feat(history): register the History tab between Zones and Setup"
```

---

## Task 5: Remove the history from zone settings

**Files:**
- Modify: `src/views/zones/view-zone-settings.ts`

- [ ] **Step 1: Remove the call**

Delete the history call and its comment (~lines 1814-1815):

```ts
              <!-- Run history + cumulative water usage (WS-2) -->
              ${this._renderRunHistory(zone)}
```

- [ ] **Step 2: Remove the two methods**

Delete `_renderRunHistory(zone)` (~1826-1869) and `_renderRunLogRow(entry, metric)` (~1871-1921) entirely.

- [ ] **Step 3: Remove the now-unused history CSS**

Delete the history rules at lines 2237-2292 — they now live in `si-zone-history`:
`.history-usage`, `.history-usage-value`, `.history-table` (+ `th`/`td`, `th.num`/`td.num`), `.history-detail`, `.history-chip`, `.history-completed`, `.history-partial`, `.history-failed`, `.history-skipped`, `.history-observed`. Before deleting each, grep the file to confirm no other markup in this view still uses it. Do NOT touch `.weather-note` — it is defined in `globalStyle`, not here.

- [ ] **Step 4: Remove now-unused imports**

Grep the file for `formatDateTime` and `RunLogEntry`; if the history methods were their only users, remove them from the imports. Leave `formatVolume`, `unsafeHTML`, `CONF_METRIC` if still used elsewhere (check each).

- [ ] **Step 5: Build + run the view-zone-settings tests**

Run: `npm run build && npx vitest run src/views/zones`
Expected: build succeeds (no unused-symbol lint errors); existing zone-settings tests pass. If a zone-settings test asserted on history markup, move that assertion to `si-zone-history.test.ts` (history is no longer this view's responsibility).

- [ ] **Step 6: Commit**

```bash
git add src/views/zones/view-zone-settings.ts
git commit -m "refactor(zones): drop the history section, now on the History tab"
```

---

## Task 6: Full suite + build + live verification

- [ ] **Step 1: Full frontend suite**

Run: `npx vitest run`
Expected: all test files pass.

- [ ] **Step 2: Build**

Run: `npm run build`
Expected: lint + rollup clean.

- [ ] **Step 3: Live verification (manual — the observable criterion)**

Load the panel in Home Assistant. Confirm:
- A **Verlauf** tab appears between Zonen and Einrichtung.
- It shows a zone dropdown defaulting to the first zone, and that zone's usage total + runs table (or the empty note).
- Changing the dropdown swaps to another zone's history.
- The **Zonen** tab's zone settings no longer contain a history section.
- Deep-linking / refreshing on the History tab stays on it (does not bounce to Zones).

- [ ] **Step 4: Commit the rebuilt dist**

```bash
git add -f custom_components/smart_irrigation/frontend/dist/*.js
git commit -m "build(history): rebuild dist bundles"
```

(Run from the repo root, or adjust the path if committing from `frontend/`.)

---

## Notes for delivery (outside this plan)

- Upstream-able: after live verification, this can go to JustChr as a PR and/or into a production rebuild (separate decision). Follow `pr-workflow` and the Regel-P1 archive step (`preserve-design-docs-archive-branch`) for this spec + plan.
- i18n: the eight translations in Task 2 are first drafts; a native speaker (or JustChr) may refine the non-en/de strings — the keys and English/German are authoritative.
