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
  } else {
    // Build service status breakdown
    const downServices: string[] = [];
    if (data.services) {
      for (const [name, svc] of Object.entries(data.services)) {
        if (svc.status !== "healthy") downServices.push(name);
      }
    }

    // Critical = core infrastructure down (postgres or redis)
    const isCritical = downServices.includes("postgres") || downServices.includes("redis");

    if (isCritical) {
      icon = <XCircle className="h-3.5 w-3.5" />;
      label = "System critical — core services down";
      colorClass = "text-[var(--status-error)]";
    } else if (downServices.includes("qdrant") && downServices.length === 1) {
      icon = <AlertTriangle className="h-3.5 w-3.5" />;
      label = "Reduced search capability";
      colorClass = "text-[var(--status-warning)]";
    } else if (downServices.length > 0) {
      icon = <AlertTriangle className="h-3.5 w-3.5" />;
      label = `System degraded — ${downServices.join(", ")} unavailable`;
      colorClass = "text-[var(--status-warning)]";
    } else {
      icon = <XCircle className="h-3.5 w-3.5" />;
      label = "System unhealthy";
      colorClass = "text-[var(--status-error)]";
    }
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
