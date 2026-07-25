"""L3 — full-novel-shaped ingest, through `CanonIngestService`, proven across all three lanes.

`story-engine ingest` (`cli/ingest.py`) is the CLI wrapper; these tests exercise the same pure
functions it calls (`build_facts_from_novel`, `build_ingest_service`) directly, against a real
multi-chapter PDF (not a fixture string — same discipline as `test_ingestion_citation_e2e.py`).

Scope actually exercised here: a SYNTHETIC 3-chapter novel, not the real
`Darkly-Dreaming-Dexter-1.pdf`. Ingesting the real book end to end is what `story-engine ingest`
is FOR and it has no artificial cap, but a full novel is slow to chunk/embed/assert on every test
run, so these tests bound the slice the same way the brief allows. Do not read "passes" here as
"the whole novel was ingested" — see `task-7-report.md` for the exact chapter range and fact
count this suite exercises versus what the CLI is capable of on the real book.
"""

from datetime import UTC, datetime
from pathlib import Path

import pymupdf
import pytest
from sqlmodel import create_engine

from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.adapters.outbound.persistence.vector_store import SqliteVectorStore
from story_engine.cli.ingest import build_facts_from_novel, build_ingest_service
from story_engine.domain.graph import LoreGraph
from story_engine.domain.models import Fact
from story_engine.services.canon_ingest import CanonIngestService

pytestmark = pytest.mark.e2e

SOURCE_ID = "test-dexter-novel"
FORK_ID = "canon"
INGESTED_AT = datetime(2026, 7, 26, 9, 0, tzinfo=UTC)

# Chapter 1 mentions only Dexter, chapter 2 introduces Deborah, chapter 3 introduces Doakes —
# each cast member's FIRST appearance lands in a different, later chapter, so a fact about a
# later-appearing character is a genuine "not yet revealed" case, not a fixture artifact.
_CHAPTERS = [
    "Chapter 1: Night Work\n"
    "Dexter kept the slides in a rosewood box beneath the air conditioner. He counted them "
    "twice before the sun came up, and the Passenger counted with him. Nobody in the "
    "department had ever asked what was in the box, and Dexter intended to keep it that way "
    "for as long as the city let him.",
    "Chapter 2: Deborah\n"
    "Deborah asked about the harbour again over breakfast, chewing through a bagel like it "
    "owed her money. She did not know about the box, and Dexter intended to keep it that way. "
    "She talked instead about the case files that would not close, and about a partner who "
    "would not return her calls.",
    "Chapter 3: Doakes\n"
    "Doakes watched from the far side of the parking lot and said nothing at all, the way he "
    "always did when he was working something out. He had begun to suspect what Deborah still "
    "could not see, and he meant to prove it before anyone stopped him.",
]


def _write_novel(path: Path) -> Path:
    """Render `_CHAPTERS` into a genuine multi-page PDF, one chapter per page."""
    document = pymupdf.open()
    for body in _CHAPTERS:
        page = document.new_page()
        page.insert_text((72, 72), body, fontsize=11)
    document.save(path)
    document.close()
    return path


def _ingest(
    tmp_path: Path,
) -> tuple[Path, list[Fact], CanonIngestService, SqliteCanonStore, SqliteVectorStore]:
    """Write the synthetic novel, chunk it, and ingest it through the real write path."""
    novel = _write_novel(tmp_path / "novel.pdf")
    db = tmp_path / "canon.db"

    facts = build_facts_from_novel(
        novel,
        source_id=SOURCE_ID,
        fork_id=FORK_ID,
        chunk_size=200,
        overlap=50,
        recorded_at=INGESTED_AT,
    )
    assert facts, "ingestion produced no facts at all"

    service, store, vectors = build_ingest_service(db)
    written = service.ingest(facts)
    assert written == len(facts)
    return db, facts, service, store, vectors


def test_canon_and_vector_counts_match_after_ingest(tmp_path: Path) -> None:
    """Invariant: every fact ingested to canon has exactly one matching vector entry.

    Proves `CanonIngestService.ingest`'s canon-first/vector-second contract left the two
    lanes in sync for a real (if small) multi-chapter ingest, not just for a single fact.
    """
    _db, facts, _service, store, vectors = _ingest(tmp_path)

    canon_ids = {f.id for f in store.all_facts(FORK_ID)}
    vector_ids = vectors.ids(FORK_ID)

    assert canon_ids == {f.id for f in facts}
    assert vector_ids == canon_ids, (
        "canon and vector lanes diverged: "
        f"canon-only={canon_ids - vector_ids} vector-only={vector_ids - canon_ids}"
    )
    assert len(store.all_facts(FORK_ID)) == len(vectors.ids(FORK_ID))


def test_graph_projection_builds_from_canon_without_error(tmp_path: Path) -> None:
    """Invariant: the graph projection builds from ingested canon, at every ingested chapter.

    `appears_in` facts are the only ones ingested with an `object_id` (narration-span facts
    carry only `object_literal`, which `LoreGraph.from_facts` correctly excludes — see
    `cli/ingest.py`'s module docstring), so this also proves the graph gets real edges out
    of a real ingest rather than trivially building an empty one.
    """
    _db, facts, _service, store, _vectors = _ingest(tmp_path)
    all_facts = store.all_facts(FORK_ID)

    max_chapter = max(f.provenance.chapter for f in facts)
    for chapter in range(1, max_chapter + 1):
        graph = LoreGraph.from_facts(all_facts, knower="dexter", chapter=chapter)
        # Must not raise, and by chapter 3 (Dexter's own appearance is revealed at chapter 1)
        # there must be at least one real edge to prove the graph is not vacuously empty.
        if chapter >= 1:
            assert isinstance(graph, LoreGraph)
    graph_at_end = LoreGraph.from_facts(all_facts, knower="dexter", chapter=max_chapter)
    assert graph_at_end.edges, (
        "the graph projection produced no edges at all from a real ingest"
    )


def test_restart_preserves_counts_and_visibility(tmp_path: Path) -> None:
    """Restart proof: close the engine, reopen a FRESH one against the same file, and confirm
    counts and per-knower visibility are IDENTICAL to before closing.

    Never `:memory:` — a real file lets the engine be disposed and a brand-new engine opened
    against the same path, so this proves durability rather than warm-process behaviour.
    """
    db, facts, _service, store, vectors = _ingest(tmp_path)

    before_canon_count = len(store.all_facts(FORK_ID))
    before_vector_count = len(vectors.ids(FORK_ID))
    max_chapter = max(f.provenance.chapter for f in facts)
    before_visible = {
        chapter: {f.id for f in store.visible_to(FORK_ID, "dexter", chapter)}
        for chapter in range(1, max_chapter + 1)
    }

    # --- RESTART: dispose the underlying engine, then build fresh store/vector instances -----
    store._engine.dispose()
    reopened_engine = create_engine(f"sqlite:///{db}")
    reopened_store = SqliteCanonStore(reopened_engine)
    reopened_vectors = SqliteVectorStore(reopened_engine)

    after_canon_count = len(reopened_store.all_facts(FORK_ID))
    after_vector_count = len(reopened_vectors.ids(FORK_ID))
    after_visible = {
        chapter: {f.id for f in reopened_store.visible_to(FORK_ID, "dexter", chapter)}
        for chapter in range(1, max_chapter + 1)
    }

    assert after_canon_count == before_canon_count == len(facts)
    assert after_vector_count == before_vector_count == len(facts)
    assert after_visible == before_visible, (
        "per-chapter visibility changed across a restart — the guard must be as durable as "
        "the data it gates"
    )


def test_guard_gates_by_chapter_in_all_three_lanes(tmp_path: Path) -> None:
    """THE regression test: a fact from a later chapter must be absent from ALL THREE lanes
    at an earlier point in the telling — store, vector search, and the graph projection.

    Doakes's `appears_in` fact is `revealed_at=3` (his first appearance in the synthetic
    novel). Queried as of chapter 1, it must not surface anywhere: not in the canon store's
    `visible_to`, not in a vector search over the SAME text (a verbatim query, since
    `HashingEmbedder` only recalls reliably on near-exact text — see its docstring), and not
    as a graph edge. This asserts the architecture already holds it, per the task brief — it
    is a regression guard, not a fix.
    """
    _db, facts, service, store, vectors = _ingest(tmp_path)

    doakes_fact = next(
        f for f in facts if f.subject_id == "doakes" and f.predicate == "appears_in"
    )
    assert doakes_fact.provenance.chapter == 3
    assert doakes_fact.revealed_at == 3

    early_chapter = 1

    # --- LANE 1: canon store -------------------------------------------------------------
    early_visible_ids = {
        f.id for f in store.visible_to(FORK_ID, "dexter", early_chapter)
    }
    assert doakes_fact.id not in early_visible_ids, (
        "LEAK: canon store surfaced it early"
    )
    late_visible_ids = {
        f.id for f in store.visible_to(FORK_ID, "dexter", doakes_fact.revealed_at)
    }
    assert doakes_fact.id in late_visible_ids, (
        "positive control failed: the fact should be visible once its own chapter is told"
    )

    # --- LANE 2: vector search, verbatim query -------------------------------------------
    query_vector = service._embedder.embed(doakes_fact.provenance.quote)
    early_hits = vectors.search(
        FORK_ID, query_vector, knower="dexter", chapter=early_chapter, k=len(facts)
    )
    assert doakes_fact.id not in {hit.fact_id for hit in early_hits}, (
        "LEAK: vector search surfaced it early"
    )
    late_hits = vectors.search(
        FORK_ID,
        query_vector,
        knower="dexter",
        chapter=doakes_fact.revealed_at,
        k=len(facts),
    )
    assert doakes_fact.id in {hit.fact_id for hit in late_hits}, (
        "positive control failed: a verbatim query should retrieve its own source fact once "
        "revealed"
    )

    # --- LANE 3: graph projection ---------------------------------------------------------
    all_facts = store.all_facts(FORK_ID)
    early_graph = LoreGraph.from_facts(
        all_facts, knower="dexter", chapter=early_chapter
    )
    assert doakes_fact.id not in {e.fact_id for e in early_graph.edges}, (
        "LEAK: the graph projection exposed it early"
    )
    assert not any(
        e.fact_id == doakes_fact.id for e in early_graph.neighbours("doakes")
    ), "LEAK: doakes's early-chapter neighbours include the withheld fact"

    late_graph = LoreGraph.from_facts(
        all_facts, knower="dexter", chapter=doakes_fact.revealed_at
    )
    assert doakes_fact.id in {e.fact_id for e in late_graph.edges}, (
        "positive control failed: the fact should be a graph edge once its own chapter is told"
    )
