import { useEffect, useRef, useState, useCallback } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { useQueryClient } from "@tanstack/react-query";

interface ServiceStatusEvent {
  type: "service.status";
  investigation_id: string;
  timestamp: string;
  payload: {
    service: string;
    status: "healthy" | "unhealthy" | "unavailable";
    detail: string;
  };
}

export interface ServiceNotification {
  id: string;
  service: string;
  status: "healthy" | "unhealthy" | "unavailable";
  detail: string;
  timestamp: number;
}

interface UseSystemSSEReturn {
  notifications: ServiceNotification[];
  dismissNotification: (id: string) => void;
}

const SERVICE_LABELS: Record<string, string> = {
  ollama: "Ollama LLM",
  neo4j: "Neo4j Graph",
  qdrant: "Qdrant Vector",
  redis: "Redis",
  postgres: "PostgreSQL",
};

/**
 * Global SSE hook for system-level service status changes.
 * Invalidates health query cache on any transition and tracks notifications.
 */
export function useSystemSSE(): UseSystemSSEReturn {
  const queryClient = useQueryClient();
  const [notifications, setNotifications] = useState<ServiceNotification[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const dismissNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  // Auto-dismiss recovery notifications after 5 seconds
  useEffect(() => {
    const recoveryNotifications = notifications.filter(
      (n) => n.status === "healthy",
    );
    if (recoveryNotifications.length === 0) return;

    const timers = recoveryNotifications.map((n) =>
      setTimeout(() => dismissNotification(n.id), 5000),
    );
    return () => timers.forEach(clearTimeout);
  }, [notifications, dismissNotification]);

  useEffect(() => {
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    fetchEventSource("/api/v1/events/system", {
      signal: ctrl.signal,
      openWhenHidden: true,

      onmessage(ev) {
        let event: ServiceStatusEvent;
        try {
          event = JSON.parse(ev.data);
        } catch {
          return;
        }

        if (event.type !== "service.status") return;

        const { service, status, detail } = event.payload;

        // Invalidate health query cache to trigger StatusBar + StatusPage re-render
        queryClient.invalidateQueries({ queryKey: ["health"] });

        const label = SERVICE_LABELS[service] ?? service;
        const notification: ServiceNotification = {
          id: `${service}-${Date.now()}`,
          service: label,
          status,
          detail,
          timestamp: Date.now(),
        };

        setNotifications((prev) => {
          // Remove any existing notification for the same service
          const filtered = prev.filter(
            (n) => !n.id.startsWith(`${service}-`) && n.service !== label,
          );
          return [...filtered, notification];
        });
      },

      onerror() {
        // Silently retry — system SSE is best-effort
      },
    });

    return () => {
      ctrl.abort();
    };
  }, [queryClient]);

  return { notifications, dismissNotification };
}
