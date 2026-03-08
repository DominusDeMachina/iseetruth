import { AlertTriangle } from "lucide-react";
import type { DocumentResponse } from "@/hooks/useDocuments";

interface ProcessingDashboardProps {
  documents: DocumentResponse[];
  investigationName: string;
  isConnected: boolean;
  connectionError: boolean;
}

export function ProcessingDashboard({
  documents,
  investigationName,
  isConnected,
  connectionError,
}: ProcessingDashboardProps) {
  const total = documents.length;
  const complete = documents.filter((d) => d.status === "complete").length;
  const failed = documents.filter((d) => d.status === "failed").length;
  const remaining = total - complete - failed;
  const hasProcessing = documents.some(
    (d) => d.status === "queued" || d.status === "extracting_text",
  );

  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-medium text-[var(--text-primary)]">
              Processing: {investigationName}
            </h3>
            {isConnected && hasProcessing && (
              <span className="inline-flex items-center gap-1 rounded-full bg-[var(--status-success)]/15 px-2 py-0.5 text-xs font-medium text-[var(--status-success)]">
                <span className="size-1.5 animate-pulse rounded-full bg-[var(--status-success)]" />
                Live
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-[var(--text-muted)]">
            {total} documents &middot; {complete} complete &middot; {failed}{" "}
            failed &middot; {remaining} remaining
          </p>
        </div>

        {total > 0 && (
          <div className="flex h-2 w-32 shrink-0 overflow-hidden rounded-full bg-[var(--bg-hover)]">
            {complete > 0 && (
              <div
                className="bg-[var(--status-success)]"
                style={{ width: `${(complete / total) * 100}%` }}
              />
            )}
            {failed > 0 && (
              <div
                className="bg-[var(--status-error)]"
                style={{ width: `${(failed / total) * 100}%` }}
              />
            )}
          </div>
        )}
      </div>

      {connectionError && (
        <div className="mt-3 flex items-center gap-2 rounded-md bg-[var(--status-warning)]/10 px-3 py-2 text-xs text-[var(--status-warning)]">
          <AlertTriangle className="size-3.5 shrink-0" />
          Live updates unavailable — showing cached status. Refresh to update.
        </div>
      )}
    </div>
  );
}
