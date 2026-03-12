import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { DocumentList } from "./DocumentList";
import type { DocumentResponse } from "@/hooks/useDocuments";

const mockDocument: DocumentResponse = {
  id: "11111111-1111-1111-1111-111111111111",
  investigation_id: "22222222-2222-2222-2222-222222222222",
  filename: "test-report.pdf",
  size_bytes: 2560000,
  sha256_checksum: "a".repeat(64),
  status: "queued",
  page_count: 5,
  extracted_text: null,
  error_message: null,
  extraction_quality: null,
  created_at: "2026-03-08T12:00:00Z",
  updated_at: "2026-03-08T12:00:00Z",
};

describe("DocumentList", () => {
  it("renders document cards", () => {
    render(
      <DocumentList
        documents={[mockDocument]}
        isLoading={false}
        onDeleteDocument={vi.fn()}
      />,
    );
    expect(screen.getByText("test-report.pdf")).toBeInTheDocument();
  });

  it("shows nothing when empty", () => {
    const { container } = render(
      <DocumentList
        documents={[]}
        isLoading={false}
        onDeleteDocument={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows loading skeleton", () => {
    const { container } = render(
      <DocumentList
        documents={[]}
        isLoading={true}
        onDeleteDocument={vi.fn()}
      />,
    );
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBe(3);
  });
});
