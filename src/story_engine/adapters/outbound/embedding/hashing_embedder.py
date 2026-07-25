"""Offline, dependency-free embedder — the default `EmbedderPort` implementation.

No network calls, no model download: hashes character n-grams into a fixed-width vector via
SHA-256 (not the builtin `hash()`, which is salted per-process by `PYTHONHASHSEED` and would
break the "same input, same vector" contract), then L2-normalises.
"""

import hashlib
import math


class HashingEmbedder:
    """Deterministic bag-of-character-n-grams embedder.

    This is NOT a semantically meaningful embedder — two texts about the same topic in
    different words will usually score low. Its job is to make the embed → store → search
    pipeline real, testable, and swappable offline, not to be accurate. Swap in a real model
    behind `EmbedderPort` (see `ports/embedder.py`) once one is available.
    """

    def __init__(self, dimensions: int = 256, n: int = 3) -> None:
        """Configure the vector width and character n-gram size.

        Args:
            dimensions: Fixed width of every embedding this instance produces.
            n: Character n-gram size used to build the bag of features.
        """
        self.dimensions = dimensions
        self._n = n

    def embed(self, text: str) -> tuple[float, ...]:
        """Return a deterministic, L2-normalised vector of length `dimensions`.

        Same `text` always yields the same vector (no randomness, no process-local salt).
        An empty (or shorter-than-`n`) string yields a zero vector rather than crashing.
        """
        vector = [0.0] * self.dimensions
        for gram in self._ngrams(text):
            digest = hashlib.sha256(gram.encode("utf-8")).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(component * component for component in vector))
        if norm == 0.0:
            return tuple(vector)
        return tuple(component / norm for component in vector)

    def _ngrams(self, text: str) -> list[str]:
        """Character n-grams of the normalised text; the whole string if shorter than n."""
        normalized = text.lower().strip()
        if not normalized:
            return []
        if len(normalized) < self._n:
            return [normalized]
        return [
            normalized[i : i + self._n] for i in range(len(normalized) - self._n + 1)
        ]
