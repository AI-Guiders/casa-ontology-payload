#!/usr/bin/env python3
"""Tests for YouTube chapter → listen manifest (no network)."""

from __future__ import annotations

import json
from pathlib import Path

from tools.yt_chapters_listen_cold import (
    build_chapter_manifest,
    chapters_from_yt_info,
    youtube_video_id,
)


def test_youtube_video_id() -> None:
    assert youtube_video_id("https://www.youtube.com/watch?v=IixOLmEcKtk") == "IixOLmEcKtk"
    assert youtube_video_id("https://youtu.be/abc123XYZ") == "abc123XYZ"


def test_chapters_from_description_fallback() -> None:
    info = {
        "duration": 200.0,
        "description": "intro\n00:00 Противоположности\n02:42 Живая азбука\n",
    }
    ch = chapters_from_yt_info(info)
    assert len(ch) == 2
    assert ch[0]["title"].startswith("Противоположности")
    assert ch[0]["t0"] == 0.0
    assert ch[1]["t0"] == 162.0


def test_build_manifest_no_words(tmp_path: Path) -> None:
    info = {
        "id": "IixOLmEcKtk",
        "title": "Лалабук сборник",
        "language": "ru",
        "chapters": [
            {"start_time": 0.0, "end_time": 10.0, "title": "Противоположности"},
            {"start_time": 10.0, "end_time": 20.0, "title": "Живая азбука"},
        ],
    }
    bundle = tmp_path / "IixOLmEcKtk"
    bundle.mkdir()
    scenes = build_chapter_manifest(
        bundle_dir=bundle,
        info=info,
        publisher="lalabook",
        collection="speech-dev",
        speaker="narrator",
        profile="bind",
        with_frames=False,
        video_path=None,
    )
    assert len(scenes) == 2
    assert "words" not in scenes[0]
    assert scenes[0]["profile"] == "bind"
    assert scenes[0]["wav"] == "audio.wav"
    assert scenes[0]["t1"] == 10.0
    assert scenes[0].get("caption")


def test_listen_corpus_root_default() -> None:
    from casa._paths import REPO_ROOT
    from casa.prisms.shared.listen_corpus_layout import listen_corpus_root

    assert listen_corpus_root() == (REPO_ROOT.parent / "casa-listen-corpus").resolve()


def test_chapters_prefers_description_when_richer() -> None:
    info = {
        "duration": 4034.0,
        "chapters": [
            {"start_time": 0.0, "end_time": 1576.0, "title": "first"},
            {"start_time": 1576.0, "end_time": 4034.0, "title": "second"},
        ],
        "description": "00:00 One\n03:21 Two\n11:37 Three\n",
    }
    ch = chapters_from_yt_info(info)
    assert len(ch) == 3
    assert ch[0]["t0"] == 0.0
    assert ch[1]["t0"] == 201.0
    assert ch[2]["t0"] == 697.0


def test_fixture_lalabook_info_chapters() -> None:
    fixture = Path(__file__).parent / "fixtures" / "lalabook_video.info.sample.json"
    if not fixture.is_file():
        return
    info = json.loads(fixture.read_text(encoding="utf-8"))
    ch = chapters_from_yt_info(info)
    assert len(ch) >= 3
