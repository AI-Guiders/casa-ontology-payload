"""Deterministic asserts for the T9 predictor ranking core (no store boot, no NCA).

Complements the bench_* scripts: benches *measure*, these *assert* the ranking
contract so a logic regression fails CI even when numbers stay plausible.
"""

from __future__ import annotations

import math

from sss_l2_shard_v0 import L2_CONCEPT_PREFIX  # type: ignore

from predictor_v0 import (  # type: ignore
    DEFAULT_T9_WEIGHTS,
    T9Weights,
    _prefix_from_index,
    _t9_score,
    build_l2_prefix_index,
    detect_lexicon_miss,
    word_anchors_from_ranked,
)


def _digest(*pairs: tuple[str, int]) -> list[tuple[str, int]]:
    return [(f"{L2_CONCEPT_PREFIX}{w}", v) for w, v in pairs]


def test_prefix_index_ranks_shorter_completion_first() -> None:
    index = build_l2_prefix_index(_digest(("cow", 5), ("code", 3), ("cobra", 1), ("dog", 9)))
    ranked = _prefix_from_index(index, "co", top_k=8)
    assert [w for w, _ in ranked] == ["cow", "code", "cobra"]
    assert "dog" not in {w for w, _ in ranked}


def test_non_prefix_scores_negative_infinity() -> None:
    assert _t9_score("dog", 9, "co") == float("-inf")
    assert _t9_score("cow", 5, "co") > 0


def test_weights_override_flips_ranking() -> None:
    index = build_l2_prefix_index(_digest(("cow", 1), ("code", 10)))
    # High vote weight: the strongly-voted longer word wins.
    by_votes = _prefix_from_index(index, "co", weights=DEFAULT_T9_WEIGHTS)
    assert [w for w, _ in by_votes] == ["code", "cow"]
    # Drop the vote term: ranking falls back to the shorter completion.
    by_length = _prefix_from_index(index, "co", weights=T9Weights(vote=0.0))
    assert [w for w, _ in by_length] == ["cow", "code"]


def test_word_anchors_normalize_activation() -> None:
    anchors = word_anchors_from_ranked([("cow", 5), ("code", 3)])
    assert [a["word"] for a in anchors] == ["cow", "code"]
    assert [a["rank"] for a in anchors] == [1, 2]
    assert anchors[0]["activation"] == 1.0
    assert math.isclose(anchors[1]["activation"], 0.6, abs_tol=1e-6)


def test_lexicon_miss_signal() -> None:
    assert detect_lexicon_miss("co", [])["miss"] is True
    assert detect_lexicon_miss("co", [("cow", 5)])["miss"] is False
    assert detect_lexicon_miss("", [])["miss"] is False


def test_default_weights_contract() -> None:
    assert DEFAULT_T9_WEIGHTS.freq_min_prefix == 3
    assert DEFAULT_T9_WEIGHTS.vote > DEFAULT_T9_WEIGHTS.length_penalty
