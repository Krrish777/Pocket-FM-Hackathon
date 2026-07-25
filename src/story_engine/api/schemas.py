"""API DTOs — request/response schemas, kept SEPARATE from domain models.

The router maps DTO ⇄ domain explicitly so wire concerns (aliases, ORM loading) never leak into the
pure core. See research/pydantic-models-errors-logging.md.
"""

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Base for edge DTOs — forbids unknowns, accepts aliases, reads from attributes."""

    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, from_attributes=True
    )


class GenerateEpisodeRequest(ApiModel):
    series_id: str
    beat: str


class EpisodeResponse(ApiModel):
    number: int
    title: str
    body: str


# --- play (Task 5 — the minimum turn-loop API) ------------------------------------------------


class CharacterResponse(ApiModel):
    """One playable character, as offered by `GET /characters`."""

    id: str
    name: str


class ChoiceOptionResponse(ApiModel):
    """One offered option, deliberately built field-by-field.

    **Never** add `consequence` here. `ChoiceOption.consequence` describes what taking the option
    does to the world — serialising it would hand the client the future of the story, which is
    exactly what the epistemic-containment guarantee forbids. This DTO is constructed from named
    fields, never `ChoiceOption.model_dump()`, so a future field added to the domain model cannot
    silently leak through this response.
    """

    id: str
    label: str
    source_work_id: str | None = None


class CitationResponse(ApiModel):
    """One receipt line: a checked claim and where in the source it came from."""

    fact_id: str
    source_id: str
    chapter: int
    quote: str


class TurnResponse(ApiModel):
    """One rendered beat of a playthrough, from one character's point of view."""

    index: int
    chapter: int
    protagonist: str
    scene: str
    choices: list[ChoiceOptionResponse]
    citations: list[CitationResponse]
    withheld_count: int


class ReactionResponse(ApiModel):
    """A derived per-character directive — computed at render time, never stored."""

    name: str
    tension: int
    blind_spots: list[str]


class PlayRequest(ApiModel):
    character_id: str


class PlayResponse(ApiModel):
    run_id: str
    turn: TurnResponse


class ActRequest(ApiModel):
    action: str


class ActResponse(ApiModel):
    run_id: str
    turn: TurnResponse
    interpreted_as: str
    reactions: list[ReactionResponse]


class ReplayAsRequest(ApiModel):
    character_id: str


class ReplayResponse(ApiModel):
    run_id: str
    turns: list[TurnResponse]
