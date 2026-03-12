import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import type { DocumentListResponse } from "@/hooks/useDocuments";

// Mock @microsoft/fetch-event-source
const mockFetchEventSource = vi.fn();
vi.mock("@microsoft/fetch-event-source", () => ({
  fetchEventSource: (...args: unknown[]) => mockFetchEventSource(...args),
}));

import { useSSE } from "./useSSE";

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

const investigationId = "inv-123";

describe("useSSE", () => {
  beforeEach(() => {
    mockFetchEventSource.mockReset();
    // Default: resolve after capturing callbacks
    mockFetchEventSource.mockImplementation(() => new Promise(() => {}));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not connect when enabled is false", () => {
    const { wrapper } = createWrapper();
    renderHook(() => useSSE(investigationId, false), { wrapper });
    expect(mockFetchEventSource).not.toHaveBeenCalled();
  });

  it("connects to SSE endpoint when enabled is true", () => {
    const { wrapper } = createWrapper();
    renderHook(() => useSSE(investigationId, true), { wrapper });
    expect(mockFetchEventSource).toHaveBeenCalledWith(
      `/api/v1/investigations/${investigationId}/events`,
      expect.objectContaining({
        signal: expect.any(AbortSignal),
        onmessage: expect.any(Function),
        onopen: expect.any(Function),
        onerror: expect.any(Function),
      }),
    );
  });

  it("returns initial state with isConnected false", () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useSSE(investigationId, false), {
      wrapper,
    });
    expect(result.current.isConnected).toBe(false);
    expect(result.current.connectionError).toBe(false);
    expect(result.current.reconnectCount).toBe(0);
  });

  it("sets isConnected true on successful open", async () => {
    const { wrapper } = createWrapper();
    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        const onopen = opts.onopen as (response: Response) => Promise<void>;
        await onopen(new Response(null, { status: 200 }));
        return new Promise(() => {});
      },
    );

    const { result } = renderHook(() => useSSE(investigationId, true), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });
  });

  it("updates TanStack Query cache on document.processing event", async () => {
    const { wrapper, queryClient } = createWrapper();

    const initialData: DocumentListResponse = {
      items: [
        {
          id: "doc-1",
          investigation_id: investigationId,
          filename: "test.pdf",
          size_bytes: 1000,
          sha256_checksum: "abc",
          status: "queued",
          page_count: null,
          extracted_text: null,
          error_message: null,
          extraction_quality: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      total: 1,
    };
    queryClient.setQueryData(["documents", investigationId], initialData);

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        const onmessage = opts.onmessage as (ev: { data: string }) => void;
        onmessage({
          data: JSON.stringify({
            type: "document.processing",
            investigation_id: investigationId,
            timestamp: "2026-01-01T00:00:01Z",
            payload: { document_id: "doc-1", stage: "extracting_text" },
          }),
        });
        return new Promise(() => {});
      },
    );

    renderHook(() => useSSE(investigationId, true), { wrapper });

    await waitFor(() => {
      const cached = queryClient.getQueryData<DocumentListResponse>([
        "documents",
        investigationId,
      ]);
      expect(cached?.items[0].status).toBe("extracting_text");
    });
  });

  it("updates cache on document.complete event", async () => {
    const { wrapper, queryClient } = createWrapper();

    const initialData: DocumentListResponse = {
      items: [
        {
          id: "doc-1",
          investigation_id: investigationId,
          filename: "test.pdf",
          size_bytes: 1000,
          sha256_checksum: "abc",
          status: "extracting_text",
          page_count: null,
          extracted_text: null,
          error_message: null,
          extraction_quality: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      total: 1,
    };
    queryClient.setQueryData(["documents", investigationId], initialData);

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        const onmessage = opts.onmessage as (ev: { data: string }) => void;
        onmessage({
          data: JSON.stringify({
            type: "document.complete",
            investigation_id: investigationId,
            timestamp: "2026-01-01T00:00:02Z",
            payload: { document_id: "doc-1" },
          }),
        });
        return new Promise(() => {});
      },
    );

    renderHook(() => useSSE(investigationId, true), { wrapper });

    await waitFor(() => {
      const cached = queryClient.getQueryData<DocumentListResponse>([
        "documents",
        investigationId,
      ]);
      expect(cached?.items[0].status).toBe("complete");
    });
  });

  it("updates cache on document.failed event with error_message", async () => {
    const { wrapper, queryClient } = createWrapper();

    const initialData: DocumentListResponse = {
      items: [
        {
          id: "doc-1",
          investigation_id: investigationId,
          filename: "test.pdf",
          size_bytes: 1000,
          sha256_checksum: "abc",
          status: "extracting_text",
          page_count: null,
          extracted_text: null,
          error_message: null,
          extraction_quality: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      total: 1,
    };
    queryClient.setQueryData(["documents", investigationId], initialData);

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        const onmessage = opts.onmessage as (ev: { data: string }) => void;
        onmessage({
          data: JSON.stringify({
            type: "document.failed",
            investigation_id: investigationId,
            timestamp: "2026-01-01T00:00:02Z",
            payload: { document_id: "doc-1", error: "OCR engine timeout" },
          }),
        });
        return new Promise(() => {});
      },
    );

    renderHook(() => useSSE(investigationId, true), { wrapper });

    await waitFor(() => {
      const cached = queryClient.getQueryData<DocumentListResponse>([
        "documents",
        investigationId,
      ]);
      expect(cached?.items[0].status).toBe("failed");
      expect(cached?.items[0].error_message).toBe("OCR engine timeout");
    });
  });

  it("invalidates entities cache on document.complete event", async () => {
    const { wrapper, queryClient } = createWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const initialData: DocumentListResponse = {
      items: [
        {
          id: "doc-1",
          investigation_id: investigationId,
          filename: "test.pdf",
          size_bytes: 1000,
          sha256_checksum: "abc",
          status: "extracting_text",
          page_count: null,
          extracted_text: null,
          error_message: null,
          extraction_quality: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      total: 1,
    };
    queryClient.setQueryData(["documents", investigationId], initialData);

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        const onmessage = opts.onmessage as (ev: { data: string }) => void;
        onmessage({
          data: JSON.stringify({
            type: "document.complete",
            investigation_id: investigationId,
            timestamp: "2026-01-01T00:00:02Z",
            payload: { document_id: "doc-1" },
          }),
        });
        return new Promise(() => {});
      },
    );

    renderHook(() => useSSE(investigationId, true), { wrapper });

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["entities", investigationId],
      });
    });
  });

  it("invalidates query on open to reconcile state", async () => {
    const { wrapper, queryClient } = createWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        const onopen = opts.onopen as (response: Response) => Promise<void>;
        await onopen(new Response(null, { status: 200 }));
        return new Promise(() => {});
      },
    );

    renderHook(() => useSSE(investigationId, true), { wrapper });

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["documents", investigationId],
      });
    });
  });

  it("throws on non-ok response in onopen", async () => {
    const { wrapper } = createWrapper();

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        const onopen = opts.onopen as (response: Response) => Promise<void>;
        await onopen(new Response(null, { status: 404 }));
      },
    );

    renderHook(() => useSSE(investigationId, true), { wrapper });

    await waitFor(() => {
      expect(mockFetchEventSource).toHaveBeenCalled();
    });
  });

  it("tracks reconnect count and sets connectionError after 3 failures", async () => {
    const { wrapper } = createWrapper();
    let errorCallback: (() => void) | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        errorCallback = opts.onerror as () => void;
        return new Promise(() => {});
      },
    );

    const { result } = renderHook(() => useSSE(investigationId, true), {
      wrapper,
    });

    await waitFor(() => {
      expect(errorCallback).toBeDefined();
    });

    // Simulate first 2 reconnect failures (no throw)
    act(() => {
      errorCallback!();
    });
    expect(result.current.reconnectCount).toBe(1);
    expect(result.current.connectionError).toBe(false);

    act(() => {
      errorCallback!();
    });
    expect(result.current.reconnectCount).toBe(2);
    expect(result.current.connectionError).toBe(false);

    // 3rd failure throws to stop retries
    act(() => {
      expect(() => errorCallback!()).toThrow(
        "SSE stopped after 3 failed reconnects",
      );
    });
    expect(result.current.reconnectCount).toBe(3);
    expect(result.current.connectionError).toBe(true);
  });

  it("aborts connection on unmount", () => {
    const { wrapper } = createWrapper();
    let capturedSignal: AbortSignal | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        capturedSignal = opts.signal as AbortSignal;
        return new Promise(() => {});
      },
    );

    const { unmount } = renderHook(() => useSSE(investigationId, true), {
      wrapper,
    });

    expect(capturedSignal).toBeDefined();
    expect(capturedSignal!.aborted).toBe(false);

    unmount();
    expect(capturedSignal!.aborted).toBe(true);
  });

  it("resets reconnect count on successful reconnection", async () => {
    const { wrapper } = createWrapper();
    let errorCallback: ((err: Error) => number | void) | undefined;
    let openCallback:
      | ((response: Response) => Promise<void>)
      | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        errorCallback = opts.onerror as (err: Error) => number | void;
        openCallback = opts.onopen as (response: Response) => Promise<void>;
        return new Promise(() => {});
      },
    );

    const { result } = renderHook(() => useSSE(investigationId, true), {
      wrapper,
    });

    await waitFor(() => {
      expect(errorCallback).toBeDefined();
    });

    // Simulate 2 reconnect failures
    act(() => {
      errorCallback!(new Error("connection failed"));
      errorCallback!(new Error("connection failed"));
    });
    expect(result.current.reconnectCount).toBe(2);

    // Successful reconnection
    await act(async () => {
      await openCallback!(new Response(null, { status: 200 }));
    });

    expect(result.current.reconnectCount).toBe(0);
    expect(result.current.connectionError).toBe(false);
  });
});
