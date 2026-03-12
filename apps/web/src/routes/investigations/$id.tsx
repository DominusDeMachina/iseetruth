import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { useInvestigation } from "@/hooks/useInvestigations";
import {
  useDocuments,
  useUploadDocuments,
  useDeleteDocument,
} from "@/hooks/useDocuments";
import { useSSE } from "@/hooks/useSSE";
import { useEntities } from "@/hooks/useEntities";
import { DocumentUploadZone } from "@/components/investigation/DocumentUploadZone";
import { DocumentList } from "@/components/investigation/DocumentList";
import { DocumentTextViewer } from "@/components/investigation/DocumentTextViewer";
import { ProcessingDashboard } from "@/components/investigation/ProcessingDashboard";
import { EntitySummaryBar } from "@/components/investigation/EntitySummaryBar";

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
  const [viewingDocumentId, setViewingDocumentId] = useState<string | null>(null);

  const { data: entitiesData } = useEntities(id);

  const documents = documentsData?.items ?? [];
  const hasCompleted = documents.some((d) => d.status === "complete");
  const hasProcessing = documents.some(
    (d) => d.status === "queued" || d.status === "extracting_text",
  );
  // Connect SSE when upload starts (not after it completes) so the connection
  // is established before Celery workers publish processing events
  const sseEnabled = hasProcessing || uploadMutation.isPending;
  const { isConnected, connectionError } = useSSE(id, sseEnabled);

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

      {documents.length > 0 && (
        <ProcessingDashboard
          documents={documents}
          investigationName={investigation.name}
          isConnected={isConnected}
          connectionError={connectionError}
        />
      )}

      {hasCompleted && entitiesData?.summary && (
        <EntitySummaryBar summary={entitiesData.summary} />
      )}

      <DocumentList
        documents={documents}
        isLoading={isLoadingDocs}
        onDeleteDocument={(docId) => {
          setDeletingId(docId);
          deleteMutation.mutate(docId, {
            onSettled: () => setDeletingId(null),
          });
        }}
        onViewText={(docId) => setViewingDocumentId(docId)}
        deletingId={deletingId}
      />

      <DocumentTextViewer
        investigationId={id}
        documentId={viewingDocumentId}
        onOpenChange={(open) => {
          if (!open) setViewingDocumentId(null);
        }}
      />
    </div>
  );
}
