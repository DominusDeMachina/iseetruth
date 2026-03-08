import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders } from "@/test-utils";
import { InvestigationCard } from "./InvestigationCard";
import type { Investigation } from "@/hooks/useInvestigations";

const mockNavigate = vi.fn();
const mockDeleteMutate = vi.fn();

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => mockNavigate,
  Link: ({ children, ...props }: { children: React.ReactNode }) => (
    <a {...props}>{children}</a>
  ),
}));

vi.mock("@/hooks/useInvestigations", async () => {
  const actual = await vi.importActual("@/hooks/useInvestigations");
  return {
    ...actual,
    useDeleteInvestigation: () => ({
      mutate: mockDeleteMutate,
      isPending: false,
    }),
  };
});

const sampleInvestigation: Investigation = {
  id: "11111111-1111-1111-1111-111111111111",
  name: "Test Investigation",
  description: "A test description",
  created_at: "2026-03-08T12:00:00Z",
  updated_at: "2026-03-08T12:00:00Z",
  document_count: 5,
  entity_count: 12,
};

describe("InvestigationCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders card data", () => {
    renderWithProviders(
      <InvestigationCard investigation={sampleInvestigation} />,
    );

    expect(screen.getByText("Test Investigation")).toBeInTheDocument();
    expect(screen.getByText("A test description")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("navigates on card click", async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <InvestigationCard investigation={sampleInvestigation} />,
    );

    await user.click(screen.getByText("Test Investigation"));

    expect(mockNavigate).toHaveBeenCalledWith({
      to: "/investigations/$id",
      params: { id: "11111111-1111-1111-1111-111111111111" },
    });
  });

  it("opens delete confirmation dialog", async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <InvestigationCard investigation={sampleInvestigation} />,
    );

    await user.click(screen.getByLabelText("Delete investigation"));

    expect(screen.getByText("Delete Investigation?")).toBeInTheDocument();
    expect(
      screen.getByText(/and all its data will be permanently deleted/),
    ).toBeInTheDocument();
  });

  it("calls delete mutation on confirm", async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <InvestigationCard investigation={sampleInvestigation} />,
    );

    await user.click(screen.getByLabelText("Delete investigation"));
    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(mockDeleteMutate).toHaveBeenCalledWith(
      "11111111-1111-1111-1111-111111111111",
      expect.any(Object),
    );
  });
});
