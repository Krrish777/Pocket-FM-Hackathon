"""Application exception hierarchy.

One base (`StoryEngineError`) with specific typed subclasses carrying a stable `code` and optional
structured `context`. Deliberately **HTTP-agnostic** — no status codes here; the API adapter maps
`code -> HTTP status` at the edge (see `adapters`/`api/errors.py`). Never raise bare `Exception`;
never swallow. See .claude/rules/python-design.md.
"""


class StoryEngineError(Exception):
    """Base for every error raised by the application/domain."""

    code: str = "story_engine_error"

    def __init__(
        self, message: str, *, context: dict[str, object] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}


# --- domain / validation ---------------------------------------------------------------------
class DomainError(StoryEngineError):
    """A rule or invariant in the story domain was violated."""

    code = "domain_error"


class StoryNotFoundError(DomainError):
    code = "story_not_found"


class ContinuityError(DomainError):
    """Generated content contradicts canonical state (e.g. a dead character acting)."""

    code = "continuity_error"


class PlaythroughNotFoundError(DomainError):
    """No playthrough run exists for the given `run_id`.

    Deliberately distinct from `StoryNotFoundError` (which names a missing story/series):
    a run id is an opaque handle into the playthrough repository, not a story identifier, and the
    two must map to the same 404 status without being the same concept.
    """

    code = "playthrough_not_found"


class NoIntentMatchError(DomainError):
    """The player's typed action did not confidently match any option currently on offer.

    A sibling of `PlaythroughNotFoundError` here — not beside `PlaythroughError` in
    `services/playthrough.py` — because this is not a turn-loop state-transition failure: no
    consequence was ever computed and the turn was never advanced. It exists so this outcome flows
    through the one `api/errors.py` handler and serialises as `{"error": {...}}` like every other
    error, instead of as a bare `HTTPException`'s `{"detail": {...}}` — a second, incompatible shape
    for the same 422 status. `options` (the offered labels) travels in `context` so a client can
    still re-prompt the player from the single error envelope.
    """

    code = "no_intent_match"

    def __init__(self, message: str, *, options: tuple[str, ...]) -> None:
        super().__init__(message, context={"options": list(options)})
        self.options = options


class RunCompleteError(DomainError):
    """The current turn offers no choices: the run has reached the end of its branches.

    Distinct from `NoIntentMatchError` — that one means the player's words didn't match any
    *offered* option; this one means there is nothing on offer at all, because the branch tree
    ended. `api/routers/play.py`'s `act` must check for this before ever calling
    `IntentRouter.resolve`, or an ended run's `/act` reads as an unmatched action rather than as
    the natural end of a playthrough.
    """

    code = "run_complete"


# --- generation / infrastructure -------------------------------------------------------------
class GenerationError(StoryEngineError):
    """An LLM generation failed or produced unusable output."""

    code = "generation_error"


class BudgetExceededError(GenerationError):
    code = "budget_exceeded"


class PromptError(StoryEngineError):
    """A prompt template was missing, malformed, or given the wrong variables."""

    code = "prompt_error"


# --- corpus harvesting -----------------------------------------------------------------------
class HarvestError(StoryEngineError):
    """Building a corpus from an external source failed."""

    code = "harvest_error"


class SourceUnavailableError(HarvestError):
    """A fan-fiction host was unreachable, rate-limited, or returned an unusable payload."""

    code = "source_unavailable"


class DocumentIngestionError(HarvestError):
    """A source document could not be read into citable chapters.

    Raised rather than degraded, because every downstream guarantee is chapter-addressed: a
    document that silently collapses to one chapter produces facts whose `chapter` is a lie, and
    the spoiler guard gates on exactly that field.
    """

    code = "document_ingestion_failed"


class CorpusReadError(HarvestError):
    """A previously-harvested corpus artifact is missing or malformed.

    Raised rather than degraded to an empty result: a `CorpusBranchOracle` that swallowed a bad
    read and returned `()` would be indistinguishable from a chapter fan fiction genuinely never
    wrote about, which is exactly the ambiguity `project_context.md` OD-4 warns against.
    """

    code = "corpus_read_failed"


# --- canon <-> vector ingest -------------------------------------------------------------------
class IngestDriftError(StoryEngineError):
    """Canon and the vector index disagree: one or more facts have no vector entry.

    Raised by `CanonIngestService.ingest` only after every fact in the batch was attempted —
    never mid-batch. Canon is the source of truth and a missing vector entry is a repairable
    degradation (semantic recall under-returns; the guard, the graph and every correctness
    property still hold) — never a reason to compensate by deleting the canon row. Repair with
    `CanonIngestService.reconcile`.
    """

    code = "ingest_drift"

    def __init__(
        self,
        message: str,
        *,
        orphan_fact_ids: tuple[str, ...],
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, context=context)
        self.orphan_fact_ids = orphan_fact_ids
