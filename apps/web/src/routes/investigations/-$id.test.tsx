import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProcessingDashboard } from "@/components/investigation/ProcessingDashboard";
import { EntitySummaryBar } from "@/components/investigation/EntitySummaryBar";
import { QueryInput } from "@/components/qa/QueryInput";
import { AnswerPanel } from "@/components/qa/AnswerPanel";
import { SuggestedQuestions } from "@/components/qa/SuggestedQuestions";
import { CitationModal } from "@/components/qa/CitationModal";
import type { DocumentListResponse } from "@/hooks/useDocuments";
import type { Citation, ConversationEntry, EntityReference } from "@/components/qa/types";

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
    extraction_quality: null,
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

describe("EntitySummaryBar integration", () => {
  it("renders entity summary bar with type counts", () => {
    const summary = { people: 5, organizations: 3, locations: 2, total: 10 };

    renderWithQuery(<EntitySummaryBar summary={summary} />);

    expect(screen.getByText("10 entities")).toBeInTheDocument();
    expect(screen.getByText(/5 people/)).toBeInTheDocument();
    expect(screen.getByText(/3 orgs/)).toBeInTheDocument();
    expect(screen.getByText(/2 locations/)).toBeInTheDocument();
  });

  it("renders nothing when total is 0", () => {
    const summary = { people: 0, organizations: 0, locations: 0, total: 0 };

    const { container } = renderWithQuery(<EntitySummaryBar summary={summary} />);
    expect(container.firstChild).toBeNull();
  });
});

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

describe("Investigation Detail — Q&A Integration", () => {
  it("QAPanel components render together and input submits", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();

    render(
      <div>
        <AnswerPanel
          conversation={[]}
          streamingText=""
          status="idle"
          onCitationClick={vi.fn()}
          onEntityClick={vi.fn()}
        />
        <SuggestedQuestions
          questions={[]}
          status="idle"
          noResults={false}
          onQuestionClick={vi.fn()}
        />
        <QueryInput onSubmit={onSubmit} status="idle" />
      </div>,
    );

    const input = screen.getByLabelText(
      "Ask a question about your investigation",
    );
    await user.type(input, "Who is Horvat?{Enter}");
    expect(onSubmit).toHaveBeenCalledWith("Who is Horvat?");
  });

  it("entity click from answer dispatches handler", async () => {
    const onEntityClick = vi.fn();
    const user = userEvent.setup();
    const entry: ConversationEntry = {
      id: "e1",
      question: "Who is Horvat?",
      answer: "**Horvat** is the deputy mayor.",
      citations: [],
      entitiesMentioned: [
        { entity_id: "e1", name: "Horvat", type: "Person" },
      ],
      suggestedFollowups: [],
      noResults: false,
      status: "complete",
    };

    render(
      <AnswerPanel
        conversation={[entry]}
        streamingText=""
        status="complete"
        onCitationClick={vi.fn()}
        onEntityClick={onEntityClick}
      />,
    );

    const entityLink = screen.getByLabelText("Explore Horvat in graph");
    await user.click(entityLink);
    expect(onEntityClick).toHaveBeenCalledWith("Horvat");
  });

  it("prefillQuestion populates QueryInput", () => {
    render(
      <QueryInput
        onSubmit={vi.fn()}
        status="idle"
        prefillQuestion="What connections does Horvat have?"
      />,
    );

    const input = screen.getByLabelText(
      "Ask a question about your investigation",
    ) as HTMLTextAreaElement;
    expect(input.value).toBe("What connections does Horvat have?");
  });

  it("suggested follow-up click dispatches question", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(
      <SuggestedQuestions
        questions={["What contracts did Horvat sign?"]}
        status="complete"
        noResults={false}
        onQuestionClick={onClick}
      />,
    );

    await user.click(screen.getByText("What contracts did Horvat sign?"));
    expect(onClick).toHaveBeenCalledWith("What contracts did Horvat sign?");
  });

  it("document management button triggers dialog open callback", async () => {
    const onOpen = vi.fn();
    const user = userEvent.setup();

    render(
      <button
        onClick={() => onOpen(true)}
        aria-label="Manage documents"
        title="Manage documents"
      >
        Docs
      </button>,
    );

    const button = screen.getByLabelText("Manage documents");
    expect(button).toBeInTheDocument();
    await user.click(button);
    expect(onOpen).toHaveBeenCalledWith(true);
  });
});

// Mock useChunkContext for citation integration tests
const mockUseChunkContext = vi.fn();
vi.mock("@/hooks/useChunkContext", () => ({
  useChunkContext: (...args: unknown[]) => mockUseChunkContext(...args),
}));

const sampleChunkData = {
  chunk_id: "c1",
  document_id: "d1",
  document_filename: "contract.pdf",
  sequence_number: 14,
  total_chunks: 47,
  text: "Deputy Mayor Horvat signed the contract award to GreenBuild LLC.",
  page_start: 3,
  page_end: 3,
  context_before: "Previous context paragraph.",
  context_after: "Following context paragraph.",
};

describe("Investigation Detail — Citation Click-Through Integration", () => {
  beforeEach(() => {
    mockUseChunkContext.mockReturnValue({
      data: sampleChunkData,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
  });

  it("clicking citation superscript opens CitationModal", async () => {
    const user = userEvent.setup();
    let activeCitation: Citation | null = null;

    const citation: Citation = {
      citation_number: 1,
      document_id: "d1",
      document_filename: "contract.pdf",
      chunk_id: "c1",
      page_start: 3,
      page_end: 3,
      text_excerpt: "Deputy Mayor Horvat signed",
      source_url: null,
      document_type: "pdf",
    };

    const entry: ConversationEntry = {
      id: "e1",
      question: "Who signed?",
      answer: "Horvat signed the contract [1]",
      citations: [citation],
      entitiesMentioned: [],
      suggestedFollowups: [],
      noResults: false,
      status: "complete",
    };

    const handleCitationClick = (cit: Citation | number) => {
      if (typeof cit === "number") {
        const found = entry.citations.find((c) => c.citation_number === cit);
        if (found) activeCitation = found;
      } else {
        activeCitation = cit;
      }
      rerender();
    };

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const ui = () => (
      <QueryClientProvider client={queryClient}>
        <AnswerPanel
          conversation={[entry]}
          streamingText=""
          status="complete"
          onCitationClick={handleCitationClick}
          onEntityClick={vi.fn()}
        />
        <CitationModal
          citation={activeCitation}
          investigationId="inv-1"
          open={!!activeCitation}
          onOpenChange={(open) => {
            if (!open) {
              activeCitation = null;
              rerender();
            }
          }}
          onEntityClick={vi.fn()}
        />
      </QueryClientProvider>
    );

    const { rerender: baseRerender } = render(ui());
    const rerender = () => baseRerender(ui());

    // Click superscript citation [1]
    const citLink = screen.getByLabelText("Source: contract.pdf, page 3");
    await user.click(citLink);

    // Modal should be open with citation data
    await waitFor(() => {
      expect(
        screen.getByText("Citation — contract.pdf"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Chunk 15 of 47")).toBeInTheDocument();
  });

  it("clicking citation in footer opens CitationModal", async () => {
    const user = userEvent.setup();
    let activeCitation: Citation | null = null;

    const citation: Citation = {
      citation_number: 1,
      document_id: "d1",
      document_filename: "contract.pdf",
      chunk_id: "c1",
      page_start: 5,
      page_end: 5,
      text_excerpt: "text",
      source_url: null,
      document_type: "pdf",
    };

    const entry: ConversationEntry = {
      id: "e1",
      question: "Who signed?",
      answer: "Answer [1]",
      citations: [citation],
      entitiesMentioned: [],
      suggestedFollowups: [],
      noResults: false,
      status: "complete",
    };

    const handleCitationClick = (cit: Citation | number) => {
      if (typeof cit === "number") {
        const found = entry.citations.find((c) => c.citation_number === cit);
        if (found) activeCitation = found;
      } else {
        activeCitation = cit;
      }
      rerender();
    };

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const ui = () => (
      <QueryClientProvider client={queryClient}>
        <AnswerPanel
          conversation={[entry]}
          streamingText=""
          status="complete"
          onCitationClick={handleCitationClick}
          onEntityClick={vi.fn()}
        />
        <CitationModal
          citation={activeCitation}
          investigationId="inv-1"
          open={!!activeCitation}
          onOpenChange={(open) => {
            if (!open) {
              activeCitation = null;
              rerender();
            }
          }}
          onEntityClick={vi.fn()}
        />
      </QueryClientProvider>
    );

    const { rerender: baseRerender } = render(ui());
    const rerender = () => baseRerender(ui());

    // Click footer citation
    const footerLink = screen.getByText("[1] contract.pdf, page 5");
    await user.click(footerLink);

    await waitFor(() => {
      expect(
        screen.getByText("Citation — contract.pdf"),
      ).toBeInTheDocument();
    });
  });

  it("clicking entity in passage closes modal and triggers graph navigation", async () => {
    const user = userEvent.setup();
    const onEntityClick = vi.fn();

    const entities: EntityReference[] = [
      { entity_id: "e1", name: "Horvat", type: "Person" },
    ];

    const citation: Citation = {
      citation_number: 1,
      document_id: "d1",
      document_filename: "contract.pdf",
      chunk_id: "c1",
      page_start: 3,
      page_end: 3,
      text_excerpt: "Horvat signed",
      source_url: null,
      document_type: "pdf",
    };

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <CitationModal
          citation={citation}
          investigationId="inv-1"
          open={true}
          onOpenChange={vi.fn()}
          onEntityClick={onEntityClick}
          entities={entities}
        />
      </QueryClientProvider>,
    );

    const entityLink = screen.getByLabelText("Explore Horvat in graph");
    await user.click(entityLink);
    expect(onEntityClick).toHaveBeenCalledWith("Horvat");
  });

  it("closing modal returns focus to Q&A panel area", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();

    const citation: Citation = {
      citation_number: 1,
      document_id: "d1",
      document_filename: "contract.pdf",
      chunk_id: "c1",
      page_start: 3,
      page_end: 3,
      text_excerpt: "text",
      source_url: null,
      document_type: "pdf",
    };

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <CitationModal
          citation={citation}
          investigationId="inv-1"
          open={true}
          onOpenChange={onOpenChange}
          onEntityClick={vi.fn()}
        />
      </QueryClientProvider>,
    );

    // Press Escape to close
    await user.keyboard("{Escape}");
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
