import { beforeEach, describe, expect, it } from "vitest";

import { useDemoStore } from "@/store/demoStore";

const initial = useDemoStore.getState();

beforeEach(() => {
  useDemoStore.setState(initial, true);
});

describe("demoStore", () => {
  it("starts on the shelf in Hindi", () => {
    const state = useDemoStore.getState();
    expect(state.screen).toBe("shelf");
    expect(state.locale).toBe("hi");
    expect(state.presenterMode).toBe(false);
  });

  it("walks the rehearsed path forward", () => {
    const s = () => useDemoStore.getState();

    s().selectStory("ST-01");
    expect(s().screen).toBe("timeline");

    s().selectCharacter("CH-02");
    s().openMoment("E03", "M-0301");
    expect(s().screen).toBe("divergence");
    expect(s().momentId).toBe("M-0301");

    s().selectAlternative("ALT-A");
    s().commitFlip();
    expect(s().screen).toBe("ripple");

    s().setRipple("RP-0301-A");
    s().markCascadeComplete();
    s().showOutput();
    expect(s().screen).toBe("output");
    expect(s().rippleId).toBe("RP-0301-A");
  });

  it("clears the episode when the character changes", () => {
    const s = () => useDemoStore.getState();
    s().selectCharacter("CH-02");
    s().openMoment("E03", "M-0301");
    s().selectCharacter("CH-03");

    // An episode only means something alongside the character whose moment it
    // holds — keeping E03 selected here would let a stale pair through.
    expect(s().episodeId).toBeNull();
    expect(s().momentId).toBeNull();
  });

  it("discards a stale ripple when a new divergence is committed", () => {
    const s = () => useDemoStore.getState();
    s().setRipple("RP-0301-A");
    s().markCascadeComplete();
    s().commitFlip();

    expect(s().rippleId).toBeNull();
    expect(s().cascadeComplete).toBe(false);
  });

  it("walks back through the flow, and treats the defect proof as a detour", () => {
    const s = () => useDemoStore.getState();
    s().showOutput();
    s().showDefect();
    expect(s().screen).toBe("defect");

    s().back();
    expect(s().screen).toBe("output");
    s().back();
    expect(s().screen).toBe("ripple");
  });

  it("cannot navigate back past the shelf", () => {
    const s = () => useDemoStore.getState();
    s().back();
    expect(s().screen).toBe("shelf");
  });

  it("keeps stage settings across a reset", () => {
    const s = () => useDemoStore.getState();
    s().toggleLocale();
    s().togglePresenterMode();
    s().selectStory("ST-01");
    s().reset();

    // Demo progress resets; stage settings are not progress.
    expect(s().screen).toBe("shelf");
    expect(s().storyId).toBeNull();
    expect(s().locale).toBe("en");
    expect(s().presenterMode).toBe(true);
  });

  it("toggles locale both ways", () => {
    const s = () => useDemoStore.getState();
    s().toggleLocale();
    expect(s().locale).toBe("en");
    s().toggleLocale();
    expect(s().locale).toBe("hi");
  });
});
