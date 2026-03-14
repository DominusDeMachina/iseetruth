import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

// Mock api client
const mockGet = vi.fn();
vi.mock("@/lib/api-client", () => ({
  api: { GET: (...args: unknown[]) => mockGet(...args) },
}));

import { useChunkContext } from "./useChunkContext";

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

describe("useChunkContext", () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it("does not fetch when chunkId is null", () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useChunkContext("inv-1", null), {
      wrapper,
    });
    expect(result.current.isFetching).toBe(false);
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("fetches chunk context when chunkId is provided", async () => {
    const mockData = {
      chunk_id: "c1",
      document_id: "d1",
      document_filename: "report.pdf",
      sequence_number: 5,
      total_chunks: 20,
      text: "Sample passage text",
      page_start: 3,
      page_end: 3,
      context_before: "Previous text.",
      context_after: "Next text.",
    };
    mockGet.mockResolvedValue({ data: mockData, error: undefined });

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useChunkContext("inv-1", "c1"), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockData);
    expect(mockGet).toHaveBeenCalledWith(
      "/api/v1/investigations/{investigation_id}/chunks/{chunk_id}",
      {
        params: {
          path: {
            investigation_id: "inv-1",
            chunk_id: "c1",
          },
        },
      },
    );
  });

  it("handles API error", async () => {
    mockGet.mockResolvedValue({
      data: undefined,
      error: { detail: "Not found" },
    });

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useChunkContext("inv-1", "c1"), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });

  it("uses correct query key", async () => {
    mockGet.mockResolvedValue({
      data: {
        chunk_id: "c1",
        document_id: "d1",
        document_filename: "a.pdf",
        sequence_number: 0,
        total_chunks: 1,
        text: "text",
        page_start: 1,
        page_end: 1,
        context_before: null,
        context_after: null,
      },
      error: undefined,
    });

    const { wrapper, queryClient } = createWrapper();
    renderHook(() => useChunkContext("inv-1", "c1"), { wrapper });

    await waitFor(() => {
      const state = queryClient.getQueryState([
        "chunk-context",
        "inv-1",
        "c1",
      ]);
      expect(state?.status).toBe("success");
    });
  });
});
