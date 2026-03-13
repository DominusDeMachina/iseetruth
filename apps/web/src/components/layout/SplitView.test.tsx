import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { SplitView } from "./SplitView";

describe("SplitView", () => {
  it("renders left and right panels", () => {
    render(
      createElement(SplitView, {
        left: createElement("div", null, "Left Panel"),
        right: createElement("div", null, "Right Panel"),
      }),
    );

    expect(screen.getByText("Left Panel")).toBeTruthy();
    expect(screen.getByText("Right Panel")).toBeTruthy();
  });

  it("applies default 40% left split", () => {
    const { container } = render(
      createElement(SplitView, {
        left: createElement("div", null, "Left"),
        right: createElement("div", null, "Right"),
      }),
    );

    const grid = container.firstElementChild as HTMLElement;
    expect(grid.style.gridTemplateColumns).toBe("40% 4px 1fr");
  });

  it("respects custom defaultLeftPercent", () => {
    const { container } = render(
      createElement(SplitView, {
        left: createElement("div", null, "Left"),
        right: createElement("div", null, "Right"),
        defaultLeftPercent: 50,
      }),
    );

    const grid = container.firstElementChild as HTMLElement;
    expect(grid.style.gridTemplateColumns).toBe("50% 4px 1fr");
  });

  it("renders the drag handle", () => {
    const { container } = render(
      createElement(SplitView, {
        left: createElement("div", null, "Left"),
        right: createElement("div", null, "Right"),
      }),
    );

    const grid = container.firstElementChild as HTMLElement;
    // The drag handle is the second child (index 1)
    const handle = grid.children[1] as HTMLElement;
    expect(handle.className).toContain("cursor-col-resize");
  });
});
