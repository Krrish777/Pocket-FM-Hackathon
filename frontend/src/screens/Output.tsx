"use client";

import { motion } from "framer-motion";
import { Pause, Play, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

import { DefectDemoTrigger } from "@/components/DefectDemoTrigger";
import { SceneOutputPanel } from "@/components/SceneOutputPanel";
import { VerifierBadge } from "@/components/VerifierBadge";
import { useRun } from "@/lib/api";
import { t, ui } from "@/lib/mockData";
import { isSpeechSupported, speak, stopSpeaking } from "@/lib/voice";
import { useDemoStore } from "@/store/demoStore";

/** The replay closing beat is pre-committed to Debra — see project_context.md §8.1. */
const REPLAY_CHARACTER_ID = "CH-02";

/** A small canned equalizer, driven by real speechSynthesis start/end events — not fake frequency analysis, just a "the system is speaking" cue. */
function Equalizer({ active }: { active: boolean }) {
  return (
    <div className="flex h-5 items-end gap-1" aria-hidden="true">
      {[0.4, 0.8, 1, 0.6, 0.9].map((base, i) => (
        <motion.span
          key={i}
          className="bg-accent w-1 rounded-full"
          initial={{ height: 4 }}
          animate={active ? { height: [4, base * 20, 6, base * 16, 4] } : { height: 4 }}
          transition={active ? { duration: 0.9 + i * 0.07, repeat: Infinity, ease: "easeInOut" } : { duration: 0.2 }}
        />
      ))}
    </div>
  );
}

/**
 * Output — the closing beat. Text is always shown; narration is real (Web
 * Speech API, lib/voice.ts — Higgsfield generation is out of credits in this
 * workspace, confirmed live, so this is the free path that actually works on
 * stage rather than a silent button).
 */
export function Output() {
  const locale = useDemoStore((s) => s.locale);
  const protagonistId = useDemoStore((s) => s.protagonistId);
  const startReplay = useDemoStore((s) => s.startReplay);
  const [speaking, setSpeaking] = useState(false);

  const { data: run, isPending } = useRun(protagonistId);

  useEffect(() => stopSpeaking, []);

  if (isPending || !run) {
    return (
      <p className="type-cite text-ink-muted py-24 text-center">
        {t(ui.loadingScene, locale)}
      </p>
    );
  }

  const finalTurn = run.turns.at(-1)!;
  const header = `${t(ui.outputHeading, locale)} · ${t(ui.turnLabel, locale)} ${finalTurn.turnIndex} / ${run.turns.length}`.toUpperCase();

  const toggleNarration = () => {
    if (speaking) {
      stopSpeaking();
      setSpeaking(false);
      return;
    }
    // Web Speech reads best in English regardless of display locale.
    speak(finalTurn.sceneText.en, setSpeaking);
  };

  return (
    /* Paper centred in the viewport; the badge and trigger align to its left
       edge rather than to the page (DESIGN.md §8). */
    <section className="mx-auto flex w-fit flex-col items-start gap-8">
      <SceneOutputPanel
        header={header}
        sceneText={finalTurn.sceneText}
        locale={locale}
      />

      <div className="border-ink-line bg-shell-raised/30 flex w-full max-w-[68ch] items-center gap-4 rounded-2xl border p-4">
        <button
          type="button"
          onClick={toggleNarration}
          disabled={!isSpeechSupported()}
          className="border-ink-line bg-shell-base flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full border disabled:opacity-40"
          aria-label={speaking ? t(ui.pauseNarrationButton, locale) : t(ui.playNarrationButton, locale)}
        >
          {speaking ? (
            <Pause className="text-ink-bright size-4" strokeWidth={1.75} fill="currentColor" />
          ) : (
            <Play className="text-ink-bright size-4" strokeWidth={1.75} fill="currentColor" />
          )}
        </button>

        <div className="flex flex-col gap-1">
          <span className="type-label text-ink-bright">
            {speaking ? t(ui.pauseNarrationButton, locale) : t(ui.playNarrationButton, locale)}
          </span>
          <span className="type-cite text-ink-faint">{t(ui.addYourMusicNote, locale)}</span>
        </div>

        <div className="ml-auto">
          <Equalizer active={speaking} />
        </div>
      </div>

      <VerifierBadge verifier={finalTurn.verifier} locale={locale} />

      <div className="flex flex-wrap gap-4">
        <DefectDemoTrigger />

        <button
          type="button"
          onClick={() => {
            stopSpeaking();
            startReplay(REPLAY_CHARACTER_ID);
          }}
          className="type-label flex cursor-pointer items-center gap-2 rounded-full px-6 py-3.5 text-shell-void"
          style={{
            background: "linear-gradient(135deg, #f2994a, #e0608f 60%, #a86ee0)",
          }}
        >
          <RotateCcw className="size-4" strokeWidth={1.75} />
          {t(ui.replayAsDebraButton, locale)}
        </button>
      </div>
    </section>
  );
}
