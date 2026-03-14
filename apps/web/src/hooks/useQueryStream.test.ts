import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

// Mock @microsoft/fetch-event-source
const mockFetchEventSource = vi.fn();
vi.mock("@microsoft/fetch-event-source", () => ({
  fetchEventSource: (...args: unknown[]) => mockFetchEventSource(...args),
}));

// Mock crypto.randomUUID
let uuidCounter = 0;
vi.stubGlobal(
  "crypto",
  Object.assign({}, globalThis.crypto, {
    randomUUID: () => `test-uuid-${++uuidCounter}`,
  }),
);

import { useQueryStream } from "./useQueryStream";

const investigationId = "inv-123";

describe("useQueryStream", () => {
  beforeEach(() => {
    uuidCounter = 0;
    mockFetchEventSource.mockReset();
    mockFetchEventSource.mockImplementation(() => new Promise(() => {}));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns initial idle state", () => {
    const { result } = renderHook(() => useQueryStream(investigationId));
    expect(result.current.queryStatus).toBe("idle");
    expect(result.current.conversationEntries).toEqual([]);
    expect(result.current.currentStreamingText).toBe("");
  });

  it("transitions: idle → translating → searching → streaming → complete", async () => {
    let onmessage: ((ev: { event: string; data: string }) => void) | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        onmessage = opts.onmessage as typeof onmessage;
        return new Promise(() => {});
      },
    );

    const { result } = renderHook(() => useQueryStream(investigationId));

    act(() => {
      result.current.submitQuery("Who is Horvat?");
    });

    expect(result.current.queryStatus).toBe("translating");

    await waitFor(() => {
      expect(onmessage).toBeDefined();
    });

    act(() => {
      onmessage!({
        event: "query.translating",
        data: JSON.stringify({
          query_id: "q1",
          message: "Translating your question...",
        }),
      });
    });
    expect(result.current.queryStatus).toBe("translating");

    act(() => {
      onmessage!({
        event: "query.searching",
        data: JSON.stringify({
          query_id: "q1",
          message: "Searching knowledge graph and documents...",
        }),
      });
    });
    expect(result.current.queryStatus).toBe("searching");

    act(() => {
      onmessage!({
        event: "query.streaming",
        data: JSON.stringify({ query_id: "q1", chunk: "Deputy Mayor " }),
      });
    });
    expect(result.current.queryStatus).toBe("streaming");
    expect(result.current.currentStreamingText).toBe("Deputy Mayor ");

    act(() => {
      onmessage!({
        event: "query.complete",
        data: JSON.stringify({
          query_id: "q1",
          answer: "Deputy Mayor Horvat signed contract #2024-089 [1]",
          citations: [
            {
              citation_number: 1,
              document_id: "doc-1",
              document_filename: "contract.pdf",
              chunk_id: "ch-1",
              page_start: 3,
              page_end: 3,
              text_excerpt: "Horvat signed...",
            },
          ],
          entities_mentioned: [
            { entity_id: "e1", name: "Horvat", type: "Person" },
          ],
          suggested_followups: ["What other contracts did Horvat sign?"],
          no_results: false,
        }),
      });
    });
    expect(result.current.queryStatus).toBe("complete");
    expect(result.current.currentStreamingText).toBe("");
  });

  it("accumulates streaming chunks", async () => {
    let onmessage: ((ev: { event: string; data: string }) => void) | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        onmessage = opts.onmessage as typeof onmessage;
        return new Promise(() => {});
      },
    );

    const { result } = renderHook(() => useQueryStream(investigationId));

    act(() => {
      result.current.submitQuery("test");
    });

    await waitFor(() => {
      expect(onmessage).toBeDefined();
    });

    act(() => {
      onmessage!({
        event: "query.streaming",
        data: JSON.stringify({ query_id: "q1", chunk: "Hello " }),
      });
    });
    expect(result.current.currentStreamingText).toBe("Hello ");

    act(() => {
      onmessage!({
        event: "query.streaming",
        data: JSON.stringify({ query_id: "q1", chunk: "world" }),
      });
    });
    expect(result.current.currentStreamingText).toBe("Hello world");
  });

  it("parses query.complete payload fully", async () => {
    let onmessage: ((ev: { event: string; data: string }) => void) | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        onmessage = opts.onmessage as typeof onmessage;
        return new Promise(() => {});
      },
    );

    const { result } = renderHook(() => useQueryStream(investigationId));

    act(() => {
      result.current.submitQuery("Who is Horvat?");
    });

    await waitFor(() => {
      expect(onmessage).toBeDefined();
    });

    act(() => {
      onmessage!({
        event: "query.complete",
        data: JSON.stringify({
          query_id: "q1",
          answer: "**Horvat** is connected to **GreenBuild LLC** [1]",
          citations: [
            {
              citation_number: 1,
              document_id: "doc-1",
              document_filename: "report.pdf",
              chunk_id: "ch-1",
              page_start: 1,
              page_end: 2,
              text_excerpt: "excerpt",
            },
          ],
          entities_mentioned: [
            { entity_id: "e1", name: "Horvat", type: "Person" },
            { entity_id: "e2", name: "GreenBuild LLC", type: "Organization" },
          ],
          suggested_followups: ["Tell me more about GreenBuild"],
          no_results: false,
        }),
      });
    });

    const entry = result.current.conversationEntries[0];
    expect(entry.status).toBe("complete");
    expect(entry.answer).toBe(
      "**Horvat** is connected to **GreenBuild LLC** [1]",
    );
    expect(entry.citations).toHaveLength(1);
    expect(entry.citations[0].document_filename).toBe("report.pdf");
    expect(entry.entitiesMentioned).toHaveLength(2);
    expect(entry.suggestedFollowups).toEqual(["Tell me more about GreenBuild"]);
    expect(entry.noResults).toBe(false);
  });

  it("handles query.failed event", async () => {
    let onmessage: ((ev: { event: string; data: string }) => void) | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        onmessage = opts.onmessage as typeof onmessage;
        return new Promise(() => {});
      },
    );

    const { result } = renderHook(() => useQueryStream(investigationId));

    act(() => {
      result.current.submitQuery("test");
    });

    await waitFor(() => {
      expect(onmessage).toBeDefined();
    });

    act(() => {
      onmessage!({
        event: "query.failed",
        data: JSON.stringify({
          query_id: "q1",
          error: "Graph database unavailable",
        }),
      });
    });

    expect(result.current.queryStatus).toBe("error");
    const entry = result.current.conversationEntries[0];
    expect(entry.status).toBe("error");
    expect(entry.error).toBe("Graph database unavailable");
  });

  it("adds conversation turn after complete", async () => {
    let onmessage: ((ev: { event: string; data: string }) => void) | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        onmessage = opts.onmessage as typeof onmessage;
        return new Promise(() => {});
      },
    );

    const { result } = renderHook(() => useQueryStream(investigationId));

    act(() => {
      result.current.submitQuery("Who is Horvat?");
    });

    await waitFor(() => {
      expect(onmessage).toBeDefined();
    });

    act(() => {
      onmessage!({
        event: "query.complete",
        data: JSON.stringify({
          query_id: "q1",
          answer: "Horvat is the deputy mayor.",
          citations: [],
          entities_mentioned: [],
          suggested_followups: [],
          no_results: false,
        }),
      });
    });

    expect(result.current.conversationEntries).toHaveLength(1);
    expect(result.current.conversationEntries[0].question).toBe(
      "Who is Horvat?",
    );
    expect(result.current.conversationEntries[0].answer).toBe(
      "Horvat is the deputy mayor.",
    );
  });

  it("passes conversation history to subsequent queries", async () => {
    let onmessage: ((ev: { event: string; data: string }) => void) | undefined;
    let capturedBody: string | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        onmessage = opts.onmessage as typeof onmessage;
        capturedBody = opts.body as string;
        return new Promise(() => {});
      },
    );

    const { result } = renderHook(() => useQueryStream(investigationId));

    // First query
    act(() => {
      result.current.submitQuery("Who is Horvat?");
    });
    await waitFor(() => {
      expect(onmessage).toBeDefined();
    });

    // Complete first query
    act(() => {
      onmessage!({
        event: "query.complete",
        data: JSON.stringify({
          query_id: "q1",
          answer: "Horvat is the deputy mayor.",
          citations: [],
          entities_mentioned: [],
          suggested_followups: [],
          no_results: false,
        }),
      });
    });

    // Reset mock to capture second call
    mockFetchEventSource.mockReset();
    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        capturedBody = opts.body as string;
        return new Promise(() => {});
      },
    );

    // Second query
    act(() => {
      result.current.submitQuery("What contracts did he sign?");
    });

    const body = JSON.parse(capturedBody!);
    expect(body.question).toBe("What contracts did he sign?");
    expect(body.conversation_history).toEqual([
      { role: "user", content: "Who is Horvat?" },
      { role: "assistant", content: "Horvat is the deputy mayor." },
    ]);
  });

  it("handles no_results flag", async () => {
    let onmessage: ((ev: { event: string; data: string }) => void) | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        onmessage = opts.onmessage as typeof onmessage;
        return new Promise(() => {});
      },
    );

    const { result } = renderHook(() => useQueryStream(investigationId));

    act(() => {
      result.current.submitQuery("test");
    });

    await waitFor(() => {
      expect(onmessage).toBeDefined();
    });

    act(() => {
      onmessage!({
        event: "query.complete",
        data: JSON.stringify({
          query_id: "q1",
          answer: "",
          citations: [],
          entities_mentioned: [],
          suggested_followups: [],
          no_results: true,
        }),
      });
    });

    expect(result.current.conversationEntries[0].noResults).toBe(true);
  });

  it("handles SSE connection error", async () => {
    let onerror: (() => void) | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        onerror = opts.onerror as typeof onerror;
        return new Promise(() => {});
      },
    );

    const { result } = renderHook(() => useQueryStream(investigationId));

    act(() => {
      result.current.submitQuery("test");
    });

    await waitFor(() => {
      expect(onerror).toBeDefined();
    });

    act(() => {
      expect(() => onerror!()).toThrow("SSE connection error");
    });

    expect(result.current.queryStatus).toBe("error");
    expect(result.current.conversationEntries[0].status).toBe("error");
    expect(result.current.conversationEntries[0].error).toBe(
      "Connection error. Please try again.",
    );
  });

  it("POSTs to correct endpoint with question", () => {
    const { result } = renderHook(() => useQueryStream(investigationId));

    act(() => {
      result.current.submitQuery("Who is Horvat?");
    });

    expect(mockFetchEventSource).toHaveBeenCalledWith(
      `/api/v1/investigations/${investigationId}/query/`,
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );

    const body = JSON.parse(
      (
        mockFetchEventSource.mock.calls[0][1] as Record<string, unknown>
      ).body as string,
    );
    expect(body.question).toBe("Who is Horvat?");
  });

  it("aborts SSE connection on unmount", async () => {
    let capturedSignal: AbortSignal | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        capturedSignal = opts.signal as AbortSignal;
        return new Promise(() => {});
      },
    );

    const { result, unmount } = renderHook(() =>
      useQueryStream(investigationId),
    );

    act(() => {
      result.current.submitQuery("test");
    });

    await waitFor(() => {
      expect(capturedSignal).toBeDefined();
    });

    expect(capturedSignal!.aborted).toBe(false);
    unmount();
    expect(capturedSignal!.aborted).toBe(true);
  });

  it("resetConversation clears all state", async () => {
    let onmessage: ((ev: { event: string; data: string }) => void) | undefined;

    mockFetchEventSource.mockImplementation(
      async (_url: string, opts: Record<string, unknown>) => {
        onmessage = opts.onmessage as typeof onmessage;
        return new Promise(() => {});
      },
    );

    const { result } = renderHook(() => useQueryStream(investigationId));

    act(() => {
      result.current.submitQuery("test");
    });

    await waitFor(() => {
      expect(onmessage).toBeDefined();
    });

    act(() => {
      onmessage!({
        event: "query.complete",
        data: JSON.stringify({
          query_id: "q1",
          answer: "Answer",
          citations: [],
          entities_mentioned: [],
          suggested_followups: [],
          no_results: false,
        }),
      });
    });

    expect(result.current.conversationEntries).toHaveLength(1);

    act(() => {
      result.current.resetConversation();
    });

    expect(result.current.queryStatus).toBe("idle");
    expect(result.current.conversationEntries).toEqual([]);
    expect(result.current.currentStreamingText).toBe("");
  });
});
