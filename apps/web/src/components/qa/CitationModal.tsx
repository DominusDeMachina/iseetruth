import { type ReactNode } from "react";
import { RefreshCw } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { useChunkContext } from "@/hooks/useChunkContext";
import { ENTITY_COLORS } from "@/lib/entity-constants";
import type { Citation, EntityReference } from "./types";

function highlightEntities(
  text: string,
  entities: EntityReference[],
  onEntityClick: (entityName: string) => void,
): ReactNode[] {
  if (!entities.length) return [text];

  // Build a list of matches with their positions
  const matches: Array<{
    start: number;
    end: number;
    name: string;
    entity: EntityReference;
  }> = [];

  for (const entity of entities) {
    const lowerText = text.toLowerCase();
    const lowerName = entity.name.toLowerCase();
    let searchFrom = 0;
    while (searchFrom < lowerText.length) {
      const idx = lowerText.indexOf(lowerName, searchFrom);
      if (idx === -1) break;
      matches.push({
        start: idx,
        end: idx + entity.name.length,
        name: text.slice(idx, idx + entity.name.length),
        entity,
      });
      searchFrom = idx + entity.name.length;
    }
  }

  if (!matches.length) return [text];

  // Sort by position, then longest match first (to handle overlaps)
  matches.sort((a, b) => a.start - b.start || b.end - a.end);

  // Remove overlapping matches (keep first/longest)
  const filtered: typeof matches = [];
  let lastEnd = 0;
  for (const m of matches) {
    if (m.start >= lastEnd) {
      filtered.push(m);
      lastEnd = m.end;
    }
  }

  const parts: ReactNode[] = [];
  let cursor = 0;

  for (const m of filtered) {
    if (m.start > cursor) {
      parts.push(text.slice(cursor, m.start));
    }
    const color =
      ENTITY_COLORS[m.entity.type] ?? "var(--text-primary)";
    parts.push(
      <a
        key={`entity-${m.start}`}
        onClick={() => onEntityClick(m.entity.name)}
        className="cursor-pointer font-semibold hover:underline"
        style={{ color, textDecorationColor: color }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onEntityClick(m.entity.name);
          }
        }}
        aria-label={`Explore ${m.name} in graph`}
      >
        {m.name}
      </a>,
    );
    cursor = m.end;
  }

  if (cursor < text.length) {
    parts.push(text.slice(cursor));
  }

  return parts;
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {/* Header skeleton */}
      <div className="space-y-2">
        <div className="h-4 w-48 rounded bg-[var(--bg-hover)]" />
        <div className="h-3 w-24 rounded bg-[var(--bg-hover)]" />
      </div>
      {/* Context before skeleton */}
      <div className="space-y-1.5">
        <div className="h-3 w-full rounded bg-[var(--bg-hover)]" />
        <div className="h-3 w-3/4 rounded bg-[var(--bg-hover)]" />
      </div>
      {/* Passage skeleton */}
      <div className="rounded-md bg-[var(--bg-hover)] p-4 space-y-1.5">
        <div className="h-3.5 w-full rounded bg-[var(--border-subtle)]" />
        <div className="h-3.5 w-full rounded bg-[var(--border-subtle)]" />
        <div className="h-3.5 w-2/3 rounded bg-[var(--border-subtle)]" />
      </div>
      {/* Context after skeleton */}
      <div className="space-y-1.5">
        <div className="h-3 w-full rounded bg-[var(--bg-hover)]" />
        <div className="h-3 w-1/2 rounded bg-[var(--bg-hover)]" />
      </div>
      {/* Footer skeleton */}
      <div className="h-3 w-32 rounded bg-[var(--bg-hover)]" />
    </div>
  );
}

interface CitationModalProps {
  citation: Citation | null;
  investigationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEntityClick: (entityName: string) => void;
  entities?: EntityReference[];
}

export function CitationModal({
  citation,
  investigationId,
  open,
  onOpenChange,
  onEntityClick,
  entities = [],
}: CitationModalProps) {
  const chunkId = citation?.chunk_id ?? null;
  const { data, isLoading, isError, refetch } = useChunkContext(
    investigationId,
    chunkId,
  );

  const pageLabel = data
    ? data.page_start === data.page_end
      ? `Page ${data.page_start}`
      : `Pages ${data.page_start}–${data.page_end}`
    : null;

  const ariaLabel = citation
    ? `Source citation from ${citation.document_filename}, page ${citation.page_start}`
    : "Source citation";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl bg-[var(--bg-elevated)]"
        aria-label={ariaLabel}
      >
        <DialogHeader>
          <DialogTitle className="text-[var(--text-primary)]">
            Citation — {citation?.document_filename ?? "Unknown"}
          </DialogTitle>
          <DialogDescription className="text-[var(--text-secondary)]">
            {isLoading ? "Loading..." : pageLabel}
          </DialogDescription>
        </DialogHeader>

        {isLoading && <LoadingSkeleton />}

        {isError && (
          <div className="flex flex-col items-center gap-3 py-8">
            <p className="text-sm text-[var(--status-error)]">
              Failed to load source passage. Please try again.
            </p>
            <button
              onClick={() => refetch()}
              className="flex items-center gap-1.5 rounded px-3 py-1.5 text-sm text-[var(--text-primary)] bg-[var(--bg-hover)] hover:bg-[var(--border-subtle)] transition-colors"
            >
              <RefreshCw className="size-3.5" />
              Retry
            </button>
          </div>
        )}

        {data && !isLoading && !isError && (
          <>
            <div className="max-h-[60vh] overflow-y-auto space-y-0">
              {/* Context before */}
              {data.context_before && (
                <div
                  className="px-4 py-3 text-[var(--text-muted)] border-b border-[var(--border-subtle)]"
                  style={{
                    fontFamily: "var(--font-serif)",
                    fontSize: "15px",
                    lineHeight: "1.8",
                  }}
                >
                  {data.context_before}
                </div>
              )}

              {/* Highlighted passage */}
              <div
                className="px-4 py-3 bg-[var(--bg-hover)]"
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: "15px",
                  lineHeight: "1.8",
                }}
              >
                <mark className="bg-transparent text-[var(--text-primary)]">
                  {highlightEntities(data.text, entities, onEntityClick)}
                </mark>
              </div>

              {/* Context after */}
              {data.context_after && (
                <div
                  className="px-4 py-3 text-[var(--text-muted)] border-t border-[var(--border-subtle)]"
                  style={{
                    fontFamily: "var(--font-serif)",
                    fontSize: "15px",
                    lineHeight: "1.8",
                  }}
                >
                  {data.context_after}
                </div>
              )}
            </div>

            <DialogFooter className="justify-start">
              <span className="text-xs text-[var(--text-secondary)]">
                Chunk {data.sequence_number + 1} of {data.total_chunks}
              </span>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
