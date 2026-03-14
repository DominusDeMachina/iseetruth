export type QueryStatus =
  | "idle"
  | "translating"
  | "searching"
  | "streaming"
  | "complete"
  | "error";

export interface Citation {
  citation_number: number;
  document_id: string;
  document_filename: string;
  chunk_id: string;
  page_start: number;
  page_end: number;
  text_excerpt: string;
}

export interface EntityReference {
  entity_id: string;
  name: string;
  type: string;
}

export interface ConversationEntry {
  id: string;
  question: string;
  answer: string | null;
  citations: Citation[];
  entitiesMentioned: EntityReference[];
  suggestedFollowups: string[];
  noResults: boolean;
  status: "streaming" | "complete" | "error";
  error?: string;
}
