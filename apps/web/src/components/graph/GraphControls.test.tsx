import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement } from "react";

import { GraphControls } from "./GraphControls";

function makeMockCy() {
  return {
    zoom: vi.fn(() => 1),
    width: vi.fn(() => 800),
    height: vi.fn(() => 600),
    fit: vi.fn(),
  } as unknown as import("cytoscape").Core;
}

describe("GraphControls", () => {
  it("renders cross-investigation links button when handler provided", () => {
    const cy = makeMockCy();
    render(
      createElement(GraphControls, {
        cy,
        onRelayout: vi.fn(),
        onToggleCrossInvestigation: vi.fn(),
      }),
    );

    expect(
      screen.getByRole("button", { name: "Cross-Investigation Links" }),
    ).toBeTruthy();
  });

  it("does not render cross-investigation button without handler", () => {
    const cy = makeMockCy();
    render(createElement(GraphControls, { cy, onRelayout: vi.fn() }));

    expect(
      screen.queryByRole("button", { name: "Cross-Investigation Links" }),
    ).toBeNull();
  });

  it("shows notification badge with match count", () => {
    const cy = makeMockCy();
    render(
      createElement(GraphControls, {
        cy,
        onRelayout: vi.fn(),
        onToggleCrossInvestigation: vi.fn(),
        crossInvestigationCount: 5,
        crossInvestigationOpen: false,
      }),
    );

    expect(screen.getByText("5")).toBeTruthy();
  });

  it("hides badge when panel is open", () => {
    const cy = makeMockCy();
    render(
      createElement(GraphControls, {
        cy,
        onRelayout: vi.fn(),
        onToggleCrossInvestigation: vi.fn(),
        crossInvestigationCount: 5,
        crossInvestigationOpen: true,
      }),
    );

    expect(screen.queryByText("5")).toBeNull();
  });

  it("calls toggle handler on click", async () => {
    const cy = makeMockCy();
    const onToggle = vi.fn();
    render(
      createElement(GraphControls, {
        cy,
        onRelayout: vi.fn(),
        onToggleCrossInvestigation: onToggle,
      }),
    );

    await userEvent.click(
      screen.getByRole("button", { name: "Cross-Investigation Links" }),
    );
    expect(onToggle).toHaveBeenCalledOnce();
  });
});
