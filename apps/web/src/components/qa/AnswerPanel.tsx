import { useEffect, useRef, useCallback, memo, type ReactNode } from "react";
import { RefreshCw } from "lucide-react";
import { ENTITY_COLORS } from "@/lib/entity-constants";
import type {
  ConversationEntry,
  QueryStatus,
  Citation,
  EntityReference,
} from "./types";

function parseAnswerText(
  text: string,
  entities: EntityReference[],
  citations: Citation[],
  onCitationClick: (citation: Citation | number) => void,
  onEntityClick: (entityName: string) => void,
): ReactNode[] {
  const CITATION_REGEX = /\[(\d+)\]/g;
  const ENTITY_REGEX = /\*\*([^*]+)\*\*/g;

  const parts: ReactNode[] = [];
  let keyCounter = 0;

  // First pass: split text by citations
  const segments: Array<
    { type: "text"; content: string } | { type: "citation"; num: number }
  > = [];
  let lastIdx = 0;
  let citMatch;

  while ((citMatch = CITATION_REGEX.exec(text)) !== null) {
    if (citMatch.index > lastIdx) {
      segments.push({
        type: "text",
        content: text.slice(lastIdx, citMatch.index),
      });
    }
    segments.push({ type: "citation", num: parseInt(citMatch[1], 10) });
    lastIdx = citMatch.index + citMatch[0].length;
  }
  if (lastIdx < text.length) {
    segments.push({ type: "text", content: text.slice(lastIdx) });
  }

  // Second pass: render segments, parsing entities within text segments
  for (const seg of segments) {
    if (seg.type === "citation") {
      const cit = citations.find((c) => c.citation_number === seg.num);
      const ariaLabel = cit
        ? `Source: ${cit.document_filename}, page ${cit.page_start}`
        : `Source ${seg.num}`;
      parts.push(
        <sup key={`cite-${keyCounter++}`} className="ml-0.5">
          <a
            href={`#citation-${seg.num}`}
            onClick={(e) => {
              e.preventDefault();
              onCitationClick(seg.num);
            }}
            className="cursor-pointer text-[var(--status-info)] hover:underline"
            aria-label={ariaLabel}
          >
            {seg.num}
          </a>
        </sup>,
      );
    } else {
      ENTITY_REGEX.lastIndex = 0;
      let entLastIdx = 0;
      let entMatch;

      while ((entMatch = ENTITY_REGEX.exec(seg.content)) !== null) {
        if (entMatch.index > entLastIdx) {
          parts.push(seg.content.slice(entLastIdx, entMatch.index));
        }
        const name = entMatch[1];
        const entity = entities.find(
          (e) => e.name.toLowerCase() === name.toLowerCase(),
        );
        const color = entity
          ? ENTITY_COLORS[entity.type] ?? "var(--text-primary)"
          : "var(--text-primary)";
        parts.push(
          <a
            key={`entity-${keyCounter++}`}
            onClick={() => onEntityClick(name)}
            className="cursor-pointer font-semibold hover:underline"
            style={{ color, textDecorationColor: color }}
            aria-label={`Explore ${name} in graph`}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter") onEntityClick(name);
            }}
          >
            {name}
          </a>,
        );
        entLastIdx = entMatch.index + entMatch[0].length;
      }

      if (entLastIdx < seg.content.length) {
        parts.push(seg.content.slice(entLastIdx));
      }
    }
  }

  return parts;
}

interface AnswerEntryProps {
  entry: ConversationEntry;
  onCitationClick: (citation: Citation | number) => void;
  onEntityClick: (entityName: string) => void;
  onRetry?: (question: string) => void;
}

const AnswerEntry = memo(function AnswerEntry({
  entry,
  onCitationClick,
  onEntityClick,
  onRetry,
}: AnswerEntryProps) {
  const parsed = entry.answer
    ? parseAnswerText(
        entry.answer,
        entry.entitiesMentioned,
        entry.citations,
        onCitationClick,
        onEntityClick,
      )
    : null;

  return (
    <div className="space-y-2">
      {/* User question */}
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-lg bg-[var(--bg-hover)] px-3 py-2 text-sm text-[var(--text-primary)]">
          {entry.question}
        </div>
      </div>

      {/* Answer */}
      {entry.status === "error" && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-[var(--status-error)]">
            {entry.error ?? "An error occurred"}
          </span>
          {onRetry && (
            <button
              onClick={() => onRetry(entry.question)}
              className="rounded px-2 py-0.5 text-xs text-[var(--text-primary)] bg-[var(--bg-elevated)] hover:bg-[var(--bg-hover)] transition-colors"
            >
              Try again
            </button>
          )}
        </div>
      )}

      {entry.noResults && entry.status === "complete" && (
        <div className="text-sm text-[var(--text-secondary)]">
          No connection found in your documents. Try rephrasing your question or
          explore the graph manually.
        </div>
      )}

      {parsed && !entry.noResults && (
        <div
          className="max-w-[65ch] text-[15px] leading-[1.8] text-[var(--text-primary)]"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          {parsed}
        </div>
      )}

      {/* Citation footer */}
      {entry.citations.length > 0 && (
        <div className="mt-2 space-y-0.5 border-t border-[var(--border-subtle)] pt-2">
          {entry.citations.map((cit) => (
            <button
              key={cit.citation_number}
              onClick={() => onCitationClick(cit)}
              className="block text-xs text-[var(--text-secondary)] hover:text-[var(--status-info)] hover:underline transition-colors"
            >
              [{cit.citation_number}] {cit.document_filename}
              {cit.page_start ? `, page ${cit.page_start}` : ""}
            </button>
          ))}
        </div>
      )}
    </div>
  );
});

interface AnswerPanelProps {
  conversation: ConversationEntry[];
  streamingText: string;
  status: QueryStatus;
  onCitationClick: (citation: Citation | number) => void;
  onEntityClick: (entityName: string) => void;
  onRetry?: (question: string) => void;
}

export function AnswerPanel({
  conversation,
  streamingText,
  status,
  onCitationClick,
  onEntityClick,
  onRetry,
}: AnswerPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const userScrolledUp = useRef(false);

  // Auto-scroll logic
  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    userScrolledUp.current = !atBottom;
  }, []);

  useEffect(() => {
    if (!userScrolledUp.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [conversation, streamingText]);

  // Status message for current query
  const statusMessage =
    status === "translating"
      ? "Translating your question..."
      : status === "searching"
        ? "Searching knowledge graph and documents..."
        : status === "streaming"
          ? "Streaming answer..."
          : null;

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-4 py-4 space-y-6"
      aria-live="polite"
    >
      {conversation.map((entry) => {
        if (entry.status === "streaming") {
          // Render streaming entry inline
          return (
            <div key={entry.id} className="space-y-2">
              {/* User question */}
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-lg bg-[var(--bg-hover)] px-3 py-2 text-sm text-[var(--text-primary)]">
                  {entry.question}
                </div>
              </div>

              {/* Status indicator */}
              {statusMessage && (
                <p className="text-xs text-[var(--text-secondary)] flex items-center gap-1.5">
                  <RefreshCw className="size-3 animate-spin" />
                  {statusMessage}
                </p>
              )}

              {/* Streaming text */}
              {streamingText && (
                <div
                  className="max-w-[65ch] text-[15px] leading-[1.8] text-[var(--text-primary)]"
                  style={{ fontFamily: "var(--font-serif)" }}
                >
                  {streamingText}
                  <span className="inline-block w-[2px] h-[1em] bg-[var(--text-primary)] align-text-bottom animate-pulse ml-0.5" />
                </div>
              )}
            </div>
          );
        }

        return (
          <AnswerEntry
            key={entry.id}
            entry={entry}
            onCitationClick={onCitationClick}
            onEntityClick={onEntityClick}
            onRetry={onRetry}
          />
        );
      })}

      <div ref={bottomRef} />
    </div>
  );
}
