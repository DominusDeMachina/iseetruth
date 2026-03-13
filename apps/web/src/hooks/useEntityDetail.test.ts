import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

const mockGet = vi.fn();
vi.mock("@/lib/api-client", () => ({
  api: { GET: (...args: unknown[]) => mockGet(...args) },
}));

import { useEntityDetail } from "./useEntityDetail";

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

const mockEntityDetail = {
  id: "entity-1",
  name: "Deputy Mayor Horvat",
  type: "Person",
  confidence_score: 0.92,
  investigation_id: "inv-1",
  relationships: [
    {
      relation_type: "WORKS_FOR",
      target_id: "entity-2",
      target_name: "City Council",
      target_type: "Organization",
      confidence_score: 0.88,
    },
  ],
  sources: [
    {
      document_id: "doc-1",
      document_filename: "contract-award-089.pdf",
      chunk_id: "chunk-1",
      page_start: 3,
      page_end: 3,
      text_excerpt: "Deputy Mayor Horvat signed the contract...",
    },
  ],
  evidence_strength: "corroborated",
};

describe("useEntityDetail", () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it("fetches entity detail when both IDs are present", async () => {
    mockGet.mockResolvedValue({ data: mockEntityDetail, error: undefined });

    const { wrapper } = createWrapper();
    const { result } = renderHook(
      () => useEntityDetail("inv-1", "entity-1"),
      { wrapper },
    );

    await waitFor(() => {
      expect(result.current.data).toBeDefined();
    });

    expect(result.current.data).toEqual(mockEntityDetail);
    expect(mockGet).toHaveBeenCalledWith(
      "/api/v1/investigations/{investigation_id}/entities/{entity_id}",
      {
        params: {
          path: {
            investigation_id: "inv-1",
            entity_id: "entity-1",
          },
        },
      },
    );
  });

  it("does not fetch when entityId is null", () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useEntityDetail("inv-1", null), {
      wrapper,
    });

    expect(result.current.data).toBeUndefined();
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("handles API error", async () => {
    mockGet.mockResolvedValue({
      data: undefined,
      error: { detail: "Not found" },
    });

    const { wrapper } = createWrapper();
    const { result } = renderHook(
      () => useEntityDetail("inv-1", "entity-1"),
      { wrapper },
    );

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });
});
