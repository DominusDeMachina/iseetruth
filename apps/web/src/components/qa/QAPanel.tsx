import { useCallback } from "react";
import { useQueryStream } from "@/hooks/useQueryStream";
import { QueryInput } from "./QueryInput";
import { AnswerPanel } from "./AnswerPanel";
import { SuggestedQuestions } from "./SuggestedQuestions";
import type { Citation } from "./types";

interface QAPanelProps {
  investigationId: string;
  onEntityClick: (entityName: string) => void;
  onCitationClick: (citation: Citation | number) => void;
  prefillQuestion?: string;
  onQueryStart?: () => void;
}

export function QAPanel({
  investigationId,
  onEntityClick,
  onCitationClick,
  prefillQuestion,
  onQueryStart,
}: QAPanelProps) {
  const {
    queryStatus,
    conversationEntries,
    currentStreamingText,
    submitQuery,
  } = useQueryStream(investigationId);

  const handleSubmit = useCallback(
    (question: string) => {
      onQueryStart?.();
      submitQuery(question);
    },
    [submitQuery, onQueryStart],
  );

  // Get suggested followups from the last completed entry
  const lastCompleted = [...conversationEntries]
    .reverse()
    .find((e) => e.status === "complete");
  const suggestedQuestions = lastCompleted?.suggestedFollowups ?? [];
  const noResults = lastCompleted?.noResults ?? false;

  const hasConversation = conversationEntries.length > 0;

  return (
    <div className="flex flex-col h-full bg-[var(--bg-secondary)]">
      {/* Conversation area */}
      {hasConversation ? (
        <AnswerPanel
          conversation={conversationEntries}
          streamingText={currentStreamingText}
          status={queryStatus}
          onCitationClick={onCitationClick}
          onEntityClick={onEntityClick}
          onRetry={handleSubmit}
        />
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
          <p
            className="text-lg font-medium text-[var(--text-primary)] mb-2"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            Ask about your investigation
          </p>
          <p className="text-sm text-[var(--text-secondary)] mb-6 max-w-sm">
            Ask questions in natural language. Answers are grounded in your
            uploaded documents and knowledge graph.
          </p>
          <div className="space-y-2 w-full max-w-sm">
            {[
              "How are the entities in your documents connected?",
              "What are the key relationships in this investigation?",
            ].map((q) => (
              <button
                key={q}
                onClick={() => handleSubmit(q)}
                className="w-full text-left rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] bg-[var(--bg-elevated)] hover:bg-[var(--bg-hover)] transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Suggested follow-ups */}
      {hasConversation && (
        <SuggestedQuestions
          questions={suggestedQuestions}
          status={queryStatus}
          noResults={noResults}
          onQuestionClick={handleSubmit}
        />
      )}

      {/* Input */}
      <QueryInput
        onSubmit={handleSubmit}
        status={queryStatus}
        prefillQuestion={prefillQuestion}
      />
    </div>
  );
}
