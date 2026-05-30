#!/usr/bin/env python3
"""Text ingest via char scan + W: field competition (Phase B hot path)."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from field_write import load_field_state  # type: ignore
from gen_kb_from_text_v0 import build_bundle_from_text  # type: ignore
from sss_cylinders_v0 import ensure_cylinders, run_sleep, save_state  # type: ignore
from sss_field_words_v0 import listen_word_field  # type: ignore
from sss_text_stream_v0 import norm_text, scan_paragraphs_to_scenes, scan_stream  # type: ignore
from sss_text_tokenize_v0 import extract_punctuation_unique  # type: ignore
from sss_vocab_v0 import apply_story_compose, listen_punct, punct_votes_from_field, word_votes_from_field  # type: ignore


def read_session_field(
    state: dict,
    session: dict,
    *,
    bundle: dict | None = None,
) -> dict[str, Any]:
    state = ensure_cylinders(state)
    copies = max(1, int(session.get("listen_copies") or 3))
    scenes = list(session.get("scenes") or [])
    if bundle:
        apply_story_compose(state, bundle)

    state["sn"] = {
        **(state.get("sn") or {}),
        "mode": "listen_field",
        "active_lattice": "L2_word",
        "active_cylinder": "cyl_memory",
    }

    frames: list[dict] = []
    words_heard: set[str] = set()
    for sc in scenes:
        sid = str(sc.get("id") or "")
        caption = str(sc.get("caption") or "")
        words = [str(w) for w in (sc.get("words") or []) if str(w).strip()]
        punct = [str(p) for p in (sc.get("punctuation") or []) if str(p).strip()]

        from sss_vocab_v0 import _listen_scene_on_l3  # type: ignore

        _listen_scene_on_l3(state, sid, caption, words, copies=copies, punctuation=punct)
        heard_words: list[dict] = []
        for w in words:
            fr = listen_word_field(
                state,
                w,
                scene_id=sid,
                caption=caption,
                copies=copies,
                bundle=bundle,
                link_scene=False,
            )
            heard_words.append(fr)
            words_heard.add(str(fr.get("word") or ""))
        heard_punct: list[dict] = []
        for mark in punct:
            heard_punct.append(
                listen_punct(state, mark, scene_id=sid, caption=caption, copies=max(1, copies - 1), link_scene=False)
            )
        frames.append({"scene_id": sid, "caption": caption, "words": heard_words, "punctuation": heard_punct})

    report: dict[str, Any] = {
        "session_id": f"read-field-{int(time.time() * 1000) % 10_000_000}",
        "title": session.get("title"),
        "modality": session.get("modality") or "text_field",
        "scenes_read": len(frames),
        "words_unique": sorted(w for w in words_heard if w),
        "frames": frames,
        "field_version": state.get("field_version"),
        "ingest_mode": "char_scan_field",
    }

    if session.get("sleep") and bundle:
        report["sleep"] = run_sleep(state, bundle)

    state["sn"] = {**(state.get("sn") or {}), "mode": "wake", "active_lattice": "L2_word"}
    return report


def ingest_text_field(
    state: dict,
    text: str,
    *,
    title: str = "text field ingest",
    bukvar_bundle: dict | None = None,
    listen_copies: int = 2,
    sleep: bool = True,
    min_word_len: int = 1,
) -> dict[str, Any]:
    state = ensure_cylinders(state)
    before_w = word_votes_from_field(state)
    before_p = punct_votes_from_field(state)
    dynamic = build_bundle_from_text(text, bukvar_bundle=bukvar_bundle, title=title)
    scenes = scan_paragraphs_to_scenes(text)

    session = {
        "title": title,
        "modality": "text_field",
        "listen_copies": listen_copies,
        "sleep": sleep,
        "scenes": scenes,
        "source": "char_scan",
    }
    report = read_session_field(state, session, bundle=dynamic)
    after_w = word_votes_from_field(state)
    after_p = punct_votes_from_field(state)

    discovered: list[str] = []
    reinforced: list[str] = []
    for tok in scan_stream(text, min_word_len=min_word_len):
        if tok["kind"] != "word":
            continue
        w = str(tok["surface"])
        if before_w.get(w, 0) == 0 and after_w.get(w, 0) > 0:
            if w not in discovered:
                discovered.append(w)
        elif before_w.get(w, 0) > 0:
            if w not in reinforced:
                reinforced.append(w)

    punct_discovered: list[str] = []
    for mark in extract_punctuation_unique(text):
        if before_p.get(mark, 0) == 0 and after_p.get(mark, 0) > 0:
            punct_discovered.append(mark)

    report["extract"] = {
        "words_total": len([t for t in scan_stream(text, min_word_len=min_word_len) if t["kind"] == "word"]),
        "words_unique": dynamic.get("extract", {}).get("words"),
        "discovered": discovered,
        "reinforced": reinforced,
        "punct_discovered": punct_discovered,
        "paragraphs": len(scenes),
        "stream_mode": "char_scan",
    }
    report["ingest_mode"] = "char_scan_field"
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest text via char scan + W: field competition")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--text", type=Path, required=True)
    p.add_argument("--bukvar", type=Path, default=Path("examples/kb/kb-bukvar-ru-full-v1.payload.json"))
    p.add_argument("--title", default=None)
    p.add_argument("--listen-copies", type=int, default=2)
    p.add_argument("--no-sleep", action="store_true")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    path = store / "field_state.json"
    text = norm_text(args.text.read_text(encoding="utf-8"))
    title = args.title or f"Читаем (field): {args.text.name}"
    bukvar = json.loads(args.bukvar.read_text(encoding="utf-8")) if args.bukvar.exists() else None

    state = ensure_cylinders(load_field_state(path))
    report = ingest_text_field(
        state,
        text,
        title=title,
        bukvar_bundle=bukvar,
        listen_copies=max(1, args.listen_copies),
        sleep=not args.no_sleep,
    )
    save_state(path, state)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
