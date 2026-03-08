import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DocumentCard } from "./DocumentCard";
import type { DocumentResponse } from "@/hooks/useDocuments";

const mockDocument: DocumentResponse = {
  id: "11111111-1111-1111-1111-111111111111",
  investigation_id: "22222222-2222-2222-2222-222222222222",
  filename: "evidence-report.pdf",
  size_bytes: 2560000,
  sha256_checksum: "a".repeat(64),
  status: "queued",
  page_count: 12,
  extracted_text: null,
  error_message: null,
  created_at: "2026-03-08T12:00:00Z",
  updated_at: "2026-03-08T12:00:00Z",
};

describe("DocumentCard", () => {
  it("renders card data", () => {
    render(<DocumentCard document={mockDocument} onDelete={vi.fn()} />);
    expect(screen.getByText("evidence-report.pdf")).toBeInTheDocument();
    expect(screen.getByText("2.4 MB")).toBeInTheDocument();
    expect(screen.getByText("12 pages")).toBeInTheDocument();
  });

  it("shows delete confirmation flow", () => {
    const onDelete = vi.fn();
    render(<DocumentCard document={mockDocument} onDelete={onDelete} />);

    // Click the delete button (trash icon)
    const deleteBtn = screen.getByRole("button");
    fireEvent.click(deleteBtn);

    // Confirmation dialog should appear
    expect(screen.getByText("Delete Document?")).toBeInTheDocument();
    expect(
      screen.getByText(
        /evidence-report\.pdf.*will be permanently removed/,
      ),
    ).toBeInTheDocument();

    // Click confirm
    fireEvent.click(screen.getByText("Delete"));
    expect(onDelete).toHaveBeenCalledWith(mockDocument.id);
  });

  it("displays status badge", () => {
    render(<DocumentCard document={mockDocument} onDelete={vi.fn()} />);
    expect(screen.getByText("Queued")).toBeInTheDocument();
  });

  it("displays complete status badge", () => {
    const completeDoc = { ...mockDocument, status: "complete" };
    render(<DocumentCard document={completeDoc} onDelete={vi.fn()} />);
    expect(screen.getByText("Complete")).toBeInTheDocument();
  });

  it("displays failed status badge", () => {
    const failedDoc = { ...mockDocument, status: "failed" };
    render(<DocumentCard document={failedDoc} onDelete={vi.fn()} />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("displays extracting_text status as 'Extracting Text'", () => {
    const extractingDoc = { ...mockDocument, status: "extracting_text" };
    render(<DocumentCard document={extractingDoc} onDelete={vi.fn()} />);
    expect(screen.getByText("Extracting Text")).toBeInTheDocument();
  });

  it("shows enabled 'View Text' button for completed documents", () => {
    const completeDoc = { ...mockDocument, status: "complete" };
    render(<DocumentCard document={completeDoc} onDelete={vi.fn()} />);
    const viewTextBtn = screen.getByRole("button", { name: /view text/i });
    expect(viewTextBtn).toBeInTheDocument();
    expect(viewTextBtn).not.toBeDisabled();
  });

  it("fires onViewText when 'View Text' button is clicked", () => {
    const completeDoc = { ...mockDocument, status: "complete" };
    const onViewText = vi.fn();
    render(
      <DocumentCard document={completeDoc} onDelete={vi.fn()} onViewText={onViewText} />,
    );
    const viewTextBtn = screen.getByRole("button", { name: /view text/i });
    fireEvent.click(viewTextBtn);
    expect(onViewText).toHaveBeenCalledWith(completeDoc.id);
  });

  it("does not show 'View Text' button for non-complete documents", () => {
    render(<DocumentCard document={mockDocument} onDelete={vi.fn()} />);
    expect(
      screen.queryByRole("button", { name: /view text/i }),
    ).not.toBeInTheDocument();
  });
});
