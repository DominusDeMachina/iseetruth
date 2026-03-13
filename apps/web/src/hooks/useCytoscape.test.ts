import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

// Mock cytoscape module
const mockCy = {
  add: vi.fn(),
  remove: vi.fn(),
  layout: vi.fn(() => ({ run: vi.fn() })),
  destroy: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  ready: vi.fn((cb: () => void) => cb()),
  fit: vi.fn(),
  zoom: vi.fn(() => 1),
  json: vi.fn(),
  elements: vi.fn(() => ({
    diff: vi.fn(() => ({ left: [], right: [], both: [] })),
    map: vi.fn(() => []),
  })),
  mount: vi.fn(),
  style: vi.fn(),
  width: vi.fn(() => 800),
  height: vi.fn(() => 600),
};

const mockCytoscapeFactory = vi.fn((_opts?: unknown) => mockCy);
vi.mock("cytoscape", () => {
  const factory = (opts: unknown) => mockCytoscapeFactory(opts);
  factory.use = vi.fn();
  return { default: factory };
});

vi.mock("cytoscape-fcose", () => ({ default: vi.fn() }));

import { useCytoscape } from "./useCytoscape";

describe("useCytoscape", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates a Cytoscape instance when container ref is provided", () => {
    const container = document.createElement("div");
    const ref = { current: container };

    const { result } = renderHook(() => useCytoscape(ref));

    expect(mockCytoscapeFactory).toHaveBeenCalledWith(
      expect.objectContaining({
        container,
        userZoomingEnabled: true,
        userPanningEnabled: true,
        boxSelectionEnabled: false,
        minZoom: 0.1,
        maxZoom: 3,
      }),
    );
    expect(result.current.isReady).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("returns null cy and not ready when container ref is null", () => {
    const ref = { current: null };

    const { result } = renderHook(() => useCytoscape(ref));

    expect(result.current.cy).toBeNull();
    expect(result.current.isReady).toBe(false);
    expect(mockCytoscapeFactory).not.toHaveBeenCalled();
  });

  it("destroys the instance on unmount", () => {
    const container = document.createElement("div");
    const ref = { current: container };

    const { unmount } = renderHook(() => useCytoscape(ref));
    unmount();

    expect(mockCy.destroy).toHaveBeenCalled();
  });

  it("handles Cytoscape initialization error", () => {
    mockCytoscapeFactory.mockImplementationOnce(() => {
      throw new Error("Init failed");
    });

    const container = document.createElement("div");
    const ref = { current: container };

    const { result } = renderHook(() => useCytoscape(ref));

    expect(result.current.cy).toBeNull();
    expect(result.current.isReady).toBe(false);
    expect(result.current.error).toEqual(new Error("Init failed"));
  });

  it("respects reducedMotion option", () => {
    const container = document.createElement("div");
    const ref = { current: container };

    const { result } = renderHook(() =>
      useCytoscape(ref, { reducedMotion: true }),
    );

    expect(result.current.reducedMotion).toBe(true);
  });

  it("detects prefers-reduced-motion media query", () => {
    // jsdom doesn't have matchMedia, so define it
    window.matchMedia = vi.fn().mockReturnValue({
      matches: true,
    } as unknown as MediaQueryList);

    const container = document.createElement("div");
    const ref = { current: container };

    const { result } = renderHook(() => useCytoscape(ref));

    expect(result.current.reducedMotion).toBe(true);

    // Clean up
    // @ts-expect-error — removing mock from jsdom
    delete window.matchMedia;
  });
});
