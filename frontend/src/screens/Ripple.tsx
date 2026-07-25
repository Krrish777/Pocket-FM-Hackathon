"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect } from "react";

import { CanonButton } from "@/components/CanonButton";
import { IndexMark } from "@/components/IndexMark";
import { RippleCounters } from "@/components/RippleCounters";
import { RippleGraph } from "@/components/RippleGraph";
import { useDivergence } from "@/lib/api";
import { t, ui } from "@/lib/mockData";
import { CASCADE, DURATION, EASE } from "@/lib/tokens";
import { useDemoStore } from "@/store/demoStore";

/** When the cascade has fully settled, in ms. Drives the reveal of the CTA. */
const CASCADE_TOTAL_MS = (CASCADE.new.at + CASCADE.new.duration + 0.3) * 1000;

/**
 * Screen 4 — Ripple Map (REQUIREMENTS.md §6).
 *
 * The screen everything rides on: it is the wow moment and the trust moment at
 * once. The forward button deliberately does not exist until the cascade has
 * settled — letting someone skip past the proof would waste the whole point.
 */
export function Ripple() {
  const locale = useDemoStore((s) => s.locale);
  const storyId = useDemoStore((s) => s.storyId);
  const momentId = useDemoStore((s) => s.momentId);
  const altId = useDemoStore((s) => s.altId);
  const cascadeComplete = useDemoStore((s) => s.cascadeComplete);
  const setRipple = useDemoStore((s) => s.setRipple);
  const markCascadeComplete = useDemoStore((s) => s.markCascadeComplete);
  const showOutput = useDemoStore((s) => s.showOutput);

  const { data: ripple, isPending } = useDivergence(storyId, momentId, altId);

  /* Publish the rippleId so the Output screen can regenerate against it. */
  useEffect(() => {
    if (ripple) setRipple(ripple.rippleId);
  }, [ripple, setRipple]);

  /* Unlock the forward action once the cascade has played out. */
  useEffect(() => {
    if (!ripple || cascadeComplete) return;
    const timer = setTimeout(markCascadeComplete, CASCADE_TOTAL_MS);
    return () => clearTimeout(timer);
  }, [ripple, cascadeComplete, markCascadeComplete]);

  return (
    <section className="flex flex-col gap-10">
      <header className="flex flex-col gap-2">
        <IndexMark className="text-ink-muted">
          {ripple?.rippleId ?? "—"}
        </IndexMark>
        <h1 className="type-title text-ink-bright">
          {t(ui.rippleHeading, locale)}
        </h1>
      </header>

      {isPending || !ripple ? (
        <p className="type-cite text-ink-muted py-24 text-center">
          {t(ui.loadingRipple, locale)}
        </p>
      ) : (
        <div className="grid gap-10 lg:grid-cols-[1fr_auto]">
          <div className="min-h-[380px]">
            <RippleGraph ripple={ripple} running />
          </div>

          {/* Counters, separated from the graph by a vertical rule (DESIGN.md §8). */}
          <div className="border-ink-line lg:border-l lg:pl-10">
            <RippleCounters ripple={ripple} locale={locale} running />
          </div>
        </div>
      )}

      <div className="flex min-h-[52px] justify-end">
        <AnimatePresence>
          {cascadeComplete ? (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: DURATION.base, ease: EASE.canon }}
            >
              <CanonButton onClick={showOutput}>
                {t(ui.seeResultButton, locale)}
              </CanonButton>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </section>
  );
}
