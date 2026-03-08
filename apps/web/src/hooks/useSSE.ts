import { useEffect, useRef, useState, useCallback } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { useQueryClient } from "@tanstack/react-query";
import type { DocumentListResponse } from "@/hooks/useDocuments";

interface SSEEvent {
  type: "document.processing" | "document.complete" | "document.failed";
  investigation_id: string;
  timestamp: string;
  payload: {
    document_id: string;
    stage?: string;
    error?: string;
  };
}

interface UseSSEReturn {
  isConnected: boolean;
  connectionError: boolean;
  reconnectCount: number;
}

const MAX_RECONNECT_FAILURES = 3;

class FatalSSEError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FatalSSEError";
  }
}

export function useSSE(
  investigationId: string,
  enabled: boolean,
): UseSSEReturn {
  const queryClient = useQueryClient();
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const [reconnectCount, setReconnectCount] = useState(0);
  const reconnectCountRef = useRef(0);

  const updateDocumentCache = useCallback(
    (event: SSEEvent) => {
      queryClient.setQueryData<DocumentListResponse>(
        ["documents", investigationId],
        (old) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.map((doc) => {
              if (doc.id !== event.payload.document_id) return doc;
              switch (event.type) {
                case "document.processing":
                  return { ...doc, status: "extracting_text" };
                case "document.complete":
                  return { ...doc, status: "complete" };
                case "document.failed":
                  return {
                    ...doc,
                    status: "failed",
                    error_message: event.payload.error ?? null,
                  };
                default:
                  return doc;
              }
            }),
          };
        },
      );
    },
    [queryClient, investigationId],
  );

  useEffect(() => {
    if (!enabled) {
      setIsConnected(false);
      return;
    }

    const ctrl = new AbortController();

    fetchEventSource(
      `/api/v1/investigations/${investigationId}/events`,
      {
        signal: ctrl.signal,

        async onopen(response) {
          if (!response.ok) {
            throw new FatalSSEError(
              `SSE connection failed: ${response.status}`,
            );
          }
          setIsConnected(true);
          reconnectCountRef.current = 0;
          setReconnectCount(0);
          setConnectionError(false);
          queryClient.invalidateQueries({
            queryKey: ["documents", investigationId],
          });
        },

        onmessage(ev) {
          let event: SSEEvent;
          try {
            event = JSON.parse(ev.data);
          } catch {
            // Ignore malformed JSON from server
            return;
          }
          updateDocumentCache(event);
        },

        onerror() {
          setIsConnected(false);
          reconnectCountRef.current += 1;
          const count = reconnectCountRef.current;
          setReconnectCount(count);
          if (count >= MAX_RECONNECT_FAILURES) {
            setConnectionError(true);
            throw new FatalSSEError(
              `SSE stopped after ${MAX_RECONNECT_FAILURES} failed reconnects`,
            );
          }
          // Return undefined to use default retry behavior
        },
      },
    );

    return () => {
      ctrl.abort();
      setIsConnected(false);
    };
  }, [investigationId, enabled, queryClient, updateDocumentCache]);

  return { isConnected, connectionError, reconnectCount };
}
