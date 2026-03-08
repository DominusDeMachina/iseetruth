import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { useInvestigation } from "@/hooks/useInvestigations";
import {
  useDocuments,
  useUploadDocuments,
  useDeleteDocument,
} from "@/hooks/useDocuments";
import { DocumentUploadZone } from "@/components/investigation/DocumentUploadZone";
import { DocumentList } from "@/components/investigation/DocumentList";

export const Route = createFileRoute("/investigations/$id")({
  component: InvestigationDetail,
});

function InvestigationDetail() {
  const { id } = Route.useParams();
  const { data: investigation, isLoading, isError } = useInvestigation(id);
  const { data: documentsData, isLoading: isLoadingDocs } = useDocuments(id);
  const uploadMutation = useUploadDocuments(id);
  const deleteMutation = useDeleteDocument(id);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="animate-pulse">
          <div className="h-7 w-1/3 rounded bg-[var(--bg-hover)]" />
          <div className="mt-2 h-4 w-1/2 rounded bg-[var(--bg-hover)]" />
        </div>
      </div>
    );
  }

  if (isError || !investigation) {
    return (
      <div className="flex flex-col items-center gap-4 pt-12 text-center">
        <p className="text-[var(--text-primary)]">Investigation not found</p>
        <Link
          to="/"
          className="text-sm text-[var(--status-info)] hover:underline"
        >
          Back to investigations
        </Link>
      </div>
    );
  }

  const documents = documentsData?.items ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          to="/"
          className="mb-2 inline-flex items-center gap-1 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
        >
          <ArrowLeft className="size-3" />
          Investigations
        </Link>
        <h2 className="text-xl font-semibold text-[var(--text-primary)]">
          {investigation.name}
        </h2>
        {investigation.description && (
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            {investigation.description}
          </p>
        )}
      </div>

      <DocumentUploadZone
        onUpload={(files) => uploadMutation.mutate(files)}
        isUploading={uploadMutation.isPending}
        hasDocuments={documents.length > 0}
      />

      <DocumentList
        documents={documents}
        isLoading={isLoadingDocs}
        onDeleteDocument={(docId) => {
          setDeletingId(docId);
          deleteMutation.mutate(docId, {
            onSettled: () => setDeletingId(null),
          });
        }}
        deletingId={deletingId}
      />
    </div>
  );
}
