import { CheckCircle2, AlertTriangle, X } from "lucide-react";
import type { ServiceNotification } from "@/hooks/useSystemSSE";

interface ServiceNotificationsProps {
  notifications: ServiceNotification[];
  onDismiss: (id: string) => void;
}

export function ServiceNotifications({
  notifications,
  onDismiss,
}: ServiceNotificationsProps) {
  if (notifications.length === 0) return null;

  return (
    <div
      className="fixed bottom-14 right-4 z-50 flex flex-col gap-2"
      role="status"
      aria-live="polite"
    >
      {notifications.map((n) => {
        const isRecovery = n.status === "healthy";
        return (
          <div
            key={n.id}
            className="flex items-start gap-2 rounded-lg border bg-[var(--bg-elevated)] px-4 py-3 shadow-lg"
            style={{
              borderLeftWidth: "3px",
              borderLeftColor: isRecovery
                ? "var(--status-success)"
                : "var(--status-warning)",
            }}
          >
            {isRecovery ? (
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-[var(--status-success)]" />
            ) : (
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--status-warning)]" />
            )}
            <div className="flex-1 text-sm">
              <span className="text-[var(--text-primary)]">
                {isRecovery
                  ? `${n.service} is back online`
                  : `${n.service} is unavailable — some features are limited`}
              </span>
            </div>
            <button
              onClick={() => onDismiss(n.id)}
              className="shrink-0 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              aria-label={`Dismiss ${n.service} notification`}
            >
              <X className="size-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
