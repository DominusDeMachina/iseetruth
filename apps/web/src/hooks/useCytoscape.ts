import { useEffect, useRef, useState, type RefObject } from "react";
import cytoscape, { type Core } from "cytoscape";
import fcose from "cytoscape-fcose";

// Register fcose layout extension once at module scope (Task 1.4)
cytoscape.use(fcose);

interface UseCytoscapeOptions {
  reducedMotion?: boolean;
}

interface UseCytoscapeResult {
  cy: Core | null;
  isReady: boolean;
  error: Error | null;
  reducedMotion: boolean;
}

export function useCytoscape(
  containerRef: RefObject<HTMLDivElement | null>,
  options?: UseCytoscapeOptions,
): UseCytoscapeResult {
  const cyRef = useRef<Core | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Detect prefers-reduced-motion
  const reducedMotion =
    options?.reducedMotion ??
    (typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    try {
      const cy = cytoscape({
        container,
        style: [], // styles applied separately via GraphCanvas
        userZoomingEnabled: true,
        userPanningEnabled: true,
        boxSelectionEnabled: false,
        minZoom: 0.1,
        maxZoom: 3,
      });

      cy.ready(() => {
        setIsReady(true);
      });

      cyRef.current = cy;
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error("Failed to initialize graph"),
      );
      setIsReady(false);
      cyRef.current = null;
    }

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
      setIsReady(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [containerRef]);

  return { cy: cyRef.current, isReady, error, reducedMotion };
}
