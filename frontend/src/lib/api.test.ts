import { describe, expect, it } from "vitest";

import { client } from "@/lib/api";

/**
 * Guards the mock ⇄ live seam. These assert the *shape* the CanonClient
 * contract promises, so if the real backend is swapped in behind the same
 * interface the UI keeps working. See docs/API_CONTRACT_NOTES.md.
 */
describe("CanonClient (mock implementation)", () => {
  it("lists the fixed 5-character cast", async () => {
    const characters = await client.getCharacters();
    expect(characters).toHaveLength(5);
    for (const character of characters) {
      expect(character.id).toBeTruthy();
      expect(character.name.hi).toBeTruthy();
      expect(character.name.en).toBeTruthy();
    }
  });

  it("returns Dexter's run with at least 5 turns", async () => {
    const run = await client.getRun("CH-01");
    expect(run.protagonistId).toBe("CH-01");
    expect(run.turns.length).toBeGreaterThanOrEqual(5);
  });

  it("resolves a choice to the delta the run itself carries for that turn", async () => {
    const run = await client.getRun("CH-01");
    const { delta } = await client.postChoice(run.runId, 1, "T1-A");
    expect(delta).toEqual(run.turns[0].delta);
  });

  it("always flags the planted defect", async () => {
    const result = await client.postDefectDemo();
    expect(result.verifier.status).toBe("flagged");
  });
});
