"use client";

import { DefectDemoTrigger } from "@/components/DefectDemoTrigger";
import { SceneOutputPanel } from "@/components/SceneOutputPanel";
import { VerifierBadge } from "@/components/VerifierBadge";
import { useRegenerate } from "@/lib/api";
import { t, ui } from "@/lib/mockData";
import { useDemoStore } from "@/store/demoStore";

/**
 * Screen 5 — Output (REQUIREMENTS.md §6). The payoff.
 *
 * Text is MUST-tier and has to be rock solid. Narration and stills are
 * SHOULD-tier and are not built — see docs/API_CONTRACT_NOTES.md.
 */
export function Output() {
  const locale = useDemoStore((s) => s.locale);
  const rippleId = useDemoStore((s) => s.rippleId);
  const episodeId = useDemoStore((s) => s.episodeId);
  const altId = useDemoStore((s) => s.altId);

  const { data: result, isPending } = useRegenerate(rippleId);

  if (isPending || !result) {
    return (
      <p className="type-cite text-ink-muted py-24 text-center">
        {t(ui.loadingScene, locale)}
      </p>
    );
  }

  const header = [
    episodeId ?? "",
    t(ui.revisedLabel, locale),
    `${t(ui.branchLabel, locale)} ${altId ?? ""}`,
  ]
    .filter(Boolean)
    .join(" · ")
    .toUpperCase();

  return (
    /* Paper centred in the viewport; the badge and trigger align to its left
       edge rather than to the page (DESIGN.md §8). */
    <section className="mx-auto flex w-fit flex-col items-start gap-8">
      <SceneOutputPanel
        header={header}
        sceneText={result.sceneText}
        locale={locale}
      />

      <VerifierBadge verifier={result.verifier} locale={locale} />

      <DefectDemoTrigger />
    </section>
  );
}
