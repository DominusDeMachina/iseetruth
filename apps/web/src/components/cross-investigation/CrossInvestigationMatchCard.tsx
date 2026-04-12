import { useState } from "react";
import { ChevronDown, ChevronRight, X as XIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ENTITY_COLORS } from "@/lib/entity-constants";
import {
  useDismissCrossMatch,
  type CrossInvestigationMatch,
} from "@/hooks/useCrossInvestigation";

interface CrossInvestigationMatchCardProps {
  match: CrossInvestigationMatch;
  investigationId?: string;
  onNavigateToInvestigation?: (investigationId: string) => void;
  onOpenEntityDetail?: (entityName: string, entityType: string) => void;
}

export function CrossInvestigationMatchCard({
  match,
  investigationId,
  onNavigateToInvestigation,
  onOpenEntityDetail,
}: CrossInvestigationMatchCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [dismissedInvIds, setDismissedInvIds] = useState<Set<string>>(
    new Set(),
  );
  const dismissMutation = useDismissCrossMatch(investigationId ?? "");
  const typeLabel =
    match.entity_type.charAt(0).toUpperCase() + match.entity_type.slice(1);
  const dotColor = ENTITY_COLORS[typeLabel] ?? "var(--text-secondary)";

  const visibleInvestigations = match.investigations.filter(
    (inv) => !dismissedInvIds.has(inv.investigation_id),
  );

  // If all investigations are dismissed, hide the entire card
  if (visibleInvestigations.length === 0) return null;

  const handleDismiss = (targetInvestigationId: string) => {
    // Optimistic update
    setDismissedInvIds((prev) => new Set(prev).add(targetInvestigationId));
    dismissMutation.mutate({
      entityName: match.entity_name,
      entityType: match.entity_type,
      targetInvestigationId,
    });
  };

  return (
    <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3">
      <button
        className="flex w-full items-center gap-2 text-left"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="size-3.5 shrink-0 text-[var(--text-muted)]" />
        ) : (
          <ChevronRight className="size-3.5 shrink-0 text-[var(--text-muted)]" />
        )}
        <span
          className="size-2 shrink-0 rounded-full"
          style={{ backgroundColor: dotColor }}
        />
        {onOpenEntityDetail ? (
          <span
            role="button"
            tabIndex={0}
            className="min-w-0 flex-1 truncate text-sm font-medium text-[var(--text-primary)] hover:underline"
            onClick={(e) => {
              e.stopPropagation();
              onOpenEntityDetail(match.entity_name, match.entity_type);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.stopPropagation();
                onOpenEntityDetail(match.entity_name, match.entity_type);
              }
            }}
          >
            {match.entity_name}
          </span>
        ) : (
          <span className="min-w-0 flex-1 truncate text-sm font-medium text-[var(--text-primary)]">
            {match.entity_name}
          </span>
        )}
        <Badge
          variant="outline"
          className="shrink-0 text-[10px]"
          style={{ borderColor: dotColor, color: dotColor }}
        >
          {typeLabel}
        </Badge>
      </button>

      {expanded && (
        <div className="mt-2 space-y-1.5 pl-6">
          <p className="text-xs text-[var(--text-muted)]">
            Found in {visibleInvestigations.length} other investigation
            {visibleInvestigations.length !== 1 ? "s" : ""}
          </p>
          {visibleInvestigations.map((inv) => (
            <div
              key={inv.investigation_id}
              className="group flex items-center justify-between rounded px-2 py-1 text-xs hover:bg-[var(--bg-hover)]"
            >
              {onNavigateToInvestigation ? (
                <button
                  className="truncate text-left text-[var(--text-primary)] underline decoration-[var(--border-subtle)] underline-offset-2 hover:decoration-[var(--text-primary)]"
                  onClick={() =>
                    onNavigateToInvestigation(inv.investigation_id)
                  }
                  title={`Open ${inv.investigation_name}`}
                >
                  {inv.investigation_name}
                </button>
              ) : (
                <span className="truncate text-[var(--text-primary)]">
                  {inv.investigation_name}
                </span>
              )}
              <div className="flex shrink-0 items-center gap-1.5">
                <span className="text-[var(--text-muted)]">
                  {inv.relationship_count} rel
                  {inv.relationship_count !== 1 ? "s" : ""}
                </span>
                {investigationId && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDismiss(inv.investigation_id);
                    }}
                    className="hidden rounded p-0.5 text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--status-error)] group-hover:block"
                    title="Not the same entity"
                    aria-label={`Dismiss match with ${inv.investigation_name}`}
                  >
                    <XIcon className="size-3" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
