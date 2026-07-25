"use client";

/**
 * Real, zero-dependency narration via the browser's built-in Web Speech API.
 *
 * Higgsfield voice generation is out of credits in this workspace right now
 * (confirmed live, twice) — rather than fake a "voice" that silently does
 * nothing on stage, this uses `speechSynthesis`, which actually speaks, needs
 * no network call, and can't run out of credits mid-demo. Swap this module
 * for real generated narration later; every call site here is already the
 * seam (same pattern as the old audio.ts cue surface).
 */

let currentUtterance: SpeechSynthesisUtterance | null = null;

function pickVoice(): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis.getVoices();
  // Prefer a higher-quality network/neural-sounding voice if the browser has one.
  return (
    voices.find((v) => /Google|Natural|Neural/i.test(v.name) && v.lang.startsWith("en")) ??
    voices.find((v) => v.lang.startsWith("en")) ??
    voices[0]
  );
}

export function speak(text: string, onBoundaryChange?: (speaking: boolean) => void): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  const voice = pickVoice();
  if (voice) utterance.voice = voice;
  // Slightly slower and a touch lower — reads as more deliberate/dramatic than the default.
  utterance.rate = 0.94;
  utterance.pitch = 0.92;
  utterance.onstart = () => onBoundaryChange?.(true);
  utterance.onend = () => onBoundaryChange?.(false);
  utterance.onerror = () => onBoundaryChange?.(false);

  currentUtterance = utterance;
  window.speechSynthesis.speak(utterance);
}

export function stopSpeaking(): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  currentUtterance = null;
}

export function isSpeechSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}
