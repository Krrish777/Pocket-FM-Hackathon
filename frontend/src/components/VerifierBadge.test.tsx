import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VerifierBadge } from "@/components/VerifierBadge";
import { defectDemo, run } from "@/lib/mockData";

const turn1Verifier = run.turns[0].verifier;

/**
 * Both states have to be right: the green one is the everyday payoff, the amber
 * one is the proof shown on stage. A flagged verdict that renders without its
 * citation would look like an unexplained error rather than evidence.
 */
describe("VerifierBadge", () => {
  it("reports a consistent verdict with the fact count it verified against", () => {
    render(<VerifierBadge verifier={turn1Verifier} locale="en" />);

    const badge = screen.getByTestId("verifier-badge");
    expect(badge).toHaveAttribute("data-status", "ok");
    expect(badge).toHaveTextContent("CANON-CONSISTENT");
    if (turn1Verifier.status === "ok") {
      expect(badge).toHaveTextContent(String(turn1Verifier.verifiedAgainst));
    }
  });

  it("renders the flagged verdict with both sides of the contradiction", () => {
    render(<VerifierBadge verifier={defectDemo.verifier} locale="en" />);

    const badge = screen.getByTestId("verifier-badge");
    expect(badge).toHaveAttribute("data-status", "flagged");
    expect(badge).toHaveTextContent("CONTRADICTION FLAGGED");
    expect(badge).toHaveTextContent("Ray Kessler is alive and testifying");
    expect(badge).toHaveTextContent("Ray Kessler was dealt with per Harry's Code");
    // Without a source reference the claim is unfalsifiable.
    expect(badge).toHaveTextContent("Turn 4");
  });

  it("switches locale", () => {
    render(<VerifierBadge verifier={turn1Verifier} locale="hi" />);
    expect(screen.getByTestId("verifier-badge")).toHaveTextContent("कैनन-संगत");
  });
});
