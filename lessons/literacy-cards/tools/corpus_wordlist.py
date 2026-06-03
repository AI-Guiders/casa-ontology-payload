#!/usr/bin/env python3
"""Build ru/en frequency wordlists for literacy corpus (authoring, not OCR)."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"

CYRILLIC_RE = re.compile(r"^[а-яё]+$", re.IGNORECASE)
LATIN_RE = re.compile(r"^[a-z]+$", re.IGNORECASE)


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def _filter_words(words: list[str], *, script: str, min_len: int, max_len: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    pat = CYRILLIC_RE if script == "ru" else LATIN_RE
    for raw in words:
        w = _nfc(raw.lower())
        if not w or w in seen:
            continue
        if len(w) < min_len or len(w) > max_len:
            continue
        if not pat.fullmatch(w):
            continue
        seen.add(w)
        out.append(w)
    return out


def _top_wordfreq(lang: str, n: int) -> list[str]:
    import wordfreq  # type: ignore

    code = "ru" if lang == "ru" else "en"
    return list(wordfreq.top_n_list(code, n * 3))


def _fallback_ru() -> list[str]:
    path = DATA / "ru-wordlist-seed.txt"
    if path.is_file():
        return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [
        "мама", "папа", "дом", "кот", "сок", "мир", "рука", "вода", "день", "ночь",
        "город", "улица", "школа", "учитель", "ребёнок", "работа", "время", "жизнь",
        "человек", "женщина", "мужчина", "друг", "любовь", "слово", "книга", "язык",
    ]


def _fallback_en() -> list[str]:
    path = DATA / "en-wordlist-seed.txt"
    if path.is_file():
        return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
        "you", "he", "with", "on", "do", "say", "this", "they", "at", "we",
        "mother", "father", "house", "cat", "water", "day", "night", "city", "school", "book",
    ]


def build_list(lang: str, *, n: int, min_len: int, max_len: int) -> list[str]:
    raw: list[str]
    try:
        raw = _top_wordfreq(lang, n)
        source = "wordfreq"
    except Exception:
        raw = _fallback_ru() if lang == "ru" else _fallback_en()
        source = "seed"
    words = _filter_words(raw, script=lang, min_len=min_len, max_len=max_len)[:n]
    return words, source


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--lang", choices=("ru", "en"), required=True)
    p.add_argument("-n", type=int, default=500)
    p.add_argument("--min-len", type=int, default=2)
    p.add_argument("--max-len", type=int, default=12)
    p.add_argument("-o", type=Path, default=None)
    args = p.parse_args()
    words, source = build_list(
        args.lang, n=args.n, min_len=args.min_len, max_len=args.max_len
    )
    out = args.o or DATA / f"{args.lang}-wordlist-v1.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(words) + "\n", encoding="utf-8")
    print(json.dumps({"lang": args.lang, "count": len(words), "source": source, "path": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
