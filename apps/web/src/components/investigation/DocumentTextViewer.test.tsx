import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test-utils";
import { DocumentTextViewer } from "./DocumentTextViewer";

// Mock the useDocumentText hook
const mockUseDocumentText = vi.fn();
vi.mock("@/hooks/useDocuments", () => ({
  useDocumentText: (...args: unknown[]) => mockUseDocumentText(...args),
}));

const defaultProps = {
  investigationId: "inv-1",
  documentId: "doc-1" as string | null,
  onOpenChange: vi.fn(),
};

describe("DocumentTextViewer", () => {
  beforeEach(() => {
    mockUseDocumentText.mockReset();
    defaultProps.onOpenChange = vi.fn();
  });

  it("renders loading state while text is fetching", () => {
    mockUseDocumentText.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    renderWithProviders(<DocumentTextViewer {...defaultProps} />);
    expect(screen.getByTestId("loading-indicator")).toBeInTheDocument();
    expect(screen.getByText("Loading text...")).toBeInTheDocument();
  });

  it("renders extracted text with page markers", async () => {
    mockUseDocumentText.mockReturnValue({
      data: {
        document_id: "doc-1",
        filename: "report.pdf",
        page_count: 2,
        extracted_text:
          "--- Page 1 ---\nFirst page content\n--- Page 2 ---\nSecond page content",
      },
      isLoading: false,
    });

    renderWithProviders(<DocumentTextViewer {...defaultProps} />);

    expect(screen.getByText("report.pdf")).toBeInTheDocument();
    expect(screen.getByText("2 pages")).toBeInTheDocument();
    expect(screen.getByText("First page content")).toBeInTheDocument();
    expect(screen.getByText("Second page content")).toBeInTheDocument();
    expect(screen.getByText("Page 1")).toBeInTheDocument();
    expect(screen.getByText("Page 2")).toBeInTheDocument();
  });

  it("handles empty/null text with empty state message", () => {
    mockUseDocumentText.mockReturnValue({
      data: {
        document_id: "doc-1",
        filename: "empty.pdf",
        page_count: 1,
        extracted_text: null,
      },
      isLoading: false,
    });

    renderWithProviders(<DocumentTextViewer {...defaultProps} />);
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(
      screen.getByText("No text could be extracted from this document."),
    ).toBeInTheDocument();
  });

  it("shows singular 'page' for single-page document", () => {
    mockUseDocumentText.mockReturnValue({
      data: {
        document_id: "doc-1",
        filename: "single.pdf",
        page_count: 1,
        extracted_text: "--- Page 1 ---\nContent",
      },
      isLoading: false,
    });

    renderWithProviders(<DocumentTextViewer {...defaultProps} />);
    expect(screen.getByText("1 page")).toBeInTheDocument();
  });

  it("does not render dialog when documentId is null", () => {
    mockUseDocumentText.mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    renderWithProviders(
      <DocumentTextViewer {...defaultProps} documentId={null} />,
    );
    expect(screen.queryByText("Document Text")).not.toBeInTheDocument();
  });

  it("renders error state when API request fails", () => {
    mockUseDocumentText.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    renderWithProviders(<DocumentTextViewer {...defaultProps} />);
    expect(screen.getByTestId("error-state")).toBeInTheDocument();
    expect(
      screen.getByText("Failed to load document text. Please try again."),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("empty-state")).not.toBeInTheDocument();
  });

  it("renders text without page markers as single page", () => {
    mockUseDocumentText.mockReturnValue({
      data: {
        document_id: "doc-1",
        filename: "plain.pdf",
        page_count: 1,
        extracted_text: "Plain text without any page markers.",
      },
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<DocumentTextViewer {...defaultProps} />);
    expect(screen.getByText("Plain text without any page markers.")).toBeInTheDocument();
    expect(screen.getByText("Page 1")).toBeInTheDocument();
  });

  it("calls onOpenChange when close button is clicked", async () => {
    mockUseDocumentText.mockReturnValue({
      data: {
        document_id: "doc-1",
        filename: "report.pdf",
        page_count: 1,
        extracted_text: "--- Page 1 ---\nContent",
      },
      isLoading: false,
    });

    renderWithProviders(<DocumentTextViewer {...defaultProps} />);

    const closeButton = screen.getByRole("button", { name: /close/i });
    await userEvent.click(closeButton);

    await waitFor(() => {
      expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
    });
  });
});
