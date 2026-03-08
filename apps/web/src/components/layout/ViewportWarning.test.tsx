import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { ViewportWarning } from "./ViewportWarning";

describe("ViewportWarning", () => {
  let originalInnerWidth: number;

  beforeEach(() => {
    originalInnerWidth = window.innerWidth;
  });

  afterEach(() => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: originalInnerWidth,
    });
  });

  function setViewportWidth(width: number) {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: width,
    });
    act(() => {
      window.dispatchEvent(new Event("resize"));
    });
  }

  it("renders warning below 1280px", () => {
    setViewportWidth(1024);
    render(<ViewportWarning />);
    expect(
      screen.getByText("OSINT is designed for screens 1280px and wider"),
    ).toBeInTheDocument();
  });

  it("hidden at 1280px and above", () => {
    setViewportWidth(1280);
    render(<ViewportWarning />);
    expect(
      screen.queryByText("OSINT is designed for screens 1280px and wider"),
    ).not.toBeInTheDocument();
  });

  it("is dismissible", async () => {
    setViewportWidth(1024);
    const user = userEvent.setup();
    render(<ViewportWarning />);

    expect(
      screen.getByText("OSINT is designed for screens 1280px and wider"),
    ).toBeInTheDocument();

    const dismissButton = screen.getByRole("button", {
      name: "Dismiss viewport warning",
    });
    await user.click(dismissButton);

    expect(
      screen.queryByText("OSINT is designed for screens 1280px and wider"),
    ).not.toBeInTheDocument();
  });
});
