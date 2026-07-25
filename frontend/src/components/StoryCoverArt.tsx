import { buildConstellation } from "@/lib/procedural";

/**
 * A hand-authored mood per story — not procedural, because these three
 * stories are named/curated content, not an infinite catalog. Stands in for
 * real cover photography (none exists yet; see `coverUrl` in mockData.ts).
 */
const PALETTE: Record<
  string,
  { backdrop: string; glow: string; accent: string }
> = {
  "ST-01": {
    // Rain-slick night, a lamppost's amber pool.
    backdrop:
      "radial-gradient(120% 90% at 20% 85%, #4a2a1a 0%, #241328 38%, #0c0a14 72%, #060508 100%)",
    glow: "radial-gradient(circle at 22% 88%, rgb(255 176 90 / 0.55), transparent 32%)",
    accent: "#ff8a5b",
  },
  "ST-02": {
    // Misty lake below storm-grey mountains.
    backdrop:
      "radial-gradient(120% 90% at 50% 15%, #2c3b45 0%, #16232c 40%, #0a1116 75%, #05080a 100%)",
    glow: "radial-gradient(circle at 52% 18%, rgb(216 100 255 / 0.35), transparent 34%)",
    accent: "#e879f9",
  },
  "ST-03": {
    // Desert dunes at sunset, a map laid on the sand.
    backdrop:
      "radial-gradient(120% 90% at 70% 20%, #6b2f3a 0%, #3a2144 42%, #16101f 75%, #08060c 100%)",
    glow: "radial-gradient(circle at 68% 22%, rgb(255 140 90 / 0.45), transparent 32%)",
    accent: "#ffb15b",
  },
};

/**
 * Card backdrop for the Shelf redesign — a CSS-generated moody gradient
 * (no photography assets exist) with the constellation motif from
 * `ProceduralCover` layered on top, restyled to read against a colour field
 * instead of a flat shell surface.
 */
export function StoryCoverArt({ storyId }: { storyId: string }) {
  const palette = PALETTE[storyId] ?? PALETTE["ST-01"];
  const { nodes, edges } = buildConstellation(storyId);

  return (
    <div
      className="absolute inset-0"
      style={{ background: palette.backdrop }}
      aria-hidden="true"
    >
      <div className="absolute inset-0" style={{ background: palette.glow }} />

      <svg
        viewBox="0 0 100 150"
        preserveAspectRatio="xMidYMid slice"
        className="absolute inset-0 h-full w-full"
      >
        <g stroke="white" strokeOpacity="0.25" strokeWidth="0.35">
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
              r={node.accent ? node.r + 1.4 : node.r}
              fill={node.accent ? palette.accent : "white"}
              opacity={node.accent ? 1 : 0.55}
            />
          ))}
        </g>
      </svg>

      {/* Legibility scrim so the title block always reads over the art. */}
      <div
        className="absolute inset-x-0 bottom-0 h-2/3"
        style={{
          background:
            "linear-gradient(to top, rgb(6 5 8 / 0.95) 0%, rgb(6 5 8 / 0.55) 45%, transparent 100%)",
        }}
      />
    </div>
  );
}
