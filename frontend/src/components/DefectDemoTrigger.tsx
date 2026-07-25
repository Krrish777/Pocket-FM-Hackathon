"use client";

import { CanonButton } from "@/components/CanonButton";
import { useDemoStore } from "@/store/demoStore";

/**
 * One-click known-broken-branch demo (REQUIREMENTS.md §6 Screen 6).
 *
 * This is the falsifiable proof moment — arguably as important for judge trust
 * as the Ripple Map itself. It must be reachable in a single click and behave
 * identically every time, so it is a plain navigation to a cached result.
 */
export function DefectDemoTrigger() {
  const showDefect = useDemoStore((s) => s.showDefect);

  return (
    <CanonButton variant="secondary" arrow onClick={showDefect}>
      RUN BROKEN BRANCH
    </CanonButton>
  );
}
