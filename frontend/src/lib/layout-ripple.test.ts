import { describe, expect, it } from "vitest";

import { buildRippleLayout } from "@/lib/layout-ripple";
import { rippleALTA, rippleALTC } from "@/lib/mockData";
import { RIPPLE_VIEWBOX } from "@/lib/tokens";

/**
 * The layout must be frozen and total. A NaN coordinate silently drops a node
 * from the SVG — on stage that reads as "the graph is broken", and nothing in
 * the UI would report it.
 */
describe.each([
  ["ALT-A", rippleALTA],
  ["ALT-C", rippleALTC],
])("buildRippleLayout · %s", (_label, ripple) => {
  const layout = buildRippleLayout(ripple);
  const expectedNodes =
    ripple.invalidated.length + ripple.held.length + ripple.newNeeded.length + 1;

  it("emits one node per fact, plus the fork", () => {
    expect(layout.nodes).toHaveLength(expectedNodes);
    expect(layout.fork.state).toBe("fork");
  });

  it("gives every node finite coordinates inside the viewBox", () => {
    for (const node of layout.nodes) {
      expect(Number.isFinite(node.x), `${node.factId}.x`).toBe(true);
      expect(Number.isFinite(node.y), `${node.factId}.y`).toBe(true);
      expect(node.x).toBeGreaterThanOrEqual(0);
      expect(node.x).toBeLessThanOrEqual(RIPPLE_VIEWBOX.width);
      expect(node.y).toBeGreaterThanOrEqual(0);
      expect(node.y).toBeLessThanOrEqual(RIPPLE_VIEWBOX.height);
    }
  });

  it("assigns each fact exactly one node", () => {
    const ids = layout.nodes.map((n) => n.factId);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("connects every edge to nodes that exist", () => {
    const ids = new Set(layout.nodes.map((n) => n.factId));
    for (const edge of layout.edges) {
      expect(ids, edge.from).toContain(edge.from);
      expect(ids, edge.to).toContain(edge.to);
    }
  });

  it("marks exactly the invalidated branch as dying", () => {
    const dying = layout.edges.filter((e) => e.dies);
    expect(dying).toHaveLength(ripple.invalidated.length);
  });

  it("is deterministic — the same ripple always draws identically", () => {
    // Rehearsal and the live run must produce the same picture.
    expect(buildRippleLayout(ripple).nodes).toEqual(layout.nodes);
  });

  it("preserves cascade ordering within each state group", () => {
    for (const state of ["invalid", "hold", "new"] as const) {
      const orders = layout.nodes
        .filter((n) => n.state === state)
        .map((n) => n.order);
      expect(orders).toEqual(orders.map((_, i) => i));
    }
  });
});

describe("buildRippleLayout · degenerate input", () => {
  it("survives a ripple with nothing in it", () => {
    const layout = buildRippleLayout({
      rippleId: "RP-EMPTY",
      invalidated: [],
      held: [],
      newNeeded: [],
    });
    expect(layout.nodes).toHaveLength(1);
    expect(layout.edges).toHaveLength(0);
    expect(Number.isFinite(layout.fork.x)).toBe(true);
  });

  it("survives a single invalidated fact (no divide-by-zero on the curve)", () => {
    const layout = buildRippleLayout({
      rippleId: "RP-ONE",
      invalidated: [
        { factId: "F-X", summary: { hi: "क", en: "k" }, establishedIn: "E01" },
      ],
      held: [],
      newNeeded: [],
    });
    const node = layout.nodes.find((n) => n.factId === "F-X");
    expect(Number.isFinite(node?.x)).toBe(true);
    expect(Number.isFinite(node?.y)).toBe(true);
  });
});
