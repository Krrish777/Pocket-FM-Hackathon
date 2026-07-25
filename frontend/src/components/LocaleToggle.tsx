"use client";

import { playSelect } from "@/lib/audio";
import { cn } from "@/lib/utils";
import { useDemoStore } from "@/store/demoStore";

const LOCALES = [
  { id: "hi", label: "हि" },
  { id: "en", label: "EN" },
] as const;

/**
 * Hindi/English switch. The seed story is Hindi-first (mockData.ts declares
 * `hi` the default), but every string ships in both, so judges who don't read
 * Devanagari are never locked out.
 *
 * Rendered as a segmented text control, not a switch — a pill-shaped switch
 * would break the radius discipline in DESIGN.md §4.
 */
export function LocaleToggle() {
  const locale = useDemoStore((s) => s.locale);
  const toggleLocale = useDemoStore((s) => s.toggleLocale);

  return (
    <div className="border-ink-line flex border" role="group" aria-label="Language">
      {LOCALES.map((option) => {
        const active = locale === option.id;
        return (
          <button
            key={option.id}
            type="button"
            aria-pressed={active}
            onClick={() => {
              if (!active) {
                playSelect();
                toggleLocale();
              }
            }}
            className={cn(
              "type-index px-3 py-2 transition-colors duration-[160ms] ease-out",
              active
                ? "bg-accent text-shell-void"
                : "text-ink-muted hover:text-ink-bright",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
