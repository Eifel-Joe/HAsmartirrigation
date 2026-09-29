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

type ViewModule = typeof import("./view-distributor-settings");
let View: ViewModule["SmartIrrigationViewDistributorSettings"];
beforeAll(async () => {
  ({ SmartIrrigationViewDistributorSettings: View } =
    await import("./view-distributor-settings"));
});

function distributor(id: number, pause_seconds: number) {
  return { id, name: `Distributor ${id}`, pause_seconds };
}

function make(distributors: unknown[]) {
  const callApi = vi.fn().mockResolvedValue(true);
  const el: any = new View();
  el.hass = { language: "en", states: {}, callApi };
  el.distributors = distributors;
  return { el, callApi };
}

// Which distributor each save was for, and the value edited on it.
function saved(callApi: ReturnType<typeof vi.fn>) {
  return callApi.mock.calls.map(([method, path, body]) => {
    expect([method, path]).toEqual(["POST", "irrigation_plus/distributors"]);
    return [body.id, body.pause_seconds];
  });
}

describe("a distributor edit is saved", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("saves every distributor edited inside one debounce window", () => {
    const { el, callApi } = make([distributor(1, 5), distributor(2, 5)]);
    el.handleEditDistributor(0, distributor(1, 7));
    el.handleEditDistributor(1, distributor(2, 9));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      [1, 7],
      [2, 9],
    ]);
  });

  it("does not save a distributor twice once it has been saved", () => {
    const { el, callApi } = make([distributor(1, 5), distributor(2, 5)]);
    el.handleEditDistributor(0, distributor(1, 7));
    vi.advanceTimersByTime(500);
    el.handleEditDistributor(1, distributor(2, 9));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([
      [1, 7],
      [2, 9],
    ]);
  });

  it("drops the pending save of a distributor deleted before it is sent", () => {
    const { el, callApi } = make([distributor(1, 5), distributor(2, 5)]);
    el.handleEditDistributor(0, distributor(1, 7));
    el.handleEditDistributor(1, distributor(2, 9));
    el._confirmDeleteId = 1;
    el._confirmDelete();
    vi.advanceTimersByTime(500);
    // The delete posts the id as a number, so this reads the raw bodies.
    expect(callApi.mock.calls.map(([, path, body]) => [path, body])).toEqual([
      ["irrigation_plus/distributors", { id: 1, remove: true }],
      [
        "irrigation_plus/distributors",
        expect.objectContaining({ id: 2, pause_seconds: 9 }),
      ],
    ]);
  });

  it("saves only the latest copy of a distributor edited twice", () => {
    const { el, callApi } = make([distributor(1, 5), distributor(2, 5)]);
    el.handleEditDistributor(0, distributor(1, 7));
    el.handleEditDistributor(0, distributor(1, 70));
    vi.advanceTimersByTime(500);
    expect(saved(callApi)).toEqual([[1, 70]]);
  });

  it("does not report a save when the only pending save was deleted", async () => {
    const { el, callApi } = make([distributor(1, 5), distributor(2, 5)]);
    el.handleEditDistributor(0, distributor(1, 7));
    el._confirmDeleteId = 1;
    el._confirmDelete();
    await vi.advanceTimersByTimeAsync(500);
    expect(el._saveStatus).toBe("idle");
  });
});
