import { TemplateResult, LitElement, html, CSSResultGroup, css } from "lit";
import { property, state, customElement } from "lit/decorators.js";
import { HomeAssistant } from "custom-card-helpers";
import { loadHaForm } from "../../load-ha-elements";
import { UnsubscribeFunc } from "home-assistant-js-websocket";
import { mdiCog, mdiClose } from "@mdi/js";
import {
  fetchConfig,
  fetchZones,
  calculateZone,
  updateZone,
  calculateAllZones,
  updateAllZones,
  irrigateNow,
} from "../../data/websockets";
import { SubscribeMixin } from "../../subscribe-mixin";

import {
  SmartIrrigationConfig,
  SmartIrrigationZone,
  SmartIrrigationZoneState,
} from "../../types";
import {
  output_unit,
  extractErrorMessage,
  showToast,
  showErrorToast,
  navigate,
  formatDuration,
} from "../../helpers";
import { exportPath } from "../../common/navigation";
import { globalStyle } from "../../styles/global-style";
import { localize } from "../../../localize/localize";
import { DOMAIN, ZONE_BUCKET } from "../../const";
import moment from "moment";

/**
 * Everyday dashboard for zones: at-a-glance decision + status, and the
 * operational actions (update / calculate / irrigate). Zone configuration,
 * reporting and management live in Setup → Zones; a gear icon on each card
 * deep-links there. (UX restructure N2/N3.)
 */
@customElement("smart-irrigation-view-zones")
class SmartIrrigationViewZones extends SubscribeMixin(LitElement) {
  hass?: HomeAssistant;
  @property() config?: SmartIrrigationConfig;

  @property({ type: Array })
  private zones: SmartIrrigationZone[] = [];

  @property({ type: Boolean })
  private isLoading = true;

  private _initialLoadDone = false;

  @property({ type: Boolean })
  private isSaving = false;

  @state() private _operationError: string | null = null;

  // Pending irrigate confirmation: "all", a zone id (string), or null.
  @state() private _confirmIrrigate: string | null = null;

  private _updateScheduled = false;
  private _scheduleUpdate() {
    if (this._updateScheduled) return;
    this._updateScheduled = true;
    requestAnimationFrame(() => {
      this._updateScheduled = false;
      this.requestUpdate();
    });
  }

  firstUpdated() {
    loadHaForm()
      .then(() => this._scheduleUpdate())
      .catch((error) => {
        console.error("Failed to load HA form:", error);
        this._scheduleUpdate();
      });
  }

  public hassSubscribe(): Promise<UnsubscribeFunc>[] {
    this._fetchData().catch((error) => {
      console.error("Failed to fetch initial data:", error);
    });

    return [
      this.hass!.connection.subscribeMessage(
        () => {
          this._fetchData().catch((error) => {
            console.error("Failed to fetch data on config update:", error);
          });
        },
        { type: DOMAIN + "_config_updated" },
      ),
    ];
  }

  private async _fetchData(): Promise<void> {
    if (!this.hass) return;

    const isInitial = !this._initialLoadDone;

    try {
      if (isInitial) this.isLoading = true;

      const [config, zones] = await Promise.all([
        fetchConfig(this.hass),
        fetchZones(this.hass),
      ]);

      this.config = config;
      this.zones = zones;
      this._initialLoadDone = true;
    } catch (error) {
      console.error("Error fetching data:", error);
      showErrorToast(this, this.hass, "common.errors.load_failed", error);
    } finally {
      if (isInitial) this.isLoading = false;
      this._scheduleUpdate();
    }
  }

  private handleCalculateAllZones(): void {
    if (!this.hass) return;
    this.isSaving = true;
    this._scheduleUpdate();
    calculateAllZones(this.hass)
      .catch((error) => {
        console.error("Failed to calculate all zones:", error);
        showErrorToast(this, this.hass, "common.errors.action_failed", error);
      })
      .finally(() => {
        this.isSaving = false;
        this._fetchData().catch((e) =>
          console.error("fetchData after calc-all:", e),
        );
      });
  }

  private handleUpdateAllZones(): void {
    if (!this.hass) return;
    this.isSaving = true;
    this._scheduleUpdate();
    updateAllZones(this.hass)
      .catch((error) => {
        console.error("Failed to update all zones:", error);
        showErrorToast(this, this.hass, "common.errors.action_failed", error);
      })
      .finally(() => {
        this.isSaving = false;
        this._fetchData().catch((e) =>
          console.error("fetchData after update-all:", e),
        );
      });
  }

  // Number of zones an "irrigate all" would actually start (linked + duration).
  private get _linkedZoneCount(): number {
    return this.zones.filter((z) => z.linked_entity && (z.duration ?? 0) > 0)
      .length;
  }

  private async _doIrrigate(): Promise<void> {
    const target = this._confirmIrrigate;
    this._confirmIrrigate = null;
    if (target === null || !this.hass) return;

    const isAll = target === "all";
    const zone = isAll
      ? undefined
      : this.zones.find((z) => z.id?.toString() === target);
    const label = isAll
      ? `(${this._linkedZoneCount})`
      : `: ${zone?.name ?? target}`;

    try {
      await irrigateNow(this.hass, isAll ? undefined : target);
      showToast(
        this,
        `${localize("panels.zones.confirm_irrigate.toast_started", this.hass.language)} ${label}`,
      );
    } catch (err) {
      const msg = extractErrorMessage(err);
      console.error("irrigate_now failed", err);
      showToast(
        this,
        `${localize("panels.zones.confirm_irrigate.toast_failed", this.hass.language)}: ${msg}`,
      );
    }
  }

  private handleCalculateZone(index: number): void {
    const zone = this.zones[index];
    if (!zone || zone.id == undefined || !this.hass) return;
    this._operationError = null;
    this.isSaving = true;
    this._scheduleUpdate();
    calculateZone(this.hass, zone.id.toString())
      .catch((err) => {
        const msg = extractErrorMessage(err);
        console.error("calculateZone failed:", err);
        this._operationError = msg;
      })
      .finally(() => {
        this.isSaving = false;
        this._fetchData().catch((e) =>
          console.error("fetchData after calc:", e),
        );
      });
  }

  private handleUpdateZone(index: number): void {
    const zone = this.zones[index];
    if (!zone || zone.id == undefined || !this.hass) return;
    this._operationError = null;
    this.isSaving = true;
    this._scheduleUpdate();
    updateZone(this.hass, zone.id.toString())
      .catch((err) => {
        const msg = extractErrorMessage(err);
        console.error("updateZone failed:", err);
        this._operationError = msg;
      })
      .finally(() => {
        this.isSaving = false;
        this._fetchData().catch((e) =>
          console.error("fetchData after update:", e),
        );
      });
  }

  /** Open this zone's settings in the Setup → Zones tab. */
  private _openZoneSettings(zone: SmartIrrigationZone): void {
    const params =
      zone.id !== undefined ? { params: { zone: String(zone.id) } } : undefined;
    navigate(
      this,
      params
        ? exportPath("setup", "zones", params)
        : exportPath("setup", "zones"),
    );
  }

  /**
   * At-a-glance answer to "will this zone water, and why" — the daily question.
   * Derived from existing zone fields (state / duration / last_calculated).
   */
  private _renderZoneDecision(zone: SmartIrrigationZone): TemplateResult {
    if (!this.hass) return html``;
    const lang = this.hass.language;
    const duration = zone.duration ?? 0;

    let text: string;
    let cls: string;
    let icon: string;
    if (zone.state === SmartIrrigationZoneState.Disabled) {
      text = localize("panels.zones.status.decision_disabled", lang);
      cls = "neutral";
      icon = "mdi:power-off";
    } else if (duration > 0) {
      text = localize(
        "panels.zones.status.decision_water",
        lang,
        "{duration}",
        formatDuration(duration),
      );
      cls = "water";
      icon = "mdi:water";
    } else if (zone.last_calculated) {
      text = localize("panels.zones.status.decision_no_water", lang);
      cls = "ok";
      icon = "mdi:check-circle-outline";
    } else {
      text = localize("panels.zones.status.decision_unknown", lang);
      cls = "unknown";
      icon = "mdi:help-circle-outline";
    }

    return html`
      <div class="zone-decision ${cls}">
        <ha-icon icon="${icon}"></ha-icon>
        <span>${text}</span>
      </div>
    `;
  }

  private renderZone(zone: SmartIrrigationZone, index: number): TemplateResult {
    if (!this.hass) return html``;

    const bucket = Number(zone.bucket ?? 0);
    const bucketColor =
      bucket < 0 ? "var(--warning-color)" : "var(--success-color)";
    const stateClass =
      zone.state === SmartIrrigationZoneState.Automatic
        ? "state-automatic"
        : zone.state === SmartIrrigationZoneState.Manual
          ? "state-manual"
          : "state-disabled";
    const lastChecked = zone.last_calculated
      ? moment(zone.last_calculated).format("YYYY-MM-DD HH:mm")
      : localize("panels.zones.status.never", this.hass.language);

    return html`
      <ha-card>
        <div class="card-header">
          <div class="name">${zone.name}</div>
          <span class="zone-state-badge ${stateClass}">
            ${localize(
              `panels.zones.labels.states.${zone.state}`,
              this.hass.language,
            )}
          </span>
          <ha-icon-button
            .path="${mdiCog}"
            title="${localize(
              "panels.zones.actions.open_settings",
              this.hass.language,
            )}"
            @click="${() => this._openZoneSettings(zone)}"
          ></ha-icon-button>
        </div>

        <!-- AT-A-GLANCE DECISION -->
        ${this._renderZoneDecision(zone)}

        <!-- COMPACT STATUS -->
        <div class="card-content">
          <div class="zone-status-line">
            <span
              title="${localize(
                "panels.zones.help.bucket",
                this.hass.language,
              )}"
            >
              ${localize("panels.zones.labels.bucket", this.hass.language)}:
              <strong style="color: ${bucketColor}"
                >${bucket.toFixed(2)}
                ${output_unit(this.config, ZONE_BUCKET)}</strong
              >
            </span>
            <span class="status-sep">·</span>
            <span>
              ${localize(
                "panels.zones.status.last_checked",
                this.hass.language,
              )}:
              <strong>${lastChecked}</strong>
            </span>
          </div>
        </div>

        <!-- ACTION BUTTONS -->
        <div class="card-content zone-action-bar">
          ${zone.state === SmartIrrigationZoneState.Automatic
            ? html`
                <button
                  class="action-btn"
                  title="${localize(
                    "panels.zones.help.update",
                    this.hass.language,
                  )}"
                  @click="${() => this.handleUpdateZone(index)}"
                  ?disabled="${this.isSaving}"
                >
                  <ha-icon slot="icon" icon="mdi:update"></ha-icon>
                  ${localize("panels.zones.actions.update", this.hass.language)}
                </button>
                <button
                  class="action-btn"
                  title="${localize(
                    "panels.zones.help.calculate",
                    this.hass.language,
                  )}"
                  @click="${() => this.handleCalculateZone(index)}"
                  ?disabled="${this.isSaving}"
                >
                  <ha-icon slot="icon" icon="mdi:calculator"></ha-icon>
                  ${localize(
                    "panels.zones.actions.calculate",
                    this.hass.language,
                  )}
                </button>
              `
            : ""}
          ${zone.linked_entity && (zone.duration ?? 0) > 0
            ? html`
                <button
                  class="action-btn"
                  raised
                  @click="${() => {
                    if (zone.id !== undefined) {
                      this._confirmIrrigate = zone.id.toString();
                    }
                  }}"
                  ?disabled="${this.isSaving}"
                >
                  ${localize(
                    "panels.zones.labels.irrigate_now",
                    this.hass.language,
                  )}
                </button>
              `
            : !zone.linked_entity
              ? html`
                  <button
                    class="action-btn"
                    disabled
                    title="${localize(
                      "panels.zones.help.irrigate_link_entity",
                      this.hass.language,
                    )}"
                  >
                    ${localize(
                      "panels.zones.labels.irrigate_now",
                      this.hass.language,
                    )}
                  </button>
                  <span class="zones-top-note">
                    ${localize(
                      "panels.zones.help.irrigate_link_entity",
                      this.hass.language,
                    )}
                  </span>
                `
              : ""}
        </div>
      </ha-card>
    `;
  }

  render(): TemplateResult {
    if (!this.hass) return html``;

    if (this.isLoading) {
      return html`
        <ha-card header="${localize("panels.zones.title", this.hass.language)}">
          <div class="card-content">
            <div class="loading-indicator">
              ${localize("common.loading-messages.general", this.hass.language)}
            </div>
          </div>
        </ha-card>
      `;
    }

    const hasLinkedZones = this.zones.some(
      (z) => z.linked_entity && (z.duration ?? 0) > 0,
    );

    // First-time setup banner: shown when no zones exist yet.
    const isFirstTime = this.zones.length === 0;

    return html`
      ${isFirstTime
        ? html`
            <ha-card class="setup-banner-card">
              <div class="setup-banner">
                <div class="setup-banner-icon">🌱</div>
                <div class="setup-banner-content">
                  <div class="setup-banner-title">
                    ${localize("wizard.title", this.hass.language)}
                  </div>
                  <div class="setup-banner-desc">
                    ${localize(
                      "wizard.setup_complete_banner",
                      this.hass.language,
                    )}
                  </div>
                </div>
                <button
                  class="action-btn setup-banner-btn"
                  @click="${() => {
                    this.dispatchEvent(
                      new CustomEvent("open-wizard", {
                        bubbles: true,
                        composed: true,
                      }),
                    );
                  }}"
                >
                  ${localize("wizard.open_wizard", this.hass.language)}
                </button>
              </div>
            </ha-card>
          `
        : ""}

      <!-- Zones header card: run-all operational actions -->
      <ha-card>
        <div class="card-header">
          <div class="name">
            ${localize("panels.zones.title", this.hass.language)}
          </div>
        </div>
        <div class="card-content zones-top-actions">
          <button
            class="action-btn"
            raised
            @click="${() => {
              this._confirmIrrigate = "all";
            }}"
            ?disabled="${!hasLinkedZones || this.isSaving}"
          >
            ${localize("panels.zones.actions.irrigate_all", this.hass.language)}
          </button>
          <button
            class="action-btn"
            @click="${this.handleUpdateAllZones}"
            ?disabled="${this.isSaving}"
          >
            ${localize(
              "panels.zones.cards.zone-actions.actions.update-all",
              this.hass.language,
            )}
          </button>
          <button
            class="action-btn"
            @click="${this.handleCalculateAllZones}"
            ?disabled="${this.isSaving}"
          >
            ${localize(
              "panels.zones.cards.zone-actions.actions.calculate-all",
              this.hass.language,
            )}
          </button>
          ${!hasLinkedZones
            ? html`<span class="zones-top-note"
                >${localize(
                  "panels.info.cards.irrigate_now.no_linked_zones",
                  this.hass.language,
                )}</span
              >`
            : ""}
        </div>
      </ha-card>

      <!-- Irrigate confirmation dialog -->
      ${this._confirmIrrigate !== null
        ? html`
            <ha-dialog
              open
              @closed="${() => {
                this._confirmIrrigate = null;
              }}"
              heading="${localize(
                "panels.zones.confirm_irrigate.title",
                this.hass.language,
              )}"
            >
              <p>
                ${localize(
                  "panels.zones.confirm_irrigate.body",
                  this.hass.language,
                )}
              </p>
              <p>
                <strong>
                  ${this._confirmIrrigate === "all"
                    ? `${localize("panels.zones.confirm_irrigate.all_linked_zones", this.hass.language)} (${this._linkedZoneCount})`
                    : (this.zones.find(
                        (z) => z.id?.toString() === this._confirmIrrigate,
                      )?.name ?? this._confirmIrrigate)}
                </strong>
              </p>
              <div class="dialog-footer">
                <button
                  class="dialog-btn"
                  @click="${() => {
                    this._confirmIrrigate = null;
                  }}"
                >
                  ${localize("common.actions.cancel", this.hass.language)}
                </button>
                <button
                  class="dialog-btn dialog-btn-primary"
                  @click="${this._doIrrigate}"
                >
                  ${localize(
                    "panels.zones.labels.irrigate_now",
                    this.hass.language,
                  )}
                </button>
              </div>
            </ha-dialog>
          `
        : ""}

      <!-- Operation error banner -->
      ${this._operationError
        ? html`
            <ha-card class="error-banner-card">
              <div class="error-banner">
                <ha-icon
                  class="error-banner-icon"
                  icon="mdi:alert-circle-outline"
                ></ha-icon>
                <span class="error-banner-msg">${this._operationError}</span>
                <ha-icon-button
                  .path="${mdiClose}"
                  @click="${() => {
                    this._operationError = null;
                  }}"
                  aria-label="${localize(
                    "common.actions.cancel",
                    this.hass.language,
                  )}"
                ></ha-icon-button>
              </div>
            </ha-card>
          `
        : ""}

      <!-- Zone cards -->
      ${this.zones.map((zone, index) => this.renderZone(zone, index))}
    `;
  }

  static get styles(): CSSResultGroup {
    return css`
      ${globalStyle}

      /* At-a-glance decision line */
      .zone-decision {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0 16px 12px;
        padding: 10px 12px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 500;
        line-height: 1.35;
      }

      .zone-decision ha-icon {
        flex-shrink: 0;
        --mdc-icon-size: 22px;
      }

      .zone-decision.water {
        background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12);
        color: var(--primary-color);
      }

      .zone-decision.ok {
        background: rgba(76, 175, 80, 0.12);
        color: var(--success-color, #2e7d32);
      }

      .zone-decision.neutral {
        background: var(--secondary-background-color);
        color: var(--secondary-text-color);
      }

      .zone-decision.unknown {
        background: rgba(255, 152, 0, 0.12);
        color: var(--warning-color, #ed6c02);
      }

      /* Compact one-line status */
      .zone-status-line {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 6px;
        font-size: 0.875rem;
        color: var(--secondary-text-color);
      }

      .zone-status-line strong {
        color: var(--primary-text-color);
        font-weight: 500;
      }

      .status-sep {
        opacity: 0.5;
      }

      /* Action bar */
      .zone-action-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding-top: 0;
        padding-bottom: 12px;
      }

      /* State badge */
      .zone-state-badge {
        font-size: 0.75rem;
        font-weight: 500;
        padding: 2px 8px;
        border-radius: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        align-self: center;
        margin-left: auto;
      }

      .state-automatic {
        background: var(--success-color, #4caf50);
        color: white;
      }

      .state-manual {
        background: var(--accent-color, var(--primary-color));
        color: white;
      }

      .state-disabled {
        background: var(--disabled-color, #bdbdbd);
        color: white;
      }

      /* First-time setup banner */
      .setup-banner-card {
        border-left: 4px solid var(--primary-color);
      }

      .setup-banner {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 16px;
        flex-wrap: wrap;
      }

      .setup-banner-icon {
        font-size: 2rem;
        flex-shrink: 0;
      }

      .setup-banner-content {
        flex: 1;
        min-width: 180px;
      }

      .setup-banner-title {
        font-weight: 600;
        font-size: 0.95rem;
        color: var(--primary-text-color);
        margin-bottom: 4px;
      }

      .setup-banner-desc {
        font-size: 0.83rem;
        color: var(--secondary-text-color);
      }

      .setup-banner-btn {
        flex-shrink: 0;
      }

      .zones-top-actions {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
      }

      .zones-top-note {
        font-size: 0.8125rem;
        color: var(--secondary-text-color);
        font-style: italic;
      }

      /* Dialog footer buttons */
      .dialog-footer {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        padding: 16px 0 8px;
        margin-top: 8px;
        border-top: 1px solid var(--divider-color);
      }

      .dialog-btn {
        background: transparent;
        border: 1px solid var(--primary-color);
        border-radius: 4px;
        color: var(--primary-color);
        cursor: pointer;
        font-family: inherit;
        font-size: 0.875rem;
        font-weight: 500;
        padding: 8px 16px;
        transition: background 0.15s;
      }

      .dialog-btn:hover {
        background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.08);
      }

      .dialog-btn-primary {
        background: var(--primary-color);
        color: var(--text-primary-color, white);
      }

      .dialog-btn-primary:hover {
        opacity: 0.9;
        background: var(--primary-color);
      }

      /* Operation error banner */
      .error-banner-card {
        border-left: 4px solid var(--error-color, #f44336);
      }

      .error-banner {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 8px 8px 16px;
      }

      .error-banner-icon {
        color: var(--error-color, #f44336);
        flex-shrink: 0;
      }

      .error-banner-msg {
        flex: 1;
        color: var(--error-color, #f44336);
        font-size: 0.9rem;
        line-height: 1.4;
      }
    `;
  }
}

export { SmartIrrigationViewZones };
