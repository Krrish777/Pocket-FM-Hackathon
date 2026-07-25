"use client";

import { EyeOff, RotateCcw } from "lucide-react";

import { CanonButton } from "@/components/CanonButton";
import { SceneOutputPanel } from "@/components/SceneOutputPanel";
import { useCharacters, useRun } from "@/lib/api";
import { t, ui } from "@/lib/mockData";
import { useDemoStore } from "@/store/demoStore";

/**
 * Replay — the closing beat (S3/§8.1, project_context.md).
 *
 * A thin, parameterized variant of the Turn renderer: walks the SAME
 * completed run, but reads `characterViews[replayCharacterId]` instead of the
 * protagonist's. No choices here — this is a read-only lens over data that
 * already exists (M8: the renderer takes a character as a parameter), proving
 * both headline claims at once — per-character epistemic state, and a side
 * character becoming the protagonist without breaking continuity.
 */
export function Replay() {
  const locale = useDemoStore((s) => s.locale);
  const protagonistId = useDemoStore((s) => s.protagonistId);
  const replayCharacterId = useDemoStore((s) => s.replayCharacterId);
  const replayTurnIndex = useDemoStore((s) => s.replayTurnIndex);
  const advanceReplay = useDemoStore((s) => s.advanceReplay);
  const exitReplay = useDemoStore((s) => s.exitReplay);

  const { data: run } = useRun(protagonistId);
  const { data: characters } = useCharacters();

  const turn = run?.turns.find((candidate) => candidate.turnIndex === replayTurnIndex);
  const replayCharacter = characters?.find((c) => c.id === replayCharacterId);
  const view = replayCharacterId && turn ? turn.characterViews[replayCharacterId] : null;

  if (!run || !turn || !view || !replayCharacter) return null;

  const isFinalTurn = replayTurnIndex >= run.turns.length;

  return (
    <section className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <span className="type-index bg-accent-wash text-accent flex w-fit items-center gap-2 rounded-full px-3 py-1.5">
          <RotateCcw size={14} aria-hidden="true" />
          {t(ui.replayBadgeLabel, locale)} · {t(replayCharacter.name, locale)} ·{" "}
          {`${t(ui.turnLabel, locale)} ${turn.turnIndex} / ${run.turns.length}`}
        </span>
        <h1 className="type-title text-ink-bright">{t(run.title, locale)}</h1>
      </header>

      <SceneOutputPanel
        header={t(ui.canonLabel, locale)}
        sceneText={view.sceneText}
        locale={locale}
      />

      {view.notYetKnown && view.notYetKnown.length > 0 ? (
        <div className="border-accent/40 bg-accent-wash/40 flex flex-col gap-3 rounded-2xl border p-5">
          <span className="type-label text-accent flex items-center gap-2">
            <EyeOff size={16} aria-hidden="true" />
            {t(ui.notYetKnownHeading, locale)}
          </span>
          <ul className="flex flex-col gap-2">
            {view.notYetKnown.map((item, i) => (
              <li key={i} className="type-body text-ink-muted">
                — {t(item, locale)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="flex justify-between">
        <CanonButton variant="ghost" arrow={false} onClick={exitReplay}>
          {t(ui.exitReplayButton, locale)}
        </CanonButton>

        <CanonButton variant="secondary" arrow onClick={() => advanceReplay(run.turns.length)}>
          {isFinalTurn ? t(ui.exitReplayButton, locale) : t(ui.continueButton, locale)}
        </CanonButton>
      </div>
    </section>
  );
}
