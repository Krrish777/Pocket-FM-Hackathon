import { Sparkles } from "lucide-react";

import { t, ui } from "@/lib/mockData";
import type { Locale } from "@/lib/mockData";

/**
 * The wordmark + mark lockup — DESIGN.md §5.
 *
 * The mark is the divergence glyph: one vertical timeline with a single branch
 * splitting off at the 40% mark. It is literally the product.
 */
export function Logo({ locale }: { locale: Locale }) {
  return (
    <div className="flex items-center gap-3">
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        className="text-accent"
        aria-hidden="true"
      >
        <path d="M12 2 V22" />
        <path d="M12 9.6 H21" />
        <circle cx="12" cy="9.6" r="2" fill="currentColor" stroke="none" />
      </svg>

      <span className="font-story text-ink-bright text-[1.05rem] font-semibold tracking-[0.24em] uppercase">
        {t(ui.appName, locale)}
      </span>

      <span className="type-index text-ink-muted hidden items-center gap-1.5 sm:inline-flex">
        {t(ui.appSubtitle, locale)}
        <Sparkles className="size-3" strokeWidth={1.75} aria-hidden="true" />
      </span>
    </div>
  );
}
