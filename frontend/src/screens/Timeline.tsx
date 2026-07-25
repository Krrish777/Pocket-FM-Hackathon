"use client";

import { Clapperboard, Clock, Hourglass, Play, Sparkles, Users } from "lucide-react";

import { CharacterCard } from "@/components/CharacterCard";
import { StoryCoverArt } from "@/components/StoryCoverArt";
import { TimelineTrack } from "@/components/TimelineTrack";
import { useEpisodesWithMoments, useStory } from "@/lib/api";
import { moments, t, ui } from "@/lib/mockData";
import { useDemoStore } from "@/store/demoStore";

/**
 * Screen 2 — Story Timeline, redesigned per the reference mock: a hero card
 * (cover art + meta), a gradient episode track, and a cast grid closing on a
 * "Time Machine" banner. Still proves the story has real structure —
 * episodes, a cast, facts being tracked — and choosing a character still
 * reveals which of their episodes hold an authored divergence point.
 */
export function Timeline() {
  const locale = useDemoStore((s) => s.locale);
  const storyId = useDemoStore((s) => s.storyId);
  const characterId = useDemoStore((s) => s.characterId);
  const episodeId = useDemoStore((s) => s.episodeId);
  const selectCharacter = useDemoStore((s) => s.selectCharacter);
  const openMoment = useDemoStore((s) => s.openMoment);

  const { data: story } = useStory(storyId);
  const episodeIds = story?.episodes.map((episode) => episode.id) ?? [];

  const { withMoments, momentsByEpisode } = useEpisodesWithMoments(
    storyId,
    characterId,
    episodeIds,
  );

  function handleSelectEpisode(nextEpisodeId: string) {
    const moment = momentsByEpisode.get(nextEpisodeId)?.[0];
    // The track disables episodes without a moment, so this is belt-and-braces.
    if (!moment) return;
    openMoment(nextEpisodeId, moment.momentId);
  }

  // The banner's fast path: jump straight to the rehearsed demo moment
  // (mockData.ts's stage note: ST-01 → E03 → CH-02) rather than stranding the
  // operator on an empty divergence screen with nothing selected yet.
  function handleOpenTimeMachine() {
    const primary = moments[0];
    if (!primary) return;
    selectCharacter(primary.characterId);
    openMoment(primary.episodeId, primary.momentId);
  }

  if (!story) return null;

  return (
    <section className="flex flex-col gap-14">
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_1.1fr]">
        <div className="flex flex-col justify-center gap-4">
          <span className="type-index bg-accent-wash text-accent w-fit rounded-full px-3 py-1.5">
            {story.id}
          </span>

          <h1 className="type-display text-ink-bright">{t(story.title, locale)}</h1>

          <p className="type-body text-ink-muted max-w-[52ch]">
            {t(story.logline, locale)}
          </p>

          <div className="mt-2 flex items-center gap-5">
            <span className="type-body flex items-center gap-2 text-ink-muted">
              <Clapperboard className="size-4" strokeWidth={1.75} />
              {story.episodes.length} {t(ui.episodesCountLabel, locale)}
            </span>
            <span className="text-ink-faint" aria-hidden="true">
              ·
            </span>
            <span className="type-body flex items-center gap-2 text-ink-muted">
              <Users className="size-4" strokeWidth={1.75} />
              {story.characters.length} {t(ui.charactersCountLabel, locale)}
            </span>
          </div>
        </div>

        <div className="border-ink-line relative aspect-[16/10] w-full overflow-hidden rounded-2xl border">
          <StoryCoverArt storyId={story.id} />
          <div
            className="bg-accent absolute bottom-5 left-5 flex size-11 items-center justify-center rounded-full"
            aria-hidden="true"
          >
            <Play className="size-4 fill-shell-void text-shell-void" strokeWidth={0} />
          </div>
        </div>
      </div>

      <TimelineTrack
        episodes={story.episodes}
        characterId={characterId}
        selectedEpisodeId={episodeId}
        episodesWithMoments={withMoments}
        locale={locale}
        onSelectEpisode={handleSelectEpisode}
      />

      <div className="flex flex-col gap-6">
        <div className="text-ink-muted flex items-center gap-3">
          <span className="type-index flex items-center gap-2">
            <Sparkles className="size-3.5 text-orange-300" strokeWidth={1.75} />
            {t(ui.charactersLabel, locale)}
            <Sparkles className="size-3.5 text-orange-300" strokeWidth={1.75} />
          </span>
          <span className="bg-ink-line h-px flex-1" aria-hidden="true" />
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {story.characters.map((character, i) => (
            <CharacterCard
              key={character.id}
              character={character}
              locale={locale}
              index={i}
              selected={characterId === character.id}
              onSelect={selectCharacter}
            />
          ))}
        </div>
      </div>

      <div className="border-ink-line bg-shell-raised/40 flex flex-col items-center justify-between gap-6 rounded-2xl border p-6 sm:flex-row">
        <div className="flex items-center gap-4">
          <div className="border-accent/40 text-accent flex size-11 shrink-0 items-center justify-center rounded-full border">
            <Hourglass className="size-4" strokeWidth={1.75} />
          </div>
          <p className="type-body">
            <span className="text-ink-bright block font-medium">
              {t(ui.infinityBannerLead, locale)}
            </span>
            <span className="text-ink-muted">{t(ui.timelineBannerSub, locale)}</span>
          </p>
        </div>

        <button
          type="button"
          onClick={handleOpenTimeMachine}
          className="type-label group/cta flex shrink-0 cursor-pointer items-center gap-2 rounded-full px-5 py-3 text-shell-void transition-all duration-150 ease-out"
          style={{
            background: "linear-gradient(135deg, #f2994a, #e0608f 60%, #a86ee0)",
          }}
        >
          <Clock className="size-4" strokeWidth={1.75} />
          {t(ui.openTimeMachineButton, locale)}
        </button>
      </div>
    </section>
  );
}
