import { lazy, Suspense, useState, useCallback, useRef } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, RefreshCw, FileText } from "lucide-react";
import { useInvestigation } from "@/hooks/useInvestigations";
import {
  useDocuments,
  useUploadDocuments,
  useDeleteDocument,
} from "@/hooks/useDocuments";
import { useSSE } from "@/hooks/useSSE";
import { ACTIVE_STATUSES, statusLabels } from "@/lib/document-constants";
import { useEntities } from "@/hooks/useEntities";
import { DocumentUploadZone } from "@/components/investigation/DocumentUploadZone";
import { DocumentList } from "@/components/investigation/DocumentList";
import { DocumentTextViewer } from "@/components/investigation/DocumentTextViewer";
import { ProcessingDashboard } from "@/components/investigation/ProcessingDashboard";
import { EntitySummaryBar } from "@/components/investigation/EntitySummaryBar";
import { SplitView } from "@/components/layout/SplitView";
import { QAPanel } from "@/components/qa/QAPanel";
import { CitationModal } from "@/components/qa/CitationModal";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import type { Citation, ConversationEntry, EntityReference } from "@/components/qa/types";

const GraphCanvas = lazy(() =>
  import("@/components/graph/GraphCanvas").then((m) => ({
    default: m.GraphCanvas,
  })),
);

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
  const [docsDialogOpen, setDocsDialogOpen] = useState(false);
  const [prefillQuestion, setPrefillQuestion] = useState<string | undefined>();
  const [highlightEntities, setHighlightEntities] = useState<string[]>([]);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [activeCitationEntities, setActiveCitationEntities] = useState<EntityReference[]>([]);
  const [citationNotFound, setCitationNotFound] = useState(false);
  const conversationRef = useRef<ConversationEntry[]>([]);

  const documents = documentsData?.items ?? [];
  const hasProcessing = documents.some((d) => ACTIVE_STATUSES.has(d.status));
  const activeDoc = documents.find((d) => ACTIVE_STATUSES.has(d.status));
  const activeStageLabel = activeDoc ? (statusLabels[activeDoc.status] ?? activeDoc.status) : undefined;

  const { data: entitiesData } = useEntities(id, undefined, hasProcessing);
  // Connect SSE when upload starts (not after it completes) so the connection
  // is established before Celery workers publish processing events
  const sseEnabled = hasProcessing || uploadMutation.isPending;
  const { isConnected, connectionError, discoveredEntities } = useSSE(id, sseEnabled);

  const handleConversationUpdate = useCallback(
    (entries: ConversationEntry[]) => {
      conversationRef.current = entries;
    },
    [],
  );

  const handleEntityClick = useCallback((entityName: string) => {
    setHighlightEntities([entityName]);
  }, []);

  const handleCitationClick = useCallback((citation: Citation | number) => {
    if (typeof citation === "number") {
      // Resolve citation number to full Citation object from conversation entries
      const entries = conversationRef.current;
      for (let i = entries.length - 1; i >= 0; i--) {
        const found = entries[i].citations.find(
          (c) => c.citation_number === citation,
        );
        if (found) {
          setActiveCitationEntities(entries[i].entitiesMentioned);
          setActiveCitation(found);
          return;
        }
      }
      // Citation not found — show user feedback
      setCitationNotFound(true);
      setTimeout(() => setCitationNotFound(false), 4000);
    } else {
      // Direct Citation object — find matching entry for entity context
      const entries = conversationRef.current;
      for (let i = entries.length - 1; i >= 0; i--) {
        if (entries[i].citations.some((c) => c.chunk_id === citation.chunk_id)) {
          setActiveCitationEntities(entries[i].entitiesMentioned);
          break;
        }
      }
      setActiveCitation(citation);
    }
  }, []);

  const handleCitationEntityClick = useCallback(
    (entityName: string) => {
      setActiveCitation(null);
      setActiveCitationEntities([]);
      // Delay entity highlight to allow modal close animation
      setTimeout(() => {
        setHighlightEntities([entityName]);
      }, 150);
    },
    [],
  );

  const handleAskAboutEntity = useCallback((entityName: string) => {
    setPrefillQuestion(`What connections does ${entityName} have?`);
  }, []);

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

  const hasEntities = (entitiesData?.items?.length ?? 0) > 0;

  const documentManagementContent = (
    <div className="flex flex-col gap-6 overflow-y-auto h-full p-1">
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
          discoveredEntities={discoveredEntities}
          extractedEntities={entitiesData?.items}
        />
      )}

      {entitiesData?.summary && (
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

  // Split view when entities exist: QAPanel (left) + GraphCanvas (right)
  if (hasEntities) {
    const header = (
      <div className="flex items-start justify-between">
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
        <button
          onClick={() => setDocsDialogOpen(true)}
          className="relative shrink-0 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
          title="Manage documents"
          aria-label="Manage documents"
        >
          <FileText className="size-4" />
          {hasProcessing && (
            <span
              className="absolute -top-1 -right-1 size-2.5 rounded-full bg-[var(--status-info)] animate-pulse"
              title={activeStageLabel}
            />
          )}
        </button>
      </div>
    );

    return (
      <div className="flex flex-col h-full">
        <div className="shrink-0 px-1 pb-4">{header}</div>
        <div className="flex-1 min-h-0">
          <SplitView
            left={
              <QAPanel
                investigationId={id}
                onEntityClick={handleEntityClick}
                onCitationClick={handleCitationClick}
                prefillQuestion={prefillQuestion}
                onQueryStart={() => setHighlightEntities([])}
                onConversationUpdate={handleConversationUpdate}
                disabled={hasProcessing}
                disabledReason="Documents are still processing..."
              />
            }
            right={
              <Suspense
                fallback={
                  <div className="flex h-full items-center justify-center">
                    <RefreshCw className="size-6 animate-spin text-[var(--text-muted)]" />
                  </div>
                }
              >
                <GraphCanvas
                  investigationId={id}
                  documents={documentsData?.items}
                  onAskAboutEntity={handleAskAboutEntity}
                  highlightEntities={highlightEntities}
                  onHighlightClear={() => setHighlightEntities([])}
                />
              </Suspense>
            }
          />
        </div>

        {/* Document management dialog */}
        <Dialog open={docsDialogOpen} onOpenChange={setDocsDialogOpen}>
          <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Documents</DialogTitle>
              <DialogDescription>
                Upload and manage documents for this investigation.
              </DialogDescription>
            </DialogHeader>
            {documentManagementContent}
          </DialogContent>
        </Dialog>

        {/* Citation modal */}
        <CitationModal
          citation={activeCitation}
          investigationId={id}
          open={!!activeCitation}
          onOpenChange={(open) => {
            if (!open) {
              setActiveCitation(null);
              setActiveCitationEntities([]);
            }
          }}
          onEntityClick={handleCitationEntityClick}
          entities={activeCitationEntities}
        />

        {/* Citation not found notification */}
        {citationNotFound && (
          <div className="fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-lg bg-[var(--status-error)] px-4 py-2 text-sm text-white shadow-lg">
            Citation not found — the answer may have changed.
          </div>
        )}
      </div>
    );
  }

  // No entities yet — full-width document management layout
  const header = (
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
  );

  return (
    <div className="flex flex-col gap-6">
      {header}

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
          discoveredEntities={discoveredEntities}
          extractedEntities={entitiesData?.items}
        />
      )}

      {entitiesData?.summary && (
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
