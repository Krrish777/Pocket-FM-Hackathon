"use client";

import { useEffect } from "react";

import { cn } from "@/lib/utils";
import { useDemoStore } from "@/store/demoStore";

/**
 * Presenter Mode toggle — DESIGN.md §8, REQUIREMENTS.md Screen 0.
 *
 * Presenter Mode hides the header entirely, which would strand the operator
 * with no way back. Two escapes, both deliberate:
 *   1. the `P` key toggles from anywhere;
 *   2. while presenting, a near-invisible corner control reveals on hover.
 *
 * "Never let a crash end the demo" (REQUIREMENTS.md §10) applies to the demo
 * controls themselves, not just to screens.
 */
export function PresenterModeToggle() {
  const presenterMode = useDemoStore((s) => s.presenterMode);
  const togglePresenterMode = useDemoStore((s) => s.togglePresenterMode);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "p" && event.key !== "P") return;
      // Don't hijack the key while the operator is typing somewhere.
      const target = event.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      togglePresenterMode();
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [togglePresenterMode]);

  return (
    <button
      type="button"
      onClick={togglePresenterMode}
      aria-pressed={presenterMode}
      title="Presenter mode (P)"
      className={cn(
        "type-index border px-3 py-2 transition-all duration-[160ms] ease-out",
        presenterMode
          ? // Escape hatch: parked top-right, all but invisible until hovered.
            "fixed top-4 right-4 z-50 border-ink-line text-ink-faint opacity-15 hover:opacity-100 hover:text-ink-bright"
          : "border-ink-line text-ink-muted hover:border-ink-muted hover:text-ink-bright",
      )}
    >
      {presenterMode ? "EXIT" : "PRESENT"}
    </button>
  );
}
