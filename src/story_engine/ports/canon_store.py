"""The canon-store port — the only seam the services see for tri-temporal fact storage."""

from datetime import datetime
from typing import Protocol

from story_engine.domain.models import ChapterIndex, Fact


class CanonStorePort(Protocol):
    """Append-only, tri-temporally queryable storage for canon facts."""

    def append(self, fact: Fact) -> None:
        """Store a fact. Never overwrites an existing one."""
        ...

    def get(self, fact_id: str) -> Fact | None:
        """Return one fact by id, or None."""
        ...

    def all_facts(self, fork_id: str) -> tuple[Fact, ...]:
        """Every fact in a fork, in record order."""
        ...

    def as_of(
        self,
        fork_id: str,
        subject_id: str,
        predicate: str,
        story_time: ChapterIndex,
    ) -> Fact | None:
        """The fact true at a story-time position, or None."""
        ...

    def visible_to(
        self, fork_id: str, knower: str, chapter: ChapterIndex
    ) -> tuple[Fact, ...]:
        """Facts that may be surfaced to this knower at this point in the telling."""
        ...

    def withheld_from(
        self, fork_id: str, knower: str, chapter: ChapterIndex
    ) -> tuple[Fact, ...]:
        """The spoiler-guard exclusion set — retrieval performed in order to EXCLUDE."""
        ...

    def supersede(
        self,
        old_fact_id: str,
        replacement: Fact,
        closes_at: ChapterIndex,
        superseded_at: datetime,
    ) -> None:
        """Close the old fact's window and append its replacement, atomically.

        Never deletes: the superseded fact remains canon at its own timestamp.
        `superseded_at` is supplied by the caller because the domain and its ports take no
        clock.

        Raises:
            KeyError: `old_fact_id` does not exist — a silent no-op here would lose the
                replacement fact entirely.
        """
        ...
