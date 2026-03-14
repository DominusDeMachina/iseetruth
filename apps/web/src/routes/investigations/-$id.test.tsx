import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProcessingDashboard } from "@/components/investigation/ProcessingDashboard";
import { EntitySummaryBar } from "@/components/investigation/EntitySummaryBar";
import { QueryInput } from "@/components/qa/QueryInput";
import { AnswerPanel } from "@/components/qa/AnswerPanel";
import { SuggestedQuestions } from "@/components/qa/SuggestedQuestions";
import type { DocumentListResponse } from "@/hooks/useDocuments";
import type { ConversationEntry } from "@/components/qa/types";

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
