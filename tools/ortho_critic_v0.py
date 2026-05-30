#!/usr/bin/env python3
"""Ortho critic: display + lexeme checks for process lab."""

from __future__ import annotations

from typing import Any

from ortho_process_v0 import same_lexeme  # type: ignore


def critic_ortho_surface(
    *,
    canonical: str,
    surface: str,
    expect_display: str,
    context: str = "plain",
) -> dict[str, Any]:
    """
    plain context: display must match expect_display; lexeme via norm always checked.
    """
    lexeme_ok = same_lexeme(surface, canonical) and same_lexeme(expect_display, canonical)
    display_ok = surface == expect_display
    ok = lexeme_ok and display_ok
    return {
        "verdict": "pass" if ok else "fail",
        "context": context,
        "canonical": canonical,
        "surface": surface,
        "expect_display": expect_display,
        "lexeme_ok": lexeme_ok,
        "display_ok": display_ok,
        "ok": ok,
    }


def critic_ortho_undo(
    *,
    before: str,
    after: str,
    expect: str,
) -> dict[str, Any]:
    ok = after == expect and same_lexeme(after, before)
    return {
        "verdict": "pass" if ok else "fail",
        "before": before,
        "after": after,
        "expect": expect,
        "ok": ok,
    }
