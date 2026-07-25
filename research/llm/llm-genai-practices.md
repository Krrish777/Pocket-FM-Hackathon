# Research: Engineering Conventions for a Generative Storytelling Engine (Python, LLM)

> **Provenance:** Web research by a `general-purpose` sub-agent. Raw cited artifact; distilled rules
> live in `.claude/rules/python/08-llm-storytelling.md`. This is the highest-value section for
> THIS project.

---

## 1. Secrets & Config Management
**Principle:** Deployment-varying config (keys, model IDs, budgets) lives in the environment (12-Factor III).
Use `pydantic-settings` as the single typed entry point — validated at startup, not a mid-generation `KeyError`.

- No literal keys/tokens/org IDs in the repo; CI greps for provider prefixes (`sk-`, `sk-ant-`) and fails.
- `.env` gitignored; commit `.env.example` with blank values.
- All config through one `Settings(BaseSettings)`, imported once. No scattered `os.getenv()` in business logic.
- Secrets typed `SecretStr` (masked in logs/tracebacks/`repr()`); `.get_secret_value()` only at the network boundary.
- Fail fast at boot if a required secret is missing (Pydantic `ValidationError`).
- Group with `env_prefix`; `env_nested_delimiter="__"` for structured config.

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="STORYENGINE_", env_file=".env", case_sensitive=False
    )
    anthropic_api_key: SecretStr
    default_model: str = "claude-sonnet-4"
    max_output_tokens: int = 2000
    request_budget_usd: float = 0.50
    temperature: float = 0.8


settings = Settings()  # validates at import; missing key => startup crash
```

## 2. Prompt Management — Prompts Are Versioned Assets
**Principle:** In a storytelling engine the *prompt is the product*. Inline string literals make behavior
changes invisible to review and impossible to roll back. HumanLayer 12-Factor Agents: "Own Your Prompts"
(Factor 2), "Own Your Context Window" (Factor 3).

- Prompts as versioned artifacts (template files in `prompts/`, or a registry), never string literals in domain logic.
- Every prompt: stable **name + version** (semver) + changelog. Production references a version/alias, never "latest by accident."
- A prompt change is a reviewable diff.
- Explicit templating (Jinja / `str.format` named fields); expected variables documented + validated before render.
- Log which prompt *version* produced each generation (§3).
- Registry (MLflow/PromptLayer/Langfuse/Agenta) once >~10 prompts or non-engineers iterate; **files-in-git is a
  legitimate small-team start** — registry is an upgrade path, not day-one.

**Contested:** registry vs files is a real tradeoff; prompt-semver conventions aren't standardized — pick a house
rule (minor = wording, major = schema/behavior) and document it.

## 3. Reproducibility & Determinism
**Principle:** You cannot make hosted-LLM output bit-for-bit reproducible; you *can and must* make every generation
**auditable and re-runnable-ish** by recording the full generation context.

**Hard truth:** LLM output is non-deterministic **even at temperature 0**. Temp 0 removes sampling randomness, not:
- fp non-associativity + reduced precision (fp16/bf16);
- **lack of batch invariance** — dynamic batching means kernels produce different logits depending on batch size your
  request lands in, so identical prompts diverge under load (Thinking Machines Lab, Horace He, "Defeating
  Nondeterminism in LLM Inference," Sept 2025; bitwise-identical runs require controlling the inference stack).
- **Seed** is partial: OpenAI / Vertex Gemini / open-weight expose a seed (improves but does not guarantee identical
  output); **Anthropic exposes no seed** and can vary at temp 0 — guidance is to sample multiple times.

**Rules**
- Record a **generation manifest** per call, stored with the output: `model_id`, `provider`, `temperature`,
  `top_p`, `max_tokens`, `seed?`, `prompt_name`+`version`, rendered messages (or hash + inputs),
  `system_fingerprint?`, timestamp, token usage.
- Pin the exact model snapshot (dated), never a floating alias, for anything you compare across a series.
- Track `system_fingerprint` (OpenAI) to detect silent backend changes (continuity drift).
- Temperature by task: **low (0–0.3)** for structured/continuity-critical steps, **high (0.7–1.0)** for prose. Not one global temp.
- For must-reproduce paths, prefer recorded fixtures (§4) over trusting live reproducibility.

**Contested:** true determinism only from self-hosted stacks with batch-invariant kernels (vLLM/SGLang deterministic
modes), at a throughput cost. **Promise auditability, not reproducibility.**

## 4. Testing Generative Code
**Principle:** Never assert exact generated text. Assert **structure, schema, invariants**. Split: fast unit (LLM
mocked) → recorded-fixture integration → evals (quality, non-blocking).

- Validate parsed output against a Pydantic model; assert domain invariants (episode has ≥1 scene; referenced
  characters exist in the bible; word count in bounds).
- Mock the LLM client in unit tests (single wrapper §5 makes this trivial) → fast, free, deterministic.
- VCR.py-style cassettes for integration tests: record a real response once, replay offline; fail only when the
  input to the model changes.
- **Evals separate from unit tests** — golden-dataset + LLM-as-judge, non-blocking, tracked over time.

```python
def test_episode_generation_is_well_formed(fake_llm):
    fake_llm.returns(
        Episode(title="The Return", scenes=[Scene(characters=["Mara"], text="...")])
    )
    ep = generate_episode(series_id="s1", beat="reunion", client=fake_llm)
    assert isinstance(ep, Episode)
    assert ep.scenes
    assert all(c in load_character_bible("s1").names for c in ep.characters())
```

**Contested:** LLM-as-judge reliability is debated — treat scores as directional; keep a human-reviewed golden set.

## 5. Cost & Token Governance
**Principle:** Every model call through **one client wrapper** — the choke point for budgets, logging, caps, caching,
retry, model-swap. Scattered `openai.`/`anthropic.` calls are banned.

- One wrapper; domain depends on an interface (`LLMClient.generate(...)`), never a vendor SDK.
- Log per call: model id, prompt+completion tokens, USD cost, latency, prompt version, request id, retry count.
  Meter *tokens* not HTTP calls; tie to an idempotency key so **retries don't double-count**.
- **Always set `max_tokens`** (top runaway-cost/latency risk) + explicit length instruction in the prompt.
- Budget guardrail: pre-flight token estimate (tiktoken / provider counter); reject/downgrade over-budget requests.
- Cache identical prompt→completion; use provider prompt-caching for the large stable prefix (series bible, style
  guide). Semantic caching is contested (risks wrong continuation).
- Cheapest adequate model per task: cheap/fast for extraction/classification, expensive for prose. Routing is a governance lever.
- Retries: exponential backoff + jitter on 429/5xx; same provider first, then optional failover.

```python
from typing import Protocol
from pydantic import BaseModel


class Generation(BaseModel):
    output: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class LLMClient(Protocol):
    def generate(
        self,
        *,
        messages: list[dict],
        model: str,
        max_tokens: int,
        temperature: float,
        response_model: type[BaseModel] | None = None,
        idempotency_key: str | None = None,
    ) -> Generation: ...
```

## 6. Structured Output & Validation — "LLM at the Edges"
**Principle:** LLM at the *boundary*, domain logic *pure*. Model turns fuzzy input → validated typed object;
downstream continuity checks / plot-graph / persistence operate on trusted structures, not raw text. Hexagonal:
LLM is an **adapter** behind a **port**; core never imports a vendor SDK.

- Validate at the edge with Pydantic; unparseable/invalid output never reaches the core.
- Use `instructor` (or provider-native structured outputs): `response_model` + validation + **auto re-ask on
  validation error** (`max_retries`); `from_provider(...)` across OpenAI/Anthropic/Google/Ollama. Add
  `@field_validator`s to encode domain rules (e.g. narrator must be a known POV character → auto retry).
- Core is a port: define `LLMClient`, implement provider adapters behind it; swapping providers changes an adapter.
- Trust boundary: treat model output as untrusted input — validate/bound/sanitize before storage or echo to users.

```python
import instructor
from pydantic import BaseModel, field_validator


class SceneState(BaseModel):
    pov_character: str
    location: str
    unresolved_threads: list[str]

    @field_validator("pov_character")
    @classmethod
    def known_character(cls, v):
        if v not in KNOWN_CHARACTERS:
            raise ValueError(f"Unknown POV character: {v}")
        return v


client = instructor.from_provider("anthropic/claude-sonnet-4")
state = client.create(response_model=SceneState, max_retries=3, messages=[...])
```

## 7. Reference Architectures
- **12-Factor Agents (HumanLayer)** — "production AI apps aren't fully autonomous agents; they're well-engineered
  traditional software with LLM capabilities integrated at key points." Agents as stateless reducers over an event log.
- **Hexagonal / Ports-and-Adapters for AI** — domain isolated from vendor.
- **Twelve-Factor App (config)** — §1 backbone.
- **MLflow Prompt Registry / PromptLayer / Langfuse / Agenta** — §2 prompt-as-asset lifecycle.
- **Instructor (567-labs)** — de-facto structured-extraction library, Pydantic-based.
- **Thinking Machines — batch-invariant inference** — authoritative account of §3 non-determinism.

## Sources
- https://github.com/pydantic/pydantic-settings — BaseSettings, SecretStr, env loading (§1).
- https://pydantic.dev/articles/llm-intro — Pydantic for LLMs (§6).
- https://github.com/humanlayer/12-factor-agents (factor-02, factor-03) — own prompts/context (§2, §7).
- https://mlflow.org/prompt-registry — prompt registry lifecycle (§2).
- https://www.braintrust.dev/articles/best-prompt-versioning-tools-2025 ; https://agenta.ai/blog/prompt-versioning-guide — prompt versioning (§2).
- https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/ — batch-invariance / temp-0 non-determinism (§3).
- https://dylancastillo.co/posts/seed-temperature-llms.html — temperature/seed/system_fingerprint (§3).
- https://www.keywordsai.co/blog/llm_consistency_2025 ; https://www.lmsys.org/blog/2025-09-22-sglang-deterministic/ — consistency/deterministic inference (§3).
- https://docs.langchain.com/oss/python/langchain/test — unit vs integration vs evals; fake LLMs (§4).
- https://anaynayak.medium.com/eliminating-flaky-tests-using-vcr-tests-for-llms-a3feabf90bc5 — VCR cassettes (§4).
- https://www.confident-ai.com/blog/llm-testing-in-2024-top-methods-and-strategies — LLM testing methods (§4).
- https://python.useinstructor.com/ ; https://github.com/567-labs/instructor — structured outputs + auto-retry (§6).
- https://matheuspalma.com/blog/llm-cost-governance-token-budgets-model-routing-spend-guardrails — token budgets/routing (§5).
- https://www.clawpulse.org/blog/llm-api-rate-limiting-best-practices... — 429/backoff/failover (§5).
- https://redis.io/blog/llm-token-optimization-speed-up-apps/ — token optimization/caching (§5).
- Hexagonal-for-LLM writeups (medium/@tejasrawat, knitish91) — ports & adapters with LLM adapter (§6, §7).

**Most decision-relevant finding:** batch-invariance explains temp-0 non-determinism (Thinking Machines, Sept 2025)
— build §3 around *auditability* (record the manifest), not a reproducibility promise.

---

## 2026-07-24 currency refresh (session 3 — REVIEW-03)
- Typed LLM output now has three current paths (all end in a validated Pydantic model): provider-native structured outputs, `instructor` (thin patch), or `pydantic-ai` (agent framework). Framework choice deferred to the event brief. https://python.useinstructor.com/ · https://ai.pydantic.dev/
- Seed / `system_fingerprint` support varies by provider — verify against live API docs at adoption time (softened the "Anthropic exposes no seed" absolute).
