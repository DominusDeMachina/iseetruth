import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CitationModal } from "./CitationModal";
import type { Citation, EntityReference } from "./types";

// Mock useChunkContext
const mockUseChunkContext = vi.fn();
vi.mock("@/hooks/useChunkContext", () => ({
  useChunkContext: (...args: unknown[]) => mockUseChunkContext(...args),
}));

const sampleCitation: Citation = {
  citation_number: 1,
  document_id: "d1",
  document_filename: "contract-award-089.pdf",
  chunk_id: "c1",
  page_start: 3,
  page_end: 3,
  text_excerpt: "Deputy Mayor Horvat signed the contract",
  source_url: null,
  document_type: "pdf",
};

const sampleWebCitation: Citation = {
  citation_number: 2,
  document_id: "d2",
  document_filename: "Corporate Registry - GreenBuild LLC",
  chunk_id: "c2",
  page_start: 1,
  page_end: 1,
  text_excerpt: "GreenBuild LLC was registered on March 1",
  source_url: "https://registry.example.com/greenbuild",
  document_type: "web",
};

const sampleChunkData = {
  chunk_id: "c1",
  document_id: "d1",
  document_filename: "contract-award-089.pdf",
  sequence_number: 14,
  total_chunks: 47,
  text: "Deputy Mayor Horvat signed the contract award #2024-089 granting the municipal construction tender to GreenBuild LLC on March 15.",
  page_start: 3,
  page_end: 3,
  context_before: "The committee reviewed all submitted proposals during the February session.",
  context_after: "The contract value was estimated at EUR 2.4 million over three years.",
};

const sampleEntities: EntityReference[] = [
  { entity_id: "e1", name: "Horvat", type: "Person" },
  { entity_id: "e2", name: "GreenBuild LLC", type: "Organization" },
];

function renderModal(
  props: Partial<React.ComponentProps<typeof CitationModal>> = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <CitationModal
        citation={sampleCitation}
        investigationId="inv-1"
        open={true}
        onOpenChange={vi.fn()}
        onEntityClick={vi.fn()}
        entities={[]}
        {...props}
      />
    </QueryClientProvider>,
  );
}

describe("CitationModal", () => {
  beforeEach(() => {
    mockUseChunkContext.mockReset();
  });

  it("renders modal when open with citation data", () => {
    mockUseChunkContext.mockReturnValue({
      data: sampleChunkData,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal();

    expect(
      screen.getByText("Citation — contract-award-089.pdf"),
    ).toBeInTheDocument();
    expect(screen.getByText("Page 3")).toBeInTheDocument();
  });

  it("displays filename and page range for multi-page citations", () => {
    mockUseChunkContext.mockReturnValue({
      data: { ...sampleChunkData, page_start: 3, page_end: 5 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal();

    expect(screen.getByText("Pages 3–5")).toBeInTheDocument();
  });

  it("renders highlighted passage with mark element", () => {
    mockUseChunkContext.mockReturnValue({
      data: sampleChunkData,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal();

    const mark = document.querySelector("mark");
    expect(mark).not.toBeNull();
    expect(mark!.textContent).toContain("Deputy Mayor Horvat signed");
  });

  it("renders context_before and context_after in muted text", () => {
    mockUseChunkContext.mockReturnValue({
      data: sampleChunkData,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal();

    expect(
      screen.getByText(
        "The committee reviewed all submitted proposals during the February session.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "The contract value was estimated at EUR 2.4 million over three years.",
      ),
    ).toBeInTheDocument();
  });

  it("displays chunk position footer", () => {
    mockUseChunkContext.mockReturnValue({
      data: sampleChunkData,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal();

    expect(screen.getByText("Chunk 15 of 47")).toBeInTheDocument();
  });

  it("shows loading skeleton when data is loading", () => {
    mockUseChunkContext.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal();

    // Skeleton uses animate-pulse class
    const skeleton = document.querySelector(".animate-pulse");
    expect(skeleton).not.toBeNull();
    // Should not show passage or chunk position
    expect(screen.queryByText(/Chunk \d+ of \d+/)).not.toBeInTheDocument();
  });

  it("shows error state with retry button", async () => {
    const refetch = vi.fn();
    const user = userEvent.setup();

    mockUseChunkContext.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch,
    });

    renderModal();

    expect(
      screen.getByText("Failed to load source passage. Please try again."),
    ).toBeInTheDocument();

    const retryButton = screen.getByText("Retry");
    await user.click(retryButton);
    expect(refetch).toHaveBeenCalled();
  });

  it("renders entity names in passage as clickable links", async () => {
    const onEntityClick = vi.fn();
    const user = userEvent.setup();

    mockUseChunkContext.mockReturnValue({
      data: sampleChunkData,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal({ entities: sampleEntities, onEntityClick });

    const horvatLink = screen.getByLabelText("Explore Horvat in graph");
    expect(horvatLink).toBeInTheDocument();

    await user.click(horvatLink);
    expect(onEntityClick).toHaveBeenCalledWith("Horvat");
  });

  it("activates entity link on Space key (accessibility)", async () => {
    const onEntityClick = vi.fn();
    const user = userEvent.setup();

    mockUseChunkContext.mockReturnValue({
      data: sampleChunkData,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal({ entities: sampleEntities, onEntityClick });

    const horvatLink = screen.getByLabelText("Explore Horvat in graph");
    horvatLink.focus();
    await user.keyboard(" ");
    expect(onEntityClick).toHaveBeenCalledWith("Horvat");
  });

  it("closes on Escape key", async () => {
    const onOpenChange = vi.fn();
    const user = userEvent.setup();

    mockUseChunkContext.mockReturnValue({
      data: sampleChunkData,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal({ onOpenChange });

    await user.keyboard("{Escape}");
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("sets aria-label with filename and page", () => {
    mockUseChunkContext.mockReturnValue({
      data: sampleChunkData,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal();

    const dialogContent = document.querySelector(
      '[aria-label="Source citation from contract-award-089.pdf, page 3"]',
    );
    expect(dialogContent).not.toBeNull();
  });

  it("shows Web Source badge and URL for web citations", () => {
    mockUseChunkContext.mockReturnValue({
      data: { ...sampleChunkData, page_start: 1, page_end: 1 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal({ citation: sampleWebCitation });

    // Web Source badge
    const badge = screen.getByTestId("web-source-badge");
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toBe("Web Source");

    // Source URL link
    const urlLink = screen.getByTestId("citation-source-url");
    expect(urlLink).toBeInTheDocument();
    expect(urlLink).toHaveAttribute(
      "href",
      "https://registry.example.com/greenbuild",
    );
    expect(urlLink).toHaveAttribute("target", "_blank");
  });

  it("renders external link icon for web citations", () => {
    mockUseChunkContext.mockReturnValue({
      data: { ...sampleChunkData, page_start: 1, page_end: 1 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal({ citation: sampleWebCitation });

    const externalLink = screen.getByTestId("citation-external-link");
    expect(externalLink).toBeInTheDocument();
    expect(externalLink).toHaveAttribute(
      "href",
      "https://registry.example.com/greenbuild",
    );
    expect(externalLink).toHaveAttribute("target", "_blank");
    expect(externalLink).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("does not show Web Source badge for PDF citations", () => {
    mockUseChunkContext.mockReturnValue({
      data: sampleChunkData,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal({ citation: sampleCitation });

    expect(screen.queryByTestId("web-source-badge")).not.toBeInTheDocument();
    expect(screen.queryByTestId("citation-source-url")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("citation-external-link"),
    ).not.toBeInTheDocument();
  });

  it("sets web-specific aria-label for web citations", () => {
    mockUseChunkContext.mockReturnValue({
      data: { ...sampleChunkData, page_start: 1, page_end: 1 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderModal({ citation: sampleWebCitation });

    const dialogContent = document.querySelector(
      '[aria-label="Source citation from web page Corporate Registry - GreenBuild LLC"]',
    );
    expect(dialogContent).not.toBeNull();
  });
});
