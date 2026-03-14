import { useRef, useEffect, useCallback, useState, useMemo } from "react";
import { RefreshCw, Search } from "lucide-react";
import { useCytoscape } from "@/hooks/useCytoscape";
import {
  useGraphData,
  useExpandNeighbors,
  type GraphFilters,
} from "@/hooks/useGraphData";
import type { DocumentResponse } from "@/hooks/useDocuments";
import type { EntityListItem } from "@/hooks/useEntities";
import { cytoscapeStylesheet } from "@/lib/cytoscape-styles";
import { GraphControls } from "./GraphControls";
import { GraphFilterPanel } from "./GraphFilterPanel";
import { EntityDetailCard } from "./EntityDetailCard";
import { EdgeDetailPopover } from "./EdgeDetailPopover";
import { EntitySearchCommand } from "./EntitySearchCommand";

interface GraphCanvasProps {
  investigationId: string;
  documents?: DocumentResponse[];
  onAskAboutEntity?: (entityName: string) => void;
  highlightEntities?: string[];
  onHighlightClear?: () => void;
}

function buildFcoseOptions(
  reducedMotion: boolean,
  overrides?: { animationDuration?: number },
): cytoscape.LayoutOptions {
  return {
    name: "fcose",
    animate: !reducedMotion,
    animationDuration: reducedMotion
      ? 0
      : (overrides?.animationDuration ?? 400),
    quality: "default",
    randomize: false,
    nodeSeparation: 75,
  } as unknown as cytoscape.LayoutOptions;
}

export function GraphCanvas({
  investigationId,
  documents,
  onAskAboutEntity: onAskAboutEntityProp,
  highlightEntities: highlightEntitiesProp,
  onHighlightClear,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { cy, isReady, error: cyError, reducedMotion } = useCytoscape(containerRef);

  // Filter state
  const [entityTypes, setEntityTypes] = useState<string[]>([]);
  const [documentId, setDocumentId] = useState<string | undefined>();
  const [filtersCollapsed, setFiltersCollapsed] = useState(true);

  const filters: GraphFilters = useMemo(
    () => ({
      entityTypes: entityTypes.length > 0 ? entityTypes : undefined,
      documentId,
    }),
    [entityTypes, documentId],
  );

  const {
    data,
    isLoading,
    isError,
    error: dataError,
    refetch,
  } = useGraphData(investigationId, filters);
  const { expandNeighbors } = useExpandNeighbors(investigationId, filters);

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

  // Search state
  const [searchOpen, setSearchOpen] = useState(false);
  const [highlightedEntityIds, setHighlightedEntityIds] = useState<string[]>([]);

  // Tooltip ref for node hover
  const tooltipRef = useRef<HTMLDivElement | null>(null);

  const clearHighlights = useCallback(() => {
    if (!cy) return;
    cy.elements().removeClass("search-highlighted search-dimmed");
    setHighlightedEntityIds([]);
  }, [cy]);

  const clearSelection = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setCardPosition(null);
    setSelectedEdgeData(null);
    clearHighlights();
  }, [clearHighlights]);

  // Close detail card when filter change removes the selected node or edge
  useEffect(() => {
    if (!data) return;
    if (selectedNodeId) {
      const nodeStillVisible = data.nodes?.some(
        (n) => n.data.id === selectedNodeId,
      );
      if (!nodeStillVisible) {
        clearSelection();
        return;
      }
    }
    if (selectedEdgeId) {
      const edgeStillVisible = data.edges?.some(
        (e) => e.data.id === selectedEdgeId,
      );
      if (!edgeStillVisible) {
        clearSelection();
      }
    }
  }, [data, selectedNodeId, selectedEdgeId, clearSelection]);

  // Apply stylesheet once Cytoscape is ready
  useEffect(() => {
    if (!cy || !isReady) return;
    cy.style(cytoscapeStylesheet);
  }, [cy, isReady]);

  // Sync data into Cytoscape when data changes (including filter changes)
  useEffect(() => {
    if (!cy || !isReady || !data) return;

    const incoming = [...(data.nodes ?? []), ...(data.edges ?? [])];
    const incomingIds = new Set(incoming.map((el) => el.data.id));
    const existingIds = new Set(cy.elements().map((ele) => ele.id()));

    const toAdd = incoming.filter((el) => !existingIds.has(el.data.id));
    const toRemove = cy.elements().filter((ele) => !incomingIds.has(ele.id()));

    if (toAdd.length === 0 && toRemove.length === 0) return;

    cy.startBatch();
    if (toRemove.length > 0) {
      cy.remove(toRemove);
    }
    if (toAdd.length > 0) {
      cy.add(toAdd);
    }
    cy.endBatch();

    // Use faster animation for filter transitions (200ms) vs initial/expansion (400ms)
    const isFilterTransition = toRemove.length > 0;
    cy.layout(
      buildFcoseOptions(reducedMotion, {
        animationDuration: isFilterTransition ? 200 : 400,
      }),
    ).run();
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

  const handleAskAboutEntity = useCallback(
    (entityName: string) => {
      onAskAboutEntityProp?.(entityName);
    },
    [onAskAboutEntityProp],
  );

  const centerAndHighlight = useCallback(
    (entityId: string) => {
      if (!cy) return;
      const node = cy.getElementById(entityId);
      if (node.empty()) return;

      // Clear previous highlights before applying new ones
      cy.elements().removeClass("search-highlighted search-dimmed");
      cy.elements().addClass("search-dimmed");
      node.removeClass("search-dimmed").addClass("search-highlighted");

      // Center on node
      cy.animate({
        center: { eles: node },
        zoom: cy.zoom(),
        duration: reducedMotion ? 0 : 400,
        easing: "ease-out",
        complete: () => {
          // Pulse animation: 2 cycles of border-width oscillation
          if (!reducedMotion) {
            node.animate({
              style: { "border-width": 6 } as unknown as Record<string, string>,
              duration: 150,
              easing: "ease-in-out",
              complete: () => {
                node.animate({
                  style: { "border-width": 4 } as unknown as Record<string, string>,
                  duration: 150,
                  easing: "ease-in-out",
                  complete: () => {
                    node.animate({
                      style: { "border-width": 6 } as unknown as Record<string, string>,
                      duration: 150,
                      easing: "ease-in-out",
                      complete: () => {
                        node.animate({
                          style: { "border-width": 4 } as unknown as Record<string, string>,
                          duration: 150,
                          easing: "ease-in-out",
                        });
                      },
                    });
                  },
                });
              },
            });
          }
        },
      });
    },
    [cy, reducedMotion],
  );

  const handleSearchSelect = useCallback(
    (entity: EntityListItem) => {
      setSearchOpen(false);
      if (!cy) return;

      const node = cy.getElementById(entity.id);
      if (node.nonempty()) {
        // Node already in graph — center and highlight directly
        centerAndHighlight(entity.id);
      } else {
        // Node not in graph — expand neighbors to load it, then highlight
        setHighlightedEntityIds([entity.id]);
        expandNeighbors(entity.id);
      }
    },
    [cy, centerAndHighlight, expandNeighbors],
  );

  // After expand adds new nodes, center on highlighted entity
  useEffect(() => {
    if (!cy || highlightedEntityIds.length === 0) return;
    const targetId = highlightedEntityIds[0];
    const node = cy.getElementById(targetId);
    if (node.nonempty()) {
      // Wait for layout to settle before centering
      const timeout = setTimeout(() => {
        centerAndHighlight(targetId);
        setHighlightedEntityIds([]);
      }, reducedMotion ? 50 : 500);
      return () => clearTimeout(timeout);
    }
  }, [cy, highlightedEntityIds, data, centerAndHighlight, reducedMotion]);

  // Highlight entities from Q&A answers
  useEffect(() => {
    if (!cy || !highlightEntitiesProp || highlightEntitiesProp.length === 0)
      return;

    // Find matching nodes by name (case-insensitive)
    const matchingNodes = cy.nodes().filter((node) => {
      const name = (node.data("name") as string) ?? "";
      return highlightEntitiesProp.some(
        (h) => h.toLowerCase() === name.toLowerCase(),
      );
    });

    if (matchingNodes.empty()) return;

    // Apply highlight classes
    cy.elements().addClass("search-dimmed");
    matchingNodes.removeClass("search-dimmed").addClass("search-highlighted");

    // Center on first matching node
    const first = matchingNodes.first();
    cy.animate({
      center: { eles: first },
      zoom: cy.zoom(),
      duration: reducedMotion ? 0 : 400,
    });

    return () => {
      // Clean up when highlight entities change
      cy.elements().removeClass("search-highlighted search-dimmed");
    };
  }, [cy, highlightEntitiesProp, reducedMotion]);

  // Clear Q&A highlights when user interacts with graph
  useEffect(() => {
    if (!cy || !onHighlightClear) return;
    const handler = () => {
      if (highlightEntitiesProp && highlightEntitiesProp.length > 0) {
        onHighlightClear();
      }
    };
    cy.on("tap", handler);
    return () => {
      cy.off("tap", handler);
    };
  }, [cy, highlightEntitiesProp, onHighlightClear]);

  // Keyboard shortcut: Cmd/Ctrl+K to open search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const handleRelayout = useCallback(() => {
    if (!cy) return;
    cy.layout(buildFcoseOptions(reducedMotion)).run();
  }, [cy, reducedMotion]);

  // Only pass completed documents to filter panel
  const completedDocuments = (documents ?? []).filter(
    (d) => d.status === "complete",
  );

  const hasElements =
    data && ((data.nodes?.length ?? 0) > 0 || (data.edges?.length ?? 0) > 0);
  const hasActiveFilters =
    (entityTypes.length > 0) || !!documentId;

  // Determine which overlay to show (if any) on top of the always-rendered container
  let overlay: React.ReactNode = null;
  // Whether to show filters even when overlay is active (empty filtered results)
  let showFiltersWithOverlay = false;
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
  } else if (!hasElements && hasActiveFilters) {
    // Filters are active but no results — keep filter panel visible
    overlay = (
      <p className="text-sm text-[var(--text-secondary)]">
        No entities match the current filters.
      </p>
    );
    showFiltersWithOverlay = true;
  } else if (!hasElements) {
    overlay = (
      <p className="text-sm text-[var(--text-secondary)]">
        No entities found. Upload and process documents to populate the graph.
      </p>
    );
  }

  const showFilters = cy && (!overlay || showFiltersWithOverlay);

  return (
    <div className="relative h-full w-full">
      {/* Always render the container so useCytoscape can attach on mount */}
      <div ref={containerRef} className="h-full w-full" />
      {overlay && (
        <div className="absolute inset-0 flex items-center justify-center bg-[var(--bg-primary)]">
          {overlay}
        </div>
      )}

      {/* Filter panel — visible even when filtered results are empty */}
      {showFilters && (
        <GraphFilterPanel
          entityTypes={entityTypes}
          onEntityTypesChange={setEntityTypes}
          documentId={documentId}
          onDocumentIdChange={setDocumentId}
          documents={completedDocuments}
          isCollapsed={filtersCollapsed}
          onToggleCollapse={() => setFiltersCollapsed((prev) => !prev)}
        />
      )}

      {cy && !overlay && (
        <GraphControls cy={cy} onRelayout={handleRelayout} />
      )}

      {/* Search button */}
      {cy && !overlay && (
        <button
          onClick={() => setSearchOpen(true)}
          className="absolute top-3 right-3 z-30 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-1.5 shadow-lg transition-colors hover:bg-[var(--bg-hover)]"
          title="Search entities (⌘K)"
          aria-label="Search entities"
        >
          <Search className="size-4 text-[var(--text-primary)]" />
        </button>
      )}

      {/* Entity Search Command Palette */}
      <EntitySearchCommand
        investigationId={investigationId}
        open={searchOpen}
        onOpenChange={setSearchOpen}
        onSelectEntity={handleSearchSelect}
      />

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
