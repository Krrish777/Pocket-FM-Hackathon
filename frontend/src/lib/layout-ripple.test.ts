import { describe, expect, it } from "vitest";

import { buildRippleLayout } from "@/lib/layout-ripple";
import { run, type CharacterId, type CharacterView } from "@/lib/mockData";
import { RIPPLE_VIEWBOX } from "@/lib/tokens";

const CAST_ORDER: CharacterId[] = ["CH-01", "CH-02", "CH-03", "CH-04", "CH-05"];

/**
 * The layout must be frozen and total. A NaN coordinate silently drops a seat
 * from the SVG — on stage that reads as "the graph is broken", and nothing in
 * the UI would report it.
 */
describe.each(run.turns.map((t) => [`turn ${t.turnIndex}`, t.characterViews] as const))(
  "buildRippleLayout · %s",
  (_label, views) => {
    const layout = buildRippleLayout(CAST_ORDER, views);

    it("emits exactly one node per cast member", () => {
      expect(layout.nodes).toHaveLength(5);
    });

    it("assigns each character exactly one seat", () => {
      const ids = layout.nodes.map((n) => n.characterId);
      expect(new Set(ids).size).toBe(5);
    });

    it("gives every node finite coordinates inside the viewBox", () => {
      for (const node of layout.nodes) {
        expect(Number.isFinite(node.x), `${node.characterId}.x`).toBe(true);
        expect(Number.isFinite(node.y), `${node.characterId}.y`).toBe(true);
        expect(node.x).toBeGreaterThanOrEqual(0);
        expect(node.x).toBeLessThanOrEqual(RIPPLE_VIEWBOX.width);
        expect(node.y).toBeGreaterThanOrEqual(0);
        expect(node.y).toBeLessThanOrEqual(RIPPLE_VIEWBOX.height);
      }
    });

    it("carries the belief state straight through from the character view", () => {
      for (const node of layout.nodes) {
        expect(node.state).toBe(views[node.characterId].beliefState);
      }
    });

    it("is deterministic — the same turn always draws identically", () => {
      expect(buildRippleLayout(CAST_ORDER, views).nodes).toEqual(layout.nodes);
    });

    it("preserves cascade ordering within each state group", () => {
      for (const state of ["invalid", "hold", "new"] as const) {
        const orders = layout.nodes.filter((n) => n.state === state).map((n) => n.order);
        expect(orders).toEqual(orders.map((_, i) => i));
      }
    });
  },
);

describe("buildRippleLayout · seats are stable across turns", () => {
  it("keeps each character in the same seat regardless of belief state", () => {
    const firstTurnLayout = buildRippleLayout(CAST_ORDER, run.turns[0].characterViews);
    const lastTurnLayout = buildRippleLayout(CAST_ORDER, run.turns.at(-1)!.characterViews);

    for (const characterId of CAST_ORDER) {
      const a = firstTurnLayout.nodes.find((n) => n.characterId === characterId)!;
      const b = lastTurnLayout.nodes.find((n) => n.characterId === characterId)!;
      expect(b.x).toBeCloseTo(a.x);
      expect(b.y).toBeCloseTo(a.y);
    }
  });
});

describe("buildRippleLayout · degenerate input", () => {
  it("survives everyone being unaware (no divide-by-zero, no NaN)", () => {
    const blankView: CharacterView = {
      sceneText: { hi: "", en: "" },
      beliefSummary: { hi: "", en: "" },
      beliefState: "unaware",
      present: false,
      knownFactIds: [],
    };
    const allUnaware: Record<CharacterId, CharacterView> = {
      "CH-01": blankView,
      "CH-02": blankView,
      "CH-03": blankView,
      "CH-04": blankView,
      "CH-05": blankView,
    };

    const layout = buildRippleLayout(CAST_ORDER, allUnaware);
    expect(layout.nodes).toHaveLength(5);
    for (const node of layout.nodes) {
      expect(Number.isFinite(node.x)).toBe(true);
      expect(Number.isFinite(node.y)).toBe(true);
    }
  });
});
