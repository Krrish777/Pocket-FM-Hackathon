import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VerifierBadge } from "@/components/VerifierBadge";
import { defectDemo, regenerateALTA } from "@/lib/mockData";

/**
 * Both states have to be right: the green one is the everyday payoff, the amber
 * one is the proof shown on stage. A flagged verdict that renders without its
 * citation would look like an unexplained error rather than evidence.
 */
describe("VerifierBadge", () => {
  it("reports a consistent verdict with the fact count it verified against", () => {
    render(<VerifierBadge verifier={regenerateALTA.verifier} locale="en" />);

    const badge = screen.getByTestId("verifier-badge");
    expect(badge).toHaveAttribute("data-status", "ok");
    expect(badge).toHaveTextContent("CANON-CONSISTENT");
    expect(badge).toHaveTextContent("20");
  });

  it("renders the flagged verdict with both sides of the contradiction", () => {
    render(<VerifierBadge verifier={defectDemo.verifier} locale="en" />);

    const badge = screen.getByTestId("verifier-badge");
    expect(badge).toHaveAttribute("data-status", "flagged");
    expect(badge).toHaveTextContent("CONTRADICTION FLAGGED");
    expect(badge).toHaveTextContent("Devansh Iyer is present and speaking");
    expect(badge).toHaveTextContent("Devansh Iyer is not alive in this branch");
    // Without a source reference the claim is unfalsifiable.
    expect(badge).toHaveTextContent("E03");
  });

  it("switches locale", () => {
    render(<VerifierBadge verifier={regenerateALTA.verifier} locale="hi" />);
    expect(screen.getByTestId("verifier-badge")).toHaveTextContent("कैनन-संगत");
  });
});
