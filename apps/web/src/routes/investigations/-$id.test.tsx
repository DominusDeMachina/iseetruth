import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProcessingDashboard } from "@/components/investigation/ProcessingDashboard";
import type { DocumentListResponse } from "@/hooks/useDocuments";

function makeDoc(
  overrides: Partial<DocumentListResponse["items"][0]> & {
    id: string;
    status: string;
  },
): DocumentListResponse["items"][0] {
  return {
    investigation_id: "inv-123",
    filename: `file-${overrides.id}.pdf`,
    size_bytes: 1024,
    sha256_checksum: "abc",
    page_count: null,
    extracted_text: null,
    error_message: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("Investigation Detail Page — SSE Integration", () => {
  it("shows Live indicator and progress when connected with processing docs", () => {
    const docs = [
      makeDoc({ id: "1", status: "extracting_text" }),
      makeDoc({ id: "2", status: "complete" }),
      makeDoc({ id: "3", status: "failed" }),
      makeDoc({ id: "4", status: "queued" }),
    ];

    renderWithQuery(
      <ProcessingDashboard
        documents={docs}
        investigationName="Test Investigation"
        isConnected={true}
        connectionError={false}
      />,
    );

    expect(screen.getByText(/4 documents/)).toBeInTheDocument();
    expect(screen.getByText(/1 complete/)).toBeInTheDocument();
    expect(screen.getByText(/1 failed/)).toBeInTheDocument();
    expect(screen.getByText(/2 remaining/)).toBeInTheDocument();
    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("hides Live indicator when disconnected even with processing docs", () => {
    const docs = [makeDoc({ id: "1", status: "extracting_text" })];

    renderWithQuery(
      <ProcessingDashboard
        documents={docs}
        investigationName="Test"
        isConnected={false}
        connectionError={false}
      />,
    );

    expect(screen.queryByText("Live")).not.toBeInTheDocument();
  });

  it("hides Live indicator when connected but all docs terminal", () => {
    const docs = [
      makeDoc({ id: "1", status: "complete" }),
      makeDoc({ id: "2", status: "failed" }),
    ];

    renderWithQuery(
      <ProcessingDashboard
        documents={docs}
        investigationName="Test"
        isConnected={true}
        connectionError={false}
      />,
    );

    expect(screen.queryByText("Live")).not.toBeInTheDocument();
  });

  it("shows degraded banner with connectionError and no Live indicator", () => {
    const docs = [makeDoc({ id: "1", status: "extracting_text" })];

    renderWithQuery(
      <ProcessingDashboard
        documents={docs}
        investigationName="Test"
        isConnected={false}
        connectionError={true}
      />,
    );

    expect(
      screen.getByText(/Live updates unavailable/),
    ).toBeInTheDocument();
    expect(screen.queryByText("Live")).not.toBeInTheDocument();
  });
});
