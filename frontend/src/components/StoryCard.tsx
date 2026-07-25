"use client";

import { ArrowRight, Clapperboard, Sparkles, Star } from "lucide-react";

import { IndexMark } from "@/components/IndexMark";
import { StoryCoverArt } from "@/components/StoryCoverArt";
import { playSelect } from "@/lib/audio";
import { t, ui, type Locale, type StorySummary } from "@/lib/mockData";
import { cn } from "@/lib/utils";

/**
 * StoryCard — Shelf redesign (see reference mock).
 *
 * Rounded, gradient-backed, photographic-feeling cover (CSS-generated, see
 * StoryCoverArt) with a floating "Enter Story" CTA. The whole card scales
 * slightly on hover; only the CTA is a real `<button>` so the card itself
 * stays a plain container (no nested interactive elements).
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
  const handleSelect = () => {
    if (!interactive) return;
    playSelect();
    onSelect(story.id);
  };

  return (
    <article
      className={cn(
        "group border-ink-line relative flex aspect-[3/4] w-full flex-col overflow-hidden rounded-2xl border text-left",
        "transition-transform duration-[400ms] ease-out",
        interactive && "hover:-translate-y-1",
      )}
    >
      <div className="absolute inset-0 transition-transform duration-[400ms] ease-out group-hover:scale-[1.03]">
        <StoryCoverArt storyId={story.id} />
      </div>

      <div className="relative flex items-start justify-between p-4">
        <IndexMark className="text-white/70">
          {`ST-${String(index + 1).padStart(2, "0")}`}
        </IndexMark>

        <span className="type-index flex items-center gap-1.5 rounded-full border border-amber-300/30 bg-amber-400/15 px-2.5 py-1 text-amber-200">
          <Star className="size-3" fill="currentColor" strokeWidth={0} />
          {t(ui.recommendedBadge, locale)}
        </span>
      </div>

      <div className="relative mt-auto flex flex-col gap-4 p-5 pt-0">
        <div>
          <h2 className="type-title text-white">{t(story.title, locale)}</h2>
          <p className="type-body mt-2 whitespace-pre-line text-white/70">
            {t(story.blurb, locale)}
          </p>
        </div>

        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-4">
            <span className="type-index flex items-center gap-1.5 text-white/60">
              <Clapperboard className="size-3.5 shrink-0" strokeWidth={1.75} />
              {String(story.episodeCount).padStart(2, "0")}
              <span className="text-white/40">{t(ui.episodesLabel, locale)}</span>
            </span>
            <span className="type-index flex items-center gap-1.5 text-white/60">
              <Sparkles className="size-3.5 shrink-0" strokeWidth={1.75} />
              {story.factCount}
              <span className="text-white/40">{t(ui.factsLabel, locale)}</span>
            </span>
          </div>
        </div>

        <button
          type="button"
          disabled={!interactive}
          aria-label={t(ui.enterStoryButton, locale)}
          onClick={handleSelect}
          className={cn(
            "type-label group/cta ml-auto flex w-fit max-w-full cursor-pointer items-center gap-2 rounded-full px-4 py-2.5 text-shell-void transition-all duration-150 ease-out",
            "disabled:cursor-default",
          )}
          style={{
            background: "linear-gradient(135deg, #f2994a, #e0608f 60%, #a86ee0)",
          }}
        >
          <span className="truncate">{t(ui.enterStoryButton, locale)}</span>
          <ArrowRight
            className="size-3.5 shrink-0 transition-transform duration-150 ease-out group-hover/cta:translate-x-0.5"
            strokeWidth={2}
          />
        </button>
      </div>
    </article>
  );
}
