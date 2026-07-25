"""Shared pytest configuration: mark every test by the tier its directory declares.

`feature_list.json` verifies features with commands like `pytest -m unit -k epistemic`. Those
commands selected **nothing**, because `unit` was never a registered marker and unit tests were
never marked — so the command exited "no tests collected" and the feature could never flip to
passing however good the code was (recorded as AUD-M3).

Marking by hand in ~40 files would rot: a new test file added without the marker silently drops out
of the tier it lives in, and a tier that quietly shrinks still looks green. Deriving the marker from
the directory means the layout *is* the declaration, and `tests/unit/...` cannot be anything but a
unit test.
"""

from pathlib import Path

import pytest

TIER_BY_DIRECTORY = {"unit": "unit", "integration": "integration", "e2e": "e2e"}


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Apply `unit` / `integration` / `e2e` based on which tests/ subdirectory a test lives in.

    Additive only: a file that already declares `pytestmark` keeps it, and applying the same marker
    twice is harmless. Nothing here can remove a marker a test asked for.
    """
    root = Path(str(config.rootpath)) / "tests"
    for item in items:
        try:
            relative = Path(str(item.path)).relative_to(root)
        except ValueError:
            continue  # a test collected from outside tests/ — leave it alone
        if not relative.parts:
            continue
        tier = TIER_BY_DIRECTORY.get(relative.parts[0])
        if tier is not None:
            item.add_marker(getattr(pytest.mark, tier))
