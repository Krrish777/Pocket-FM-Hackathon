"use client";

import { ChevronRight } from "lucide-react";

import { ProceduralPortrait } from "@/components/ProceduralPortrait";
import { playSelect } from "@/lib/audio";
import { t, ui, type Character, type Locale } from "@/lib/mockData";
import { cn } from "@/lib/utils";

/** Alternates orange/violet across the cast — same two accents as the rest of the redesign. */
const TINTS = [
  { ring: "border-orange-400/50", badge: "bg-orange-500/90", role: "text-orange-300" },
  { ring: "border-violet-400/50", badge: "bg-violet-500/90", role: "text-violet-300" },
] as const;

/**
 * Character card — Timeline redesign (see reference mock).
 *
 * "View Journey" reuses the existing `selectCharacter` interaction (the
 * portrait grid used to do this on click): it feeds the TimelineTrack above,
 * which lights up exactly the episodes that character has an authored
 * moment in.
 */
export function CharacterCard({
  character,
  locale,
  index,
  selected,
  onSelect,
}: {
  character: Character;
  locale: Locale;
  index: number;
  selected: boolean;
  onSelect: (characterId: string) => void;
}) {
  const name = t(character.name, locale);
  const tint = TINTS[index % TINTS.length];

  const handleSelect = () => {
    playSelect();
    onSelect(character.id);
  };

  return (
    <article
      className={cn(
        "bg-shell-raised/30 flex flex-col gap-4 rounded-2xl border p-5 transition-colors duration-150 ease-out",
        selected ? "border-accent/60" : "border-ink-line",
      )}
    >
      <div className="flex items-center gap-3">
        <span
          className={cn(
            "block size-14 shrink-0 overflow-hidden rounded-2xl border",
            tint.ring,
          )}
        >
          <ProceduralPortrait characterId={character.id} initial={name.charAt(0)} />
        </span>

        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={cn("size-1.5 shrink-0 rounded-full", tint.badge)}
              aria-hidden="true"
            />
            <h3 className="type-body text-ink-bright truncate font-semibold">{name}</h3>
          </div>
          <p className={cn("type-index mt-1 normal-case", tint.role)}>
            {t(character.role, locale)}
          </p>
        </div>
      </div>

      <p className="type-body text-ink-muted whitespace-pre-line">
        {t(character.blurb, locale)}
      </p>

      <button
        type="button"
        aria-pressed={selected}
        onClick={handleSelect}
        className="border-ink-line bg-shell-base group/cta text-ink-bright mt-auto flex w-fit cursor-pointer items-center gap-1.5 rounded-full border px-4 py-2 transition-colors duration-150 ease-out hover:border-ink-muted"
      >
        <span className="type-index normal-case">{t(ui.viewJourneyButton, locale)}</span>
        <ChevronRight
          className={cn("size-3.5 transition-transform duration-150 ease-out group-hover/cta:translate-x-0.5", tint.role)}
        />
      </button>
    </article>
  );
}
