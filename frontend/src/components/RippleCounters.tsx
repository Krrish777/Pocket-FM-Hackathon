"use client";

import { t, ui, type Locale, type RippleResult } from "@/lib/mockData";
import { CASCADE } from "@/lib/tokens";
import { useCountUp } from "@/lib/useCountUp";

/**
 * The three counters beside the Ripple Map — DESIGN.md §6.7.
 *
 * Each one rises during its own cascade phase, so the numbers and the nodes
 * tell the same story at the same time. These are `--state-*` colours, which
 * are legal here and on the VerifierBadge, and nowhere else in the app.
 */
function Counter({
  value,
  label,
  color,
  duration,
  delay,
  running,
  testId,
}: {
  value: number;
  label: string;
  color: string;
  duration: number;
  delay: number;
  running: boolean;
  testId: string;
}) {
  const shown = useCountUp(value, { duration, delay, enabled: running });

  return (
    <div className="flex flex-col gap-1">
      <span className="type-metric tabular-nums" style={{ color }} data-testid={testId}>
        {shown}
      </span>
      <span className="type-label text-ink-muted">{label}</span>
    </div>
  );
}

export function RippleCounters({
  ripple,
  locale,
  running,
}: {
  ripple: RippleResult;
  locale: Locale;
  running: boolean;
}) {
  return (
    <div className="flex flex-col gap-10">
      <Counter
        testId="counter-invalidated"
        value={ripple.invalidated.length}
        label={t(ui.invalidatedLabel, locale)}
        color="var(--color-state-invalid)"
        // Track the whole phase: start to last staggered node.
        duration={
          CASCADE.invalid.duration +
          ripple.invalidated.length * CASCADE.invalid.stagger
        }
        delay={CASCADE.invalid.at}
        running={running}
      />
      <Counter
        testId="counter-held"
        value={ripple.held.length}
        label={t(ui.heldLabel, locale)}
        color="var(--color-state-hold)"
        duration={
          CASCADE.hold.duration + ripple.held.length * CASCADE.hold.stagger
        }
        delay={CASCADE.hold.at}
        running={running}
      />
      <Counter
        testId="counter-new"
        value={ripple.newNeeded.length}
        label={t(ui.newNeededLabel, locale)}
        color="var(--color-state-new)"
        duration={
          CASCADE.new.duration + ripple.newNeeded.length * CASCADE.new.stagger
        }
        delay={CASCADE.new.at}
        running={running}
      />
    </div>
  );
}
