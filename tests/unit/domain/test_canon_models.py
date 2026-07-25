"""Unit tests for the Canon Kernel schema (domain/models/canon.py)."""

import pytest
from pydantic import ValidationError

from story_engine.domain.enums import (
    AssertionMode,
    CommitmentState,
    EntityStatus,
    FactStatus,
    PresenceGrade,
    SourceType,
)
from story_engine.domain.models.canon import Fork, Provenance, Source


def test_kernel_enums_are_str_enums() -> None:
    """Kernel enums render as plain strings across the LLM/JSON boundary."""
    # StrEnum members ARE strings at runtime; mypy strict mode doesn't recognize this.
    assert AssertionMode.ATTRIBUTED == "attributed"  # type: ignore
    assert FactStatus.QUARANTINED == "quarantined"  # type: ignore
    assert EntityStatus.DEAD == "dead"  # type: ignore
    assert CommitmentState.PAID_OFF == "paid_off"  # type: ignore
    assert PresenceGrade.SILENT == "silent"  # type: ignore


def test_provenance_requires_a_forward_span() -> None:
    """char_end must come after char_start — a zero-width span cites nothing."""
    with pytest.raises(ValidationError):
        Provenance(
            source_id="src-1", chapter=3, char_start=100, char_end=100, quote="x"
        )


def test_provenance_accepts_a_valid_span() -> None:
    """Accept a valid character span."""
    prov = Provenance(
        source_id="src-1",
        chapter=3,
        char_start=100,
        char_end=118,
        quote="the vault was empty",
    )
    assert prov.chapter == 3


def test_root_fork_has_no_parent_and_no_divergence() -> None:
    """Root forks are base canon without a parent or divergence point."""
    root = Fork(
        id="canon",
        parent_fork_id=None,
        divergence_at=None,
        source_id="src-1",
        label="base novel",
    )
    assert root.is_root is True


def test_non_root_fork_must_declare_a_divergence_point() -> None:
    """A branch without a divergence point cannot be resolved against its parent."""
    with pytest.raises(ValidationError):
        Fork(
            id="fork-a",
            parent_fork_id="canon",
            divergence_at=None,
            source_id="src-2",
            label="what if Kael never defects",
        )


def test_root_fork_may_not_declare_a_divergence_point() -> None:
    """Root forks cannot declare a divergence point."""
    with pytest.raises(ValidationError):
        Fork(
            id="canon",
            parent_fork_id=None,
            divergence_at=12,
            source_id="src-1",
            label="base novel",
        )


def test_source_carries_an_authority_tier() -> None:
    """Sources have an authority tier for conflict resolution."""
    source = Source(
        id="src-2",
        type=SourceType.FANFIC,
        tier=2,
        title="A Study in Anything",
        url=None,
        license_note=None,
    )
    assert source.tier == 2
