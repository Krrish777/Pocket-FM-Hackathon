import { describe, expect, it } from "vitest";

import { client } from "@/lib/api";

/**
 * Guards the mock ⇄ live seam. These assert the *shape* the CanonClient
 * contract promises, so if the real backend is swapped in behind the same
 * interface the UI keeps working. See docs/API_CONTRACT_NOTES.md.
 */
describe("CanonClient (mock implementation)", () => {
  it("lists stories with everything the shelf renders", async () => {
    const stories = await client.getStories();
    expect(stories.length).toBeGreaterThan(0);

    for (const story of stories) {
      expect(story.id).toBeTruthy();
      expect(story.title.hi).toBeTruthy();
      expect(story.title.en).toBeTruthy();
      expect(typeof story.episodeCount).toBe("number");
      expect(typeof story.factCount).toBe("number");
    }
  });

  it("returns a story with episodes and cast", async () => {
    const story = await client.getStory("ST-01");
    expect(story.episodes.length).toBeGreaterThan(0);
    expect(story.characters.length).toBeGreaterThan(0);
  });

  it("scopes moments to an episode and character", async () => {
    const found = await client.getMoments("ST-01", "E03", "CH-02");
    expect(found).toHaveLength(1);
    expect(found[0].momentId).toBe("M-0301");
  });

  it("returns nothing for a pair with no authored moment", async () => {
    // This is why the timeline resolves moments before enabling an episode:
    // the empty result is real, and must never surface as a dead click.
    const found = await client.getMoments("ST-01", "E01", "CH-02");
    expect(found).toHaveLength(0);
  });

  it("computes the rehearsed ripple: 11 invalidated / 20 hold / 3 new", async () => {
    const ripple = await client.postDivergence("ST-01", "M-0301", "ALT-A");
    expect(ripple.rippleId).toBe("RP-0301-A");
    expect(ripple.invalidated).toHaveLength(11);
    expect(ripple.held).toHaveLength(20);
    expect(ripple.newNeeded).toHaveLength(3);
  });

  it("computes a distinct, non-fatal ripple for ALT-C", async () => {
    const ripple = await client.postDivergence("ST-01", "M-0301", "ALT-C");
    expect(ripple.rippleId).toBe("RP-0301-C");
    expect(ripple.invalidated).toHaveLength(9);
    expect(ripple.held).toHaveLength(14);
  });

  it("regenerates a consistent scene for the rehearsed branch", async () => {
    const result = await client.postRegenerate("RP-0301-A");
    expect(result.verifier.status).toBe("ok");
    expect(result.sceneText.en.length).toBeGreaterThan(50);
  });

  it("always flags the planted defect", async () => {
    const result = await client.postDefectDemo();
    expect(result.verifier.status).toBe("flagged");
  });
});
