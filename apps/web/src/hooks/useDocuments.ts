import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types.generated";

export type DocumentResponse = components["schemas"]["DocumentResponse"];
export type DocumentListResponse = components["schemas"]["DocumentListResponse"];

/** DocumentResponse + transient SSE progress fields (not from the API) */
export type DocumentWithProgress = DocumentResponse & {
  _progress?: number;
  _chunkCount?: number;
  _chunksDone?: number;
};
export type DocumentTextResponse = components["schemas"]["DocumentTextResponse"];
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

export function useDocumentText(
  investigationId: string,
  documentId: string | null,
) {
  return useQuery<DocumentTextResponse>({
    queryKey: ["document-text", investigationId, documentId],
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/investigations/{investigation_id}/documents/{document_id}/text",
        {
          params: {
            path: {
              investigation_id: investigationId,
              document_id: documentId!,
            },
          },
        },
      );
      if (error) throw error;
      return data;
    },
    enabled: !!documentId,
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
    onSuccess: (response) => {
      // Immediately merge uploaded documents (status: "queued") into cache
      // so hasProcessing becomes true and SSE connects before Celery publishes events
      queryClient.setQueryData<DocumentListResponse>(
        ["documents", investigationId],
        (old) => {
          if (!old) return { items: response.items, total: response.items.length };
          const existingIds = new Set(old.items.map((d) => d.id));
          const newItems = response.items.filter((d) => !existingIds.has(d.id));
          return {
            ...old,
            items: [...old.items, ...newItems],
            total: old.total + newItems.length,
          };
        },
      );
      // Also refetch in background to reconcile with server state
      queryClient.invalidateQueries({
        queryKey: ["documents", investigationId],
      });
      queryClient.invalidateQueries({ queryKey: ["investigations"] });
    },
  });
}

export function useRetryDocument(investigationId: string) {
  const queryClient = useQueryClient();
  return useMutation<DocumentResponse, Error, string, { previous: DocumentListResponse | undefined }>({
    mutationFn: async (documentId) => {
      const { data, error } = await api.POST(
        "/api/v1/investigations/{investigation_id}/documents/{document_id}/retry",
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
      return data;
    },
    onMutate: async (documentId) => {
      await queryClient.cancelQueries({ queryKey: ["documents", investigationId] });
      const previous = queryClient.getQueryData<DocumentListResponse>(
        ["documents", investigationId],
      );

      // Optimistically update document cache
      queryClient.setQueryData<DocumentListResponse>(
        ["documents", investigationId],
        (old) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.map((doc) =>
              doc.id === documentId
                ? { ...doc, status: "queued", error_message: null, failed_stage: null }
                : doc,
            ),
          };
        },
      );

      return { previous };
    },
    onError: (_err, _documentId, context) => {
      // Rollback optimistic update
      if (context?.previous) {
        queryClient.setQueryData(
          ["documents", investigationId],
          context.previous,
        );
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", investigationId],
      });
    },
  });
}

export function useCaptureWebPage(investigationId: string) {
  const queryClient = useQueryClient();
  return useMutation<DocumentResponse, Error, string>({
    mutationFn: async (url) => {
      const { data, error } = await api.POST(
        "/api/v1/investigations/{investigation_id}/documents/capture",
        {
          params: { path: { investigation_id: investigationId } },
          body: { url },
        },
      );
      if (error) throw error;
      return data;
    },
    onSuccess: (response) => {
      queryClient.setQueryData<DocumentListResponse>(
        ["documents", investigationId],
        (old) => {
          if (!old) return { items: [response], total: 1 };
          return {
            ...old,
            items: [...old.items, response],
            total: old.total + 1,
          };
        },
      );
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
