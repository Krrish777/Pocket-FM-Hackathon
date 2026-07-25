"use client";

import { Sparkles, Volume2 } from "lucide-react";
import { useEffect, useState } from "react";

import { playSelect } from "@/lib/audio";
import { t, ui, type Story } from "@/lib/mockData";
import { isSpeechSupported, speak, stopSpeaking } from "@/lib/voice";
import { cn } from "@/lib/utils";
import { useStories } from "@/lib/api";
import { useDemoStore } from "@/store/demoStore";

/**
 * Shelf — 3 story cards. Every card's voice teaser is REAL (Web Speech API,
 * lib/voice.ts) — tapping any of them is a genuine working interaction, not a
 * dead click. Only the fully-authored story (`interactive: true`) proceeds
 * into the playthrough; the others are voice-only, same "present but inert"
 * precedent as before.
 */
function StoryCard({ story, locale }: { story: Story; locale: "hi" | "en" }) {
  const selectStory = useDemoStore((s) => s.selectStory);
  const [playing, setPlaying] = useState(false);

  useEffect(() => stopSpeaking, []); // stop any narration if this card unmounts mid-play

  const toggleVoice = () => {
    if (playing) {
      stopSpeaking();
      setPlaying(false);
      return;
    }
    playSelect();
    speak(story.voiceSummary, setPlaying);
  };

  return (
    <article
      className={cn(
        "border-ink-line bg-shell-raised/30 flex flex-col gap-4 rounded-2xl border p-6 transition-colors duration-150 ease-out",
        playing && "border-accent/60",
      )}
    >
      <div>
        <h2 className="type-title text-ink-bright">{t(story.title, locale)}</h2>
        <p className="type-body text-ink-muted mt-2">{t(story.tagline, locale)}</p>
      </div>

      <div className="mt-auto flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={toggleVoice}
          disabled={!isSpeechSupported()}
          className={cn(
            "type-label flex cursor-pointer items-center gap-2 rounded-full border px-4 py-2.5 transition-colors duration-150 ease-out",
            playing
              ? "border-accent bg-accent-wash text-accent"
              : "border-ink-line bg-shell-base text-ink-bright hover:border-ink-muted",
            "disabled:cursor-default disabled:opacity-40",
          )}
        >
          <Volume2 className="size-3.5" strokeWidth={1.75} />
          {playing ? t(ui.nowPlayingLabel, locale) : t(ui.holdToHearLabel, locale)}
        </button>

        {story.interactive ? (
          <button
            type="button"
            onClick={() => {
              stopSpeaking();
              playSelect();
              selectStory(story.id);
            }}
            className="type-label flex cursor-pointer items-center gap-2 rounded-full px-4 py-2.5 text-shell-void"
            style={{ background: "linear-gradient(135deg, #f2994a, #e0608f 60%, #a86ee0)" }}
          >
            {t(ui.enterThisStoryButton, locale)}
          </button>
        ) : (
          <span className="type-index text-ink-faint normal-case">{t(ui.comingSoonLabel, locale)}</span>
        )}
      </div>
    </article>
  );
}

export function Shelf() {
  const locale = useDemoStore((s) => s.locale);
  const { data: stories, isPending } = useStories();

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
          {t(ui.shelfHeading, locale)}
        </h1>

        <p className="type-body text-ink-muted">{t(ui.shelfSub, locale)}</p>
      </header>

      <div className="grid w-full max-w-[1120px] grid-cols-1 gap-6 lg:grid-cols-3">
        {isPending
          ? Array.from({ length: 3 }, (_, i) => (
              <div key={i} className="border-ink-line bg-shell-base aspect-[4/3] rounded-2xl border" />
            ))
          : stories?.map((story) => <StoryCard key={story.id} story={story} locale={locale} />)}
      </div>
    </section>
  );
}
