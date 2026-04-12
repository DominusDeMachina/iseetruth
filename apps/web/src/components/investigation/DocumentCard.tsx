import { useState } from "react";
import { AlertTriangle, Eye, FileText, ImageIcon, RotateCcw, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DeleteDocumentDialog } from "./DeleteDocumentDialog";
import type { DocumentWithProgress } from "@/hooks/useDocuments";
import {
  MAX_AUTO_RETRIES,
  PROCESSING_STAGES,
  statusLabels,
  statusStyles,
} from "@/lib/document-constants";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const qualityStyles: Record<string, string> = {
  high: "bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/30",
  medium: "bg-[var(--status-warning)]/15 text-[var(--status-warning)] border-[var(--status-warning)]/30 border-dashed",
  low: "bg-[var(--status-warning)]/15 text-[var(--status-warning)] border-[var(--status-warning)]/30 border-dotted",
};

function stageIndex(status: string): number {
  return PROCESSING_STAGES.indexOf(
    status as (typeof PROCESSING_STAGES)[number],
  );
}

function isProcessing(status: string): boolean {
  return stageIndex(status) >= 0;
}

interface DocumentCardProps {
  document: DocumentWithProgress;
  onDelete: (id: string) => void;
  onViewText?: (id: string) => void;
  onRetry?: (id: string) => void;
  isDeleting?: boolean;
  isRetrying?: boolean;
}

export function DocumentCard({
  document,
  onDelete,
  onViewText,
  onRetry,
  isDeleting = false,
  isRetrying = false,
}: DocumentCardProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const processing = isProcessing(document.status);
  const currentStage = stageIndex(document.status);

  return (
    <>
      <div className="group flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-4 py-3 transition-colors hover:bg-[var(--bg-hover)]">
        {document.document_type === "image" ? (
          <ImageIcon className="size-5 shrink-0 text-[var(--text-muted)]" />
        ) : (
          <FileText className="size-5 shrink-0 text-[var(--text-muted)]" />
        )}

        <div className="min-w-0 flex-1">
          <p className="truncate font-medium text-[var(--text-primary)]">
            {document.filename}
          </p>
          <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
            <span>{formatFileSize(document.size_bytes)}</span>
            <span>&middot;</span>
            <span>{formatDate(document.created_at)}</span>
            {document.page_count != null && (
              <>
                <span>&middot;</span>
                <span>
                  {document.page_count}{" "}
                  {document.page_count === 1 ? "page" : "pages"}
                </span>
              </>
            )}
            {document.entity_count != null && (
              <>
                <span>&middot;</span>
                <span>{document.entity_count} entities</span>
              </>
            )}
            {document._chunksDone != null &&
              document._chunkCount != null &&
              document._chunkCount > 0 && (
                <>
                  <span>&middot;</span>
                  <span>
                    {document._chunksDone}/{document._chunkCount} chunks
                  </span>
                </>
              )}
          </div>
          {document.status === "failed" && document.error_message && (
            <p className="truncate text-xs text-[var(--status-error)]">
              {document.error_message}
            </p>
          )}
          {document.status === "failed" && (document.retry_count ?? 0) > 0 && (
            <p
              className={`text-xs ${(document.retry_count ?? 0) >= MAX_AUTO_RETRIES ? "text-[var(--status-warning)]" : "text-[var(--text-muted)]"}`}
            >
              {(document.retry_count ?? 0) >= MAX_AUTO_RETRIES
                ? "Max retries exceeded \u2014 manual retry available"
                : `Auto-retried ${document.retry_count}/${MAX_AUTO_RETRIES} times`}
            </p>
          )}
        </div>

        {processing && (
          <div className="flex items-center gap-1" title={statusLabels[document.status]}>
            {PROCESSING_STAGES.map((stage, i) => {
              const isDone = i < currentStage;
              const isActive = i === currentStage;
              return (
                <div
                  key={stage}
                  className={`size-1.5 rounded-full transition-colors ${
                    isDone
                      ? "bg-[var(--status-success)]"
                      : isActive
                        ? "animate-pulse bg-[var(--status-info)]"
                        : "bg-[var(--bg-hover)]"
                  }`}
                  title={statusLabels[stage]}
                />
              );
            })}
          </div>
        )}

        <Badge
          variant="outline"
          className={statusStyles[document.status] ?? ""}
        >
          {document.status === "failed" && document.error_message
            ? "Failed — Retry"
            : (statusLabels[document.status] ??
                document.status.charAt(0).toUpperCase() + document.status.slice(1))}
        </Badge>

        {document.extraction_quality && (
          <Badge
            variant="outline"
            className={qualityStyles[document.extraction_quality] ?? ""}
          >
            {document.extraction_quality === "low" && (
              <AlertTriangle className="size-3 mr-1" />
            )}
            {document.extraction_quality.charAt(0).toUpperCase() +
              document.extraction_quality.slice(1)}{" "}
            confidence
          </Badge>
        )}

        {document.status === "failed" && onRetry && (
          <Button
            variant="ghost"
            size="sm"
            className="shrink-0 gap-1 text-xs text-[var(--text-muted)] hover:text-[var(--status-warning)]"
            onClick={() => onRetry(document.id)}
            disabled={isRetrying}
            aria-label={`Retry processing ${document.filename}`}
          >
            <RotateCcw className={`size-3 ${isRetrying ? "animate-spin" : ""}`} />
            Retry
          </Button>
        )}

        {document.status === "complete" && (
          <Button
            variant="ghost"
            size="sm"
            className="shrink-0 gap-1 text-xs text-[var(--text-muted)]"
            onClick={() => onViewText?.(document.id)}
          >
            <Eye className="size-3" />
            View Text
          </Button>
        )}

        <Button
          variant="ghost"
          size="icon-xs"
          className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100 text-[var(--text-muted)] hover:text-[var(--status-error)]"
          onClick={() => setShowDeleteDialog(true)}
        >
          <Trash2 className="size-3.5" />
        </Button>
      </div>

      <DeleteDocumentDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        filename={document.filename}
        onConfirm={() => {
          onDelete(document.id);
          setShowDeleteDialog(false);
        }}
        isPending={isDeleting}
      />
    </>
  );
}
