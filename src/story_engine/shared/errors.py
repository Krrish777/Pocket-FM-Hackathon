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
