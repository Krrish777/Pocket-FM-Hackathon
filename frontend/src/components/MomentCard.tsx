"use client";

import { Radio } from "@base-ui/react/radio";

import { IndexMark } from "@/components/IndexMark";
import { RadioGroup } from "@/components/ui/radio-group";
import { playSelect } from "@/lib/audio";
import { t, ui, type Choice, type Locale } from "@/lib/mockData";
import { cn } from "@/lib/utils";

/**
 * MomentCard — the per-turn choice list (formerly the Divergence redesign's
 * two-column canon/hypothetical split; the current scene is now shown by
 * `SceneOutputPanel` above this component every turn, so this card is just
 * the choice list).
 *
 * Every option carries a visible fan-fiction attribution line (M4/SD-9,
 * project_context.md §5.2) — the whole point is that these are sourced, not
 * invented by us. Rows are real radios (Base UI) so arrow-key navigation and
 * screen-reader semantics work.
 */
export function MomentCard({
  choices,
  locale,
  selectedChoiceId,
  onSelect,
}: {
  choices: Choice[];
  locale: Locale;
  selectedChoiceId: string | null;
  onSelect: (choiceId: string) => void;
}) {
  return (
    <div>
      <IndexMark className="text-ink-muted mb-3 block">
        {t(ui.choicesHeading, locale)}
      </IndexMark>

      <RadioGroup
        className="flex flex-col gap-3"
        // Always a string, never undefined: Base UI decides controlled vs
        // uncontrolled on first render, and `undefined → "T1-A"` would flip
        // it mid-life and warn.
        value={selectedChoiceId ?? ""}
        onValueChange={(value) => {
          playSelect();
          onSelect(String(value));
        }}
      >
        {choices.map((choice) => {
          const selected = selectedChoiceId === choice.choiceId;

          return (
            <Radio.Root
              key={choice.choiceId}
              value={choice.choiceId}
              className={cn(
                "flex w-full cursor-pointer flex-col items-start gap-2 rounded-2xl border p-4 text-left",
                "transition-colors duration-200 ease-out outline-none",
                "focus-visible:bg-shell-raised",
                selected
                  ? "border-accent/60 bg-accent-wash text-ink-bright"
                  : "border-ink-line text-ink-muted hover:bg-shell-raised hover:text-ink-bright",
              )}
            >
              <div className="flex w-full items-start gap-4">
                <IndexMark className={cn("mt-1 shrink-0", selected && "text-accent")}>
                  {choice.choiceId}
                </IndexMark>
                <span className="type-body">{t(choice.label, locale)}</span>
              </div>

              <span className="type-cite text-ink-faint pl-[calc(1.5rem+1rem)]">
                {t(ui.sourcedFromLabel, locale)} · &ldquo;{choice.source.workTitle}&rdquo;
                {" — "}
                {choice.source.author} · {choice.source.platform}
              </span>
            </Radio.Root>
          );
        })}
      </RadioGroup>
    </div>
  );
}
