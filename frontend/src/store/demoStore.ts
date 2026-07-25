"use client";

import { create } from "zustand";

import type { CharacterId, Locale } from "@/lib/mockData";

/**
 * The whole demo is ONE route (FRONTEND_TECH_STACK.md §0). Screens are views
 * switched by this store, so Framer Motion transitions carry across screen
 * changes instead of being torn down by a navigation event.
 *
 * testing branch: collapsed the 5-turn compounding loop into ONE dramatic
 * beat (shelf → characterSelect → plotInput → ripple → output) for a
 * demo-video-first flow — free-text plot input instead of bounded per-turn
 * choices. `currentTurnIndex`/`history` are kept and just point at a fixed
 * turn (4) so Ripple/Output's existing data-fetching needs no rework.
 */
export type Screen = "shelf" | "characterSelect" | "plotInput" | "ripple" | "output" | "replay" | "defect";

const PREVIOUS_SCREEN: Record<Screen, Screen> = {
  shelf: "shelf",
  characterSelect: "shelf",
  plotInput: "characterSelect",
  ripple: "plotInput",
  output: "ripple",
  replay: "output",
  defect: "output",
};

/** The single turn whose delta/scene powers the one-beat flow. */
const BEAT_TURN_INDEX = 4;
const BEAT_CHOICE_ID = "T4-A";

type DemoState = {
  screen: Screen;
  locale: Locale;
  presenterMode: boolean;

  selectedStoryId: string | null;
  protagonistId: CharacterId | null;
  freeformPrompt: string;

  currentTurnIndex: number;
  history: { turnIndex: number; chosenChoiceId: string }[];
  cascadeComplete: boolean;

  replayCharacterId: CharacterId | null;
  replayTurnIndex: number;

  sidebarActive: string;

  selectStory: (storyId: string) => void;
  selectCharacter: (characterId: CharacterId) => void;
  setFreeformPrompt: (text: string) => void;
  submitPlot: () => void;
  markCascadeComplete: () => void;
  proceedToOutput: () => void;
  showDefect: () => void;
  startReplay: (characterId: CharacterId) => void;
  advanceReplay: (totalTurns: number) => void;
  exitReplay: () => void;
  back: () => void;
  reset: () => void;
  toggleLocale: () => void;
  togglePresenterMode: () => void;
  setSidebarActive: (id: string) => void;
};

const INITIAL = {
  screen: "shelf" as Screen,
  locale: "en" as Locale,
  presenterMode: false,
  selectedStoryId: null,
  protagonistId: null,
  freeformPrompt: "",
  currentTurnIndex: BEAT_TURN_INDEX,
  history: [] as { turnIndex: number; chosenChoiceId: string }[],
  cascadeComplete: false,
  replayCharacterId: null,
  replayTurnIndex: 1,
  sidebarActive: "home",
};

export const useDemoStore = create<DemoState>((set, get) => ({
  ...INITIAL,

  selectStory: (storyId) => set({ selectedStoryId: storyId, screen: "characterSelect" }),

  selectCharacter: (characterId) => set({ protagonistId: characterId, screen: "plotInput" }),

  setFreeformPrompt: (text) => set({ freeformPrompt: text }),

  /* Fully fake, on purpose (testing branch): whatever was typed is accepted
     as-is and always drives the same rich, pre-authored turn — the point is
     the illusion of "your words became this story", not a real generation
     pipeline, for a demo video with hours to spare, not weeks. */
  submitPlot: () => {
    set({
      history: [{ turnIndex: BEAT_TURN_INDEX, chosenChoiceId: BEAT_CHOICE_ID }],
      cascadeComplete: false,
      screen: "ripple",
    });
  },

  markCascadeComplete: () => set({ cascadeComplete: true }),

  proceedToOutput: () => set({ screen: "output" }),

  showDefect: () => set({ screen: "defect" }),

  startReplay: (characterId) => set({ replayCharacterId: characterId, replayTurnIndex: 1, screen: "replay" }),

  advanceReplay: (totalTurns) => {
    const { replayTurnIndex } = get();
    if (replayTurnIndex >= totalTurns) {
      set({ screen: "output", replayCharacterId: null });
    } else {
      set({ replayTurnIndex: replayTurnIndex + 1 });
    }
  },

  exitReplay: () => set({ screen: "output", replayCharacterId: null }),

  back: () => set({ screen: PREVIOUS_SCREEN[get().screen] }),

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
