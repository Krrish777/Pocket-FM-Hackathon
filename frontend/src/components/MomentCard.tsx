"use client";

import { Radio } from "@base-ui/react/radio";

import { IndexMark } from "@/components/IndexMark";
import { RadioGroup } from "@/components/ui/radio-group";
import { playSelect } from "@/lib/audio";
import { t, ui, type Locale, type Moment } from "@/lib/mockData";
import { cn } from "@/lib/utils";

/**
 * MomentCard — DESIGN.md §6.6.
 *
 * The paper/dark contrast does the heavy lifting here: canon is *paper*, the
 * hypotheticals are *machine*. That split teaches the whole visual language in
 * one screen without a word of explanation.
 *
 * Rows are real radios (Base UI, the primitive shadcn installed) so arrow-key
 * navigation and screen-reader semantics work. The spec shows no radio dot, so
 * selection is expressed by the accent wash and the 2px left border instead.
 */
export function MomentCard({
  moment,
  episodeId,
  locale,
  selectedAltId,
  onSelect,
}: {
  moment: Moment;
  episodeId: string;
  locale: Locale;
  selectedAltId: string | null;
  onSelect: (altId: string) => void;
}) {
  return (
    /* Two-column split with a vertical hairline between (DESIGN.md §8):
       canon on the left, hypotheticals on the right. */
    <div className="grid gap-10 md:grid-cols-2 md:gap-0">
      {/* CANON — on paper. */}
      <div className="md:pr-10">
        <IndexMark className="text-ink-muted mb-3 block">
          {`${t(ui.canonLabel, locale)} · ${episodeId}`}
        </IndexMark>

        <blockquote className="bg-paper-warm text-paper-ink type-prose p-6">
          {t(moment.originalLine, locale)}
        </blockquote>
      </div>

      {/* HYPOTHETICALS — on the shell. */}
      <div className="border-ink-line md:border-l md:pl-10">
        <IndexMark className="text-ink-muted mb-3 block">
          {t(ui.whatIfLabel, locale)}
        </IndexMark>

        <RadioGroup
          className="gap-0"
          // Always a string, never undefined: Base UI decides controlled vs
          // uncontrolled on first render, and `undefined → "ALT-A"` would flip
          // it mid-life and warn.
          value={selectedAltId ?? ""}
          onValueChange={(value) => {
            playSelect();
            onSelect(String(value));
          }}
        >
          {moment.alternatives.map((alternative) => {
            const selected = selectedAltId === alternative.altId;

            return (
              <Radio.Root
                key={alternative.altId}
                value={alternative.altId}
                className={cn(
                  "border-ink-line flex w-full cursor-pointer items-start gap-4 border-b p-4 text-left",
                  "border-l-2 transition-colors duration-200 ease-out outline-none",
                  "focus-visible:bg-shell-raised",
                  selected
                    ? "border-l-accent bg-accent-wash text-ink-bright"
                    : "text-ink-muted hover:bg-shell-raised hover:text-ink-bright border-l-transparent",
                )}
              >
                <IndexMark
                  className={cn("mt-1 shrink-0", selected && "text-accent")}
                >
                  {alternative.altId}
                </IndexMark>
                <span className="type-body">{t(alternative.label, locale)}</span>
              </Radio.Root>
            );
          })}
        </RadioGroup>
      </div>
    </div>
  );
}
