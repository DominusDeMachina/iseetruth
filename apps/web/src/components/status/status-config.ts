import { CheckCircle2, XCircle, MinusCircle } from "lucide-react";

export const statusConfig = {
  healthy: {
    icon: CheckCircle2,
    color: "text-[var(--status-success)]",
    badgeBg:
      "bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/30",
    label: "Healthy",
  },
  unhealthy: {
    icon: XCircle,
    color: "text-[var(--status-error)]",
    badgeBg:
      "bg-[var(--status-error)]/15 text-[var(--status-error)] border-[var(--status-error)]/30",
    label: "Unhealthy",
  },
  unavailable: {
    icon: MinusCircle,
    color: "text-[var(--text-muted)]",
    badgeBg:
      "bg-[var(--text-muted)]/15 text-[var(--text-muted)] border-[var(--text-muted)]/30",
    label: "Unavailable",
  },
} as const;
