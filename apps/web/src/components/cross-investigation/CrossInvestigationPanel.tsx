import { useEffect } from "react";
import { X, RefreshCw, Link2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCrossInvestigation } from "@/hooks/useCrossInvestigation";
import { CrossInvestigationMatchCard } from "./CrossInvestigationMatchCard";

interface CrossInvestigationPanelProps {
  investigationId: string;
  onClose: () => void;
  onNavigateToInvestigation?: (investigationId: string) => void;
}

export function CrossInvestigationPanel({
  investigationId,
  onClose,
  onNavigateToInvestigation,
}: CrossInvestigationPanelProps) {
  const { data, isLoading, isError, refetch } =
    useCrossInvestigation(investigationId);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-label="Cross-Investigation Links"
      className="absolute right-0 top-0 z-50 flex h-full w-80 flex-col border-l border-[var(--border-subtle)] bg-[var(--bg-secondary)] shadow-lg animate-in slide-in-from-right duration-200"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3">
        <div className="flex items-center gap-2">
          <Link2 className="size-4 text-[var(--text-secondary)]" />
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            Cross-Investigation Links
          </h2>
        </div>
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={onClose}
          aria-label="Close panel"
        >
          <X className="size-4" />
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {isLoading && <LoadingSkeleton />}

        {isError && (
          <div className="flex flex-col items-center gap-3 py-8 text-center">
            <p className="text-sm text-[var(--text-secondary)]">
              Unable to load cross-investigation matches.
            </p>
            <Button variant="ghost" size="sm" onClick={() => refetch()}>
              <RefreshCw className="mr-1.5 size-3" />
              Retry
            </Button>
          </div>
        )}

        {data && data.total_matches === 0 && (
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--text-secondary)]">
              No matching entities found in other investigations.
            </p>
            <p className="mt-2 text-xs text-[var(--text-muted)]">
              Cross-investigation matching requires two or more investigations
              with overlapping entities. Create another investigation to
              discover shared entities.
            </p>
          </div>
        )}

        {data && data.total_matches > 0 && (
          <div className="space-y-3">
            <p className="text-xs text-[var(--text-muted)]">
              {data.total_matches} entit{data.total_matches !== 1 ? "ies" : "y"} found in other investigations
            </p>
            {data.matches.map((match) => (
              <CrossInvestigationMatchCard
                key={`${match.entity_name}-${match.entity_type}`}
                match={match}
                onNavigateToInvestigation={onNavigateToInvestigation}
              />
            ))}
            <p className="text-[10px] text-[var(--text-muted)]">
              Query: {data.query_duration_ms.toFixed(0)}ms
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-14 animate-pulse rounded-md bg-[var(--bg-elevated)]"
        />
      ))}
    </div>
  );
}
