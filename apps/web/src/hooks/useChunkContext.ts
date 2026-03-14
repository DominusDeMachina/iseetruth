import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types.generated";

export type ChunkWithContextResponse =
  components["schemas"]["ChunkWithContextResponse"];

export function useChunkContext(
  investigationId: string,
  chunkId: string | null,
) {
  return useQuery<ChunkWithContextResponse>({
    queryKey: ["chunk-context", investigationId, chunkId],
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/investigations/{investigation_id}/chunks/{chunk_id}",
        {
          params: {
            path: {
              investigation_id: investigationId,
              chunk_id: chunkId!,
            },
          },
        },
      );
      if (error) throw error;
      return data;
    },
    enabled: !!chunkId,
    staleTime: Infinity,
  });
}
