"use client";

import { AnimatePresence, motion } from "framer-motion";

import { AppHeader } from "@/components/AppHeader";
import { CanonButton } from "@/components/CanonButton";
import { Sidebar, SIDEBAR_WIDTH } from "@/components/Sidebar";
import { t, ui } from "@/lib/mockData";
import { SCREEN_TRANSITION } from "@/lib/tokens";
import { cn } from "@/lib/utils";
import { DefectProof } from "@/screens/DefectProof";
import { Divergence } from "@/screens/Divergence";
import { Output } from "@/screens/Output";
import { Ripple } from "@/screens/Ripple";
import { Shelf } from "@/screens/Shelf";
import { Timeline } from "@/screens/Timeline";
import { useDemoStore, type Screen } from "@/store/demoStore";

/**
 * The single route (FRONTEND_TECH_STACK.md §0).
 *
 * Every screen is a view switched by store state, not a Next.js route, so
 * Framer Motion transitions carry across screen changes instead of being torn
 * down by a navigation event. Do NOT split these into /shelf, /timeline, …
 */
const SCREENS: Record<Screen, React.ComponentType> = {
  shelf: Shelf,
  timeline: Timeline,
  divergence: Divergence,
  ripple: Ripple,
  output: Output,
  defect: DefectProof,
};

export default function Page() {
  const screen = useDemoStore((s) => s.screen);
  const locale = useDemoStore((s) => s.locale);
  const presenterMode = useDemoStore((s) => s.presenterMode);
  const back = useDemoStore((s) => s.back);

  const CurrentScreen = SCREENS[screen];

  return (
    <div className={cn("min-h-screen", presenterMode && "presenting")}>
      {presenterMode ? null : <Sidebar locale={locale} />}
      <AppHeader />

      <main
        style={presenterMode ? undefined : { paddingLeft: SIDEBAR_WIDTH }}
        className={cn(
          "mx-auto w-full px-6 pb-24 lg:px-16",
          // Presenter Mode drops the max-width constraint and the header/sidebar offset.
          presenterMode ? "pt-12" : "max-w-[1280px] pt-28",
        )}
      >
        {/* One direction, but never a dead end — there is always a way back. */}
        <div className="mb-8 flex min-h-[40px] items-center">
          {screen !== "shelf" ? (
            <CanonButton variant="ghost" arrow={false} onClick={back}>
              {`← ${screen === "timeline" ? t(ui.backToStories, locale) : "BACK"}`}
            </CanonButton>
          ) : null}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={screen}
            initial={SCREEN_TRANSITION.initial}
            animate={SCREEN_TRANSITION.animate}
            exit={SCREEN_TRANSITION.exit}
          >
            <CurrentScreen />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
