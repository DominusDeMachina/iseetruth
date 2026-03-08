import { useState } from "react";
import { FileText, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DeleteDocumentDialog } from "./DeleteDocumentDialog";
import type { DocumentResponse } from "@/hooks/useDocuments";

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

const statusStyles: Record<string, string> = {
  queued: "bg-[var(--status-info)]/15 text-[var(--status-info)] border-[var(--status-info)]/30",
  extracting_text: "bg-[var(--status-info)]/15 text-[var(--status-info)] border-[var(--status-info)]/30",
  complete: "bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/30",
  failed: "bg-[var(--status-error)]/15 text-[var(--status-error)] border-[var(--status-error)]/30",
};

const statusLabels: Record<string, string> = {
  queued: "Queued",
  extracting_text: "Extracting Text",
  complete: "Complete",
  failed: "Failed",
};

interface DocumentCardProps {
  document: DocumentResponse;
  onDelete: (id: string) => void;
  isDeleting?: boolean;
}

export function DocumentCard({
  document,
  onDelete,
  isDeleting = false,
}: DocumentCardProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  return (
    <>
      <div className="group flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-4 py-3 transition-colors hover:bg-[var(--bg-hover)]">
        <FileText className="size-5 shrink-0 text-[var(--text-muted)]" />

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
                  {document.page_count} {document.page_count === 1 ? "page" : "pages"}
                </span>
              </>
            )}
          </div>
        </div>

        <Badge
          variant="outline"
          className={statusStyles[document.status] ?? ""}
        >
          {statusLabels[document.status] ?? document.status.charAt(0).toUpperCase() + document.status.slice(1)}
        </Badge>

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
