"use client";

import { playSelect } from "@/lib/audio";
import type { Episode } from "@/lib/mockData";
import { cn } from "@/lib/utils";

/**
 * TimelineTrack — DESIGN.md §6.4.
 *
 * A single hairline rule with episode nodes sitting on it. Nodes breathe
 * (opacity 0.85 → 1.0 over 4s, staggered 200ms) to signal the system is
 * tracking state. Ambient only — it must never pull focus from the cascade.
 *
 * An episode is clickable only when the selected character has an authored
 * divergence point there, so there is no such thing as a dead click.
 */
export function TimelineTrack({
  episodes,
  characterId,
  selectedEpisodeId,
  episodesWithMoments,
  onSelectEpisode,
}: {
  episodes: Episode[];
  characterId: string | null;
  selectedEpisodeId: string | null;
  episodesWithMoments: Set<string>;
  onSelectEpisode: (episodeId: string) => void;
}) {
  return (
    <div className="relative w-full">
      {/* The rule the whole track hangs from. */}
      <div className="bg-ink-line absolute top-[11px] right-0 left-0 h-px" />

      <ol className="relative flex items-start justify-between">
        {episodes.map((episode, i) => {
          const present = characterId
            ? episode.characters.includes(characterId)
            : false;
          const selectable = episodesWithMoments.has(episode.id);
          const selected = selectedEpisodeId === episode.id;

          return (
            <li key={episode.id} className="flex flex-col items-center gap-3">
              <button
                type="button"
                disabled={!selectable}
                aria-label={episode.id}
                aria-pressed={selected}
                onClick={() => {
                  playSelect();
                  onSelectEpisode(episode.id);
                }}
                className={cn(
                  "relative grid size-[22px] place-items-center",
                  selectable ? "cursor-pointer" : "cursor-default",
                )}
              >
                {/* Selection ring — 20px, accent, 1px. */}
                {selected ? (
                  <span className="border-accent absolute size-5 rounded-full border" />
                ) : null}

                <span
                  className={cn(
                    "animate-breathe block size-[10px] rounded-full border transition-colors duration-200 ease-out",
                    selected
                      ? "bg-accent border-accent"
                      : present
                        ? "bg-ink-muted border-ink-muted"
                        : "bg-shell-raised border-ink-line",
                    selectable && !selected && "hover:border-accent",
                  )}
                  style={{ animationDelay: `${i * 200}ms` }}
                />
              </button>

              <span
                className={cn(
                  "type-index",
                  selected ? "text-accent" : "text-ink-faint",
                )}
              >
                {episode.id}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
