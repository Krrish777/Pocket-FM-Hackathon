"use client";

import { Play, Sparkles, Users } from "lucide-react";

import { CharacterCard } from "@/components/CharacterCard";
import { useCharacters } from "@/lib/api";
import { t, ui } from "@/lib/mockData";
import { useDemoStore } from "@/store/demoStore";

/** The only character with a fully authored, playable run — REQUIREMENTS §4 core loop. */
const PLAYABLE_CHARACTER_ID = "CH-01";

/**
 * CharacterSelect (formerly Screen 2 — Story Timeline).
 *
 * project_context.md §2.2/§4: no story browsing, no episode archive — the
 * player picks a character and the story reveals itself turn by turn. This
 * screen is now the app's root screen (Shelf was cut — one novel series, one
 * cast, §2.2).
 */
export function Timeline() {
  const locale = useDemoStore((s) => s.locale);
  const selectCharacter = useDemoStore((s) => s.selectCharacter);
  const { data: characters, isPending } = useCharacters();

  return (
    <section className="flex flex-col items-center gap-12">
      <header className="flex max-w-2xl flex-col items-center gap-4 text-center">
        <div className="text-ink-muted flex items-center gap-3">
          <span className="bg-ink-line h-px w-10" aria-hidden="true" />
          <span className="type-index flex items-center gap-2">
            <Sparkles className="size-3.5 text-violet-300" strokeWidth={1.75} />
            {t(ui.appSubtitle, locale)}
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
          {t(ui.characterSelectHeading, locale)}
        </h1>

        <p className="type-body text-ink-muted">{t(ui.characterSelectSub, locale)}</p>
      </header>

      <div className="flex w-full max-w-[1120px] items-center gap-3">
        <Users className="text-ink-faint size-4 shrink-0" strokeWidth={1.75} />
        <span className="type-index text-ink-muted">
          {characters?.length ?? 5} {t(ui.charactersLabel, locale)}
        </span>
        <span className="bg-ink-line h-px flex-1" aria-hidden="true" />
      </div>

      <div className="grid w-full max-w-[1120px] grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {isPending
          ? Array.from({ length: 5 }, (_, i) => (
              <div
                key={i}
                className="border-ink-line bg-shell-base aspect-[4/3] rounded-2xl border"
              />
            ))
          : characters?.map((character, i) => (
              <CharacterCard
                key={character.id}
                character={character}
                locale={locale}
                index={i}
                selected={false}
                interactive={character.id === PLAYABLE_CHARACTER_ID}
                onSelect={selectCharacter}
              />
            ))}
      </div>

      <div className="border-ink-line bg-shell-raised/40 flex w-full max-w-[1120px] flex-col items-center justify-between gap-6 rounded-2xl border p-6 sm:flex-row">
        <div className="flex items-center gap-4">
          <div className="border-accent/40 text-accent flex size-11 shrink-0 items-center justify-center rounded-full border">
            <Sparkles className="size-4" strokeWidth={1.75} />
          </div>
          <p className="type-body text-left">
            <span className="text-ink-bright block font-medium">
              {t(ui.infinityBannerLead, locale)}
            </span>
            <span className="text-ink-muted">{t(ui.infinityBannerSub, locale)}</span>
          </p>
        </div>

        <button
          type="button"
          onClick={() => selectCharacter(PLAYABLE_CHARACTER_ID)}
          className="type-label group/cta flex shrink-0 cursor-pointer items-center gap-2 rounded-full px-5 py-3 text-shell-void transition-all duration-150 ease-out"
          style={{
            background: "linear-gradient(135deg, #f2994a, #e0608f 60%, #a86ee0)",
          }}
        >
          <Play className="size-4" strokeWidth={1.75} fill="currentColor" />
          {t(ui.enterPlaythroughButton, locale)}
        </button>
      </div>
    </section>
  );
}
