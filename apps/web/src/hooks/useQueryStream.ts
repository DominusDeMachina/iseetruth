import { useState, useCallback, useRef, useEffect } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import type {
  QueryStatus,
  Citation,
  EntityReference,
  ConversationEntry,
} from "@/components/qa/types";

export interface UseQueryStreamReturn {
  queryStatus: QueryStatus;
  conversationEntries: ConversationEntry[];
  currentStreamingText: string;
  submitQuery: (question: string) => void;
  resetConversation: () => void;
}

export function useQueryStream(investigationId: string): UseQueryStreamReturn {
  const [queryStatus, setQueryStatus] = useState<QueryStatus>("idle");
  const [conversationEntries, setConversationEntries] = useState<
    ConversationEntry[]
  >([]);
  const [currentStreamingText, setCurrentStreamingText] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  // Abort SSE connection on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // Use ref for stable closure in submitQuery
  const entriesRef = useRef<ConversationEntry[]>([]);
  entriesRef.current = conversationEntries;

  const submitQuery = useCallback(
    (question: string) => {
      // Abort any existing query
      if (abortRef.current) {
        abortRef.current.abort();
      }

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      // Create new conversation entry
      const entryId = crypto.randomUUID();
      const newEntry: ConversationEntry = {
        id: entryId,
        question,
        answer: null,
        citations: [],
        entitiesMentioned: [],
        suggestedFollowups: [],
        noResults: false,
        status: "streaming",
      };

      setConversationEntries((prev) => [...prev, newEntry]);
      setCurrentStreamingText("");
      setQueryStatus("translating");

      // Build conversation history from completed entries
      const history = entriesRef.current
        .filter((e) => e.status === "complete" && e.answer)
        .flatMap((e) => [
          { role: "user" as const, content: e.question },
          { role: "assistant" as const, content: e.answer! },
        ]);

      let accumulatedText = "";

      fetchEventSource(
        `/api/v1/investigations/${investigationId}/query/`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question,
            conversation_history: history.length > 0 ? history : null,
          }),
          signal: ctrl.signal,
          openWhenHidden: true,

          onmessage(ev) {
            let data: Record<string, unknown>;
            try {
              data = JSON.parse(ev.data);
            } catch {
              return;
            }

            switch (ev.event) {
              case "query.translating":
                setQueryStatus("translating");
                break;
              case "query.searching":
                setQueryStatus("searching");
                break;
              case "query.streaming":
                setQueryStatus("streaming");
                accumulatedText += (data.chunk as string) ?? "";
                setCurrentStreamingText(accumulatedText);
                break;
              case "query.degraded": {
                // Qdrant is down — results are graph-only
                const degradedMsg =
                  (data.message as string) ??
                  "Results based on graph data only — vector search unavailable";
                setConversationEntries((prev) =>
                  prev.map((e) =>
                    e.id === entryId
                      ? { ...e, degradedMessage: degradedMsg }
                      : e,
                  ),
                );
                break;
              }
              case "query.complete": {
                setQueryStatus("complete");
                const answer = data.answer as string;
                const citations = (data.citations ?? []) as Citation[];
                const entitiesMentioned = (data.entities_mentioned ??
                  []) as EntityReference[];
                const suggestedFollowups = (data.suggested_followups ??
                  []) as string[];
                const noResults = (data.no_results ?? false) as boolean;
                const degraded = (data.degraded ?? false) as boolean;

                setConversationEntries((prev) =>
                  prev.map((e) =>
                    e.id === entryId
                      ? {
                          ...e,
                          answer,
                          citations,
                          entitiesMentioned,
                          suggestedFollowups,
                          noResults,
                          degraded,
                          status: "complete" as const,
                        }
                      : e,
                  ),
                );
                setCurrentStreamingText("");
                break;
              }
              case "query.failed": {
                setQueryStatus("error");
                const errorMsg =
                  (data.error as string) ?? "An unexpected error occurred";
                setConversationEntries((prev) =>
                  prev.map((e) =>
                    e.id === entryId
                      ? { ...e, status: "error" as const, error: errorMsg }
                      : e,
                  ),
                );
                setCurrentStreamingText("");
                break;
              }
            }
          },

          onerror() {
            setQueryStatus("error");
            setConversationEntries((prev) =>
              prev.map((e) =>
                e.id === entryId
                  ? {
                      ...e,
                      status: "error" as const,
                      error: "Connection error. Please try again.",
                    }
                  : e,
              ),
            );
            setCurrentStreamingText("");
            // Throw to prevent automatic retries
            throw new Error("SSE connection error");
          },
        },
      );
    },
    [investigationId],
  );

  const resetConversation = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    setConversationEntries([]);
    setCurrentStreamingText("");
    setQueryStatus("idle");
  }, []);

  return {
    queryStatus,
    conversationEntries,
    currentStreamingText,
    submitQuery,
    resetConversation,
  };
}
