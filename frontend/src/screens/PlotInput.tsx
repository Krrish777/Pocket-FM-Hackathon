"use client";

import { Wand2 } from "lucide-react";
import { useState } from "react";

import { playFlip } from "@/lib/audio";
import { t, ui } from "@/lib/mockData";
import { cn } from "@/lib/utils";
import { useDemoStore } from "@/store/demoStore";

/**
 * PlotInput — free-text "what if" (testing branch only; project_context.md's
 * SD-3 keeps this OUT for the real build, but this branch exists purely to
 * get a demo video out fast — see docs/API_CONTRACT_NOTES.md history).
 *
 * Deliberately, fully fake: whatever is typed is accepted as-is and always
 * drives the same rich pre-authored beat. The point is the *illusion* that
 * "your words became this story", not a real generate-then-verify pipeline —
 * there is no time left before the submission deadline for that to be safe
 * to run live, and it isn't what this branch is for.
 */
export function PlotInput() {
  const locale = useDemoStore((s) => s.locale);
  const freeformPrompt = useDemoStore((s) => s.freeformPrompt);
  const setFreeformPrompt = useDemoStore((s) => s.setFreeformPrompt);
  const submitPlot = useDemoStore((s) => s.submitPlot);
  const [generating, setGenerating] = useState(false);

  const handleSubmit = () => {
    if (!freeformPrompt.trim() || generating) return;
    playFlip();
    setGenerating(true);
    setTimeout(() => {
      setGenerating(false);
      submitPlot();
    }, 1400);
  };

  return (
    <section className="mx-auto flex w-full max-w-2xl flex-col gap-8">
      <header className="flex flex-col gap-3">
        <h1 className="type-title text-ink-bright">{t(ui.plotInputHeading, locale)}</h1>
        <p className="type-body text-ink-muted">{t(ui.plotInputSub, locale)}</p>
      </header>

      <textarea
        value={freeformPrompt}
        onChange={(e) => setFreeformPrompt(e.target.value)}
        placeholder={t(ui.plotInputPlaceholder, locale)}
        rows={4}
        disabled={generating}
        className={cn(
          "border-ink-line bg-shell-raised/30 text-ink-bright type-body w-full resize-none rounded-2xl border p-5 outline-none",
          "focus:border-accent/60 placeholder:text-ink-faint",
        )}
      />

      <div className="flex justify-end">
        <button
          type="button"
          disabled={!freeformPrompt.trim() || generating}
          onClick={handleSubmit}
          className={cn(
            "type-label flex cursor-pointer items-center gap-2 rounded-full px-6 py-3.5 text-shell-void transition-opacity duration-150 ease-out",
            "disabled:pointer-events-none disabled:opacity-40",
          )}
          style={{ background: "linear-gradient(135deg, #f2994a, #e0608f 60%, #a86ee0)" }}
        >
          <Wand2 className="size-4" strokeWidth={1.75} />
          {generating ? t(ui.generatingLabel, locale) : t(ui.generateButton, locale)}
        </button>
      </div>
    </section>
  );
}
