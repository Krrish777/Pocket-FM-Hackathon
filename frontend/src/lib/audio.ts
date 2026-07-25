/**
 * Audio cue seam.
 *
 * FRONTEND_TECH_STACK.md §4 specifies exactly three one-shot cues plus one
 * ambient bed, played through Howler. No audio assets exist yet, and Howler
 * cannot synthesise — it needs real files.
 *
 * So this module ships the **call surface** with no-op implementations. Every
 * interaction site already calls the right cue, which means enabling sound
 * later is a change to this file only, not a hunt through components.
 *
 * To enable: drop files in `public/audio/`, add Howler, and implement `play()`.
 * Do not add a fourth cue — three is the spec'd limit, and more reads as noisy
 * on stage.
 */

const AUDIO_ENABLED = false;

type Cue = "select" | "flip" | "tick";

function play(cue: Cue): void {
  if (!AUDIO_ENABLED) return;
  // Intentionally unimplemented — see module docstring.
  void cue;
}

/** Soft cue — selecting an alternative, a character, a story. */
export const playSelect = (): void => play("select");

/** Deep, decisive cue — the FLIP commit. One of the two assertive moments. */
export const playFlip = (): void => play("flip");

/** Small falling tick — one per invalidated node during the Ripple cascade. */
export const playTick = (): void => play("tick");

/** True when cues are actually audible. Lets UI hide a mute control that would do nothing. */
export const isAudioEnabled = (): boolean => AUDIO_ENABLED;
