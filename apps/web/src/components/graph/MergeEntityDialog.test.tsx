import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MergeEntityDialog } from "./MergeEntityDialog";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("MergeEntityDialog", () => {
  const defaultProps = {
    investigationId: "inv-1",
    sourceEntityId: "entity-1",
    sourceEntityName: "Dep. Mayor Horvat",
    sourceEntityType: "person",
    open: true,
    onOpenChange: vi.fn(),
  };

  it("renders dialog with source entity name", () => {
    render(<MergeEntityDialog {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Merge Entity")).toBeInTheDocument();
    expect(screen.getByText("Dep. Mayor Horvat")).toBeInTheDocument();
  });

  it("shows search input for merge target", () => {
    render(<MergeEntityDialog {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.getByPlaceholderText("Search person entities..."),
    ).toBeInTheDocument();
  });

  it("does not render when open is false", () => {
    render(<MergeEntityDialog {...defaultProps} open={false} />, {
      wrapper: createWrapper(),
    });

    expect(screen.queryByText("Merge Entity")).not.toBeInTheDocument();
  });
});
