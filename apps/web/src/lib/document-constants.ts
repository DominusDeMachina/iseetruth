/** Document statuses that indicate active processing (not terminal). */
export const ACTIVE_STATUSES = new Set([
  "queued",
  "extracting_text",
  "chunking",
  "chunking_complete",
  "extracting_entities",
  "embedding",
]);

export const PROCESSING_STAGES = [
  "extracting_text",
  "chunking",
  "extracting_entities",
  "embedding",
] as const;

export const statusLabels: Record<string, string> = {
  queued: "Queued",
  extracting_text: "Extracting Text",
  chunking: "Chunking",
  chunking_complete: "Chunking Complete",
  extracting_entities: "Extracting Entities",
  embedding: "Generating Embeddings",
  complete: "Complete",
  failed: "Failed",
};

export const statusStyles: Record<string, string> = {
  queued:
    "bg-[var(--status-info)]/15 text-[var(--status-info)] border-[var(--status-info)]/30",
  extracting_text:
    "bg-[var(--status-info)]/15 text-[var(--status-info)] border-[var(--status-info)]/30",
  chunking:
    "bg-[var(--status-info)]/15 text-[var(--status-info)] border-[var(--status-info)]/30",
  chunking_complete:
    "bg-[var(--status-info)]/15 text-[var(--status-info)] border-[var(--status-info)]/30",
  extracting_entities:
    "bg-[var(--status-info)]/15 text-[var(--status-info)] border-[var(--status-info)]/30",
  embedding:
    "bg-[var(--status-info)]/15 text-[var(--status-info)] border-[var(--status-info)]/30",
  complete:
    "bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/30",
  failed:
    "bg-[var(--status-error)]/15 text-[var(--status-error)] border-[var(--status-error)]/30",
};
