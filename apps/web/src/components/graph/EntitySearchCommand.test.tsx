import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

// Mock useSearchEntities
const mockSearchResults = vi.fn(() => ({
  data: [] as unknown[],
  isLoading: false,
}));
vi.mock("@/hooks/useSearchEntities", () => ({
  useSearchEntities: (...args: unknown[]) => mockSearchResults(...args),
}));

import { EntitySearchCommand } from "./EntitySearchCommand";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

const sampleResults = [
  { id: "e1", name: "John Smith", type: "person", confidence_score: 0.9, source_count: 3, evidence_strength: "corroborated" },
  { id: "e2", name: "Acme Corp", type: "organization", confidence_score: 0.8, source_count: 2, evidence_strength: "corroborated" },
  { id: "e3", name: "Berlin", type: "location", confidence_score: 0.7, source_count: 1, evidence_strength: "single_source" },
];

describe("EntitySearchCommand", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchResults.mockReturnValue({ data: [], isLoading: false });
  });

  it("renders search input when open", () => {
    render(
      createElement(EntitySearchCommand, {
        investigationId: "inv-1",
        open: true,
        onOpenChange: vi.fn(),
        onSelectEntity: vi.fn(),
      }),
      { wrapper: createWrapper() },
    );

    expect(screen.getByPlaceholderText("Search entities by name...")).toBeTruthy();
  });

  it("shows initial state when no search typed", () => {
    render(
      createElement(EntitySearchCommand, {
        investigationId: "inv-1",
        open: true,
        onOpenChange: vi.fn(),
        onSelectEntity: vi.fn(),
      }),
      { wrapper: createWrapper() },
    );

    expect(screen.getByText("Type to search entities")).toBeTruthy();
  });

  it("displays results grouped by entity type", async () => {
    mockSearchResults.mockReturnValue({ data: sampleResults, isLoading: false });

    render(
      createElement(EntitySearchCommand, {
        investigationId: "inv-1",
        open: true,
        onOpenChange: vi.fn(),
        onSelectEntity: vi.fn(),
      }),
      { wrapper: createWrapper() },
    );

    // Type a query to trigger search
    const input = screen.getByPlaceholderText("Search entities by name...");
    await userEvent.type(input, "test");

    await waitFor(() => {
      expect(screen.getByText("John Smith")).toBeTruthy();
      expect(screen.getByText("Acme Corp")).toBeTruthy();
      expect(screen.getByText("Berlin")).toBeTruthy();
    });

    // Group headings should appear
    expect(screen.getByText("People")).toBeTruthy();
    expect(screen.getByText("Organizations")).toBeTruthy();
    expect(screen.getByText("Locations")).toBeTruthy();
  });

  it("calls onSelectEntity when a result is clicked", async () => {
    const onSelect = vi.fn();
    mockSearchResults.mockReturnValue({
      data: [sampleResults[0]],
      isLoading: false,
    });

    render(
      createElement(EntitySearchCommand, {
        investigationId: "inv-1",
        open: true,
        onOpenChange: vi.fn(),
        onSelectEntity: onSelect,
      }),
      { wrapper: createWrapper() },
    );

    const input = screen.getByPlaceholderText("Search entities by name...");
    await userEvent.type(input, "john");

    await waitFor(() => {
      expect(screen.getByText("John Smith")).toBeTruthy();
    });

    await userEvent.click(screen.getByText("John Smith"));
    expect(onSelect).toHaveBeenCalledWith(sampleResults[0]);
  });

  it("shows empty state when search has no results", async () => {
    mockSearchResults.mockReturnValue({ data: [], isLoading: false });

    render(
      createElement(EntitySearchCommand, {
        investigationId: "inv-1",
        open: true,
        onOpenChange: vi.fn(),
        onSelectEntity: vi.fn(),
      }),
      { wrapper: createWrapper() },
    );

    const input = screen.getByPlaceholderText("Search entities by name...");
    await userEvent.type(input, "nonexistent");

    // Wait for debounce
    await waitFor(
      () => {
        expect(screen.getByText(/No entities matching/)).toBeTruthy();
      },
      { timeout: 500 },
    );
  });
});
