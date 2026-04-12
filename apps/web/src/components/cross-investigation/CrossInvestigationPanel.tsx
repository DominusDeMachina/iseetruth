import { useEffect, useState, useCallback, useRef } from "react";
import { X, RefreshCw, Link2, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  useCrossInvestigation,
  useCrossInvestigationSearch,
} from "@/hooks/useCrossInvestigation";
import { CrossInvestigationMatchCard } from "./CrossInvestigationMatchCard";
import { CrossInvestigationEntityDetail } from "./CrossInvestigationEntityDetail";
import { CrossInvestigationSearchResults } from "./CrossInvestigationSearchResults";

type PanelView =
  | { type: "matches" }
  | { type: "detail"; entityName: string; entityType: string }
  | { type: "search"; query: string };

interface CrossInvestigationPanelProps {
  investigationId: string;
  onClose: () => void;
  onNavigateToInvestigation?: (investigationId: string, entityName?: string) => void;
}

export function CrossInvestigationPanel({
  investigationId,
  onClose,
  onNavigateToInvestigation,
}: CrossInvestigationPanelProps) {
  const { data, isLoading, isError, refetch } =
    useCrossInvestigation(investigationId);

  const [view, setView] = useState<PanelView>({ type: "matches" });
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  const {
    data: searchData,
    isLoading: isSearchLoading,
  } = useCrossInvestigationSearch(
    debouncedSearch,
    view.type === "search" && debouncedSearch.length >= 2,
  );

  // Debounce search input
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(searchInput);
      if (searchInput.length >= 2) {
        setView({ type: "search", query: searchInput });
      } else if (searchInput.length === 0) {
        setView({ type: "matches" });
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchInput]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (view.type !== "matches") {
          setView({ type: "matches" });
          setSearchInput("");
        } else {
          onClose();
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose, view.type]);

  const handleOpenEntity = useCallback(
    (entityName: string, entityType: string) => {
      setView({ type: "detail", entityName, entityType });
      setSearchInput("");
    },
    [],
  );

  const handleOpenInInvestigation = useCallback(
    (targetInvestigationId: string, entityName: string) => {
      onNavigateToInvestigation?.(targetInvestigationId, entityName);
    },
    [onNavigateToInvestigation],
  );

  // Entity detail view
  if (view.type === "detail") {
    return (
      <div
        role="dialog"
        aria-label="Cross-Investigation Entity Detail"
        className="absolute right-0 top-0 z-50 flex h-full w-80 flex-col border-l border-[var(--border-subtle)] bg-[var(--bg-secondary)] shadow-lg animate-in slide-in-from-right duration-200"
      >
        <CrossInvestigationEntityDetail
          entityName={view.entityName}
          entityType={view.entityType}
          onBack={() => setView({ type: "matches" })}
          onOpenInInvestigation={handleOpenInInvestigation}
        />
      </div>
    );
  }

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

      {/* Search input */}
      <div className="border-b border-[var(--border-subtle)] px-4 py-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search across investigations..."
            className="w-full rounded-md border border-[var(--border-subtle)] bg-[var(--bg-primary)] py-1.5 pl-8 pr-8 text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-[var(--status-info)]"
            aria-label="Search across investigations"
          />
          {searchInput && (
            <button
              onClick={() => {
                setSearchInput("");
                setView({ type: "matches" });
              }}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              aria-label="Clear search"
            >
              <X className="size-3" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {/* Search results view */}
        {view.type === "search" && (
          <>
            {isSearchLoading && <LoadingSkeleton />}
            {searchData && (
              <CrossInvestigationSearchResults
                results={searchData.results}
                query={view.query}
                onOpenEntity={handleOpenEntity}
                onOpenInInvestigation={handleOpenInInvestigation}
              />
            )}
          </>
        )}

        {/* Default matches view */}
        {view.type === "matches" && (
          <>
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
                  Cross-investigation matching requires two or more
                  investigations with overlapping entities. Create another
                  investigation to discover shared entities.
                </p>
              </div>
            )}

            {data && data.total_matches > 0 && (
              <div className="space-y-3">
                <p className="text-xs text-[var(--text-muted)]">
                  {data.total_matches} entit
                  {data.total_matches !== 1 ? "ies" : "y"} found in other
                  investigations
                </p>
                {data.matches.map((match) => (
                  <CrossInvestigationMatchCard
                    key={`${match.entity_name}-${match.entity_type}`}
                    match={match}
                    investigationId={investigationId}
                    onNavigateToInvestigation={(invId) =>
                      handleOpenInInvestigation(invId, match.entity_name)
                    }
                    onOpenEntityDetail={handleOpenEntity}
                  />
                ))}
                <p className="text-[10px] text-[var(--text-muted)]">
                  Query: {data.query_duration_ms.toFixed(0)}ms
                </p>
              </div>
            )}
          </>
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
