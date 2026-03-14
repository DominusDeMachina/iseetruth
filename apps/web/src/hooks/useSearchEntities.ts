import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { EntityListItem } from "./useEntities";

export function useSearchEntities(
  investigationId: string,
  query: string,
) {
  const trimmed = query.trim();

  const result = useQuery({
    queryKey: ["entities", "search", investigationId, trimmed],
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/investigations/{investigation_id}/entities/",
        {
          params: {
            path: { investigation_id: investigationId },
            query: { search: trimmed, limit: 20 },
          },
        },
      );
      if (error) throw error;
      return data;
    },
    enabled: !!investigationId && trimmed.length >= 2,
    staleTime: 30_000,
  });

  return {
    data: (result.data?.items ?? []) as EntityListItem[],
    isLoading: result.isLoading,
  };
}
