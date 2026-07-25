"use client";

import { useEffect, useState } from "react";

import { CanonButton } from "@/components/CanonButton";
import type { Character, ReactionDTO, TurnDTO } from "@/lib/contract";
import { PlayApiError, playApi } from "@/lib/playClient";
import { cn } from "@/lib/utils";

/**
 * The live turn-loop screen — REQUIREMENTS: task-10 (`.superpowers/sdd/demo-path-integration/`).
 *
 * A new, self-contained route. It does NOT reuse the six existing (mock-data)
 * screens or their store — see task-9-report.md §3 for why: the backend
 * serves a turn loop (pick a character → type an action → get a rendered
 * turn), not the browse/pick-alternative/ripple-diff/regenerate model those
 * screens were built for. This page talks to the real API through the
 * existing same-origin proxy (`app/api/[...path]/route.ts`) via `playClient.ts`.
 *
 * Nothing here is rendered when a request fails — failures show what failed,
 * never a guessed placeholder. That honesty is the product's own argument
 * (every fact is checked, every gap is disclosed as a count, not hidden).
 */

type LastAction =
  | { kind: "none" }
  | { kind: "interpreted"; interpretedAs: string; reactions: ReactionDTO[] }
  | { kind: "no_match"; message: string; options: string[] }
  | { kind: "run_complete"; message: string };

type ReplayState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "loaded"; characterId: string; turn: TurnDTO };

export default function PlayPage() {
  // ── Cast ──────────────────────────────────────────────────────────────
  const [characters, setCharacters] = useState<Character[] | null>(null);
  const [castError, setCastError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    playApi
      .getCharacters()
      .then((cast) => {
        if (!cancelled) setCharacters(cast);
      })
      .catch((err: unknown) => {
        if (!cancelled) setCastError(describeError(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // ── Run state ─────────────────────────────────────────────────────────
  const [runId, setRunId] = useState<string | null>(null);
  const [playedAsId, setPlayedAsId] = useState<string | null>(null);
  const [turn, setTurn] = useState<TurnDTO | null>(null);
  const [selectPending, setSelectPending] = useState(false);
  const [selectError, setSelectError] = useState<string | null>(null);
  const [lastAction, setLastAction] = useState<LastAction>({ kind: "none" });

  // ── Natural-language action ──────────────────────────────────────────────
  const [actionText, setActionText] = useState("");
  const [actionPending, setActionPending] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // ── Replay-as ─────────────────────────────────────────────────────────
  const [replayCharacterId, setReplayCharacterId] = useState<string>("");
  const [replay, setReplay] = useState<ReplayState>({ kind: "idle" });

  const nameFor = (id: string): string =>
    characters?.find((c) => c.id === id)?.name ?? id;

  async function handleSelectCharacter(characterId: string): Promise<void> {
    setSelectPending(true);
    setSelectError(null);
    try {
      const res = await playApi.play({ character_id: characterId });
      setRunId(res.run_id);
      setPlayedAsId(characterId);
      setTurn(res.turn);
      setLastAction({ kind: "none" });
      setActionText("");
      setActionError(null);
      setReplay({ kind: "idle" });
      setReplayCharacterId("");
    } catch (err) {
      setSelectError(describeError(err));
    } finally {
      setSelectPending(false);
    }
  }

  async function handleAct(): Promise<void> {
    if (!runId || actionText.trim().length === 0) return;
    setActionPending(true);
    setActionError(null);
    try {
      const res = await playApi.act(runId, { action: actionText });
      setTurn(res.turn);
      setLastAction({
        kind: "interpreted",
        interpretedAs: res.interpreted_as,
        reactions: res.reactions,
      });
      setActionText("");
      // A new turn invalidates whatever "replay as" view was showing.
      setReplay({ kind: "idle" });
    } catch (err) {
      if (err instanceof PlayApiError && err.code === "no_intent_match") {
        const options = Array.isArray(err.context?.options)
          ? (err.context.options as unknown[]).filter(
              (o): o is string => typeof o === "string",
            )
          : [];
        setLastAction({ kind: "no_match", message: err.message, options });
        setActionError(null);
      } else if (err instanceof PlayApiError && err.code === "run_complete") {
        setLastAction({ kind: "run_complete", message: err.message });
        setActionError(null);
      } else {
        setActionError(describeError(err));
      }
    } finally {
      setActionPending(false);
    }
  }

  async function handleReplayAs(characterId: string): Promise<void> {
    if (!runId || characterId.length === 0) return;
    setReplay({ kind: "loading" });
    try {
      const res = await playApi.replayAs(runId, { character_id: characterId });
      const lastTurn = res.turns.at(-1);
      if (!lastTurn) {
        setReplay({ kind: "error", message: "replay-as returned no turns" });
        return;
      }
      setReplay({ kind: "loaded", characterId, turn: lastTurn });
    } catch (err) {
      setReplay({ kind: "error", message: describeError(err) });
    }
  }

  return (
    <div className="min-h-screen px-6 pb-24 pt-16 lg:px-16">
      <div className="mx-auto w-full max-w-[880px]">
        <header className="mb-10">
          <p className="type-label text-ink-muted">live turn loop</p>
          <h1 className="type-title text-ink-bright mt-1 text-3xl">Play</h1>
          <p className="type-body text-ink-muted mt-2">
            Talks to the real Canon Kernel API — not the rehearsed mock demo.
          </p>
        </header>

        {!runId ? (
          <CharacterSelect
            characters={characters}
            castError={castError}
            selectPending={selectPending}
            selectError={selectError}
            onSelect={handleSelectCharacter}
          />
        ) : (
          <div className="flex flex-col gap-10">
            <div className="type-label text-ink-muted flex items-center gap-2">
              <span>
                Playing as <span className="text-ink-bright">{nameFor(playedAsId ?? "")}</span>
              </span>
              <span aria-hidden="true">·</span>
              <button
                type="button"
                className="cursor-pointer underline decoration-ink-line underline-offset-2 hover:text-ink-bright"
                onClick={() => {
                  setRunId(null);
                  setTurn(null);
                  setPlayedAsId(null);
                }}
              >
                start over
              </button>
            </div>

            {turn ? <TurnView turn={turn} /> : null}

            {lastAction.kind === "interpreted" ? (
              <ReactionsPanel
                interpretedAs={lastAction.interpretedAs}
                reactions={lastAction.reactions}
              />
            ) : null}

            {lastAction.kind === "no_match" ? (
              <NoMatchPanel
                message={lastAction.message}
                options={lastAction.options}
                onPick={(label) => setActionText(label)}
              />
            ) : null}

            {lastAction.kind === "run_complete" ? (
              <RunCompletePanel message={lastAction.message} />
            ) : null}

            <ActionInput
              value={actionText}
              onChange={setActionText}
              onSubmit={handleAct}
              pending={actionPending}
              error={actionError}
            />

            {runId && characters ? (
              <ReplaySection
                characters={characters}
                selectedId={replayCharacterId}
                onSelectedIdChange={setReplayCharacterId}
                onReplay={handleReplayAs}
                replay={replay}
                baselineWithheldCount={turn?.withheld_count ?? null}
              />
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Character selection ───────────────────────────────────────────────────

function CharacterSelect({
  characters,
  castError,
  selectPending,
  selectError,
  onSelect,
}: {
  characters: Character[] | null;
  castError: string | null;
  selectPending: boolean;
  selectError: string | null;
  onSelect: (characterId: string) => void;
}) {
  if (castError) {
    return <ErrorBanner message={`Could not load the cast: ${castError}`} />;
  }

  if (!characters) {
    return <p className="type-body text-ink-muted">Loading the cast…</p>;
  }

  if (characters.length === 0) {
    return <p className="type-body text-ink-muted">The backend returned no characters.</p>;
  }

  return (
    <div>
      <p className="type-label text-ink-muted mb-4">choose who to play</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
        {characters.map((character) => (
          <button
            key={character.id}
            type="button"
            disabled={selectPending}
            onClick={() => onSelect(character.id)}
            className={cn(
              "border-ink-line bg-shell-raised/30 type-body text-ink-bright cursor-pointer rounded-2xl border p-5 text-left transition-colors duration-150 ease-out hover:border-ink-muted",
              "disabled:pointer-events-none disabled:opacity-50",
            )}
          >
            <div className="type-body font-semibold">{character.name}</div>
            <div className="type-index text-ink-muted mt-1 normal-case">{character.id}</div>
          </button>
        ))}
      </div>
      {selectPending ? (
        <p className="type-body text-ink-muted mt-4">Starting the run…</p>
      ) : null}
      {selectError ? (
        <div className="mt-4">
          <ErrorBanner message={`Could not start the run: ${selectError}`} />
        </div>
      ) : null}
    </div>
  );
}

// ── Turn rendering ─────────────────────────────────────────────────────────

function TurnView({ turn }: { turn: TurnDTO }) {
  return (
    <section className="border-ink-line rounded-2xl border p-6">
      <div className="type-index text-ink-muted mb-3 flex items-center gap-3 normal-case">
        <span>turn {turn.index}</span>
        <span aria-hidden="true">·</span>
        <span>chapter {turn.chapter}</span>
        <span aria-hidden="true">·</span>
        <span>as {turn.protagonist}</span>
      </div>

      <p className="type-prose text-ink-bright whitespace-pre-line text-lg">{turn.scene}</p>

      {turn.choices.length > 0 ? (
        <div className="border-ink-line mt-6 border-t pt-4">
          <p className="type-label text-ink-muted mb-2">you could:</p>
          <ul className="flex flex-col gap-1">
            {turn.choices.map((choice) => (
              <li key={choice.id} className="type-body text-ink-bright">
                {choice.label}
                {choice.source_work_id !== null ? (
                  <span className="type-index text-ink-faint ml-2 normal-case">
                    from fan fiction {choice.source_work_id}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="border-ink-line mt-6 border-t pt-4">
        <p className="type-label text-ink-muted mb-2">
          {turn.citations.length} fact{turn.citations.length === 1 ? "" : "s"} cited ·{" "}
          {turn.withheld_count} withheld from this view
        </p>
        {turn.citations.length > 0 ? (
          <ul className="flex flex-col gap-2">
            {turn.citations.map((citation) => (
              <li
                key={citation.fact_id}
                className="type-cite text-ink-muted border-ink-line rounded-md border px-3 py-2"
              >
                <span className="text-ink-bright">ch.{citation.chapter}</span> —{" "}
                &ldquo;{citation.quote}&rdquo;{" "}
                <span className="text-ink-faint">
                  ({citation.source_id} · {citation.fact_id})
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}

function ReactionsPanel({
  interpretedAs,
  reactions,
}: {
  interpretedAs: string;
  reactions: ReactionDTO[];
}) {
  return (
    <section className="border-ink-line rounded-2xl border p-6">
      <p className="type-label text-ink-muted mb-4">
        interpreted your action as: <span className="text-ink-bright">{interpretedAs}</span>
      </p>
      {reactions.length === 0 ? (
        <p className="type-body text-ink-muted">No other characters reacted to this turn.</p>
      ) : (
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {reactions.map((reaction) => (
            <li key={reaction.name} className="border-ink-line rounded-lg border p-3">
              <div className="type-body text-ink-bright font-semibold">{reaction.name}</div>
              <div className="type-index text-ink-muted mt-1 normal-case">
                tension {reaction.tension}
              </div>
              {reaction.blind_spots.length > 0 ? (
                <ul className="type-index text-ink-faint mt-2 list-disc pl-4 normal-case">
                  {reaction.blind_spots.map((spot) => (
                    <li key={spot}>{spot}</li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function NoMatchPanel({
  message,
  options,
  onPick,
}: {
  message: string;
  options: string[];
  onPick: (label: string) => void;
}) {
  return (
    <section className="border-accent/60 bg-accent-wash rounded-2xl border p-6">
      <p className="type-body text-ink-bright">
        That action didn&apos;t map to anything this run understands.
      </p>
      <p className="type-index text-ink-muted mt-1 normal-case">{message}</p>
      {options.length > 0 ? (
        <>
          <p className="type-label text-ink-muted mt-4 mb-2">try one of the offered options</p>
          <div className="flex flex-wrap gap-2">
            {options.map((label) => (
              <button
                key={label}
                type="button"
                onClick={() => onPick(label)}
                className="border-ink-line bg-shell-base type-index text-ink-bright cursor-pointer rounded-full border px-4 py-2 normal-case hover:border-ink-muted"
              >
                {label}
              </button>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}

function RunCompletePanel({ message }: { message: string }) {
  return (
    <section className="border-ink-line bg-shell-raised/30 rounded-2xl border p-6">
      <p className="type-body text-ink-bright">
        This run has reached the end of its branches.
      </p>
      <p className="type-index text-ink-muted mt-1 normal-case">{message}</p>
    </section>
  );
}

function ActionInput({
  value,
  onChange,
  onSubmit,
  pending,
  error,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  pending: boolean;
  error: string | null;
}) {
  return (
    <section>
      <p className="type-label text-ink-muted mb-2">what do you do?</p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
        className="flex gap-3"
      >
        <input
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={pending}
          placeholder="Type your action…"
          className="border-ink-line bg-shell-base type-body text-ink-bright flex-1 rounded-lg border px-4 py-3 outline-none focus:border-ink-muted disabled:opacity-50"
        />
        <CanonButton
          type="submit"
          disabled={pending || value.trim().length === 0}
          arrow={false}
        >
          {pending ? "Sending…" : "Act"}
        </CanonButton>
      </form>
      {error ? (
        <div className="mt-3">
          <ErrorBanner message={`The action failed: ${error}`} />
        </div>
      ) : null}
    </section>
  );
}

// ── Replay as ────────────────────────────────────────────────────────────

function ReplaySection({
  characters,
  selectedId,
  onSelectedIdChange,
  onReplay,
  replay,
  baselineWithheldCount,
}: {
  characters: Character[];
  selectedId: string;
  onSelectedIdChange: (id: string) => void;
  onReplay: (characterId: string) => void;
  replay: ReplayState;
  baselineWithheldCount: number | null;
}) {
  return (
    <section className="border-ink-line rounded-2xl border p-6">
      <p className="type-label text-ink-muted mb-4">replay this run as…</p>
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={selectedId}
          onChange={(event) => onSelectedIdChange(event.target.value)}
          className="border-ink-line bg-shell-base type-body text-ink-bright rounded-lg border px-3 py-2"
        >
          <option value="">Select a character…</option>
          {characters.map((character) => (
            <option key={character.id} value={character.id}>
              {character.name}
            </option>
          ))}
        </select>
        <CanonButton
          type="button"
          variant="secondary"
          arrow={false}
          disabled={selectedId.length === 0 || replay.kind === "loading"}
          onClick={() => onReplay(selectedId)}
        >
          {replay.kind === "loading" ? "Replaying…" : "Replay"}
        </CanonButton>
      </div>

      {replay.kind === "error" ? (
        <div className="mt-4">
          <ErrorBanner message={`Replay failed: ${replay.message}`} />
        </div>
      ) : null}

      {replay.kind === "loaded" ? (
        <div className="mt-6">
          <p className="type-label text-ink-muted mb-3">
            as {replay.characterId} —{" "}
            <span className="text-ink-bright">
              {replay.turn.withheld_count} facts withheld
            </span>
            {baselineWithheldCount !== null ? (
              <>
                {" "}
                vs.{" "}
                <span className="text-ink-bright">{baselineWithheldCount}</span> in the current
                view
                {replay.turn.withheld_count !== baselineWithheldCount ? (
                  <span className="text-accent">
                    {" "}
                    (
                    {replay.turn.withheld_count > baselineWithheldCount ? "+" : ""}
                    {replay.turn.withheld_count - baselineWithheldCount})
                  </span>
                ) : null}
              </>
            ) : null}
          </p>
          <TurnView turn={replay.turn} />
        </div>
      ) : null}
    </section>
  );
}

// ── Shared bits ─────────────────────────────────────────────────────────

function ErrorBanner({ message }: { message: string }) {
  return (
    <p className="type-body border-accent/60 bg-accent-wash text-ink-bright rounded-lg border px-4 py-3">
      {message}
    </p>
  );
}

function describeError(err: unknown): string {
  if (err instanceof PlayApiError) {
    return `${err.code}: ${err.message}`;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return String(err);
}
