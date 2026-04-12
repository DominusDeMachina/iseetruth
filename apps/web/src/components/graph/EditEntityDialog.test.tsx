import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

const mockMutate = vi.fn();
vi.mock("@/hooks/useEntityMutations", () => ({
  useUpdateEntity: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

import { EditEntityDialog } from "./EditEntityDialog";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

const defaultProps = {
  investigationId: "inv-1",
  entityId: "entity-1",
  entityName: "Deputy Mayor Horvat",
  entityType: "person",
  sourceAnnotation: "Found in records",
  aliases: ["Dep. Mayor Horvat"],
  open: true,
  onOpenChange: vi.fn(),
};

describe("EditEntityDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form pre-populated with entity data", () => {
    render(createElement(EditEntityDialog, defaultProps), {
      wrapper: createWrapper(),
    });

    const nameInput = screen.getByLabelText("Name") as HTMLInputElement;
    expect(nameInput.value).toBe("Deputy Mayor Horvat");
    expect(
      screen.getByText("Found in records", { exact: false }),
    ).toBeTruthy();
  });

  it("shows entity type as read-only", () => {
    render(createElement(EditEntityDialog, defaultProps), {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("(read-only)")).toBeTruthy();
    expect(screen.getByText("person")).toBeTruthy();
  });

  it("shows previous names as alias chips", () => {
    render(createElement(EditEntityDialog, defaultProps), {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Previous names")).toBeTruthy();
    expect(screen.getByText("Dep. Mayor Horvat")).toBeTruthy();
  });
});
