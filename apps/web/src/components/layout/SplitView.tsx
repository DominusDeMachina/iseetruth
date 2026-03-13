import { useState, useCallback, useRef, type ReactNode } from "react";

interface SplitViewProps {
  left: ReactNode;
  right: ReactNode;
  defaultLeftPercent?: number;
  minPercent?: number;
}

export function SplitView({
  left,
  right,
  defaultLeftPercent = 40,
  minPercent = 25,
}: SplitViewProps) {
  const [leftPercent, setLeftPercent] = useState(defaultLeftPercent);
  const containerRef = useRef<HTMLDivElement>(null);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      const container = containerRef.current;
      if (!container) return;

      const onPointerMove = (moveEvent: PointerEvent) => {
        const rect = container.getBoundingClientRect();
        const x = moveEvent.clientX - rect.left;
        const percent = (x / rect.width) * 100;
        setLeftPercent(Math.min(100 - minPercent, Math.max(minPercent, percent)));
      };

      const onPointerUp = () => {
        document.removeEventListener("pointermove", onPointerMove);
        document.removeEventListener("pointerup", onPointerUp);
      };

      document.addEventListener("pointermove", onPointerMove);
      document.addEventListener("pointerup", onPointerUp);
    },
    [minPercent],
  );

  return (
    <div
      ref={containerRef}
      className="grid h-full"
      style={{ gridTemplateColumns: `${leftPercent}% 4px 1fr` }}
    >
      <div className="overflow-hidden">{left}</div>
      <div
        className="cursor-col-resize bg-[var(--border-subtle)] hover:bg-[var(--border-strong)] transition-colors"
        onPointerDown={handlePointerDown}
      />
      <div className="overflow-hidden">{right}</div>
    </div>
  );
}
