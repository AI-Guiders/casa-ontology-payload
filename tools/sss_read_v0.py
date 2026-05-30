#!/usr/bin/env python3
"""Read-aloud session: story scenes → listen words on L2 (text modality)."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms, run_sleep, save_state  # type: ignore
from sss_vocab_v0 import apply_story_compose, listen_scene  # type: ignore


def read_session(
    state: dict,
    session: dict,
    *,
    bundle: dict | None = None,
) -> dict[str, Any]:
    state = ensure_prisms(state)
    copies = max(1, int(session.get("listen_copies") or 3))
    scenes = list(session.get("scenes") or [])
    if bundle:
        apply_story_compose(state, bundle)

    state["sn"] = {
        **(state.get("sn") or {}),
        "mode": "listen",
        "active_lattice": "L2_word",
        "active_prism": "prism_memory",
    }

    frames: list[dict] = []
    words_heard: set[str] = set()
    for sc in scenes:
        fr = listen_scene(state, sc, copies=copies, bundle=bundle)
        frames.append(fr)
        for item in fr.get("words") or []:
            words_heard.add(str(item.get("word") or ""))

    report: dict[str, Any] = {
        "session_id": f"read-{int(time.time() * 1000) % 10_000_000}",
        "title": session.get("title"),
        "modality": session.get("modality") or "text",
        "scenes_read": len(frames),
        "words_unique": sorted(w for w in words_heard if w),
        "frames": frames,
        "field_version": state.get("field_version"),
    }

    if session.get("sleep") and bundle:
        report["sleep"] = run_sleep(state, bundle)

    vocab = state.setdefault("vocab", {})
    history = list(vocab.get("read_sessions") or [])
    history.append(
        {
            "id": report["session_id"],
            "title": session.get("title"),
            "words": report["words_unique"],
            "scenes": report["scenes_read"],
        }
    )
    vocab["read_sessions"] = history[-16:]
    vocab["last_read"] = history[-1]
    state["sn"] = {**(state.get("sn") or {}), "mode": "wake", "active_lattice": "L2_word"}
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Read story session — text scenes, word listen on L2")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--session", type=Path, required=True)
    p.add_argument("--bundle", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    path = store / "field_state.json"
    session = json.loads(args.session.read_text(encoding="utf-8"))
    bundle = None
    if args.bundle:
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    elif (store / "bundles").exists():
        for name in ("kb-skazka-primer-v1.payload.json", "kb-bukvar-ru-full-v1.payload.json"):
            bp = store / "bundles" / name
            if bp.exists():
                bundle = json.loads(bp.read_text(encoding="utf-8"))
                break

    state = ensure_prisms(load_field_state(path))
    report = read_session(state, session, bundle=bundle)
    save_state(path, state)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
