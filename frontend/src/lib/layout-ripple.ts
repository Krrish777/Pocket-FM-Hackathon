import type { CharacterId, CharacterView } from "@/lib/mockData";
import { RIPPLE_VIEWBOX } from "@/lib/tokens";

/**
 * Frozen layout for the Ripple Map — now a character-belief cascade (S2,
 * project_context.md §7.2: "shows the cast and what each character now
 * believes — not abstract fact-nodes"), not a fact graph.
 *
 * FRONTEND_TECH_STACK.md §3 is explicit: no graph library, no force-directed
 * physics. There are always exactly 5 seats — one per cast member — arranged
 * in a fixed pentagon around the fork point. A character's SEAT never moves
 * turn to turn (Dexter is always top-centre); only which state lights up
 * changes. That constancy is what makes the cascade legible on a projector
 * across a multi-turn run instead of re-orienting the viewer every time.
 */

export type NodeState = "invalid" | "hold" | "new" | "unaware";

export type RippleNode = {
  characterId: CharacterId;
  state: NodeState;
  x: number;
  y: number;
  /** Position within its own state group — drives the cascade stagger. */
  order: number;
};

export type RippleLayout = {
  nodes: RippleNode[];
  fork: { x: number; y: number };
};

const { width: W, height: H } = RIPPLE_VIEWBOX;
const FORK_X = W / 2;
const FORK_Y = H / 2 + 10;
const RADIUS = Math.min(W, H) / 2 - 70;

/** Top, then clockwise — a regular pentagon, one seat per cast member. */
const SEAT_ANGLES_DEG = [-90, -18, 54, 126, 198];

export function buildRippleLayout(
  castOrder: CharacterId[],
  views: Record<CharacterId, CharacterView>,
): RippleLayout {
  const orderCounters: Record<NodeState, number> = { invalid: 0, hold: 0, new: 0, unaware: 0 };

  const nodes: RippleNode[] = castOrder.map((characterId, i) => {
    const angle = (SEAT_ANGLES_DEG[i % SEAT_ANGLES_DEG.length] * Math.PI) / 180;
    const state = views[characterId].beliefState;
    const order = orderCounters[state]++;

    return {
      characterId,
      state,
      x: FORK_X + RADIUS * Math.cos(angle),
      y: FORK_Y + RADIUS * Math.sin(angle),
      order,
    };
  });

  return { nodes, fork: { x: FORK_X, y: FORK_Y } };
}
