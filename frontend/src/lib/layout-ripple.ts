import type { Fact, RippleResult } from "@/lib/mockData";
import { hashString, seededRandom } from "@/lib/procedural";
import { RIPPLE_VIEWBOX } from "@/lib/tokens";

/**
 * Frozen layout for the Ripple Map.
 *
 * FRONTEND_TECH_STACK.md §3 is explicit: no graph library, no force-directed
 * physics. The dataset is small and known ahead of time, and a simulation would
 * look janky next to a hand-authored animation. Positions are computed once
 * from the seed data and frozen.
 *
 * The composition reads left-to-right as cause-and-effect:
 *   · the surviving canon is a two-row trunk along the lower half;
 *   · the FORK sits on that trunk;
 *   · invalidated facts sweep up and away from the fork on a dying branch;
 *   · newly-required facts wait in a column on the right.
 *
 * Jitter is seeded per factId, so the same ripple always draws identically —
 * a rehearsal and the live run produce the same picture.
 */

export type NodeState = "fork" | "invalid" | "hold" | "new";

export type RippleNode = {
  factId: string;
  state: NodeState;
  x: number;
  y: number;
  /** Position within its own state group — drives the cascade stagger. */
  order: number;
  summaryKey: string;
};

export type RippleEdge = { from: string; to: string; dies: boolean };

export type RippleLayout = {
  nodes: RippleNode[];
  edges: RippleEdge[];
  fork: RippleNode;
};

const { width: W, height: H } = RIPPLE_VIEWBOX;

const FORK_ID = "__fork__";
const FORK_X = 232;
const FORK_Y = 268;

function jitter(factId: string, amount: number): [number, number] {
  const random = seededRandom(hashString(factId));
  return [(random() - 0.5) * amount, (random() - 0.5) * amount];
}

/** Held facts: a two-row trunk across the lower half — the surviving spine. */
function layoutHeld(facts: Fact[]): RippleNode[] {
  const perRow = Math.ceil(facts.length / 2);

  return facts.map((fact, i) => {
    const row = i < perRow ? 0 : 1;
    const indexInRow = row === 0 ? i : i - perRow;
    const countInRow = row === 0 ? perRow : facts.length - perRow;
    const spread = (W - 150) / Math.max(countInRow - 1, 1);
    const [dx, dy] = jitter(fact.factId, 16);

    return {
      factId: fact.factId,
      state: "hold" as const,
      x: 75 + indexInRow * spread + dx,
      y: (row === 0 ? 268 : 348) + dy,
      order: i,
      summaryKey: fact.factId,
    };
  });
}

/** Invalidated facts: a branch curving up and right, away from the fork. */
function layoutInvalid(facts: Fact[]): RippleNode[] {
  return facts.map((fact, i) => {
    const t = facts.length === 1 ? 0.5 : i / (facts.length - 1);
    // Quadratic Bézier from just past the fork to the upper right.
    // The control point sits above the canvas so the arc fills the upper half
    // instead of leaving a quarter of the viewBox empty.
    const p0 = { x: FORK_X + 40, y: FORK_Y - 30 };
    const p1 = { x: FORK_X + 180, y: -30 };
    const p2 = { x: W - 190, y: 110 };
    const inv = 1 - t;

    const [dx, dy] = jitter(fact.factId, 20);

    return {
      factId: fact.factId,
      state: "invalid" as const,
      x: inv * inv * p0.x + 2 * inv * t * p1.x + t * t * p2.x + dx,
      y: inv * inv * p0.y + 2 * inv * t * p1.y + t * t * p2.y + dy,
      order: i,
      summaryKey: fact.factId,
    };
  });
}

/** New facts: a column on the right — open questions the branch created. */
function layoutNew(facts: Fact[]): RippleNode[] {
  const spacing = 74;
  const top = H / 2 - ((facts.length - 1) * spacing) / 2 - 40;

  return facts.map((fact, i) => ({
    factId: fact.factId,
    state: "new" as const,
    x: W - 72,
    y: top + i * spacing,
    order: i,
    summaryKey: fact.factId,
  }));
}

export function buildRippleLayout(ripple: RippleResult): RippleLayout {
  const fork: RippleNode = {
    factId: FORK_ID,
    state: "fork",
    x: FORK_X,
    y: FORK_Y,
    order: 0,
    summaryKey: FORK_ID,
  };

  const held = layoutHeld(ripple.held);
  const invalid = layoutInvalid(ripple.invalidated);
  const created = layoutNew(ripple.newNeeded);

  const edges: RippleEdge[] = [];

  // The surviving trunk: chain each row, then stitch the rows together.
  const perRow = Math.ceil(held.length / 2);
  held.forEach((node, i) => {
    const sameRow = i < perRow ? i < perRow - 1 : i < held.length - 1;
    if (sameRow) edges.push({ from: node.factId, to: held[i + 1].factId, dies: false });
    if (i < perRow && i + perRow < held.length && i % 3 === 0) {
      edges.push({ from: node.factId, to: held[i + perRow].factId, dies: false });
    }
  });

  // The fork sits on the trunk.
  if (held.length > 0) {
    edges.push({ from: held[0].factId, to: FORK_ID, dies: false });
    const anchor = held[Math.min(perRow, held.length - 1)];
    edges.push({ from: FORK_ID, to: anchor.factId, dies: false });
  }

  // The dying branch: fork → first invalidated, then chained.
  invalid.forEach((node, i) => {
    edges.push({
      from: i === 0 ? FORK_ID : invalid[i - 1].factId,
      to: node.factId,
      dies: true,
    });
  });

  // New facts hang off the end of the dead branch — they exist *because* it died.
  const branchTail = invalid.at(-1)?.factId ?? FORK_ID;
  created.forEach((node) => {
    edges.push({ from: branchTail, to: node.factId, dies: false });
  });

  return { nodes: [fork, ...held, ...invalid, ...created], edges, fork };
}
