import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

const mockUseCrossInvestigationEntityDetail = vi.fn();
vi.mock("@/hooks/useCrossInvestigation", () => ({
  useCrossInvestigationEntityDetail: (...args: unknown[]) =>
    mockUseCrossInvestigationEntityDetail(...args),
}));

import { CrossInvestigationEntityDetail } from "./CrossInvestigationEntityDetail";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

const defaultProps = {
  entityName: "John Doe",
  entityType: "person",
  onBack: vi.fn(),
};

describe("CrossInvestigationEntityDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders entity name and type", () => {
    mockUseCrossInvestigationEntityDetail.mockReturnValue({
      data: {
        entity_name: "John Doe",
        entity_type: "person",
        investigations: [
          {
            investigation_id: "inv-1",
            investigation_name: "Investigation A",
            entity_id: "e1",
            relationships: [
              {
                type: "WORKS_FOR",
                target_name: "Acme Corp",
                target_type: "organization",
                confidence_score: 0.9,
              },
            ],
            source_documents: [
              { document_id: "doc-1", filename: "report.pdf", mention_count: 1 },
            ],
            relationship_count: 1,
            confidence_score: 0.9,
          },
        ],
        total_investigations: 1,
      },
      isLoading: false,
      isError: false,
    });

    render(createElement(CrossInvestigationEntityDetail, defaultProps), {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("John Doe")).toBeTruthy();
    expect(screen.getByText("Person")).toBeTruthy();
    expect(screen.getByText("Found in 1 investigation")).toBeTruthy();
  });

  it("shows relationships per investigation", () => {
    mockUseCrossInvestigationEntityDetail.mockReturnValue({
      data: {
        entity_name: "John Doe",
        entity_type: "person",
        investigations: [
          {
            investigation_id: "inv-1",
            investigation_name: "Investigation A",
            entity_id: "e1",
            relationships: [
              {
                type: "WORKS_FOR",
                target_name: "Acme Corp",
                target_type: "organization",
                confidence_score: 0.9,
              },
            ],
            source_documents: [],
            relationship_count: 1,
            confidence_score: 0.9,
          },
        ],
        total_investigations: 1,
      },
      isLoading: false,
      isError: false,
    });

    render(createElement(CrossInvestigationEntityDetail, defaultProps), {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("WORKS_FOR")).toBeTruthy();
    expect(screen.getByText("Acme Corp")).toBeTruthy();
  });

  it("shows source documents per investigation", () => {
    mockUseCrossInvestigationEntityDetail.mockReturnValue({
      data: {
        entity_name: "John Doe",
        entity_type: "person",
        investigations: [
          {
            investigation_id: "inv-1",
            investigation_name: "Investigation A",
            entity_id: "e1",
            relationships: [],
            source_documents: [
              { document_id: "doc-1", filename: "evidence.pdf", mention_count: 2 },
            ],
            relationship_count: 0,
            confidence_score: 0.9,
          },
        ],
        total_investigations: 1,
      },
      isLoading: false,
      isError: false,
    });

    render(createElement(CrossInvestigationEntityDetail, defaultProps), {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("evidence.pdf")).toBeTruthy();
  });

  it("back button calls onBack", async () => {
    mockUseCrossInvestigationEntityDetail.mockReturnValue({
      data: {
        entity_name: "John Doe",
        entity_type: "person",
        investigations: [],
        total_investigations: 0,
      },
      isLoading: false,
      isError: false,
    });

    const onBack = vi.fn();
    render(
      createElement(CrossInvestigationEntityDetail, {
        ...defaultProps,
        onBack,
      }),
      { wrapper: createWrapper() },
    );

    await userEvent.click(screen.getByLabelText("Back to matches"));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it("Open in Investigation button navigates", async () => {
    mockUseCrossInvestigationEntityDetail.mockReturnValue({
      data: {
        entity_name: "John Doe",
        entity_type: "person",
        investigations: [
          {
            investigation_id: "inv-1",
            investigation_name: "Investigation A",
            entity_id: "e1",
            relationships: [],
            source_documents: [],
            relationship_count: 0,
            confidence_score: 0.9,
          },
        ],
        total_investigations: 1,
      },
      isLoading: false,
      isError: false,
    });

    const onOpenInInvestigation = vi.fn();
    render(
      createElement(CrossInvestigationEntityDetail, {
        ...defaultProps,
        onOpenInInvestigation,
      }),
      { wrapper: createWrapper() },
    );

    await userEvent.click(screen.getByText("Open"));
    expect(onOpenInInvestigation).toHaveBeenCalledWith("inv-1", "John Doe");
  });
});
