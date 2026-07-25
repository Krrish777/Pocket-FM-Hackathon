"use client";

import { useEffect, useState } from "react";

/**
 * Counts from 0 to `target`, easing out.
 *
 * DESIGN.md §6.7 is specific that counters rise *in sync with* their cascade
 * phase rather than snapping to the final number afterwards — the count-up is
 * part of the proof that something is being computed, not a decoration.
 */
export function useCountUp(
  target: number,
  {
    duration,
    delay = 0,
    enabled = true,
  }: { duration: number; delay?: number; enabled?: boolean },
): number {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setValue(0);
      return;
    }

    // Respect a reduced-motion preference by landing on the final value.
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    if (reduced || duration <= 0) {
      setValue(target);
      return;
    }

    let frame = 0;
    let startedAt: number | null = null;

    const timer = setTimeout(() => {
      const tick = (now: number) => {
        startedAt ??= now;
        const progress = Math.min((now - startedAt) / 1000 / duration, 1);
        const eased = 1 - (1 - progress) ** 3;
        setValue(Math.round(target * eased));
        if (progress < 1) frame = requestAnimationFrame(tick);
      };
      frame = requestAnimationFrame(tick);
    }, delay * 1000);

    return () => {
      clearTimeout(timer);
      cancelAnimationFrame(frame);
    };
  }, [target, duration, delay, enabled]);

  return value;
}
