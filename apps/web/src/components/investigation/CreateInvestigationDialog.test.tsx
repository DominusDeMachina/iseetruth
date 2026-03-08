import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders } from "@/test-utils";
import { CreateInvestigationDialog } from "./CreateInvestigationDialog";

const mockMutate = vi.fn();

vi.mock("@/hooks/useInvestigations", () => ({
  useCreateInvestigation: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
}));

describe("CreateInvestigationDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders trigger button and opens dialog", async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <CreateInvestigationDialog
        trigger={<button>New Investigation</button>}
      />,
    );

    await user.click(screen.getByText("New Investigation"));

    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Description")).toBeInTheDocument();
    expect(screen.getByText("Create Investigation")).toBeInTheDocument();
  });

  it("disables submit when name is empty", async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <CreateInvestigationDialog
        trigger={<button>New Investigation</button>}
      />,
    );

    await user.click(screen.getByText("New Investigation"));

    const submitButton = screen.getByText("Create Investigation");
    expect(submitButton).toBeDisabled();
  });

  it("calls mutate with form data on submit", async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <CreateInvestigationDialog
        trigger={<button>New Investigation</button>}
      />,
    );

    await user.click(screen.getByText("New Investigation"));
    await user.type(screen.getByLabelText("Name"), "My Investigation");
    await user.type(screen.getByLabelText("Description"), "A description");
    await user.click(screen.getByText("Create Investigation"));

    expect(mockMutate).toHaveBeenCalledWith(
      { name: "My Investigation", description: "A description" },
      expect.any(Object),
    );
  });
});
