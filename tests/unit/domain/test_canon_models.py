"""Unit tests for the Canon Kernel schema (domain/models/canon.py)."""

from story_engine.domain.enums import (
    AssertionMode,
    CommitmentState,
    EntityStatus,
    FactStatus,
    PresenceGrade,
)


def test_kernel_enums_are_str_enums() -> None:
    """Kernel enums render as plain strings across the LLM/JSON boundary."""
    # StrEnum members ARE strings at runtime; mypy strict mode doesn't recognize this.
    assert AssertionMode.ATTRIBUTED == "attributed"  # type: ignore
    assert FactStatus.QUARANTINED == "quarantined"  # type: ignore
    assert EntityStatus.DEAD == "dead"  # type: ignore
    assert CommitmentState.PAID_OFF == "paid_off"  # type: ignore
    assert PresenceGrade.SILENT == "silent"  # type: ignore
