import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MomentCard } from "@/components/MomentCard";
import { run } from "@/lib/mockData";

const turn1Choices = run.turns[0].choices;

describe("MomentCard", () => {
  it("shows every bounded choice with its fan-fiction attribution", () => {
    render(
      <MomentCard choices={turn1Choices} locale="en" selectedChoiceId={null} onSelect={vi.fn()} />,
    );

    for (const choice of turn1Choices) {
      expect(screen.getByText(choice.label.en)).toBeVisible();
      expect(screen.getByText(new RegExp(choice.source.author))).toBeVisible();
    }
  });

  it("reports the chosen choice", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <MomentCard choices={turn1Choices} locale="en" selectedChoiceId={null} onSelect={onSelect} />,
    );

    await user.click(screen.getByText(turn1Choices[0].label.en));
    expect(onSelect).toHaveBeenCalledWith(turn1Choices[0].choiceId);
  });

  it("exposes the choices as real radios", () => {
    render(
      <MomentCard
        choices={turn1Choices}
        locale="en"
        selectedChoiceId={turn1Choices[0].choiceId}
        onSelect={vi.fn()}
      />,
    );

    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(turn1Choices.length);
    expect(radios[0]).toHaveAttribute("aria-checked", "true");
  });

  it("renders Hindi when asked", () => {
    render(
      <MomentCard choices={turn1Choices} locale="hi" selectedChoiceId={null} onSelect={vi.fn()} />,
    );
    expect(screen.getByText(turn1Choices[0].label.hi)).toBeVisible();
  });
});
