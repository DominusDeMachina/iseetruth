import { useState, useEffect } from "react";
import { X } from "lucide-react";

const MIN_WIDTH = 1280;

export function ViewportWarning() {
  const [isNarrow, setIsNarrow] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const check = () => setIsNarrow(window.innerWidth < MIN_WIDTH);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  if (!isNarrow || dismissed) return null;

  return (
    <div className="flex items-center justify-between bg-[var(--status-warning)]/15 border-t border-[var(--status-warning)]/30 px-4 py-2">
      <span className="text-xs text-[var(--status-warning)]">
        OSINT is designed for screens 1280px and wider
      </span>
      <button
        onClick={() => setDismissed(true)}
        className="ml-4 rounded p-1 text-[var(--status-warning)] hover:bg-[var(--status-warning)]/20 transition-colors"
        aria-label="Dismiss viewport warning"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
