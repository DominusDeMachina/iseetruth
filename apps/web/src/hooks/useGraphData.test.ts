import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

const mockGet = vi.fn();
vi.mock("@/lib/api-client", () => ({
  api: { GET: (...args: unknown[]) => mockGet(...args) },
}));

import { useGraphData, useExpandNeighbors, type GraphFilters } from "./useGraphData";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return {
    queryClient,
    wrapper: ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children),
  };
}

const mockGraphResponse = {
  nodes: [
    {
      group: "nodes" as const,
      data: {
        id: "n1",
        name: "John",
        type: "Person",
        confidence_score: 0.9,
        relationship_count: 5,
      },
    },
    {
      group: "nodes" as const,
      data: {
        id: "n2",
        name: "Acme",
        type: "Organization",
        confidence_score: 0.8,
        relationship_count: 3,
      },
    },
  ],
  edges: [
    {
      group: "edges" as const,
      data: {
        id: "n1-WORKS_FOR-n2",
        source: "n1",
        target: "n2",
        type: "WORKS_FOR",
        confidence_score: 0.85,
      },
    },
  ],
  total_nodes: 2,
  total_edges: 1,
};

describe("useGraphData", () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it("fetches graph data for an investigation", async () => {
    mockGet.mockResolvedValue({ data: mockGraphResponse, error: undefined });

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useGraphData("inv-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockGraphResponse);
    expect(mockGet).toHaveBeenCalledWith(
      "/api/v1/investigations/{investigation_id}/graph/",
      {
        params: {
          path: { investigation_id: "inv-1" },
          query: { limit: 50 },
        },
      },
    );
  });

  it("handles empty graph response", async () => {
    const emptyResponse = {
      nodes: [],
      edges: [],
      total_nodes: 0,
      total_edges: 0,
    };
    mockGet.mockResolvedValue({ data: emptyResponse, error: undefined });

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useGraphData("inv-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.nodes).toEqual([]);
    expect(result.current.data?.edges).toEqual([]);
  });

  it("handles API error", async () => {
    mockGet.mockResolvedValue({
      data: undefined,
      error: { detail: "Not found" },
    });

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useGraphData("inv-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });

  it("does not fetch when investigationId is empty", () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useGraphData(""), { wrapper });

    expect(result.current.isFetching).toBe(false);
    expect(mockGet).not.toHaveBeenCalled();
  });
});

describe("useGraphData with filters", () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it("includes entity_types filter in API call when provided", async () => {
    mockGet.mockResolvedValue({ data: mockGraphResponse, error: undefined });

    const { wrapper } = createWrapper();
    const filters: GraphFilters = { entityTypes: ["person", "organization"] };
    const { result } = renderHook(() => useGraphData("inv-1", filters), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGet).toHaveBeenCalledWith(
      "/api/v1/investigations/{investigation_id}/graph/",
      {
        params: {
          path: { investigation_id: "inv-1" },
          query: { limit: 50, entity_types: "person,organization" },
        },
      },
    );
  });

  it("includes document_id filter in API call when provided", async () => {
    mockGet.mockResolvedValue({ data: mockGraphResponse, error: undefined });

    const { wrapper } = createWrapper();
    const filters: GraphFilters = { documentId: "doc-123" };
    const { result } = renderHook(() => useGraphData("inv-1", filters), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGet).toHaveBeenCalledWith(
      "/api/v1/investigations/{investigation_id}/graph/",
      {
        params: {
          path: { investigation_id: "inv-1" },
          query: { limit: 50, document_id: "doc-123" },
        },
      },
    );
  });

  it("omits filter params when filters are undefined", async () => {
    mockGet.mockResolvedValue({ data: mockGraphResponse, error: undefined });

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useGraphData("inv-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGet).toHaveBeenCalledWith(
      "/api/v1/investigations/{investigation_id}/graph/",
      {
        params: {
          path: { investigation_id: "inv-1" },
          query: { limit: 50 },
        },
      },
    );
  });

  it("includes filters in query key for cache separation", async () => {
    mockGet.mockResolvedValue({ data: mockGraphResponse, error: undefined });

    const { queryClient, wrapper } = createWrapper();
    const filters: GraphFilters = { entityTypes: ["person"] };
    const { result } = renderHook(() => useGraphData("inv-1", filters), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Cache entry should use filter-aware key
    const cached = queryClient.getQueryData([
      "graph",
      "inv-1",
      ["person"],
      undefined,
    ]);
    expect(cached).toEqual(mockGraphResponse);
  });
});

describe("useExpandNeighbors", () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it("merges new neighbors into cached graph data without duplicates", async () => {
    // Seed the cache with initial graph data (cache key includes filter slots)
    const { queryClient, wrapper } = createWrapper();
    queryClient.setQueryData(["graph", "inv-1", undefined, undefined], mockGraphResponse);

    const neighborResponse = {
      nodes: [
        // n2 already exists — should be deduplicated
        {
          group: "nodes" as const,
          data: {
            id: "n2",
            name: "Acme",
            type: "Organization",
            confidence_score: 0.8,
            relationship_count: 3,
          },
        },
        // n3 is new
        {
          group: "nodes" as const,
          data: {
            id: "n3",
            name: "Berlin",
            type: "Location",
            confidence_score: 0.7,
            relationship_count: 1,
          },
        },
      ],
      edges: [
        // Existing edge — should be deduplicated
        {
          group: "edges" as const,
          data: {
            id: "n1-WORKS_FOR-n2",
            source: "n1",
            target: "n2",
            type: "WORKS_FOR",
            confidence_score: 0.85,
          },
        },
        // New edge
        {
          group: "edges" as const,
          data: {
            id: "n2-LOCATED_IN-n3",
            source: "n2",
            target: "n3",
            type: "LOCATED_IN",
            confidence_score: 0.75,
          },
        },
      ],
      total_nodes: 3,
      total_edges: 2,
    };
    mockGet.mockResolvedValue({ data: neighborResponse, error: undefined });

    const { result } = renderHook(() => useExpandNeighbors("inv-1"), {
      wrapper,
    });

    await act(async () => {
      await result.current.expandNeighbors("n1");
    });

    const updated = queryClient.getQueryData<typeof mockGraphResponse>([
      "graph",
      "inv-1",
      undefined,
      undefined,
    ]);
    // Should have 3 nodes (2 original + 1 new), not 4
    expect(updated?.nodes).toHaveLength(3);
    // Should have 2 edges (1 original + 1 new), not 3
    expect(updated?.edges).toHaveLength(2);
    // New node should be present
    expect(updated?.nodes.find((n) => n.data.id === "n3")).toBeTruthy();
    // New edge should be present
    expect(
      updated?.edges.find((e) => e.data.id === "n2-LOCATED_IN-n3"),
    ).toBeTruthy();
  });
});
