# Session Record — Product Definition

> **Date:** 2026-07-25 · **Branch:** `main` · **Type:** elicitation / product definition (no code written)
> **Deliverable:** `project_context.md` at repo root
> **Purpose of this file:** a durable record of *what was decided and why* during this session, so that
> whoever merges this branch inherits the reasoning and not just the conclusions. Rejected alternatives
> are recorded deliberately — a decision without its discarded options is not reviewable.

---

## 1. Session objective

Not a build session. The goal was to **extract a concrete problem statement** from the user's head and
land it as `project_context.md`.

Entering the session the repo had `Problem statement: TODO` in `CLAUDE.md` and feature `INIT-01` blocked
on it. Two *conflicting* candidate problem statements already existed in the repo (see §3), neither of
which reflected what the user actually wanted to build.

Process used: the `superpowers:brainstorming` skill — explore context → clarifying questions one at a
time → present design → approval → write spec.

---

## 2. Starting state

| Artifact | What it was | Status after this session |
|---|---|---|
| `_PROBLEM STATEMENT (official).md` | The real hackathon brief — 6 tracks (P1–P6), ~40 statements | Confirmed authoritative; used to select the track |
| `_PROBLEM VERDICT (evidence-selected).md` | Three demand sweeps concluding "build a verifier, for creators" | **Partially overridden** (see D-4) |
| `PRD-KNOWLEDGE-BASE.md` | 739-line Canon Kernel PRD from a prior session, with 6 open decisions | Several open decisions now closed |
| "CANON: Time Machine" PRD | Friend-authored build spec, listener-facing, single-flip interaction | **Superseded** (see D-3) |
| `feature_list.json` | `INIT-01` failing | Ready to close once `CLAUDE.md` is patched |

---

## 3. The central conflict found at the start

The repo contained two incompatible answers to "who is this for":

- **`_PROBLEM VERDICT`** concluded, in bold, *"Build for the creator/producer, not the passive
  listener"* — on evidence that passive listeners express continuity pain as a Tier-5 grumble while
  creators and interactive-AI users show Tier-1 costly behaviour (paid subscriptions, paid editors).
- **The friend's PRD** built a listener-facing consumer product and demoted the creator tool to a
  roadmap slide.

Both agreed on the engine (verifier / auditable story-state). They disagreed on the buyer. Nobody had
resolved it, and `_PROBLEM VERDICT` itself left it open: *"which face of it we build/demo, and who the
buyer is."*

**This session resolved it — against the vault's own recommendation.** See D-4.

---

## 4. Decisions

Each decision records what was chosen, why, and what was rejected.

### D-1 — Root problem is *participation*, not continuity
**Decided:** the problem being solved is that serialized fiction is passive by construction — the
audience cannot participate. Continuity/consistency is the *enabling constraint*, not the problem.

**Why:** user's framing, verbatim — *"the current stories are just aesthetic. I can't participate in
that."* Everything else in the product is downstream of this.

**Rejected:** framing the problem as continuity failure (the vault's framing). Continuity is what makes
participation *possible at scale*; it is not what a user wants. Leading with it produces a developer
tool, not a product.

---

### D-2 — Fan-fiction is the branch oracle
**Decided:** scraped fan-fiction supplies the *choices* presented at each decision point. It is a source
of branch structure only — not quoted, reproduced, or used as generated prose.

**Why — this is the load-bearing idea of the project.** Interactive fiction has failed exactly twice:
hand-authored branches (Until Dawn, Bandersnatch) are coherent but the authoring cost explodes
combinatorially; fully generated branches (AI Dungeon, ~1.5M → ~350K users) are affordable but
incoherent. Fan-fiction is a **third path**: branches pre-authored by the crowd, for free, already
filtered by audience response, and dense precisely at the emotionally significant moments. The AI's job
becomes *selection and enforcement* rather than invention.

Origin: the user's own remark — *"I don't know where this branch needs to go, so those things can help
me."*

**Rejected:** hand-authoring branches (does not scale, and is what killed the format commercially);
free LLM generation of branches (the coherence wall; documented graveyard).

---

### D-3 — Hero interaction is a *playthrough*, not a single flip
**Decided:** up to 10 sequential, compounding choices — Until Dawn style. Ceiling 10, rehearsed demo run
≥ 5.

**Why:** the claim being made is that state compounds correctly. A single flip cannot demonstrate
compounding, and compounding under constraint is exactly what breaks in competing systems.

**Rejected:** the friend's PRD core loop (pick a moment → flip one decision → read the regenerated
scene). Directionally right, but it is a diff viewer rather than a game, and it cannot show the thing
that actually differentiates the system.

**Note:** the user initially selected "flip one decision" from an options list, then described an Until
Dawn-style playthrough in a subsequent free-form ramble. The ramble was taken as the truer signal and
the earlier selection was explicitly revised.

---

### D-4 — Primary user is the Player; creator is a slide
**Decided:** the single player is the primary and only user served by the MUST scope. The creator
surface (post your own story, explore its branches) is pitch-only, not built.

**Why:** the user chose participation as the root problem (D-1), and the player is who experiences it.
With 24–36 hours and 2–4 people, one hero surface is the maximum that can be built properly.

**Rejected:** `_PROBLEM VERDICT`'s creator-first recommendation. Its *evidence* is not disputed —
creators do show the costly behaviour — but the hackathon artifact is judged on demonstrated concept,
not on revenue proximity. **This override is recorded explicitly so it is not mistaken for an oversight.**

---

### D-5 — Corpus is the Dexter novels
**Decided:** Dexter (Jeff Lindsay novel series).

**Why:** four ordinary reasons — real prose to extract from (so facts have genuine provenance rather
than being hand-authored props), novels have endings (a known destination makes it measurable whether a
branch converged or broke), deep first-person interiority (prose saturated with extractable character
state), and dense fan-fiction coverage for the branch oracle.

**And one decisive reason:** the series' central engine *is* who-knows-what. It runs on one secret and
the shifting set of people who suspect it. This makes per-character epistemic state — the hardest thing
being built — the thing the audience is already watching, rather than invisible plumbing. In any other
story "this character doesn't know yet" is a footnote; here it is the plot.

**Rejected:** public-domain works (recommended by `PRD-KNOWLEDGE-BASE` A-4 on legal grounds — see D-6);
an original team-authored story (no audience familiarity, small fact base); Avengers as a literal corpus
(no canonical prose to extract from — the films are not text, so the fact base would be fabricated,
which collapses the provenance claim). "Avengers" was raised by the user as shorthand for *a world
people already know*, and Dexter satisfies that while also being text.

**Cast fixed at 5:** Dexter, Debra, Doakes, LaGuerta, Rita. "Every character has persistent memory" is
a roadmap claim; five is the build, and the audience will not feel the difference.

---

### D-6 — Commercial IP is acceptable
**Decided:** no legal constraint on corpus choice.

**Why:** user's ruling — hackathon artifact, not a shipped product. *"We don't have to worry about
legality here because we are working in a hackathon."*

**Note:** the assistant raised two objections to Avengers; only one was legal. The legal objection was
withdrawn on this ruling. The *corpus* objection (films have no ingestible prose) was independent and
was resolved separately by D-5. Recorded so the distinction is not lost.

---

### D-7 — Per-character epistemic state is a MUST
**Decided:** one world state plus N filtered views. Every fact records who witnessed it, who was told,
who could infer it. Context assembly retrieves what a character is *entitled to know*, not what is
topically relevant.

**Why:** takeover makes it unavoidable — whatever the system shows the player is what the player can act
on, so without filtering the player receives either a spoiler or an unearned advantage. It prevents two
distinct failures: *spoiler leak* (audience learns something unrevealed) and *broken characterization*
(a character acts on knowledge never earned). And it must be in the data model from the start;
retrofitting "who witnessed this" onto already-extracted facts means re-extracting everything.

**Rejected:** SHOULD tier (every character sees full world state). Cheaper, but it removes the single
sharpest differentiator, and Dexter was chosen specifically because it makes this visible.

---

### D-8 — Bounded choices now, free-form later
**Decided:** 2–4 discrete options per decision point. No free text in this build.

**Why:** with bounded choices a branch can be validated *before* being shown. Free text forces
generate-then-verify, where failures are visible to the audience. This is the failure mode that killed
AI Dungeon.

**Rejected:** free-form input in this build. It remains the stated long-term direction — the user's
*"in the end I want to say or type what they want to do"* — and is recorded as roadmap, not as a cut.

---

### D-9 — Consistency claim: "Every fact is checked, and we show you the receipt"
**Decided:** the strongest of the three claims offered. Citations are a hard requirement.

**Why:** it is the claim the entire pre-existing research asset was built to support, and the only one a
judge cannot dismiss as vague.

**Consequence:** it forces the fork/tier question (OD-1), because a citation must resolve to *a* canon.
It also forces the distinction between **intentional divergence** (a consequence the player chose —
expected, not an error) and **accidental contradiction** (drift nobody chose — the actual error). A
verifier that flags every divergence is useless for fan-fiction, where breaking canon is the point.

**Rejected:** a narrower ripple-only claim; a soft "consistency at scale" claim.

---

### D-10 — Reaction architecture: uniform data model, single-call runtime
**Decided:** every character has an *identical* state structure (knowledge set over shared world state +
traits + goals). State transitions computed deterministically in code. One LLM call per turn renders the
scene from the acting character's filtered view, with *derived directives* for other characters computed
at render time.

**Why — the epistemic guarantee comes from what is absent from the assembled context, not from
instructing a model to withhold.** A fact never placed in the prompt cannot leak. This is simultaneously
cheaper (1 call/turn vs ~6) and structurally stronger than asking one model to respect five knowledge
boundaries at once. Deterministic code transitions are also unit-testable, which makes the acceptance
condition (§4.2 of `project_context.md`) an actual test rather than a hope.

**Rejected:**
- *One call per turn with all canon and rules in the prompt* — cheapest to write, least trustworthy;
  leaks are invisible until someone catches one.
- *One agent per character per turn* — strongest demo story, ~6× the calls and real orchestration risk.
  Preserved as an upgrade path: it is a **runtime** change requiring no data migration.

**Correction made mid-session:** the assistant initially proposed "derived NPC directives" in a way that
implied a *stored* asymmetry between the protagonist and other characters. That was wrong and was
corrected — see D-11.

---

### D-11 — Protagonist-ness is a rendering choice, not a stored property
**Decided:** no player-character / non-player-character distinction anywhere in storage. Character state
is never stored as narrative text. The renderer takes a character as a **parameter**, never a constant.

**Why:** the project also targets *Infinite Story Universe* ("every side character can become the
protagonist of a new story without breaking continuity"). That is free **only if** every character
carries the same shape of state — then "make Debra the protagonist" is just pointing the renderer at a
different view. Storing rich state for the protagonist and thin directives for everyone else hardcodes a
hierarchy and turns that feature into a rewrite.

**Consequence — the closing demo beat:** after a playthrough, replay the *same branch, same events* as
Debra. She visibly does not know things the audience just watched happen. One toggle proves **both**
headline claims at once — per-character epistemics *and* Infinite Story Universe — with no graph to
explain. Promoted Infinite Story Universe from pitch-only to SHOULD (S3) on this basis.

---

### D-12 — Modality: text first, audio via ElevenLabs
**Decided:** text is the MUST; ElevenLabs narration is SHOULD.

**Why:** user's call, on integration ease. Noted at the time that Pocket FM is an audio company and a
text-only demo has a fit question; the user accepted that and chose text-first sequencing.

---

### D-13 — Ingestion is external
**Decided:** the scraper / corpus ingestion is owned by a **parallel session**, not this repo. Recorded
as dependency EXT-1 with its output contract explicitly **undefined**.

**Why:** user's instruction. Flagged as the highest-risk integration in the project, because everything
downstream of ingestion depends on a shape nobody has written down.

---

## 5. Corrections made during this session

Recorded so the reasoning trail is honest.

| # | What was initially wrong | Correction |
|---|---|---|
| C-1 | Assistant treated the official brief as a single problem statement | It is a *menu* of ~40 statements across 6 tracks; "the problem statement" is a selection + narrowing decision |
| C-2 | Assistant objected to Avengers partly on legal grounds | Withdrawn — hackathon artifact (D-6). The independent corpus objection stood and was resolved by D-5 |
| C-3 | Assistant assumed Avengers had no ingestible text | Wrong — fan-fiction archives and wikis are large prose corpora. Superseded anyway by D-5 |
| C-4 | User selected "flip one decision" from an options list | Revised to a playthrough (D-3) after the user's free-form description contradicted the earlier selection |
| C-5 | Assistant proposed "derived NPC directives" ambiguously | Clarified: fine as render-time computation, fatal as stored asymmetry (D-11) |

---

## 6. Open items carried forward

Full detail in `project_context.md` §11.

| ID | Question | Owner | Recommendation |
|---|---|---|---|
| OD-1 | Fork vs. tier for base-canon-vs-branch | This repo | **Fork** — tier mislabels every deliberate divergence as an error |
| OD-2 | Novel canon vs. screen canon mismatch — KB is novel-based, fan-fiction is largely screen-based | This repo + scraper session | Decide deliberately; this is a silent corruption path |
| OD-3 | EXT-1 scraper output contract | Parallel session | Must be obtained, not guessed |
| OD-4 | Sparse fan-fiction coverage at non-famous moments | This repo | Restrict demo to dense moments; define a degradation path |
| OD-5 | Product name ("CANON: Time Machine" no longer describes it) | Team | — |
| OD-6 | Judging rubric | Unknown | Do not optimise for a guessed rubric |

---

## 7. State of the repo after this session

- **Created:** `project_context.md` (root) — the product spec and single source of truth
- **Created:** this file
- **No code written.** No dependencies added. `make check` unaffected.
- **Not done:** `CLAUDE.md` still contains `Problem statement: TODO`, so `INIT-01` still fails its
  verification. Patching that line to point at `project_context.md` closes it.
- **Nothing staged or committed** — per the maintainer's standing rule that commits require explicit
  permission.

---

## 8. Recommended next steps

1. Patch `CLAUDE.md`'s problem-statement line → closes `INIT-01`.
2. Sync with the parallel scraper session to fill EXT-1's contract (OD-3) — highest-risk unknown.
3. Resolve OD-2 (novel vs. screen canon) before any fan-fiction is ingested.
4. Seed `feature_list.json` with M1–M8 from `project_context.md` §7.1, each with a verification command.
5. Design the character state schema first (D-10, D-11) — it is the one thing that is expensive to
   retrofit.
