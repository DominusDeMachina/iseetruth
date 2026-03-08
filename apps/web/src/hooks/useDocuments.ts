import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types.generated";

export type DocumentResponse = components["schemas"]["DocumentResponse"];
export type DocumentListResponse = components["schemas"]["DocumentListResponse"];
export type UploadDocumentsResponse =
  components["schemas"]["UploadDocumentsResponse"];

export function useDocuments(investigationId: string) {
  return useQuery<DocumentListResponse>({
    queryKey: ["documents", investigationId],
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/investigations/{investigation_id}/documents",
        { params: { path: { investigation_id: investigationId } } },
      );
      if (error) throw error;
      return data;
    },
    enabled: !!investigationId,
  });
}

export function useUploadDocuments(investigationId: string) {
  const queryClient = useQueryClient();
  return useMutation<UploadDocumentsResponse, Error, File[]>({
    mutationFn: async (files) => {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));

      const { data, error } = await api.POST(
        "/api/v1/investigations/{investigation_id}/documents",
        {
          params: { path: { investigation_id: investigationId } },
          body: formData as never,
          bodySerializer: (body: unknown) => body as BodyInit,
        },
      );
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", investigationId],
      });
      queryClient.invalidateQueries({ queryKey: ["investigations"] });
    },
  });
}

export function useDeleteDocument(investigationId: string) {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (documentId) => {
      const { error } = await api.DELETE(
        "/api/v1/investigations/{investigation_id}/documents/{document_id}",
        {
          params: {
            path: {
              investigation_id: investigationId,
              document_id: documentId,
            },
          },
        },
      );
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", investigationId],
      });
      queryClient.invalidateQueries({ queryKey: ["investigations"] });
    },
  });
}
