import { useState, useRef, useEffect, useCallback } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { QueryStatus } from "./types";

interface QueryInputProps {
  onSubmit: (question: string) => void;
  status: QueryStatus;
  prefillQuestion?: string;
}

export function QueryInput({
  onSubmit,
  status,
  prefillQuestion,
}: QueryInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isDisabled =
    status === "translating" ||
    status === "searching" ||
    status === "streaming";

  // Auto-resize textarea
  const resize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 150)}px`;
  }, []);

  useEffect(() => {
    resize();
  }, [value, resize]);

  // Handle prefillQuestion
  useEffect(() => {
    if (prefillQuestion) {
      setValue(prefillQuestion);
    }
  }, [prefillQuestion]);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isDisabled) return;
    onSubmit(trimmed);
    setValue("");
  }, [value, isDisabled, onSubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <div className="flex items-end gap-2 border-t border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-3">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isDisabled}
        placeholder="Ask a question about your investigation..."
        aria-label="Ask a question about your investigation"
        rows={1}
        className="flex-1 resize-none rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-2 text-[15px] leading-relaxed text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:outline-none disabled:opacity-50"
        style={{ fontFamily: "var(--font-serif)" }}
      />
      <Button
        size="icon"
        onClick={handleSubmit}
        disabled={isDisabled || !value.trim()}
        aria-label="Send question"
        className="shrink-0"
      >
        <Send className="size-4" />
      </Button>
    </div>
  );
}
