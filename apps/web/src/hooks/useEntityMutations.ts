import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types.generated";

type EntityCreateRequest = components["schemas"]["EntityCreateRequest"];
type EntityUpdateRequest = components["schemas"]["EntityUpdateRequest"];
type EntityDetailResponse = components["schemas"]["EntityDetailResponse"];
type RelationshipCreateRequest = components["schemas"]["RelationshipCreateRequest"];
type RelationshipResponse = components["schemas"]["RelationshipResponse"];

export function useCreateEntity(investigationId: string) {
  const queryClient = useQueryClient();

  return useMutation<EntityDetailResponse, Error, EntityCreateRequest>({
    mutationFn: async (body) => {
      const { data, error } = await api.POST(
        "/api/v1/investigations/{investigation_id}/entities/",
        {
          params: { path: { investigation_id: investigationId } },
          body,
        },
      );
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["entities", investigationId],
      });
      queryClient.invalidateQueries({
        queryKey: ["graph", investigationId],
      });
    },
  });
}

export function useUpdateEntity(investigationId: string) {
  const queryClient = useQueryClient();

  return useMutation<
    EntityDetailResponse,
    Error,
    { entityId: string; body: EntityUpdateRequest }
  >({
    mutationFn: async ({ entityId, body }) => {
      const { data, error } = await api.PATCH(
        "/api/v1/investigations/{investigation_id}/entities/{entity_id}",
        {
          params: {
            path: {
              investigation_id: investigationId,
              entity_id: entityId,
            },
          },
          body,
        },
      );
      if (error) throw error;
      return data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["entities", investigationId],
      });
      queryClient.invalidateQueries({
        queryKey: ["entity-detail", investigationId, variables.entityId],
      });
      queryClient.invalidateQueries({
        queryKey: ["graph", investigationId],
      });
    },
  });
}

export function useCreateRelationship(investigationId: string) {
  const queryClient = useQueryClient();

  return useMutation<RelationshipResponse, Error, RelationshipCreateRequest>({
    mutationFn: async (body) => {
      const { data, error } = await api.POST(
        "/api/v1/investigations/{investigation_id}/relationships/",
        {
          params: { path: { investigation_id: investigationId } },
          body,
        },
      );
      if (error) throw error;
      return data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["graph", investigationId],
      });
      queryClient.invalidateQueries({
        queryKey: ["entity-detail", investigationId, variables.source_entity_id],
      });
      queryClient.invalidateQueries({
        queryKey: ["entity-detail", investigationId, variables.target_entity_id],
      });
    },
  });
}
