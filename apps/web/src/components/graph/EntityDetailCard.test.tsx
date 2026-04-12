import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

const mockUseEntityDetail = vi.fn();
vi.mock("@/hooks/useEntityDetail", () => ({
  useEntityDetail: (...args: unknown[]) => mockUseEntityDetail(...args),
}));

import { EntityDetailCard } from "./EntityDetailCard";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

const mockEntityData = {
  id: "entity-1",
  name: "Deputy Mayor Horvat",
  type: "Person",
  confidence_score: 0.92,
  investigation_id: "inv-1",
  relationships: [
    { relation_type: "WORKS_FOR", target_id: "e2", target_name: "City Council", target_type: "Organization", confidence_score: 0.88 },
    { relation_type: "SIGNED", target_id: "e3", target_name: "Contract #089", target_type: "Organization", confidence_score: 0.85 },
    { relation_type: "KNOWS", target_id: "e4", target_name: "Marko Petrovic", target_type: "Person", confidence_score: 0.7 },
    { relation_type: "LOCATED_IN", target_id: "e5", target_name: "Zagreb", target_type: "Location", confidence_score: 0.95 },
    { relation_type: "OWNS", target_id: "e6", target_name: "Holding Corp", target_type: "Organization", confidence_score: 0.6 },
    { relation_type: "MET_WITH", target_id: "e7", target_name: "Ana Kovac", target_type: "Person", confidence_score: 0.55 },
    { relation_type: "FUNDED_BY", target_id: "e8", target_name: "Fund XYZ", target_type: "Organization", confidence_score: 0.4 },
  ],
  sources: [
    { document_id: "doc-1", document_filename: "contract-award-089.pdf", chunk_id: "c1", page_start: 3, page_end: 3, text_excerpt: "excerpt1" },
    { document_id: "doc-2", document_filename: "council-minutes.pdf", chunk_id: "c2", page_start: 1, page_end: 2, text_excerpt: "excerpt2" },
  ],
  evidence_strength: "corroborated",
};

const defaultProps = {
  entityId: "entity-1",
  investigationId: "inv-1",
  position: { x: 200, y: 100 },
  onClose: vi.fn(),
  onNavigateToEntity: vi.fn(),
  onAskAboutEntity: vi.fn(),
};

describe("EntityDetailCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders entity name, type badge, and confidence", () => {
    mockUseEntityDetail.mockReturnValue({
      data: mockEntityData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(EntityDetailCard, defaultProps), {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Deputy Mayor Horvat")).toBeTruthy();
    expect(screen.getByText("Person")).toBeTruthy();
    expect(screen.getByText("High confidence")).toBeTruthy();
  });

  it("shows relationships truncated at 5 with show more button", async () => {
    mockUseEntityDetail.mockReturnValue({
      data: mockEntityData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(EntityDetailCard, defaultProps), {
      wrapper: createWrapper(),
    });

    // Should show "Relationships (7)"
    expect(screen.getByText("Relationships (7)")).toBeTruthy();

    // Should see first 5 relationships
    expect(screen.getByText("City Council")).toBeTruthy();
    expect(screen.getByText("Marko Petrovic")).toBeTruthy();

    // 6th and 7th should be hidden initially
    expect(screen.queryByText("Ana Kovac")).toBeNull();

    // Show more button
    const showMore = screen.getByText("Show 2 more");
    await userEvent.click(showMore);

    // Now all should be visible
    expect(screen.getByText("Ana Kovac")).toBeTruthy();
    expect(screen.getByText("Fund XYZ")).toBeTruthy();
  });

  it("calls onNavigateToEntity when clicking a target entity name", async () => {
    mockUseEntityDetail.mockReturnValue({
      data: mockEntityData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(EntityDetailCard, defaultProps), {
      wrapper: createWrapper(),
    });

    await userEvent.click(screen.getByText("City Council"));
    expect(defaultProps.onNavigateToEntity).toHaveBeenCalledWith("e2");
  });

  it("calls onClose when clicking close button", async () => {
    mockUseEntityDetail.mockReturnValue({
      data: mockEntityData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(EntityDetailCard, defaultProps), {
      wrapper: createWrapper(),
    });

    const dialog = screen.getByRole("dialog");
    const closeBtn = within(dialog).getByLabelText("Close");
    await userEvent.click(closeBtn);
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it("shows loading skeleton", () => {
    mockUseEntityDetail.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(EntityDetailCard, defaultProps), {
      wrapper: createWrapper(),
    });

    const dialog = screen.getByRole("dialog");
    // Skeleton should have shimmer elements
    const skeletons = dialog.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows error state with retry", async () => {
    const mockRefetch = vi.fn();
    mockUseEntityDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Network error"),
      refetch: mockRefetch,
    });

    render(createElement(EntityDetailCard, defaultProps), {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Failed to load entity details")).toBeTruthy();
    await userEvent.click(screen.getByText("Retry"));
    expect(mockRefetch).toHaveBeenCalled();
  });

  it("has correct dialog accessibility attributes", () => {
    mockUseEntityDetail.mockReturnValue({
      data: mockEntityData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(EntityDetailCard, defaultProps), {
      wrapper: createWrapper(),
    });

    const dialog = screen.getByRole("dialog");
    expect(dialog.getAttribute("aria-label")).toBe(
      "Details for Deputy Mayor Horvat",
    );
  });

  it("closes on Escape key", async () => {
    mockUseEntityDetail.mockReturnValue({
      data: mockEntityData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(EntityDetailCard, defaultProps), {
      wrapper: createWrapper(),
    });

    await userEvent.keyboard("{Escape}");
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it("calls onAskAboutEntity when clicking ask button", async () => {
    mockUseEntityDetail.mockReturnValue({
      data: mockEntityData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(EntityDetailCard, defaultProps), {
      wrapper: createWrapper(),
    });

    await userEvent.click(screen.getByText("Ask about this entity"));
    expect(defaultProps.onAskAboutEntity).toHaveBeenCalledWith(
      "Deputy Mayor Horvat",
    );
  });

  it("shows edit button that opens edit dialog", () => {
    mockUseEntityDetail.mockReturnValue({
      data: mockEntityData,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(createElement(EntityDetailCard, defaultProps), {
      wrapper: createWrapper(),
    });

    const editBtn = screen.getByLabelText("Edit entity");
    expect(editBtn).toBeTruthy();
  });
});
