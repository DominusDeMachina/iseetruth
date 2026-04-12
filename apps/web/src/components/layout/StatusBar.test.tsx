import { screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders } from "@/test-utils";
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
      data: { status: "degraded", services: { ollama: { status: "unavailable" } } },
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<StatusBar />);

    expect(screen.getByText(/degraded.*ollama/i)).toBeInTheDocument();
  });

  it("renders reduced search capability when qdrant is down", () => {
    mockUseHealthStatus.mockReturnValue({
      data: { status: "degraded", services: { qdrant: { status: "unavailable" } } },
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<StatusBar />);

    expect(screen.getByText("Reduced search capability")).toBeInTheDocument();
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

  it("renders critical state when postgres is down", () => {
    mockUseHealthStatus.mockReturnValue({
      data: {
        status: "unhealthy",
        services: {
          postgres: { status: "unavailable" },
          neo4j: { status: "healthy" },
          qdrant: { status: "healthy" },
          redis: { status: "healthy" },
          ollama: { status: "healthy" },
        },
      },
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<StatusBar />);

    expect(
      screen.getByText("System critical — core services down"),
    ).toBeInTheDocument();
  });

  it("renders critical state when redis is down", () => {
    mockUseHealthStatus.mockReturnValue({
      data: {
        status: "unhealthy",
        services: {
          postgres: { status: "healthy" },
          neo4j: { status: "healthy" },
          qdrant: { status: "healthy" },
          redis: { status: "unavailable" },
          ollama: { status: "healthy" },
        },
      },
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<StatusBar />);

    expect(
      screen.getByText("System critical — core services down"),
    ).toBeInTheDocument();
  });

  it("renders degraded (not critical) when only ollama is down", () => {
    mockUseHealthStatus.mockReturnValue({
      data: {
        status: "degraded",
        services: {
          postgres: { status: "healthy" },
          neo4j: { status: "healthy" },
          qdrant: { status: "healthy" },
          redis: { status: "healthy" },
          ollama: { status: "unavailable" },
        },
      },
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<StatusBar />);

    expect(screen.getByText(/degraded.*ollama/i)).toBeInTheDocument();
  });
});
