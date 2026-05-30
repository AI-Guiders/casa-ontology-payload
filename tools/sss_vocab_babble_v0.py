#!/usr/bin/env python3
"""Babble vocabulary from scene cue — field L: links + W: votes only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import ensure_cylinders  # type: ignore
from sss_vocab_v0 import recall_words_for_scene  # type: ignore


def babble_scene(state: dict, scene_id: str, *, top_k: int = 8) -> dict[str, Any]:
    ranked = recall_words_for_scene(state, scene_id)[:top_k]
    words = [r["word"] for r in ranked]
    if words:
        text = " ".join(words)
        babble = f"Слышал на странице: {text}."
    else:
        babble = "…"
    return {
        "scene_id": scene_id,
        "babble_text": babble,
        "words": ranked,
        "word_count": len(words),
    }


def babble_paragraph_caption(state: dict, caption: str, scene_id: str) -> dict[str, Any]:
    out = babble_scene(state, scene_id)
    out["caption"] = caption[:120]
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--scene-id", required=True)
    p.add_argument("--caption", default="")
    p.add_argument("--top-k", type=int, default=8)
    args = p.parse_args()

    state = ensure_cylinders(load_field_state(args.store_dir / "field_state.json"))
    out = babble_paragraph_caption(state, args.caption, args.scene_id)
    out["top_k"] = args.top_k
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
