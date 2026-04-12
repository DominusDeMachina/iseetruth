import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AddRelationshipDialog } from "./AddRelationshipDialog";

// Mock hooks
const mockMutate = vi.fn();
vi.mock("@/hooks/useEntities", () => ({
  useEntities: () => ({
    data: {
      items: [
        { id: "e1", name: "John Smith", type: "person", confidence_score: 0.9, source_count: 1, evidence_strength: "single_source", source: "extracted" },
        { id: "e2", name: "Acme Corp", type: "organization", confidence_score: 0.8, source_count: 1, evidence_strength: "single_source", source: "extracted" },
        { id: "e3", name: "Berlin", type: "location", confidence_score: 0.7, source_count: 1, evidence_strength: "single_source", source: "extracted" },
      ],
      total: 3,
      summary: { people: 1, organizations: 1, locations: 1, total: 3 },
    },
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/hooks/useEntityMutations", () => ({
  useCreateRelationship: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

function renderDialog(props = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const defaultProps = {
    investigationId: "inv-1",
    open: true,
    onOpenChange: vi.fn(),
    ...props,
  };
  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(AddRelationshipDialog, defaultProps),
    ),
  );
}

describe("AddRelationshipDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form with source entity, target entity, type, and annotation fields", () => {
    renderDialog();

    expect(screen.getByRole("heading", { name: "Add Relationship" })).toBeTruthy();
    expect(screen.getByLabelText("Source Entity")).toBeTruthy();
    expect(screen.getByLabelText("Target Entity")).toBeTruthy();
    expect(screen.getByText("Relationship Type")).toBeTruthy();
    expect(screen.getByText("WORKS_FOR")).toBeTruthy();
    expect(screen.getByText("KNOWS")).toBeTruthy();
    expect(screen.getByText("LOCATED_AT")).toBeTruthy();
    expect(screen.getByText("MENTIONED_IN")).toBeTruthy();
    expect(screen.getByText("Custom...")).toBeTruthy();
    expect(screen.getByLabelText(/Evidence/)).toBeTruthy();
  });

  it("submit button disabled when required fields are empty", () => {
    renderDialog();

    const submitButton = screen.getByRole("button", { name: "Add Relationship" });
    expect(submitButton).toBeDisabled();
  });

  it("calls mutate with correct data on successful submission", async () => {
    const onOpenChange = vi.fn();
    renderDialog({ onOpenChange });

    const user = userEvent.setup();

    // Select source entity
    const sourceSelect = screen.getByLabelText("Source Entity");
    await user.selectOptions(sourceSelect, "e1");

    // Select target entity
    const targetSelect = screen.getByLabelText("Target Entity");
    await user.selectOptions(targetSelect, "e2");

    // Select relationship type
    await user.click(screen.getByText("WORKS_FOR"));

    // Submit
    const submitButton = screen.getByRole("button", { name: "Add Relationship" });
    await user.click(submitButton);

    expect(mockMutate).toHaveBeenCalledWith(
      {
        source_entity_id: "e1",
        target_entity_id: "e2",
        type: "WORKS_FOR",
        source_annotation: null,
      },
      expect.objectContaining({
        onSuccess: expect.any(Function),
        onError: expect.any(Function),
      }),
    );
  });
});
