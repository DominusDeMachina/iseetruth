import { useEffect, useRef, useState } from "react";
import { X, ArrowRight } from "lucide-react";

interface EdgeData {
  id: string;
  source: string;
  target: string;
  type: string;
  confidence_score: number;
  origin?: string;
  source_annotation?: string | null;
}

interface EdgeDetailPopoverProps {
  edgeData: EdgeData;
  sourceEntityName: string;
  targetEntityName: string;
  position: { x: number; y: number };
  onClose: () => void;
  onNavigateToEntity?: (entityId: string) => void;
}

export function EdgeDetailPopover({
  edgeData,
  sourceEntityName,
  targetEntityName,
  position,
  onClose,
  onNavigateToEntity,
}: EdgeDetailPopoverProps) {
  const popoverRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  // Compute clamped position
  const [clampedPos, setClampedPos] = useState(position);
  useEffect(() => {
    const el = popoverRef.current;
    const container = el?.parentElement;
    if (!el || !container) {
      setClampedPos(position);
      return;
    }
    const containerRect = container.getBoundingClientRect();
    const w = el.offsetWidth || 260;
    const h = el.offsetHeight || 150;
    const padding = 8;

    let x = position.x - w / 2; // center on midpoint
    let y = position.y - h - 10; // above the edge

    // If overflow top, show below
    if (y < padding) {
      y = position.y + 10;
    }
    x = Math.max(padding, Math.min(x, containerRect.width - w - padding));
    y = Math.max(padding, Math.min(y, containerRect.height - h - padding));

    setClampedPos({ x, y });
  }, [position]);

  const reducedMotion =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const confidencePercent = Math.round(edgeData.confidence_score * 100);

  return (
    <div
      ref={popoverRef}
      role="dialog"
      aria-label={`Relationship details: ${edgeData.type}`}
      className={`absolute z-50 max-w-[260px] rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] shadow-lg ${
        reducedMotion ? "" : "animate-in fade-in zoom-in-95 duration-150"
      }`}
      style={{ left: clampedPos.x, top: clampedPos.y }}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2 p-3 pb-2">
        <div className="flex items-center gap-1.5">
          <span className="rounded bg-[var(--bg-hover)] px-2 py-0.5 text-xs font-medium text-[var(--text-primary)]">
            {edgeData.type}
          </span>
          {edgeData.origin === "manual" && (
            <span className="rounded bg-[var(--bg-hover)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-muted)] border border-[var(--border-subtle)]">
              Manual
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--text-secondary)]">
            {confidencePercent}%
          </span>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          >
            <X className="size-3.5" />
          </button>
        </div>
      </div>

      {/* Source → Target */}
      <div className="px-3 pb-2">
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-[var(--text-primary)] truncate">
            {sourceEntityName}
          </span>
          <ArrowRight className="size-3 shrink-0 text-[var(--text-muted)]" />
          <span className="text-[var(--text-primary)] truncate">
            {targetEntityName}
          </span>
        </div>
      </div>

      {/* Evidence / Source annotation */}
      <div className="border-t border-[var(--border-subtle)] px-3 py-2">
        {edgeData.source_annotation ? (
          <div className="flex flex-col gap-1">
            <p className="text-xs text-[var(--text-muted)]">Evidence:</p>
            <p className="text-xs text-[var(--text-secondary)] italic">
              {edgeData.source_annotation}
            </p>
          </div>
        ) : onNavigateToEntity ? (
          <div className="flex flex-col gap-1">
            <p className="text-xs text-[var(--text-muted)]">
              View source entities for evidence:
            </p>
            <div className="flex flex-wrap gap-x-2 gap-y-0.5">
              <button
                onClick={() => onNavigateToEntity(edgeData.source)}
                className="text-xs text-[var(--text-primary)] hover:underline"
              >
                {sourceEntityName}
              </button>
              <button
                onClick={() => onNavigateToEntity(edgeData.target)}
                className="text-xs text-[var(--text-primary)] hover:underline"
              >
                {targetEntityName}
              </button>
            </div>
          </div>
        ) : (
          <p className="text-xs text-[var(--text-muted)]">
            View source entities for evidence
          </p>
        )}
      </div>
    </div>
  );
}
