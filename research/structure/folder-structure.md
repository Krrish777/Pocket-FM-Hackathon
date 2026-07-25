# Research: Repository / Folder Structure for a Python LLM Storytelling Engine

> **Provenance:** Web research by a `general-purpose` sub-agent. Raw cited artifact; the distilled
> rules live in `.claude/rules/structure/`, and the actual skeleton is built from the tree below.

## TL;DR verdict
Use a **`src/` layout**, a **hexagonal (ports-and-adapters) core**, and **treat prompts, config,
data, and evals as first-class top-level assets** rather than burying them in code.

---

## 1. `src` layout vs flat layout
**Use `src/` layout** for anything installable/tested/shipped.
- **PyPA** ([src-vs-flat](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)):
  three advantages — (1) requires editable install so you develop against the real artifact;
  (2) prevents accidental import of the in-repo copy (CWD shadowing); (3) validates packaging config.
  PyPA frames it as a tradeoff, not a mandate.
- **pytest** ([Good Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html))
  **strongly** recommends `src/` for new projects, `tests/` outside the package, `--import-mode=importlib`.
- **⚠ Conflict:** cookiecutter-data-science uses **flat** layout (DS-notebook-centric). For a
  production LLM engine, prefer `src/`; borrow only CCDS's `data/` conventions.

---

## 2. Recommended folder tree (build as-is)

```text
story-engine/
├── pyproject.toml              # Single source of truth: deps, build backend, tool config
├── README.md
├── .env.example                # Every env var name (API keys, model IDs) with dummy values
├── .gitignore                  # Ignores .env, data artifacts, __pycache__, .venv, caches
├── .pre-commit-config.yaml
├── Makefile                    # (or justfile) make test / eval / lint / run
├── LICENSE
│
├── src/
│   └── story_engine/           # THE installable package (import story_engine)
│       ├── __init__.py
│       ├── domain/             # PURE core: story/episode/character/plot models + rules. NO LLM/HTTP/IO.
│       │   ├── models.py       # Story, Episode, Character, PlotBeat, Arc
│       │   ├── narrative.py    # Pure logic: continuity, arc progression, beat sequencing
│       │   └── errors.py       # Domain exceptions
│       ├── ports/              # ABC/Protocol interfaces the core depends on
│       │   ├── llm.py          # LLMPort.generate(prompt, params) -> completion
│       │   ├── prompt_store.py # PromptStorePort.render(name, version, vars)
│       │   ├── repository.py   # StoryRepositoryPort.load/save
│       │   └── retriever.py    # RetrieverPort.search (lore/RAG) — optional
│       ├── services/           # Application/use-case layer: orchestrates domain + ports
│       │   ├── episode_generator.py
│       │   ├── story_adapter.py
│       │   └── interactive_plot.py
│       ├── adapters/           # Concrete port impls — ONLY place external SDKs live
│       │   ├── inbound/        # Driving adapters
│       │   └── outbound/       # Driven adapters
│       │       ├── openai_llm.py        # implements LLMPort (swap for anthropic_llm.py, local_llm.py)
│       │       ├── file_prompt_store.py # implements PromptStorePort, reads prompts/
│       │       └── sqlite_repository.py # implements StoryRepositoryPort
│       ├── api/                # HTTP delivery (FastAPI): routers, schemas, wiring. Thin.
│       │   ├── app.py
│       │   ├── routers/
│       │   └── schemas.py      # request/response DTOs (NOT domain models)
│       ├── cli/                # CLI delivery. Thin.
│       │   └── main.py         # entry in pyproject [project.scripts]
│       ├── config/             # Typed settings loader (pydantic-settings)
│       │   └── settings.py
│       └── observability/      # Logging, tracing, token/cost metering
│
├── prompts/                    # Prompt templates as VERSIONED ASSETS (not Python strings)
│   ├── episode_generation/{v1.jinja,v2.jinja}
│   ├── character_voice/v1.jinja
│   └── README.md               # Naming + versioning convention (name/vN.jinja)
│
├── config/                     # Non-secret runtime config by environment
│   ├── default.yaml            # model names, temperature, max_tokens, retry policy
│   ├── dev.yaml
│   └── prod.yaml
│
├── data/                       # cookiecutter-data-science convention (raw is immutable)
│   ├── raw/                    # never edited
│   ├── interim/                # cleaned/segmented intermediates
│   ├── processed/              # final canonical datasets (embeddings, indexed lore)
│   └── external/               # third-party reference data
│
├── evals/                      # LLM evaluation harness + datasets (distinct from unit tests)
│   ├── datasets/
│   ├── cases/
│   ├── metrics/                # coherence, continuity, tone, LLM-as-judge
│   └── run_evals.py
│
├── tests/                      # Mirrors src/story_engine/ ; OUTSIDE the package
│   ├── unit/{domain,services}/ # mocked ports, fast, offline
│   ├── integration/            # real adapters, marked, opt-in
│   ├── conftest.py             # fixtures: fake LLMPort, sample stories
│   └── fixtures/
│
├── notebooks/                  # Exploration ONLY. Numbered (01-explore.ipynb).
├── scripts/                    # One-off / operational (ingest, index build, migrations)
└── docs/                       # Architecture, prompt-versioning policy, ADRs
```

---

## 3. Reasoning per top-level folder
- **`src/story_engine/`** — one installable package; subdivided by *architectural layer*, not file type.
- **`prompts/` (top-level)** — highest-churn, highest-leverage assets, edited by non-engineers too.
  External `.jinja` files → diff-able in PRs, versionable (`name/vN`), swappable without code change;
  loaded by `file_prompt_store` via `PromptStorePort`.
- **`config/` + `settings.py`** — `config/*.yaml` = non-secret env-specific values; `settings.py` =
  typed loader (pydantic-settings) merging YAML + env; **secrets only in `.env`**, documented by
  `.env.example`.
- **`data/{raw,interim,processed,external}`** — from cookiecutter-data-science; **raw is immutable**;
  transformations flow raw→interim→processed. Gitignored; kept via `.gitkeep`.
- **`evals/` (separate from `tests/`)** — LLM quality is non-deterministic and graded, slow, and costs
  money → must not sit in the unit-test path.
- **`tests/` (outside, mirroring)** — pytest good practice; split **unit** (mocked, offline) vs
  **integration** (real adapters, opt-in).
- **`notebooks/`** — exploration only; "notebooks explore, source repeats."
- **`scripts/`** — operational one-offs; import from the package, never imported by it.
- **`docs/`** — architecture, prompt-versioning policy, ADRs.
- **Top-level files:** `pyproject.toml` (single config source), `.env.example`, `.gitignore`,
  `.pre-commit-config.yaml`, `Makefile`/`justfile`.

---

## 4. Architecture layering → folder mapping (hexagonal / ports-and-adapters)
Principle: **LLM I/O, HTTP, DBs, vendor SDKs live at the edges; pure narrative logic in the center
imports nothing external.** Swap OpenAI→Anthropic→local or bump a prompt version without touching core.

| Layer | Responsibility | Folder | Dependency rule |
|---|---|---|---|
| Domain (core) | Story/episode/character models + pure rules | `domain/` | Imports nothing outward. No LLM/HTTP/IO. |
| Ports | Interfaces (ABC/`Protocol`): `LLMPort`, `PromptStorePort`, `StoryRepositoryPort`, `RetrieverPort` | `ports/` | Defined by core, implemented by adapters. |
| Application/use-cases | "generate next episode", "adapt story", "branch plot" | `services/` | Depends on domain + ports only. |
| Outbound adapters | OpenAI/Anthropic/local LLM, file prompt store, SQLite repo, retriever | `adapters/outbound/` | Only place vendor SDKs imported. Swappable. |
| Inbound adapters | FastAPI routers, CLI, webhooks | `api/`, `cli/`, `adapters/inbound/` | Thin. Translate requests → service calls. |
| Cross-cutting | Config, logging, tracing, token/cost metering | `config/`, `observability/` | Wired at composition root. |

**Composition root** (`api/app.py`, `cli/main.py`) is the one place that instantiates concrete
adapters and injects them into services (dependency inversion).

---

## 5. Anti-patterns (what NOT to do)
- God package / giant `utils.py` — split by layer.
- **LLM SDK imports in the core** — breaks the hexagon; vendor imports only in `adapters/outbound/`.
- Circular deps between layers — dependencies point **inward only**.
- Prompts as inline Python strings — kills diff review/versioning; externalize to `prompts/`.
- Evals mixed into unit tests — flaky, paid, slow in CI; keep `evals/` separate and opt-in.
- Flat layout for an installable app — invites import shadowing.
- Notebooks as production code — explore in notebooks, ship in `src/`.
- Secrets in `config/` or committed `.env` — only `.env.example` is committed.
- Mutating `data/raw/` — raw is immutable.

---

## Sources
- https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/ — the three `src/` advantages (tradeoff-framed).
- https://docs.pytest.org/en/stable/explanation/goodpractices.html — strongly recommends `src/`, tests outside package, importlib mode.
- https://cookiecutter-data-science.drivendata.org/ — `data/{raw,interim,processed,external}`, "notebooks explore / source repeats". (Uses flat layout — conflicts for installable apps.)
- https://realpython.com/ref/best-practices/project-layout/ , https://pydevtools.com/handbook/explanation/src-layout-vs-flat-layout/ — endorse `src/` as default.
- https://anoliphantneverforgets.com/notes/2026-03-18-hexagonal-agents — hexagonal architecture for LLM agents; core vs inbound/outbound ports/adapters.
- https://medium.com/@gngsn/mastering-hexagonal-architecture-structuring-software-with-ports-and-adapters-e2751e985e43 , https://dev.to/dyarleniber/hexagonal-architecture-and-clean-architecture-with-examples-48oi — ports & adapters definitions.
- https://apxml.com/courses/prompt-engineering-llm-application-development/chapter-8-application-development-considerations/structuring-llm-application-code — prompts as separate assets, LLM client wrappers.
- https://mastra.ai/blog/how-to-structure-projects-for-ai-agents-and-llms , https://www.readyforagents.com/resources/llm-projects-structure — corroborate config/src/tests split.
- https://github.com/sanketrs/ai-llm-project-file-structure-template — concrete LLM template.

**Disagreements flagged:** (1) PyPA neutral vs pytest/RealPython pushing `src/` hard → follow the
stronger camp. (2) CCDS flat layout + `config.py` inside package → adopt its `data/` convention but
override layout with `src/` + top-level `config/`. (3) Some templates keep `data/`/`models/` inside
`src/`; recommend `data/` at top level (artifact store, not importable code).

---

## 2026-07-24 currency refresh (session 3 — REVIEW-03)
Structure docs re-synced to the actual `src/story_engine/` tree (they had drifted): added `bootstrap.py` (single composition root), `shared/`, `resources/`, the `domain/models/` package, split ports (`EpisodeLogRepositoryPort`/`StoryBibleRepositoryPort`/`LoreRetrieverPort`), and `adapters/outbound/persistence/`. Principles unchanged.
- src-layout requires an (editable) install before tests run. https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/
- One composition root wiring adapters→ports; `typing.Protocol` outbound ports; avoid over-granular "interface explosion". https://dev.to/elpic/hexagonal-architecture-in-python-wiring-adapters-dependency-injection-and-the-application-layer-61l
- uv layout: commit `uv.lock`. https://docs.astral.sh/uv/concepts/projects/layout/
