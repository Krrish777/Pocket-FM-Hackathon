---
paths:
  - "src/**"
  - "prompts/**"
---

# LLM & Storytelling

**The differentiator for this project.** (Prompt *authoring* rules live in `prompts.md`.)

## 1. Secrets & config
- **Never hardcode keys/tokens.** One `Settings(BaseSettings)` (pydantic-settings), imported once; no
  scattered `os.getenv()` in business logic.
- Secrets typed `SecretStr` (masked in logs/`repr()`); `.get_secret_value()` only at the network boundary.
- `.env` gitignored; commit `.env.example` with blank values. **Fail fast at boot** if a required secret is missing.

## 2. Prompts are versioned assets
- Prompts live in `prompts/` as template files (`name/vN.jinja`), **never as string literals in domain logic**.
- Every prompt has a stable name + version; a change is a reviewable diff. Production references a
  specific version, never "latest by accident".
- Files-in-git now; a registry (MLflow/Langfuse) is an upgrade path once you exceed ~10 prompts.

## 3. Reproducibility → auditability, not determinism
- Hosted-LLM output is non-deterministic **even at temperature 0** (batch-invariance + fp precision).
  **Do not promise reproducibility.**
- **Do** record a **generation manifest** with every call, stored beside the output: `model_id`,
  `provider`, `temperature`, `top_p`, `max_tokens`, `seed?`, `prompt_name`+`version`, rendered messages
  (or hash + inputs), `system_fingerprint?`, timestamp, token usage. Makes any episode traceable.
- Pin the exact dated model snapshot for anything compared across a series. Temperature by task:
  **low (0–0.3)** for structured/continuity-critical, **high (0.7–1.0)** for prose.

## 4. Cost & token governance
- **All model calls go through ONE client wrapper.** Direct `openai.`/`anthropic.` calls are banned.
- The wrapper logs per call: model, prompt+completion tokens, USD cost, latency, prompt version, retry
  count. Meter *tokens* not calls; tie to an idempotency key so **retries don't double-count**.
- **Always set `max_tokens`** (top runaway-cost risk) + an explicit length instruction in the prompt.
- Budget guardrail: pre-flight token estimate; reject/downgrade over-budget requests. Cache the stable
  prefix (bible, style guide) via provider prompt-caching. Retries: exponential backoff + jitter on 429/5xx.

## 5. LLM at the edges
- LLM I/O, HTTP, DBs, and vendor SDKs live in **adapters** (`adapters/outbound/`), behind **ports**
  (`ports/`). The **domain core imports no vendor SDK** and is unit-testable offline.
- **Validate model output at the boundary with Pydantic** before it reaches the core — treat model
  output as untrusted input. Add `@field_validator`s for domain rules ("narrator must be a known POV
  character"). The typed-output mechanism (native structured outputs / `instructor` / `pydantic-ai`) is
  deferred to the event brief — the port stays the same either way.

```python
class LLMClient(Protocol):  # the only seam the domain sees
    def generate(
        self,
        *,
        messages: list[dict],
        model: str,
        max_tokens: int,
        temperature: float,
        idempotency_key: str | None = None,
    ) -> "Generation": ...
```
