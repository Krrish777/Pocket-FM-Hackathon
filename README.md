# Story Engine — Pocket FM Hackathon

AI-powered **generative storytelling engine** (Python 3.12+): writes, adapts, and extends serialized
stories — episode generators, AI co-writers, interactive plots. Built with a hexagonal architecture so
the LLM sits at the edges and the story logic stays pure and testable.

> **Problem statement:** _TBD — the exact hackathon brief is not yet known. See `CLAUDE.md`._

## Quick start
```bash
make setup     # create env + install deps (uv)
./init.sh      # session startup: state + consistency check
make check     # full gate: ruff + mypy + pytest
```

## For contributors & coding agents
This repo is built as an **agent harness**. Before writing code:
- **Any agent:** read `AGENTS.md` (mirrors `CLAUDE.md`) — the entry-file map.
- **Conventions** (Python, structure, LLM, testing): `.claude/rules/` — path-scoped, auto-loaded by file type.
- **How work flows** (session clock-in/out, feature list, progress): `CLAUDE.md` → *Session Lifecycle*.
- **Methodology** behind the harness: `Harness-Engineering/Harness-Engineering-Hub.md`.

## Layout
`src/story_engine/` (domain · ports · services · adapters · api · cli · config) · `prompts/` ·
`config/` · `data/` · `evals/` · `tests/`. Full map: `.claude/rules/structure.md`.

## State files (session handoff)
`BACKLOG.md` (task queue) · `feature_list.json` (machine SSOT) · `PROGRESS.md` (durable state) ·
`DECISIONS.md` (decision log) · `session_handoff.md` (per-session clock-out).
