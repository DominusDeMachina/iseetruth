import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types.generated";

export type GraphResponse = components["schemas"]["GraphResponse"];
export type GraphNode = components["schemas"]["GraphNode"];
export type GraphEdge = components["schemas"]["GraphEdge"];

export interface GraphFilters {
  entityTypes?: string[];
  documentId?: string;
}

function graphQueryKey(investigationId: string, filters?: GraphFilters) {
  return [
    "graph",
    investigationId,
    filters?.entityTypes,
    filters?.documentId,
  ];
}

export function useGraphData(
  investigationId: string,
  filters?: GraphFilters,
) {
  return useQuery({
    queryKey: graphQueryKey(investigationId, filters),
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/investigations/{investigation_id}/graph/",
        {
          params: {
            path: { investigation_id: investigationId },
            query: {
              limit: 50,
              ...(filters?.entityTypes?.length
                ? { entity_types: filters.entityTypes.join(",") }
                : {}),
              ...(filters?.documentId
                ? { document_id: filters.documentId }
                : {}),
            },
          },
        },
      );
      if (error) throw error;
      return data;
    },
    enabled: !!investigationId,
  });
}

export function useExpandNeighbors(
  investigationId: string,
  filters?: GraphFilters,
) {
  const queryClient = useQueryClient();

  const expandNeighbors = useCallback(
    async (entityId: string) => {
      const { data, error } = await api.GET(
        "/api/v1/investigations/{investigation_id}/graph/neighbors/{entity_id}",
        {
          params: {
            path: {
              investigation_id: investigationId,
              entity_id: entityId,
            },
          },
        },
      );
      if (error) throw error;

      // Merge new nodes/edges into cached graph data, deduplicating by id
      // Cache key includes filters so setQueryData targets the correct entry
      queryClient.setQueryData<GraphResponse>(
        graphQueryKey(investigationId, filters),
        (old) => {
          if (!old || !data) return old;

          const existingNodeIds = new Set(old.nodes.map((n) => n.data.id));
          const existingEdgeIds = new Set(old.edges.map((e) => e.data.id));

          const newNodes = data.nodes.filter(
            (n) => !existingNodeIds.has(n.data.id),
          );
          const newEdges = data.edges.filter(
            (e) => !existingEdgeIds.has(e.data.id),
          );

          return {
            ...old,
            nodes: [...old.nodes, ...newNodes],
            edges: [...old.edges, ...newEdges],
            total_nodes: old.total_nodes,
            total_edges: old.total_edges,
          };
        },
      );

      return data;
    },
    [investigationId, filters, queryClient],
  );

  return { expandNeighbors };
}
