"""Shared base for all domain models.

Centralizes Pydantic config so every entity/value object is immutable, strict, and self-validating.
Domain models never carry API concerns (aliases, ORM loading) — those live on a separate DTO base in
the API adapter. See .claude/rules/python-design.md.
"""

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Immutable, strict base for domain entities and value objects."""

    model_config = ConfigDict(
        frozen=True,  # immutable + hashable value objects
        extra="forbid",  # reject unknown fields — crisp contracts
        str_strip_whitespace=True,
        validate_assignment=True,
        validate_default=True,
    )
