"use client";

import { ProceduralPortrait } from "@/components/ProceduralPortrait";
import { playSelect } from "@/lib/audio";
import { t, type Character, type Locale } from "@/lib/mockData";
import { cn } from "@/lib/utils";

/**
 * CharacterPortrait — DESIGN.md §6.5.
 *
 * 56px circle, greyscale at rest, colour and an accent ring when selected.
 * One of only two places `--radius-full` is legal.
 */
export function CharacterPortrait({
  character,
  locale,
  selected,
  onSelect,
}: {
  character: Character;
  locale: Locale;
  selected: boolean;
  onSelect: (characterId: string) => void;
}) {
  const name = t(character.name, locale);

  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={() => {
        playSelect();
        onSelect(character.id);
      }}
      className="group flex w-24 cursor-pointer flex-col items-center gap-3"
    >
      <span
        className={cn(
          "block size-14 overflow-hidden rounded-full border transition-all duration-200 ease-out",
          selected
            ? "border-accent grayscale-0"
            : "border-ink-line grayscale group-hover:border-ink-muted group-hover:grayscale-0",
        )}
      >
        <ProceduralPortrait
          characterId={character.id}
          initial={name.trim().charAt(0)}
        />
      </span>

      <span
        className={cn(
          "type-label text-center leading-tight transition-colors duration-200 ease-out",
          selected ? "text-ink-bright" : "text-ink-muted",
        )}
      >
        {name}
      </span>
    </button>
  );
}
