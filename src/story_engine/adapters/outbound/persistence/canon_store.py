"""SQLite-backed canon store — implements `CanonStorePort`.

The Kernel's system of record. Facts are NEVER overwritten: a superseding claim closes the
old row's validity window and stamps `superseded_at`, and both rows stay queryable, because
the superseded fact is still canon at its own timestamp.

Maps Row ⇄ domain explicitly and always INSIDE the session scope — rows detach on close
(the HARDEN-01 `DetachedInstanceError`).
"""

from datetime import datetime

from sqlalchemy import Engine
from sqlmodel import col, select

from story_engine.adapters.outbound.persistence.db import session_scope
from story_engine.adapters.outbound.persistence.tables import FactRow
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import ChapterIndex, Fact, Provenance


def _to_row(fact: Fact) -> FactRow:
    """Map a domain fact to a fresh storage row."""
    return FactRow(
        id=fact.id,
        fork_id=fact.fork_id,
        subject_id=fact.subject_id,
        predicate=fact.predicate,
        object_id=fact.object_id,
        object_literal=fact.object_literal,
        valid_from=fact.valid_from,
        valid_to=fact.valid_to,
        revealed_at=fact.revealed_at,
        assertion_mode=str(fact.assertion_mode),
        attributed_to=fact.attributed_to,
        # None (untracked) must stay NULL — an empty list would be a different, invalid state.
        knower_scope=(None if fact.knower_scope is None else sorted(fact.knower_scope)),
        provenance=fact.provenance.model_dump(),
        confidence=fact.confidence,
        tier=fact.tier,
        status=str(fact.status),
        # ISO-8601 text preserves tzinfo; a native SQLite DateTime column would not.
        recorded_at=fact.recorded_at.isoformat(),
        superseded_at=(
            None if fact.superseded_at is None else fact.superseded_at.isoformat()
        ),
    )


def _to_domain(row: FactRow) -> Fact:
    """Map a storage row back to the pure domain model."""
    return Fact(
        id=row.id,
        fork_id=row.fork_id,
        subject_id=row.subject_id,
        predicate=row.predicate,
        object_id=row.object_id,
        object_literal=row.object_literal,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        revealed_at=row.revealed_at,
        assertion_mode=AssertionMode(row.assertion_mode),
        attributed_to=row.attributed_to,
        knower_scope=(
            None if row.knower_scope is None else frozenset(row.knower_scope)
        ),
        # model_validate (not **row.provenance): the JSON column is typed dict[str, object]
        # for storage generality, but Provenance's fields are concretely typed — validate
        # rather than unpack so strict mypy doesn't see a dict[str, object] splatted onto
        # str/int-typed parameters.
        provenance=Provenance.model_validate(row.provenance),
        confidence=row.confidence,
        tier=row.tier,
        status=FactStatus(row.status),
        recorded_at=datetime.fromisoformat(row.recorded_at),
        superseded_at=(
            None
            if row.superseded_at is None
            else datetime.fromisoformat(row.superseded_at)
        ),
    )


class SqliteCanonStore:
    """SQLite implementation of `CanonStorePort`.

    Every read maps Row → domain INSIDE the session scope, then returns pure models, so no
    caller can trip `DetachedInstanceError` on a lazily-loaded attribute.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def append(self, fact: Fact) -> None:
        """Store a fact. Never overwrites — supersession closes windows instead."""
        with session_scope(self._engine) as session:
            session.add(_to_row(fact))

    def get(self, fact_id: str) -> Fact | None:
        """Return one fact by id, or None."""
        with session_scope(self._engine) as session:
            row = session.get(FactRow, fact_id)
            return _to_domain(row) if row is not None else None

    def all_facts(self, fork_id: str) -> tuple[Fact, ...]:
        """Every fact in a fork, in record order."""
        with session_scope(self._engine) as session:
            statement = (
                select(FactRow)
                .where(col(FactRow.fork_id) == fork_id)
                .order_by(col(FactRow.recorded_at).asc())
            )
            return tuple(_to_domain(row) for row in session.exec(statement).all())

    def as_of(
        self,
        fork_id: str,
        subject_id: str,
        predicate: str,
        story_time: ChapterIndex,
    ) -> Fact | None:
        """The fact whose story-time window contains `story_time`.

        Includes INVALIDATED rows: a superseded fact is still canon at its own past
        story-time (I-4 says supersession is append-only, not a rewrite of history) — only
        the closed `valid_to` on the old row and the open one on the new row disambiguate
        which is live "now". QUARANTINED facts never reach retrieval, so they alone are
        excluded here.
        """
        with session_scope(self._engine) as session:
            statement = (
                select(FactRow)
                .where(col(FactRow.fork_id) == fork_id)
                .where(col(FactRow.subject_id) == subject_id)
                .where(col(FactRow.predicate) == predicate)
                .where(col(FactRow.status) != str(FactStatus.QUARANTINED))
                .where(col(FactRow.valid_from) <= story_time)
                .order_by(col(FactRow.valid_from).desc())
            )
            for row in session.exec(statement).all():
                if row.valid_to is None or story_time <= row.valid_to:
                    return _to_domain(row)
            return None

    def visible_to(
        self, fork_id: str, knower: str, chapter: ChapterIndex
    ) -> tuple[Fact, ...]:
        """Facts that may be surfaced to this knower at this point in the telling."""
        return tuple(
            f for f in self.all_facts(fork_id) if f.is_visible_to(knower, chapter)
        )

    def withheld_from(
        self, fork_id: str, knower: str, chapter: ChapterIndex
    ) -> tuple[Fact, ...]:
        """The spoiler-guard exclusion set — retrieval performed in order to EXCLUDE."""
        return tuple(
            f for f in self.all_facts(fork_id) if not f.is_visible_to(knower, chapter)
        )

    def supersede(
        self,
        old_fact_id: str,
        replacement: Fact,
        closes_at: ChapterIndex,
        superseded_at: datetime,
    ) -> None:
        """Close the old row's window and insert the replacement in ONE transaction.

        Both writes share a session so there is no window in which both rows are live, and
        none in which neither is (invariant I-3).

        Raises:
            KeyError: `old_fact_id` does not exist — a silent no-op here would lose the
                replacement fact entirely.
        """
        with session_scope(self._engine) as session:
            row = session.get(FactRow, old_fact_id)
            if row is None:
                raise KeyError(f"cannot supersede unknown fact: {old_fact_id}")
            row.valid_to = closes_at
            # Explicit isoformat, same as _to_row — never hand a bare datetime to the sqlite3
            # driver's deprecated implicit adapter (it happens to work, but silently).
            row.superseded_at = superseded_at.isoformat()
            row.status = str(FactStatus.INVALIDATED)
            session.add(row)
            session.add(_to_row(replacement))
