"use client";

import { Hourglass, Sparkles } from "lucide-react";

import { StoryCard } from "@/components/StoryCard";
import { useStories } from "@/lib/api";
import { t, ui } from "@/lib/mockData";
import { useDemoStore } from "@/store/demoStore";

/** The story that is authored end-to-end. The rest are shelf realism only. */
const PLAYABLE_STORY_ID = "ST-01";

/**
 * Screen 1 — Story Shelf, redesigned per the reference mock: a centered
 * hero (eyebrow, gradient headline, subhead), three cover cards, and a
 * closing tagline bar. Still establishes tone fast — headline, covers,
 * one line of framing — no nav, no filters, no empty states.
 */
export function Shelf() {
  const locale = useDemoStore((s) => s.locale);
  const selectStory = useDemoStore((s) => s.selectStory);
  const { data: stories, isPending } = useStories();

  return (
    <section className="flex flex-col items-center gap-12">
      <header className="flex max-w-2xl flex-col items-center gap-4 text-center">
        <div className="text-ink-muted flex items-center gap-3">
          <span className="bg-ink-line h-px w-10" aria-hidden="true" />
          <span className="type-index flex items-center gap-2">
            <Sparkles className="size-3.5 text-violet-300" strokeWidth={1.75} />
            {t(ui.welcomeEyebrow, locale)}
            <Sparkles className="size-3.5 text-violet-300" strokeWidth={1.75} />
          </span>
          <span className="bg-ink-line h-px w-10" aria-hidden="true" />
        </div>

        <h1
          className="type-display bg-clip-text text-transparent"
          style={{
            backgroundImage:
              "linear-gradient(90deg, #f6f2ea 0%, #f6f2ea 45%, #b8a8f2 75%, #8fa8f0 100%)",
          }}
        >
          {t(ui.shelfHeading, locale)}
        </h1>

        <p className="type-body text-ink-muted">{t(ui.shelfSub, locale)}</p>
      </header>

      <div className="grid w-full max-w-[1120px] grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {isPending
          ? /* Skeletons are hairline outlines, not shimmering blocks — a
               shimmer would be a third assertive motion. */
            Array.from({ length: 3 }, (_, i) => (
              <div
                key={i}
                className="border-ink-line bg-shell-base aspect-[3/4] rounded-2xl border"
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

      <div className="border-ink-line bg-shell-raised/40 flex w-full max-w-[1120px] items-center justify-center gap-3 rounded-full border px-6 py-4">
        <Sparkles className="text-ink-faint size-4 shrink-0" strokeWidth={1.5} />
        <Hourglass className="text-ink-muted size-4 shrink-0" strokeWidth={1.75} />
        <p className="type-body text-center">
          <span className="text-ink-bright font-medium">
            {t(ui.infinityBannerLead, locale)}
          </span>{" "}
          <span className="text-ink-muted">{t(ui.infinityBannerSub, locale)}</span>
        </p>
        <Sparkles className="text-ink-faint size-4 shrink-0" strokeWidth={1.5} />
      </div>
    </section>
  );
}
