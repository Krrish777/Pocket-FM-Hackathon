import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MomentCard } from "@/components/MomentCard";
import { moments } from "@/lib/mockData";

const rehearsedMoment = moments.find((m) => m.momentId === "M-0301")!;

describe("MomentCard", () => {
  it("shows the canon line and every bounded alternative", () => {
    render(
      <MomentCard
        moment={rehearsedMoment}
        episodeId="E03"
        locale="en"
        selectedAltId={null}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByText(/Aarav reaches the roof in time/)).toBeVisible();
    for (const alternative of rehearsedMoment.alternatives) {
      expect(screen.getByText(alternative.label.en)).toBeVisible();
    }
  });

  it("reports the chosen alternative", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <MomentCard
        moment={rehearsedMoment}
        episodeId="E03"
        locale="en"
        selectedAltId={null}
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByText(rehearsedMoment.alternatives[0].label.en));
    expect(onSelect).toHaveBeenCalledWith("ALT-A");
  });

  it("exposes the alternatives as real radios", () => {
    render(
      <MomentCard
        moment={rehearsedMoment}
        episodeId="E03"
        locale="en"
        selectedAltId="ALT-A"
        onSelect={vi.fn()}
      />,
    );

    // Radio semantics give arrow-key navigation and screen-reader support for
    // free; a div-with-onClick would give neither.
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(rehearsedMoment.alternatives.length);
    expect(radios[0]).toHaveAttribute("aria-checked", "true");
  });

  it("renders Hindi when asked", () => {
    render(
      <MomentCard
        moment={rehearsedMoment}
        episodeId="E03"
        locale="hi"
        selectedAltId={null}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(rehearsedMoment.originalLine.hi)).toBeVisible();
  });
});
