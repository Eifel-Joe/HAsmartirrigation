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

type ViewModule = typeof import("./view-modules");
let View: ViewModule["SmartIrrigationViewModules"];
beforeAll(async () => {
  ({ SmartIrrigationViewModules: View } = await import("./view-modules"));
});

function mod(id: number, name: string) {
  return { id, name, config: {} };
}

function make(modules: unknown[]) {
  const callApi = vi.fn().mockResolvedValue(true);
  const el: any = new View();
  el.hass = { language: "en", states: {}, callApi };
  el.modules = modules;
  return { el, callApi };
}

// Which module each save was for, and the name it was saved with.
function saved(callApi: ReturnType<typeof vi.fn>) {
  return callApi.mock.calls.map(([method, path, body]) => {
    expect([method, path]).toEqual(["POST", "irrigation_plus/modules"]);
    return [body.id, body.name];
  });
}

describe("a module edit is saved", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("saves every module edited inside one debounce window", () => {
    const { el, callApi } = make([mod(1, "PyETO"), mod(2, "Static")]);
    el.handleEditConfig(0, mod(1, "PyETO east"));
    el.handleEditConfig(1, mod(2, "Static west"));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      [1, "PyETO east"],
      [2, "Static west"],
    ]);
  });

  it("does not save a module twice once it has been saved", () => {
    const { el, callApi } = make([mod(1, "PyETO"), mod(2, "Static")]);
    el.handleEditConfig(0, mod(1, "PyETO east"));
    vi.advanceTimersByTime(500);
    el.handleEditConfig(1, mod(2, "Static west"));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      [1, "PyETO east"],
      [2, "Static west"],
    ]);
  });

  it("drops the pending save of a module deleted before it is sent", () => {
    const { el, callApi } = make([mod(1, "PyETO"), mod(2, "Static")]);
    el.handleEditConfig(0, mod(1, "PyETO east"));
    el.handleRemoveModule({}, 0);
    vi.advanceTimersByTime(500);
    expect(callApi.mock.calls.map(([, path, body]) => [path, body])).toEqual([
      ["irrigation_plus/modules", { id: "1", remove: true }],
    ]);
  });
});
