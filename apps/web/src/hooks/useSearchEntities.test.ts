import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

// Mock the API client
const mockGet = vi.fn();
vi.mock("@/lib/api-client", () => ({
  api: { GET: (...args: unknown[]) => mockGet(...args) },
}));

import { useSearchEntities } from "./useSearchEntities";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useSearchEntities", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls API with search param when query >= 2 chars", async () => {
    mockGet.mockResolvedValue({
      data: {
        items: [
          { id: "e1", name: "John Smith", type: "person", confidence_score: 0.9, source_count: 3, evidence_strength: "corroborated" },
        ],
        total: 1,
        summary: { people: 1, organizations: 0, locations: 0, total: 1 },
      },
    });

    const { result } = renderHook(
      () => useSearchEntities("inv-1", "john"),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.data.length).toBe(1);
    });

    expect(mockGet).toHaveBeenCalledWith(
      "/api/v1/investigations/{investigation_id}/entities/",
      {
        params: {
          path: { investigation_id: "inv-1" },
          query: { search: "john", limit: 20 },
        },
      },
    );
  });

  it("does not call API when query < 2 chars", () => {
    renderHook(
      () => useSearchEntities("inv-1", "j"),
      { wrapper: createWrapper() },
    );

    expect(mockGet).not.toHaveBeenCalled();
  });

  it("returns empty array on no results", async () => {
    mockGet.mockResolvedValue({
      data: {
        items: [],
        total: 0,
        summary: { people: 0, organizations: 0, locations: 0, total: 0 },
      },
    });

    const { result } = renderHook(
      () => useSearchEntities("inv-1", "zzz"),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual([]);
  });

  it("does not call API when query is only whitespace", () => {
    renderHook(
      () => useSearchEntities("inv-1", "   "),
      { wrapper: createWrapper() },
    );

    expect(mockGet).not.toHaveBeenCalled();
  });
});
