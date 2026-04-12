import type { Core } from "cytoscape";
import { ZoomIn, ZoomOut, Maximize2, RefreshCw, Link2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface GraphControlsProps {
  cy: Core;
  onRelayout: () => void;
  crossInvestigationCount?: number;
  onToggleCrossInvestigation?: () => void;
  crossInvestigationOpen?: boolean;
}

export function GraphControls({
  cy,
  onRelayout,
  crossInvestigationCount,
  onToggleCrossInvestigation,
  crossInvestigationOpen,
}: GraphControlsProps) {
  return (
    <div className="absolute bottom-3 right-3 flex flex-col gap-1 rounded-lg bg-[var(--bg-elevated)] p-1 shadow-lg border border-[var(--border-subtle)]">
      {onToggleCrossInvestigation && (
        <div className="relative">
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={onToggleCrossInvestigation}
            title="Cross-Investigation Links"
            aria-label="Cross-Investigation Links"
            aria-pressed={crossInvestigationOpen}
          >
            <Link2 />
          </Button>
          {crossInvestigationCount != null && crossInvestigationCount > 0 && !crossInvestigationOpen && (
            <span className="absolute -right-1 -top-1 flex size-3.5 items-center justify-center rounded-full bg-[var(--status-info)] text-[9px] font-bold text-white">
              {crossInvestigationCount > 9 ? "9+" : crossInvestigationCount}
            </span>
          )}
        </div>
      )}
      <Button
        variant="ghost"
        size="icon-xs"
        onClick={() => cy.zoom({ level: cy.zoom() * 1.2, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } })}
        title="Zoom in"
      >
        <ZoomIn />
      </Button>
      <Button
        variant="ghost"
        size="icon-xs"
        onClick={() => cy.zoom({ level: cy.zoom() / 1.2, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } })}
        title="Zoom out"
      >
        <ZoomOut />
      </Button>
      <Button
        variant="ghost"
        size="icon-xs"
        onClick={() => cy.fit(undefined, 50)}
        title="Fit to view"
      >
        <Maximize2 />
      </Button>
      <Button
        variant="ghost"
        size="icon-xs"
        onClick={onRelayout}
        title="Re-layout"
      >
        <RefreshCw />
      </Button>
    </div>
  );
}
