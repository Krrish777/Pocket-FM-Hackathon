import { describe, expect, it } from "vitest";

import {
  defectDemo,
  moments,
  regenerateALTA,
  regenerateALTC,
  rippleALTA,
  rippleALTC,
  storyDetail,
  stories,
  t,
  ui,
  type RippleResult,
} from "@/lib/mockData";

/**
 * These assert invariants of the seed dataset, never exact generated prose.
 * The point is to catch a dataset edit that would silently break the demo —
 * a fact landing in two states, a moment pointing at a character who isn't in
 * the episode, a counter no longer matching what the verifier claims.
 */

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

describe("story structure", () => {
  it("exposes the playable story first on the shelf", () => {
    expect(stories[0].id).toBe("ST-01");
    expect(storyDetail.id).toBe("ST-01");
  });

  it("agrees with the shelf summary on episode count", () => {
    const summary = stories.find((s) => s.id === storyDetail.id);
    expect(summary?.episodeCount).toBe(storyDetail.episodes.length);
  });

  it("only references characters that exist in the cast", () => {
    const cast = new Set(storyDetail.characters.map((c) => c.id));
    for (const episode of storyDetail.episodes) {
      for (const characterId of episode.characters) {
        expect(cast, `${episode.id} → ${characterId}`).toContain(characterId);
      }
    }
  });
});

describe("moments", () => {
  it("anchors every moment to a real episode containing that character", () => {
    for (const moment of moments) {
      const episode = storyDetail.episodes.find(
        (e) => e.id === moment.episodeId,
      );
      expect(episode, moment.momentId).toBeDefined();
      expect(episode!.characters).toContain(moment.characterId);
    }
  });

  it("offers 2-3 bounded alternatives — never freeform", () => {
    for (const moment of moments) {
      expect(moment.alternatives.length).toBeGreaterThanOrEqual(2);
      expect(moment.alternatives.length).toBeLessThanOrEqual(3);
    }
  });

  it("keeps the rehearsed demo path intact (E03 · CH-02 · ALT-A)", () => {
    const rehearsed = moments.find((m) => m.momentId === "M-0301");
    expect(rehearsed?.episodeId).toBe("E03");
    expect(rehearsed?.characterId).toBe("CH-02");
    expect(rehearsed?.alternatives.map((a) => a.altId)).toContain("ALT-A");
  });
});

describe.each([
  ["ALT-A", rippleALTA],
  ["ALT-C", rippleALTC],
])("ripple %s", (_label, ripple: RippleResult) => {
  it("never places a fact in two states at once", () => {
    const ids = [
      ...ripple.invalidated,
      ...ripple.held,
      ...ripple.newNeeded,
    ].map((f) => f.factId);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("invalidates something and keeps something", () => {
    expect(ripple.invalidated.length).toBeGreaterThan(0);
    expect(ripple.held.length).toBeGreaterThan(0);
  });
});

describe("regeneration", () => {
  it("verifies against exactly the number of facts that still hold", () => {
    // The badge claims a number; it must be the number the ripple produced,
    // or the consistency claim is decoration rather than evidence.
    const ok = regenerateALTA.verifier;
    expect(ok.status).toBe("ok");
    if (ok.status === "ok") {
      expect(ok.verifiedAgainst).toBe(rippleALTA.held.length);
    }

    const okC = regenerateALTC.verifier;
    if (okC.status === "ok") {
      expect(okC.verifiedAgainst).toBe(rippleALTC.held.length);
    }
  });

  it("returns prose in both locales", () => {
    expect(regenerateALTA.sceneText.hi.length).toBeGreaterThan(50);
    expect(regenerateALTA.sceneText.en.length).toBeGreaterThan(50);
  });
});

describe("planted defect", () => {
  it("is flagged and carries a citation with a source reference", () => {
    expect(defectDemo.verifier.status).toBe("flagged");
    if (defectDemo.verifier.status === "flagged") {
      const { citation } = defectDemo.verifier;
      expect(citation.draftClaim.en).toBeTruthy();
      expect(citation.canonFact.en).toBeTruthy();
      expect(citation.episodeRef).toMatch(/E\d{2}/);
    }
  });
});
