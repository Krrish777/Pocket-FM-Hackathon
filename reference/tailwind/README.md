# Tailwind CSS — Story Engine reference note

> Utility-first CSS framework planned for the Story Engine's future frontend (not yet built — no
> frontend code exists today).

- **Version pin (ours):** none yet — frontend not scaffolded.
- **Latest stable (verified):** v4.3.x (v4.3.3 observed; v4.3 line confirmed latest, checked 2026-07).
- **Upstream `llms.txt`:** none — `tailwindcss.com/llms.txt` is 404. Use the docs site.
- **Docs home:** https://tailwindcss.com/docs

## Planned use in Story Engine
- Style the future Next.js App Router + React 19 frontend with Tailwind v4 utility classes.
- Adopt shadcn/ui components (which layer on Tailwind) for the component library.
- Define design tokens via CSS-first `@theme` config rather than a `tailwind.config.js`.
- Build toward WCAG 2.2 AA (contrast, focus-visible, motion) — Tailwind provides utilities but does not enforce accessibility on its own.

## Read this for… (task → doc link)
- Install Tailwind v4 in Next.js → https://tailwindcss.com/docs/installation/framework-guides/nextjs
- General v4 install / setup → https://tailwindcss.com/docs/installation
- Configure theme tokens CSS-first with `@theme` → https://tailwindcss.com/docs/theme
- Upgrade an existing v3 codebase to v4 (`npx @tailwindcss/upgrade`) → https://tailwindcss.com/docs/upgrade-guide
- v4 release / rationale → https://tailwindcss.com/blog/tailwindcss-v4

## Gotchas to watch
- **v4 is a major break from v3:** CSS-first config (`@import "tailwindcss"` + `@theme` in CSS), no `tailwind.config.js` by default, `@tailwind` directives gone — most v3 tutorials/snippets are stale.
- **v4 requires modern browsers** (Safari 16.4+, Chrome 111+, Firefox 128+) — it won't run on older targets.
- **Verify shadcn/ui's Tailwind-v4 track** before wiring it up — shadcn had a distinct v3→v4 migration path.
- **No upstream `llms.txt` (404)** — link the HTML docs above; don't point at a nonexistent llms.txt.

_Sources: tailwindcss.com/docs, github.com/tailwindlabs/tailwindcss/releases. Verified 2026-07-24 (v4.3 line confirmed; exact v4.3.3 date unverified — a GitHub timestamp fetch artifact)._
