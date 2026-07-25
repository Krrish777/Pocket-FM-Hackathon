# React — Story Engine reference note

> UI library for the **planned** (not-yet-built) React frontend that will consume the Story Engine
> backend; no frontend code exists yet.

- **Version pin (ours):** none yet — frontend not scaffolded.
- **Latest stable (verified):** React 19.2 (patch line 19.2.x); React Compiler 1.0 (stable, GA Oct 2025) — checked 2026-07.
- **Upstream `llms.txt`:** yes — vendored at `./llms.txt`.
- **Docs home:** https://react.dev/

## Planned use in Story Engine
- React 19 + TypeScript frontend inside Next.js App Router, rendering serialized stories/episodes served by the Python backend (LLM stays server-side; React never calls models directly).
- UI on shadcn/ui + Tailwind v4; Server Components for data-heavy story/episode reads, Client Components (`"use client"`) only for interactive controls (episode navigation, interactive-plot choices).
- Adopt React Compiler 1.0 from the start for automatic memoization, removing most manual `useMemo`/`useCallback`.
- Enforce Rules of Hooks / component purity via `eslint-plugin-react-hooks` in CI, mirroring the backend's `make check` discipline.

## Read this for… (task → doc link)
- Server-rendered story/episode views → https://react.dev/reference/rsc/server-components
- Mark interactive components client-side → https://react.dev/reference/rsc/use-client
- Rules of Hooks → https://react.dev/reference/rules/rules-of-hooks
- Component/hook purity → https://react.dev/reference/rules/components-and-hooks-must-be-pure
- Type components and hooks → https://react.dev/learn/typescript
- Set up the React Compiler → https://react.dev/learn/react-compiler

## Gotchas to watch
- **Rules of Hooks are non-negotiable for the Compiler:** call Hooks only at the top level — never in conditions/loops/nested functions. The Compiler *assumes* Rules-compliant, pure code; violations miscompile rather than error loudly.
- **Server vs Client boundary:** Server Components can `async/await` and read data directly but can't use state/effects/browser APIs; anything interactive needs a `"use client"` boundary. Don't pass non-serializable props across it.
- **Purity:** components must be pure during render (no prop/state mutation, no render-time side effects) — that's what makes Compiler memoization safe.
- **Compiler is opt-in build tooling, not a syntax change** — it optimizes; it does not fix Rules violations.

_Sources: react.dev/versions, react.dev/blog (React Compiler 1.0), react.dev docs. Verified 2026-07-24._
