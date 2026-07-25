import { hashString, seededRandom } from "@/lib/procedural";

/**
 * Generated character portrait — stands in for `portraitUrl`.
 *
 * A monogram on a seeded arc pattern. Deliberately abstract: an AI-generated
 * face would clash with the archival tone and drag in a binary asset the
 * offline requirement doesn't allow.
 */
export function ProceduralPortrait({
  characterId,
  initial,
}: {
  characterId: string;
  /** First glyph of the character's name — works for Devanagari and Latin alike. */
  initial: string;
}) {
  const random = seededRandom(hashString(characterId));
  const arcs = Array.from({ length: 3 }, () => ({
    radius: 16 + random() * 16,
    rotation: random() * 360,
    length: 60 + random() * 140,
  }));

  return (
    <svg viewBox="0 0 56 56" className="h-full w-full" aria-hidden="true">
      <circle cx="28" cy="28" r="28" fill="var(--color-shell-raised)" />

      <g
        fill="none"
        stroke="var(--color-ink-faint)"
        strokeWidth="0.75"
        opacity="0.7"
      >
        {arcs.map((arc, i) => (
          <circle
            key={i}
            cx="28"
            cy="28"
            r={arc.radius}
            strokeDasharray={`${arc.length} 400`}
            transform={`rotate(${arc.rotation} 28 28)`}
          />
        ))}
      </g>

      <text
        x="28"
        y="28"
        textAnchor="middle"
        dominantBaseline="central"
        fill="var(--color-ink-bright)"
        style={{ font: "600 20px var(--font-story)" }}
      >
        {initial}
      </text>
    </svg>
  );
}
