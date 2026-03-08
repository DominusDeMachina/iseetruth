import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useDocumentText } from "@/hooks/useDocuments";
import { Loader2 } from "lucide-react";

interface DocumentTextViewerProps {
  investigationId: string;
  documentId: string | null;
  onOpenChange: (open: boolean) => void;
}

function parsePages(text: string) {
  const parts = text.split(/^--- Page (\d+) ---$/m);
  // parts: [textBefore, pageNum1, textAfter1, pageNum2, textAfter2, ...]
  // If the text starts with a page marker, parts[0] is ""
  const pages: { pageNumber: number; content: string }[] = [];

  // If there's text before the first page marker, treat it as page 0
  if (parts[0].trim()) {
    pages.push({ pageNumber: 1, content: parts[0].trim() });
  }

  for (let i = 1; i < parts.length; i += 2) {
    const pageNumber = parseInt(parts[i], 10);
    const content = parts[i + 1]?.trim() ?? "";
    pages.push({ pageNumber, content });
  }

  return pages;
}

export function DocumentTextViewer({
  investigationId,
  documentId,
  onOpenChange,
}: DocumentTextViewerProps) {
  const { data, isLoading, isError } = useDocumentText(investigationId, documentId);

  return (
    <Dialog open={!!documentId} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] flex flex-col bg-[var(--bg-elevated)] border-[var(--border-subtle)]">
        <DialogHeader>
          <DialogTitle className="text-[var(--text-primary)]">
            {data?.filename ?? "Document Text"}
          </DialogTitle>
          <DialogDescription className="text-[var(--text-secondary)]">
            {data?.page_count != null
              ? `${data.page_count} page${data.page_count !== 1 ? "s" : ""}`
              : "Extracted text"}
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-y-auto flex-1 min-h-0">
          {isLoading && (
            <div className="flex items-center justify-center py-12" data-testid="loading-indicator">
              <Loader2 className="h-6 w-6 animate-spin text-[var(--text-muted)]" />
              <span className="ml-2 text-sm text-[var(--text-muted)]">
                Loading text...
              </span>
            </div>
          )}

          {!isLoading && isError && (
            <div className="text-center py-12 text-[var(--status-error)]" data-testid="error-state">
              Failed to load document text. Please try again.
            </div>
          )}

          {!isLoading && !isError && (!data?.extracted_text) && (
            <div className="text-center py-12 text-[var(--text-muted)]" data-testid="empty-state">
              No text could be extracted from this document.
            </div>
          )}

          {!isLoading && !isError && data?.extracted_text && (
            <div className="space-y-4" data-testid="text-content">
              {parsePages(data.extracted_text).map((page) => (
                <div key={page.pageNumber}>
                  <div className="flex items-center gap-2 mb-2">
                    <hr className="flex-1 border-[var(--border-subtle)]" />
                    <span className="text-sm text-[var(--text-muted)] font-sans whitespace-nowrap">
                      Page {page.pageNumber}
                    </span>
                    <hr className="flex-1 border-[var(--border-subtle)]" />
                  </div>
                  <p className="font-serif text-base text-[var(--text-primary)] whitespace-pre-wrap">
                    {page.content}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
