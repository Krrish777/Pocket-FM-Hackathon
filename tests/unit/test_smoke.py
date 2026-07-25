"""Smoke test: proves the test harness runs and the package imports.

Replace/extend with real domain tests as features land. Per conventions, tests assert
structure/invariants — never exact LLM output (see
.claude/rules/testing.md).
"""

import importlib


def test_package_imports() -> None:
    """The story_engine package is importable from the src/ layout."""
    assert importlib.import_module("story_engine") is not None
