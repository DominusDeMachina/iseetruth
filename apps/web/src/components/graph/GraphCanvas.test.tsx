import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

// Mock cytoscape
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
  getElementById: vi.fn(() => ({
    renderedPosition: vi.fn(() => ({ x: 100, y: 100 })),
    data: vi.fn(() => "John"),
    empty: vi.fn(() => false),
  })),
  animate: vi.fn(),
};

vi.mock("cytoscape", () => {
  const factory = () => mockCy;
  factory.use = vi.fn();
  return { default: factory };
});

vi.mock("cytoscape-fcose", () => ({ default: vi.fn() }));

// Mock useGraphData
const mockUseGraphData = vi.fn();
const mockExpandNeighbors = vi.fn().mockResolvedValue(null);
vi.mock("@/hooks/useGraphData", () => ({
  useGraphData: (...args: unknown[]) => mockUseGraphData(...args),
  useExpandNeighbors: () => ({ expandNeighbors: mockExpandNeighbors }),
}));

// Mock useEntityDetail for EntityDetailCard
vi.mock("@/hooks/useEntityDetail", () => ({
  useEntityDetail: () => ({
    data: undefined,
    isLoading: true,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

import { GraphCanvas } from "./GraphCanvas";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

const mockGraphData = {
  nodes: [
    { group: "nodes", data: { id: "n1", name: "John", type: "Person", confidence_score: 0.9, relationship_count: 5 } },
    { group: "nodes", data: { id: "n2", name: "Acme", type: "Organization", confidence_score: 0.8, relationship_count: 3 } },
  ],
  edges: [
    { group: "edges", data: { id: "n1-WORKS_FOR-n2", source: "n1", target: "n2", type: "WORKS_FOR", confidence_score: 0.85 } },
  ],
  total_nodes: 2,
  total_edges: 1,
};

describe("GraphCanvas", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a container div", () => {
    mockUseGraphData.mockReturnValue({
      data: mockGraphData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    const { container } = render(
      createElement(GraphCanvas, { investigationId: "inv-1" }),
      { wrapper: createWrapper() },
    );

    const relativeDiv = container.querySelector(".relative");
    expect(relativeDiv).toBeTruthy();
  });

  it("shows loading state", () => {
    mockUseGraphData.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(GraphCanvas, { investigationId: "inv-1" }), {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Loading graph data…")).toBeTruthy();
  });

  it("shows empty state when no entities", () => {
    mockUseGraphData.mockReturnValue({
      data: { nodes: [], edges: [], total_nodes: 0, total_edges: 0 },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(GraphCanvas, { investigationId: "inv-1" }), {
      wrapper: createWrapper(),
    });

    expect(
      screen.getByText(
        "No entities found. Upload and process documents to populate the graph.",
      ),
    ).toBeTruthy();
  });

  it("shows error state with retry button", async () => {
    const mockRefetch = vi.fn();
    mockUseGraphData.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Network error"),
      refetch: mockRefetch,
    });

    render(createElement(GraphCanvas, { investigationId: "inv-1" }), {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Failed to load graph data.")).toBeTruthy();

    const retryButton = screen.getByText("Retry");
    await userEvent.click(retryButton);
    expect(mockRefetch).toHaveBeenCalled();
  });

  it("registers node tap handler on cytoscape", () => {
    mockUseGraphData.mockReturnValue({
      data: mockGraphData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(GraphCanvas, { investigationId: "inv-1" }), {
      wrapper: createWrapper(),
    });

    // Verify cy.on was called with tap handlers
    const tapNodeCalls = mockCy.on.mock.calls.filter(
      (call: unknown[]) => call[0] === "tap" && call[1] === "node",
    );
    expect(tapNodeCalls.length).toBeGreaterThan(0);
  });

  it("registers edge tap handler on cytoscape", () => {
    mockUseGraphData.mockReturnValue({
      data: mockGraphData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(GraphCanvas, { investigationId: "inv-1" }), {
      wrapper: createWrapper(),
    });

    const tapEdgeCalls = mockCy.on.mock.calls.filter(
      (call: unknown[]) => call[0] === "tap" && call[1] === "edge",
    );
    expect(tapEdgeCalls.length).toBeGreaterThan(0);
  });

  it("registers double-tap handler for neighbor expansion", () => {
    mockUseGraphData.mockReturnValue({
      data: mockGraphData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(GraphCanvas, { investigationId: "inv-1" }), {
      wrapper: createWrapper(),
    });

    const dblTapCalls = mockCy.on.mock.calls.filter(
      (call: unknown[]) => call[0] === "dbltap" && call[1] === "node",
    );
    expect(dblTapCalls.length).toBeGreaterThan(0);
  });

  it("registers background tap handler to clear selection", () => {
    mockUseGraphData.mockReturnValue({
      data: mockGraphData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(GraphCanvas, { investigationId: "inv-1" }), {
      wrapper: createWrapper(),
    });

    // Background tap is cy.on('tap', handler) without a selector
    const bgTapCalls = mockCy.on.mock.calls.filter(
      (call: unknown[]) => call[0] === "tap" && typeof call[1] === "function",
    );
    expect(bgTapCalls.length).toBeGreaterThan(0);
  });

  it("registers node mouseover/mouseout for tooltip", () => {
    mockUseGraphData.mockReturnValue({
      data: mockGraphData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(GraphCanvas, { investigationId: "inv-1" }), {
      wrapper: createWrapper(),
    });

    const mouseoverCalls = mockCy.on.mock.calls.filter(
      (call: unknown[]) => call[0] === "mouseover" && call[1] === "node",
    );
    const mouseoutCalls = mockCy.on.mock.calls.filter(
      (call: unknown[]) => call[0] === "mouseout" && call[1] === "node",
    );
    expect(mouseoverCalls.length).toBeGreaterThan(0);
    expect(mouseoutCalls.length).toBeGreaterThan(0);
  });
});
