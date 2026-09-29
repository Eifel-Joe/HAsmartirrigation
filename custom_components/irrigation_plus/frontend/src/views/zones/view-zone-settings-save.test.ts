import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

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
  // _scheduleUpdate() defers a re-render to the next frame; nothing renders here.
  (globalThis as any).requestAnimationFrame = () => 0;
});

type ViewModule = typeof import("./view-zone-settings");
let View: ViewModule["SmartIrrigationViewZoneSettings"];
beforeAll(async () => {
  ({ SmartIrrigationViewZoneSettings: View } =
    await import("./view-zone-settings"));
});

// A zone as the page holds it: loaded before a run, so its bucket is the pre-run
// level. The server has credited the run since, and the page never heard of it:
// it re-reads only on _update_frontend, which a credit does not send.
function staleZone(id: number, extra: Record<string, unknown> = {}) {
  return {
    id,
    name: `Zone ${id}`,
    size: 10,
    throughput: 5,
    state: "automatic",
    duration: 0,
    bucket: -6.2,
    delta: 0,
    explanation: "",
    multiplier: 1,
    lead_time: 0,
    module: 1,
    mapping: 1,
    water_used_total: 12.5,
    run_log: [],
    ...extra,
  };
}

function make(zones: unknown[]) {
  const callApi = vi.fn().mockResolvedValue(true);
  const el: any = new View();
  el.hass = { language: "en", states: {}, callApi };
  el.zones = zones;
  return { el, callApi };
}

// What went over the wire: each POST body as JSON carries it, so an
// `undefined` value is gone here exactly as it is on the way to the server.
function bodies(callApi: ReturnType<typeof vi.fn>) {
  return callApi.mock.calls.map(([method, path, body]) => {
    expect([method, path]).toEqual(["POST", "irrigation_plus/zones"]);
    return JSON.parse(JSON.stringify(body));
  });
}

// That no call site hands handleEditZone the page's copy of the zone is pinned
// in tests/test_zone_view_save.py: CI runs pytest, not these tests.

describe("a zone edit posts what it set", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("sends the zone id and the edited field, nothing from the page's copy", () => {
    const { el, callApi } = make([staleZone(1)]);
    el.handleEditZone(0, { name: "Beet" });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([{ id: 1, name: "Beet" }]);
  });

  it("shows the edit at once and keeps the rest of the page's copy", () => {
    const { el } = make([staleZone(1)]);
    el.handleEditZone(0, { name: "Beet" });
    expect(el.zones[0]).toEqual({ ...staleZone(1), name: "Beet" });
  });

  it("saves every zone edited inside one debounce window", () => {
    const { el, callApi } = make([staleZone(1), staleZone(2)]);
    el.handleEditZone(0, { name: "Beet" });
    el.handleEditZone(1, { name: "Hecke" });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([
      { id: 1, name: "Beet" },
      { id: 2, name: "Hecke" },
    ]);
  });

  it("merges two edits to one zone into one post", () => {
    const { el, callApi } = make([staleZone(1)]);
    el.handleEditZone(0, { name: "Beet" });
    el.handleEditZone(0, { size: 12 });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([{ id: 1, name: "Beet", size: 12 }]);
  });

  it("does not post an edit twice once it has been sent", () => {
    const { el, callApi } = make([staleZone(1)]);
    el.handleEditZone(0, { name: "Beet" });
    vi.advanceTimersByTime(500);
    el.handleEditZone(0, { size: 12 });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([
      { id: 1, name: "Beet" },
      { id: 1, size: 12 },
    ]);
  });

  it("sends a cleared field as null, so the server stores the clear", () => {
    const { el, callApi } = make([staleZone(1)]);
    el.handleEditZone(0, { module: undefined });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([{ id: 1, module: null }]);
  });

  it("sends every field the edit set, even one the page's copy already shows", () => {
    // The state select resets the duration with the state. The page's copy may
    // show 0 while the server holds a calculated duration, so a difference
    // against the copy would drop the reset.
    const { el, callApi } = make([staleZone(1, { duration: 0 })]);
    el.handleEditZone(0, { state: "manual", duration: 0 });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([{ id: 1, state: "manual", duration: 0 }]);
  });

  it("posts nothing for a zone that has no id yet", () => {
    // handleAddZone is still creating it. A body without an id is a create on
    // the server, so an edit must not be posted for it.
    const { el, callApi } = make([{ ...staleZone(1), id: undefined }]);
    el.handleEditZone(0, { name: "Beet" });
    expect(el.zones[0].name).toBe("Beet");
    vi.advanceTimersByTime(500);
    expect(callApi).not.toHaveBeenCalled();
  });

  it("waits the full window, and every edit restarts it", () => {
    const { el, callApi } = make([staleZone(1)]);
    el.handleEditZone(0, { name: "Beet" });
    vi.advanceTimersByTime(499);
    expect(callApi).not.toHaveBeenCalled();
    el.handleEditZone(0, { size: 12 });
    vi.advanceTimersByTime(499);
    expect(callApi).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(bodies(callApi)).toEqual([{ id: 1, name: "Beet", size: 12 }]);
  });

  it("finds its zone by id when a confirmed edit runs later", () => {
    // The reset dialog was opened for zone 2 while it sat at index 1. Zone 1
    // was removed before the user confirmed, so index 1 now holds zone 3.
    const { el, callApi } = make([staleZone(2), staleZone(3)]);
    el._editZoneById(2, { bucket: 0 });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([{ id: 2, bucket: 0 }]);
    expect(el.zones.map((z: any) => z.bucket)).toEqual([0, -6.2]);
  });

  it("drops the pending edit of a zone deleted before it is sent", () => {
    // Sent after the delete, the edit would reach the server for an id it no
    // longer knows, and it would create a zone from the edited fields alone.
    // Another zone's edit in the same window still goes out.
    const { el, callApi } = make([staleZone(1), staleZone(2)]);
    el.handleEditZone(0, { name: "Beet" });
    el.handleEditZone(1, { name: "Hecke" });
    el._confirmDeleteZoneId = 1;
    el._confirmDelete();
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([
      { id: "1", remove: true },
      { id: 2, name: "Hecke" },
    ]);
  });

  it("drops an unsent edit when the page is left", () => {
    // Put back later, the page must not post an edit made long before: the
    // level it carries may be out of date by then.
    const { el, callApi } = make([staleZone(1)]);
    el.handleEditZone(0, { bucket: 5 });
    el.disconnectedCallback();
    el.handleEditZone(0, { name: "Beet" });
    vi.advanceTimersByTime(500);
    expect(bodies(callApi)).toEqual([{ id: 1, name: "Beet" }]);
  });
});

describe("select value for an optional id", () => {
  it("shows the empty option for a cleared id, and the id otherwise", () => {
    // The server returns a cleared module or mapping as null; String(null)
    // would select nothing instead of the empty option.
    const el: any = new View();
    expect(el._selectValue(null)).toBe("");
    expect(el._selectValue(undefined)).toBe("");
    expect(el._selectValue(3)).toBe("3");
    expect(el._selectValue(0)).toBe("0");
  });
});
