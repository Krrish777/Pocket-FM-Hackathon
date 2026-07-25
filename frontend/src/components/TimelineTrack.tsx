"use client";

import { playSelect } from "@/lib/audio";
import { t, type Episode, type Locale } from "@/lib/mockData";
import { cn } from "@/lib/utils";

/**
 * TimelineTrack — Timeline redesign (see reference mock).
 *
 * A single rule, gradient orange → violet, with episode nodes sitting on it.
 * Nodes breathe (opacity 0.85 → 1.0 over 4s, staggered 200ms) to signal the
 * system is tracking state. Ambient only — it must never pull focus from the
 * cascade.
 *
 * An episode is clickable only when the selected character has an authored
 * divergence point there, so there is no such thing as a dead click.
 */
export function TimelineTrack({
  episodes,
  characterId,
  selectedEpisodeId,
  episodesWithMoments,
  locale,
  onSelectEpisode,
}: {
  episodes: Episode[];
  characterId: string | null;
  selectedEpisodeId: string | null;
  episodesWithMoments: Set<string>;
  locale: Locale;
  onSelectEpisode: (episodeId: string) => void;
}) {
  return (
    <div className="relative w-full">
      {/* The rule the whole track hangs from. */}
      <div
        className="absolute top-[13px] right-0 left-0 h-px"
        style={{
          background: "linear-gradient(90deg, #f2994a, #a86ee0)",
          opacity: 0.4,
        }}
      />

      <ol className="relative flex items-start justify-between gap-2">
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
                  "relative grid size-[26px] place-items-center rounded-full border",
                  selected
                    ? "border-accent"
                    : present
                      ? "border-violet-400/50"
                      : "border-ink-line",
                  selectable ? "cursor-pointer" : "cursor-default",
                )}
              >
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
              <span
                className={cn(
                  "type-body text-center whitespace-nowrap",
                  selected ? "text-ink-bright" : "text-ink-muted",
                )}
              >
                {t(episode.title, locale)}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
