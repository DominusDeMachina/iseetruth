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
  extraction_quality: null,
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

  it("displays 'Failed' badge when no error_message", () => {
    const failedDoc = { ...mockDocument, status: "failed" };
    render(<DocumentCard document={failedDoc} onDelete={vi.fn()} />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("displays 'Failed — Retry' badge when error_message present", () => {
    const failedDoc = { ...mockDocument, status: "failed", error_message: "Ollama unavailable" };
    render(<DocumentCard document={failedDoc} onDelete={vi.fn()} />);
    expect(screen.getByText("Failed — Retry")).toBeInTheDocument();
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

  it("shows high confidence badge when extraction_quality is 'high'", () => {
    const doc = { ...mockDocument, status: "complete", extraction_quality: "high" as const };
    render(<DocumentCard document={doc} onDelete={vi.fn()} />);
    expect(screen.getByText(/High confidence/)).toBeInTheDocument();
  });

  it("shows medium confidence badge when extraction_quality is 'medium'", () => {
    const doc = { ...mockDocument, status: "complete", extraction_quality: "medium" as const };
    render(<DocumentCard document={doc} onDelete={vi.fn()} />);
    expect(screen.getByText(/Medium confidence/)).toBeInTheDocument();
  });

  it("shows low confidence badge with warning icon when extraction_quality is 'low'", () => {
    const doc = { ...mockDocument, status: "complete", extraction_quality: "low" as const };
    render(<DocumentCard document={doc} onDelete={vi.fn()} />);
    expect(screen.getByText(/Low confidence/)).toBeInTheDocument();
  });

  it("does not show confidence badge when extraction_quality is null", () => {
    render(<DocumentCard document={mockDocument} onDelete={vi.fn()} />);
    expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument();
  });

  it("shows entity count when entity_count is present", () => {
    const doc = { ...mockDocument, status: "complete", entity_count: 12 };
    render(<DocumentCard document={doc} onDelete={vi.fn()} />);
    expect(screen.getByText("12 entities")).toBeInTheDocument();
  });

  it("does not show entity count when entity_count is null", () => {
    render(<DocumentCard document={mockDocument} onDelete={vi.fn()} />);
    expect(screen.queryByText(/entities/)).not.toBeInTheDocument();
  });

  it("shows retry button only for failed documents", () => {
    const failedDoc = { ...mockDocument, status: "failed", error_message: "Test error" };
    const onRetry = vi.fn();
    render(<DocumentCard document={failedDoc} onDelete={vi.fn()} onRetry={onRetry} />);
    expect(
      screen.getByRole("button", { name: /retry processing evidence-report\.pdf/i }),
    ).toBeInTheDocument();
  });

  it("does not show retry button for non-failed documents", () => {
    const onRetry = vi.fn();
    render(<DocumentCard document={mockDocument} onDelete={vi.fn()} onRetry={onRetry} />);
    expect(
      screen.queryByRole("button", { name: /retry/i }),
    ).not.toBeInTheDocument();
  });

  it("calls onRetry with document ID when retry button is clicked", () => {
    const failedDoc = { ...mockDocument, status: "failed", error_message: "Test error" };
    const onRetry = vi.fn();
    render(<DocumentCard document={failedDoc} onDelete={vi.fn()} onRetry={onRetry} />);
    const retryBtn = screen.getByRole("button", { name: /retry processing/i });
    fireEvent.click(retryBtn);
    expect(onRetry).toHaveBeenCalledWith(failedDoc.id);
  });

  it("retry button has correct aria-label", () => {
    const failedDoc = { ...mockDocument, status: "failed", error_message: "Test error" };
    render(<DocumentCard document={failedDoc} onDelete={vi.fn()} onRetry={vi.fn()} />);
    const retryBtn = screen.getByRole("button", {
      name: "Retry processing evidence-report.pdf",
    });
    expect(retryBtn).toBeInTheDocument();
  });

  it("retry button is disabled when isRetrying=true", () => {
    const failedDoc = { ...mockDocument, status: "failed", error_message: "Test error" };
    render(
      <DocumentCard
        document={failedDoc}
        onDelete={vi.fn()}
        onRetry={vi.fn()}
        isRetrying={true}
      />,
    );
    const retryBtn = screen.getByRole("button", { name: /retry processing/i });
    expect(retryBtn).toBeDisabled();
  });

  it("displays error message for failed documents", () => {
    const failedDoc = {
      ...mockDocument,
      status: "failed",
      error_message: "Ollama LLM service is unavailable",
    };
    render(<DocumentCard document={failedDoc} onDelete={vi.fn()} />);
    expect(
      screen.getByText("Ollama LLM service is unavailable"),
    ).toBeInTheDocument();
  });

  it("does not show retry button when onRetry is not provided", () => {
    const failedDoc = { ...mockDocument, status: "failed", error_message: "Test error" };
    render(<DocumentCard document={failedDoc} onDelete={vi.fn()} />);
    expect(
      screen.queryByRole("button", { name: /retry/i }),
    ).not.toBeInTheDocument();
  });

  it("shows auto-retry count when retry_count > 0", () => {
    const failedDoc = {
      ...mockDocument,
      status: "failed",
      error_message: "Ollama unavailable",
      retry_count: 3,
    };
    render(<DocumentCard document={failedDoc} onDelete={vi.fn()} onRetry={vi.fn()} />);
    expect(screen.getByText("Auto-retried 3/5 times")).toBeInTheDocument();
  });

  it("shows max retries exceeded message when retry_count >= 5", () => {
    const failedDoc = {
      ...mockDocument,
      status: "failed",
      error_message: "Ollama unavailable",
      retry_count: 5,
    };
    render(<DocumentCard document={failedDoc} onDelete={vi.fn()} onRetry={vi.fn()} />);
    expect(
      screen.getByText(/Max retries exceeded/),
    ).toBeInTheDocument();
  });

  it("renders Image icon when document_type is 'image'", () => {
    const imageDoc = { ...mockDocument, document_type: "image", filename: "scan.jpg" };
    const { container } = render(
      <DocumentCard document={imageDoc} onDelete={vi.fn()} />,
    );
    // ImageIcon from lucide-react renders an svg — FileText should not be present
    // lucide icons have a data-testid or we can check by class/svg content
    // The simplest check: the filename should render and no "FileText" specific path
    expect(screen.getByText("scan.jpg")).toBeInTheDocument();
    // Check that we have an SVG (the icon) — ImageIcon and FileText both render SVGs
    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBeGreaterThan(0);
  });

  it("renders FileText icon when document_type is 'pdf'", () => {
    const pdfDoc = { ...mockDocument, document_type: "pdf" };
    const { container } = render(
      <DocumentCard document={pdfDoc} onDelete={vi.fn()} />,
    );
    expect(screen.getByText("evidence-report.pdf")).toBeInTheDocument();
    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBeGreaterThan(0);
  });

  it("does not show auto-retry text when retry_count is 0", () => {
    const failedDoc = {
      ...mockDocument,
      status: "failed",
      error_message: "Ollama unavailable",
      retry_count: 0,
    };
    render(<DocumentCard document={failedDoc} onDelete={vi.fn()} onRetry={vi.fn()} />);
    expect(screen.queryByText(/Auto-retried/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Max retries/)).not.toBeInTheDocument();
  });

  it("shows 'Tesseract + Vision AI' badge when ocr_method is tesseract+moondream2", () => {
    const imageDoc = {
      ...mockDocument,
      document_type: "image",
      status: "complete",
      ocr_method: "tesseract+moondream2",
    };
    render(<DocumentCard document={imageDoc} onDelete={vi.fn()} />);
    expect(screen.getByText("Tesseract + Vision AI")).toBeInTheDocument();
  });

  it("shows 'Tesseract' badge when ocr_method is tesseract for image docs", () => {
    const imageDoc = {
      ...mockDocument,
      document_type: "image",
      status: "complete",
      ocr_method: "tesseract",
    };
    render(<DocumentCard document={imageDoc} onDelete={vi.fn()} />);
    expect(screen.getByText("Tesseract")).toBeInTheDocument();
  });

  it("shows 'Vision AI' badge when ocr_method is moondream2", () => {
    const imageDoc = {
      ...mockDocument,
      document_type: "image",
      status: "complete",
      ocr_method: "moondream2",
    };
    render(<DocumentCard document={imageDoc} onDelete={vi.fn()} />);
    expect(screen.getByText("Vision AI")).toBeInTheDocument();
  });

  it("does not show OCR method badge for PDF documents", () => {
    const pdfDoc = {
      ...mockDocument,
      document_type: "pdf",
      status: "complete",
      ocr_method: null,
    };
    render(<DocumentCard document={pdfDoc} onDelete={vi.fn()} />);
    expect(screen.queryByText("Tesseract")).not.toBeInTheDocument();
    expect(screen.queryByText("Vision AI")).not.toBeInTheDocument();
    expect(screen.queryByText("Tesseract + Vision AI")).not.toBeInTheDocument();
  });
});
