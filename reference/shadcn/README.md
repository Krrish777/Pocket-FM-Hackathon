# shadcn/ui — Story Engine reference note

> Copy-in component registry for the **planned, not-yet-built** Story Engine frontend — you own the
> generated code (it is NOT an npm component-library dependency); CLI-driven for a Next.js App Router +
> React 19 + Tailwind v4 stack.

- **Version pin (ours):** none yet — frontend not scaffolded.
- **CLI / status (verified):** package is `shadcn` (invoked `shadcn@latest`); CLI v4 line, latest npm **4.14.1** (checked 2026-07). The older `shadcn-ui` package is **deprecated** — use `shadcn`.
- **Upstream `llms.txt`:** yes — vendored at `./llms.txt`.
- **Docs home:** https://ui.shadcn.com/docs

## Planned use in Story Engine
- Scaffold a Next.js App Router frontend and run `shadcn@latest init` to generate `components.json` + the `cn` util; no such code exists today.
- Pull components on demand via `shadcn@latest add <component>` — copied into our repo, so we own and can freely edit them.
- Theme via CSS variables (OKLCH tokens, background/foreground pairs, `--radius` scale) to match Story Engine branding; dark mode through `.dark` overrides.
- Target React 19 + Tailwind v4 from the start (both GA-supported), so no v3→v4 migration for a greenfield frontend.

## Read this for… (task → doc link)
- Scaffold the frontend / run init → https://ui.shadcn.com/docs/installation/next
- Understand/edit `components.json` (style, tailwind, aliases, tsx, rsc, registries) → https://ui.shadcn.com/docs/components-json
- CLI reference (`init`, `add`, `search`, `view`, `build`, `migrate`, `preset`) → https://ui.shadcn.com/docs/cli
- Theming (CSS variables, OKLCH, dark mode, radius) → https://ui.shadcn.com/docs/theming
- Tailwind v4 support → https://ui.shadcn.com/docs/tailwind-v4
- React 19 notes → https://ui.shadcn.com/docs/react-19

## Gotchas to watch
- **Copy-in, not a dependency:** `add` writes source into our repo — there's no package to bump; updates mean re-pulling/diffing components ourselves (we own the code and any local edits).
- **Tailwind v4 + React 19 are GA and non-breaking** — existing v3/React 18 apps keep working; only *new* projects start on v4/React 19. For greenfield this is what we want.
- **Deprecations:** `tailwindcss-animate` → `tw-animate-css`; component `style` `"default"` → `"new-york"`. Verify current defaults at init time.
- **Package name:** use `shadcn` (CLI v4); `shadcn-ui` is the old deprecated name — don't pin to it.

_Sources: ui.shadcn.com/docs, npmjs.com/package/shadcn, vendored llms.txt. Verified 2026-07-24._
