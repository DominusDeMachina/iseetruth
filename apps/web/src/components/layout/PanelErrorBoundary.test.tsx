import { screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders } from "@/test-utils";
import { PanelErrorBoundary } from "./PanelErrorBoundary";

// A component that throws on render
function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("Test render error");
  }
  return <div>Child rendered OK</div>;
}

describe("PanelErrorBoundary", () => {
  beforeEach(() => {
    // Suppress console.error from React and our error boundary
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("renders children when no error", () => {
    renderWithProviders(
      <PanelErrorBoundary panelName="Test Panel">
        <div>Hello world</div>
      </PanelErrorBoundary>,
    );

    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });

  it("shows fallback with panel name when child throws", () => {
    renderWithProviders(
      <PanelErrorBoundary panelName="Q&A Panel">
        <ThrowingChild shouldThrow={true} />
      </PanelErrorBoundary>,
    );

    expect(screen.getByText("Q&A Panel — Rendering error")).toBeInTheDocument();
    expect(screen.getByText("Test render error")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reload panel/i })).toBeInTheDocument();
  });

  it("shows fallback with aria-live assertive for accessibility", () => {
    renderWithProviders(
      <PanelErrorBoundary panelName="Test Panel">
        <ThrowingChild shouldThrow={true} />
      </PanelErrorBoundary>,
    );

    expect(screen.getByRole("alert")).toHaveAttribute("aria-live", "assertive");
  });

  it("resets error state when Reload Panel is clicked", () => {
    // Use a global flag to control throwing — first render throws, after reset it won't
    let shouldThrow = true;
    function ConditionalChild() {
      if (shouldThrow) throw new Error("Test render error");
      return <div>Child rendered OK</div>;
    }

    renderWithProviders(
      <PanelErrorBoundary panelName="Test Panel">
        <ConditionalChild />
      </PanelErrorBoundary>,
    );

    // Error fallback should be shown
    expect(screen.getByText("Test Panel — Rendering error")).toBeInTheDocument();

    // Stop throwing before clicking reload
    shouldThrow = false;

    // Click reload — this resets error state and remounts children
    fireEvent.click(screen.getByRole("button", { name: /reload panel/i }));

    // Children should be rendered again
    expect(screen.getByText("Child rendered OK")).toBeInTheDocument();
  });

  it("calls onError callback when error occurs", () => {
    const onError = vi.fn();
    renderWithProviders(
      <PanelErrorBoundary panelName="Test Panel" onError={onError}>
        <ThrowingChild shouldThrow={true} />
      </PanelErrorBoundary>,
    );

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(expect.any(Error));
  });

  it("truncates long error messages", () => {
    const LongErrorChild = () => {
      throw new Error("A".repeat(300));
    };

    renderWithProviders(
      <PanelErrorBoundary panelName="Test Panel">
        <LongErrorChild />
      </PanelErrorBoundary>,
    );

    // Message should be truncated to 200 chars + "..."
    const errorText = screen.getByText(/^A+\.\.\.$/);
    expect(errorText.textContent!.length).toBeLessThanOrEqual(203);
  });
});
