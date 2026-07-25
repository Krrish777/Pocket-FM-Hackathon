# Research — Provenance & Sources

Distilled notes and the source index behind this project's conventions (`.claude/rules/`). Kept
**outside** `.claude/` so it never burns agent context. Organized by domain to mirror `.claude/rules/`.

## Layout
| Subfolder | Holds | Feeds rule |
|---|---|---|
| `python/` | style & tooling, OOP/errors/logging, Pydantic v2 | `python-style.md`, `python-design.md` |
| `structure/` | folder layout, FastAPI/Typer/adapters | `structure.md` |
| `llm/` | LLM/GenAI engineering practices | `llm-storytelling.md`, `prompts.md` |
| `persistence/` | story memory + SQLModel/SQLite | `persistence.md` |
| `frontend/` | Next.js/React/shadcn (future app) | (future frontend rules) |

`llms.txt` — the curated external **source index** (primary docs + URLs), grouped by topic.

## Placement rule
A new research doc goes in the `research/<domain>/` that matches the `.claude/rules/<domain>` its findings
feed. If no domain fits, add a new `research/<domain>/`. Keep descriptive kebab-case names — do **not**
number these files (numbering implies a reading order; provenance docs are independent).
