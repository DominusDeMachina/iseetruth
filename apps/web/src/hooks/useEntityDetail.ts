import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types.generated";

export type EntityDetailResponse =
  components["schemas"]["EntityDetailResponse"];

export function useEntityDetail(
  investigationId: string,
  entityId: string | null,
) {
  return useQuery({
    queryKey: ["entity-detail", investigationId, entityId],
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/investigations/{investigation_id}/entities/{entity_id}",
        {
          params: {
            path: {
              investigation_id: investigationId,
              entity_id: entityId!,
            },
          },
        },
      );
      if (error) throw error;
      return data;
    },
    enabled: !!investigationId && !!entityId,
    staleTime: 30_000,
  });
}
