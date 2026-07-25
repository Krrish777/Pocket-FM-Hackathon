/**
 * CONTRACT — turn-loop API (Task 5), mirrored field-for-field from the backend.
 * ─────────────────────────────────────────────────────────────────────
 * Source of truth: `src/story_engine/api/schemas.py` +
 * `src/story_engine/api/routers/play.py`. The backend is authoritative — if
 * this file and the backend disagree, the backend wins and this file is wrong.
 *
 * Machine-checked by `tests/e2e/test_api_contract.py`, which fetches the
 * served `/api/v1/openapi.json` and asserts every path and field name declared
 * here actually exists on the wire. A backend rename fails that test instead
 * of silently breaking the UI at demo time. Keep the two in sync explicitly —
 * see the comment binding them in that test file.
 *
 * Endpoints (mounted under `settings.api_v1_str`, i.e. `/api/v1`):
 *   GET  /characters
 *   POST /play
 *   GET  /play/{run_id}
 *   POST /play/{run_id}/act
 *   POST /play/{run_id}/replay-as
 */

// ── GET /characters → CharacterResponse[] ─────────────────────────────

export type Character = {
  id: string;
  name: string;
};

// ── TurnResponse.choices[] — deliberately NEVER carries `consequence` ──
// (see `ChoiceOptionResponse` docstring in schemas.py: serialising the
// consequence would leak the future of the story to the client).

export type ChoiceDTO = {
  id: string;
  label: string;
  source_work_id: string | null;
};

// ── TurnResponse.citations[] ───────────────────────────────────────────

export type CitationDTO = {
  fact_id: string;
  source_id: string;
  chapter: number;
  quote: string;
};

// ── TurnResponse — one rendered beat, from one character's POV ────────

export type TurnDTO = {
  index: number;
  chapter: number;
  protagonist: string;
  scene: string;
  choices: ChoiceDTO[];
  citations: CitationDTO[];
  withheld_count: number;
};

// ── ActResponse.reactions[] — derived per-character directives ────────

export type ReactionDTO = {
  name: string;
  tension: number;
  blind_spots: string[];
};

// ── POST /play ──────────────────────────────────────────────────────────

export type PlayRequest = {
  character_id: string;
};

export type PlayResponse = {
  run_id: string;
  turn: TurnDTO;
};

// ── POST /play/{run_id}/act ─────────────────────────────────────────────

export type ActRequest = {
  action: string;
};

export type ActResponse = {
  run_id: string;
  turn: TurnDTO;
  interpreted_as: string;
  reactions: ReactionDTO[];
};

// ── POST /play/{run_id}/replay-as ──────────────────────────────────────

export type ReplayAsRequest = {
  character_id: string;
};

export type ReplayResponse = {
  run_id: string;
  turns: TurnDTO[];
};

// ── Uniform error envelope (api/errors.py: `_handle`) ──────────────────
// `context` is present only when the underlying `StoryEngineError` carries
// one (e.g. `NoIntentMatchError`'s offered option labels on a 422) — omitted
// entirely otherwise, never `null`/`{}`.

export type ApiErrorBody = {
  code: string;
  message: string;
  context?: Record<string, unknown>;
};

export type ApiErrorEnvelope = {
  error: ApiErrorBody;
};
