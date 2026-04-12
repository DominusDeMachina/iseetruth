import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

const mockUseCrossInvestigation = vi.fn();
const mockUseCrossInvestigationSearch = vi.fn();
vi.mock("@/hooks/useCrossInvestigation", () => ({
  useCrossInvestigation: (...args: unknown[]) =>
    mockUseCrossInvestigation(...args),
  useCrossInvestigationSearch: (...args: unknown[]) =>
    mockUseCrossInvestigationSearch(...args),
  useDismissCrossMatch: () => ({ mutate: vi.fn() }),
  useUndismissCrossMatch: () => ({ mutate: vi.fn() }),
}));

import { CrossInvestigationPanel } from "./CrossInvestigationPanel";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

const defaultProps = {
  investigationId: "inv-1",
  onClose: vi.fn(),
};

describe("CrossInvestigationPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCrossInvestigationSearch.mockReturnValue({
      data: undefined,
      isLoading: false,
    });
  });

  it("renders match cards when data is present", () => {
    mockUseCrossInvestigation.mockReturnValue({
      data: {
        matches: [
          {
            entity_name: "John Doe",
            entity_type: "person",
            match_confidence: 1.0,
            match_type: "exact",
            source_entity_id: "e1",
            source_relationship_count: 3,
            source_confidence_score: 0.9,
            investigations: [
              {
                investigation_id: "inv-2",
                investigation_name: "Investigation B",
                entity_id: "e2",
                relationship_count: 2,
                confidence_score: 0.85,
              },
            ],
          },
        ],
        total_matches: 1,
        query_duration_ms: 42,
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(
      createElement(CrossInvestigationPanel, defaultProps),
      { wrapper: createWrapper() },
    );

    expect(screen.getByText("Cross-Investigation Links")).toBeTruthy();
    expect(screen.getByText("John Doe")).toBeTruthy();
    expect(screen.getByText("1 entity found in other investigations")).toBeTruthy();
  });

  it("shows empty state for single investigation", () => {
    mockUseCrossInvestigation.mockReturnValue({
      data: {
        matches: [],
        total_matches: 0,
        query_duration_ms: 5,
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(
      createElement(CrossInvestigationPanel, defaultProps),
      { wrapper: createWrapper() },
    );

    expect(
      screen.getByText(/Cross-investigation matching requires two or more investigations/),
    ).toBeTruthy();
  });

  it("shows loading skeleton", () => {
    mockUseCrossInvestigation.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    });

    render(
      createElement(CrossInvestigationPanel, defaultProps),
      { wrapper: createWrapper() },
    );

    // Skeleton elements should be present (animate-pulse divs)
    const container = screen.getByRole("dialog");
    expect(container).toBeTruthy();
  });

  it("shows error state with retry", async () => {
    const mockRefetch = vi.fn();
    mockUseCrossInvestigation.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: mockRefetch,
    });

    render(
      createElement(CrossInvestigationPanel, defaultProps),
      { wrapper: createWrapper() },
    );

    expect(
      screen.getByText("Unable to load cross-investigation matches."),
    ).toBeTruthy();

    const retryButton = screen.getByText("Retry");
    await userEvent.click(retryButton);
    expect(mockRefetch).toHaveBeenCalledOnce();
  });

  it("renders search input", () => {
    mockUseCrossInvestigation.mockReturnValue({
      data: { matches: [], total_matches: 0, query_duration_ms: 5 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(
      createElement(CrossInvestigationPanel, defaultProps),
      { wrapper: createWrapper() },
    );

    expect(
      screen.getByPlaceholderText("Search across investigations..."),
    ).toBeTruthy();
  });
});
