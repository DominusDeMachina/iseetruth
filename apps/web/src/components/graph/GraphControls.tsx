import type { Core } from "cytoscape";
import { ZoomIn, ZoomOut, Maximize2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface GraphControlsProps {
  cy: Core;
  onRelayout: () => void;
}

export function GraphControls({ cy, onRelayout }: GraphControlsProps) {
  return (
    <div className="absolute bottom-3 right-3 flex flex-col gap-1 rounded-lg bg-[var(--bg-elevated)] p-1 shadow-lg border border-[var(--border-subtle)]">
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
