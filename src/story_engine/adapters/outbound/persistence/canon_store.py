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
from story_engine.adapters.outbound.persistence.tables import FactRow, ForkRow
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import Awareness, ChapterIndex, Fact, Fork, Provenance


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
        # The model already normalises order, so the stored JSON is stable across
        # writes of an equal fact.
        knower_scope=(
            None
            if fact.knower_scope is None
            else [
                {"knower": a.knower, "learned_at": a.learned_at}
                for a in fact.knower_scope
            ]
        ),
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
            None
            if row.knower_scope is None
            else tuple(Awareness.model_validate(entry) for entry in row.knower_scope)
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

    def register_fork(self, fork: Fork) -> None:
        """Record a branch and what it descends from. Re-registering replaces."""
        with session_scope(self._engine) as session:
            existing = session.get(ForkRow, fork.id)
            if existing is not None:
                session.delete(existing)
                session.flush()
            session.add(
                ForkRow(
                    id=fork.id,
                    parent_fork_id=fork.parent_fork_id,
                    divergence_at=fork.divergence_at,
                    source_id=fork.source_id,
                    label=fork.label,
                )
            )

    def get_fork(self, fork_id: str) -> Fork | None:
        """Return one registered fork by id, or None."""
        with session_scope(self._engine) as session:
            row = session.get(ForkRow, fork_id)
            if row is None:
                return None
            return Fork(
                id=row.id,
                parent_fork_id=row.parent_fork_id,
                divergence_at=row.divergence_at,
                source_id=row.source_id,
                label=row.label,
            )

    def lineage(self, fork_id: str) -> tuple[tuple[str, ChapterIndex | None], ...]:
        """Walk fork → parent → … → root, pairing each with its inherited story-time cap.

        The cap is the tightest divergence point seen so far on the walk, not the local
        one: a grandchild that branched at chapter 40 from a child that branched at 12
        inherits the grandparent only up to 12, because everything after 12 in the
        grandparent was already replaced by the child's version of events.

        An UNREGISTERED fork is treated as a root. That keeps a bare `fork_id` working
        exactly as it did before branches existed, so callers that never register anything
        see no behaviour change.

        Raises:
            ValueError: the parent chain contains a cycle — an unguarded walk would hang.
        """
        chain: list[tuple[str, ChapterIndex | None]] = []
        seen: set[str] = set()
        current: str | None = fork_id
        cap: ChapterIndex | None = None
        while current is not None:
            if current in seen:
                raise ValueError(f"fork lineage contains a cycle at: {current}")
            seen.add(current)
            chain.append((current, cap))
            fork = self.get_fork(current)
            if fork is None or fork.parent_fork_id is None:
                break
            divergence = fork.divergence_at
            cap = divergence if cap is None else min(cap, divergence or cap)
            current = fork.parent_fork_id
        return tuple(chain)

    def all_facts(self, fork_id: str) -> tuple[Fact, ...]:
        """Every fact visible in a fork, nearest ancestor first, in record order.

        Resolution walks the lineage: the fork's own facts, then each ancestor's facts that
        predate the divergence, with a nearer fork SHADOWING an ancestor on the same
        (subject_id, predicate). Shadowing is what makes a branch a rewrite rather than a
        contradiction — "Debra opened the files" must replace the canon version of that
        beat, not sit beside it and trip the conflict detector.

        Ordered by (recorded_at, id): `recorded_at` alone is not a total order, and bulk
        ingest routinely stamps many facts with one timestamp, which left the tie order to
        SQLite and made every downstream "deterministic" guarantee conditional.
        """
        collected: list[Fact] = []
        shadowed: set[tuple[str, str]] = set()
        for ancestor_id, cap in self.lineage(fork_id):
            with session_scope(self._engine) as session:
                statement = (
                    select(FactRow)
                    .where(col(FactRow.fork_id) == ancestor_id)
                    .order_by(col(FactRow.recorded_at).asc(), col(FactRow.id).asc())
                )
                rows = [_to_domain(row) for row in session.exec(statement).all()]
            inherited = [
                fact
                for fact in rows
                if (cap is None or fact.valid_from <= cap)
                and (fact.subject_id, fact.predicate) not in shadowed
            ]
            collected.extend(inherited)
            # Shadow on what THIS fork actually declares, not on what it inherited, so a
            # key only stops resolving to an ancestor when a nearer fork overrides it.
            shadowed.update((fact.subject_id, fact.predicate) for fact in rows)
        return tuple(collected)

    def as_of(
        self,
        fork_id: str,
        subject_id: str,
        predicate: str,
        story_time: ChapterIndex,
    ) -> Fact | None:
        """The fact whose story-time window contains `story_time`.

        Resolves across the fork's lineage, so a branch answers with inherited canon where
        it has not overridden it.

        Includes INVALIDATED rows: a superseded fact is still canon at its own past
        story-time (I-4 says supersession is append-only, not a rewrite of history) — only
        the closed `valid_to` on the old row and the open one on the new row disambiguate
        which is live "now". QUARANTINED facts never reach retrieval, so they alone are
        excluded here.

        The winner is chosen by a TOTAL order — live-before-retired, then latest
        `valid_from`, then latest `recorded_at`, then id. Ordering on `valid_from` alone is
        not total: two rows sharing a `valid_from` left the choice to SQLite's row order,
        so an INVALIDATED row could beat the ACTIVE one that replaced it.
        """
        candidates = [
            fact
            for fact in self.all_facts(fork_id)
            if fact.subject_id == subject_id
            and fact.predicate == predicate
            and fact.status is not FactStatus.QUARANTINED
            and fact.is_valid_at(story_time)
        ]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda f: (
                f.status is not FactStatus.INVALIDATED,
                f.valid_from,
                f.recorded_at,
                f.id,
            ),
        )

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

        The closed row is rebuilt as a `Fact` and re-validated BEFORE it is written. This
        path mutates row attributes directly, which skips every model validator — so
        without the round-trip a `closes_at` earlier than `valid_from` wrote happily and
        then raised `ValidationError` on every subsequent read of that fork, permanently,
        with no delete path to repair it. Validation must be symmetric: what cannot be read
        must not be writable.

        Raises:
            KeyError: `old_fact_id` does not exist — a silent no-op here would lose the
                replacement fact entirely.
            ValueError: the target is already superseded (I-2/I-8: a second supersession
                would leave two live successors), the replacement is not in the same fork,
                or the closed row would violate a domain invariant.
        """
        with session_scope(self._engine) as session:
            row = session.get(FactRow, old_fact_id)
            if row is None:
                raise KeyError(f"cannot supersede unknown fact: {old_fact_id}")

            current = _to_domain(row)
            if current.status is not FactStatus.ACTIVE:
                raise ValueError(
                    f"cannot supersede {old_fact_id}: it is already "
                    f"{current.status}. Supersede its live successor instead — closing a "
                    "retired fact a second time leaves two live successors for one key."
                )
            if replacement.id == old_fact_id:
                raise ValueError("a fact cannot supersede itself")
            if replacement.fork_id != current.fork_id:
                raise ValueError(
                    f"replacement is in fork {replacement.fork_id!r} but the superseded "
                    f"fact is in {current.fork_id!r} — supersession is fork-local"
                )

            # Re-validate through the domain before touching the row.
            closed = current.model_copy(
                update={
                    "valid_to": closes_at,
                    "superseded_at": superseded_at,
                    "status": FactStatus.INVALIDATED,
                }
            )
            Fact.model_validate(closed.model_dump())

            row.valid_to = closed.valid_to
            # Explicit isoformat, same as _to_row — never hand a bare datetime to the sqlite3
            # driver's deprecated implicit adapter (it happens to work, but silently).
            row.superseded_at = superseded_at.isoformat()
            row.status = str(FactStatus.INVALIDATED)
            session.add(row)
            session.add(_to_row(replacement))
