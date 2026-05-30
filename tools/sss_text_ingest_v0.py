#!/usr/bin/env python3
"""
Ingest plain text: extract words + punctuation → listen on L2/L3.

Three input modes (lab):
  1) structured session JSON (hand-made scenes)
  2) real tale .txt (paragraphs → auto scenes)
  3) future: NCA stream — same API, tokenizer replaced by field dynamics
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from field_write import load_field_state  # type: ignore
from gen_kb_from_text_v0 import build_bundle_from_text  # type: ignore
from sss_cylinders_v0 import ensure_prisms, run_sleep, save_state  # type: ignore
from sss_read_v0 import read_session  # type: ignore
from sss_text_tokenize_v0 import extract_punctuation_unique, extract_words, norm_text, paragraphs_to_scenes  # type: ignore
from sss_vocab_v0 import punct_votes_from_field, word_votes_from_field  # type: ignore


def ingest_text(
    state: dict,
    text: str,
    *,
    title: str = "text ingest",
    bukvar_bundle: dict | None = None,
    listen_copies: int = 2,
    sleep: bool = True,
    min_word_len: int = 1,
) -> dict[str, Any]:
    """
    Agent hears running text; words extracted from signal (not from labeled cards).
    Returns discovered vs reinforced based on W: votes before listen.
    """
    state = ensure_prisms(state)
    before_w = word_votes_from_field(state)
    before_p = punct_votes_from_field(state)
    dynamic = build_bundle_from_text(text, bukvar_bundle=bukvar_bundle, title=title)

    scenes = paragraphs_to_scenes(text)

    session = {
        "title": title,
        "modality": "text_stream",
        "listen_copies": listen_copies,
        "sleep": sleep,
        "scenes": scenes,
        "source": "text_extract",
    }
    report = read_session(state, session, bundle=dynamic)
    after_w = word_votes_from_field(state)
    after_p = punct_votes_from_field(state)

    discovered: list[str] = []
    reinforced: list[str] = []
    for w in extract_words(text, min_len=min_word_len):
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
        "words_total": len(extract_words(text, min_len=min_word_len)),
        "words_unique": dynamic.get("extract", {}).get("words"),
        "word_syllables": dynamic.get("extract", {}).get("word_syllables"),
        "punctuation_unique": dynamic.get("extract", {}).get("punctuation"),
        "discovered": discovered,
        "reinforced": reinforced,
        "punct_discovered": punct_discovered,
        "paragraphs": len(scenes),
    }
    report["ingest_mode"] = "text_stream"
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest plain text tale — words + punctuation from stream")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--text", type=Path, required=True, help="Plain UTF-8 tale (real or generated)")
    p.add_argument("--bukvar", type=Path, default=Path("lab/kb/kb-bukvar-ru-full-v1.payload.json"))
    p.add_argument("--title", default=None)
    p.add_argument("--listen-copies", type=int, default=2)
    p.add_argument("--no-sleep", action="store_true")
    p.add_argument("--min-word-len", type=int, default=1)
    p.add_argument("--save-bundle", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    path = store / "field_state.json"
    text = norm_text(args.text.read_text(encoding="utf-8"))
    title = args.title or f"Читаем: {args.text.name}"

    bukvar = None
    if args.bukvar.exists():
        bukvar = json.loads(args.bukvar.read_text(encoding="utf-8"))

    dynamic = build_bundle_from_text(text, bukvar_bundle=bukvar, doc_path=str(args.text), title=title)
    if args.save_bundle:
        args.save_bundle.parent.mkdir(parents=True, exist_ok=True)
        args.save_bundle.write_text(json.dumps(dynamic, ensure_ascii=False, indent=2), encoding="utf-8")
        (store / "bundles").mkdir(exist_ok=True)
        (store / "bundles" / args.save_bundle.name).write_text(
            json.dumps(dynamic, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    state = ensure_prisms(load_field_state(path))
    report = ingest_text(
        state,
        text,
        title=title,
        bukvar_bundle=bukvar,
        listen_copies=max(1, args.listen_copies),
        sleep=not args.no_sleep,
        min_word_len=max(1, args.min_word_len),
    )
    report["session_id"] = report.get("session_id") or f"ingest-{int(time.time() * 1000) % 10_000_000}"

    ingest_hist = state.setdefault("text_ingest", {})
    hist = list(ingest_hist.get("sessions") or [])
    hist.append(
        {
            "id": report["session_id"],
            "title": title,
            "source": str(args.text),
            "words_unique": len(report.get("extract", {}).get("words_unique") or []),
            "discovered": len(report.get("extract", {}).get("discovered") or []),
        }
    )
    ingest_hist["sessions"] = hist[-24:]
    ingest_hist["last"] = hist[-1]

    save_state(path, state)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
