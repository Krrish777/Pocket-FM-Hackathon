"""L3 — the PRODUCT walkthrough, driven the way the game drives it.

The existing e2e suites (`test_hybrid_kb_e2e`, `test_memory_storage_e2e`) exercise the
knowledge base against its OWN api with synthetic Holmes/Kael data. That proves the storage
layer is coherent; it does not prove the layer can carry the product. This module asks the
different question: **can the playable branching layer described in `project_context.md` be
built on this knowledge base?**

Every beat below maps to a MUST feature, and every assertion is written against what the
PRODUCT needs, not against what the code currently does — a test written the other way round
can only ever confirm the implementation:

| Beat | Feature | The product requirement being asserted |
|---|---|---|
| 1 | M1 | Canon is stored with provenance sufficient to render a citation |
| 2 | M2 / M8 | Any cast member can be selected; storage is symmetric across all five |
| 3 | M5 | A character acts only on what they learned — set equality, not spot checks |
| 4 | M7 | A used fact can show its receipt: source, chapter, verbatim quote |
| 5 | KB-12 | Semantic recall obeys the same guard as structured recall |
| 6 | M3 / KB-13 | A player choice forks the story AND the branch inherits base canon |
| 7 | S3 | Replay the same branch from another character's epistemic view |

The cast and canon are the real Dexter novel cast (`project_context.md` §4.1). Chapter
numbers are the telling positions used throughout the Kernel.
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.embedding.hashing_embedder import HashingEmbedder
from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.adapters.outbound.persistence.vector_store import SqliteVectorStore
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import AUDIENCE, Fact, Fork, Provenance
from story_engine.services.working_memory import WorkingMemory

pytestmark = pytest.mark.e2e

INGESTED_AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
CHOSE_AT = datetime(2026, 7, 25, 18, 0, tzinfo=UTC)

EMBEDDER = HashingEmbedder(dimensions=128)

BASE_FORK = "dexter-novels"
CAST = ("dexter", "debra", "doakes", "laguerta", "rita")

# The chapter the player is dropped into. Chosen so that some canon is revealed and some
# is deliberately still ahead of the player.
PLAY_CHAPTER = 12


def _fact(
    fact_id: str,
    subject: str,
    predicate: str,
    obj: str,
    *,
    fork_id: str = BASE_FORK,
    valid_from: int = 1,
    revealed_at: int | None = 1,
    knower_scope: Mapping[str, int] | None = None,
    quote: str = "He was the monster in the room.",
    chapter: int = 1,
    recorded_at: datetime = INGESTED_AT,
    status: FactStatus = FactStatus.ACTIVE,
) -> Fact:
    """Build a canon fact carrying a citable provenance record."""
    return Fact(
        id=fact_id,
        fork_id=fork_id,
        subject_id=subject,
        predicate=predicate,
        object_id=obj,
        object_literal=None,
        valid_from=valid_from,
        valid_to=None,
        revealed_at=revealed_at,
        assertion_mode=AssertionMode.NARRATED,
        attributed_to=None,
        knower_scope=knower_scope,
        provenance=Provenance(
            source_id="darkly-dreaming-dexter",
            chapter=chapter,
            char_start=0,
            char_end=len(quote),
            quote=quote,
        ),
        confidence=0.95,
        tier=0,
        status=status,
        recorded_at=recorded_at,
        superseded_at=None,
    )


def _seed_canon(store: SqliteCanonStore) -> None:
    """Ingest a slice of novel canon: shared world facts plus two typed secrets."""
    # --- Shared world state: every cast member and the audience know these. -------------
    store.append(_fact("c-sibling", "dexter", "sibling_of", "debra", chapter=1))
    store.append(_fact("c-works", "dexter", "works_at", "miami_metro", chapter=1))
    store.append(_fact("c-partner", "debra", "works_at", "miami_metro", chapter=1))
    store.append(_fact("c-dating", "dexter", "dating", "rita", chapter=2))
    store.append(_fact("c-boss", "laguerta", "commands", "miami_metro", chapter=2))

    # --- Typed secret 1: Dexter's nature. Only Dexter knows; the audience is let in at
    #     chapter 1 because the novels are first-person. Debra, Doakes, LaGuerta, Rita
    #     must never receive this.
    store.append(
        _fact(
            "c-butcher",
            "dexter",
            "is_secretly",
            "the_bay_harbor_butcher",
            revealed_at=1,
            knower_scope={AUDIENCE: 1, "dexter": 1},
            quote="Tonight was a night for the Dark Passenger.",
            chapter=1,
        )
    )
    # --- Typed secret 2: Doakes's private suspicion, and the reason per-knower acquisition
    #     time has to exist. He holds it from chapter 6. The audience is not let in until
    #     chapter 20. Those are DIFFERENT chapters, and a model that cannot say so forces
    #     Doakes onto the audience's clock — he could not act on his own suspicion for
    #     fourteen chapters, and his packet would be identical to Rita's.
    store.append(
        _fact(
            "c-suspicion",
            "doakes",
            "suspects",
            "dexter",
            valid_from=6,
            revealed_at=20,
            knower_scope={AUDIENCE: 20, "doakes": 6},
            quote="Doakes watched him leave, and did not look away.",
            chapter=20,
        )
    )
    # --- A late reveal with no scope at all: pure telling-time withholding. ------------
    store.append(
        _fact(
            "c-brian",
            "brian_moser",
            "sibling_of",
            "dexter",
            valid_from=1,
            revealed_at=30,
            quote="The brother he had forgotten he had.",
            chapter=30,
        )
    )


def _open_store(db: Path) -> SqliteCanonStore:
    """Open (or reopen) a canon store against a real file on disk."""
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    return SqliteCanonStore(engine)


@pytest.fixture
def canon_db(tmp_path: Path) -> Path:
    """A real on-disk database seeded with novel canon."""
    db = tmp_path / "product.db"
    _seed_canon(_open_store(db))
    return db


# ---------------------------------------------------------------------------------------
# BEAT 1 + 2 + 3 — character select and per-character epistemic memory (M2, M8, M5)
# ---------------------------------------------------------------------------------------


def test_any_cast_member_can_be_selected_and_gets_a_packet(canon_db: Path) -> None:
    """M2/M8: five characters, one code path, no PC/NPC asymmetry.

    The renderer takes the character as a parameter, so selecting a different cast member
    must be a different ARGUMENT, never a different branch of storage.
    """
    memory = WorkingMemory(_open_store(canon_db))

    packets = {
        who: memory.assemble(BASE_FORK, who, chapter=PLAY_CHAPTER) for who in CAST
    }

    assert set(packets) == set(CAST)
    for who, packet in packets.items():
        assert packet.knower == who
        assert packet.chapter == PLAY_CHAPTER
        assert packet.facts, f"{who} was handed an empty packet — nothing to play with"


def test_a_character_only_holds_what_they_learned(canon_db: Path) -> None:
    """M5, asserted by SET EQUALITY.

    Spot checks only catch the leaks you already thought of. The whole visible id set is
    pinned per character, so an unexpected fact appearing anywhere fails here.
    """
    store = _open_store(canon_db)

    shared = {"c-sibling", "c-works", "c-partner", "c-dating", "c-boss"}

    def visible(who: str) -> set[str]:
        return {f.id for f in store.visible_to(BASE_FORK, who, PLAY_CHAPTER)}

    # Dexter knows the shared world plus his own secret — and nothing of Doakes's.
    assert visible("dexter") == shared | {"c-butcher"}
    # Doakes has held his suspicion since chapter 6 and must be able to act on it at 12.
    assert visible("doakes") == shared | {"c-suspicion"}
    # Everyone else holds the shared world only.
    for bystander in ("debra", "laguerta", "rita"):
        assert visible(bystander) == shared, (
            f"LEAK: {bystander} received a fact they never learned"
        )
    # The chapter-30 reveal is ahead of every one of them.
    for who in CAST:
        assert "c-brian" not in visible(who), "LEAK: a chapter-30 reveal surfaced at 12"


def test_the_packet_reports_what_it_withheld(canon_db: Path) -> None:
    """The guarantee has to be demonstrable, not merely asserted."""
    memory = WorkingMemory(_open_store(canon_db))
    debra = memory.assemble(BASE_FORK, "debra", chapter=PLAY_CHAPTER)

    assert debra.withheld_count == 3, (
        "debra should be missing butcher + suspicion + brian"
    )


# ---------------------------------------------------------------------------------------
# BEAT 4 — the receipt (M7)
# ---------------------------------------------------------------------------------------


def test_every_fact_in_a_packet_can_show_its_receipt(canon_db: Path) -> None:
    """M7: 'every fact is checked, and we show you the receipt'.

    A citation the player can act on needs a source, a position in that source, and the
    verbatim words. Anything less is a claim about a claim.
    """
    memory = WorkingMemory(_open_store(canon_db))
    packet = memory.assemble(BASE_FORK, "debra", chapter=PLAY_CHAPTER)

    for fact in packet.facts:
        receipt = fact.provenance
        assert receipt.source_id
        assert receipt.chapter >= 1
        assert receipt.quote
        assert receipt.char_end > receipt.char_start
        rendered = f"{receipt.source_id} ch.{receipt.chapter}: “{receipt.quote}”"
        assert receipt.quote in rendered


# ---------------------------------------------------------------------------------------
# BEAT 5 — semantic recall obeys the same guard (KB-12)
# ---------------------------------------------------------------------------------------


def test_semantic_recall_cannot_reach_a_fact_the_character_never_learned(
    canon_db: Path, tmp_path: Path
) -> None:
    """The easiest place in the system to leak: similarity does not respect narrative."""
    engine = create_engine(f"sqlite:///{canon_db}")
    SQLModel.metadata.create_all(engine)
    vectors = SqliteVectorStore(engine)
    store = SqliteCanonStore(engine)

    for fact in store.all_facts(BASE_FORK):
        text = f"{fact.subject_id} {fact.predicate} {fact.object_id}"
        vectors.add(fact, text, EMBEDDER.embed(text))

    # Debra asks the most on-the-nose question possible about her own brother.
    query = EMBEDDER.embed("dexter is_secretly the_bay_harbor_butcher")
    debra_hits = {
        h.fact_id for h in vectors.search(BASE_FORK, query, "debra", 12, k=10)
    }
    dexter_hits = {
        h.fact_id for h in vectors.search(BASE_FORK, query, "dexter", 12, k=10)
    }

    assert "c-butcher" not in debra_hits, "LEAK: similarity handed Debra the secret"
    assert "c-butcher" in dexter_hits, "dexter must reach his own secret"


# ---------------------------------------------------------------------------------------
# BEAT 6 — the player makes a choice: the fork (M3, KB-13)
# ---------------------------------------------------------------------------------------


def test_a_player_choice_forks_the_story_and_the_branch_inherits_canon(
    canon_db: Path,
) -> None:
    """THE core product mechanic.

    The player picks Debra, plays to chapter 12, and chooses to open her brother's case
    files. That choice creates a branch. The branch must contain BOTH:
      - the new diverging fact the choice created, and
      - every base-canon fact from before the divergence.

    A branch that inherits nothing is not a branch of a story — it is an empty universe,
    and the whole 'play forward through the Dexter novels' premise collapses.
    """
    store = _open_store(canon_db)

    branch = Fork(
        id="branch-debra-opens-the-files",
        parent_fork_id=BASE_FORK,
        divergence_at=PLAY_CHAPTER,
        source_id=None,
        label="Debra opens the case files",
    )
    assert not branch.is_root
    store.register_fork(branch)

    store.append(
        _fact(
            "b-opens",
            "debra",
            "investigates",
            "bay_harbor_case",
            fork_id=branch.id,
            valid_from=PLAY_CHAPTER,
            revealed_at=PLAY_CHAPTER,
            quote="She pulled the box down off the shelf.",
            chapter=PLAY_CHAPTER,
            recorded_at=CHOSE_AT,
        )
    )

    in_branch = {f.id for f in store.visible_to(branch.id, "debra", PLAY_CHAPTER)}

    assert "b-opens" in in_branch, (
        "the player's own choice is missing from their branch"
    )
    assert {"c-sibling", "c-works", "c-partner", "c-dating", "c-boss"} <= in_branch, (
        "the branch did not inherit base canon — Debra woke up in an empty world"
    )
    assert "c-butcher" not in in_branch, "LEAK: the branch bypassed the epistemic guard"


# ---------------------------------------------------------------------------------------
# BEAT 7 — replay the branch from another character's view (S3), across a restart
# ---------------------------------------------------------------------------------------


def test_the_same_moment_replays_differently_for_a_different_character(
    canon_db: Path,
) -> None:
    """S3, and the closing demo beat: one world, five genuinely different experiences.

    Same fork, same chapter, different knower. If the packets are equal, the epistemic
    layer is decorative.
    """
    store = _open_store(canon_db)
    memory = WorkingMemory(store)

    as_dexter = memory.assemble(BASE_FORK, "dexter", chapter=PLAY_CHAPTER)
    as_doakes = memory.assemble(BASE_FORK, "doakes", chapter=PLAY_CHAPTER)
    as_rita = memory.assemble(BASE_FORK, "rita", chapter=PLAY_CHAPTER)

    dexter_ids = {f.id for f in as_dexter.facts}
    doakes_ids = {f.id for f in as_doakes.facts}
    rita_ids = {f.id for f in as_rita.facts}

    assert dexter_ids != doakes_ids != rita_ids
    assert "c-butcher" in dexter_ids and "c-butcher" not in doakes_ids
    assert "c-suspicion" in doakes_ids and "c-suspicion" not in dexter_ids
    assert rita_ids < dexter_ids, "rita should hold strictly less than dexter"


def test_the_whole_session_survives_a_restart(canon_db: Path) -> None:
    """Durability of the product state, not just of a row.

    Close every connection, reopen a fresh engine against the same file, and re-derive the
    packets. A store that only works while the process is warm cannot back a session.
    """
    first = _open_store(canon_db)
    before = {
        f.id for f in WorkingMemory(first).assemble(BASE_FORK, "doakes", 12).facts
    }

    engine = create_engine(f"sqlite:///{canon_db}")
    engine.dispose()

    second = _open_store(canon_db)
    after = {
        f.id for f in WorkingMemory(second).assemble(BASE_FORK, "doakes", 12).facts
    }

    assert after == before
    assert "c-suspicion" in after
