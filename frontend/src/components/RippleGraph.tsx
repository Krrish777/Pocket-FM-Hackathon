"use client";

import { motion } from "framer-motion";
import { useMemo } from "react";

import { buildRippleLayout, type NodeState } from "@/lib/layout-ripple";
import type { RippleResult } from "@/lib/mockData";
import { CASCADE, EASE, RIPPLE_VIEWBOX } from "@/lib/tokens";

/**
 * The Ripple Map — the hero component (REQUIREMENTS.md §6 Screen 4).
 *
 * This is simultaneously the wow moment and the trust moment: it has to look
 * arresting *and* be the actual evidence for "guaranteed consistent". It is one
 * of only two places in the app with assertive motion.
 *
 * Everything is hand-authored SVG on frozen coordinates (see layout-ripple.ts)
 * — positions never animate, only opacity/scale/color, so the graph never
 * reads as a physics simulation. The 2026-07-25 redesign re-choreographs the
 * cascade (fork glow burst, a "pop" on hold/invalid instead of a flat tween)
 * but keeps the CASCADE timing envelope from DESIGN.md §6.7 so the counters
 * beside the graph and the forward-button gate in Ripple.tsx stay in sync.
 */

const NODE_RADIUS = 4;
const FORK_RADIUS = 5;

/** Resting appearance — every node starts untouched, then earns its state. */
const UNTOUCHED = {
  fill: "var(--color-shell-raised)",
  stroke: "var(--color-ink-line)",
  opacity: 1,
  r: NODE_RADIUS,
};

const FINAL: Record<NodeState, Record<string, string | number | number[]>> = {
  fork: {
    fill: "var(--color-accent)",
    stroke: "var(--color-accent)",
    opacity: 1,
    r: FORK_RADIUS,
  },
  // Invalidated: a brief pop before settling dim (0.35 opacity) and shrunk.
  invalid: {
    fill: "var(--color-state-invalid)",
    stroke: "var(--color-state-invalid)",
    opacity: 0.35,
    r: [NODE_RADIUS, NODE_RADIUS * 1.35, NODE_RADIUS * 0.75],
  },
  // Held: a confirming pop as it brightens, not a flat fade-in.
  hold: {
    fill: "var(--color-state-hold)",
    stroke: "var(--color-state-hold)",
    opacity: 1,
    r: [NODE_RADIUS, NODE_RADIUS * 1.25, NODE_RADIUS],
  },
  new: {
    fill: "var(--color-state-new)",
    stroke: "var(--color-state-new)",
    opacity: 1,
    r: [NODE_RADIUS * 0.5, NODE_RADIUS * 1.2, NODE_RADIUS],
  },
};

/** Absolute start time for a node, from its phase offset + position in the stagger. */
function delayFor(state: NodeState, order: number): number {
  switch (state) {
    case "invalid":
      return CASCADE.invalid.at + order * CASCADE.invalid.stagger;
    case "hold":
      return CASCADE.hold.at + order * CASCADE.hold.stagger;
    case "new":
      return CASCADE.new.at + order * CASCADE.new.stagger;
    case "fork":
      return CASCADE.fork.at;
  }
}

function durationFor(state: NodeState): number {
  switch (state) {
    case "invalid":
      return CASCADE.invalid.duration;
    case "hold":
      return CASCADE.hold.duration;
    case "new":
      return CASCADE.new.duration;
    case "fork":
      return CASCADE.fork.duration;
  }
}

export function RippleGraph({
  ripple,
  running,
}: {
  ripple: RippleResult;
  /** Gates the cascade so it plays once, when the screen is actually shown. */
  running: boolean;
}) {
  const layout = useMemo(() => buildRippleLayout(ripple), [ripple]);

  const positions = useMemo(
    () => new Map(layout.nodes.map((node) => [node.factId, node])),
    [layout],
  );

  /** An edge dies with the node it feeds — its stagger has to match. */
  const edgeDelay = (toFactId: string) => {
    const node = positions.get(toFactId);
    return node ? delayFor(node.state, node.order) : 0;
  };

  return (
    <svg
      viewBox={`0 0 ${RIPPLE_VIEWBOX.width} ${RIPPLE_VIEWBOX.height}`}
      className="h-full w-full"
      role="img"
      aria-label="Ripple map of invalidated, held and newly required facts"
    >
      <g>
        {layout.edges.map((edge, i) => {
          const from = positions.get(edge.from);
          const to = positions.get(edge.to);
          if (!from || !to) return null;

          return (
            <motion.line
              key={`${edge.from}-${edge.to}-${i}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke="var(--color-ink-line)"
              strokeWidth={1}
              initial={{ opacity: 0.4 }}
              animate={running ? { opacity: edge.dies ? 0.1 : 0.4 } : { opacity: 0.4 }}
              transition={{
                duration: CASCADE.invalid.duration,
                delay: edge.dies ? edgeDelay(edge.to) : 0,
                ease: EASE.canon,
              }}
            />
          );
        })}
      </g>

      <g>
        {/* The fork's glow burst — a soft gradient ring expanding once, under
            everything else, so the pulse reads as light rather than a shape. */}
        <motion.circle
          cx={layout.fork.x}
          cy={layout.fork.y}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth={2}
          initial={{ r: 0, opacity: 0 }}
          animate={
            running
              ? { r: [0, FORK_RADIUS * 5], opacity: [0.9, 0] }
              : { r: 0, opacity: 0 }
          }
          transition={{
            duration: CASCADE.fork.duration * 2,
            delay: CASCADE.fork.at,
            ease: EASE.canon,
          }}
        />

        {layout.nodes.map((node) => {
          const isNew = node.state === "new";
          const delay = delayFor(node.state, node.order);

          return (
            <g key={node.factId}>
              {/* New facts carry a ring that expands as they arrive — two
                  staggered rings (accent → state-new) read as a shimmer. */}
              {isNew ? (
                <>
                  <motion.circle
                    cx={node.x}
                    cy={node.y}
                    fill="none"
                    stroke="var(--color-accent)"
                    strokeWidth={1}
                    initial={{ r: 0, opacity: 0 }}
                    animate={running ? { r: 10, opacity: 0 } : { r: 0, opacity: 0 }}
                    transition={{
                      duration: CASCADE.new.duration * 1.4,
                      delay,
                      ease: EASE.canon,
                    }}
                  />
                  <motion.circle
                    cx={node.x}
                    cy={node.y}
                    fill="none"
                    stroke="var(--color-state-new)"
                    strokeWidth={1}
                    initial={{ r: 0, opacity: 0 }}
                    animate={running ? { r: 8, opacity: 0.8 } : { r: 0, opacity: 0 }}
                    transition={{
                      duration: CASCADE.new.duration,
                      delay: delay + 0.08,
                      ease: EASE.canon,
                    }}
                  />
                </>
              ) : null}

              <motion.circle
                cx={node.x}
                cy={node.y}
                strokeWidth={1}
                initial={UNTOUCHED}
                animate={
                  running
                    ? node.state === "fork"
                      ? {
                          ...FINAL.fork,
                          // Pulse once: 1 → 1.8 → 1.
                          r: [FORK_RADIUS, FORK_RADIUS * 1.8, FORK_RADIUS],
                        }
                      : FINAL[node.state]
                    : UNTOUCHED
                }
                transition={{
                  duration: durationFor(node.state),
                  delay,
                  ease: EASE.canon,
                }}
              />
            </g>
          );
        })}
      </g>
    </svg>
  );
}
