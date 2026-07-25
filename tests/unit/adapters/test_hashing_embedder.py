"""Unit tests for the offline `HashingEmbedder`.

No I/O, no randomness — pure determinism and shape checks. See the class docstring: this
embedder is deliberately NOT semantically accurate, so these tests assert the contract
(determinism, fixed width, normalisation), never meaning.
"""

import math

from story_engine.adapters.outbound.embedding.hashing_embedder import HashingEmbedder


def test_same_text_embeds_identically_twice() -> None:
    embedder = HashingEmbedder()
    assert embedder.embed("Kael knelt before the crown.") == embedder.embed(
        "Kael knelt before the crown."
    )


def test_dimensionality_is_fixed_regardless_of_input_length() -> None:
    embedder = HashingEmbedder(dimensions=64)
    assert len(embedder.embed("a")) == 64
    assert (
        len(
            embedder.embed(
                "A much longer piece of narrative text about grief and loyalty."
            )
        )
        == 64
    )


def test_empty_string_does_not_crash() -> None:
    embedder = HashingEmbedder(dimensions=32)
    vector = embedder.embed("")
    assert len(vector) == 32
    assert all(component == 0.0 for component in vector)


def test_vectors_are_l2_normalised() -> None:
    embedder = HashingEmbedder()
    vector = embedder.embed("The crown belongs to no one now.")
    norm = math.sqrt(sum(component * component for component in vector))
    assert math.isclose(norm, 1.0, rel_tol=1e-9)


def test_different_texts_give_different_vectors() -> None:
    embedder = HashingEmbedder()
    assert embedder.embed("grief and loss") != embedder.embed("triumph and glory")
