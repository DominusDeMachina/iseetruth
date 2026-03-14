import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AnswerPanel } from "./AnswerPanel";
import type { ConversationEntry } from "./types";

const baseEntry: ConversationEntry = {
  id: "e1",
  question: "Who is Horvat?",
  answer: null,
  citations: [],
  entitiesMentioned: [],
  suggestedFollowups: [],
  noResults: false,
  status: "complete",
};

describe("AnswerPanel", () => {
  it("renders citation as clickable superscript", async () => {
    const onCitationClick = vi.fn();
    const user = userEvent.setup();
    const entry: ConversationEntry = {
      ...baseEntry,
      answer: "Horvat signed contract [1]",
      citations: [
        {
          citation_number: 1,
          document_id: "d1",
          document_filename: "contract.pdf",
          chunk_id: "c1",
          page_start: 3,
          page_end: 3,
          text_excerpt: "signed",
        },
      ],
    };

    render(
      <AnswerPanel
        conversation={[entry]}
        streamingText=""
        status="complete"
        onCitationClick={onCitationClick}
        onEntityClick={vi.fn()}
      />,
    );

    const citLink = screen.getByLabelText("Source: contract.pdf, page 3");
    expect(citLink).toBeDefined();
    await user.click(citLink);
    expect(onCitationClick).toHaveBeenCalledWith(1);
  });

  it("renders entity name as clickable link with correct color", async () => {
    const onEntityClick = vi.fn();
    const user = userEvent.setup();
    const entry: ConversationEntry = {
      ...baseEntry,
      answer: "**Horvat** is connected to **GreenBuild LLC**",
      entitiesMentioned: [
        { entity_id: "e1", name: "Horvat", type: "Person" },
        { entity_id: "e2", name: "GreenBuild LLC", type: "Organization" },
      ],
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

    const horvatLink = screen.getByLabelText("Explore Horvat in graph");
    expect(horvatLink).toBeDefined();
    expect(horvatLink.style.color).toBe("rgb(107, 155, 210)"); // #6b9bd2

    const greenBuildLink = screen.getByLabelText(
      "Explore GreenBuild LLC in graph",
    );
    expect(greenBuildLink.style.color).toBe("rgb(196, 162, 101)"); // #c4a265

    await user.click(horvatLink);
    expect(onEntityClick).toHaveBeenCalledWith("Horvat");
  });

  it("shows streaming text with blinking cursor", () => {
    const streamingEntry: ConversationEntry = {
      ...baseEntry,
      answer: null,
      status: "streaming",
    };

    render(
      <AnswerPanel
        conversation={[streamingEntry]}
        streamingText="Deputy Mayor Horvat"
        status="streaming"
        onCitationClick={vi.fn()}
        onEntityClick={vi.fn()}
      />,
    );

    expect(screen.getByText(/Deputy Mayor Horvat/)).toBeDefined();
    // Blinking cursor element
    expect(
      document.querySelector(".animate-pulse"),
    ).toBeDefined();
  });

  it("displays no-results message", () => {
    const entry: ConversationEntry = {
      ...baseEntry,
      answer: "",
      noResults: true,
    };

    render(
      <AnswerPanel
        conversation={[entry]}
        streamingText=""
        status="complete"
        onCitationClick={vi.fn()}
        onEntityClick={vi.fn()}
      />,
    );

    expect(screen.getByText(/No connection found/)).toBeDefined();
  });

  it("displays error state with message", () => {
    const entry: ConversationEntry = {
      ...baseEntry,
      answer: null,
      status: "error",
      error: "Graph database unavailable",
    };

    render(
      <AnswerPanel
        conversation={[entry]}
        streamingText=""
        status="error"
        onCitationClick={vi.fn()}
        onEntityClick={vi.fn()}
      />,
    );

    expect(screen.getByText("Graph database unavailable")).toBeDefined();
  });

  it("shows status indicator during processing", () => {
    const streamingEntry: ConversationEntry = {
      ...baseEntry,
      answer: null,
      status: "streaming",
    };

    render(
      <AnswerPanel
        conversation={[streamingEntry]}
        streamingText=""
        status="searching"
        onCitationClick={vi.fn()}
        onEntityClick={vi.fn()}
      />,
    );

    expect(
      screen.getByText("Searching knowledge graph and documents..."),
    ).toBeDefined();
  });

  it("shows Try again button in error state that resubmits question", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    const entry: ConversationEntry = {
      ...baseEntry,
      answer: null,
      status: "error",
      error: "Graph database unavailable",
    };

    render(
      <AnswerPanel
        conversation={[entry]}
        streamingText=""
        status="error"
        onCitationClick={vi.fn()}
        onEntityClick={vi.fn()}
        onRetry={onRetry}
      />,
    );

    const retryButton = screen.getByText("Try again");
    expect(retryButton).toBeInTheDocument();
    await user.click(retryButton);
    expect(onRetry).toHaveBeenCalledWith("Who is Horvat?");
  });

  it("renders citation footer with clickable entries", async () => {
    const onCitationClick = vi.fn();
    const user = userEvent.setup();
    const entry: ConversationEntry = {
      ...baseEntry,
      answer: "Answer [1]",
      citations: [
        {
          citation_number: 1,
          document_id: "d1",
          document_filename: "report.pdf",
          chunk_id: "c1",
          page_start: 5,
          page_end: 5,
          text_excerpt: "text",
        },
      ],
    };

    render(
      <AnswerPanel
        conversation={[entry]}
        streamingText=""
        status="complete"
        onCitationClick={onCitationClick}
        onEntityClick={vi.fn()}
      />,
    );

    const footerLink = screen.getByText("[1] report.pdf, page 5");
    await user.click(footerLink);
    expect(onCitationClick).toHaveBeenCalledWith(entry.citations[0]);
  });
});
