"""The canon-store port — the only seam the services see for tri-temporal fact storage."""

from datetime import datetime
from typing import Protocol

from story_engine.domain.models import Awareness, ChapterIndex, Fact, Fork


class CanonStorePort(Protocol):
    """Append-only, tri-temporally queryable storage for canon facts."""

    def append(self, fact: Fact) -> None:
        """Store a fact. Never overwrites an existing one."""
        ...

    def get(self, fact_id: str) -> Fact | None:
        """Return one fact by id, or None."""
        ...

    def register_fork(self, fork: Fork) -> None:
        """Record a branch and what it descends from. Re-registering replaces."""
        ...

    def get_fork(self, fork_id: str) -> Fork | None:
        """Return one registered fork by id, or None."""
        ...

    def lineage(self, fork_id: str) -> tuple[tuple[str, ChapterIndex | None], ...]:
        """Walk fork → parent → … → root, pairing each with its inherited story-time cap.

        An unregistered fork resolves as a root, so a bare `fork_id` keeps working exactly
        as it did before branches existed.
        """
        ...

    def all_facts(self, fork_id: str) -> tuple[Fact, ...]:
        """Every fact visible in a fork — its own plus inherited ancestor canon.

        Ancestor facts that predate the divergence are included; a nearer fork shadows an
        ancestor on the same (subject_id, predicate). Ordered by (recorded_at, id), a
        TOTAL order, so assembly downstream is genuinely deterministic.
        """
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

    def record_learning(
        self, fact_id: str, knower_scope: tuple[Awareness, ...]
    ) -> None:
        """Amend who knows a fact, without touching the claim itself.

        Learning is not a claim change: the fact stays exactly as true as it was, and only the
        set of people who know it grows. Routing it through `supersede` would close a validity
        window that nothing invalidated and litter the history with phantom corrections.

        Implementations MUST reject a non-monotonic scope — one that drops a knower or delays an
        existing acquisition — so the invariant holds no matter which caller is wrong. See
        `domain.propagation`.

        Raises:
            KeyError: `fact_id` does not exist.
            ValueError: The fact is untracked (a scope would narrow visibility rather than widen
                it), or the new scope is not monotonic over the stored one.
        """
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
