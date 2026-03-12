import type { EntityTypeSummary } from "@/hooks/useEntities";

interface EntitySummaryBarProps {
  summary: EntityTypeSummary;
}

export function EntitySummaryBar({ summary }: EntitySummaryBarProps) {
  if (summary.total === 0) return null;

  return (
    <div className="flex items-center gap-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-4 py-2">
      <span className="text-sm font-medium text-[var(--text-primary)]">
        {summary.total} entities
      </span>
      <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
        <span className="flex items-center gap-1">
          <span className="size-2 rounded-full bg-[var(--entity-person)]" />
          {summary.people} people
        </span>
        <span className="flex items-center gap-1">
          <span className="size-2 rounded-full bg-[var(--entity-org)]" />
          {summary.organizations} orgs
        </span>
        <span className="flex items-center gap-1">
          <span className="size-2 rounded-full bg-[var(--entity-location)]" />
          {summary.locations} locations
        </span>
      </div>
    </div>
  );
}
