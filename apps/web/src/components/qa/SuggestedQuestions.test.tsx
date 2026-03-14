import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SuggestedQuestions } from "./SuggestedQuestions";

describe("SuggestedQuestions", () => {
  it("renders questions and they are clickable", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(
      <SuggestedQuestions
        questions={["What about GreenBuild?", "Who else is involved?"]}
        status="complete"
        noResults={false}
        onQuestionClick={onClick}
      />,
    );

    expect(screen.getByText("What about GreenBuild?")).toBeDefined();
    expect(screen.getByText("Who else is involved?")).toBeDefined();

    await user.click(screen.getByText("What about GreenBuild?"));
    expect(onClick).toHaveBeenCalledWith("What about GreenBuild?");
  });

  it("shows skeleton during streaming", () => {
    render(
      <SuggestedQuestions
        questions={["Q1", "Q2"]}
        status="streaming"
        noResults={false}
        onQuestionClick={vi.fn()}
      />,
    );

    expect(screen.getByTestId("suggested-skeleton")).toBeDefined();
    expect(screen.queryByText("Q1")).toBeNull();
  });

  it("is hidden when noResults is true", () => {
    const { container } = render(
      <SuggestedQuestions
        questions={["Q1"]}
        status="complete"
        noResults={true}
        onQuestionClick={vi.fn()}
      />,
    );

    expect(container.innerHTML).toBe("");
  });

  it("is hidden when questions array is empty", () => {
    const { container } = render(
      <SuggestedQuestions
        questions={[]}
        status="complete"
        noResults={false}
        onQuestionClick={vi.fn()}
      />,
    );

    expect(container.innerHTML).toBe("");
  });
});
