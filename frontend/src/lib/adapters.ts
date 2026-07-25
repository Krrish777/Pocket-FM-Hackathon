/**
 * ADAPTERS — the seam between the live turn-loop payloads (`contract.ts`) and
 * the shapes the existing (mock-data-only) screens already know how to render
 * (`mockData.ts`: `Moment`, `RippleResult`, and friends).
 *
 * RENAME AND RESHAPE ONLY. No business logic, no invented defaults, no
 * fabricated localization. Where a screen's target shape needs a field the
 * turn-loop API does not serve, that field is DELIBERATELY OMITTED here
 * rather than invented — see the "unbridgeable gaps" section of
 * `.superpowers/sdd/demo-path-integration/task-9-report.md` for the full
 * list and what the backend would need to add to close each one.
 *
 * This file adapts what CAN be adapted today. It does not, and must not,
 * pretend the turn-loop API is a drop-in replacement for the single-flip
 * divergence contract (`api.ts`'s `CanonClient`) the screens were built
 * against — that rewire is Task 10's job, at the call sites, not here.
 */

import type { Character as BackendCharacter, ChoiceDTO, TurnDTO } from "@/lib/contract";

// ── Character ────────────────────────────────────────────────────────────
// `contract.ts`'s `Character` has only `id`/`name` — no bilingual `role`,
// `blurb`, or `portraitUrl` (mockData.ts's `Character` needs all four).
// See report gap "Character — cast screens".

export type AdaptedCharacter = {
  id: string;
  /** Backend serves one string; mockData.ts's `Character.name` is `LocalizedText`.
   * Not translated here — see report gap "Character — cast screens". */
  name: string;
};

export function adaptCharacter(character: BackendCharacter): AdaptedCharacter {
  return { id: character.id, name: character.name };
}

// ── Choice ───────────────────────────────────────────────────────────────
// Renamed to read like mockData.ts's `Alternative`, but `weight`/`tone`
// (consumed by RippleGraph/RippleCounters styling) have no backend
// analogue. See report gap "Alternative.weight/tone — Ripple screen".

export type AdaptedChoice = {
  id: string;
  label: string;
  sourceWorkId: string | null;
};

export function adaptChoice(choice: ChoiceDTO): AdaptedChoice {
  return {
    id: choice.id,
    label: choice.label,
    sourceWorkId: choice.source_work_id,
  };
}

// ── Turn ─────────────────────────────────────────────────────────────────
// A rendered beat (`TurnDTO`) is not an authored branch point: it carries no
// `momentId`/`episodeId`/`originalLine`, because it is one turn of an
// open-ended playthrough, not a pick-an-alternative-for-this-moment UI.
// See report gap "Moment — Timeline/Divergence screens".

export type AdaptedTurn = {
  index: number;
  chapter: number;
  protagonist: string;
  scene: string;
  choices: AdaptedChoice[];
  withheldCount: number;
};

export function adaptTurn(turn: TurnDTO): AdaptedTurn {
  return {
    index: turn.index,
    chapter: turn.chapter,
    protagonist: turn.protagonist,
    scene: turn.scene,
    choices: turn.choices.map(adaptChoice),
    withheldCount: turn.withheld_count,
  };
}

// ── RippleResult — NOT adapted ───────────────────────────────────────────
// `RippleResult` (invalidated/held/newNeeded fact deltas computed from one
// divergence) has no backend analogue at all: the turn loop never diffs
// facts across a choice — it only ever returns the citations backing the
// CURRENT beat (`TurnDTO.citations`), which is a different question
// ("what do I know right now") than a ripple ("what changed because of my
// choice"). No adapter is written for it. See report gap "RippleResult —
// Ripple/Output screens" for what the backend would need to add.
