# Prompts

Prompt templates are **versioned assets**, not string literals in code (see
`.claude/rules/llm-storytelling.md` and `.claude/rules/prompts.md`). They are loaded through the
`PromptStorePort` adapter, so behavior changes are reviewable diffs and rollbacks are one-line.

## Convention
```
prompts/<name>/v<N>.jinja
```
- `<name>` = the job (`episode_generation`, `character_voice`, `plot_branching`).
- `v<N>` = a version bumped on any wording/behavior change. **Never edit a shipped version in place** —
  add `vN+1` so old generations stay reproducible.
- Production references a specific version (or an alias like `production`), never "latest by accident".
- Document each template's expected variables at the top of the file.

## House versioning rule
- **minor change** (wording, tone) → bump the version number.
- **major change** (output schema / behavior contract) → bump the version **and** update the code/tests
  that depend on its shape.
