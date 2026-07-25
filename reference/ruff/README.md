# Ruff — Story Engine reference note

> Astral's Rust-based Python linter + formatter — one tool replacing Flake8, isort, pyupgrade, and Black at high speed.

- **Version pin (ours):** `ruff>=0.6`
- **Latest stable (verified):** 0.16.0 (released 2026-07-23; checked 2026-07). ⚠️ **Breaking:** 0.16.0 enables a much larger default rule set (413, up from 59) and can format Python in Markdown. We pin exact rule families and run `ruff format` explicitly, so our config is unaffected — but an unpinned `>=0.6` **will pull 0.16.x**.
- **Upstream `llms.txt`:** yes — vendored at `./llms.txt`. No `llms-full.txt` (append `index.md` to any doc URL for raw markdown).
- **Docs home:** https://docs.astral.sh/ruff/

## How Story Engine uses it
- `ruff check` with rule families `E,W,F,I,UP,B,C4,SIM,TID,PTH,RET,RUF`; `E501` (line length) ignored because the formatter owns wrapping.
- `ruff format` (Black-compatible) owns layout; line length 88.
- The `I` family replaces isort; `UP` (pyupgrade) autofixes legacy typing (`List` → `list`, `Optional[X]` → `X | None`) — matches our modern-type-hints hard constraint.
- Part of `make check` and pre-commit, run as `ruff check --fix` **before** `ruff format`.

## Read this for… (task → doc link)
- Browse/verify which rules a family enables → https://docs.astral.sh/ruff/rules/
- Configure `select`/`ignore`, line-length, per-file ignores → https://docs.astral.sh/ruff/configuration/
- Formatter behavior & Black deviations → https://docs.astral.sh/ruff/formatter/ · https://docs.astral.sh/ruff/formatter/black/
- Linter concepts / looking up a specific rule → https://docs.astral.sh/ruff/linter/
- Versioning + stable-vs-preview (before moving off 0.6) → https://docs.astral.sh/ruff/versioning/ · https://docs.astral.sh/ruff/preview/
- Editor/CI integrations → https://docs.astral.sh/ruff/integrations/

## Gotchas that bite us
- **`E501` is intentionally ignored** — the formatter wraps to 88; don't hand-fix a long line or re-enable E501 (unwrappable strings/comments are the exception).
- **Ordering matters:** `ruff check --fix` *before* `ruff format`. The linter rewrites code (import sorting, `UP`); the formatter then normalizes layout. Reversing leaves a dirty diff.
- **`SIM`/`RUF` autofixes can change semantics in edge cases** — review autofixed diffs; some fixes are "unsafe" and only apply with `--unsafe-fixes`.
- **Version drift on `>=0.6`:** 0.16.0 broadened defaults massively. Our explicit `select` shields us, but anyone relying on Ruff's *default* set instead of our list will see many new diagnostics on upgrade.

_Sources: github.com/astral-sh/ruff/releases (incl. 0.16.0 tag), docs.astral.sh/ruff/rules, vendored llms.txt. Verified 2026-07-24._
