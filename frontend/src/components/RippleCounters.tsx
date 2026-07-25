"use client";

import { CheckCircle2, EyeOff, Sparkles, XCircle, type LucideIcon } from "lucide-react";

import { t, ui, type CharacterId, type CharacterView, type Locale } from "@/lib/mockData";
import { CASCADE } from "@/lib/tokens";
import { useCountUp } from "@/lib/useCountUp";

/**
 * The four counters beside the Ripple Map — one per belief state (S2), tallied
 * across the 5 cast members instead of fact-array lengths. Still driven by
 * DESIGN.md §6.7's cascade timing so the numbers and the nodes tell the same
 * story at the same time. `--state-*` colours are legal here and on the
 * VerifierBadge, and nowhere else in the app — that reservation is semantic,
 * not decorative.
 */
function Counter({
  icon: Icon,
  value,
  label,
  color,
  duration,
  delay,
  running,
  testId,
}: {
  icon: LucideIcon;
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
    <div className="border-ink-line bg-shell-raised/30 flex flex-col gap-3 rounded-2xl border p-5">
      <Icon className="size-4" style={{ color }} strokeWidth={1.75} aria-hidden="true" />
      <span className="type-metric tabular-nums" style={{ color }} data-testid={testId}>
        {shown}
      </span>
      <span className="type-label text-ink-muted">{label}</span>
    </div>
  );
}

export function RippleCounters({
  views,
  locale,
  running,
}: {
  views: Record<CharacterId, CharacterView>;
  locale: Locale;
  running: boolean;
}) {
  const all = Object.values(views);
  const invalidated = all.filter((v) => v.beliefState === "invalid").length;
  const held = all.filter((v) => v.beliefState === "hold").length;
  const learned = all.filter((v) => v.beliefState === "new").length;
  const unaware = all.filter((v) => v.beliefState === "unaware").length;

  return (
    <div className="flex flex-col gap-4">
      <Counter
        testId="counter-invalidated"
        icon={XCircle}
        value={invalidated}
        label={t(ui.invalidatedLabel, locale)}
        color="var(--color-state-invalid)"
        duration={CASCADE.invalid.duration + invalidated * CASCADE.invalid.stagger}
        delay={CASCADE.invalid.at}
        running={running}
      />
      <Counter
        testId="counter-held"
        icon={CheckCircle2}
        value={held}
        label={t(ui.heldLabel, locale)}
        color="var(--color-state-hold)"
        duration={CASCADE.hold.duration + held * CASCADE.hold.stagger}
        delay={CASCADE.hold.at}
        running={running}
      />
      <Counter
        testId="counter-new"
        icon={Sparkles}
        value={learned}
        label={t(ui.newNeededLabel, locale)}
        color="var(--color-state-new)"
        duration={CASCADE.new.duration + learned * CASCADE.new.stagger}
        delay={CASCADE.new.at}
        running={running}
      />
      <Counter
        testId="counter-unaware"
        icon={EyeOff}
        value={unaware}
        label={t(ui.unawareLabel, locale)}
        color="var(--color-ink-muted)"
        duration={0.4}
        delay={0}
        running={running}
      />
    </div>
  );
}
