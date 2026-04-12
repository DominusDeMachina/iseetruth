import { ChevronDown, ChevronUp, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ENTITY_COLORS } from "@/lib/entity-constants";
import type { DocumentResponse } from "@/hooks/useDocuments";

interface GraphFilterPanelProps {
  entityTypes: string[];
  onEntityTypesChange: (types: string[]) => void;
  documentId: string | undefined;
  onDocumentIdChange: (id: string | undefined) => void;
  documents: DocumentResponse[];
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

const ENTITY_TYPE_CHIPS = [
  { value: "person", label: "People", colorKey: "Person" },
  { value: "organization", label: "Orgs", colorKey: "Organization" },
  { value: "location", label: "Locations", colorKey: "Location" },
] as const;

function getActiveFilterCount(
  entityTypes: string[],
  documentId: string | undefined,
): number {
  let count = 0;
  // entity types filter is active if not all types are shown (non-empty means subset)
  if (entityTypes.length > 0) count++;
  if (documentId) count++;
  return count;
}

function getFilterSummary(
  entityTypes: string[],
  documentId: string | undefined,
  documents: DocumentResponse[],
): string {
  const parts: string[] = [];
  if (entityTypes.length > 0) {
    const labels = entityTypes.map(
      (t) => ENTITY_TYPE_CHIPS.find((c) => c.value === t)?.label ?? t,
    );
    parts.push(labels.join(", "));
  }
  if (documentId) {
    const doc = documents.find((d) => d.id === documentId);
    parts.push(doc?.filename ?? "1 document");
  }
  return parts.join(" · ") || "No filters";
}

export function GraphFilterPanel({
  entityTypes,
  onEntityTypesChange,
  documentId,
  onDocumentIdChange,
  documents,
  isCollapsed,
  onToggleCollapse,
}: GraphFilterPanelProps) {
  const activeCount = getActiveFilterCount(entityTypes, documentId);
  const hasActiveFilters = activeCount > 0;

  const handleToggleType = (type: string) => {
    if (entityTypes.length === 0) {
      // Currently showing all — toggling one means "show only NOT this one"
      // Actually: empty array = all shown. Clicking means "deactivate this type"
      // = show all except this one
      const allTypes = ENTITY_TYPE_CHIPS.map((c) => c.value);
      const remaining = allTypes.filter((t) => t !== type);
      onEntityTypesChange(remaining);
    } else if (entityTypes.includes(type)) {
      // Remove this type from active list
      const remaining = entityTypes.filter((t) => t !== type);
      if (remaining.length === 0) {
        // Can't deactivate the last type — re-enable all
        onEntityTypesChange([]);
      } else {
        onEntityTypesChange(remaining);
      }
    } else {
      // Add this type
      const updated = [...entityTypes, type];
      // If all three types are now selected, reset to empty (= show all)
      if (updated.length === ENTITY_TYPE_CHIPS.length) {
        onEntityTypesChange([]);
      } else {
        onEntityTypesChange(updated);
      }
    }
  };

  const isTypeActive = (type: string): boolean => {
    // Empty array means all types are active
    return entityTypes.length === 0 || entityTypes.includes(type);
  };

  const handleClearAll = () => {
    onEntityTypesChange([]);
    onDocumentIdChange(undefined);
  };

  if (isCollapsed) {
    return (
      <div
        className="absolute top-3 left-3 z-30 flex items-center gap-2 rounded-lg bg-[var(--bg-elevated)] border border-[var(--border-subtle)] shadow-lg p-2 cursor-pointer"
        role="toolbar"
        aria-label="Graph filters"
        onClick={onToggleCollapse}
      >
        <span className="text-xs text-[var(--text-secondary)]">
          {hasActiveFilters
            ? getFilterSummary(entityTypes, documentId, documents)
            : "Filters"}
        </span>
        {hasActiveFilters && (
          <span className="inline-flex items-center justify-center rounded-full bg-[var(--status-info)] text-white text-[10px] font-medium min-w-[18px] h-[18px] px-1">
            {activeCount}
          </span>
        )}
        <ChevronDown className="size-3 text-[var(--text-muted)]" />
      </div>
    );
  }

  return (
    <div
      className="absolute top-3 left-3 z-30 rounded-lg bg-[var(--bg-elevated)] border border-[var(--border-subtle)] shadow-lg p-2 flex flex-col gap-2"
      role="toolbar"
      aria-label="Graph filters"
    >
      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-[var(--text-secondary)]">
          Filters
        </span>
        <div className="flex items-center gap-1">
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={handleClearAll}
              aria-label="Clear all filters"
              title="Clear all filters"
            >
              <X />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={onToggleCollapse}
            aria-label="Collapse filters"
          >
            <ChevronUp />
          </Button>
        </div>
      </div>

      {/* Entity type chips */}
      <div className="flex items-center gap-1">
        {ENTITY_TYPE_CHIPS.map((chip) => {
          const active = isTypeActive(chip.value);
          const color = ENTITY_COLORS[chip.colorKey];
          return (
            <button
              key={chip.value}
              role="checkbox"
              aria-checked={active}
              onClick={() => handleToggleType(chip.value)}
              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium transition-colors border"
              style={
                active
                  ? {
                      backgroundColor: `${color}20`,
                      borderColor: color,
                      color: "var(--text-primary)",
                    }
                  : {
                      backgroundColor: "transparent",
                      borderColor: "var(--border-subtle)",
                      color: "var(--text-muted)",
                    }
              }
            >
              <span
                className="inline-block size-2 rounded-full"
                style={{
                  backgroundColor: active ? color : "var(--text-muted)",
                }}
              />
              {chip.label}
            </button>
          );
        })}
      </div>

      {/* Document filter dropdown */}
      {documents.length > 0 && (
        <select
          value={documentId ?? ""}
          onChange={(e) =>
            onDocumentIdChange(e.target.value || undefined)
          }
          className="w-full rounded-md border border-[var(--border-subtle)] bg-[var(--bg-primary)] px-2 py-1 text-xs text-[var(--text-primary)]"
          aria-label="Filter by document"
        >
          <option value="">All documents</option>
          {documents.map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.document_type === "web" ? "[Web] " : ""}{doc.filename}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
