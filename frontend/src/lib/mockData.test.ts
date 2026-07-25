import { describe, expect, it } from "vitest";

import {
  characters,
  defectDemo,
  run,
  t,
  ui,
  type CharacterId,
} from "@/lib/mockData";

/**
 * These assert invariants of the seed dataset, never exact generated prose.
 * The point is to catch a dataset edit that would silently break the demo —
 * a turn missing a character's view, a fact landing in two states, a counter
 * no longer matching what the verifier claims.
 */

const ALL_CHARACTER_IDS: CharacterId[] = ["CH-01", "CH-02", "CH-03", "CH-04", "CH-05"];

describe("t()", () => {
  it("resolves each locale", () => {
    expect(t(ui.appName, "en")).toBe("CANON");
    expect(t(ui.appName, "hi")).toBe("कैनन");
  });

  it("has both locales populated for every UI string", () => {
    for (const [key, value] of Object.entries(ui)) {
      expect(value.hi, `${key}.hi`).toBeTruthy();
      expect(value.en, `${key}.en`).toBeTruthy();
    }
  });
});

describe("cast", () => {
  it("is exactly the fixed 5, in order (SD-6, M8 — no protagonist special-casing)", () => {
    expect(characters.map((c) => c.id)).toEqual(ALL_CHARACTER_IDS);
  });

  it("gives every character both locales for every field", () => {
    for (const character of characters) {
      expect(character.name.hi, character.id).toBeTruthy();
      expect(character.name.en, character.id).toBeTruthy();
      expect(character.role.en).toBeTruthy();
      expect(character.blurb.en).toBeTruthy();
    }
  });
});

describe("run", () => {
  it("is Dexter's playthrough, at least 5 turns deep (§4.1/§8/SD-12)", () => {
    expect(run.protagonistId).toBe("CH-01");
    expect(run.turns.length).toBeGreaterThanOrEqual(5);
  });

  it("numbers turns sequentially starting at 1", () => {
    run.turns.forEach((turn, i) => expect(turn.turnIndex).toBe(i + 1));
  });

  it("gives every turn a characterView for all 5 cast members — M8's testable invariant", () => {
    for (const turn of run.turns) {
      expect(Object.keys(turn.characterViews).sort()).toEqual([...ALL_CHARACTER_IDS].sort());
      for (const characterId of ALL_CHARACTER_IDS) {
        const view = turn.characterViews[characterId];
        expect(view.sceneText.en, `turn ${turn.turnIndex} · ${characterId}`).toBeTruthy();
        expect(view.beliefSummary.en, `turn ${turn.turnIndex} · ${characterId}`).toBeTruthy();
      }
    }
  });

  it("offers 2-4 bounded choices per turn — never freeform (SD-3)", () => {
    for (const turn of run.turns) {
      expect(turn.choices.length).toBeGreaterThanOrEqual(2);
      expect(turn.choices.length).toBeLessThanOrEqual(4);
    }
  });

  it("sources every choice from fan-fiction (M4/SD-9)", () => {
    for (const turn of run.turns) {
      for (const choice of turn.choices) {
        expect(choice.source.workTitle, choice.choiceId).toBeTruthy();
        expect(choice.source.author, choice.choiceId).toBeTruthy();
      }
    }
  });

  it("commits to a choice that is actually one of the turn's own options", () => {
    for (const turn of run.turns) {
      const ids = turn.choices.map((c) => c.choiceId);
      expect(ids, `turn ${turn.turnIndex}`).toContain(turn.chosenChoiceId);
    }
  });

  it("never places a fact in two delta buckets at once, per turn", () => {
    for (const turn of run.turns) {
      const ids = [...turn.delta.invalidated, ...turn.delta.held, ...turn.delta.newNeeded].map(
        (f) => f.factId,
      );
      expect(new Set(ids).size, `turn ${turn.turnIndex}`).toBe(ids.length);
    }
  });

  it("verifies against exactly the number of facts that still hold, per turn", () => {
    for (const turn of run.turns) {
      if (turn.verifier.status === "ok") {
        expect(turn.verifier.verifiedAgainst, `turn ${turn.turnIndex}`).toBe(turn.delta.held.length);
      }
    }
  });

  it("keeps the rehearsed demo path intact (always the -A choice)", () => {
    for (const turn of run.turns) {
      expect(turn.chosenChoiceId).toBe(`T${turn.turnIndex}-A`);
    }
  });

  it("gives the replay character (Debra) something she doesn't yet know by the final turn", () => {
    const finalTurn = run.turns.at(-1)!;
    const debra = finalTurn.characterViews["CH-02"];
    expect(debra.notYetKnown?.length ?? 0).toBeGreaterThan(0);
  });
});

describe("planted defect", () => {
  it("is flagged and carries a citation with a source reference", () => {
    expect(defectDemo.verifier.status).toBe("flagged");
    if (defectDemo.verifier.status === "flagged") {
      const { citation } = defectDemo.verifier;
      expect(citation.draftClaim.en).toBeTruthy();
      expect(citation.canonFact.en).toBeTruthy();
      expect(citation.sourceRef).toMatch(/Turn \d/);
    }
  });
});
