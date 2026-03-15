import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types.generated";

export type EntityListItem = components["schemas"]["EntityListItem"];
export type EntityListResponse = components["schemas"]["EntityListResponse"];
export type EntityTypeSummary = components["schemas"]["EntityTypeSummary"];

export function useEntities(
  investigationId: string,
  typeFilter?: string,
  /** When true, poll every 5s to pick up newly extracted entities. */
  polling = false,
) {
  return useQuery<EntityListResponse>({
    queryKey: ["entities", investigationId, typeFilter],
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/investigations/{investigation_id}/entities/",
        {
          params: {
            path: { investigation_id: investigationId },
            query: typeFilter ? { type: typeFilter } : {},
          },
        },
      );
      if (error) throw error;
      return data;
    },
    enabled: !!investigationId,
    refetchInterval: polling ? 5000 : false,
  });
}
