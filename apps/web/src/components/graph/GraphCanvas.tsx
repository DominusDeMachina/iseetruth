import { useRef, useEffect, useCallback } from "react";
import { RefreshCw } from "lucide-react";
import { useCytoscape } from "@/hooks/useCytoscape";
import { useGraphData } from "@/hooks/useGraphData";
import { cytoscapeStylesheet } from "@/lib/cytoscape-styles";
import { GraphControls } from "./GraphControls";

interface GraphCanvasProps {
  investigationId: string;
}

function buildFcoseOptions(reducedMotion: boolean): cytoscape.LayoutOptions {
  return {
    name: "fcose",
    animate: !reducedMotion,
    animationDuration: reducedMotion ? 0 : 400,
    quality: "default",
    randomize: false,
    nodeSeparation: 75,
  } as unknown as cytoscape.LayoutOptions;
}

export function GraphCanvas({ investigationId }: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { cy, isReady, error: cyError, reducedMotion } = useCytoscape(containerRef);
  const {
    data,
    isLoading,
    isError,
    error: dataError,
    refetch,
  } = useGraphData(investigationId);

  // Apply stylesheet once Cytoscape is ready
  useEffect(() => {
    if (!cy || !isReady) return;
    cy.style(cytoscapeStylesheet);
  }, [cy, isReady]);

  // Sync data into Cytoscape when data changes
  useEffect(() => {
    if (!cy || !isReady || !data) return;

    const incoming = [...(data.nodes ?? []), ...(data.edges ?? [])];
    if (incoming.length === 0) return;

    // Compute diff to avoid re-adding existing elements
    const existingIds = new Set(cy.elements().map((ele) => ele.id()));
    const toAdd = incoming.filter(
      (el) => !existingIds.has(el.data.id),
    );

    if (toAdd.length > 0) {
      cy.add(toAdd);
      cy.layout(buildFcoseOptions(reducedMotion)).run();
    }
  }, [cy, isReady, data, reducedMotion]);

  // Edge hover label toggle
  useEffect(() => {
    if (!cy || !isReady) return;

    const showLabel = (e: cytoscape.EventObject) =>
      e.target.addClass("show-label");
    const hideLabel = (e: cytoscape.EventObject) =>
      e.target.removeClass("show-label");

    cy.on("mouseover", "edge", showLabel);
    cy.on("mouseout", "edge", hideLabel);

    return () => {
      cy.off("mouseover", "edge", showLabel);
      cy.off("mouseout", "edge", hideLabel);
    };
  }, [cy, isReady]);

  const handleRelayout = useCallback(() => {
    if (!cy) return;
    cy.layout(buildFcoseOptions(reducedMotion)).run();
  }, [cy, reducedMotion]);

  const hasElements =
    data && ((data.nodes?.length ?? 0) > 0 || (data.edges?.length ?? 0) > 0);

  // Determine which overlay to show (if any) on top of the always-rendered container
  let overlay: React.ReactNode = null;
  if (cyError) {
    overlay = (
      <p className="text-[var(--text-secondary)]">
        Failed to initialize graph engine.
      </p>
    );
  } else if (isLoading) {
    overlay = (
      <div className="flex flex-col items-center gap-3">
        <RefreshCw className="size-6 animate-spin text-[var(--text-muted)]" />
        <p className="text-sm text-[var(--text-secondary)]">
          Loading graph data…
        </p>
      </div>
    );
  } else if (isError) {
    overlay = (
      <div className="flex flex-col items-center gap-3">
        <p className="text-sm text-[var(--status-error)]">
          Failed to load graph data.
        </p>
        <button
          onClick={() => refetch()}
          className="rounded bg-[var(--bg-elevated)] px-3 py-1.5 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
        >
          Retry
        </button>
        {dataError && (
          <p className="text-xs text-[var(--text-muted)]">
            {String(dataError)}
          </p>
        )}
      </div>
    );
  } else if (!hasElements) {
    overlay = (
      <p className="text-sm text-[var(--text-secondary)]">
        No entities found. Upload and process documents to populate the graph.
      </p>
    );
  }

  return (
    <div className="relative h-full w-full">
      {/* Always render the container so useCytoscape can attach on mount */}
      <div ref={containerRef} className="h-full w-full" />
      {overlay && (
        <div className="absolute inset-0 flex items-center justify-center bg-[var(--bg-primary)]">
          {overlay}
        </div>
      )}
      {cy && !overlay && (
        <GraphControls cy={cy} onRelayout={handleRelayout} />
      )}
    </div>
  );
}
