# Next.js — Story Engine reference note

> Planned App Router frontend (Server/Client Components + Server Actions, TypeScript) for the Story
> Engine — **future frontend, not yet built; no frontend code exists in the repo.**

- **Version pin (ours):** none yet — frontend not scaffolded.
- **Latest stable (verified):** 16.2.x — upstream reports **16.2.11** (checked 2026-07); 16.3 is Preview, not stable. Next.js 16's App Router runs on React 19.2.
- **Upstream `llms.txt`:** yes — vendored at `./llms.txt`.
- **Docs home:** https://nextjs.org/docs

## Planned use in Story Engine
- App Router frontend consuming the Python backend's story/episode APIs — Server Components fetch data server-side (keeping API keys/secrets off the client), Client Components layer in interactivity.
- Server Actions (React Server Functions) for mutations (trigger episode generation, edit story bible) invoked from forms/event handlers.
- Paired with React 19.x (Next 16 uses React 19.2), shadcn/ui, Tailwind v4, targeting WCAG 2.2 AA.
- _Not current:_ none of this is implemented; treat as intended architecture only.

## Read this for… (task → doc link)
- Get started with the App Router → https://nextjs.org/docs/app/getting-started
- Server/client boundary → https://nextjs.org/docs/app/getting-started/server-and-client-components
- Fetch data (Server Components, streaming) → https://nextjs.org/docs/app/getting-started/fetching-data
- Mutate data / Server Actions → https://nextjs.org/docs/app/getting-started/mutating-data · https://nextjs.org/docs/app/guides/server-actions
- The `use server` directive → https://nextjs.org/docs/app/api-reference/directives/use-server
- Upgrade to v16 (breaking changes) → https://nextjs.org/docs/app/guides/upgrading/version-16

## Gotchas to watch
- **Server/client boundary:** `'use client'` pulls a component *and everything it imports* into the client bundle; only `NEXT_PUBLIC_`-prefixed env vars reach the client — use the `server-only` package to keep backend API keys out of client code.
- **Server Actions are public POST endpoints** — reachable via direct POST, not just your UI; always verify auth/authorization inside every action. They dispatch one-at-a-time from the client; use Server-Component fetching for parallelism.
- **v16 breaking changes:** async Request APIs (`cookies`/`headers`/`params`/`searchParams` are now Promises); Turbopack default; `middleware` renamed to `proxy`; `revalidateTag` needs a second `cacheLife` arg; `next lint` and AMP removed. Node 20.9+ / TS 5.1+ required.
- **16.3 is Preview only** — pin 16.2.x for stable when the frontend is eventually scaffolded; verify the then-current latest at build time.

_Sources: nextjs.org/docs, vendored llms.txt. Verified 2026-07-24._
