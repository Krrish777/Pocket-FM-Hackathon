"""Story + Episode aggregates.

STARTER models — refine field shapes to the hackathon brief. They demonstrate the conventions:
`DomainModel` base, `Field` constraints, `field_validator`/`model_validator`, `computed_field`.
"""

from pydantic import Field, computed_field, field_validator, model_validator

from story_engine.domain.base import DomainModel
from story_engine.domain.enums import EpisodeStatus, Genre


class Episode(DomainModel):
    """A single episode of a serialized story."""

    number: int = Field(ge=1, description="1-based episode index within the series.")
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(
        default="", description="The episode prose (may be empty while drafting)."
    )
    status: EpisodeStatus = EpisodeStatus.DRAFT

    @field_validator("title")
    @classmethod
    def _title_not_placeholder(cls, value: str) -> str:
        if value.strip().lower() in {"tbd", "todo"}:
            raise ValueError("title must not be a placeholder")
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def word_count(self) -> int:
        """Number of whitespace-separated words in the body."""
        return len(self.body.split())


class Story(DomainModel):
    """A serialized story and its ordered episodes."""

    id: str
    title: str = Field(min_length=1, max_length=200)
    genre: Genre
    premise: str = ""
    episodes: tuple[Episode, ...] = ()

    @model_validator(mode="after")
    def _episodes_contiguous(self) -> "Story":
        numbers = [e.number for e in self.episodes]
        if numbers and numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("episode numbers must be contiguous starting at 1")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_words(self) -> int:
        return sum(e.word_count for e in self.episodes)
