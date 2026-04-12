import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface PanelErrorBoundaryProps {
  panelName: string;
  children: React.ReactNode;
  onError?: (error: Error) => void;
}

interface PanelErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class PanelErrorBoundary extends React.Component<
  PanelErrorBoundaryProps,
  PanelErrorBoundaryState
> {
  constructor(props: PanelErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): PanelErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(`[${this.props.panelName}] Render error:`, error, errorInfo);
    this.props.onError?.(error);
  }

  resetError = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      const message = this.state.error?.message ?? "An unexpected error occurred";
      const truncated =
        message.length > 200 ? message.slice(0, 200) + "..." : message;

      return (
        <div
          role="alert"
          aria-live="assertive"
          className="flex h-full flex-col items-center justify-center gap-4 border-l-4 border-[var(--status-error)] bg-[var(--bg-elevated)] p-6"
        >
          <AlertTriangle className="size-8 text-[var(--status-error)]" />
          <h3 className="text-base font-semibold text-[var(--text-primary)]">
            {this.props.panelName} — Rendering error
          </h3>
          <p className="max-w-md text-center text-sm text-[var(--text-secondary)]">
            {truncated}
          </p>
          <p className="max-w-md text-center text-xs text-[var(--text-muted)]">
            Try reloading the panel, or refresh the page if the problem
            persists.
          </p>
          <button
            onClick={this.resetError}
            className="inline-flex items-center gap-2 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-4 py-2 text-sm text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
          >
            <RefreshCw className="size-3.5" />
            Reload Panel
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
