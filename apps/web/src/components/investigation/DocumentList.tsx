import { DocumentCard } from "./DocumentCard";
import type { DocumentWithProgress } from "@/hooks/useDocuments";

interface DocumentListProps {
  documents: DocumentWithProgress[];
  isLoading: boolean;
  onDeleteDocument: (id: string) => void;
  onViewText?: (id: string) => void;
  deletingId?: string | null;
}

export function DocumentList({
  documents,
  isLoading,
  onDeleteDocument,
  onViewText,
  deletingId,
}: DocumentListProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 animate-pulse rounded-lg bg-[var(--bg-hover)]"
          />
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col gap-2">
      {documents.map((doc) => (
        <DocumentCard
          key={doc.id}
          document={doc}
          onDelete={onDeleteDocument}
          onViewText={onViewText}
          isDeleting={deletingId === doc.id}
        />
      ))}
    </div>
  );
}
