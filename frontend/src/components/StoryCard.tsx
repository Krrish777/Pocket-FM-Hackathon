"use client";

import { ProceduralCover } from "@/components/ProceduralCover";
import { IndexMark } from "@/components/IndexMark";
import { playSelect } from "@/lib/audio";
import { t, ui, type Locale, type StorySummary } from "@/lib/mockData";
import { cn } from "@/lib/utils";

/**
 * StoryCard — DESIGN.md §6.3.
 *
 * Hover does exactly two things: the border goes accent, and the cover scales
 * 1.03 over 400ms. No lift, no glow, no shadow.
 */
export function StoryCard({
  story,
  index,
  locale,
  interactive,
  onSelect,
}: {
  story: StorySummary;
  /** Position on the shelf, for the `ST-01` catalog mark. */
  index: number;
  locale: Locale;
  /** Only the fully-authored story is clickable; the rest are shelf realism. */
  interactive: boolean;
  onSelect: (storyId: string) => void;
}) {
  const meta = [
    `${String(story.episodeCount).padStart(2, "0")} ${t(ui.episodesLabel, locale)}`,
    `${story.factCount} ${t(ui.factsLabel, locale)}`,
  ].join(" · ");

  return (
    <button
      type="button"
      disabled={!interactive}
      aria-label={t(story.title, locale)}
      onClick={() => {
        if (!interactive) return;
        playSelect();
        onSelect(story.id);
      }}
      className={cn(
        "group border-ink-line relative block aspect-[2/3] w-full overflow-hidden border text-left",
        "transition-colors duration-[400ms] ease-out",
        interactive
          ? "hover:border-accent cursor-pointer"
          : "cursor-default opacity-70",
      )}
    >
      <div
        className={cn(
          "absolute inset-0 transition-transform duration-[400ms] ease-out",
          interactive && "group-hover:scale-[1.03]",
        )}
      >
        <ProceduralCover storyId={story.id} />
      </div>

      <IndexMark className="absolute top-4 left-4">
        {`ST-${String(index + 1).padStart(2, "0")}`}
      </IndexMark>

      <div className="absolute right-4 bottom-4 left-4">
        <h2 className="type-title text-ink-bright">{t(story.title, locale)}</h2>
        <p className="type-index text-ink-muted mt-2">{meta}</p>
      </div>
    </button>
  );
}
