import { AlertTriangle } from "lucide-react";
import type { DocumentResponse } from "@/hooks/useDocuments";
import type { DiscoveredEntity } from "@/hooks/useSSE";
import type { EntityListItem } from "@/hooks/useEntities";
import { ACTIVE_STATUSES } from "@/lib/document-constants";
import { ENTITY_COLORS } from "@/lib/entity-constants";

interface ProcessingDashboardProps {
  documents: DocumentResponse[];
  investigationName: string;
  isConnected: boolean;
  connectionError: boolean;
  discoveredEntities?: DiscoveredEntity[];
  /** Already-extracted entities from API (survives page reload). */
  extractedEntities?: EntityListItem[];
}

export function ProcessingDashboard({
  documents,
  investigationName,
  isConnected,
  connectionError,
  discoveredEntities = [],
  extractedEntities = [],
}: ProcessingDashboardProps) {
  const total = documents.length;
  const complete = documents.filter((d) => d.status === "complete").length;
  const failed = documents.filter((d) => d.status === "failed").length;
  const remaining = documents.filter((d) => ACTIVE_STATUSES.has(d.status)).length;
  const hasProcessing = remaining > 0;

  const pdfCount = documents.filter((d) => d.document_type === "pdf").length;
  const imageCount = documents.filter((d) => d.document_type === "image").length;
  const webCount = documents.filter((d) => d.document_type === "web").length;

  // Merge API entities with SSE discoveries (SSE may have entities not yet returned by API)
  const apiNames = new Set(extractedEntities.map((e) => e.name));
  const newFromSSE = discoveredEntities.filter((e) => !apiNames.has(e.entityName));

  const entityTags: { name: string; type: string }[] = [
    ...extractedEntities.map((e) => ({ name: e.name, type: e.type })),
    ...newFromSSE.map((e) => ({ name: e.entityName, type: e.entityType })),
  ];

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
            {total} document{total !== 1 ? "s" : ""}
            {(pdfCount > 0 || imageCount > 0 || webCount > 0) && (
              <> ({[
                pdfCount > 0 ? `${pdfCount} PDF${pdfCount !== 1 ? "s" : ""}` : null,
                imageCount > 0 ? `${imageCount} image${imageCount !== 1 ? "s" : ""}` : null,
                webCount > 0 ? `${webCount} web` : null,
              ].filter(Boolean).join(", ")})</>
            )}
            {" "}&middot; {complete} complete &middot; {failed}{" "}
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

      {entityTags.length > 0 && (
        <div className="mt-3">
          <h4 className="text-xs font-medium text-[var(--text-muted)] mb-1.5">
            Discovered entities ({entityTags.length})
          </h4>
          <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
            {entityTags.slice(-20).reverse().map((entity, i) => {
              const color =
                entity.type === "person"
                  ? ENTITY_COLORS.Person
                  : entity.type === "organization"
                    ? ENTITY_COLORS.Organization
                    : ENTITY_COLORS.Location;
              return (
                <span
                  key={`${entity.name}-${i}`}
                  className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs bg-[var(--bg-hover)] text-[var(--text-secondary)]"
                >
                  <span
                    className="size-1.5 shrink-0 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  {entity.name}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
