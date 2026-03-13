import { useRef, useEffect, useCallback, useState } from "react";
import { RefreshCw } from "lucide-react";
import { useCytoscape } from "@/hooks/useCytoscape";
import { useGraphData, useExpandNeighbors } from "@/hooks/useGraphData";
import { cytoscapeStylesheet } from "@/lib/cytoscape-styles";
import { GraphControls } from "./GraphControls";
import { EntityDetailCard } from "./EntityDetailCard";
import { EdgeDetailPopover } from "./EdgeDetailPopover";

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
  const { expandNeighbors } = useExpandNeighbors(investigationId);

  // Selection state for detail cards
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [cardPosition, setCardPosition] = useState<{ x: number; y: number } | null>(null);
  // Store edge data for the popover
  const [selectedEdgeData, setSelectedEdgeData] = useState<{
    id: string;
    source: string;
    target: string;
    type: string;
    confidence_score: number;
  } | null>(null);
  const [edgeEntityNames, setEdgeEntityNames] = useState<{
    sourceName: string;
    targetName: string;
  }>({ sourceName: "", targetName: "" });

  // Tooltip ref for node hover
  const tooltipRef = useRef<HTMLDivElement | null>(null);

  const clearSelection = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setCardPosition(null);
    setSelectedEdgeData(null);
  }, []);

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

  // Node hover tooltip (DOM-based for performance)
  useEffect(() => {
    if (!cy || !isReady) return;

    // Create tooltip element
    const tooltip = document.createElement("div");
    tooltip.className =
      "pointer-events-none absolute z-40 rounded px-2 py-1 text-xs shadow bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-subtle)] hidden";
    containerRef.current?.parentElement?.appendChild(tooltip);
    tooltipRef.current = tooltip;

    const onMouseOver = (e: cytoscape.EventObject) => {
      const node = e.target;
      const name = node.data("name") ?? "";
      const type = node.data("type") ?? "";
      const relCount = node.data("relationship_count") ?? 0;
      tooltip.textContent = `${name} · ${type} · ${relCount} connections`;
      const pos = node.renderedPosition();
      tooltip.style.left = `${pos.x + 15}px`;
      tooltip.style.top = `${pos.y - 30}px`;
      tooltip.classList.remove("hidden");
    };

    const onMouseOut = () => {
      tooltip.classList.add("hidden");
    };

    cy.on("mouseover", "node", onMouseOver);
    cy.on("mouseout", "node", onMouseOut);

    return () => {
      cy.off("mouseover", "node", onMouseOver);
      cy.off("mouseout", "node", onMouseOut);
      tooltip.remove();
      tooltipRef.current = null;
    };
  }, [cy, isReady]);

  // Click handlers: tap node, tap edge, tap background, dbltap node
  useEffect(() => {
    if (!cy || !isReady) return;

    let tapTimeout: ReturnType<typeof setTimeout> | null = null;
    let pendingNodeId: string | null = null;
    let pendingPos: { x: number; y: number } | null = null;

    const onNodeTap = (e: cytoscape.EventObject) => {
      const nodeId = e.target.data("id") as string;
      const pos = e.target.renderedPosition();

      // Delay single-tap to distinguish from double-tap
      pendingNodeId = nodeId;
      pendingPos = { x: pos.x, y: pos.y };
      if (tapTimeout) clearTimeout(tapTimeout);
      tapTimeout = setTimeout(() => {
        // Hide tooltip when card opens
        if (tooltipRef.current) tooltipRef.current.classList.add("hidden");
        setSelectedEdgeId(null);
        setSelectedEdgeData(null);
        setSelectedNodeId(pendingNodeId);
        setCardPosition(pendingPos);
        pendingNodeId = null;
        pendingPos = null;
      }, 200);
    };

    const onEdgeTap = (e: cytoscape.EventObject) => {
      const edgeData = e.target.data();
      const sourceNode = cy.getElementById(edgeData.source);
      const targetNode = cy.getElementById(edgeData.target);
      const sourcePos = sourceNode.renderedPosition();
      const targetPos = targetNode.renderedPosition();
      const midpoint = {
        x: (sourcePos.x + targetPos.x) / 2,
        y: (sourcePos.y + targetPos.y) / 2,
      };

      setSelectedNodeId(null);
      setSelectedEdgeId(edgeData.id);
      setSelectedEdgeData({
        id: edgeData.id,
        source: edgeData.source,
        target: edgeData.target,
        type: edgeData.type,
        confidence_score: edgeData.confidence_score,
      });
      setEdgeEntityNames({
        sourceName: sourceNode.data("name") ?? edgeData.source,
        targetName: targetNode.data("name") ?? edgeData.target,
      });
      setCardPosition(midpoint);
    };

    const onBackgroundTap = (e: cytoscape.EventObject) => {
      if (e.target === cy) {
        clearSelection();
      }
    };

    const onNodeDblTap = (e: cytoscape.EventObject) => {
      // Cancel pending single-tap so the card doesn't re-open for the first click
      if (tapTimeout) {
        clearTimeout(tapTimeout);
        tapTimeout = null;
      }
      const entityId = e.target.data("id") as string;
      // expandNeighbors merges results into TanStack Query cache;
      // the data sync useEffect will detect new elements and re-run layout
      expandNeighbors(entityId);
    };

    cy.on("tap", "node", onNodeTap);
    cy.on("tap", "edge", onEdgeTap);
    cy.on("tap", onBackgroundTap);
    cy.on("dbltap", "node", onNodeDblTap);

    return () => {
      if (tapTimeout) clearTimeout(tapTimeout);
      cy.off("tap", "node", onNodeTap);
      cy.off("tap", "edge", onEdgeTap);
      cy.off("tap", onBackgroundTap);
      cy.off("dbltap", "node", onNodeDblTap);
    };
  }, [cy, isReady, expandNeighbors, clearSelection]);

  const handleNavigateToEntity = useCallback(
    (targetId: string) => {
      if (!cy) return;
      const targetNode = cy.getElementById(targetId);
      if (targetNode.empty()) return;

      // Close current card, center on target, open new card
      cy.animate({
        center: { eles: targetNode },
        duration: reducedMotion ? 0 : 300,
        complete: () => {
          const pos = targetNode.renderedPosition();
          setSelectedEdgeId(null);
          setSelectedEdgeData(null);
          setSelectedNodeId(targetId);
          setCardPosition({ x: pos.x, y: pos.y });
        },
      });
    },
    [cy, reducedMotion],
  );

  const handleAskAboutEntity = useCallback((entityName: string) => {
    // TODO: Epic 5 — wire to Q&A input
    console.log(`Ask about entity: ${entityName}`);
  }, []);

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

      {/* Entity Detail Card */}
      {selectedNodeId && cardPosition && (
        <EntityDetailCard
          entityId={selectedNodeId}
          investigationId={investigationId}
          position={cardPosition}
          onClose={clearSelection}
          onNavigateToEntity={handleNavigateToEntity}
          onAskAboutEntity={handleAskAboutEntity}
        />
      )}

      {/* Edge Detail Popover */}
      {selectedEdgeId && selectedEdgeData && cardPosition && (
        <EdgeDetailPopover
          edgeData={selectedEdgeData}
          sourceEntityName={edgeEntityNames.sourceName}
          targetEntityName={edgeEntityNames.targetName}
          position={cardPosition}
          onClose={clearSelection}
          onNavigateToEntity={handleNavigateToEntity}
        />
      )}
    </div>
  );
}
