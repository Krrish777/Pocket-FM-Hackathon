# Project Context

> **Status:** ACTIVE — this is the single source of truth for *what we are building and why*.
> **Written:** 2026-07-25 · **Event:** Zero to One GenAI Storytelling Hackathon, IIM Bangalore, Jul 25–26 2026
> **Supersedes:** the "CANON: Time Machine" PRD and parts of `_PROBLEM VERDICT` — see §12.
>
> **How to use this file.** Read §1–§5 to understand the product. Read §7 before building anything.
> Read §11 before assuming anything. If a statement here conflicts with any other document in this
> repo or in `research/`, **this file wins** — every superseded claim is listed explicitly in §12.
> Nothing in this file is implied, inferred, or left to judgment: unknowns are recorded in §11 with an
> ID and an owner, never left blank.

---

## 1. The Problem

### 1.1 The root problem
Serialized fiction is **passive by construction**. A listener consumes a story; they cannot participate
in it. The story is an aesthetic object that happens *at* the audience, not *with* them.

### 1.2 Why nobody has fixed it
Interactive fiction solves participation and has failed twice, in two distinct and well-documented ways:

| Approach | Example | Why it failed | Evidence |
|---|---|---|---|
| **Hand-authored branches** | Until Dawn, Bandersnatch | Authoring cost grows combinatorially with branch depth. Every branch is written by a human. Economically impossible past a few hours of content. | Netflix retired interactive titles; Bandersnatch pulled. |
| **Fully generated branches** | AI Dungeon | Infinite branches, but state stops fitting in context and the world becomes incoherent. | ~1.5M → ~350K users; characteristic complaint "mixes up names". Recorded in `research/Pocket FM Hack/Pocket-FM-Hackathon/_PROBLEM VERDICT (evidence-selected).md`. |

These are the only two known approaches. One is coherent but unaffordable. The other is affordable but
incoherent.

### 1.3 The insight this project is built on
**The branches already exist, and they are free.**

Millions of fan-fiction writers have already written the interesting divergences from popular stories.
Two properties make this supply valuable and not merely large:

1. **It is dense at the moments that matter.** Fan-fiction clusters on emotionally significant decision
   points, because those are the ones people care enough to rewrite.
2. **It is pre-filtered by an audience.** Divergences that did not resonate did not accumulate readers.
   Popularity has already done quality selection that we would otherwise have to do ourselves.

Nobody has connected this supply to an engine capable of keeping the results consistent.

### 1.4 The problem statement, stated exactly
> **Participation in serialized fiction is blocked by two constraints simultaneously: the
> branch-authoring bottleneck, and the coherence wall. Fan-fiction removes the first. A canon
> knowledge base with per-character epistemic state removes the second. This project is the first
> system to do both at once.**

### 1.5 Hackathon track alignment
Primary: **P1 — AI Native Storytelling**, statements *Story Time Machine* and *Infinite Story Universe*.
Secondary (not built, referenced in pitch only): **P2 — Living Characters**.
Source: `research/Pocket FM Hack/Pocket-FM-Hackathon/_PROBLEM STATEMENT (official).md`.

---

## 2. The Product

### 2.1 One line
A playable branching layer over existing novels: pick a character in a world you already know, play it
forward through choices that real fan-fiction already wrote, with every character remembering only what
they actually learned.

### 2.2 What it is NOT
Stated explicitly to remove ambiguity. This product is **not**:

- Not a story *generator*. Generation happens, but the differentiator is selection and enforcement.
- Not a chatbot or companion app. There is no open conversation with a character in the MUST scope.
- Not a single "flip one decision and read the result" diff viewer. It is a **playthrough** of up to 10
  compounding choices. (This is a change from the prior PRD — see §12.)
- Not a creator tool in this build. The creator surface is a pitch slide only (§7.3).
- Not audio-first in the MUST scope. Text first; audio is §7.2.
- Not multi-story. One novel series, one cast (§6).

---

## 3. Users

### 3.1 Primary user — THE PLAYER (the only user served by the MUST scope)
A single person who knows the source world and wants to be inside it rather than beside it. They select
a character, are presented with choices at narrative decision points, and play the story forward. They
are not writing; they are choosing.

**What they need:** the world to stay coherent as it diverges, and the character they inhabit to behave
like that character actually would — including being ignorant of what that character does not know.

### 3.2 Secondary user — THE CREATOR (pitch only, NOT BUILT)
A writer who posts their own story and uses the same engine to explore branches of it. Referenced in
the pitch as roadmap. **No creator functionality is in scope.** See §7.3.

### 3.3 The judge (audience for the artifact, not a user of it)
Must understand the concept in under 10 seconds and must be unable to dismiss the demo as "an LLM with
a nice interface." §8 defines what makes that dismissal impossible.

---

## 4. Core Loop (exact)

This is the complete interaction. There are no other flows in the MUST scope.

1. Player selects one character from the fixed cast (§6.3).
2. System presents the current scene as text, rendered from the character's filtered view (§5.3).
3. System presents **2–4 discrete choices**. Choices are derived from scraped fan-fiction (§5.2), not
   authored by us and not freely invented by the model.
4. Player selects exactly one choice. No free-text input in the MUST scope.
5. System applies the choice to world state, recomputes which facts are invalidated / still hold / are
   newly required, and updates each character's knowledge according to what they witnessed or were told.
6. System generates the next scene, verified against canon, with source citations available (§5.4).
7. Repeat from step 2. **Demo depth: up to 10 choices.**

### 4.1 Demo depth, stated exactly
**10 is a ceiling, not a target.** A demo run is any sequence of N choices where 1 ≤ N ≤ 10. The system
must not require 10 and must not break before 10.

### 4.2 The acceptance condition
At every step N, the world state must correctly reflect choices 1 through N−1. A character who did not
learn a fact at step 4 must still not know it at step N for all N > 4, unless they learned it at some
step in between. This holds at whatever depth a given run reaches; it is not a property of the number
10 specifically. This is the acceptance condition for the whole build (§8).

### 4.3 What "characters react in real time" means (SD-11), stated exactly
**In scope:** on every turn, each of the 5 cast members re-evaluates their own state — knowledge,
disposition, and goals — against the changed world, and the generated scene reflects those updated
states. A character's reaction to a choice made at step 3 can surface at step 7.

**Not in scope:** characters acting continuously or autonomously *within* a scene, background simulation
between turns, or any character taking action while the player is not making a choice. The loop is
strictly turn-based (§4, steps 2–7). "Real time" here means *responsive to current state on every turn*,
never *concurrent* or *always-running*.

### 4.4 How it is built (SD-16) — uniform data model, single-call runtime
Two separable concerns, decided independently:

**Data model — uniform, non-negotiable.** Every character has an *identical* state structure: a
knowledge set over the shared world state, plus traits and goals. There is **no player-character /
non-player-character distinction anywhere in storage.** Character state is never stored as narrative
text — text cannot be diffed, filtered, or replayed from another character's view.

**Runtime — one narration call per turn.** Character state transitions are computed **deterministically
in code**, not by a model. One LLM call then renders the scene. It receives the acting character's
filtered view, plus *derived directives* for the other characters —
e.g. `Debra — does not know: <fact>. Suspicion 2/5. Deflects if asked about <topic>.`

**Critical distinction:** those derived directives are computed **at render time** and are never a
stored asymmetry. Storing rich state for one character and thin directives for the others would
hardcode a hierarchy and make §7.2 S3 (Infinite Story Universe) a rewrite rather than a parameter change.

**Why this runtime and not per-character agents:** the epistemic guarantee comes from *what is absent
from the assembled context*, not from instructing a model to withhold. A fact that was never placed in
the prompt cannot leak. This is simultaneously cheaper (1 call/turn vs ~6) and structurally stronger
than prompting a model to respect five knowledge boundaries at once.

**Consequences that must hold:**
1. All 5 characters share one state schema — no special-casing the protagonist.
2. Knowledge is stored as per-character sets over one world state, never as per-character prose.
3. The renderer takes a character as a **parameter**, never a constant.

**Upgrade path (not in scope, but preserved):** replacing the single narration call with one agent per
character is a *runtime* change only. It requires no data migration, because the data model above
already supports it.

---

## 5. Key Concepts (glossary — these terms are used precisely throughout)

### 5.1 Canon Kernel
The knowledge base holding the story's facts. Every fact carries **provenance**: the exact source it was
extracted from, so any claim can be traced back and cited. Pre-existing research asset; architecture in
`research/Pocket FM Hack/Pocket-FM-Hackathon/Knowledge-Base/09 - Proposed Architecture.md` and
`PRD-KNOWLEDGE-BASE.md`.

### 5.2 Branch Oracle
The mechanism that supplies choices. Scraped fan-fiction is mined for divergence points and the
alternate paths taken from them; these become the 2–4 options presented at each decision point.

**Definitional constraint:** fan-fiction supplies *what the options are*. It is **not** quoted, reproduced,
or used as generated prose. It is a source of branch structure only.

### 5.3 Epistemic State (per-character knowledge)
**Definition:** a fact can be *true in the world* while being *unknown to a character*. These are two
different things and the system tracks them separately.

**Mechanism:** one world state, plus N filtered views — one per character. Every fact records who
witnessed it, who was told it, and who could reasonably infer it. When assembling context for a
character, the system retrieves **what that character is entitled to know**, not what is topically
relevant.

**Two failures this prevents:**
- *Spoiler leak* — the audience learns something the story has not revealed.
- *Broken characterization* — a character acts on knowledge they never earned.

**Why it is a MUST and not an optimization:** the player *inhabits* a character, so whatever the system
shows the player is what the player can act on. Without filtering, the player is handed either a spoiler
or an unearned advantage. Additionally, this must be designed into the data model from the start —
retrofitting "who witnessed this" onto already-extracted facts requires re-extracting everything.

### 5.4 The Receipt
The consistency claim made on stage, stated exactly: **"Every fact is checked, and we show you the
receipt."** Concretely: when the system asserts or rejects something, it can display the canon fact it
checked against and the source location that fact came from. The citation path is a hard requirement,
not a nice-to-have.

### 5.5 Intentional divergence vs. accidental contradiction
The system must distinguish:
- **Intentional divergence** — a consequence of a choice the player made. Expected. Not an error.
- **Accidental contradiction** — drift nobody chose. An error, and what the verifier flags.

A verifier that flags every divergence as an error is useless for this product, because deliberately
breaking canon is the entire point of the genre.

---

## 6. Corpus

### 6.1 Source work
**Dexter**, the novel series by Jeff Lindsay.

### 6.2 Why this work specifically
1. **Novels exist** — real prose to extract from, so facts have genuine provenance rather than being
   hand-authored props.
2. **Novels have endings** — a known destination makes it measurable whether a branch converged,
   diverged, or broke.
3. **Deep character interiority** — first-person narration means the prose is saturated with extractable
   character state.
4. **Dense fan-fiction coverage** — the branch oracle has material to mine.
5. **The decisive reason: the story's central engine is who-knows-what.** The series runs on one secret
   and the shifting set of people who suspect it. This makes epistemic state — the hardest thing we are
   building — *the thing the audience is already watching*, rather than invisible plumbing. In any other
   story, "this character doesn't know yet" is a footnote. Here it is the plot.

### 6.3 Cast (fixed, small, deliberate)
**Five characters maximum.** Dexter, Debra, Doakes, LaGuerta, Rita.

"Every character has persistent memory" is a roadmap claim. "The five that carry the story have
persistent memory" is the build. The audience will not feel the difference.

⚠ **Exact character names, roles, and relationships must be confirmed against the novels during
ingestion** — novel and screen versions differ in detail. Do not encode character facts from memory.

### 6.4 Known corpus hazard — OPEN, see OD-2
Dexter has **two canons that diverge**: the novels and the television series. Our knowledge base is
built from **novels**. Fan-fiction for Dexter is predominantly **screen**-based. The branch oracle may
therefore propose choices referencing events, characters, or arcs that our canon has never heard of.
This is a silent corruption path and must be resolved deliberately. See §11 OD-2.

---

## 7. Scope

### 7.1 MUST — the build
| # | Item | Definition of done |
|---|---|---|
| M1 | Knowledge base extracted from the Dexter novels | Facts stored with provenance sufficient to produce a citation |
| M2 | Character selection | Player can select any of the 5 cast members (§6.3) |
| M3 | Choice-based playthrough, text | Up to 10 sequential choices; 2–4 options per decision point |
| M4 | Choices sourced from fan-fiction | Options originate from the branch oracle (§5.2), not hand-authored |
| M5 | Per-character epistemic memory | One world state, 5 filtered views; a character cannot act on unwitnessed facts |
| M6 | Characters react to the diverged world | Characters respond to state changes caused by choices, **as defined in §4.3** (per-turn re-evaluation, turn-based, not concurrent) |
| M8 | Uniform character state schema | All 5 characters share one identical state structure; renderer takes a character as a parameter. **As defined in §4.4.** Enables S3 at near-zero cost. |
| M7 | Consistency enforced with citations | The receipt (§5.4) can be displayed for a checked claim |

### 7.2 SHOULD — only after every MUST item works end to end
| # | Item | Note |
|---|---|---|
| S1 | Audio narration via ElevenLabs | Text first, then swap. Chosen for integration ease. |
| S2 | Ripple visualization | Shows **the cast and what each character now believes** — not abstract fact-nodes. Character-state ripple is more legible on a projector and uses the same underlying data. |
| S3 | **Infinite Story Universe — replay as another character** | Re-render the same completed branch from a different character's epistemic view (see §8.1). The *mechanism* is free given M8; only the UI toggle is work. This is the second hackathon statement (§1.5) and the strongest single demo beat available. |

### 7.3 OUT — pitch slides only, do not build
- Creator surface (posting own stories, exploring branches of them)
- Free-form input — player saying or typing what they do instead of selecting. **Long-term direction,
  explicitly not this build.** Bounded choices allow validating a branch *before* showing it; free text
  forces generate-then-verify, where failures are visible to the audience.
- Endlessly adapting universes / multi-novel support
- Plot Hole Hunter / creator QA surface
- Any account, save, share, or social feature

---

## 8. What Proves the Demo

**The proof is not a good alternate scene.** Any team can generate one.

The proof is **compounding state under epistemic constraint**: at the final step of a run, the world
correctly reflects every prior choice, and a character who did not learn something at step 4 still does
not know it. This is precisely what breaks in every competing system, and it is what a judge will
remember.

The demo must therefore reach meaningful depth — **a rehearsed run of at least 5 choices**. A
single-flip demo does not demonstrate the claim, because a single flip cannot show compounding.

### 8.1 The closing beat — replay as another character (S3)
After the playthrough, re-render the **same branch, same events** from a different character's view —
e.g. as Debra instead of Dexter. She visibly does not know things the audience just watched happen.

This single toggle proves **both** headline claims at once:
- **Per-character epistemic state** (M5) — the missing knowledge is visible, not asserted
- **Infinite Story Universe** (§1.5) — a side character becomes the protagonist without breaking continuity

It is also the most legible possible demonstration on a projector: there is no graph to explain. The
judge watches the same scene twice and *feels* the difference. Given M8, the mechanism costs nothing
beyond the renderer already being built — only the toggle is work.

---

## 9. External Dependencies

| ID | Dependency | Owner | Status |
|---|---|---|---|
| **EXT-1** | Fan-fiction / corpus scraper and ingestion | A **parallel session**, not this repo | Output contract **UNDEFINED**. This is the highest-risk integration in the project. Fill this section on merge. |
| **EXT-2** | ElevenLabs (audio, SHOULD tier) | This repo | Not started |

**EXT-1 contract — to be completed on merge. Do not assume any of these:**
- [ ] What it emits: raw text / extracted facts / structured choice objects — **unknown**
- [ ] Which canon it scrapes: novel-based or screen-based fan-fiction — **unknown, see OD-2**
- [ ] Delivery mechanism: files, database, API — **unknown**
- [ ] Whether it links fan-fic divergences back to specific canon moments — **unknown**

---

## 10. Settled Decisions

Each of these is closed. Reopening one requires editing this file.

| ID | Decision | Settled as |
|---|---|---|
| SD-1 | Track / problem statement | P1 — Story Time Machine + Infinite Story Universe |
| SD-2 | Hero interaction | Choice-based playthrough, up to 10 choices — **not** a single flip |
| SD-3 | Input mode (this build) | Bounded choices only, 2–4 per decision point. No free text. |
| SD-4 | Primary user | The Player. Creator is a slide. |
| SD-5 | Corpus | Dexter novels (Jeff Lindsay) |
| SD-6 | Cast size | 5 characters maximum |
| SD-7 | Per-character epistemic state | **MUST** — in the data model from the start |
| SD-8 | Consistency claim | "Every fact is checked, and we show you the receipt" — citations required |
| SD-9 | Source of choices | Scraped fan-fiction (branch oracle), not hand-authored, not freely invented |
| SD-10 | Modality | Text first; ElevenLabs audio is SHOULD tier |
| SD-11 | Characters act in real time | Yes, in the specific sense defined in **§4.3** — per-turn state re-evaluation, not continuous or concurrent simulation |
| SD-12 | Demo depth | Ceiling 10 choices, rehearsed run ≥ 5 (§4.1, §8) |
| SD-13 | IP posture | Commercial IP is acceptable — hackathon artifact, not a shipped product. Not revisited. |
| SD-14 | Runway | 24–36 hours, 2–4 people |
| SD-15 | Substrate | This repo — Python 3.12, hexagonal, SQLModel/SQLite (per `.claude/rules/structure.md`) |
| SD-16 | Character reaction architecture | **Uniform per-character data model + single narration call per turn** (§4.4). State transitions deterministic in code; no PC/NPC asymmetry in storage; renderer takes a character as a parameter. Per-character agents rejected for this build as ~6× cost with no epistemic gain — the guarantee comes from context assembly, not from model instruction. |
| SD-17 | Infinite Story Universe | In scope as **SHOULD (S3)** — replay a completed branch as another character (§8.1). Promoted from pitch-only because M8 makes the mechanism nearly free. |

---

## 11. Open Items

Every unknown in this project is listed here. If something is not in this table, it is settled.

| ID | Question | Blocks | Owner | Recommendation | Needed by |
|---|---|---|---|---|---|
| **OD-1** | Fork vs. tier for base-canon-vs-branch. Does a branch inherit canon and shadow invalidated facts (fork), or is base canon authoritative and branch facts subordinate (tier)? | Data model, retrieval resolution, verifier semantics | This repo | **Fork.** Tier structurally mislabels every deliberate divergence as an error, which is fatal for this genre. Recorded as the working assumption; confirm before storage is written. | Before storage layer is built |
| **OD-2** | Novel canon vs. screen canon mismatch (§6.4). Our KB is novel-based; fan-fiction is largely screen-based. | Branch oracle validity, EXT-1 scraper targeting | This repo + parallel scraper session | Restrict the branch oracle to fan-fiction consistent with novel canon, **or** accept screen canon as the base and change §6.1. Decide, do not discover. | Before EXT-1 merge |
| **OD-3** | EXT-1 output contract (§9) | Everything downstream of ingestion | Parallel session | — must be obtained, not guessed | Immediately |
| **OD-4** | Sparse fan-fiction coverage. Fan-fics cluster at famous divergence points, not evenly. Behaviour when a chosen moment has thin coverage is undefined. | Choice generation at arbitrary moments | This repo | For the demo, restrict to densely covered moments. Define a degradation path (LLM-generate a candidate branch, or restrict selectable moments) before claiming "any moment". | Before demo script is fixed |
| **OD-5** | Product name. "CANON: Time Machine" is inherited from the prior PRD and no longer describes the product. | Pitch, UI chrome | Team | — | Before pitch |
| **OD-6** | Judging rubric | Pitch emphasis, what to over-invest in | Unknown — event has not published it | Flag as unverified; do not optimise for a guessed rubric | — |

---

## 12. Supersessions

Documents in this repo that this file overrides. Listed so no one builds from a stale source.

| Superseded | What changed |
|---|---|
| **"CANON: Time Machine" PRD** (friend-authored) | Its hero interaction — *flip one decision, read the result* — is replaced by a 10-choice playthrough (SD-2). Its listener-only framing, its Ripple Map as abstract fact-graph (now character-belief ripple, S2), its original-story corpus, and its §11 out-of-scope ban on commercial IP (SD-13) are all superseded. Its component inventory and data-contract discipline remain useful reference. |
| **`_PROBLEM VERDICT (evidence-selected).md`** | Its conclusion "build for the creator/producer, not the passive listener" is **overridden**. The Player is the primary user (SD-4). Its engine thesis — verifier over generator — is retained and remains correct. |
| **`PRD-KNOWLEDGE-BASE.md`** | OD-2 in that document ("producer or takeover player") is now settled as **player** (SD-4). Its A-4 assumption (public-domain corpus) is superseded by SD-5/SD-13. Its OD-6 ("bounded options or free prose") is settled as **bounded** (SD-3). Its remaining architecture, data model, and knowledge-model sections stand. |
| **`CLAUDE.md`** — `Problem statement: TODO` | Closed by §1.4 of this file. Closes feature **INIT-01**. |

---

## 13. Non-Goals

Restated in one place so they are never re-litigated mid-build:

- Generating prose quality beyond what consistency requires
- Multilingual support
- Auto-repair of flagged contradictions (flag only)
- Guaranteeing *soft* consistency — tone, motivation, prose quality. The system enforces **hard**
  continuity (facts, state, knowledge) and does not claim otherwise.
- Any persistence beyond the demo session
- Real Pocket FM catalog integration
