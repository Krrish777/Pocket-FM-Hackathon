import { beforeEach, describe, expect, it } from "vitest";

import { useDemoStore } from "@/store/demoStore";

const initial = useDemoStore.getState();

beforeEach(() => {
  useDemoStore.setState(initial, true);
});

describe("demoStore (testing branch — one-beat flow)", () => {
  it("starts on the shelf in English", () => {
    const state = useDemoStore.getState();
    expect(state.screen).toBe("shelf");
    expect(state.locale).toBe("en");
    expect(state.presenterMode).toBe(false);
  });

  it("walks the full flow: shelf -> characterSelect -> plotInput -> ripple -> output", () => {
    const s = () => useDemoStore.getState();

    s().selectStory("ST-01");
    expect(s().screen).toBe("characterSelect");
    expect(s().selectedStoryId).toBe("ST-01");

    s().selectCharacter("CH-01");
    expect(s().screen).toBe("plotInput");
    expect(s().protagonistId).toBe("CH-01");

    s().setFreeformPrompt("What if he got caught?");
    s().submitPlot();
    expect(s().screen).toBe("ripple");
    expect(s().history).toHaveLength(1);

    s().markCascadeComplete();
    s().proceedToOutput();
    expect(s().screen).toBe("output");
  });

  it("walks back through the flow, and treats the defect proof as a detour off output", () => {
    const s = () => useDemoStore.getState();
    s().showDefect();
    expect(s().screen).toBe("defect");
    s().back();
    expect(s().screen).toBe("output");
  });

  it("cannot navigate back past the shelf", () => {
    const s = () => useDemoStore.getState();
    s().back();
    expect(s().screen).toBe("shelf");
  });

  it("runs the replay independently of the live playthrough", () => {
    const s = () => useDemoStore.getState();
    s().startReplay("CH-02");
    expect(s().screen).toBe("replay");
    expect(s().replayCharacterId).toBe("CH-02");
    expect(s().replayTurnIndex).toBe(1);

    s().advanceReplay(5);
    expect(s().replayTurnIndex).toBe(2);

    s().exitReplay();
    expect(s().screen).toBe("output");
    expect(s().replayCharacterId).toBeNull();
  });

  it("keeps stage settings across a reset", () => {
    const s = () => useDemoStore.getState();
    s().toggleLocale();
    s().togglePresenterMode();
    s().selectStory("ST-01");
    s().reset();

    expect(s().screen).toBe("shelf");
    expect(s().selectedStoryId).toBeNull();
    expect(s().locale).toBe("hi");
    expect(s().presenterMode).toBe(true);
  });

  it("toggles locale both ways", () => {
    const s = () => useDemoStore.getState();
    s().toggleLocale();
    expect(s().locale).toBe("hi");
    s().toggleLocale();
    expect(s().locale).toBe("en");
  });
});
