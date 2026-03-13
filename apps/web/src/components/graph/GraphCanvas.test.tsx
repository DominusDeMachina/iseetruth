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
};

vi.mock("cytoscape", () => {
  const factory = () => mockCy;
  factory.use = vi.fn();
  return { default: factory };
});

vi.mock("cytoscape-fcose", () => ({ default: vi.fn() }));

// Mock useGraphData
const mockUseGraphData = vi.fn();
vi.mock("@/hooks/useGraphData", () => ({
  useGraphData: (...args: unknown[]) => mockUseGraphData(...args),
  useExpandNeighbors: () => ({ expandNeighbors: vi.fn() }),
}));

import { GraphCanvas } from "./GraphCanvas";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("GraphCanvas", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a container div", () => {
    mockUseGraphData.mockReturnValue({
      data: { nodes: [{ group: "nodes", data: { id: "n1", name: "John", type: "Person", confidence_score: 0.9, relationship_count: 5 } }], edges: [], total_nodes: 1, total_edges: 0 },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    const { container } = render(
      createElement(GraphCanvas, { investigationId: "inv-1" }),
      { wrapper: createWrapper() },
    );

    // The component should render a relative container with the cytoscape div inside
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
});
