---
paths:
  - "prompts/**"
---

# Prompt Engineering (Claude Opus 4.8)

How we author every prompt asset. Two prompt classes governed separately: **STRUCTURED-CONTROL**
(schema data) and **PROSE** (story text).

## Non-negotiables
- **Never inline a prompt as a string literal in code.** Prompts are versioned files in `prompts/`.
- **Never prefill the assistant turn** — it returns a **400 on Opus 4.6+**. Use Structured Outputs instead.
- **Always set `max_tokens`** on every call (the client wrapper enforces).
- **Write for a new hire with zero context** — if a colleague would be confused, so is Claude. Be explicit.
- **Instruct positively** — say what to do, not what not to do ("Write flowing prose paragraphs", not
  "don't use markdown").
- **Don't over-prompt with `CRITICAL`/`YOU MUST`/all-caps** — Opus 4.x over-triggers on aggressive language.

## Model behavior (Opus 4.8)
- **Effort is the primary quality/cost lever — tune it before rewriting the prompt.** Default `high`;
  `xhigh` for agentic/coding-shaped work; `low`/`medium` for short scoped calls.
- **State instruction scope explicitly** ("apply to every episode, not just the first") — Opus 4.8 is literal.
- **Prefer general direction over prescriptive step lists when thinking is on.**
- **Get creative variety by asking for N options / varying inputs**, not by reaching for `temperature` first.

## Structured-control prompts (beats, character state, metadata)
- **Force schema conformance with Structured Outputs**, not prose pleading:
  `client.messages.parse(output_format=<PydanticModel>)`.
- **The Pydantic model IS the contract** — hand its JSON Schema to the API; don't paraphrase the schema
  in the prompt.
- **Structured Outputs silently ignores** `minimum`/`maximum`/`minLength`/`maxLength`/recursion and
  requires `additionalProperties: false` — enforce value constraints in **Python validators**, not the schema.
- **Use enums / `strict: true` tool params** for any closed label set. Run at low effort / thinking-off
  unless reasoning is genuinely needed.

## Prose-generation prompts (story text)
- **Role/voice in the system prompt; story state/inputs in the user turn.**
- **Feed continuity as explicit context near the TOP** (prior-episode summary, character sheet, canon)
  — above the instruction.
- **Ground continuity in quotes:** ask the model to cite the canon facts it must honor, then write.
- **Match prompt style to desired output** — a clean-prose prompt yields clean prose.
- **Enforce cross-episode consistency with a durable state file** (character sheet, canon log) that each
  call reads and updates.
- **Combat repetition by supplying "already-used" material as avoid-context**, not a blanket "be original".

## Prompt-file authoring & versioning
- **One prompt = one file**, named by purpose + version (`episode_generate.v3.jinja`).
- **Structure with XML tags** — `<role>`, `<context>`, `<canon>`, `<instructions>`, `<examples>`, `<input>`.
- **Variables use `{{DOUBLE_BRACE}}` placeholders**, substituted by the client wrapper — never scattered f-strings.
- **3–5 examples, relevant + diverse**, in `<example>` tags — multishot is the most reliable steering lever.
- **Bump the version on any semantic change**; never edit a released prompt in place if callers pin it.
- **Iterate against an eval set, not vibes** — flip a change in only when its eval passes.

## Anti-patterns (reject in review)
Inline prompt strings · prefilled assistant turns · missing `max_tokens` · vague/contradictory
constraints · over-stuffed instructions instead of `<example>`s · `CRITICAL`/all-caps coercion ·
role-play/flattery instead of direction · "only output JSON" as the sole guarantee where Structured
Outputs exists · assuming Structured Outputs enforces value constraints · negative-only formatting instructions.
