/**
 * Deterministic pseudo-randomness for generated artwork.
 *
 * Cover and portrait art is computed from the entity's id, never from
 * `Math.random()`. Two consequences that matter here:
 *   - the same story always renders the same cover, so nothing shifts between
 *     a rehearsal and the live run;
 *   - artwork needs no binary assets, so the demo runs fully offline
 *     (REQUIREMENTS.md §10).
 */

/** FNV-1a. Small, fast, and stable across runs — that stability is the point. */
export function hashString(value: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

/** mulberry32 — seeded PRNG returning a generator of floats in [0, 1). */
export function seededRandom(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export type ProceduralNode = { x: number; y: number; r: number; accent: boolean };
export type ProceduralEdge = { from: number; to: number };

/**
 * A small constellation of "facts" — the motif behind every cover. Nodes are
 * scattered on a jittered grid so they read as structured rather than noisy,
 * then linked to their nearest neighbour.
 */
export function buildConstellation(
  seed: string,
  count = 14,
): { nodes: ProceduralNode[]; edges: ProceduralEdge[] } {
  const random = seededRandom(hashString(seed));
  const columns = 3;
  const rows = Math.ceil(count / columns);

  const nodes: ProceduralNode[] = Array.from({ length: count }, (_, i) => {
    const column = i % columns;
    const row = Math.floor(i / columns);
    return {
      x: 14 + (column + 0.5) * (72 / columns) + (random() - 0.5) * 14,
      y: 12 + (row + 0.5) * (126 / rows) + (random() - 0.5) * 12,
      r: 1.1 + random() * 1.9,
      accent: false,
    };
  });

  // Exactly one accent node — the divergence point. More would dilute it.
  const accentIndex = Math.floor(random() * nodes.length);
  nodes[accentIndex].accent = true;

  const edges: ProceduralEdge[] = [];
  for (let i = 0; i < nodes.length; i++) {
    let nearest = -1;
    let best = Infinity;
    for (let j = 0; j < nodes.length; j++) {
      if (i === j) continue;
      const distance =
        (nodes[i].x - nodes[j].x) ** 2 + (nodes[i].y - nodes[j].y) ** 2;
      if (distance < best) {
        best = distance;
        nearest = j;
      }
    }
    if (nearest >= 0 && !edges.some((e) => e.from === nearest && e.to === i)) {
      edges.push({ from: i, to: nearest });
    }
  }

  return { nodes, edges };
}
