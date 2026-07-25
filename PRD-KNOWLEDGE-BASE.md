# PRD — Narrative Knowledge Base ("Canon Kernel")

> **Component PRD.** Scope is the *Knowledge Base component* of the Narrative Knowledge System, not
> the whole product. Written 2026-07-25 for the Pocket FM × OpenAI "Zero to One" hackathon.
>
> **Companion docs:** research vault `research/Pocket FM Hack/Pocket-FM-Hackathon/Knowledge-Base/`
> (notes 01–13), `_PROBLEM STATEMENT (official).md`, `_PROBLEM VERDICT (evidence-selected).md`.
> Build state: `PROGRESS.md`, `feature_list.json`, `DECISIONS.md`.

---

## 0. How to read this document

Requirements are IDed and testable. Every functional requirement carries **Priority · Rationale ·
Dependencies · Acceptance Criteria · Verification Method**.

Product-level decisions are still open (being resolved in a parallel session). Rather than guess,
this PRD:

- states each open item as a numbered **Assumption (A#)** with the decision that would overturn it;
- specifies **both branches** wherever the data model genuinely forks (see §14 and OD-1);
- marks anything not yet evidence-backed with ⚠.

Priority scale: **P0** = the component is not the component without it · **P1** = needed for the
claimed differentiator · **P2** = valuable, cut first under time pressure · **P3** = post-hackathon.

---

## 1. Executive Summary

Serialized fiction breaks after roughly chapter 10 because the generating model has no durable record
of *what is true, who knows it, and what the story has promised*. The **Canon Kernel** is that
record: an external, typed, tri-temporal store of narrative facts, wrapped in a verify-loop that
checks every draft against canon **before** it ships and cites the episode that proves the
contradiction.

Three things make this component defensible rather than derivative:

1. **It closes a loop that the incumbent explicitly leaves open.** Pocket FM's own AI team published
   the Narrative World Model ([arXiv 2607.05577](https://arxiv.org/abs/2607.05577), 2026-07-06) — a
   narratology-grounded typed temporal-state graph with epistemics, promise threads and chapter-safe
   retrieval. Its limitations section states plainly: *no generation-time enforcement, no verifier,
   conditioned generation remains future work.* NWM answers questions about finished text. The Canon
   Kernel governs text being written.
2. **It models multi-source canon.** Base novels are authoritative; fan fiction contradicts them by
   design; a user taking over a character contradicts both. No memory system in the surveyed field —
   including NWM — represents conflicting facts from sources of differing authority. This component
   does, via fork lineage (§14).
3. **It makes epistemic scope a user-visible mechanic, not a backend detail.** "You are playing
   Watson; you may not act on what only Holmes knows" is enforced by the same negative-retrieval
   query that prevents spoiler leaks.

**Definition of done for the hackathon slice:** hard invariants enforced deterministically with
provenance-cited flags, spoiler-guarded retrieval, and one measured with-vs-without comparison.

---

## 2. Vision

A narrative knowledge base that preserves story truth across hundreds of episodes and many authors,
and remains directly usable by an LLM — so that generated, adapted, and user-steered story can be
*trusted* at a scale where no human continuity editor can keep up.

The long-term shape: the Kernel is infrastructure. Generators, co-writers, interactive takeover
sessions, and localisation pipelines all read from and are checked against it. It is the continuity
editor, externalised and automated.

---

## 3. Problem Statement

**For creators and platforms producing long-form serialized fiction**, continuity failure is the
binding constraint on AI-assisted production.

- LLMs cannot reliably track entity state, even in-context
  ([Entity Tracking, ACL 2023](https://aclanthology.org/2023.acl-long.213/)).
- Consistency errors in long generated stories cluster in **factual and temporal** dimensions and
  peak near narrative midpoints
  ([Lost in Stories / ConStory-Bench, 2603.05890](https://arxiv.org/abs/2603.05890)).
- General-purpose memory optimises for *semantic similarity*; narrative requires *canonical truth,
  temporal evolution, epistemics, and future-consistency* — a different objective function.
- Every product that died in this space died at the state/coherence wall, not the generation wall
  (`_PROBLEM VERDICT`: AI Dungeon ~1.5M→350K users; Character.AI's top complaint is "forgets me").

The unsolved slice is not *representation* — NWM demonstrated that. It is **enforcement**: nothing
sits between a generator and the canon it is about to violate.

---

## 4. Goals

| # | Goal | Measured by |
|---|---|---|
| G1 | Detect hard continuity violations in a draft, deterministically, with a provenance citation | Recall on planted-contradiction set (M-1) |
| G2 | Prevent premature reveals — never surface a fact the audience/character has not earned | Spoiler-leak rate vs. unguarded RAG (M-2) |
| G3 | Improve end-to-end consistency of generated episodes versus a no-Kernel baseline | Consistency delta (M-3) |
| G4 | Represent conflicting canon from multiple sources without corrupting the base canon | Fork-isolation tests (M-4) |
| G5 | Make every stored fact auditable back to its source span | Provenance completeness (M-5) |

---

## 5. Non-goals

Explicitly **not** this component's job:

- **Generating prose.** The writer LLM is a consumer at the boundary.
- **Scraping.** Source acquisition is upstream; the KB accepts a normalised `RawEpisode`.
- **Audio / TTS.** Out of scope entirely.
- **Takeover UI / session management.** The KB exposes an API; the experience layer is separate.
- **Guaranteeing *soft* consistency** (motivation, tone, prose quality). The Kernel flags these for a
  human and does not claim to enforce them. Stating this boundary is a requirement, not a caveat.
- **Multilingual canon reconciliation.** Deferred (⚠ and note NWM is also English-only — this is
  unclaimed ground, but not for a 36-hour build).
- **Auto-repair of flagged drafts.** MVP is flag-only; repair is P3.

---

## 6. Personas

**P-1 — The Continuity-Constrained Producer (primary).** Runs a serialized title with AI-assisted
drafting. Currently maintains a spreadsheet bible and pays editors to catch breaks. Costly behaviour
is documented (`_PROBLEM VERDICT`: manual patch sessions, paid editors, tool-hopping). Wants: "tell
me this chapter doesn't break the last two hundred, and show me why."

**P-2 — The Writer LLM (machine persona, primary consumer).** Needs scoped canon assembled *for it*,
deterministically, every episode — it cannot be trusted to ask. Needs to be told, specifically and
with citation, what it just got wrong.

**P-3 — The Takeover Player (secondary, ⚠ pending A-3).** Assumes a character and acts in the world.
Needs the world to stay coherent and needs to be bound by what their character knows.

**P-4 — The Canon Curator.** Adjudicates whether an extracted fact enters canon. Human at low volume,
policy-driven at high volume. Exists because auto-extraction is mostly noise (Spotify's expert panel
rejected 87.5% of auto-proposed facts; ⚠ that figure is from music metadata, not fiction, and its
transfer is unvalidated).

---

## 7. Assumptions (each overturnable by the parallel session)

| # | Assumption | Overturned by | Blast radius if wrong |
|---|---|---|---|
| **A-1** | Fan fiction is modelled as a **fork** off canon, not a lower-authority tier | OD-1 | Data model §14, retrieval resolution, verifier semantics — **large** |
| **A-2** | The KB operates a **closed loop** (assemble → generate → verify → commit), not read-only memory | Confirmed this session | Component boundary, API — large |
| **A-3** | Primary buyer is **creator/producer**; takeover player is a demo surface, not the buyer | OD-2 | Personas, metrics, latency NFRs — medium |
| **A-4** | Corpus is **public-domain base novels + fan fiction of public-domain works** | OD-3 | Legal posture, eval set — medium; architecture unaffected |
| **A-5** | English-only for the MVP | — | Small (deferred by design) |
| **A-6** | Team size and remaining hours are **unknown**; §22 milestones assume a single vertical slice per stage with hard cut-lines | OD-4 | Milestone sizing — medium |
| **A-7** | Substrate is the **existing repo** (Python 3.12, hexagonal, SQLModel/SQLite), with Databricks Delta as an optional projection for time-travel demo | OD-5 | Storage §16 — medium |

---

## 8. Knowledge Model

Two orthogonal axes, taken from vault note `01 - Narrative Knowledge Taxonomy` and corroborated by
NWM's record types.

**Axis A — what is known.** Entities · Relationships · State/attributes · Events & timeline ·
Commitments (promises, secrets, foreshadowing) · World rules · Canon meta (tier, provenance, retcon).

**Axis B — who knows it.** Narrator · each character · the audience *at this point in the telling*.
The gap between audience-knowledge and character-knowledge is dramatic irony; the gap between
world-truth and audience-knowledge is suspense. A KB without Axis B cannot distinguish a spoiler
from a plot point.

### 8.1 The three time axes

This is the precision the rest of the design depends on. Most systems carry one; bitemporal systems
carry two; narrative needs **three**.

| Axis | Question it answers | Precedent |
|---|---|---|
| **Story time** (`valid_from`, `valid_to`) | When was this true *in the world*? | Zep/Graphiti valid-time |
| **Telling time** (`revealed_at`) | When did the *audience* learn it? | NWM's "reveal order" vs "event order" |
| **Record time** (`recorded_at`, `superseded_at`) | When did *our store* learn/change it? | Fowler, bitemporal history |

Story time enables "who was alive at episode 40." Telling time enables the spoiler guard. Record time
makes retcons auditable rather than corrupting.

⚠ **Open:** fan fiction introduces a fourth ordering problem — a fan story branching from chapter 12
may have been *written* after chapter 400 shipped, so its record time bears no relation to its story
or telling time. Handled by fork lineage (§14) rather than a fourth column, but this is untested.

---

## 9. Data Model

```
Source      { id, type: novel|fanfic|user_session, tier: int, title, url?, license_note }

Fork        { id, parent_fork_id | null, divergence_at: (fork_id, story_time),
              source_id, label, created_at }
              # fork_id = "canon" is the root; parent = null

Entity      { id, fork_id, type: Character|Location|Object|Organization,
              canonical_name, aliases[], attributes{}, status: alive|dead|imprisoned|unknown }

Fact        { id, fork_id,
              subject_id, predicate, object_id | literal,
              valid_from, valid_to,                    # story time
              revealed_at,                             # telling time  (null = unrevealed)
              recorded_at, superseded_at,              # record time
              knower_scope: set<entity_id | "audience" | "narrator">,
              provenance: { source_id, chapter, char_span },
              confidence: float, tier: int,
              status: active | invalidated | quarantined }

Commitment  { id, fork_id, type: foreshadow|promise|secret|mystery,
              planted_at, state: planted|triggered|paid_off|broken,
              payoff_at?, entity_ids[], provenance }

Event       { id, fork_id, story_time, telling_order, description,
              participants[], location_id, causes[], effects[], preconditions[] }

Flag        { id, draft_id, invariant, severity, lane: hard|soft,
              draft_span, cited_fact_ids[], citation_text, suggested_action }
```

**Invariants enforced at write time (Pydantic):** `valid_from <= valid_to`; `revealed_at >= valid_from`
(a fact cannot be revealed before it is true) — ⚠ except for foreshadowing, which is precisely the
exception, so this is a *warn*, not a *reject*; `knower_scope` non-empty; `provenance.source_id` must
resolve; `confidence ∈ [0,1]`; a `Fact` in fork F may only reference entities resolvable in F's
ancestry.

---

## 10. Component Responsibilities

Hexagonal, matching the existing repo layout (`.claude/rules/structure.md`).

| Layer | Module | Responsibility |
|---|---|---|
| **domain/** | `canon/` | Entity, Fact, Commitment, Event, Fork, Flag, Provenance, KnowerScope. Pure. No IO. |
| **domain/** | `invariants/` | Pure predicates: `is_dead_and_acting`, `violates_causality`, `object_not_present`, `acts_on_unknown_fact` |
| **ports/** | `CanonEventLogPort` | append(op), replay(fork, upto) |
| **ports/** | `CanonQueryPort` | typed reads: `facts_about`, `state_as_of`, `unrevealed`, `open_commitments` |
| **ports/** | `ExtractionPort` | prose → candidate facts (schema-constrained) |
| **ports/** | `ContradictionScorerPort` | (canon_fact, draft_sentence) → entail/neutral/contradict |
| **services/** | `IngestionService` | RawEpisode → candidates → curation → append |
| **services/** | `CurationService` | promote / quarantine by confidence + tier policy |
| **services/** | `RetrievalService` | query router + scoped assembly + spoiler guard |
| **services/** | `VerificationService` | hard lane, soft lane, flag emission |
| **services/** | `ForkService` | create fork, resolve lineage, isolate writes |
| **adapters/outbound/** | `persistence/` | SQLModel/SQLite (+ optional Delta projection) |
| **adapters/outbound/** | `extraction/` | Instructor / OpenAI structured outputs / Databricks `json_schema` |
| **adapters/outbound/** | `nli/` | DeBERTa-MNLI or LLM-judge fallback |
| **api/** | routes | the §17 surface |
| **bootstrap.py** | — | the only place adapters are wired |

---

## 11. Functional Requirements

### Ingestion & Extraction

**KB-F-01 — Accept normalised source episodes.**
*Priority:* P0 · *Rationale:* decouples the KB from scrapers; both scrapers become interchangeable
adapters. *Dependencies:* none.
*AC:* Given a `RawEpisode {source_id, chapter, text, tier}`, the KB stores it verbatim as an
addressable episode record before any extraction occurs.
*Verification:* integration test — ingest, then retrieve the verbatim text by `(source_id, chapter)`.

**KB-F-02 — Schema-constrained fact extraction with provenance.**
*Priority:* P0 · *Rationale:* you cannot verify what is not structured; every downstream guarantee
inherits extraction quality (the top risk, R-1). *Dependencies:* KB-F-01, `ExtractionPort`.
*AC:* Extraction emits only schema-valid `Fact`/`Entity`/`Commitment` candidates; every candidate
carries `provenance.char_span` locating it in the source text; malformed model output is rejected and
retried, never silently coerced.
*Verification:* unit test with a stubbed extractor returning malformed JSON → raises, does not store.
Integration test on one real chapter → 100% of stored candidates have resolvable spans.

**KB-F-03 — Curation gate before canon.**
*Priority:* P0 · *Rationale:* raw extraction is mostly noise; a quarantine tier keeps garbage out of
canon while remaining inspectable. *Dependencies:* KB-F-02.
*AC:* Candidates above the confidence threshold enter canon as `active`; those below enter as
`quarantined` and are excluded from all retrieval and verification; the threshold is configuration,
not a literal.
*Verification:* unit test at threshold boundaries; integration test asserting quarantined facts never
appear in retrieval results.

**KB-F-04 — Invalidate, never overwrite.**
*Priority:* P0 · *Rationale:* the superseded fact is canon at a timestamp; overwriting destroys the
ability to answer "what was true at episode N" and makes retcons indistinguishable from corruption.
*Dependencies:* KB-F-03.
*AC:* A contradicting new fact sets the prior fact's `valid_to` and `superseded_at` and appends a new
row; no `UPDATE` ever deletes a claim; both remain queryable.
*Verification:* integration test — assert an allegiance flip at episode 181 leaves both the ep-1 and
ep-181 facts retrievable, and `state_as_of(100)` returns only the former.

### Storage & Forks

**KB-F-05 — Append-only canon event log.**
*Priority:* P0 · *Rationale:* the log is truth; state is a projection. Gives replay, audit, and
"canon as of episode N" without bespoke snapshot logic. *Dependencies:* KB-F-04.
*AC:* Every canon mutation is an `ASSERT | UPDATE | INVALIDATE | RETCON` entry; replaying the log to
sequence *n* reproduces the projection at *n* byte-for-byte.
*Verification:* property test — replay determinism over a randomised operation sequence.

**KB-F-06 — Fork creation and lineage resolution.**
*Priority:* P1 · *Rationale:* the multi-source differentiator (G4); fan fiction and takeover sessions
are branches, not errors. *Dependencies:* KB-F-05, A-1.
*AC:* A fork records `parent_fork_id` and a `divergence_at` point. A query in fork F resolves facts by
walking F → parent → … → canon, with nearer-fork facts **shadowing** ancestors. Writes to F are
invisible in canon and in sibling forks.
*Verification:* integration test — assert a fact asserted in fork A is absent from canon and from
fork B; assert a canon fact is visible in A unless shadowed.

**KB-F-07 — Source tier on every fact.**
*Priority:* P1 · *Rationale:* auditability of authority; enables tier-based adjudication if OD-1
resolves to the tier model instead of forks. *Dependencies:* KB-F-02.
*AC:* Every fact carries the tier of its source; tier is queryable and filterable.
*Verification:* unit test on the write path; API test on tier filtering.

### Retrieval

**KB-F-08 — Deterministic scoped canon assembly.**
*Priority:* P0 · *Rationale:* the generator cannot be trusted to *ask* for canon; if assembly is
agent-elective, a missed lookup is a silent continuity failure. *Dependencies:* KB-F-05.
*AC:* Given `(fork, telling_time, characters, scene_intent)`, the service returns a bounded,
deterministic canon packet. The same inputs always return the same packet.
*Verification:* integration test asserting byte-identical packets across repeated calls.

**KB-F-09 — Spoiler-guard (negative retrieval).**
*Priority:* P0 · *Rationale:* this is the query no general-purpose system has, and the visible
novelty (G2). A correct retrieval and a spoiler are indistinguishable to a vector store.
*Dependencies:* KB-F-08, telling-time axis.
*AC:* Facts with `revealed_at > telling_time` or `revealed_at IS NULL` are **excluded** from every
assembled packet; the exclusion set is separately retrievable for demonstration.
*Verification:* dedicated red-team test — a story with a planted reveal; assert zero leakage at every
pre-reveal telling-time; assert the withheld fact *is* returned once telling-time passes the reveal.

**KB-F-10 — Epistemic scoping of retrieval.**
*Priority:* P1 · *Rationale:* enables the takeover mechanic and prevents characters acting on
information they were never told — the most common AI-fiction tell. *Dependencies:* KB-F-09.
*AC:* Given a `knower`, the packet contains only facts whose `knower_scope` includes that knower (or
"narrator"/"audience" as configured).
*Verification:* integration test — assert a Watson-scoped packet omits Holmes-only facts.

**KB-F-11 — Typed query router.**
*Priority:* P2 · *Rationale:* different narrative questions need different structures; a single index
is optimal for none. *Dependencies:* KB-F-08.
*AC:* MVP routes at least: exact attribute lookup · temporal `as_of` · epistemic set membership ·
open-commitment filter · negative spoiler filter. Unroutable queries fail loudly rather than
defaulting to similarity search.
*Verification:* unit tests per route; a test asserting an unknown query type raises.

### Verification

**KB-F-12 — Hard-lane deterministic verification.**
*Priority:* P0 · *Rationale:* factual and temporal errors dominate real failures and are exactly the
deterministically checkable ones — most of the win at near-zero marginal cost.
*Dependencies:* KB-F-08, `domain/invariants`.
*AC:* On a draft, the hard lane checks **identity** (one node per entity across aliases; single-valued
attributes do not drift), **mortality/status** (a dead or imprisoned character does not act freely),
**timeline** (no effect before cause; no entity in two places at one story-time), **inventory/location**
(objects do not teleport), and **epistemic precondition** (a character does not act on a fact outside
their knower scope). No model call is made in this lane.
*Verification:* planted-contradiction suite, one fixture per invariant; assert recall and assert zero
LLM calls via a spy adapter.

**KB-F-13 — Flags carry provenance citations.**
*Priority:* P0 · *Rationale:* an uncited flag is an opinion; a cited flag is evidence, and it is what
makes the demo land. *Dependencies:* KB-F-12.
*AC:* Every flag names the draft span, the violated invariant, the specific canon fact IDs, and a
human-readable citation of the form *"draft says X; canon: ¬X established at ep 181 §3."*
*Verification:* snapshot test on flag rendering; assert `cited_fact_ids` is non-empty for every hard-lane flag.

**KB-F-14 — Soft-lane sampled semantic verification.**
*Priority:* P2 · *Rationale:* catches contradictions symbolic rules cannot express, without paying an
LLM tax per sentence. *Dependencies:* KB-F-12.
*AC:* The soft lane runs only on sampled spans (mid-story and high-uncertainty passages preferred),
scores `(canon_fact, draft_sentence)` pairs, and emits flags at a *lower* severity than hard-lane
flags. Soft-lane unavailability degrades the system to hard-lane only — it never blocks.
*Verification:* integration test with the scorer adapter forced to fail → verification still returns
hard-lane flags.

**KB-F-15 — Commitment lifecycle tracking.**
*Priority:* P2 · *Rationale:* dropped setups are a named failure mode and invisible to similarity
search — nothing ever *asks* about an unfired gun. *Dependencies:* KB-F-03.
*AC:* Commitments transition `planted → triggered → paid_off`; illegal transitions are rejected;
commitments still open at an arc boundary are reportable.
*Verification:* state-machine unit tests including illegal transitions; integration test listing open
commitments.

### Evaluation

**KB-F-16 — With/without harness.**
*Priority:* P1 · *Rationale:* converts "good idea" into a number; G3. *Dependencies:* KB-F-12, KB-F-08.
*AC:* A single command runs an identical generation task with the Kernel disabled and enabled, scores
both on the same rubric, and emits a comparable artifact.
*Verification:* the command runs end-to-end in CI on a fixture corpus and produces a deterministic
report structure.

---

## 12. Non-functional Requirements

| ID | Requirement | Priority | Acceptance / Verification |
|---|---|---|---|
| KB-NF-01 | Hard-lane verification adds no LLM call and completes in **< 500 ms** per draft on the fixture corpus | P0 | Benchmark test asserting wall-clock and zero model calls |
| KB-NF-02 | Retrieval assembly is **deterministic** — identical inputs, identical packet | P0 | Repeat-call equality test |
| KB-NF-03 | Every stored fact is **traceable to a source span**; zero facts with null provenance | P0 | DB constraint + integration assertion |
| KB-NF-04 | Store runs **embedded, zero-infra** by default; cloud projection is optional and non-blocking | P0 | Full suite passes with no network access |
| KB-NF-05 | Extraction cost is **bounded and reported** per episode (tokens, spend) | P1 | Metering assertion in the ingestion test |
| KB-NF-06 | All public signatures typed; `make check` (ruff + ruff-format + mypy strict + pytest) green | P0 | `make check` |
| KB-NF-07 | No secrets in code; config via pydantic-settings | P0 | `make check` + grep gate |
| KB-NF-08 | Corpus ingestion is **restartable** — re-ingesting an already-seen chapter is a no-op | P1 | Idempotency integration test |
| KB-NF-09 | Fork operations are **isolated**: no write in a fork can mutate an ancestor | P1 | Fork-isolation test (KB-F-06) |

---

## 13. User Stories & Acceptance Criteria

**US-1 (P-1, Producer).** *As a producer, I want to know whether a new chapter breaks established
canon, and exactly where, so I don't ship a contradiction.*
**AC:** Submitting a draft returns a list of flags, each citing the violated invariant and the source
episode; a clean draft returns an empty list, not a hedge.

**US-2 (P-2, Writer LLM).** *As the writing model, I want the relevant canon handed to me, scoped to
what may be revealed now, so I don't have to know what to ask for.*
**AC:** A single call returns a bounded canon packet; no fact in it has `revealed_at` after the
requested telling-time.

**US-3 (P-3, Takeover Player, ⚠ A-3).** *As a player controlling Watson, I want to be prevented from
acting on things Watson doesn't know.*
**AC:** An action referencing a fact outside the character's knower scope is flagged with the reason
and the episode the character would have had to witness.

**US-4 (P-1).** *As a producer, I want to ingest a fan story without it corrupting the base novel's canon.*
**AC:** After ingesting fan fiction into fork A, every canon query at the root returns results
identical to before ingestion.

**US-5 (P-4, Curator).** *As a curator, I want low-confidence extractions held back for review rather
than silently entering canon.*
**AC:** Quarantined facts are listable, are excluded from retrieval and verification, and can be
promoted or rejected explicitly.

---

## 14. Architecture Decisions

**AD-1 — External state object + verify-loop, not a bigger prompt.**
*Status:* accepted. *Rationale:* LLMs demonstrably fail entity-state tracking; a tracking failure
cannot be fixed by asking the failing component to try harder.
*Rejected:* long-context-only; semantic-RAG-only. Both fail on superseded facts and spoilers.

**AD-2 — Closed loop (generation-time enforcement), not read-only memory.**
*Status:* accepted this session. *Rationale:* this is the gap NWM's own limitations section names.
*Consequence:* the KB owns write, read, **and** check — a larger component boundary than a memory store.

**AD-3 — Tri-temporal facts (story · telling · record time).**
*Status:* accepted. *Rationale:* two axes cannot express "true, but the audience hasn't learned it
yet," which is the spoiler guard's entire basis.
*Rejected:* single-timestamp (loses history); bitemporal-only (loses telling time).

**AD-4 — Event log as truth, projection for queries (CQRS-lite).**
*Status:* accepted. *Rationale:* free audit, replay, and "canon as of N."
*Mitigation:* one physical store with a derived view — not two separately maintained systems, whose
complexity is a known trap.

**AD-5 — Hard/soft lane split.**
*Status:* accepted. *Rationale:* the dominant real-world error classes are the deterministically
checkable ones; this is the single largest cost lever.
*Boundary stated honestly:* the Kernel *guarantees* hard invariants and *assists* on soft ones.

**AD-6 — Multi-source canon: FORK model.**
*Status:* **provisional (A-1, open as OD-1).** Both branches specified so the decision slots in:

| | **Branch A — Fork (assumed)** | **Branch B — Tier** |
|---|---|---|
| Model | `Fork{parent, divergence_at}`; facts scoped to a fork | Single graph; `tier` int on every fact |
| Query semantics | Walk lineage; nearer fork shadows ancestor | Filter by tier; higher tier wins conflicts |
| Verifier asks | "Consistent within *this* fork's lineage?" | "Consistent with the highest-authority fact?" |
| Takeover session | Just another fork | Facts at a user tier competing with canon |
| Cost | Lineage resolution on every read | Simpler reads; loses divergence semantics |
| Extra tables | `Fork` | none |

Schema impact is contained: Branch B is Branch A with a single root fork and tier-based resolution,
so building A does not preclude B, but B does preclude A. **Recommendation: A.**

**AD-7 — Substrate: existing embedded store first, cloud projection optional.**
*Status:* provisional (A-7, OD-5). *Rationale:* the demo must not be sinkable by cloud setup; a
time-travel projection is a demo enhancer, not a dependency.

---

## 15. Information Architecture

```
RawEpisode ──> Extraction ──> Candidates ──> Curation Gate ──┬──> quarantine
                                                             │
                                                             ▼
                                                   Canon Event Log  (truth)
                                                             │ project
                                                             ▼
                              ┌────────── Canon Projection (fork-aware) ──────────┐
                              │                                                    │
                      Retrieval Service                                  Verification Service
                   (router + spoiler guard)                              (hard lane / soft lane)
                              │                                                    │
                              ▼                                                    ▼
                     scoped canon packet  ──────> [writer LLM] ──draft──>   flags + citations
                                                                                   │
                                                                        clean ─────┴──> commit (back to ingestion)
```

---

## 16. Memory Model

- **Working set** — the current arc's live facts, always assembled.
- **Canon** — promoted, curated, provenance-stamped facts. The system of record.
- **Quarantine** — extracted but unpromoted. Inspectable, never retrieved.
- **Fork overlays** — per-branch fact sets resolved against ancestry at read time.
- **Raw episodes** — verbatim source text, addressable, never the retrieval target for canon
  questions (only for provenance display).

Retrieval never treats similarity as the organising principle. Structured/temporal/epistemic filters
scope the candidate set *first*; semantic ranking, where used at all, operates inside that slice.

---

## 17. API Requirements

Thin HTTP surface over the services; the same operations are available in-process.

| Method | Path | Purpose | Requirement |
|---|---|---|---|
| `POST` | `/episodes` | Ingest a `RawEpisode` | KB-F-01 |
| `POST` | `/episodes/{id}/extract` | Run extraction → candidates | KB-F-02 |
| `POST` | `/candidates/promote` | Curation decision | KB-F-03 |
| `GET` | `/canon/state` | `?fork=&as_of=&knower=` → entity/fact state | KB-F-08 |
| `POST` | `/canon/assemble` | Scene intent → scoped packet | KB-F-08, F-09, F-10 |
| `GET` | `/canon/withheld` | The spoiler exclusion set (demo surface) | KB-F-09 |
| `POST` | `/verify` | Draft → flags with citations | KB-F-12, F-13 |
| `POST` | `/forks` | Create a fork at a divergence point | KB-F-06 |
| `GET` | `/commitments?state=open` | Unresolved setups | KB-F-15 |
| `GET` | `/facts/{id}/provenance` | Source span for a fact | KB-NF-03 |

**Error contract:** every failure returns a typed error with a machine-readable code. Never return a
partial canon packet on error — a silently truncated packet is a continuity failure disguised as
success (see §19).

---

## 18. Edge Cases

| # | Case | Required behaviour |
|---|---|---|
| E-1 | Alias/coreference miss — "the Stranger" and "the King" extracted as two entities | Alias set on entity; identity invariant flags single-valued attribute conflict across candidate duplicates |
| E-2 | A character lies | Fact stored with `knower_scope` = the liar; world-truth stored separately. A lie is not a contradiction |
| E-3 | Retcon — canon deliberately changed | `RETCON` log op + compensating entry; prior state remains queryable |
| E-4 | Foreshadowing — revealed before it is "true" | Warn, never reject (the `revealed_at >= valid_from` rule's designed exception) |
| E-5 | Fan story with no clear divergence point | Default divergence = latest common chapter; flag as low-confidence for curation |
| E-6 | Fan story written after later canon exists | Fork lineage is by *story* position, not record time (§8.1 ⚠) |
| E-7 | Two reveals of the same secret with different content | Commitment invariant: a secret is revealed at most once; second reveal flagged |
| E-8 | Resurrection in a world where it is legal | Mortality check is gated on a world-rule flag, not hardcoded |
| E-9 | Empty canon (first episode) | Verification returns zero flags without error; assembly returns an empty packet, not a failure |
| E-10 | Extraction returns zero facts for a chapter | Logged loudly as a quality signal; ingestion succeeds; chapter marked low-yield |

---

## 19. Error Handling

- **No bare excepts, no silent pass.** Catch specific; fail loud (project hard constraint).
- **Extraction failure** → the episode is stored, extraction is marked failed, and it is retryable.
  Never a partial fact set silently committed.
- **Scorer (NLI/judge) unavailable** → degrade to hard-lane only, and *say so in the response*. A
  degraded verification must never be indistinguishable from a clean one.
- **Assembly failure** → error, never a truncated packet.
- **Fork lineage cycle** → rejected at fork creation.
- **Unknown query type** → explicit error, never a similarity-search fallback.

---

## 20. Success Metrics

| ID | Metric | Target | How measured |
|---|---|---|---|
| M-1 | Hard-invariant recall on planted contradictions | ⚠ set after baseline run — do **not** publish a number before measuring | Planted-contradiction suite, per invariant |
| M-2 | Spoiler-leak rate, Kernel vs. unguarded retrieval | Zero leaks under the guard | Red-team reveal test |
| M-3 | End-to-end consistency delta, Kernel on vs. off | ⚠ measure, do not assert. The "+20–60%" in the vault is a *target*, not a result | With/without harness (KB-F-16) |
| M-4 | Fork isolation | 100% — no ancestor mutation | Isolation suite |
| M-5 | Provenance completeness | 100% of canon facts have a resolvable span | DB assertion |
| M-6 | Extraction precision on a hand-labelled sample | ⚠ establish baseline; it caps everything downstream | Manual labelling of one chapter |
| M-7 | Hard-lane p95 latency | < 500 ms, zero LLM calls | Benchmark |

**Reporting rule:** a null or negative M-3 must be reported honestly. The harness exists to test the
thesis, not to confirm it.

---

## 21. Risks

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| R-1 | **Extraction quality caps everything.** The verifier faithfully enforces whatever canon it was given, with confident provenance — wrong canon is worse than no canon | **Critical** | Spike extraction on one real chapter before building anything downstream; curation gate; provenance makes bad facts auditable and reversible; simplify the schema if precision is poor |
| R-2 | **Novelty challenge — NWM exists and Pocket FM wrote it** | High | Lead with it. Cite it as validation, and quote its limitations section as the gap. Being the team that read the judges' paper is an advantage, not a liability |
| R-3 | **The "AI Dungeon graveyard" objection to the takeover surface** | High | Answer it explicitly: those products died at the state/coherence wall, which is the exact wall this component exists to remove. Do not let it be raised first by a judge |
| R-4 | **IP posture** — scraped commercial fiction demoed to a commercial publisher | High | Public-domain base corpus + fan fiction of public-domain works; keep source adapters generic and pitch them as pluggable onto a licensed catalogue |
| R-5 | **Corpus volume** — extraction cost scales per chapter across hundreds of chapters | Medium | Ingest a bounded slice; cache aggressively; report cost per episode (KB-NF-05) |
| R-6 | **Scope** — two scrapers, forks, takeover, and a verifier is more than one build | Medium | Milestone cut-lines (§22); the trio *hard invariants + spoiler guard + one metric* is the whole pitch and everything else is optional |
| R-7 | **Soft-lane unreliability** on motivation/tone | Medium | Scope the claim honestly (AD-5); report hard and soft recall separately |
| R-8 | **Unknown time/team budget (A-6)** | Medium | Milestones are independently shippable with explicit rollback points |

---

## 22. Milestones

Each milestone is independently testable, delivers demonstrable value, and is a safe stopping point.

**M0 — Schema & skeleton.** Domain models + Pydantic invariants + store, wired through `bootstrap.py`.
*Value:* the vocabulary exists. *Rollback:* trivial — nothing depends on it yet.

**M1 — Ingestion & extraction spike.** One real chapter → typed facts with provenance. **Gate:**
inspect precision manually before proceeding; if poor, simplify the schema *here*, not later.
*Value:* proves the load-bearing assumption. *Rollback:* schema simplification.

**M2 — Hard-lane verifier + planted contradictions.** *This alone is a working demo.*
*Value:* flags with citations. *Rollback point: everything after this is upside.*

**M3 — Scoped retrieval + spoiler guard.** *Value:* the visible novelty; the withheld-set endpoint.

**M4 — Forks.** *Value:* multi-source canon; fan fiction and takeover both land here.

**M5 — Eval harness + with/without number.** *Value:* turns the claim into a measurement.

**M6 (P2/P3) — Soft lane, commitments, time-travel projection.** Cut first under pressure.

**Cut-line:** if time is short, ship **M0 → M1 → M2 → M3 → M5**. That sequence is the entire thesis:
canon with provenance, deterministic flags, spoiler safety, and a measured delta. M4 is the
differentiator against NWM and should survive if at all possible.

---

## 23. Testing Strategy (per milestone)

Two tiers throughout: **pytest** for code correctness, **LLM-output quality evaluation** for
generation quality. Tests assert schema and invariants, never exact generated text. The LLM is mocked
in all unit tests.

| Milestone | Unit | Integration | E2E | Regression | Performance | Failure injection | Edge cases | Manual | Demo | Acceptance |
|---|---|---|---|---|---|---|---|---|---|---|
| **M0** | Model validation, invariant predicates | Store round-trip on real SQLite | — | Schema snapshot | — | Constraint violation raises | E-9 empty canon | Schema review | — | `make check` green |
| **M1** | Extractor contract with stub | Real chapter → stored facts w/ spans | Ingest→query | Fixture chapter output stable | Cost/episode reported | Malformed JSON; extractor timeout | E-1 aliases, E-10 zero-yield | **Hand-label one chapter (M-6)** | Facts accumulating with provenance | 100% facts have spans |
| **M2** | Each invariant predicate | Draft → flags | Ingest→verify | Planted-contradiction suite locked as regression | p95 < 500 ms, zero LLM calls | Store unavailable | E-2 lies, E-8 legal resurrection | Read 10 flags for false positives | **Dead character speaks → flagged with citation** | M-1 recall recorded |
| **M3** | Filter predicates | Packet assembly | Assemble→generate | Determinism snapshot | Assembly latency | Guard bypass attempt | E-4 foreshadowing, E-7 double reveal | Inspect withheld set | **Secret withheld pre-reveal, released after** | M-2 zero leaks |
| **M4** | Lineage resolution | Fork write isolation | Canon + fanfic + takeover | Canon-unchanged snapshot | Lineage depth cost | Cycle creation rejected | E-5, E-6 divergence | Diff canon before/after | **Fan story ingested; canon untouched; play inside the fork** | M-4 100% isolation |
| **M5** | Scorer wrapper | Harness runs both arms | Full with/without | Report structure stable | Total run cost | Judge unavailable → degrade | Null/negative result path | Read both outputs | **The comparison artifact** | M-3 measured and reported honestly |

**Manual validation is mandatory at M1 and M2.** Extraction precision and false-positive rate are the
two things no automated test can establish for you on a fresh corpus.

---

## 24. Deployment Strategy

- **Default:** embedded, zero-infra, runs offline. The demo must never depend on a network path.
- **Optional projection:** a cloud table for "canon as of episode N" time-travel — an enhancer, wired
  behind a feature flag, with an embedded fallback proven to work.
- **Config:** pydantic-settings, gitignored `.env`, names documented in `.env.example`.
- **Verification before "done":** `make check` — ruff, ruff-format, mypy strict, pytest. Code being
  written is not done; the gate passing is done.

---

## 25. Open Decisions (for the parallel session)

| ID | Decision | Blocks | Recommendation |
|---|---|---|---|
| **OD-1** | Fork vs. tier for multi-source canon | Data model, retrieval resolution, verifier semantics | **Fork** (AD-6 Branch A) |
| **OD-2** | Primary buyer: producer or takeover player | Personas, latency NFRs, metric choice | **Producer primary**, player as demo surface |
| **OD-3** | Corpus: public-domain vs. scraped commercial | Legal posture, eval set availability | **Public domain**; keeps adapters generic |
| **OD-4** | Remaining hours and team size | Milestone sizing, cut-line | — needed |
| **OD-5** | Cloud projection in or out | Deployment, demo risk | **Optional, flagged, fallback proven** |
| **OD-6** | Does takeover *generate prose* or *select bounded options* | Whether narrative-safe intent mapping is in scope | **Bounded first**; open input is a stretch |

---

## 26. Engineering Readiness Review

**Verdict: NOT READY for full implementation. READY for M0–M2.**

| Check | Status |
|---|---|
| Requirements complete | ⚠ Partial — complete for M0–M3; M4 depends on OD-1 |
| Architecture validated | ✅ For the loop and the temporal model; ⚠ for fork resolution |
| Dependencies identified | ✅ |
| Testing defined | ✅ Per milestone (§23) |
| Unknowns minimised | ⚠ R-1 (extraction quality) is unresolved by design — M1 exists to resolve it |
| Risk acceptable | ✅ With the M2 cut-line as the floor |

**Therefore:** start M0 and M1 now. M1's manual precision check is the gate that decides whether the
schema survives contact with real text. OD-1 must be answered before M4 begins, and the parallel
session has until then.

---

## 27. Future Work

- Auto-repair — propose the corrected line, not just the flag.
- Full per-character epistemic modelling, if a global reveal flag proves insufficient.
- Multilingual canon reconciliation — unclaimed ground; NWM is English-only and Pocket FM is not.
- Open-schema canon growth for entity types the schema never anticipated.
- Reflection-based canon distillation — compress hundreds of episodes into durable arcs.
- Cross-series shared-world canon with per-series validity.
- Author-facing continuity IDE — flag contradictions as the author types.

---

## 28. Sources

Load-bearing external evidence, verified 2026-07-25:

- [Narrative World Model, arXiv 2607.05577](https://arxiv.org/abs/2607.05577) — PocketFM authors
  (incl. Vasu Sharma, Head of AI); typed temporal-state graph; **limitations state no generation-time
  enforcement, no verifier, conditioned generation is future work**; English-only; backend
  proprietary; public benchmark on Project Gutenberg.
- [Lost in Stories / ConStory-Bench, arXiv 2603.05890](https://arxiv.org/abs/2603.05890) — error
  taxonomy; factual + temporal dominate; errors peak mid-narrative.
- [Codified Foreshadowing-Payoff, arXiv 2601.07033](https://arxiv.org/abs/2601.07033) —
  Foreshadow→Trigger→Payoff lifecycle.
- [EvolvingWorld, arXiv 2607.17250](https://arxiv.org/abs/2607.17250) — open-schema co-evolving world model.
- [Entity Tracking in Language Models, ACL 2023](https://aclanthology.org/2023.acl-long.213/) — LLMs
  do not reliably track entity state.
- [Zep / Graphiti, arXiv 2501.13956](https://arxiv.org/abs/2501.13956) — bi-temporal edges,
  invalidation-not-overwrite.
- [Bitemporal History — Fowler](https://martinfowler.com/articles/bitemporal-history.html) — valid vs.
  record time.
- Vault synthesis: `Knowledge-Base/01`–`13`, `_PROBLEM STATEMENT (official)`, `_PROBLEM VERDICT
  (evidence-selected)`, `04 - Human Editorial Systems` (Holocron canon tiers).

⚠ **Inference / unverified, carried forward:**
1. The three-time-axis framing is this document's synthesis; no single cited source presents it.
2. The 87.5% auto-extraction rejection figure is from music metadata; its transfer to narrative
   extraction is unvalidated.
3. All numeric targets in §20 are targets, not results. Nothing in §20 may be presented as measured
   until the harness has run.
4. Fork-lineage handling of fan fiction written after later canon (E-6) is untested design.
