# Research: Memory & State Persistence for an LLM Serialized-Storytelling Engine

> **Provenance:** Web research by a `general-purpose` sub-agent. Raw cited artifact; the memory subsystem
> scaffold is built from the "Recommended memory design" section. Ports adapted to this repo's layout
> (`src/story_engine/ports/`, `.../domain/models/`, `.../adapters/outbound/`).

## 1. Memory taxonomy (CoALA) → storytelling mapping
| Type | CoALA | Storytelling engine |
|---|---|---|
| Working / short-term | fits current context window | current episode draft + last N scene summaries |
| **Episodic** | ordered log of what happened | per-episode event log / summaries (append-only) |
| **Semantic** | generalized world facts | the **series bible**: lore, canon, relationships |
| **Entity** | facts about a named actor | **character state**: traits, knowledge, location, status |
| Procedural | skills/how-to | versioned `prompts/` (already handled) |

**Core design rule:** episodic = "what happened" (append-only, ordered, immutable) vs semantic/entity =
"what is currently true" (mutable, versioned, canonical). **Conflating these is the most common error.**
Episodic memory is argued to be the specifically missing piece for long-horizon agents (arXiv 2502.06975)
— and serialized fiction *is* an episodic-continuity problem.

## 2. Continuity patterns (buildable, from 2025-26 systems)
- **SCORE (arXiv 2503.23512):** a **symbolic state registry** — each critical entity/item holds a discrete
  state var, e.g. `status ∈ {active, lost, destroyed}`, with **absorbing states** (a destroyed item can't
  silently reappear "active"). Catches the classic bug: a dead character / lost object returning. Plus
  hierarchical episode summaries and hybrid retrieval (FAISS + TF-IDF + sentiment consistency).
- **FictionRAG (Algorithms 19(5):383):** **three separated retrieval lanes** — (1) factual events,
  (2) persona traits, (3) worldview constraints. Flat RAG over mixed content causes character hallucination
  and logic drift; separating the lanes preserves each. **Most transferable idea: don't put lore, character
  facts, and event log in one undifferentiated vector index.**
- **Failure taxonomy (Lost in Stories, arXiv 2603.05890):** Timeline/Plot-logic, Characterization,
  World-building, Factual/Detail contradictions — a checklist for what the state store must defend.

## 3. Persistence: repository vs SQLite/JSON vs vector store
- **Structured repo (SQLite/JSON)** for **canonical, exact-recall** state — series bible, character state,
  canon facts, open threads, episode metadata. Needs authoritative reads, transactional/versioned writes.
  A vector store is the WRONG tool here (approximate similarity ≠ authority).
- **Vector store (embeddings/RAG)** for **fuzzy associative recall** — "find lore relevant to this scene."
- **Hybrid is the real design:** retrieve candidates by similarity, then **resolve/validate against the
  canonical store** before generation.
- **Rule of thumb:** if getting it wrong is a continuity bug → structured store; if it's "nice associative
  color" → vector store.

## 4. mem0 (installed here) and when to use it
- **What it does:** LLM pipeline — **extract** salient facts → **consolidate** (ADD/UPDATE/DELETE/NOOP to
  dedup) → **retrieve** by cosine similarity. Scopes: conversation→session→user→org. Graph variant for
  relationships. SDK: `add/search/get/update/delete`. Library (`pip install mem0ai`) or self-host.
- **Use mem0 for the *associative/episodic recall* lane** — auto extraction + semantic retrieval.
- **Roll your own repo for the *canonical* lane** (bible, character state, canon). mem0's UPDATE/DELETE is
  heuristic/LLM-driven — you do NOT want an LLM silently overwriting canon. Canon needs deterministic,
  validated, versioned writes.
- **Contested:** automatic consolidation overwriting good memories, salience/promotion scoring, and
  persona-drift detection are open problems (arXiv 2602.14038, 2605.09863). Keep auto-consolidation OFF the canonical path.

## 5. Memory in hexagonal architecture
Memory = **outbound (driven) ports** in the domain, swappable adapters in `adapters/outbound/` — keeps mem0 /
vector SDKs out of `domain/`/`services/` (Hard Constraint #7). **Split into multiple ports along the lane
boundary — don't build one god-`MemoryPort`.**

## Recommended memory design (adapted to this repo)
**Ports** — `src/story_engine/ports/`
- `story_bible_repository.py` → `StoryBibleRepositoryPort`: `get_bible`, `upsert_character`, `get_character`,
  `add_canon_fact`, `list_open_threads`, `resolve_thread`.
- `episode_log_repository.py` → `EpisodeLogRepositoryPort`: `append_summary`, `get_recent(series_id, n)`,
  `get_by_episode`. Append-only.
- `lore_retriever.py` → `LoreRetrieverPort`: `index(items)`, `retrieve(query, k, lane)` returning canonical
  IDs/refs (not authority); `lane` = FictionRAG factual/persona/worldview.

**Domain models (Pydantic)** — `src/story_engine/domain/models/memory.py`
- `CharacterState` — id, name, traits, knowledge, location, `status: Literal["active","lost","dead",...]`
  (SCORE absorbing state), arc_notes, last_seen_episode.
- `CanonFact` — id, statement, `scope: Literal["world","character","plot"]`, established_episode,
  `supersedes: str | None` (versioned canon).
- `PlotThread` — id, description, `status: Literal["open","resolved","abandoned"]`, opened/resolved episode.
- `EpisodeSummary` — series_id, episode_number, synopsis, character_actions, events, emotional_beat.
- `StoryBible` — aggregate: series_id, premise, world_rules, characters, open_threads.

**Adapters (outbound)** — `src/story_engine/adapters/outbound/`
- `sqlite_story_bible_repository.py` (canonical; JSON dev alt), `sqlite_episode_log_repository.py`,
  `mem0_lore_retriever.py` (associative lane only — **all mem0/vector imports live here**).

**Services** — `src/story_engine/services/`
- `context_assembler.py` — pull canon (bible) + recent summaries (log) + associative hits (retriever) →
  compose working-memory prompt via versioned `prompts/`.
- `continuity_checker.py` — validate a generated draft against canonical state (absorbing-state / thread
  checks) before accepting.

**Why:** canon is deterministic and you control it (no LLM silently rewriting); episodic log is append-only
truth; only the fuzzy lane touches embeddings/mem0; every boundary is a mockable port.

## Sources
- https://arxiv.org/pdf/2502.06975 — episodic memory as the missing piece for long-term agents.
- https://github.com/Shichun-Liu/Agent-Memory-Paper-List — memory taxonomy / CoALA lineage.
- https://arxiv.org/html/2503.23512v1 — SCORE: symbolic state registry, absorbing states, hybrid retrieval.
- https://doi.org/10.3390/a19050383 — FictionRAG three-lane hierarchical memory.
- https://arxiv.org/html/2603.05890v1 — Lost in Stories: consistency-bug taxonomy.
- https://docs.mem0.ai/core-concepts/memory-types , https://docs.mem0.ai/open-source/overview — mem0 memory types, deploy.
- https://www.emergentmind.com/topics/mem0 , https://github.com/mem0ai/mem0 — mem0 pipeline + SDK/self-host.
- https://douwevandermeij.medium.com/hexagonal-architecture-in-python-7468c2606b63 — driven ports = repository interfaces.
- https://softwarepatternslexicon.com/python/architectural-patterns/hexagonal-architecture-ports-and-adapters/ — port/adapter placement.
- https://arxiv.org/pdf/2602.14038 — salience/consolidation unsettled.

---

## 2026-07-24 currency refresh (session 3 — REVIEW-03)
Added a dedicated persistence convention doc (`.claude/rules/python/09-persistence.md`) — SQLModel-on-SQLite was mandated stack with zero doc coverage. Rules: `table=True` models live in adapters (never `domain/`); one `Session` per unit-of-work via context manager; map Row→domain inside the session scope (avoids `DetachedInstanceError`); `create_all` at startup, no Alembic for the hackathon. https://sqlmodel.tiangolo.com/
