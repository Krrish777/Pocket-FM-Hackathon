"use client";

import { Logo } from "@/components/Logo";
import { LocaleToggle } from "@/components/LocaleToggle";
import { PresenterModeToggle } from "@/components/PresenterModeToggle";
import { SIDEBAR_WIDTH } from "@/components/Sidebar";
import { useDemoStore } from "@/store/demoStore";

/**
 * The global frame — DESIGN.md §8.
 *
 * 64px tall, a single hairline rule along the bottom, logo left, controls right.
 * Offset by `SIDEBAR_WIDTH` so it sits beside the persistent left rail rather
 * than under it. Hidden entirely in Presenter Mode; the toggle keeps its own
 * escape hatch.
 */
export function AppHeader() {
  const locale = useDemoStore((s) => s.locale);
  const presenterMode = useDemoStore((s) => s.presenterMode);
  const reset = useDemoStore((s) => s.reset);

  if (presenterMode) return <PresenterModeToggle />;

  return (
    <header
      style={{ left: SIDEBAR_WIDTH }}
      className="border-ink-line bg-shell-void fixed inset-x-0 top-0 z-40 h-16 border-b"
    >
      <div className="mx-auto flex h-full max-w-[1280px] items-center justify-between px-6 lg:px-16">
        <button
          type="button"
          onClick={reset}
          className="cursor-pointer"
          aria-label="Back to shelf"
        >
          <Logo locale={locale} />
        </button>

        <div className="flex items-center gap-4">
          <LocaleToggle />
          <PresenterModeToggle />
        </div>
      </div>
    </header>
  );
}
