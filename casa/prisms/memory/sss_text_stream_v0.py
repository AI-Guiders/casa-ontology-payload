#!/usr/bin/env python3
"""Char-by-char text scan — same stream as regex tokenizer, no re on hot path."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import unicodedata
from typing import Any, Literal

TokenKind = Literal["word", "punct"]

_CYR = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")
_PUNCT = set(".!,;:?…—-«»\"()")


def norm_text(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def _is_cyr(ch: str) -> bool:
    return ch.lower() in _CYR


def scan_stream(text: str, *, min_word_len: int = 1) -> list[dict[str, Any]]:
    """Tokens in reading order — char scan, lowercased words."""
    t = norm_text(text).lower()
    out: list[dict[str, Any]] = []
    buf: list[str] = []
    punct_buf: list[str] = []

    def flush_word() -> None:
        nonlocal buf
        if buf:
            s = "".join(buf)
            if len(s) >= min_word_len:
                out.append({"kind": "word", "surface": s})
            buf = []

    def flush_punct() -> None:
        nonlocal punct_buf
        for mark in punct_buf:
            out.append({"kind": "punct", "surface": mark})
        punct_buf = []

    for ch in t:
        if _is_cyr(ch):
            flush_punct()
            buf.append(ch)
        elif ch in _PUNCT:
            flush_word()
            punct_buf.append(ch)
        else:
            flush_word()
            flush_punct()

    flush_word()
    flush_punct()
    return out


def scan_words_ordered(text: str, *, min_len: int = 1) -> list[str]:
    return [str(t["surface"]) for t in scan_stream(text, min_word_len=min_len) if t["kind"] == "word"]


def scan_paragraphs_to_scenes(text: str, *, prefix: str = "p") -> list[dict]:
    from sss_text_tokenize_v0 import split_paragraphs  # type: ignore

    scenes: list[dict] = []
    for i, para in enumerate(split_paragraphs(text)):
        stream = scan_stream(para)
        words = [t["surface"] for t in stream if t["kind"] == "word"]
        punct = [t["surface"] for t in stream if t["kind"] == "punct"]
        scenes.append(
            {
                "id": f"{prefix}{i + 1}",
                "caption": para[:240],
                "words": list(dict.fromkeys(words)),
                "punctuation": list(dict.fromkeys(punct)),
                "tokens": len(stream),
                "stream_mode": "char_scan",
            }
        )
    return scenes
