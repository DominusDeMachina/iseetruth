import type { QueryStatus } from "./types";

interface SuggestedQuestionsProps {
  questions: string[];
  status: QueryStatus;
  noResults: boolean;
  onQuestionClick: (question: string) => void;
}

export function SuggestedQuestions({
  questions,
  status,
  noResults,
  onQuestionClick,
}: SuggestedQuestionsProps) {
  if (noResults || questions.length === 0) return null;

  const isLoading = status === "streaming" || status === "searching";

  if (isLoading) {
    return (
      <div className="px-4 pb-2 space-y-2" data-testid="suggested-skeleton">
        {[1, 2].map((i) => (
          <div
            key={i}
            className="h-10 animate-pulse rounded-lg bg-[var(--bg-elevated)]"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="px-4 pb-2 space-y-1.5">
      <p className="text-xs font-medium text-[var(--text-muted)]">
        Follow-up questions
      </p>
      <ul className="space-y-1" role="list">
        {questions.map((q) => (
          <li key={q}>
            <button
              onClick={() => onQuestionClick(q)}
              onKeyDown={(e) => {
                if (e.key === "Enter") onQuestionClick(q);
              }}
              className="w-full text-left rounded-lg px-3 py-2 text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
            >
              {q}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
