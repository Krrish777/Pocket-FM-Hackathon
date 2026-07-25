"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Waves } from "lucide-react";
import { useEffect } from "react";

import { RippleCounters } from "@/components/RippleCounters";
import { RippleGraph } from "@/components/RippleGraph";
import { useCharacters, useChoice, useRun } from "@/lib/api";
import { t, ui } from "@/lib/mockData";
import { CASCADE, DURATION, EASE } from "@/lib/tokens";
import { useDemoStore } from "@/store/demoStore";

/** When the cascade has fully settled, in ms. Drives the reveal of the CTA. */
const CASCADE_TOTAL_MS = (CASCADE.new.at + CASCADE.new.duration + 0.3) * 1000;

/**
 * Screen 4 — Ripple Map (REQUIREMENTS.md §6), now the character-belief
 * cascade (S2). The forward button deliberately does not exist until the
 * cascade has settled — letting someone skip past the proof would waste the
 * whole point.
 *
 * `useChoice` is kept purely for its artificial latency (so the cascade feels
 * earned, per docs/API_CONTRACT_NOTES.md's "latency is welcome" note) — the
 * data actually rendered is the turn's `characterViews`, already sitting in
 * the cached run.
 */
export function Ripple() {
  const locale = useDemoStore((s) => s.locale);
  const protagonistId = useDemoStore((s) => s.protagonistId);
  const currentTurnIndex = useDemoStore((s) => s.currentTurnIndex);
  const history = useDemoStore((s) => s.history);
  const cascadeComplete = useDemoStore((s) => s.cascadeComplete);
  const markCascadeComplete = useDemoStore((s) => s.markCascadeComplete);
  const proceedToOutput = useDemoStore((s) => s.proceedToOutput);

  const { data: run } = useRun(protagonistId);
  const { data: characters } = useCharacters();
  const lastChoice = history.at(-1);
  const { isPending } = useChoice(run?.runId ?? null, currentTurnIndex, lastChoice?.chosenChoiceId ?? null);

  const turn = run?.turns.find((candidate) => candidate.turnIndex === currentTurnIndex);
  const views = turn?.characterViews;
  const ready = !isPending && Boolean(views) && Boolean(characters);

  /* Unlock the forward action once the cascade has played out. */
  useEffect(() => {
    if (!ready || cascadeComplete) return;
    const timer = setTimeout(markCascadeComplete, CASCADE_TOTAL_MS);
    return () => clearTimeout(timer);
  }, [ready, cascadeComplete, markCascadeComplete]);

  return (
    <section className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <span className="type-index bg-accent-wash text-accent w-fit rounded-full px-3 py-1.5">
          {`${t(ui.turnLabel, locale)} ${currentTurnIndex} / ${run?.turns.length ?? "—"}`}
        </span>
        <h1 className="type-title text-ink-bright">
          {t(ui.beliefRippleHeading, locale)}
        </h1>
        <p className="type-body text-ink-muted max-w-[52ch]">{t(ui.rippleCaption, locale)}</p>
      </header>

      {!ready || !views || !characters ? (
        <p className="type-cite text-ink-muted py-24 text-center">
          {t(ui.loadingRipple, locale)}
        </p>
      ) : (
        <div className="border-ink-line bg-shell-raised/20 relative overflow-hidden rounded-2xl border p-8">
          {/* Ambient glow behind the graph — same atmosphere language as the
              rest of the redesign, kept out of RippleGraph itself so the SVG
              stays pure hand-authored coordinates. */}
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(60% 50% at 20% 45%, rgb(200 85 61 / 0.12), transparent 70%)",
            }}
            aria-hidden="true"
          />

          <div className="relative grid gap-10 lg:grid-cols-[1fr_auto]">
            <div className="min-h-[380px]">
              <RippleGraph
                castOrder={characters.map((c) => c.id)}
                views={views}
                characters={characters}
                locale={locale}
                running
              />
            </div>

            {/* Counters, separated from the graph by a vertical rule (DESIGN.md §8). */}
            <div className="border-ink-line lg:border-l lg:pl-10">
              <RippleCounters views={views} locale={locale} running />
            </div>
          </div>
        </div>
      )}

      <div className="flex min-h-[52px] justify-end">
        <AnimatePresence>
          {cascadeComplete ? (
            <motion.button
              type="button"
              onClick={proceedToOutput}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: DURATION.base, ease: EASE.canon }}
              className="type-label flex cursor-pointer items-center gap-2 rounded-full px-6 py-3.5 text-shell-void"
              style={{
                background: "linear-gradient(135deg, #f2994a, #e0608f 60%, #a86ee0)",
              }}
            >
              <Waves className="size-4" strokeWidth={1.75} />
              {t(ui.seeResultButton, locale)}
            </motion.button>
          ) : null}
        </AnimatePresence>
      </div>
    </section>
  );
}
