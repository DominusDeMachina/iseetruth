import { screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders } from "@/test-utils";
import { InvestigationList } from "./InvestigationList";
import type { InvestigationListResponse } from "@/hooks/useInvestigations";

const mockInvestigations: InvestigationListResponse = {
  items: [
    {
      id: "11111111-1111-1111-1111-111111111111",
      name: "Test Investigation",
      description: "A test description",
      created_at: "2026-03-08T12:00:00Z",
      updated_at: "2026-03-08T12:00:00Z",
      document_count: 5,
      entity_count: 12,
    },
    {
      id: "22222222-2222-2222-2222-222222222222",
      name: "Second Investigation",
      description: null,
      created_at: "2026-03-07T10:00:00Z",
      updated_at: "2026-03-07T10:00:00Z",
      document_count: 0,
      entity_count: 0,
    },
  ],
  total: 2,
};

const mockUseInvestigations = vi.fn();

vi.mock("@/hooks/useInvestigations", async () => {
  const actual = await vi.importActual("@/hooks/useInvestigations");
  return {
    ...actual,
    useInvestigations: () => mockUseInvestigations(),
    useDeleteInvestigation: () => ({
      mutate: vi.fn(),
      isPending: false,
    }),
  };
});

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children, ...props }: { children: React.ReactNode }) => (
    <a {...props}>{children}</a>
  ),
}));

describe("InvestigationList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders investigation cards when data is loaded", () => {
    mockUseInvestigations.mockReturnValue({
      data: mockInvestigations,
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<InvestigationList />);

    expect(screen.getByText("Test Investigation")).toBeInTheDocument();
    expect(screen.getByText("Second Investigation")).toBeInTheDocument();
    expect(screen.getByText("A test description")).toBeInTheDocument();
  });

  it("shows empty state when no investigations exist", () => {
    mockUseInvestigations.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<InvestigationList />);

    expect(
      screen.getByText("Create your first investigation to get started"),
    ).toBeInTheDocument();
  });

  it("renders loading skeleton cards", () => {
    mockUseInvestigations.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });

    renderWithProviders(<InvestigationList />);

    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBe(3);
  });

  it("shows error state when fetch fails", () => {
    mockUseInvestigations.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    renderWithProviders(<InvestigationList />);

    expect(
      screen.getByText("Failed to load investigations"),
    ).toBeInTheDocument();
  });
});
