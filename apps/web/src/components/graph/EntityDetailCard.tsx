import { useState, useEffect, useRef } from "react";
import { X, FileText, MessageSquare, ChevronDown, ChevronUp, Pencil, Link } from "lucide-react";
import { useEntityDetail } from "@/hooks/useEntityDetail";
import { ENTITY_COLORS } from "@/lib/entity-constants";
import { EditEntityDialog } from "./EditEntityDialog";
import { AddRelationshipDialog } from "./AddRelationshipDialog";

function confidenceLabel(score: number): string {
  if (score >= 0.8) return "High confidence";
  if (score >= 0.5) return "Medium confidence";
  return "Low confidence";
}

const TRUNCATE_LIMIT = 5;

interface EntityDetailCardProps {
  entityId: string;
  investigationId: string;
  position: { x: number; y: number };
  onClose: () => void;
  onNavigateToEntity: (entityId: string) => void;
  onAskAboutEntity: (entityName: string) => void;
}

export function EntityDetailCard({
  entityId,
  investigationId,
  position,
  onClose,
  onNavigateToEntity,
  onAskAboutEntity,
}: EntityDetailCardProps) {
  const { data, isLoading, isError, refetch } = useEntityDetail(
    investigationId,
    entityId,
  );
  const [expanded, setExpanded] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [addRelDialogOpen, setAddRelDialogOpen] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  // Close on Escape (suppressed when edit dialog is open)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !editDialogOpen && !addRelDialogOpen) onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, editDialogOpen, addRelDialogOpen]);

  // Compute clamped position to keep card within parent container
  const [clampedPos, setClampedPos] = useState(position);
  useEffect(() => {
    const card = cardRef.current;
    const container = card?.parentElement;
    if (!card || !container) {
      setClampedPos(position);
      return;
    }
    const containerRect = container.getBoundingClientRect();
    const cardW = card.offsetWidth || 320;
    const cardH = card.offsetHeight || 380;
    const padding = 8;

    let x = position.x + 20; // default: right of node
    let y = position.y;

    // Flip left if overflow right
    if (x + cardW > containerRect.width - padding) {
      x = position.x - cardW - 20;
    }
    // Clamp horizontal
    x = Math.max(padding, Math.min(x, containerRect.width - cardW - padding));
    // Clamp vertical
    y = Math.max(padding, Math.min(y, containerRect.height - cardH - padding));

    setClampedPos({ x, y });
  }, [position]);

  const ariaLabel = data ? `Details for ${data.name}` : "Entity details";

  // Reduced motion check
  const reducedMotion =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (isLoading) {
    return (
      <div
        ref={cardRef}
        role="dialog"
        aria-label="Loading entity details"
        className="absolute z-50 min-w-[280px] max-w-[360px] rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] shadow-lg"
        style={{ left: clampedPos.x, top: clampedPos.y }}
      >
        <div className="animate-pulse p-3 space-y-3">
          <div className="flex items-center justify-between">
            <div className="h-5 w-32 rounded bg-[var(--bg-hover)]" />
            <div className="h-4 w-4 rounded bg-[var(--bg-hover)]" />
          </div>
          <div className="h-3 w-24 rounded bg-[var(--bg-hover)]" />
          <div className="space-y-2 pt-2">
            <div className="h-3 w-full rounded bg-[var(--bg-hover)]" />
            <div className="h-3 w-3/4 rounded bg-[var(--bg-hover)]" />
            <div className="h-3 w-5/6 rounded bg-[var(--bg-hover)]" />
          </div>
          <div className="space-y-2 pt-2">
            <div className="h-3 w-full rounded bg-[var(--bg-hover)]" />
            <div className="h-3 w-2/3 rounded bg-[var(--bg-hover)]" />
          </div>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div
        ref={cardRef}
        role="dialog"
        aria-label="Entity detail error"
        className="absolute z-50 min-w-[280px] max-w-[360px] rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-4 shadow-lg"
        style={{ left: clampedPos.x, top: clampedPos.y }}
      >
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm text-[var(--status-error)]">
            Failed to load entity details
          </p>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          >
            <X className="size-4" />
          </button>
        </div>
        <button
          onClick={() => refetch()}
          className="rounded bg-[var(--bg-hover)] px-3 py-1 text-xs text-[var(--text-primary)] hover:bg-[var(--border-subtle)] transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  const relationships = data.relationships ?? [];
  const sources = data.sources ?? [];
  const visibleRels = expanded
    ? relationships
    : relationships.slice(0, TRUNCATE_LIMIT);
  const hiddenCount = relationships.length - TRUNCATE_LIMIT;
  const dotColor = ENTITY_COLORS[data.type] ?? "#a89f90";

  return (
    <div
      ref={cardRef}
      role="dialog"
      aria-label={ariaLabel}
      className={`absolute z-50 min-w-[280px] max-w-[360px] max-h-[400px] overflow-y-auto rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] shadow-lg ${
        reducedMotion ? "" : "animate-in fade-in zoom-in-95 duration-150"
      }`}
      style={{ left: clampedPos.x, top: clampedPos.y }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 p-3 pb-1">
        <div className="min-w-0">
          <p className="font-semibold text-sm text-[var(--text-primary)] truncate">
            {data.name}
          </p>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span
              className="inline-block size-2 rounded-full shrink-0"
              style={{ backgroundColor: dotColor }}
            />
            <span className="text-xs text-[var(--text-secondary)]">
              {data.type}
            </span>
            <span className="text-xs text-[var(--text-muted)]">·</span>
            <span className="text-xs text-[var(--text-secondary)]">
              {confidenceLabel(data.confidence_score)}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0 mt-0.5">
          <button
            onClick={() => setAddRelDialogOpen(true)}
            aria-label="Add relationship"
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          >
            <Link className="size-3.5" />
          </button>
          <button
            onClick={() => setEditDialogOpen(true)}
            aria-label="Edit entity"
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          >
            <Pencil className="size-3.5" />
          </button>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          >
            <X className="size-4" />
          </button>
        </div>
      </div>

      {/* Relationships */}
      <div className="border-t border-[var(--border-subtle)] px-3 py-2">
        <p className="text-xs font-medium text-[var(--text-secondary)] mb-1.5">
          Relationships ({relationships.length})
        </p>
        {relationships.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">No relationships</p>
        ) : (
          <ul className="space-y-1">
            {visibleRels.map((rel, i) => (
              <li key={`${rel.relation_type}-${rel.target_id}-${i}`} className="flex items-baseline gap-1 text-xs">
                <span className="text-[var(--text-muted)] shrink-0">→</span>
                <span className="text-[var(--text-secondary)] uppercase shrink-0">
                  {rel.relation_type}
                </span>
                {rel.target_id ? (
                  <button
                    onClick={() => onNavigateToEntity(rel.target_id!)}
                    className="text-[var(--text-primary)] hover:underline truncate text-left"
                    tabIndex={0}
                  >
                    {rel.target_name}
                  </button>
                ) : (
                  <span className="text-[var(--text-primary)] truncate">
                    {rel.target_name}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
        {hiddenCount > 0 && !expanded && (
          <button
            onClick={() => setExpanded(true)}
            className="mt-1 flex items-center gap-1 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          >
            Show {hiddenCount} more
            <ChevronDown className="size-3" />
          </button>
        )}
        {expanded && relationships.length > TRUNCATE_LIMIT && (
          <button
            onClick={() => setExpanded(false)}
            className="mt-1 flex items-center gap-1 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          >
            Show less
            <ChevronUp className="size-3" />
          </button>
        )}
      </div>

      {/* Source Documents */}
      <div className="border-t border-[var(--border-subtle)] px-3 py-2">
        <p className="text-xs font-medium text-[var(--text-secondary)] mb-1.5">
          Source Documents ({sources.length})
        </p>
        {sources.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">No sources</p>
        ) : (
          <ul className="space-y-1">
            {sources.map((src) => (
              <li key={src.chunk_id} className="flex items-center gap-1.5 text-xs">
                <FileText className="size-3 shrink-0 text-[var(--text-muted)]" />
                <span className="text-[var(--text-primary)] truncate">
                  {src.document_filename}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Action */}
      <div className="border-t border-[var(--border-subtle)] p-3 pt-2">
        <button
          onClick={() => onAskAboutEntity(data.name)}
          className="flex items-center gap-1.5 rounded bg-[var(--bg-hover)] px-3 py-1.5 text-xs text-[var(--text-primary)] hover:bg-[var(--border-subtle)] transition-colors w-full justify-center"
        >
          <MessageSquare className="size-3" />
          Ask about this entity
        </button>
      </div>

      {/* Edit dialog */}
      <EditEntityDialog
        investigationId={investigationId}
        entityId={entityId}
        entityName={data.name}
        entityType={data.type}
        sourceAnnotation={data.source_annotation}
        aliases={data.aliases}
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
      />

      {/* Add Relationship dialog */}
      <AddRelationshipDialog
        investigationId={investigationId}
        open={addRelDialogOpen}
        onOpenChange={setAddRelDialogOpen}
        preSelectedSourceId={entityId}
      />
    </div>
  );
}
