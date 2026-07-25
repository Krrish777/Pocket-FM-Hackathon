"use client";

import { TriangleAlert } from "lucide-react";

import { CanonButton } from "@/components/CanonButton";
import { SceneOutputPanel } from "@/components/SceneOutputPanel";
import { VerifierBadge } from "@/components/VerifierBadge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useDefectDemo } from "@/lib/api";
import { t, ui } from "@/lib/mockData";
import { useDemoStore } from "@/store/demoStore";

/**
 * Screen 6 — Planted-Defect Proof (REQUIREMENTS.md §6).
 *
 * A deliberately broken branch, so the verifier is caught working live with a
 * real citation. Not a "real" user screen — it exists to make the consistency
 * claim falsifiable in front of an audience.
 */
export function DefectProof() {
  const locale = useDemoStore((s) => s.locale);
  const back = useDemoStore((s) => s.back);

  const { data: result, isPending } = useDefectDemo(true);

  if (isPending || !result) {
    return (
      <p className="type-cite text-ink-muted py-24 text-center">
        {t(ui.loadingScene, locale)}
      </p>
    );
  }

  const flagged = result.verifier.status === "flagged" ? result.verifier : null;

  return (
    <section className="flex flex-col items-start gap-8">
      {/* Accent, not `--state-invalid`: the reserved red belongs to the verdict
          itself (the badge below), so it still means something when it appears. */}
      <span className="type-index bg-accent-wash text-accent flex w-fit items-center gap-2 rounded-full px-3 py-1.5">
        <TriangleAlert size={14} aria-hidden="true" />
        DEMONSTRATION · BROKEN BRANCH
      </span>

      <SceneOutputPanel
        header="DRAFT · UNVERIFIED"
        sceneText={result.sceneText}
        locale={locale}
      />

      <VerifierBadge verifier={result.verifier} locale={locale} />

      <div className="flex gap-4">
        {flagged ? (
          <Dialog>
            <DialogTrigger
              render={<CanonButton variant="secondary" arrow={false} />}
            >
              VIEW BOTH PASSAGES
            </DialogTrigger>

            <DialogContent className="bg-shell-base border-ink-line max-w-3xl rounded-2xl sm:max-w-3xl">
              <DialogHeader>
                <DialogTitle className="type-title text-ink-bright">
                  {t(ui.verifierFlagged, locale)}
                </DialogTitle>
                <DialogDescription className="type-cite text-ink-muted">
                  {flagged.citation.episodeRef}
                </DialogDescription>
              </DialogHeader>

              <div className="grid gap-8 md:grid-cols-2 md:gap-0">
                <div className="md:pr-8">
                  <span className="type-index text-ink-muted mb-3 block">
                    {t(ui.draftClaimLabel, locale)}
                  </span>
                  <p className="bg-paper-warm text-paper-ink type-prose rounded-2xl p-6">
                    {t(flagged.citation.draftClaim, locale)}
                  </p>
                </div>

                <div className="border-ink-line md:border-l md:pl-8">
                  <span className="type-index text-ink-muted mb-3 block">
                    {t(ui.canonSaysLabel, locale)}
                  </span>
                  <p className="bg-paper-aged text-paper-ink type-prose rounded-2xl p-6">
                    {t(flagged.citation.canonFact, locale)}
                  </p>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        ) : null}

        <CanonButton variant="ghost" arrow={false} onClick={back}>
          ← BACK
        </CanonButton>
      </div>
    </section>
  );
}
