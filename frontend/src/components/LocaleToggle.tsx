"use client";

import { Globe } from "lucide-react";

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
 * Devanagari are never locked out — both options stay visible at once rather
 * than hiding behind a single toggle.
 *
 * Pill-shaped per the Shelf redesign direction — the earlier "radius
 * discipline" rule (sharp corners only) is superseded on this screen.
 */
export function LocaleToggle() {
  const locale = useDemoStore((s) => s.locale);
  const toggleLocale = useDemoStore((s) => s.toggleLocale);

  return (
    <div
      role="group"
      aria-label="Language"
      className="border-ink-line bg-shell-raised/60 text-ink-muted flex items-center gap-1 rounded-full border py-1 pr-1 pl-3"
    >
      <Globe className="size-3.5" strokeWidth={1.75} aria-hidden="true" />
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
              "type-index cursor-pointer rounded-full px-3 py-1.5 transition-colors duration-150 ease-out",
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
