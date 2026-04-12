import { ArrowLeft, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ENTITY_COLORS } from "@/lib/entity-constants";
import { useCrossInvestigationEntityDetail } from "@/hooks/useCrossInvestigation";

interface CrossInvestigationEntityDetailProps {
  entityName: string;
  entityType: string;
  onBack: () => void;
  onOpenInInvestigation?: (investigationId: string, entityName: string) => void;
}

export function CrossInvestigationEntityDetail({
  entityName,
  entityType,
  onBack,
  onOpenInInvestigation,
}: CrossInvestigationEntityDetailProps) {
  const { data, isLoading, isError } = useCrossInvestigationEntityDetail(
    entityName,
    entityType,
  );

  const typeLabel =
    entityType.charAt(0).toUpperCase() + entityType.slice(1);
  const dotColor = ENTITY_COLORS[typeLabel] ?? "var(--text-secondary)";

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] px-4 py-3">
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={onBack}
          aria-label="Back to matches"
        >
          <ArrowLeft className="size-4" />
        </Button>
        <span
          className="size-2.5 shrink-0 rounded-full"
          style={{ backgroundColor: dotColor }}
        />
        <h2 className="min-w-0 flex-1 truncate text-sm font-semibold text-[var(--text-primary)]">
          {entityName}
        </h2>
        <Badge
          variant="outline"
          className="shrink-0 text-[10px]"
          style={{ borderColor: dotColor, color: dotColor }}
        >
          {typeLabel}
        </Badge>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {isLoading && <DetailSkeleton />}

        {isError && (
          <p className="py-4 text-center text-sm text-[var(--text-secondary)]">
            Failed to load entity details.
          </p>
        )}

        {data && data.total_investigations === 0 && (
          <p className="py-4 text-center text-sm text-[var(--text-secondary)]">
            Entity not found in any investigation.
          </p>
        )}

        {data && data.total_investigations > 0 && (
          <div className="space-y-4">
            <p className="text-xs text-[var(--text-muted)]">
              Found in {data.total_investigations} investigation
              {data.total_investigations !== 1 ? "s" : ""}
            </p>

            {data.investigations.map((inv) => (
              <div
                key={inv.investigation_id}
                className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-[var(--text-primary)]">
                    {inv.investigation_name}
                  </span>
                  {onOpenInInvestigation && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 gap-1 px-2 text-[10px]"
                      onClick={() =>
                        onOpenInInvestigation(inv.investigation_id, entityName)
                      }
                    >
                      <ExternalLink className="size-3" />
                      Open
                    </Button>
                  )}
                </div>

                {/* Relationships */}
                {inv.relationships.length > 0 && (
                  <div className="mt-2">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">
                      Relationships ({inv.relationship_count})
                    </p>
                    <ul className="mt-1 space-y-0.5">
                      {inv.relationships.map((rel, idx) => (
                        <li
                          key={`${rel.type}-${rel.target_name}-${idx}`}
                          className="text-xs text-[var(--text-secondary)]"
                        >
                          <span className="text-[var(--text-muted)]">
                            {rel.type}
                          </span>
                          {rel.target_name && (
                            <>
                              {" \u2192 "}
                              <span className="text-[var(--text-primary)]">
                                {rel.target_name}
                              </span>
                            </>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Source documents */}
                {inv.source_documents.length > 0 && (
                  <div className="mt-2">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">
                      Source Documents ({inv.source_documents.length})
                    </p>
                    <ul className="mt-1 space-y-0.5">
                      {inv.source_documents.map((doc) => (
                        <li
                          key={doc.document_id}
                          className="truncate text-xs text-[var(--text-secondary)]"
                        >
                          {doc.filename}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <p className="mt-2 text-[10px] text-[var(--text-muted)]">
                  Confidence: {(inv.confidence_score * 100).toFixed(0)}%
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2].map((i) => (
        <div
          key={i}
          className="h-24 animate-pulse rounded-md bg-[var(--bg-elevated)]"
        />
      ))}
    </div>
  );
}
