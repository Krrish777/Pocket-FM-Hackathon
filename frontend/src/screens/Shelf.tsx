"use client";

import { StoryCard } from "@/components/StoryCard";
import { useStories } from "@/lib/api";
import { t, ui } from "@/lib/mockData";
import { useDemoStore } from "@/store/demoStore";

/** The story that is authored end-to-end. The rest are shelf realism only. */
const PLAYABLE_STORY_ID = "ST-01";

/**
 * Screen 1 — Story Shelf (REQUIREMENTS.md §6).
 *
 * Establishes tone in two seconds and nothing else. Headline, then three
 * covers. No nav, no filters, no empty states.
 */
export function Shelf() {
  const locale = useDemoStore((s) => s.locale);
  const selectStory = useDemoStore((s) => s.selectStory);
  const { data: stories, isPending } = useStories();

  return (
    <section className="flex flex-col gap-10">
      <header className="flex flex-col gap-4">
        <h1 className="type-display text-ink-bright max-w-[18ch]">
          {t(ui.shelfHeading, locale)}
        </h1>
        <p className="type-body text-ink-muted">{t(ui.shelfSub, locale)}</p>
      </header>

      {/* Capped so three 2:3 covers fit a 16:9 projector without scrolling —
          the shelf is the opening shot and should be seen whole. */}
      <div className="grid max-w-[1020px] grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
        {isPending
          ? /* Skeletons are hairline outlines, not shimmering blocks — a
               shimmer would be a third assertive motion. */
            Array.from({ length: 3 }, (_, i) => (
              <div
                key={i}
                className="border-ink-line bg-shell-base aspect-[2/3] border"
              />
            ))
          : stories?.map((story, i) => (
              <StoryCard
                key={story.id}
                story={story}
                index={i}
                locale={locale}
                interactive={story.id === PLAYABLE_STORY_ID}
                onSelect={selectStory}
              />
            ))}
      </div>
    </section>
  );
}
