"use client";

import { t, type Locale, type LocalizedText } from "@/lib/mockData";
import { cn } from "@/lib/utils";

/**
 * SceneOutputPanel — Output redesign (same pattern as Shelf/Timeline).
 *
 * Narrative always sits on paper; the machine keeps the dark shell. This is the
 * one component allowed to cast `--shadow-lift`, because the paper physically
 * sits above the shell — everywhere else, separation is a hairline rule. That
 * physicality metaphor is untouched; only the paper's corners and the header
 * chrome pick up the new rounded/pill language.
 */
export function SceneOutputPanel({
  header,
  sceneText,
  locale,
}: {
  /** On the shell, above the paper: "EPISODE 03 · REVISED · BRANCH ALT-A". */
  header: string;
  sceneText: LocalizedText;
  locale: Locale;
}) {
  const paragraphs = t(sceneText, locale)
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);

  /* The drop cap is Latin-only on purpose. Devanagari letterforms carry matras
     above and below the baseline, so a floated 3.5rem initial collides with the
     following line instead of nesting into it. */
  const dropCap = locale === "en";

  return (
    <div className="flex flex-col gap-4">
      <span className="type-index bg-accent-wash text-accent w-fit rounded-full px-3 py-1.5">
        {header}
      </span>

      <article
        data-testid="scene-text"
        className="bg-paper-warm text-paper-ink border-paper-aged max-w-[68ch] rounded-2xl border p-12"
        style={{ boxShadow: "var(--shadow-lift)" }}
      >
        {paragraphs.map((paragraph, i) => (
          <p
            key={i}
            className={cn(
              "type-prose",
              i > 0 && "mt-6",
              dropCap &&
                i === 0 &&
                "first-letter:text-accent first-letter:font-story first-letter:mr-2 first-letter:float-left first-letter:text-[3.5rem] first-letter:leading-[0.8]",
            )}
          >
            {paragraph}
          </p>
        ))}
      </article>
    </div>
  );
}
