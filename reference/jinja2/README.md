# Jinja2 — Story Engine reference note

> Fast, sandbox-capable Python template engine — Story Engine uses it to render versioned prompt
> templates from disk with strict, fail-loud variable handling.

- **Version pin (ours):** `jinja2>=3`
- **Latest stable (verified):** 3.1.6 (released 2025-03-05; checked 2026-07)
- **Upstream `llms.txt`:** none published — use the docs site.
- **Docs home:** https://jinja.palletsprojects.com/en/stable/

## How Story Engine uses it
- `FilePromptStore` builds one `Environment(loader=FileSystemLoader(root), undefined=StrictUndefined, autoescape=False, keep_trailing_newline=True)` and renders `prompts/<name>/<version>.jinja`.
- `StrictUndefined` is deliberate: a missing prompt variable raises `UndefinedError` on access/print/iteration rather than silently rendering an empty string — a broken prompt fails loud instead of shipping a blank to the LLM.
- `autoescape=False` because prompt output is plain prose sent to an LLM, not HTML — no entity-escaping wanted.
- `keep_trailing_newline=True` preserves the template's final newline (Jinja strips it by default), so the rendered prompt matches the file byte-for-byte and stays a clean reviewable diff.
- Prompts are versioned file assets loaded through the port, never string literals in code.

## Read this for… (task → doc link)
- Configure the `Environment` (loaders, undefined, autoescape, `keep_trailing_newline`) → https://jinja.palletsprojects.com/en/stable/api/#jinja2.Environment
- Pick an undefined type (`Undefined`, `ChainableUndefined`, `DebugUndefined`, `StrictUndefined`) → https://jinja.palletsprojects.com/en/stable/api/#undefined-types
- Wire file-based template loading (`FileSystemLoader`) → https://jinja.palletsprojects.com/en/stable/api/#jinja2.FileSystemLoader
- Write/maintain template syntax (variables, filters, control structures, whitespace control) → https://jinja.palletsprojects.com/en/stable/templates/
- Sandbox untrusted template authors (`SandboxedEnvironment`) → https://jinja.palletsprojects.com/en/stable/sandbox/

## Gotchas that bite us
- **StrictUndefined fails at use, not at render start:** it raises the moment an undefined value is printed/iterated/tested — a template that references a missing var only in an untaken branch won't error, so missing-variable coverage depends on which paths execute.
- **`autoescape=False` is correct for prose but a live XSS foot-gun if this Environment is ever reused to emit HTML.** The off setting is scoped to prompt rendering only; don't reuse the same Environment for web output.
- **Plain `Environment` does NOT sandbox** — it can execute arbitrary attribute access/method calls in templates. Fine while prompt authors are trusted teammates; if templates ever come from untrusted users, switch to `SandboxedEnvironment` (`jinja2.sandbox`).
- **Whitespace control still affects diffs:** `keep_trailing_newline=True` guards the final newline, but `trim_blocks`/`lstrip_blocks` (both off by default) alter block whitespace if changed.

_Sources: pypi.org/project/Jinja2, jinja.palletsprojects.com/en/stable/api, github.com/pallets/jinja/releases. Verified 2026-07-24._
