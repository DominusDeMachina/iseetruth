import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

const mockMutate = vi.fn();
vi.mock("@/hooks/useEntityMutations", () => ({
  useCreateEntity: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

import { AddEntityDialog } from "./AddEntityDialog";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

const defaultProps = {
  investigationId: "inv-1",
  open: true,
  onOpenChange: vi.fn(),
};

describe("AddEntityDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form with name, type, and annotation fields", () => {
    render(createElement(AddEntityDialog, defaultProps), {
      wrapper: createWrapper(),
    });

    expect(screen.getByLabelText("Name")).toBeTruthy();
    expect(screen.getByText("Type")).toBeTruthy();
    expect(screen.getByText("Person")).toBeTruthy();
    expect(screen.getByText("Organization")).toBeTruthy();
    expect(screen.getByText("Location")).toBeTruthy();
    expect(
      screen.getByPlaceholderText("Where did you find this information?"),
    ).toBeTruthy();
  });

  it("submit button disabled when name empty", () => {
    render(createElement(AddEntityDialog, defaultProps), {
      wrapper: createWrapper(),
    });

    const submitBtn = screen.getByRole("button", { name: "Add Entity" });
    expect(submitBtn).toBeDisabled();
  });

  it("calls mutate on valid submission", async () => {
    const user = userEvent.setup();

    render(createElement(AddEntityDialog, defaultProps), {
      wrapper: createWrapper(),
    });

    await user.type(screen.getByLabelText("Name"), "Viktor Novak");
    await user.click(screen.getByText("Person"));
    await user.click(screen.getByRole("button", { name: "Add Entity" }));

    expect(mockMutate).toHaveBeenCalledWith(
      { name: "Viktor Novak", type: "person", source_annotation: null },
      expect.any(Object),
    );
  });
});
