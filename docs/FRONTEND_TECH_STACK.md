
# FRONTEND TECH STACK — Agent Build Spec
### Written for the coding agent (Claude Code), not for a human to manually implement. Follow directives below in order. Read alongside [[REQUIREMENTS]] before writing any code.

> [!danger] READ THIS FIRST
> You (the agent) are building this end to end. The humans on this team are doing product/design decisions and pitch prep — you own implementation. Every rule below is a constraint, not a suggestion. Where a rule says NEVER, that is not a style preference, it's a scope/time/aesthetic guardrail for a 36-hour build with one shot on stage.

---

## 0. Framework: Next.js — locked, do not reconsider

**Use Next.js (App Router, TypeScript, `src/` directory).** This is decided; do not re-litigate SSR vs. SPA tradeoffs mid-build.

Build constraints specific to Next.js on this project:
- **The entire demo lives on ONE route (`app/page.tsx`).** Do NOT create separate pages/routes per screen (no `/shelf`, `/timeline`, `/ripple`, etc.). The five screens (Shelf → Timeline → Divergence → Ripple → Output) are **views inside one page, switched by client state** (Zustand), so Framer Motion transitions carry across screen changes without a full navigation/page-load event breaking the animation continuity. This is the one place a "normal" Next.js instinct (file-based routes per page) would actively hurt this build — don't do it.
- **Every interactive component needs `"use client"`.** Anything touching Framer Motion, Zustand, Howler, or browser APIs must be a Client Component. Default to client components for everything under `components/` and `screens/`; only the root layout stays a Server Component.
- **Use Next.js Route Handlers as a thin proxy to the Python backend** (`app/api/[...path]/route.ts` forwarding to the Canon Kernel service). This kills CORS entirely and keeps one dev server (`npm run dev`) running for the whole stack instead of two origins to juggle on stage.
- **Use `next/font/google` for Fraunces and Geist, `next/font/local` for JetBrains Mono if self-hosting.** This is a genuine Next.js win here — automatic font optimization and zero flash-of-unstyled-text, which matters for a polished on-stage feel.

---

## 1. Full stack — implement exactly this, do not substitute

| Layer | Use | Do NOT use |
|---|---|---|
| Framework | Next.js 14+, App Router, TypeScript | Pages Router, separate routes per screen |
| Styling | Tailwind CSS | Inline styles, styled-components, CSS modules scattered per file |
| Components | shadcn/ui (code copied into repo via CLI, then restyled) | MUI, Chakra, Ant Design — their default look is instantly recognizable and works against §3 |
| Animation | Framer Motion | CSS-only animations for anything state-driven (FLIP, Ripple cascade) |
| Ripple Map | **Hand-authored SVG + Framer Motion** (§4) | react-flow / react-force-graph / any physics-based graph library as the primary path |
| Charts/counters | Hand-built SVG + Framer Motion; `visx` only if genuinely needed | Recharts, Chart.js, ApexCharts — default styling reads as generic dashboard |
| State | Zustand (single store, `store/demoStore.ts`) | Redux, Context-API-as-global-store for this scope |
| Data fetching | TanStack Query, hitting `/api/*` route handlers | Raw `fetch` scattered across components without loading/error handling |
| Audio | Howler.js | Raw `<audio>` tag, wavesurfer.js default skin |
| Icons | Lucide | Font Awesome, emoji-as-icon |
| Fonts | Fraunces (serif/story) + Geist (sans/UI) + JetBrains Mono (data/proof) — via `next/font` | Inter as the only or primary font |

---

## 2. Visual constraints — enforce these as hard rules, not aesthetic taste

> [!danger] NEVER produce any of the following. If a generated component includes one of these, revise it before moving on.
> - Purple-to-blue gradient backgrounds or hero blobs
> - Glassmorphism (heavy `backdrop-blur` + translucent white/gray cards)
> - Glowing borders that pulse or animate on hover, on more than the two designated interaction moments
> - `rounded-2xl` + `shadow-lg` applied to every card/button by default — vary corner radius and elevation deliberately, don't template it
> - Any 3D "AI orb" / abstract blob render as decoration
> - Emoji used as functional icons (Lucide only)

**Positive constraints (build to these instead):**
- Dark near-black base surface, **one** accent color, plus red/green/blue reserved **exclusively** for verifier and Ripple Map states — never reuse those three decoratively elsewhere in the UI.
- Real depth via soft low-opacity shadow + a subtle grain/noise overlay on dark surfaces (a CSS `background-image` noise texture at ~3-5% opacity), not blur-glow.
- Motion is calm everywhere except two moments: the FLIP action and the Ripple Map cascade. Everything else (hovers, page-idle states) should be near-static or very subtle.
- Three-font system enforced by role, not mixed: Fraunces for story/headline text, Geist for UI chrome/buttons/labels, JetBrains Mono for any data/citation/fact-count/verifier-output text. Mono appearing on the "proof" moments is intentional — it signals system-truth vs. narrative-prose visually.
- Generous whitespace; don't fill every pixel of a screen with a card or panel.

---

## 3. The Ripple Map — implementation directive

**Do not implement this with a graph library.** The dataset is small, fixed, and known in advance (one pre-authored story, a handful of facts) — there is no need for force-directed physics layout, and a physics sim will look janky compared to a hand-authored animation.

**Build it as:**
1. A fixed SVG layout — node positions authored directly in the component (or computed once from the seed data, then frozen), not recalculated by a simulation.
2. Node and edge rendering as SVG circles/paths.
3. Cascade animation via Framer Motion `AnimatePresence` + staggered `variants`: red nodes darken in sequence, green nodes hold steady, blue nodes fade in — staggered over ~2–3 seconds.
4. Counters (`23 invalidated · 118 hold · 4 new`) count up in sync with the animation using a simple animated-number hook, not appear instantly.

Only fall back to a skinned `react-flow` instance if a second, less-rehearsed story needs to be demoed live and the fixed-layout approach doesn't generalize in time — and if so, strip its default background grid/handles and restyle nodes to match the type/color system in §2.

---

## 4. Audio implementation directive

- Howler.js: one looping low-volume ambient bed instance, three one-shot cues (select / commit-flip / invalidate-tick), one narration track instance.
- Do not implement real waveform analysis/rendering. If a "the system is speaking" visual is needed during narration, build a 4–6 bar animated equalizer with Framer Motion driven by a canned animation loop synced to playback state (`isPlaying` boolean), not real audio-frequency analysis — faster to build, looks equally intentional.
- Exactly three one-shot cues + one ambient bed. Do not add more sound cues than this list.

---

## 5. Data contract — build against this from the first commit

Do not wait on the real backend. Implement `lib/mockData.ts` matching this shape immediately, wire all UI to it, and only swap the TanStack Query fetchers to hit `/api/*` once the backend confirms this contract is stable.

```
GET  /api/stories
     → [{ id, title, coverUrl, episodeCount }]

GET  /api/stories/{id}
     → { id, title, episodes: [{ id, title, characters: [charId] }],
         characters: [{ id, name, portraitUrl }] }

GET  /api/stories/{id}/moments?episodeId=&characterId=
     → [{ momentId, originalLine, alternatives: [{ altId, label }] }]

POST /api/divergence
     body: { storyId, momentId, altId }
     → { rippleId, invalidated: [{factId, summary}],
         held: [{factId, summary}], newNeeded: [{factId, summary}] }

POST /api/regenerate
     body: { rippleId }
     → { sceneText, verifier: { status: "ok"|"flagged",
         citation?: { draftClaim, canonFact, episodeRef } } }

POST /api/narrate            (build only after everything above works)
     body: { sceneText }
     → { audioUrl, imageUrls: [url, url] }

POST /api/demo/defect         (planted-defect proof)
     → { sceneText, verifier: { status: "flagged", citation } }
```

Route Handlers under `app/api/` should proxy each of these to the actual Python service — do not implement business logic in the Route Handler itself, it's a pass-through only.

---

## 6. Build order (execute in this sequence, don't skip ahead)

1. Scaffold project (§8 commands), install everything, confirm dev server runs.
2. Implement `lib/mockData.ts` + `lib/tokens.ts` (colors, fonts, motion durations as named constants) + `store/demoStore.ts`.
3. Build Screens 1→4 (Shelf, Timeline, Divergence, Ripple Map) fully wired to mock data. These require zero backend and should look complete on their own.
4. Build Screen 5 (Output) + `VerifierBadge` + `DefectDemoTrigger` against mock data.
5. Build Route Handlers proxying to the real backend; swap fetchers from mock to live one endpoint at a time, verifying each still renders correctly.
6. Add Presenter Mode last — it's a wrapper/toggle over what already exists, not new screens.
7. Only after 1–6 are solid and stable: attempt narration/audio (§4) and the second story, per REQUIREMENTS §4 SHOULD-tier.

---

## 7. Folder structure

```
frontend/
  src/
    app/
      page.tsx              ← the single route; renders current screen from store state
      layout.tsx             ← root layout, font loading via next/font
      api/
        [...path]/route.ts   ← proxy to Python backend
    components/
      StoryCard.tsx
      TimelineTrack.tsx
      CharacterPortrait.tsx
      MomentCard.tsx
      RippleGraph.tsx         ← highest-effort component, see §3
      VerifierBadge.tsx
      SceneOutputPanel.tsx
      PresenterModeToggle.tsx
      DefectDemoTrigger.tsx
    screens/
      Shelf.tsx  Timeline.tsx  Divergence.tsx  Ripple.tsx  Output.tsx
    lib/
      api.ts                  ← TanStack Query hooks, one file
      mockData.ts
      audio.ts                ← Howler setup + cue triggers
      tokens.ts               ← design tokens as code — single source of truth
    store/
      demoStore.ts
  CLAUDE.md                   ← this file's contents + link to REQUIREMENTS, kept in repo root
```

---

## 8. Scaffold commands — execute verbatim

```bash
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir --no-eslint
cd frontend
npm install framer-motion zustand @tanstack/react-query howler lucide-react @fontsource/jetbrains-mono
npx shadcn@latest init
```

Fraunces and Geist: load via `next/font/google` in `app/layout.tsx` (no separate install needed). JetBrains Mono: self-hosted via `@fontsource/jetbrains-mono` if `next/font/google` coverage is inconsistent for it, otherwise also via `next/font/google`.

---

## 9. Pre-demo QA checklist — verify all before declaring done

> [!todo]
> - [ ] Single route, screen transitions are state-driven, not page navigations
> - [ ] No gradient/glassmorphism/glow-hover violations anywhere (§2)
> - [ ] Red/green/blue appear ONLY on verifier + Ripple Map states
> - [ ] Three fonts used consistently by role, nowhere mixed arbitrarily
> - [ ] Ripple Map is the hand-authored version, not a raw graph-library default
> - [ ] All five MUST screens work fully on mock data with zero backend running
> - [ ] Route Handlers proxy correctly with the real backend, no CORS errors
> - [ ] Presenter Mode hides all debug/console/URL chrome
> - [ ] Tested at projector-scale contrast, not just on a laptop screen in a dim room

---

## 🔗 Related
[[REQUIREMENTS]] · [[DECISION — Problem Statement Analysis]] · [[09 - Proposed Architecture]]

---
*Rewritten 2026-07-25 as an agent-executable build spec. Give this file directly to Claude Code as its operating instructions for the frontend, alongside REQUIREMENTS.md.*
