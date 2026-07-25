import { buildConstellation } from "@/lib/procedural";

/**
 * Generated cover art — stands in for `coverUrl` until real artwork exists.
 *
 * The motif is the fact-graph itself (REQUIREMENTS.md Screen 1: "fact-graph
 * pulsing faintly behind the cover"), drawn in hairlines so it belongs to the
 * Archival Terminal language rather than looking like stock placeholder art.
 */
export function ProceduralCover({ storyId }: { storyId: string }) {
  const { nodes, edges } = buildConstellation(storyId);

  return (
    <svg
      viewBox="0 0 100 150"
      preserveAspectRatio="xMidYMid slice"
      className="h-full w-full"
      aria-hidden="true"
    >
      <rect width="100" height="150" fill="var(--color-shell-base)" />

      {/* Ledger grid — the printed-archive substrate. */}
      <g stroke="var(--color-ink-line)" strokeWidth="0.25" opacity="0.55">
        {[30, 60, 90, 120].map((y) => (
          <line key={`h${y}`} x1="0" y1={y} x2="100" y2={y} />
        ))}
        {[25, 50, 75].map((x) => (
          <line key={`v${x}`} x1={x} y1="0" x2={x} y2="150" />
        ))}
      </g>

      {/* The fact graph. */}
      <g stroke="var(--color-ink-line)" strokeWidth="0.4" opacity="0.8">
        {edges.map((edge, i) => (
          <line
            key={i}
            x1={nodes[edge.from].x}
            y1={nodes[edge.from].y}
            x2={nodes[edge.to].x}
            y2={nodes[edge.to].y}
          />
        ))}
      </g>

      <g>
        {nodes.map((node, i) => (
          <circle
            key={i}
            cx={node.x}
            cy={node.y}
            r={node.r}
            fill={
              node.accent ? "var(--color-accent)" : "var(--color-ink-faint)"
            }
            opacity={node.accent ? 0.9 : 0.55}
          />
        ))}
      </g>

      {/* Legibility scrim for the title block — DESIGN.md §6.3.
          A shell-void ramp, not a decorative gradient. */}
      <rect
        x="0"
        y="82"
        width="100"
        height="68"
        fill="url(#cover-scrim)"
      />
      <defs>
        <linearGradient id="cover-scrim" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--color-shell-void)" stopOpacity="0" />
          <stop offset="55%" stopColor="var(--color-shell-void)" stopOpacity="0.85" />
          <stop offset="100%" stopColor="var(--color-shell-void)" stopOpacity="0.98" />
        </linearGradient>
      </defs>
    </svg>
  );
}
