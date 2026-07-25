/**
 * Design tokens as code — the single source of truth for motion.
 * Every value is literal from docs/DESIGN.md §6.7 and §7.
 *
 * Colors/type live in `globals.css` (Tailwind `@theme`); this file exists
 * because Framer Motion needs numbers, not CSS custom properties.
 */

/** DESIGN.md §7 — durations, in seconds (Framer Motion's unit). */
export const DURATION = {
  instant: 0.12,
  quick: 0.2,
  base: 0.32,
  slow: 0.6,
  cascade: 2.4,
} as const;

/** DESIGN.md §7 — ease-out everywhere EXCEPT the FLIP commit. */
export const EASE = {
  /** cubic-bezier(0.16, 1, 0.3, 1) — the default for everything. */
  canon: [0.16, 1, 0.3, 1],
  /** cubic-bezier(0.87, 0, 0.13, 1) — sharp both ends. FLIP commit only. */
  flip: [0.87, 0, 0.13, 1],
} as const;

/**
 * DESIGN.md §6.7 — the Ripple cascade timeline. Total ≈ 2.4s.
 *
 * Phases run on absolute offsets from cascade start, not sequentially, so
 * counters can be driven from the same numbers the nodes animate on.
 */
export const CASCADE = {
  /** 1. Fork point pulses once, scale 1 → 1.8 → 1. */
  fork: { at: 0, duration: 0.4 },
  /** 2. Invalidated nodes die in sequence. */
  invalid: { at: 0.4, duration: 0.3, stagger: 0.04 },
  /** 3. Held nodes brighten. */
  hold: { at: 1.4, duration: 0.2, stagger: 0.06 },
  /** 4. New-fact nodes fade in, ring expands. */
  new: { at: 2.0, duration: 0.3, stagger: 0.06 },
} as const;

/**
 * Screen transitions (DESIGN.md §7) — identical for all screens, state-driven.
 * Outgoing: opacity 1→0, y 0→-8px over `quick`.
 * Incoming: opacity 0→1, y 8px→0 over `base`, delayed 120ms.
 */
export const SCREEN_TRANSITION = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.base, ease: EASE.canon, delay: DURATION.instant },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: { duration: DURATION.quick, ease: EASE.canon },
  },
} as const;

/** RippleGraph SVG viewBox. Positions are frozen, never simulated. */
export const RIPPLE_VIEWBOX = { width: 760, height: 420 } as const;
