import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ENTITY_COLORS } from "@/lib/entity-constants";
import type { CrossInvestigationMatch } from "@/hooks/useCrossInvestigation";

interface CrossInvestigationMatchCardProps {
  match: CrossInvestigationMatch;
  onNavigateToInvestigation?: (investigationId: string) => void;
}

export function CrossInvestigationMatchCard({
  match,
  onNavigateToInvestigation,
}: CrossInvestigationMatchCardProps) {
  const [expanded, setExpanded] = useState(false);
  const typeLabel = match.entity_type.charAt(0).toUpperCase() + match.entity_type.slice(1);
  const dotColor = ENTITY_COLORS[typeLabel] ?? "var(--text-secondary)";

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
        <span className="min-w-0 flex-1 truncate text-sm font-medium text-[var(--text-primary)]">
          {match.entity_name}
        </span>
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
            Found in {match.investigations.length} other investigation{match.investigations.length !== 1 ? "s" : ""}
          </p>
          {match.investigations.map((inv) => (
            <div
              key={inv.investigation_id}
              className="flex items-center justify-between rounded px-2 py-1 text-xs hover:bg-[var(--bg-hover)]"
            >
              {onNavigateToInvestigation ? (
                <button
                  className="truncate text-left text-[var(--text-primary)] underline decoration-[var(--border-subtle)] underline-offset-2 hover:decoration-[var(--text-primary)]"
                  onClick={() => onNavigateToInvestigation(inv.investigation_id)}
                  title={`Open ${inv.investigation_name}`}
                >
                  {inv.investigation_name}
                </button>
              ) : (
                <span className="truncate text-[var(--text-primary)]">
                  {inv.investigation_name}
                </span>
              )}
              <span className="shrink-0 text-[var(--text-muted)]">
                {inv.relationship_count} rel{inv.relationship_count !== 1 ? "s" : ""}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
