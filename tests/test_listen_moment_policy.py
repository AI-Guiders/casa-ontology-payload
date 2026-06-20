#!/usr/bin/env python3
"""Listen moment policy — fields not kinds."""

from __future__ import annotations

from casa.domain.listen_moment_policy import (
    is_multi_speaker,
    scene_speakers,
    scene_words,
    wants_lexical_imprint,
)


def test_no_words_by_default() -> None:
    assert scene_words({}) == []
    assert not wants_lexical_imprint(scene_words({}))


def test_explicit_words_only() -> None:
    words = scene_words({"words": ["маша"]})
    assert words == ["маша"]
    assert wants_lexical_imprint(words)


def test_multi_speaker_from_fields() -> None:
    speakers = scene_speakers({"speakers": ["masha", "medved"], "speaker": "masha"})
    assert speakers == ["masha", "medved"]
    assert is_multi_speaker(speakers)
    assert not is_multi_speaker(["masha"])
