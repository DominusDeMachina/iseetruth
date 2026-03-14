import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryInput } from "./QueryInput";

describe("QueryInput", () => {
  it("submits on Enter key", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<QueryInput onSubmit={onSubmit} status="idle" />);

    const input = screen.getByLabelText("Ask a question about your investigation");
    await user.type(input, "Who is Horvat?{Enter}");

    expect(onSubmit).toHaveBeenCalledWith("Who is Horvat?");
  });

  it("does not submit on Shift+Enter", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<QueryInput onSubmit={onSubmit} status="idle" />);

    const input = screen.getByLabelText("Ask a question about your investigation");
    await user.type(input, "line 1{Shift>}{Enter}{/Shift}line 2");

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables input during query processing", () => {
    const onSubmit = vi.fn();
    render(<QueryInput onSubmit={onSubmit} status="streaming" />);

    const input = screen.getByLabelText("Ask a question about your investigation");
    expect(input).toBeDisabled();
  });

  it("enables input when idle", () => {
    const onSubmit = vi.fn();
    render(<QueryInput onSubmit={onSubmit} status="idle" />);

    const input = screen.getByLabelText("Ask a question about your investigation");
    expect(input).not.toBeDisabled();
  });

  it("enables input when complete", () => {
    const onSubmit = vi.fn();
    render(<QueryInput onSubmit={onSubmit} status="complete" />);

    const input = screen.getByLabelText("Ask a question about your investigation");
    expect(input).not.toBeDisabled();
  });

  it("enables input when error", () => {
    const onSubmit = vi.fn();
    render(<QueryInput onSubmit={onSubmit} status="error" />);

    const input = screen.getByLabelText("Ask a question about your investigation");
    expect(input).not.toBeDisabled();
  });

  it("populates input with prefillQuestion", () => {
    const onSubmit = vi.fn();
    render(
      <QueryInput
        onSubmit={onSubmit}
        status="idle"
        prefillQuestion="What connections does Horvat have?"
      />,
    );

    const input = screen.getByLabelText("Ask a question about your investigation") as HTMLTextAreaElement;
    expect(input.value).toBe("What connections does Horvat have?");
  });

  it("clears input after successful submission", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<QueryInput onSubmit={onSubmit} status="idle" />);

    const input = screen.getByLabelText("Ask a question about your investigation") as HTMLTextAreaElement;
    await user.type(input, "test question{Enter}");

    expect(input.value).toBe("");
  });

  it("does not submit empty input", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<QueryInput onSubmit={onSubmit} status="idle" />);

    const input = screen.getByLabelText("Ask a question about your investigation");
    await user.click(input);
    await user.keyboard("{Enter}");

    expect(onSubmit).not.toHaveBeenCalled();
  });
});
