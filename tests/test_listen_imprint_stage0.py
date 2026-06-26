#!/usr/bin/env python3
"""Stage 0 — listen/imprint gate (pytest wrapper for verify_listen_imprint)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.verify_listen_imprint import SCENE, run_probe


def test_listen_scene_retains_words_on_field() -> None:
    result = run_probe(isolated=True, impulse=False, require_audio=True, with_words=False)
    assert int(result.get("field_version_after") or 0) > int(result.get("field_version_before") or 0)
    assert not (result.get("recalled") or [])
    assert any(str(t).startswith("A:energy:") for t in (result.get("auditory_tokens") or []))


def test_listen_imprint_impulse_nodes(tmp_path: Path) -> None:
    store = tmp_path / "agent"
    store.mkdir()
    result = run_probe(isolated=True, impulse=True, store_dir=store, require_audio=True, with_words=False)
    impulse = result.get("impulse")
    assert isinstance(impulse, dict)
    assert impulse.get("event_count", 0) >= 3
