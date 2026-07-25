"""Wiki index sink port — where a finished entity vocabulary is written.

Kept separate from `WikiSourcePort` so the knowledge-base session can consume the artifact without
this pipeline knowing anything about their storage. The written artifact — not a shared Python type —
is the integration contract (see `adapters/outbound/wiki/jsonl_index_sink.py`).
"""

from typing import Protocol

from story_engine.domain.models.wiki_index import WikiEntityIndex


class WikiSinkPort(Protocol):
    """Persist a harvested entity vocabulary."""

    def write(self, index: WikiEntityIndex) -> str:
        """Persist `index` and return a human-readable location."""
        ...
