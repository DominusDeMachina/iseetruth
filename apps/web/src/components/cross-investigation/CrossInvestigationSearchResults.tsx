import { Badge } from "@/components/ui/badge";
import { ENTITY_COLORS } from "@/lib/entity-constants";
import type { CrossInvestigationSearchResult } from "@/hooks/useCrossInvestigation";

interface CrossInvestigationSearchResultsProps {
  results: CrossInvestigationSearchResult[];
  query: string;
  onOpenEntity?: (entityName: string, entityType: string) => void;
  onOpenInInvestigation?: (investigationId: string, entityName: string) => void;
}

export function CrossInvestigationSearchResults({
  results,
  query,
  onOpenEntity,
  onOpenInInvestigation,
}: CrossInvestigationSearchResultsProps) {
  if (results.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-[var(--text-secondary)]">
        No entities matching &ldquo;{query}&rdquo; found across investigations.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-[var(--text-muted)]">
        {results.length} result{results.length !== 1 ? "s" : ""} for &ldquo;
        {query}&rdquo;
      </p>
      {results.map((result) => {
        const typeLabel =
          result.entity_type.charAt(0).toUpperCase() +
          result.entity_type.slice(1);
        const dotColor = ENTITY_COLORS[typeLabel] ?? "var(--text-secondary)";

        return (
          <div
            key={`${result.entity_name}-${result.entity_type}`}
            className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3"
          >
            <div className="flex items-center gap-2">
              <span
                className="size-2 shrink-0 rounded-full"
                style={{ backgroundColor: dotColor }}
              />
              {onOpenEntity ? (
                <button
                  className="min-w-0 flex-1 truncate text-left text-sm font-medium text-[var(--text-primary)] hover:underline"
                  onClick={() =>
                    onOpenEntity(result.entity_name, result.entity_type)
                  }
                >
                  {result.entity_name}
                </button>
              ) : (
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-[var(--text-primary)]">
                  {result.entity_name}
                </span>
              )}
              <Badge
                variant="outline"
                className="shrink-0 text-[10px]"
                style={{ borderColor: dotColor, color: dotColor }}
              >
                {typeLabel}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              Found in {result.investigation_count} investigation
              {result.investigation_count !== 1 ? "s" : ""}
            </p>
            <div className="mt-1 space-y-0.5">
              {result.investigations.map((inv) => (
                <div
                  key={inv.investigation_id}
                  className="flex items-center justify-between text-xs"
                >
                  {onOpenInInvestigation ? (
                    <button
                      className="truncate text-left text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:underline"
                      onClick={() =>
                        onOpenInInvestigation(
                          inv.investigation_id,
                          result.entity_name,
                        )
                      }
                    >
                      {inv.investigation_name}
                    </button>
                  ) : (
                    <span className="truncate text-[var(--text-secondary)]">
                      {inv.investigation_name}
                    </span>
                  )}
                  <span className="shrink-0 text-[var(--text-muted)]">
                    {inv.relationship_count} rel
                    {inv.relationship_count !== 1 ? "s" : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
