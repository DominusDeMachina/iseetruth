import { useEffect, useRef, useState, useCallback } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { useQueryClient } from "@tanstack/react-query";
import type { DocumentListResponse, DocumentWithProgress } from "@/hooks/useDocuments";

interface SSEEvent {
  type:
    | "document.queued"
    | "document.processing"
    | "document.complete"
    | "document.failed"
    | "entity.discovered";
  investigation_id: string;
  timestamp: string;
  payload: {
    document_id: string;
    stage?: string;
    progress?: number;
    chunk_count?: number;
    chunks_done?: number;
    error?: string;
    entity_count?: number;
    relationship_count?: number;
    embedded_count?: number;
    extraction_confidence?: number;
    entity_type?: string;
    entity_name?: string;
  };
}

export interface DiscoveredEntity {
  documentId: string;
  entityType: string;
  entityName: string;
  timestamp: string;
}

interface UseSSEReturn {
  isConnected: boolean;
  connectionError: boolean;
  reconnectCount: number;
  discoveredEntities: DiscoveredEntity[];
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
  const [discoveredEntities, setDiscoveredEntities] = useState<DiscoveredEntity[]>([]);

  const updateDocumentCache = useCallback(
    (event: SSEEvent) => {
      // Accumulate discovered entities
      if (
        event.type === "entity.discovered" &&
        event.payload.entity_name &&
        event.payload.entity_type
      ) {
        setDiscoveredEntities((prev) => [
          ...prev,
          {
            documentId: event.payload.document_id,
            entityType: event.payload.entity_type!,
            entityName: event.payload.entity_name!,
            timestamp: event.timestamp,
          },
        ]);
      }

      queryClient.setQueryData<DocumentListResponse>(
        ["documents", investigationId],
        (old) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.map((doc) => {
              if (doc.id !== event.payload.document_id) return doc;
              switch (event.type) {
                case "document.queued":
                  return {
                    ...doc,
                    status: "queued",
                    error_message: null,
                    failed_stage: null,
                  };
                case "document.processing": {
                  const updated: DocumentWithProgress = {
                    ...doc,
                    status: event.payload.stage ?? doc.status,
                  };
                  if (event.payload.progress != null)
                    updated._progress = event.payload.progress;
                  if (event.payload.chunk_count != null)
                    updated._chunkCount = event.payload.chunk_count;
                  if (event.payload.chunks_done != null)
                    updated._chunksDone = event.payload.chunks_done;
                  return updated;
                }
                case "document.complete":
                  return { ...doc, status: "complete" };
                case "document.failed":
                  return {
                    ...doc,
                    status: "failed",
                    error_message: event.payload.error ?? null,
                    failed_stage: event.payload.stage ?? null,
                  };
                default:
                  return doc;
              }
            }),
          };
        },
      );

      if (event.type === "document.complete") {
        // Clear discovered entities for this document
        setDiscoveredEntities((prev) =>
          prev.filter((e) => e.documentId !== event.payload.document_id),
        );
        queryClient.invalidateQueries({
          queryKey: ["documents", investigationId],
        });
        queryClient.invalidateQueries({
          queryKey: ["entities", investigationId],
        });
      }
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
      setDiscoveredEntities([]);
    };
  }, [investigationId, enabled, queryClient, updateDocumentCache]);

  return { isConnected, connectionError, reconnectCount, discoveredEntities };
}
