"""Small, focused text helpers.

A *named* module, not a catch-all `utils.py` (see the anti-utils rule in
.claude/rules/python-design.md). Add a new focused module rather than growing this
one into a dumping ground.
"""

import re

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Return a lowercase, hyphenated slug of `value` (e.g. 'The Return!' -> 'the-return')."""
    return _SLUG_STRIP.sub("-", value.strip().lower()).strip("-")


def truncate(value: str, limit: int, *, suffix: str = "…") -> str:
    """Truncate `value` to at most `limit` characters, appending `suffix` when cut."""
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if len(value) <= limit:
        return value
    return value[: max(0, limit - len(suffix))] + suffix
