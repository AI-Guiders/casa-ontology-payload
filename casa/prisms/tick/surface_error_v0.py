#!/usr/bin/env python3
"""Classify surface error axis → correction_kind (CASA critic, not developmental psych)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from sss_vocab_v0 import norm_word  # type: ignore

ERROR_AXES = frozenset(
    {
        "script",
        "phonotactic",
        "prefix_incomplete",
        "lexical",
        "morph",
        "ortho",
        "none",
    }
)

CORRECTION_KINDS = frozenset(
    {
        "script_rule",
        "wait_prefix",
        "lexical_ask",
        "morph_surface",
        "ortho_surface",
    }
)

_AXIS_TO_KIND: dict[str, str] = {
    "script": "script_rule",
    "prefix_incomplete": "wait_prefix",
    "lexical": "lexical_ask",
    "morph": "morph_surface",
    "ortho": "ortho_surface",
    "phonotactic": "wait_prefix",
    "none": "wait_prefix",
}


def is_mixed_script(text: str) -> bool:
    """Unicode letter classes — meta-level error before lexical choice."""
    has_latn = False
    has_cyrl = False
    for ch in text:
        if len(ch) != 1 or ch in "-_'":
            continue
        if "a" <= ch.lower() <= "z":
            has_latn = True
        elif "\u0400" <= ch <= "\u04ff":
            has_cyrl = True
        if has_latn and has_cyrl:
            return True
    return False


def _is_strict_prefix(shorter: str, longer: str) -> bool:
    s, lg = norm_word(shorter), norm_word(longer)
    if not s or not lg or s == lg:
        return False
    return lg.startswith(s)


def _shared_stem(a: str, b: str, *, min_len: int = 3) -> bool:
    aa, bb = norm_word(a), norm_word(b)
    if not aa or not bb:
        return False
    n = min(len(aa), len(bb), max(min_len, min(len(aa), len(bb)) - 1))
    return aa[:n] == bb[:n]


def _looks_morph_not_lemma(attempt: str, target: str) -> bool:
    """Heuristic: same stem, target is inflected form (коров → коровий), not noun spelling fix."""
    a, t = norm_word(attempt), norm_word(target)
    if not a or not t or a == t:
        return False
    if not _shared_stem(a, t):
        return False
    if t.endswith(("ий", "ый", "ая", "ое", "ые", "ого", "ому")):
        return a.startswith(t[: max(3, len(t) - 2)]) or t.startswith(a[: max(3, len(a) - 2)])
    return False


def classify_surface_error(
    cue: str,
    surface_attempt: str,
    *,
    correct: str = "",
    scene: str | None = None,
    fork_count: int | None = None,
    min_fork_for_prefix: int = 3,
) -> dict[str, Any]:
    """
    Top-down error axis (teacher-correction-protocol-v0).
    Returns axis, correction_kind, surprise, detail.
    """
    cue_n = norm_word(cue)
    attempt = (surface_attempt or "").strip()
    attempt_n = norm_word(attempt)
    correct_n = norm_word(correct)
    has_scene = bool((scene or "").strip())

    if is_mixed_script(attempt):
        return {
            "axis": "script",
            "correction_kind": "script_rule",
            "surprise": True,
            "detail": "mixed_script",
        }

    if not attempt_n:
        return {
            "axis": "phonotactic",
            "correction_kind": "wait_prefix",
            "surprise": False,
            "detail": "empty_attempt",
        }

    if correct_n and attempt_n == correct_n:
        return {
            "axis": "none",
            "correction_kind": None,
            "surprise": False,
            "detail": "already_correct",
        }

    if correct_n and _is_strict_prefix(cue_n, correct_n):
        fork = int(fork_count if fork_count is not None else 0)
        if fork >= min_fork_for_prefix and not has_scene:
            return {
                "axis": "prefix_incomplete",
                "correction_kind": "wait_prefix",
                "surprise": True,
                "detail": f"prefix={cue_n!r} target={correct_n!r} fork={fork}",
            }

    if correct_n and _looks_morph_not_lemma(attempt_n, correct_n):
        kind = "morph_surface" if has_scene else "lexical_ask"
        return {
            "axis": "morph" if has_scene else "lexical",
            "correction_kind": kind,
            "surprise": True,
            "detail": f"morph_like attempt={attempt_n!r} target={correct_n!r}",
        }

    if correct_n and attempt_n and correct_n != attempt_n:
        if _shared_stem(attempt_n, correct_n) or _shared_stem(cue_n, correct_n):
            if has_scene:
                return {
                    "axis": "ortho",
                    "correction_kind": "ortho_surface",
                    "surprise": True,
                    "detail": f"ortho attempt={attempt_n!r} target={correct_n!r}",
                }
            return {
                "axis": "lexical",
                "correction_kind": "lexical_ask",
                "surprise": True,
                "detail": "ambiguous_without_scene",
            }

    if correct_n and not has_scene and cue_n != correct_n:
        fork = int(fork_count if fork_count is not None else 0)
        if fork >= min_fork_for_prefix:
            return {
                "axis": "lexical",
                "correction_kind": "lexical_ask",
                "surprise": True,
                "detail": f"lexical_ambiguity fork={fork}",
            }

    if cue_n and attempt_n == cue_n and correct_n and correct_n != cue_n:
        return {
            "axis": "prefix_incomplete",
            "correction_kind": "wait_prefix",
            "surprise": True,
            "detail": "incomplete_on_prefix",
        }

    return {
        "axis": "phonotactic",
        "correction_kind": "wait_prefix",
        "surprise": bool(attempt_n),
        "detail": "default_phonotactic",
    }


def axis_for_kind(correction_kind: str | None) -> str | None:
    if not correction_kind:
        return None
    for axis, kind in _AXIS_TO_KIND.items():
        if kind == correction_kind:
            return axis
    return None
