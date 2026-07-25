# Project Structure & Architecture (always-on)

Read before adding a top-level folder or deciding where a file goes. (No `paths:` — this rule is
always loaded, like `CLAUDE.md`.)

## The three rules that decide everything
1. **`src/` layout** — all shippable code under `src/story_engine/`; install before running/testing.
2. **First-class assets are top-level** — `prompts/`, `config/`, `data/`, `evals/` are not buried in code.
3. **LLM at the edges, pure core in the center** — hexagonal layering.

## Where does a file go?
| Adding... | Goes in... |
|---|---|
| Story/episode/character models, pure narrative rules | `src/story_engine/domain/` |
| An interface the core depends on (LLM, prompt store, repo) | `src/story_engine/ports/` |
| A use-case ("generate next episode") | `src/story_engine/services/` |
| An OpenAI/Anthropic/DB/file implementation | `src/story_engine/adapters/outbound/` (SQLite → `.../persistence/`) |
| A FastAPI route or CLI command | `src/story_engine/api/` or `.../cli/` |
| Adapter→service wiring | `src/story_engine/bootstrap.py` (only place adapters are `new`ed) |
| A cross-cutting PURE helper (error type, retry, text util) | `src/story_engine/shared/` (no vendor/IO imports) |
| A packaged data asset (style guide, lore, schema) | `src/story_engine/resources/` |
| A prompt template | `prompts/<name>/vN.jinja` |
| A non-secret config value | `config/*.yaml` |
| A secret | `.env` (gitignored) — document the name in `.env.example` |
| A corpus/dataset artifact | `data/{raw,interim,processed,external}/` |
| An LLM quality eval | `evals/` |
| A unit / integration / e2e test | `tests/unit|integration|e2e/` (mirrors the package) |
| A throwaway exploration | `notebooks/` (numbered) |
| An operational one-off | `scripts/` |

## The tree
```text
story-engine/
├── pyproject.toml              # Single config hub: deps, build backend, [tool.*]
├── uv.lock                     # committed — reproducible installs
├── .env.example                # Env var names, blank values (plain names, no prefix)
├── Makefile                    # make setup / check / test / eval / run
├── src/story_engine/           # THE installable package (import story_engine)
│   ├── domain/                 #   PURE core: models + narrative rules. NO LLM/HTTP/IO imports.
│   ├── ports/                  #   Interfaces (typing.Protocol) the core depends on
│   ├── services/               #   Use-cases: orchestrate domain + ports
│   ├── adapters/
│   │   ├── inbound/            #     driving adapters
│   │   └── outbound/           #     driven adapters — ONLY place vendor SDKs live (persistence/ under here)
│   ├── api/  cli/              #   thin FastAPI / Typer delivery
│   ├── config/                 #   settings.py (pydantic-settings)
│   ├── shared/                 #   cross-cutting PURE helpers: errors.py, retry.py, text.py
│   ├── resources/              #   packaged data assets
│   ├── observability/          #   logging, token/cost metering
│   └── bootstrap.py            #   Composition root — ONLY importer of concrete adapters
├── prompts/  config/  data/  evals/  tests/  notebooks/  scripts/
```
`src/` layout forces you to test the *installed* package — run `uv sync` / `make setup` before tests,
or you get "works locally, fails in CI" import errors.

## Hexagonal layering
| Layer | Responsibility | Folder | May depend on |
|---|---|---|---|
| **Domain (core)** | Models + pure narrative rules | `domain/` | nothing outward |
| **Ports** | Interfaces: `LLMPort`, `PromptStorePort`, segregated repo/retriever ports | `ports/` | domain |
| **Application** | Use-cases | `services/` | domain + ports |
| **Outbound adapters** | LLM / file / SQLite implementations | `adapters/outbound/` | ports |
| **Inbound adapters** | FastAPI, CLI | `api/`, `cli/`, `adapters/inbound/` | services |
| **Cross-cutting** | Config, logging, metering, shared helpers, assets | `config/`, `observability/`, `shared/`, `resources/` | — |

Ports are `typing.Protocol` by default. Repo/retriever ports are segregated by concern — canonical
(`StoryBible`), episodic (`EpisodeLog`), associative (`LoreRetriever`) — not one god port.

## Composition root
`bootstrap.py` is the single composition root — the only module that imports concrete outbound
adapters and injects them into services. Both `api/app.py` and `cli/main.py` call `build_container()`;
neither instantiates an adapter itself.

```python
# bootstrap.py — the ONE place concrete adapters are wired to abstract ports
def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings.database_url)
    init_db(engine)  # create_all (no Alembic for the hackathon)
    generator = EpisodeGenerator(
        llm=StubLLM(),  # swap for a real, cost-logging LLM adapter here
        prompts=FilePromptStore("prompts"),
        bible=InMemoryStoryBibleRepository(),
        episodes=SqliteEpisodeLogRepository(engine),
    )
    return Container(settings=settings, engine=engine, episode_generator=generator)
```

## Anti-patterns (flagged in review)
- **Vendor SDK import in `domain/`/`services/`** — breaks the hexagon; imports live only in `adapters/outbound/`.
- **Dependencies pointing outward / circular deps** — dependencies point inward only.
- **Prompts as inline strings** — externalize to `prompts/`, load via `PromptStorePort`.
- **Model output reaching the core unvalidated** — validate at the boundary with Pydantic first.
- **God module / over-granular "interface explosion"** — split by layer; group related ops into one cohesive port.
- **`data/raw/` is immutable** — write derived artifacts to `interim/`/`processed/`.

## Tooling (who enforces what — don't hand-check what a tool checks)
| Concern | Tool | Command |
|---|---|---|
| Env + deps + lockfile | **uv** (commit `uv.lock`; CI `uv sync --frozen`) | `uv sync`, `uv add`, `uv run` |
| Format (Black-compatible) | **`ruff format`** | `ruff format` |
| Lint + import sort + pyupgrade | **Ruff** (`E,W,F,I,UP,B,C4,SIM,TID,PTH,RET,RUF`; ignore `E501`) | `ruff check --fix` |
| Types | **mypy** (`strict=true`, `no_implicit_optional=true`) | `mypy src` |
| Tests | **pytest** (≥9; `--strict-markers`) | `pytest` |
| The chain on commit | **pre-commit** (`ruff check --fix` before `ruff format`) | `pre-commit run --all-files` |

**Python 3.12+.** Exactly one `pyproject.toml` at root as the config hub (`[build-system]`,
`[project]`, all `[tool.*]`) — no `setup.py`/`setup.cfg`/`pytest.ini`/`mypy.ini`. `__init__.py` in
every package dir. The full `[tool.*]` config lives in the real `pyproject.toml`.
