import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement } from "react";

import { EdgeDetailPopover } from "./EdgeDetailPopover";

const defaultProps = {
  edgeData: {
    id: "n1-WORKS_FOR-n2",
    source: "n1",
    target: "n2",
    type: "WORKS_FOR",
    confidence_score: 0.85,
  },
  sourceEntityName: "Deputy Mayor Horvat",
  targetEntityName: "City Council",
  position: { x: 300, y: 200 },
  onClose: vi.fn(),
};

describe("EdgeDetailPopover", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders edge type and confidence", () => {
    render(createElement(EdgeDetailPopover, defaultProps));

    expect(screen.getByText("WORKS_FOR")).toBeTruthy();
    expect(screen.getByText("85%")).toBeTruthy();
  });

  it("shows source and target entity names", () => {
    render(createElement(EdgeDetailPopover, defaultProps));

    expect(screen.getByText("Deputy Mayor Horvat")).toBeTruthy();
    expect(screen.getByText("City Council")).toBeTruthy();
  });

  it("calls onClose when clicking close button", async () => {
    render(createElement(EdgeDetailPopover, defaultProps));

    const popover = screen.getByRole("dialog");
    const closeBtn = within(popover).getByLabelText("Close");
    await userEvent.click(closeBtn);
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it("has correct dialog role", () => {
    render(createElement(EdgeDetailPopover, defaultProps));

    const popover = screen.getByRole("dialog");
    expect(popover.getAttribute("aria-label")).toBe(
      "Relationship details: WORKS_FOR",
    );
  });

  it("shows Manual badge when origin is manual", () => {
    render(
      createElement(EdgeDetailPopover, {
        ...defaultProps,
        edgeData: { ...defaultProps.edgeData, origin: "manual" },
      }),
    );

    expect(screen.getByText("Manual")).toBeTruthy();
  });

  it("does not show Manual badge for extracted edges", () => {
    render(createElement(EdgeDetailPopover, defaultProps));

    expect(screen.queryByText("Manual")).toBeNull();
  });

  it("displays source annotation when present", () => {
    render(
      createElement(EdgeDetailPopover, {
        ...defaultProps,
        edgeData: {
          ...defaultProps.edgeData,
          origin: "manual",
          source_annotation: "Found in financial records",
        },
      }),
    );

    expect(screen.getByText("Evidence:")).toBeTruthy();
    expect(screen.getByText("Found in financial records")).toBeTruthy();
  });

  it("renders clickable entity links when onNavigateToEntity is provided", async () => {
    const onNavigateToEntity = vi.fn();
    render(
      createElement(EdgeDetailPopover, {
        ...defaultProps,
        onNavigateToEntity,
      }),
    );

    expect(
      screen.getByText("View source entities for evidence:"),
    ).toBeTruthy();

    // Click source entity link
    const buttons = screen.getAllByRole("button").filter(
      (btn) => btn.textContent === "Deputy Mayor Horvat" || btn.textContent === "City Council",
    );
    expect(buttons.length).toBe(2);

    await userEvent.click(buttons[0]);
    expect(onNavigateToEntity).toHaveBeenCalledWith("n1");

    await userEvent.click(buttons[1]);
    expect(onNavigateToEntity).toHaveBeenCalledWith("n2");
  });
});
