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

type ViewModule = typeof import("./view-mappings");
let View: ViewModule["SmartIrrigationViewMappings"];
beforeAll(async () => {
  ({ SmartIrrigationViewMappings: View } = await import("./view-mappings"));
});

// A group without sensors: saveToHA checks each configured sensor entity
// against hass.states, and there is none to check.
function group(id: number, name: string) {
  return { id, name, mappings: {} };
}

function make(groups: unknown[]) {
  const callApi = vi.fn().mockResolvedValue(true);
  const el: any = new View();
  el.hass = { language: "en", states: {}, callApi };
  el.mappings = groups;
  return { el, callApi };
}

function saved(callApi: ReturnType<typeof vi.fn>) {
  return callApi.mock.calls.map(([method, path, body]) => {
    expect([method, path]).toEqual(["POST", "irrigation_plus/mappings"]);
    return body;
  });
}

describe("a sensor group edit is saved", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("saves every group edited inside one debounce window", () => {
    const { el, callApi } = make([group(1, "Garden"), group(2, "Bed")]);
    el.handleEditMapping(0, group(1, "Garden south"));
    el.handleEditMapping(1, group(2, "Bed north"));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      group(1, "Garden south"),
      group(2, "Bed north"),
    ]);
  });

  it("does not save a group twice once it has been saved", () => {
    const { el, callApi } = make([group(1, "Garden"), group(2, "Bed")]);
    el.handleEditMapping(0, group(1, "Garden south"));
    vi.advanceTimersByTime(500);
    el.handleEditMapping(1, group(2, "Bed north"));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      group(1, "Garden south"),
      group(2, "Bed north"),
    ]);
  });

  it("drops the pending save of a group deleted before it is sent", () => {
    const { el, callApi } = make([group(1, "Garden"), group(2, "Bed")]);
    el.handleEditMapping(0, group(1, "Garden south"));
    el.handleRemoveMapping({}, 0);
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([{ id: "1", remove: true }]);
  });

  it("saves only the latest copy of a group edited twice", () => {
    const { el, callApi } = make([group(1, "Garden"), group(2, "Bed")]);
    el.handleEditMapping(0, group(1, "Garden s"));
    el.handleEditMapping(0, group(1, "Garden south"));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([group(1, "Garden south")]);
  });

  it("saves the other groups when one save fails, and reports it", async () => {
    const { el, callApi } = make([group(1, "Garden"), group(2, "Bed")]);
    // showErrorToast reports through the element's own event.
    el.dispatchEvent = vi.fn();
    callApi.mockImplementation((_method: string, _path: string, body: any) =>
      body.id === 1 ? Promise.reject(new Error("boom")) : Promise.resolve(true),
    );
    el.handleEditMapping(0, group(1, "Garden south"));
    el.handleEditMapping(1, group(2, "Bed north"));
    await vi.advanceTimersByTimeAsync(500);
    expect(callApi).toHaveBeenCalledTimes(2);
    expect(el.dispatchEvent).toHaveBeenCalledTimes(1);
    expect(el.isSaving).toBe(false);
  });

  it("leaves the saving state alone when the only pending save was deleted", async () => {
    const { el, callApi } = make([group(1, "Garden"), group(2, "Bed")]);
    // The delete stays in flight; its own finally clears the saving state.
    callApi.mockImplementation(() => new Promise(() => {}));
    el.handleEditMapping(0, group(1, "Garden south"));
    el.handleRemoveMapping({}, 0);
    await vi.advanceTimersByTimeAsync(500);
    expect(el.isSaving).toBe(true);
  });
});
