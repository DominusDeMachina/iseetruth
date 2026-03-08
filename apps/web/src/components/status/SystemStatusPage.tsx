import { AlertTriangle, RefreshCw } from "lucide-react";
import { useHealthStatus } from "@/hooks/useHealthStatus";
import { ServiceStatusCard } from "./ServiceStatusCard";
import { OllamaStatusCard } from "./OllamaStatusCard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const overallStatusConfig = {
  healthy: {
    label: "All Systems Operational",
    color: "text-[var(--status-success)]",
    badgeBg:
      "bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/30",
  },
  degraded: {
    label: "System Degraded",
    color: "text-[var(--status-warning)]",
    badgeBg:
      "bg-[var(--status-warning)]/15 text-[var(--status-warning)] border-[var(--status-warning)]/30",
  },
  unhealthy: {
    label: "System Unhealthy",
    color: "text-[var(--status-error)]",
    badgeBg:
      "bg-[var(--status-error)]/15 text-[var(--status-error)] border-[var(--status-error)]/30",
  },
} as const;

function StatusSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="h-8 w-48 animate-pulse rounded bg-[var(--bg-hover)]" />
        <div className="h-5 w-32 animate-pulse rounded bg-[var(--bg-hover)]" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-24 animate-pulse rounded-lg bg-[var(--bg-elevated)]"
          />
        ))}
        <div className="h-36 animate-pulse rounded-lg bg-[var(--bg-elevated)] md:col-span-2" />
      </div>
    </div>
  );
}

function ErrorState() {
  return (
    <Card className="bg-[var(--bg-elevated)] border-[var(--status-error)]/30">
      <CardContent className="flex flex-col items-center gap-3 py-8">
        <AlertTriangle className="h-10 w-10 text-[var(--status-error)]" />
        <h3 className="text-lg font-medium text-[var(--text-primary)]">
          Backend Unreachable
        </h3>
        <p className="text-sm text-[var(--text-secondary)] text-center max-w-md">
          Unable to connect to the API server. Please verify the backend is
          running and try again. Auto-retry in 30 seconds.
        </p>
      </CardContent>
    </Card>
  );
}

export function SystemStatusPage() {
  const { data, isLoading, isError } = useHealthStatus();

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-semibold text-[var(--text-primary)] mb-6">
          System Status
        </h2>
        <StatusSkeleton />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-semibold text-[var(--text-primary)] mb-6">
          System Status
        </h2>
        <ErrorState />
      </div>
    );
  }

  const overallConfig =
    overallStatusConfig[
      data.status as keyof typeof overallStatusConfig
    ] ?? overallStatusConfig.unhealthy;

  const nonOllamaServices = Object.entries(data.services).filter(
    ([name]) => name !== "ollama",
  );
  const ollamaService = data.services.ollama;

  const timestamp = new Date(data.timestamp).toLocaleTimeString();

  return (
    <div className="max-w-3xl mx-auto">
      <h2 className="text-2xl font-semibold text-[var(--text-primary)] mb-6">
        System Status
      </h2>

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Badge variant="outline" className={cn("text-sm", overallConfig.badgeBg)}>
            {overallConfig.label}
          </Badge>
          <span className="flex items-center gap-1 text-xs text-[var(--text-muted)]">
            <RefreshCw className="h-3 w-3" />
            Auto-refresh: 30s
          </span>
        </div>
        <span className="text-xs text-[var(--text-secondary)]">
          Last updated: {timestamp}
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {nonOllamaServices.map(([name, service]) => (
          <ServiceStatusCard key={name} name={name} service={service} />
        ))}
        {ollamaService && <OllamaStatusCard service={ollamaService} />}
      </div>

      {data.warnings.length > 0 && (
        <div className="mt-6 space-y-2">
          <h3 className="text-sm font-medium text-[var(--status-warning)]">
            Warnings
          </h3>
          {data.warnings.map((warning, i) => (
            <div
              key={i}
              className="flex items-center gap-2 rounded-md bg-[var(--status-warning)]/10 px-3 py-2 text-sm text-[var(--status-warning)]"
            >
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {warning}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
