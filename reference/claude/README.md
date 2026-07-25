# Anthropic / Claude — Story Engine reference note

> Claude is the intended LLM provider for Story Engine's one client-wrapper adapter behind `LLMPort`;
> the SDK dependency stays deferred until the hackathon brief lands.

- **Version pin (ours):** deferred — add `anthropic>=0.40` (or `openai>=1.50`) at brief time.
- **Latest SDK (verified):** anthropic-sdk-python **0.119.0** (released 2026-07-23; checked 2026-07).
- **Current model IDs (verified against env + docs):**
  - Claude Opus 4.8 → `claude-opus-4-8` — **our default** (matches env's stated latest).
  - Claude Sonnet 5 → `claude-sonnet-5` — cheaper high-volume tier.
  - Claude Haiku 4.5 → `claude-haiku-4-5` (dated `claude-haiku-4-5-20251001`).
  - Claude Fable 5 → `claude-fable-5` — most capable; thinking always-on.
- **Upstream `llms.txt`:** yes — vendored at `./llms.txt`. Resolves (301 → `platform.claude.com/llms.txt`; full text at `/llms-full.txt`).
- **Docs home:** https://platform.claude.com/docs/en/ (docs.claude.com redirects here).

> ⚠️ Model/API facts below were web-verified 2026-07 by a research agent and align with the environment's
> stated model list, but **re-confirm against the docs when the LLM is actually wired** (brief time) —
> especially the sampling-params and structured-output claims, which change our `LLMPort` shape.

## How Story Engine uses it
- One client-wrapper adapter in `adapters/outbound/` implements `LLMPort`; the domain core never imports `anthropic`. Everything routes through `POST /v1/messages` via `client.messages.create` / `.stream`.
- Wrapper logs per call: `model`, `usage.input_tokens` + `usage.output_tokens` (+ cache read/creation tokens), computed USD cost, latency; **always sets `max_tokens`**; ties retries to an idempotency key so a retried call reuses one meter entry (no double-count).
- A `Generation` result carries output + `model` + prompt_tokens + completion_tokens + cost_usd — populate from `response.model` and `response.usage`.
- Generation manifest per call = `model_id`, provider, temperature?, top_p?, `max_tokens`, prompt name+version, token usage.
- Structured output stays deferred (native structured outputs / instructor); `LLMPort` unchanged. When enabled, use `client.messages.parse(output_format=<PydanticModel>)` or `output_config.format` and validate at the boundary with Pydantic.

## Read this for… (task → doc link)
- Messages API (create/stream, tool_use, stop reasons) → https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md
- Structured outputs (`output_config.format`, strict tool use) → https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
- Prompt caching (cache the stable prefix: bible + style guide) → https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
- Token counting (`count_tokens`; never tiktoken) → https://platform.claude.com/docs/en/build-with-claude/token-counting.md
- Models overview + pricing → https://platform.claude.com/docs/en/about-claude/models/overview.md · https://platform.claude.com/docs/en/pricing.md
- Adaptive thinking / effort (primary quality/cost lever) → https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking.md · .../effort.md

## Gotchas that bite us
- **Our `settings.default_model = "claude-sonnet-4"` is STALE/invalid — it will 404.** Fix to a real ID: `claude-opus-4-8` (default) or `claude-sonnet-5`. (Beware: `claude-sonnet-4-0` is a *deprecated alias*, not the same as the nonexistent `claude-sonnet-4`.)
- **Sampling params may be gone on current models** — per research, `temperature`/`top_p`/`top_k` **400 on Opus 4.8 / Sonnet 5 / Fable 5**; steer via prompting + `output_config.effort` instead. This **collides with our `LLMPort.generate(temperature: float)` and the service's `temperature=0.8`** — resolve the port shape when wiring (make sampling optional/omitted per model). _Re-verify this claim at brief time._
- **Always set `max_tokens`** — top runaway-cost risk and a hard requirement; above ~16K you must stream (`.stream()` + `.get_final_message()`).
- **Pin a dated snapshot for cross-series comparison.** Most current IDs are undated floating aliases; only Haiku exposes a dated form. Pin the exact snapshot and record it in the manifest.
- **Treat model output as untrusted** — validate at the adapter boundary with Pydantic before it reaches the core; parse tool-call `input` with `json.loads`, never raw string matching.

_Sources: github.com/anthropics/anthropic-sdk-python/releases, pypi.org/project/anthropic, platform.claude.com/llms.txt. Verified 2026-07-24._
