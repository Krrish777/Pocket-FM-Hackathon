"use client";

import { motion } from "framer-motion";
import { useMemo } from "react";

import { buildRippleLayout, type NodeState } from "@/lib/layout-ripple";
import { t, type Character, type CharacterId, type CharacterView, type Locale } from "@/lib/mockData";
import { CASCADE, EASE, RIPPLE_VIEWBOX } from "@/lib/tokens";

/**
 * The Ripple Map — the hero component (REQUIREMENTS.md §6 Screen 4), now a
 * character-belief cascade (S2). Five fixed seats, one per cast member
 * (never abstract fact-nodes, project_context.md §7.2) — each settles into
 * `invalid` (a belief just got overturned), `hold` (still true), `new` (just
 * learned something), or `unaware` (untouched this turn, reuses the resting
 * style rather than a fifth reserved color).
 *
 * Positions are frozen per seat (layout-ripple.ts) — only fill/scale/opacity
 * animate, so the graph never reads as a physics simulation, and the same
 * character always occupies the same seat turn to turn.
 */

const NODE_RADIUS = 20;

const UNTOUCHED = {
  fill: "var(--color-shell-raised)",
  stroke: "var(--color-ink-line)",
  opacity: 1,
  r: NODE_RADIUS,
};

const FINAL: Record<NodeState, Record<string, string | number | number[]>> = {
  invalid: {
    fill: "var(--color-state-invalid)",
    stroke: "var(--color-state-invalid)",
    opacity: 1,
    r: [NODE_RADIUS, NODE_RADIUS * 1.3, NODE_RADIUS],
  },
  hold: {
    fill: "var(--color-state-hold)",
    stroke: "var(--color-state-hold)",
    opacity: 1,
    r: [NODE_RADIUS, NODE_RADIUS * 1.2, NODE_RADIUS],
  },
  new: {
    fill: "var(--color-state-new)",
    stroke: "var(--color-state-new)",
    opacity: 1,
    r: [NODE_RADIUS * 0.6, NODE_RADIUS * 1.25, NODE_RADIUS],
  },
  unaware: UNTOUCHED,
};

function delayFor(state: NodeState, order: number): number {
  switch (state) {
    case "invalid":
      return CASCADE.invalid.at + order * CASCADE.invalid.stagger;
    case "hold":
      return CASCADE.hold.at + order * CASCADE.hold.stagger;
    case "new":
      return CASCADE.new.at + order * CASCADE.new.stagger;
    case "unaware":
      return 0;
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
    case "unaware":
      return 0;
  }
}

export function RippleGraph({
  castOrder,
  views,
  characters,
  locale,
  running,
}: {
  castOrder: CharacterId[];
  views: Record<CharacterId, CharacterView>;
  characters: Character[];
  locale: Locale;
  /** Gates the cascade so it plays once, when the screen is actually shown. */
  running: boolean;
}) {
  const layout = useMemo(() => buildRippleLayout(castOrder, views), [castOrder, views]);
  const nameOf = (id: CharacterId) => {
    const c = characters.find((candidate) => candidate.id === id);
    return c ? t(c.name, locale) : id;
  };

  return (
    <div className="relative h-full w-full">
      <svg
        viewBox={`0 0 ${RIPPLE_VIEWBOX.width} ${RIPPLE_VIEWBOX.height}`}
        className="h-full w-full"
        role="img"
        aria-label="Cast belief map — what each character now believes"
      >
        <g>
          {layout.nodes.map((node) => (
            <motion.line
              key={node.characterId}
              x1={layout.fork.x}
              y1={layout.fork.y}
              x2={node.x}
              y2={node.y}
              stroke="var(--color-ink-line)"
              strokeWidth={1}
              initial={{ opacity: 0.35 }}
              animate={running ? { opacity: node.state === "invalid" ? 0.15 : 0.35 } : { opacity: 0.35 }}
              transition={{ duration: CASCADE.invalid.duration, delay: delayFor(node.state, node.order), ease: EASE.canon }}
            />
          ))}
        </g>

        {/* The fork's glow burst — the choice that just landed, under everything else. */}
        <motion.circle
          cx={layout.fork.x}
          cy={layout.fork.y}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth={2}
          initial={{ r: 0, opacity: 0 }}
          animate={running ? { r: [0, NODE_RADIUS * 4], opacity: [0.9, 0] } : { r: 0, opacity: 0 }}
          transition={{ duration: CASCADE.fork.duration * 2, delay: CASCADE.fork.at, ease: EASE.canon }}
        />
        <circle cx={layout.fork.x} cy={layout.fork.y} r={3} fill="var(--color-accent)" />

        {layout.nodes.map((node) => {
          const name = nameOf(node.characterId);
          const delay = delayFor(node.state, node.order);

          return (
            <g key={node.characterId}>
              <motion.circle
                cx={node.x}
                cy={node.y}
                strokeWidth={1.5}
                initial={UNTOUCHED}
                animate={running ? FINAL[node.state] : UNTOUCHED}
                transition={{ duration: durationFor(node.state), delay, ease: EASE.canon }}
              />
              <text
                x={node.x}
                y={node.y}
                textAnchor="middle"
                dominantBaseline="central"
                fill="var(--color-ink-bright)"
                style={{ font: "600 16px var(--font-story)", pointerEvents: "none" }}
              >
                {name.charAt(0)}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Name labels as an HTML overlay — real text (font, color, i18n) rather
          than fighting SVG font metrics for something this legibility-critical. */}
      {layout.nodes.map((node) => (
        <span
          key={node.characterId}
          className="type-index text-ink-muted pointer-events-none absolute -translate-x-1/2 whitespace-nowrap normal-case"
          style={{
            left: `${(node.x / RIPPLE_VIEWBOX.width) * 100}%`,
            top: `${(node.y / RIPPLE_VIEWBOX.height) * 100}%`,
            marginTop: NODE_RADIUS + 8,
          }}
        >
          {nameOf(node.characterId)}
        </span>
      ))}
    </div>
  );
}
