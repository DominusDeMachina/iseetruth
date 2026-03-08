import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types.generated";

export type Investigation = components["schemas"]["InvestigationResponse"];
export type InvestigationListResponse =
  components["schemas"]["InvestigationListResponse"];
export type CreateInvestigationInput =
  components["schemas"]["InvestigationCreate"];

export function useInvestigations() {
  return useQuery<InvestigationListResponse>({
    queryKey: ["investigations"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/investigations/");
      if (error) throw error;
      return data;
    },
  });
}

export function useInvestigation(id: string) {
  return useQuery<Investigation>({
    queryKey: ["investigations", id],
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/investigations/{investigation_id}",
        { params: { path: { investigation_id: id } } },
      );
      if (error) throw error;
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateInvestigation() {
  const queryClient = useQueryClient();
  return useMutation<Investigation, Error, CreateInvestigationInput>({
    mutationFn: async (input) => {
      const { data, error } = await api.POST("/api/v1/investigations/", {
        body: input,
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investigations"] });
    },
  });
}

export function useDeleteInvestigation() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const { error } = await api.DELETE(
        "/api/v1/investigations/{investigation_id}",
        { params: { path: { investigation_id: id } } },
      );
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investigations"] });
    },
  });
}
