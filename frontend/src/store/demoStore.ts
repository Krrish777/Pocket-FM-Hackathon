"use client";

import { create } from "zustand";

import type { Locale } from "@/lib/mockData";

/**
 * The whole demo is ONE route (FRONTEND_TECH_STACK.md §0). Screens are views
 * switched by this store, so Framer Motion transitions carry across screen
 * changes instead of being torn down by a navigation event.
 */
export type Screen =
  | "shelf"
  | "timeline"
  | "divergence"
  | "ripple"
  | "output"
  | "defect";

/** The linear flow (REQUIREMENTS.md §5). `back` walks this in reverse. */
const PREVIOUS_SCREEN: Record<Screen, Screen> = {
  shelf: "shelf",
  timeline: "shelf",
  divergence: "timeline",
  ripple: "divergence",
  output: "ripple",
  // The defect proof is a detour off the output screen, not a step in the flow.
  defect: "output",
};

type DemoState = {
  screen: Screen;
  locale: Locale;
  presenterMode: boolean;

  storyId: string | null;
  characterId: string | null;
  episodeId: string | null;
  momentId: string | null;
  altId: string | null;
  rippleId: string | null;

  /** Gates the "SEE WHAT HAPPENS" button — it appears only after the cascade settles. */
  cascadeComplete: boolean;

  /**
   * Which sidebar rail item reads as active. Only "home" maps to a real
   * destination (the shelf); the rest are shelf-realism, same spirit as the
   * two non-playable story cards — present for tone, not wired to a screen.
   */
  sidebarActive: string;

  selectStory: (storyId: string) => void;
  selectCharacter: (characterId: string) => void;
  openMoment: (episodeId: string, momentId: string) => void;
  selectAlternative: (altId: string) => void;
  commitFlip: () => void;
  setRipple: (rippleId: string) => void;
  markCascadeComplete: () => void;
  showOutput: () => void;
  showDefect: () => void;
  back: () => void;
  reset: () => void;
  toggleLocale: () => void;
  togglePresenterMode: () => void;
  setSidebarActive: (id: string) => void;
};

const INITIAL = {
  screen: "shelf" as Screen,
  // mockData.ts declares Hindi the default locale; the seed story is Hindi-first.
  locale: "hi" as Locale,
  presenterMode: false,
  storyId: null,
  characterId: null,
  episodeId: null,
  momentId: null,
  altId: null,
  rippleId: null,
  cascadeComplete: false,
  sidebarActive: "home",
};

export const useDemoStore = create<DemoState>((set, get) => ({
  ...INITIAL,

  selectStory: (storyId) => set({ storyId, screen: "timeline" }),

  /* Choosing a different character invalidates the episode selection —
     an episode is only meaningful alongside the character whose moment it holds. */
  selectCharacter: (characterId) =>
    set({ characterId, episodeId: null, momentId: null }),

  openMoment: (episodeId, momentId) =>
    set({ episodeId, momentId, altId: null, screen: "divergence" }),

  selectAlternative: (altId) => set({ altId }),

  /* A new divergence invalidates any previously computed ripple. */
  commitFlip: () =>
    set({ screen: "ripple", rippleId: null, cascadeComplete: false }),

  setRipple: (rippleId) => set({ rippleId }),

  markCascadeComplete: () => set({ cascadeComplete: true }),

  showOutput: () => set({ screen: "output" }),

  showDefect: () => set({ screen: "defect" }),

  back: () => set({ screen: PREVIOUS_SCREEN[get().screen] }),

  /* Presenter mode and locale deliberately survive a reset — they are stage
     settings, not demo progress. Re-running the demo must not undo them. */
  reset: () =>
    set({
      ...INITIAL,
      locale: get().locale,
      presenterMode: get().presenterMode,
    }),

  toggleLocale: () => set({ locale: get().locale === "hi" ? "en" : "hi" }),

  togglePresenterMode: () => set({ presenterMode: !get().presenterMode }),

  setSidebarActive: (id) => set({ sidebarActive: id }),
}));
