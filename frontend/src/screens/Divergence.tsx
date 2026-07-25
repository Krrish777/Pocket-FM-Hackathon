"use client";

import { GitBranch } from "lucide-react";

import { MomentCard } from "@/components/MomentCard";
import { useMoments, useStory } from "@/lib/api";
import { playFlip } from "@/lib/audio";
import { t, ui } from "@/lib/mockData";
import { cn } from "@/lib/utils";
import { useDemoStore } from "@/store/demoStore";

/**
 * Screen 3 — Moment + Divergence Selector, redesigned per the Shelf/Timeline
 * pattern: a pill badge for the episode, plain title, and a gradient CTA.
 *
 * The "what if" input is deliberately bounded to pre-authored alternatives.
 * Freeform text was cut on purpose: it is a quality and control risk with one
 * shot on stage (REQUIREMENTS.md §4).
 */
export function Divergence() {
  const locale = useDemoStore((s) => s.locale);
  const storyId = useDemoStore((s) => s.storyId);
  const episodeId = useDemoStore((s) => s.episodeId);
  const characterId = useDemoStore((s) => s.characterId);
  const altId = useDemoStore((s) => s.altId);
  const selectAlternative = useDemoStore((s) => s.selectAlternative);
  const commitFlip = useDemoStore((s) => s.commitFlip);

  const { data: story } = useStory(storyId);
  const { data: moments } = useMoments(storyId, episodeId, characterId);

  const moment = moments?.[0];
  const episode = story?.episodes.find((candidate) => candidate.id === episodeId);

  if (!moment || !episode) return null;

  return (
    <section className="flex flex-col gap-12">
      <header className="flex flex-col gap-3">
        <span className="type-index bg-accent-wash text-accent w-fit rounded-full px-3 py-1.5">
          {episode.id}
        </span>
        <h1 className="type-title text-ink-bright">
          {t(episode.title, locale)}
        </h1>
      </header>

      <MomentCard
        moment={moment}
        episodeId={episode.id}
        locale={locale}
        selectedAltId={altId}
        onSelect={selectAlternative}
      />

      <div className="flex justify-end">
        <button
          type="button"
          disabled={!altId}
          onClick={() => {
            playFlip();
            commitFlip();
          }}
          className={cn(
            "type-label flex cursor-pointer items-center gap-2 rounded-full px-6 py-3.5 text-shell-void transition-opacity duration-150 ease-out",
            "disabled:pointer-events-none disabled:opacity-40",
          )}
          style={{
            background: "linear-gradient(135deg, #f2994a, #e0608f 60%, #a86ee0)",
          }}
        >
          <GitBranch className="size-4" strokeWidth={1.75} />
          {t(ui.flipButton, locale)}
        </button>
      </div>
    </section>
  );
}
