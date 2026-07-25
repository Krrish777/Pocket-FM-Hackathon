# Session Handoff

> The single per-session **clock-out** note. Overwrite at the end of each session. At session start, read
> this first, then `PROGRESS.md` and `DECISIONS.md`. Keep it short.

## Last session — 2026-07-25 (session 5, THE BRIEF LANDED → problem statement selected)

**Framing:** The hackathon brief arrived. This was an **elicitation session, not a build session** — the
objective was to get the product out of the user's head and into a concrete spec. **No product code was
written, by design.** `make check` is GREEN (exit 0, 7 passed).

### The one thing to read next
**`project_context.md`** — the single source of truth for what we are building and why. It declares its own
supersessions (§12) and beats any other doc in this repo, including the friend-authored PRD and
`_PROBLEM VERDICT`. Decision provenance (13 decisions with rejected alternatives + a corrections table):
**`docs/2026-07-25-product-definition-session.md`**.

### The product, in one line
A playable branching layer over the **Dexter novels** — pick a character, play forward through choices mined
from **fan-fiction**, with every character remembering only what they actually learned.
Track: **P1 Story Time Machine + Infinite Story Universe**. Runway: 24–36h, 2–4 people.

### What I did
- **Closed INIT-01.** Established the brief is a *menu* (~40 statements / 6 tracks) — so this was a selection
  and narrowing decision, not a copy-paste. Patched `CLAUDE.md` + `AGENTS.md` (mirror in sync); verification
  command re-run and passing.
- **Resolved the repo's central conflict**: `_PROBLEM VERDICT` said build for the *creator*; the friend's PRD
  built for the *listener*. Settled **Player primary, creator is a slide** — an explicit override of the
  vault's own recommendation, recorded as such so it is not mistaken for an oversight.
- **Wrote `project_context.md`** (13 §): problem, exact core loop, glossary, corpus, MUST/SHOULD/OUT,
  demo proof, 17 settled decisions, 6 open items with owners, supersessions.
- **Wrote the session decision record** in a new top-level `docs/`.
- **Seeded the product phase** in `feature_list.json`: M1–M8 (MUST) + S1–S3 (SHOULD), each with a verification
  command, all `passes:false`.
- **Fixed the gate:** `.claude/worktrees` added to ruff `extend-exclude` — parallel worktrees are separate
  checkouts that run their own `make check`; linting them from the parent failed our gate on their code.

### Ideas established this session that neither prior doc had
1. **Fan-fiction is the branch oracle** — a third path past the dead end where hand-authored branches are
   unaffordable (Until Dawn) and generated branches are incoherent (AI Dungeon). Branches pre-authored by the
   crowd, free, audience-filtered, dense at the moments that matter.
2. **Intentional divergence ≠ accidental contradiction.** Fan-fiction breaks canon *on purpose*; a verifier
   that flags every divergence is useless. This distinction *is* the product.
3. **Protagonist-ness is a rendering choice, not a stored property** — which makes Infinite Story Universe
   nearly free and unlocks the closing demo beat: replay the same branch as Debra, who visibly does not know
   what the audience just watched happen.

### Next step (resume here)
**M8 — the uniform character state schema.** Build it first: it is the only decision expensive to retrofit,
and M5 + S3 both depend on it. Spec: `project_context.md` §4.4. In parallel, chase **OD-3** (the EXT-1 scraper
output contract) — it is the highest-risk unknown and blocks M1/M4.

### Warnings for whoever picks this up
- **The git index is shared across parallel sessions.** I staged 4 files for review; a parallel session then
  committed the entire index as `8d70e1b` "regular updates" (164 files). Staging is not a safe hold — only an
  uncommitted working tree is. Coordinate before staging.
- **Never pipe `make check` into `tail`/`head`** — you get the filter's exit code, and a red gate reads as
  green. It bit me this session. Redirect to a file, check `$?`.
- **OD-2 is a real trap:** our KB is novel-based, Dexter fan-fiction is largely screen-based. Decide it before
  ingesting anything, don't discover it at hour 20.

### State at clock-out
`make check` GREEN (exit 0, 7 passed) · INIT-01…05 + HARDEN-01…04 pass · HARDEN-05 deferred below product work ·
all M/S features `passes:false` · **uncommitted, awaiting the maintainer's permission to commit.**
