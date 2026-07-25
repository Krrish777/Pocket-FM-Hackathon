"use client";

import { motion } from "framer-motion";
import { ShieldCheck, TriangleAlert } from "lucide-react";

import { t, ui, type Locale, type VerifierResult } from "@/lib/mockData";

/**
 * VerifierBadge — Output/Defect redesign (same pattern as Shelf/Timeline).
 *
 * Both states matter: the green one is the everyday payoff, the amber one is
 * the falsifiable proof shown in Planted-Defect Mode. The flagged state shakes
 * once on entrance so a room watching a projector cannot miss it.
 *
 * Alongside the Ripple Map, this is the only place `--state-*` colours are
 * legal — that reservation is semantic, not decorative, so the redesign keeps
 * the colours and only changes shape (pill / rounded card).
 */
export function VerifierBadge({
  verifier,
  locale,
}: {
  verifier: VerifierResult;
  locale: Locale;
}) {
  if (verifier.status === "ok") {
    return (
      <div
        data-testid="verifier-badge"
        data-status="ok"
        className="border-state-hold inline-flex flex-col gap-2 rounded-2xl border px-5 py-3"
      >
        <span className="flex items-center gap-2">
          <ShieldCheck size={16} className="text-state-hold" aria-hidden="true" />
          <span className="type-label text-state-hold">
            {t(ui.verifierOk, locale)}
          </span>
        </span>
        <span className="type-cite text-ink-muted">
          {t(ui.verifierOkDetail, locale)} · {verifier.verifiedAgainst}
        </span>
      </div>
    );
  }

  const { citation } = verifier;

  return (
    <motion.div
      data-testid="verifier-badge"
      data-status="flagged"
      initial={{ x: 0 }}
      animate={{ x: [0, -4, 4, -3, 3, 0] }}
      transition={{ duration: 0.4, ease: "easeInOut" }}
      className="border-state-invalid inline-flex flex-col gap-3 rounded-2xl border px-5 py-4"
      style={{ backgroundColor: "rgb(209 73 91 / 0.06)" }}
    >
      <span className="flex items-center gap-2">
        <TriangleAlert size={16} className="text-state-invalid" aria-hidden="true" />
        <span className="type-label text-state-invalid">
          {t(ui.verifierFlagged, locale)}
        </span>
      </span>

      {/* Two-column citation: label column faint, value column bright. */}
      <dl className="type-cite grid grid-cols-[auto_1fr] gap-x-6 gap-y-1">
        <dt className="text-ink-faint">{t(ui.draftClaimLabel, locale)}</dt>
        <dd className="text-ink-bright">{t(citation.draftClaim, locale)}</dd>

        <dt className="text-ink-faint">{t(ui.canonSaysLabel, locale)}</dt>
        <dd className="text-ink-bright">{t(citation.canonFact, locale)}</dd>

        <dt className="text-ink-faint">REF</dt>
        <dd className="text-ink-bright">{citation.episodeRef}</dd>
      </dl>
    </motion.div>
  );
}
