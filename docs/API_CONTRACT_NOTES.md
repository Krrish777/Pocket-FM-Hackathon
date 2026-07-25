# API CONTRACT NOTES — frontend ⇄ Canon Kernel

> **For the backend team.** The frontend is built and working against `frontend/src/lib/mockData.ts`.
> That file is the **real contract** — it is a strict superset of the sketch in `REQUREMENTS.md §8`,
> and you will not match it by accident. Everything below is a difference that will break the UI
> if it is not honoured.
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

This is the single biggest divergence from §8. §8 implies `title: string`. The real shape is:

```ts
type LocalizedText = { hi: string; en: string };   // BOTH keys required, both non-empty
```

This applies to **every** human-readable field: `title`, `logline`, `name`, `role`, `synopsis`,
`originalLine`, alternative `label`, fact `summary`, `sceneText`, `draftClaim`, `canonFact`.

```jsonc
// ✗ what §8 suggests            // ✓ what the frontend needs
{ "title": "The Last Bench" }    { "title": { "hi": "आख़िरी बेंच", "en": "The Last Bench" } }
```

Identifiers (`id`, `factId`, `episodeRef`, `rippleId`) stay plain strings — they are never displayed
as prose.

---

## 2. Endpoint-by-endpoint

### `GET /api/stories`
```ts
{ id, title: LocalizedText, coverUrl, episodeCount, factCount, language: LocalizedText }[]
```
Beyond §8: **`factCount`** and **`language`**. Both render on the shelf card meta line.
`coverUrl` is currently ignored — covers are generated procedurally — but keep the field.

### `GET /api/stories/{id}`
```ts
{ id, title: LocalizedText, logline: LocalizedText,
  episodes:   { id, index: number, title: LocalizedText, synopsis: LocalizedText, characters: string[] }[],
  characters: { id, name: LocalizedText, role: LocalizedText, portraitUrl }[] }
```
Beyond §8: **`logline`**, episode **`index`** and **`synopsis`**, character **`role`**.

**Invariant:** every id in `episodes[].characters` must exist in `characters[]`. The timeline
resolves presence dots from this and will render a character-less episode silently.

### `GET /api/stories/{id}/moments?episodeId=&characterId=`
```ts
{ momentId, episodeId, characterId, originalLine: LocalizedText,
  alternatives: { altId, label: LocalizedText, weight: "low"|"medium"|"high", tone?: "heavy"|"standard" }[] }[]
```
Beyond §8: the response echoes **`episodeId`/`characterId`**, and alternatives carry **`weight`**
and optional **`tone`**.

**An empty array is a valid, expected answer** — most episode/character pairs have no authored
divergence point. The frontend resolves this endpoint for every episode of the selected character up
front, and disables the ones that come back empty, so there is never a dead click. Do not invent a
placeholder moment to avoid returning `[]`.

### `POST /api/divergence`
```ts
// body: { storyId, momentId, altId }
{ rippleId, invalidated: Fact[], held: Fact[], newNeeded: Fact[] }
type Fact = { factId, summary: LocalizedText, establishedIn: string }  // "E02", or "—" for new
```
Beyond §8: **`establishedIn`** on every fact.

**Invariant (enforced by a frontend test):** a `factId` must appear in **exactly one** of the three
arrays. A fact that is both invalidated and held renders as two nodes and makes the counters lie.

### `POST /api/regenerate`
```ts
// body: { rippleId }
{ sceneText: LocalizedText,
  verifier: { status: "ok",      verifiedAgainst: number }
          | { status: "flagged", citation: { draftClaim: LocalizedText,
                                             canonFact:  LocalizedText,
                                             episodeRef: string } } }
```
Beyond §8: **`verifiedAgainst`** on the ok branch.

**Invariant:** `verifiedAgainst` must equal `held.length` from the ripple it was generated against.
The badge renders that number as the evidence for the consistency claim; if it disagrees with the
counter one screen earlier, an attentive judge will catch it.

`sceneText` paragraphs are split on blank lines (`\n\n`). Send real paragraph breaks.

### `POST /api/demo/defect`
Same shape as `/api/regenerate`. Must **always** return `status: "flagged"` with a full citation —
this is the on-stage proof and has to be reproducible on every single click.

### `POST /api/narrate` — **not implemented**
§8 lists it; the mock does not have it and the frontend does not call it. Narration is SHOULD-tier
and was cut. Don't build it until the MUST path is live end to end.

---

## 3. Behavioural expectations

- **Latency is welcome, not a problem.** The mock deliberately delays `divergence` by 1200ms and
  `regenerate` by 1800ms so the cascade feels earned. Anything under ~3s is fine.
- **Determinism matters more than freshness.** Responses are cached by input
  (`staleTime: Infinity`), so the same divergence returns the same ripple for the whole session.
  Do not return a different ripple for identical `{storyId, momentId, altId}` mid-demo.
- **Errors:** non-2xx surfaces as a thrown error; the proxy returns `502` with
  `{ error: "upstream_unreachable" }` when the backend is unreachable. Prefer a proper status code
  over a 200 carrying an error body.

---

## 4. Known gaps on our side (not yours)

- `ALT-B` has no distinct ripple in the mock — `postDivergence` falls through to the `ALT-A` result
  for anything that isn't `ALT-C`. If the real engine computes ALT-B properly, that gap just closes.
- `ST-02` / `ST-03` exist for shelf realism and are non-interactive in the UI.
- Only two moments are authored (`M-0301` at E03/CH-02, `M-0501` at E05/CH-03).

---

*Frontend built 2026-07-25 against `mockData.ts`. If you need to change a shape here, tell the
frontend first — it is a contract change, not an implementation detail.*
