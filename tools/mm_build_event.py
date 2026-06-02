#!/usr/bin/env python3
"""Build a canonical mm_event JSON (or append to JSONL) from OCR+ASR outputs.

This tool is intentionally dependency-free: perception (capture/OCR/ASR) is done elsewhere.

Typical usage (operator pipeline):
- capture webcam burst + audio wav (external tooling)
- OCR burst dir -> ocr.json (external tooling)
- Whisper wav -> asr.json (external tooling)
- build mm_event -> append to events.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from time import time
from typing import Any, Iterable


def _norm_words(words: Iterable[str]) -> list[str]:
    out: list[str] = []
    for w in words:
        w = str(w or "").strip().lower()
        if w:
            out.append(w)
    return list(dict.fromkeys(out))


_PUNCT_CHARS = set(list("+-−×*/÷=→()[]«»,.!?;:—…"))
_RE_NUM_FRAC = re.compile(r"\b\d+\s*/\s*\d+\b")
_RE_STICK_HEAP = re.compile(r"\(\|+\)")


def _extract_punctuation(items: Iterable[str]) -> list[str]:
    marks: list[str] = []
    for s in items:
        for ch in str(s or ""):
            if ch in _PUNCT_CHARS:
                marks.append(ch)
    return list(dict.fromkeys(marks))


def _extract_math_glyphs(texts: Iterable[str]) -> list[str]:
    out: list[str] = []
    for t in texts:
        t = str(t or "")
        out.extend(m.group(0).replace(" ", "") for m in _RE_NUM_FRAC.finditer(t))
        out.extend(m.group(0) for m in _RE_STICK_HEAP.finditer(t))
    return list(dict.fromkeys([x for x in out if x]))


def _read_json(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_asr_text(asr: dict[str, Any]) -> str:
    for key in ("text", "asr_text", "transcript"):
        if str(asr.get(key) or "").strip():
            return str(asr.get(key) or "").strip()
    # whisper-like segments
    segs = asr.get("segments") or []
    if isinstance(segs, list):
        txt = " ".join(str(s.get("text") or "").strip() for s in segs if isinstance(s, dict))
        return re.sub(r"\s+", " ", txt).strip()
    return ""


def _pick_ocr_text(ocr: dict[str, Any]) -> str:
    # our OCR MCP typically returns {"pages":[{"text":...},...]}
    pages = ocr.get("pages") or ocr.get("images") or []
    if isinstance(pages, list):
        txt = " ".join(str(p.get("text") or "").strip() for p in pages if isinstance(p, dict))
        return re.sub(r"\s+", " ", txt).strip()
    return str(ocr.get("text") or "").strip()


def build_event(
    *,
    event_id: str,
    asr: dict[str, Any] | None = None,
    ocr: dict[str, Any] | None = None,
    words: list[str] | None = None,
    context: list[str] | None = None,
    extra_math_glyphs: list[str] | None = None,
) -> dict[str, Any]:
    asr = asr or {}
    ocr = ocr or {}
    asr_text = _pick_asr_text(asr)
    ocr_text = _pick_ocr_text(ocr)

    canon_words = _norm_words(words or [])
    if not canon_words:
        canon_words = _norm_words(re.findall(r"[\w\-]+", asr_text, flags=re.UNICODE))

    math_glyphs = _extract_math_glyphs([asr_text, ocr_text])
    if extra_math_glyphs:
        math_glyphs = list(dict.fromkeys([*math_glyphs, *[str(x) for x in extra_math_glyphs if str(x).strip()]]))
    punct = _extract_punctuation([asr_text, ocr_text, *math_glyphs])

    return {
        "schema_version": 1,
        "event_id": event_id,
        "ts_ms": int(time() * 1000),
        "window_ms": None,
        "audio": {"asr_text": asr_text, "asr_words": asr.get("segments") or asr.get("words") or []},
        "vision": {"ocr_text": ocr_text, "glyphs": ocr.get("glyphs") or [], "objects": ocr.get("objects") or []},
        "canon": {
            "context": context or [],
            "words": canon_words,
            "math_glyphs": math_glyphs,
            "punctuation": punct,
        },
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Build mm_event JSON from OCR+ASR outputs")
    p.add_argument("--event-id", required=True)
    p.add_argument("--asr-json", type=Path, default=None, help="ASR JSON (e.g. Whisper output saved to file)")
    p.add_argument("--ocr-json", type=Path, default=None, help="OCR JSON (e.g. ocr.json from batch OCR)")
    p.add_argument("--word", action="append", default=None, help="Force-add a canonical word (repeatable)")
    p.add_argument("--context", action="append", default=None, help="Context tags (repeatable), e.g. heap_model:fraction")
    p.add_argument("--math-glyph", action="append", default=None, help="Force-add a math glyph cue (repeatable)")
    p.add_argument("--out", type=Path, default=None, help="Write single JSON to this path")
    p.add_argument("--append-jsonl", type=Path, default=None, help="Append one line JSON to this JSONL")
    args = p.parse_args()

    ev = build_event(
        event_id=str(args.event_id),
        asr=_read_json(args.asr_json) if args.asr_json else {},
        ocr=_read_json(args.ocr_json) if args.ocr_json else {},
        words=list(args.word or []),
        context=list(args.context or []),
        extra_math_glyphs=list(args.math_glyph or []),
    )

    if args.out:
        args.out.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.append_jsonl:
        args.append_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.append_jsonl.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    if not args.out and not args.append_jsonl:
        print(json.dumps(ev, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

