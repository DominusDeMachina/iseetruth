import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProcessingDashboard } from "./ProcessingDashboard";
import type { DocumentResponse } from "@/hooks/useDocuments";

function makeDoc(
  overrides: Partial<DocumentResponse> & { id: string; status: string },
): DocumentResponse {
  return {
    investigation_id: "inv-1",
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

describe("ProcessingDashboard", () => {
  it("shows progress summary with correct counts", () => {
    const documents = [
      makeDoc({ id: "1", status: "complete" }),
      makeDoc({ id: "2", status: "complete" }),
      makeDoc({ id: "3", status: "extracting_text" }),
      makeDoc({ id: "4", status: "queued" }),
      makeDoc({ id: "5", status: "failed" }),
    ];

    render(
      <ProcessingDashboard
        documents={documents}
        investigationName="Test Investigation"
        isConnected={true}
        connectionError={false}
      />,
    );

    expect(screen.getByText(/5 documents/)).toBeInTheDocument();
    expect(screen.getByText(/2 complete/)).toBeInTheDocument();
    expect(screen.getByText(/1 failed/)).toBeInTheDocument();
    expect(screen.getByText(/2 remaining/)).toBeInTheDocument();
  });

  it("shows investigation name", () => {
    const documents = [makeDoc({ id: "1", status: "complete" })];
    render(
      <ProcessingDashboard
        documents={documents}
        investigationName="My Investigation"
        isConnected={false}
        connectionError={false}
      />,
    );
    expect(screen.getByText(/My Investigation/)).toBeInTheDocument();
  });

  it("shows connection error banner when connectionError is true", () => {
    const documents = [makeDoc({ id: "1", status: "extracting_text" })];
    render(
      <ProcessingDashboard
        documents={documents}
        investigationName="Test"
        isConnected={false}
        connectionError={true}
      />,
    );
    expect(
      screen.getByText(/Live updates unavailable/),
    ).toBeInTheDocument();
  });

  it("does not show connection error banner when connectionError is false", () => {
    const documents = [makeDoc({ id: "1", status: "extracting_text" })];
    render(
      <ProcessingDashboard
        documents={documents}
        investigationName="Test"
        isConnected={true}
        connectionError={false}
      />,
    );
    expect(
      screen.queryByText(/Live updates unavailable/),
    ).not.toBeInTheDocument();
  });

  it("shows all zero counts when no documents", () => {
    render(
      <ProcessingDashboard
        documents={[]}
        investigationName="Empty"
        isConnected={false}
        connectionError={false}
      />,
    );
    expect(screen.getByText(/0 documents/)).toBeInTheDocument();
  });

  it("shows live indicator when connected and processing", () => {
    const documents = [makeDoc({ id: "1", status: "extracting_text" })];
    render(
      <ProcessingDashboard
        documents={documents}
        investigationName="Test"
        isConnected={true}
        connectionError={false}
      />,
    );
    expect(screen.getByText("Live")).toBeInTheDocument();
  });
});
