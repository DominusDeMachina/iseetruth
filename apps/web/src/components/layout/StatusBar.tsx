import { CheckCircle2, AlertTriangle, XCircle, Loader2 } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { useHealthStatus } from "@/hooks/useHealthStatus";

export function StatusBar() {
  const { data, isLoading, isError } = useHealthStatus();

  let icon: React.ReactNode;
  let label: string;
  let colorClass: string;

  if (isLoading) {
    icon = <Loader2 className="h-3.5 w-3.5 animate-spin" />;
    label = "Checking services...";
    colorClass = "text-[var(--text-muted)]";
  } else if (isError || !data) {
    icon = <XCircle className="h-3.5 w-3.5" />;
    label = "Backend unreachable";
    colorClass = "text-[var(--status-error)]";
  } else if (data.status === "healthy") {
    icon = <CheckCircle2 className="h-3.5 w-3.5" />;
    label = "All systems operational";
    colorClass = "text-[var(--status-success)]";
  } else if (data.status === "degraded") {
    icon = <AlertTriangle className="h-3.5 w-3.5" />;
    // Build specific degradation label
    const downServices: string[] = [];
    if (data.services) {
      for (const [name, svc] of Object.entries(data.services)) {
        if (svc.status !== "healthy") downServices.push(name);
      }
    }
    if (downServices.includes("qdrant")) {
      label = "Reduced search capability";
    } else if (downServices.length > 0) {
      label = `System degraded — ${downServices.join(", ")} unavailable`;
    } else {
      label = "System degraded";
    }
    colorClass = "text-[var(--status-warning)]";
  } else {
    icon = <XCircle className="h-3.5 w-3.5" />;
    label = "System unhealthy";
    colorClass = "text-[var(--status-error)]";
  }

  return (
    <Link
      to="/status"
      className="flex items-center justify-between border-t border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-6 py-2 transition-colors hover:bg-[var(--bg-hover)]"
    >
      <div className={`flex items-center gap-2 text-xs ${colorClass}`}>
        {icon}
        <span>{label}</span>
      </div>
      <span className="text-xs text-[var(--text-muted)]">/status</span>
    </Link>
  );
}
