#!/usr/bin/env python3
"""Ortho compose: Capitalize atom, Upper/Lower as folds (ADR-0003 §7)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from sss_vocab_v0 import norm_word  # type: ignore

PROC_CAPITALIZE = "proc.grapheme.capitalize"
PROC_LOWER = "proc.grapheme.lower"
PROC_UPPER = "proc.word.upper"
PROC_LOWER_WORD = "proc.word.lower"
PROC_SENTENCE_CASE = "proc.word.sentence_case"


def capitalize_grapheme(ch: str) -> str:
    if not ch:
        return ch
    if len(ch) != 1:
        return ch
    if "a" <= ch <= "z":
        return ch.upper()
    if "\u0400" <= ch <= "\u04ff":
        return ch.upper() if ch.islower() else ch
    return ch


def lower_grapheme(ch: str) -> str:
    if not ch:
        return ch
    if len(ch) != 1:
        return ch
    return ch.lower()


def upper_word(word: str) -> str:
    return "".join(capitalize_grapheme(c) for c in word)


def lower_word(word: str) -> str:
    return "".join(lower_grapheme(c) for c in word)


def sentence_case_word(word: str) -> str:
    w = word
    if not w:
        return w
    return capitalize_grapheme(w[0]) + w[1:]


def apply_grapheme_proc(ch: str, proc_id: str) -> str | None:
    if proc_id == PROC_CAPITALIZE:
        return capitalize_grapheme(ch)
    if proc_id == PROC_LOWER:
        return lower_grapheme(ch)
    return None


def apply_word_proc(word: str, proc_id: str) -> str | None:
    if proc_id == PROC_UPPER:
        return upper_word(word)
    if proc_id == PROC_LOWER_WORD:
        return lower_word(word)
    if proc_id == PROC_SENTENCE_CASE:
        return sentence_case_word(word)
    return None


def same_lexeme(a: str, b: str) -> bool:
    return norm_word(a) == norm_word(b)
