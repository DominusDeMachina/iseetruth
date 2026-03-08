import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

// Mock api client
const mockGet = vi.fn();
vi.mock("@/lib/api-client", () => ({
  api: { GET: (...args: unknown[]) => mockGet(...args) },
}));

import { useDocumentText } from "./useDocuments";

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

describe("useDocumentText", () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it("does not fetch when documentId is null", () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(
      () => useDocumentText("inv-1", null),
      { wrapper },
    );
    expect(result.current.isFetching).toBe(false);
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("fetches text when documentId is provided", async () => {
    const mockData = {
      document_id: "doc-1",
      filename: "report.pdf",
      page_count: 3,
      extracted_text: "--- Page 1 ---\nHello world",
    };
    mockGet.mockResolvedValue({ data: mockData, error: undefined });

    const { wrapper } = createWrapper();
    const { result } = renderHook(
      () => useDocumentText("inv-1", "doc-1"),
      { wrapper },
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockData);
    expect(mockGet).toHaveBeenCalledWith(
      "/api/v1/investigations/{investigation_id}/documents/{document_id}/text",
      {
        params: {
          path: {
            investigation_id: "inv-1",
            document_id: "doc-1",
          },
        },
      },
    );
  });

  it("uses correct query key", async () => {
    mockGet.mockResolvedValue({
      data: { document_id: "doc-1", filename: "a.pdf", page_count: 1, extracted_text: null },
      error: undefined,
    });

    const { wrapper, queryClient } = createWrapper();
    renderHook(() => useDocumentText("inv-1", "doc-1"), { wrapper });

    await waitFor(() => {
      const state = queryClient.getQueryState(["document-text", "inv-1", "doc-1"]);
      expect(state?.status).toBe("success");
    });
  });

  it("throws on API error", async () => {
    mockGet.mockResolvedValue({ data: undefined, error: { detail: "Not found" } });

    const { wrapper } = createWrapper();
    const { result } = renderHook(
      () => useDocumentText("inv-1", "doc-1"),
      { wrapper },
    );

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});
