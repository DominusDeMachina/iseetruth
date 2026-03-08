import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SystemStatusPage } from "./SystemStatusPage";
import type { HealthResponse } from "@/hooks/useHealthStatus";

const mockHealthData: HealthResponse = {
  status: "healthy",
  timestamp: "2026-03-08T14:30:00Z",
  services: {
    postgres: { status: "healthy", detail: "Connected" },
    neo4j: {
      status: "healthy",
      detail: "Connected, server agent: Neo4j/5.x",
    },
    qdrant: { status: "healthy", detail: "Connected, version: 1.17.0" },
    redis: { status: "healthy", detail: "Connected" },
    ollama: {
      status: "healthy",
      detail: "Running, all models ready",
      models_ready: true,
      models: [
        { name: "qwen3.5:9b", available: true },
        { name: "qwen3-embedding:8b", available: true },
      ],
    },
  },
  warnings: [],
};

const mockUseHealthStatus = vi.fn();

vi.mock("@/hooks/useHealthStatus", () => ({
  useHealthStatus: () => mockUseHealthStatus(),
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

describe("SystemStatusPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading skeleton initially", () => {
    mockUseHealthStatus.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });

    renderWithProviders(<SystemStatusPage />);

    expect(screen.getByText("System Status")).toBeInTheDocument();
    // Loading skeletons have animate-pulse class
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders all 5 services when data returns", () => {
    mockUseHealthStatus.mockReturnValue({
      data: mockHealthData,
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<SystemStatusPage />);

    expect(screen.getByText("postgres")).toBeInTheDocument();
    expect(screen.getByText("neo4j")).toBeInTheDocument();
    expect(screen.getByText("qdrant")).toBeInTheDocument();
    expect(screen.getByText("redis")).toBeInTheDocument();
    expect(screen.getByText("Ollama")).toBeInTheDocument();
  });

  it("shows correct status badges", () => {
    const degradedData: HealthResponse = {
      ...mockHealthData,
      status: "degraded",
      services: {
        ...mockHealthData.services,
        redis: { status: "unhealthy", detail: "Connection refused" },
      },
    };

    mockUseHealthStatus.mockReturnValue({
      data: degradedData,
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<SystemStatusPage />);

    expect(screen.getByText("System Degraded")).toBeInTheDocument();
    // There should be both Healthy and Unhealthy badges
    const healthyBadges = screen.getAllByText("Healthy");
    expect(healthyBadges.length).toBeGreaterThan(0);
    expect(screen.getByText("Unhealthy")).toBeInTheDocument();
  });

  it("shows model readiness for Ollama", () => {
    mockUseHealthStatus.mockReturnValue({
      data: mockHealthData,
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<SystemStatusPage />);

    expect(screen.getByText("qwen3.5:9b")).toBeInTheDocument();
    expect(screen.getByText("qwen3-embedding:8b")).toBeInTheDocument();
    expect(screen.getAllByText("Available")).toHaveLength(2);
  });

  it("shows error state when backend unreachable", () => {
    mockUseHealthStatus.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    renderWithProviders(<SystemStatusPage />);

    expect(screen.getByText("Backend Unreachable")).toBeInTheDocument();
    expect(
      screen.getByText(/Unable to connect to the API server/),
    ).toBeInTheDocument();
  });

  it("shows warnings when present", () => {
    const warningData: HealthResponse = {
      ...mockHealthData,
      warnings: ["System RAM below recommended 16GB minimum"],
    };

    mockUseHealthStatus.mockReturnValue({
      data: warningData,
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<SystemStatusPage />);

    expect(screen.getByText("Warnings")).toBeInTheDocument();
    expect(
      screen.getByText("System RAM below recommended 16GB minimum"),
    ).toBeInTheDocument();
  });
});
