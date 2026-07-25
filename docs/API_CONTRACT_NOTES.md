# API CONTRACT NOTES — frontend ⇄ Canon Kernel

> **For the backend team.** ⚠ **BREAKING CHANGE (2026-07-26).** The frontend was retargeted from the
> superseded single-flip "college story" build to match `project_context.md` — the actual product spec
> (Dexter novels, 5-character epistemic memory, a compounding turn-based playthrough, replay-as-another-
> character). Nothing below is a small diff on the old contract; treat this as the contract, full stop.
> The frontend is built and working against `frontend/src/lib/mockData.ts` — that file is the real
> contract for **shapes**. It is **not** ground truth for **content**: the Dexter character facts and the
> whole 5-turn run are hand-authored, generic, unverified mock data (see the file's header comment),
> not extracted from the real novels.
>
> Swapping the frontend onto live data is one env flag (`NEXT_PUBLIC_USE_MOCK=false`) once these match.

---

## 0. How the swap works

```
browser → /api/*  (Next Route Handler, pass-through proxy)  → BACKEND_URL/api/*
```

- The proxy lives at `frontend/src/app/api/[...path]/route.ts`. It forwards method, query string,
  headers and body untouched, and adds **no** business logic. There is no CORS to configure.
- Set `BACKEND_URL` (default `http://localhost:8000`) and `NEXT_PUBLIC_USE_MOCK=false`.
- The client interface both implementations satisfy is `CanonClient` in `frontend/src/lib/api.ts`.
  If your responses satisfy that interface, the UI needs no changes.

---

## 1. ⚠ Every user-facing string is a `LocalizedText`, not a string

Unchanged from before: every human-readable field is `{ hi: string; en: string }`, both keys required and
non-empty. Applies to `name`, `role`, `blurb`, `sceneText`, `beliefSummary`, choice `label`, fact
`summary`, citation `draftClaim`/`canonFact`. Identifiers (`id`, `factId`, `choiceId`, `sourceRef`,
`runId`) stay plain strings — never displayed as prose.

---

## 2. Endpoint-by-endpoint (replaces the old `/api/stories`, `/api/moments`, `/api/divergence`, `/api/regenerate`)

### `GET /api/characters`
```ts
{ id: CharacterId, name: LocalizedText, role: LocalizedText, blurb: LocalizedText, portraitUrl: string }[]
```
**Always the fixed 5, always all 5, always the same order** (`CH-01`…`CH-05` — Dexter, Debra, Doakes,
LaGuerta, Rita). `portraitUrl` is ignored — portraits are procedural — but keep the field.

### `GET /api/runs/{protagonistId}`
```ts
{
  runId: string,
  title: LocalizedText,
  protagonistId: CharacterId,
  turns: Turn[],
}
```
The mock serves the **whole pre-computed run** at once, because it's a rehearsed static dataset. **A real
backend almost certainly computes turns live rather than serving a static array up front** — that's fine,
this endpoint's exact "serve everything now" shape is a mock simplification, not a requirement. What must
match is the shape of each `Turn` and each `CharacterView` inside it (below).

**⚠ The single most important invariant, in bold on purpose:** every `Turn.characterViews` must contain
**all 5** `CharacterId`s, every turn, with **no protagonist special-casing** in storage (project_context.md
§4.4/M8). The whole replay-as-another-character beat (S3) depends on the backend never treating one
character's state as richer or more authoritative than another's. `witnessedBy`/`toldTo`/`inferredBy` on
each `Fact` are what should drive this at the backend's context-assembly step (SD-16) — the frontend only
renders the result, it does not compute who-knows-what.

```ts
type Turn = {
  turnIndex: number,
  actingCharacterId: CharacterId,
  sceneText: LocalizedText,
  verifier: VerifierResult,
  choices: Choice[],           // 2-4, bounded — see below
  chosenChoiceId: string,      // which one the rehearsed run takes
  delta: FactDelta,
  characterViews: Record<CharacterId, CharacterView>,  // ALL 5, always
}

type CharacterView = {
  sceneText: LocalizedText,
  beliefSummary: LocalizedText,
  beliefState: "invalid" | "hold" | "new" | "unaware",
  present: boolean,
  knownFactIds: string[],
  notYetKnown?: LocalizedText[],   // only needed for whichever character(s) get replayed
}

type Choice = {
  choiceId: string,
  label: LocalizedText,
  weight: "low" | "medium" | "high",
  tone?: "heavy" | "standard",
  source: { workTitle: string, author: string, platform: string },  // required, not cosmetic — see below
}

type Fact = {
  factId: string,
  summary: LocalizedText,
  establishedIn: string,       // a real novel/chapter citation once ingestion is real
  witnessedBy: CharacterId[],
  toldTo: CharacterId[],
  inferredBy?: CharacterId[],
}

type FactDelta = { invalidated: Fact[], held: Fact[], newNeeded: Fact[] }
```

**`Choice.source` is required, not decorative.** M4/SD-9: choices must be visibly sourced from fan-fiction,
not invented by the system. The frontend renders `source.workTitle`/`author`/`platform` as a citation line
under every option — a `Choice` without it is a contract violation.

**Invariant (frontend-tested):** a `factId` must appear in **exactly one** of `invalidated`/`held`/
`newNeeded` within a given turn's `delta`. Landing in two makes the belief counters lie.

**Invariant (frontend-tested):** `verifier.verifiedAgainst` (when `status: "ok"`) must equal
`delta.held.length` for that same turn.

### `POST /api/turns/{runId}/{turnIndex}/choice`
```ts
// body: { choiceId }
{ delta: FactDelta, nextTurn: Turn | null }
```
`nextTurn: null` signals this was the run's final turn. (The mock, since it already has the whole run
cached, just returns `{ delta }` for the committed turn and lets the frontend read `nextTurn` out of the
already-fetched `run.turns` — a real backend computing turns live should actually return `nextTurn`.)

### `POST /api/demo/defect`
```ts
{ sceneText: LocalizedText, verifier: VerifierResult }
```
Same shape as before. Must **always** return `status: "flagged"` with a full citation — this is the
on-stage proof and has to be reproducible on every single click.

**Dropped entirely:** `GET /api/stories`, `GET /api/stories/{id}`, `GET /api/stories/{id}/moments`,
`POST /api/divergence`, `POST /api/regenerate`. There is no multi-story browsing and no separate
"compute the ripple" / "regenerate the scene" split anymore — a turn already carries its own scene text,
choices, and delta together. `POST /api/narrate` (§8 of the old REQUREMENTS sketch) was already
not-implemented and stays irrelevant — no separate narration endpoint concept exists in this model either.

### `VerifierResult`
```ts
type VerifierResult =
  | { status: "ok", verifiedAgainst: number }
  | { status: "flagged", citation: { draftClaim: LocalizedText, canonFact: LocalizedText, sourceRef: string } }
```
**Field rename:** `episodeRef` → `sourceRef`. **Format change:** the expected string is no longer an
episode/scene id (`"E03 §4"`); it's a citation — either `"Turn N"` (something this playthrough itself
established) or, once real ingestion exists, an actual novel chapter/page citation. This applies to the
Canon Kernel's real citation format too, not just frontend display.

---

## 3. Behavioural expectations (unchanged in spirit)

- **Latency is welcome, not a problem.** The mock delays the choice-commit response ~1200ms so the belief
  cascade feels earned. Anything under ~3s is fine.
- **Determinism matters more than freshness.** Cache by input key (`runId`, `turnIndex`, `choiceId`) —
  `staleTime: Infinity` on the frontend. The same input must return the same result for the whole session.
- **Errors:** non-2xx surfaces as a thrown error; the proxy returns `502` with
  `{ error: "upstream_unreachable" }` when the backend is unreachable.

---

## 4. Known gaps on our side (not yours)

- Only `CH-01` (Dexter) has a fully authored, playable run. The other 4 characters are selectable in the
  UI but present-as-inert — same pattern as the old build's non-playable shelf cards. `GET /api/runs/{id}`
  for anything other than `CH-01` is never actually called by the current UI.
- Only choice `"-A"` at each turn has fully distinct downstream content in the mock; the other 1-3 options
  per turn have real labels + real `source` attributions but no distinct branch computed. If the real
  engine computes every option properly, that gap just closes.
- `notYetKnown` is populated only for Debra (`CH-02`), the one character the frontend currently wires up
  for the S3 replay beat.

---

*Retargeted 2026-07-26 against the new `frontend/src/lib/mockData.ts`. If you need to change a shape here,
tell the frontend first — it is a contract change, not an implementation detail.*
