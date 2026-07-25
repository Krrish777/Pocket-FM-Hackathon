"use client";

import { CharacterPortrait } from "@/components/CharacterPortrait";
import { IndexMark } from "@/components/IndexMark";
import { TimelineTrack } from "@/components/TimelineTrack";
import { useEpisodesWithMoments, useStory } from "@/lib/api";
import { t, ui } from "@/lib/mockData";
import { useDemoStore } from "@/store/demoStore";

/**
 * Screen 2 — Story Timeline (REQUIREMENTS.md §6).
 *
 * Proves the story has real structure: episodes, a cast, and facts being
 * tracked. Choosing a character reveals which of their episodes actually hold
 * an authored divergence point.
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

  if (!story) return null;

  return (
    <section className="flex flex-col gap-16">
      <header className="flex flex-col gap-2">
        <IndexMark className="text-ink-muted">{story.id}</IndexMark>
        <h1 className="type-title text-ink-bright">{t(story.title, locale)}</h1>
        <p className="type-body text-ink-muted max-w-[60ch]">
          {t(story.logline, locale)}
        </p>
      </header>

      <div className="flex flex-col gap-6">
        <IndexMark className="text-ink-faint">
          {`${story.episodes.length} ${t(ui.episodesLabel, locale)} · ${story.characters.length} ${t(ui.charactersLabel, locale)}`}
        </IndexMark>

        <TimelineTrack
          episodes={story.episodes}
          characterId={characterId}
          selectedEpisodeId={episodeId}
          episodesWithMoments={withMoments}
          onSelectEpisode={handleSelectEpisode}
        />
      </div>

      <div className="flex flex-col gap-6">
        <IndexMark className="text-ink-faint">
          {t(ui.charactersLabel, locale)}
        </IndexMark>

        <div className="flex flex-wrap justify-center gap-12">
          {story.characters.map((character) => (
            <CharacterPortrait
              key={character.id}
              character={character}
              locale={locale}
              selected={characterId === character.id}
              onSelect={selectCharacter}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
