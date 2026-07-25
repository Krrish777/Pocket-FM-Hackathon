"use client";

import { CanonButton } from "@/components/CanonButton";
import { IndexMark } from "@/components/IndexMark";
import { MomentCard } from "@/components/MomentCard";
import { useMoments, useStory } from "@/lib/api";
import { playFlip } from "@/lib/audio";
import { t, ui } from "@/lib/mockData";
import { useDemoStore } from "@/store/demoStore";

/**
 * Screen 3 — Moment + Divergence Selector (REQUIREMENTS.md §6).
 *
 * The "what if" input, deliberately bounded to pre-authored alternatives.
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
      <header className="flex flex-col gap-2">
        <IndexMark className="text-ink-muted">{episode.id}</IndexMark>
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
        <CanonButton
          disabled={!altId}
          onClick={() => {
            playFlip();
            commitFlip();
          }}
        >
          {t(ui.flipButton, locale)}
        </CanonButton>
      </div>
    </section>
  );
}
