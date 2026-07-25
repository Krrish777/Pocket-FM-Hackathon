# Research: Frontend Conventions (next-shadcn-dashboard-starter + 2025 Next.js/React/TS)

> **Provenance:** Web research by a `general-purpose` sub-agent analyzing
> https://github.com/Kiranism/next-shadcn-dashboard-starter plus current best practice. Feeds the
> **future** `frontend` convention domain (`.claude/rules/frontend/`). `[REPO]` = specific to
> that starter; `[BP]` = general best practice.

## The reference repo (as of fetch) [REPO]
- Stack has moved past most blog posts: **Next.js 16 / React 19 / TS 5.7 strict / Tailwind v4**, shadcn on
  **Base UI** (`style: base-nova`, NOT Radix), **OxLint/Oxfmt** (not ESLint/Prettier), **TanStack Form**
  (not react-hook-form). Bun preferred. Clerk auth, Sentry, Recharts, kbar (Cmd+K), dnd-kit.
- ⚠️ Its own `AGENTS.md` has **stale lines** ("Radix UI", "Prettier/ESLint") — repo is mid-migration
  (`.migration/`). Don't copy those blindly.
- **Has `CLAUDE.md` + `AGENTS.md` + `.claude/skills/`.** `CLAUDE.md` is short and points to `AGENTS.md` +
  `docs/*.md` (same "map not manual" philosophy). `AGENTS.md` is the substantive rulebook with imperative,
  specific "Critical Rules for AI Agents."

### Most distinctive repo ideas worth adopting
- **Feature-based modularity:** `src/features/<name>/` = `components/` + `schemas/` + a **3-file API layer**:
  `api/types.ts` (contracts) → `api/service.ts` (**only** file you edit to swap mock→real backend) →
  `api/queries.ts` (React Query `queryOptions` + key factories, stable once set).
- **Data = TanStack Query** with SSR prefetch (`prefetchQuery` + `HydrationBoundary` → `useSuspenseQuery`
  in `<Suspense>`); **URL state = nuqs**; **UI state = Zustand** (never server data); **forms = TanStack
  Form + Zod** via `useAppForm`.
- Central **icon registry** (`@/components/icons`, never import `@tabler/icons-react` directly);
  `<PageContainer>` for headers; `<Button isLoading>`; RBAC nav filtering (client-side, with server enforcement).

## General best practice [BP]
- **Next.js App Router:** Server Components by default; `'use client'` only at leaves (state/effects/browser
  APIs); children-as-slot pattern; Server Actions for mutations; parallel fetching (no waterfalls); streaming
  via `loading.tsx` + `<Suspense>`; `error.tsx` boundaries; route groups `(x)`; parallel routes `@slot`;
  Metadata API.
- **React:** composition over prop-drilling; compound components; container/presenter; Rules of Hooks
  (top-level only, pure); **React Compiler v1.0 → automatic memoization**, so `useMemo`/`useCallback`/`memo`
  are escape hatches only (with a stated reason); colocation.
- **TypeScript:** `strict: true`; `@/*` path alias (no deep relative); explicit return types on exports;
  `interface` for props; **discriminated unions** for variants + state modeling; **Zod at boundaries** with
  `z.infer` for derived types.
- **shadcn/ui:** "not a component library — how you build yours"; Open Code + **ownership** (CLI copies into
  `components/ui/`, you edit them); `components.json` config; theme via CSS-variable/OKLCH tokens; merge
  classes with `cn()` (never string-concat).
- **Web design / a11y:** token systems (Tailwind 4px scale, semantic color tokens — no magic numbers/hex);
  **WCAG 2.2 AA** (POUR); semantic HTML + landmarks; keyboard + visible focus; contrast; alt text;
  mobile-first responsive.

## Recommended folder tree (scaffold later) [BP/REPO]
```
src/
├── app/  (marketing)/ (app)/{layout,page,loading,error}.tsx  api/  globals.css
├── components/  ui/ (shadcn, owned)  layout/  icons.tsx
├── features/  <feature>/  api/{types,service,queries}.ts  components/  schemas/ (zod)
├── hooks/  lib/ (cn, query-client, searchparams)  config/  styles/  types/
```

## frontend-design skill split
Global `frontend-design` skill = *how it should look* (aesthetics, anti-templated). A project skill should
encode *the project's* tokens/theme names, the a11y acceptance bar, and composition house rules, and **invoke**
the global skill for aesthetics — don't duplicate.

## Sources
- https://github.com/Kiranism/next-shadcn-dashboard-starter (+ raw AGENTS.md, CLAUDE.md, components.json, tsconfig.json).
- https://nextjs.org/docs/app/getting-started/server-and-client-components ; /building-your-application/data-fetching/patterns ; /server-actions-and-mutations ; /guides/production-checklist.
- https://react.dev/reference/react/useMemo ; /blog/2025/10/07/react-compiler-1 ; /reference/rules/components-and-hooks-must-be-pure ; /reference/eslint-plugin-react-hooks ; /learn/typescript.
- https://ui.shadcn.com/docs ; /docs/components-json.
- https://www.totaltypescript.com/discriminated-unions-are-a-devs-best-friend ; https://www.typescriptlang.org/docs/handbook/unions-and-intersections.html.
- https://www.w3.org/TR/WCAG22/ ; https://www.w3.org/WAI/WCAG21/Techniques/html/H101 ; https://developer.mozilla.org/en-US/docs/Web/Accessibility.

---

## 2026-07-24 currency refresh (session 3 — REVIEW-03)
Frontend is future/unbuilt; version pins framed "verify at project creation". Verified currents:
- **Next.js 16**: async request APIs (`await params/searchParams/cookies()/headers()`), Turbopack default, `middleware`→`proxy`, `cacheComponents`, `next lint` removed. https://nextjs.org/docs/app/guides/upgrading/version-16
- **React 19.2 + React Compiler 1.0** (opt-in `reactCompiler: true`); `useEffectEvent` stable. https://react.dev/blog/2025/10/07/react-compiler-1
- **Tailwind v4** CSS-first (`@theme`, `@import "tailwindcss"`, `@tailwindcss/postcss`). https://tailwindcss.com/blog/tailwindcss-v4
- **shadcn** defaults new inits to Base UI (~Jul 2026); Radix still supported. https://ui.shadcn.com/docs
- **Zustand v5** `useShallow`; **RHF resolvers v5** + Zod 4. https://zustand.docs.pmnd.rs/migrations/migrating-to-v5
- **WCAG 2.2 AA** new criteria (2.5.8 target size, 2.4.11 focus not obscured, …); ISO/IEC 40500:2025. https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
