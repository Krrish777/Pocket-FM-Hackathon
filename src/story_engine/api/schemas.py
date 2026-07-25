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
