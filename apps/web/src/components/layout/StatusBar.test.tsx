import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { StatusBar } from "./StatusBar";

const mockUseHealthStatus = vi.fn();

vi.mock("@/hooks/useHealthStatus", () => ({
  useHealthStatus: () => mockUseHealthStatus(),
}));

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    to,
    className,
  }: {
    children: React.ReactNode;
    to: string;
    className?: string;
  }) => (
    <a href={to} className={className}>
      {children}
    </a>
  ),
}));

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
}

function renderWithProviders(ui: React.ReactElement) {
  const testClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={testClient}>{ui}</QueryClientProvider>,
  );
}

describe("StatusBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders healthy summary", () => {
    mockUseHealthStatus.mockReturnValue({
      data: { status: "healthy" },
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<StatusBar />);

    expect(screen.getByText("All systems operational")).toBeInTheDocument();
  });

  it("renders degraded summary", () => {
    mockUseHealthStatus.mockReturnValue({
      data: { status: "degraded" },
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<StatusBar />);

    expect(screen.getByText("System degraded")).toBeInTheDocument();
  });

  it("links to /status page", () => {
    mockUseHealthStatus.mockReturnValue({
      data: { status: "healthy" },
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<StatusBar />);

    expect(screen.getByText("/status")).toBeInTheDocument();
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/status");
  });

  it("renders loading state", () => {
    mockUseHealthStatus.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });

    renderWithProviders(<StatusBar />);

    expect(screen.getByText("Checking services...")).toBeInTheDocument();
  });

  it("renders error state when backend unreachable", () => {
    mockUseHealthStatus.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    renderWithProviders(<StatusBar />);

    expect(screen.getByText("Backend unreachable")).toBeInTheDocument();
  });
});
