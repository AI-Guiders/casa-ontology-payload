#!/usr/bin/env python3
"""Critic helpers for merged BiT9 preview chip expectations."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from merge_preview_v0 import merge_preview_anchors, preview_words, preview_words_for_lang  # type: ignore


def apply_preview_expectations(
    checks: list[dict[str, Any]],
    *,
    branches: list[dict[str, Any]],
    top_k: int,
    state: dict[str, Any] | None = None,
    expect_preview_in: list[str] | None = None,
    expect_preview_en_any: list[str] | None = None,
    expect_preview_ru_any: list[str] | None = None,
) -> bool:
    """Append preview_* checks; return all pass."""
    if not (expect_preview_in or expect_preview_en_any or expect_preview_ru_any):
        return True

    preview = merge_preview_anchors(branches, state=state, top_k=top_k, hub_boost=True)
    words = set(preview_words(preview))
    ok = True

    if expect_preview_in:
        missing = [w for w in expect_preview_in if w not in words]
        p_ok = not missing
        checks.append(
            {
                "name": "preview_in",
                "pass": p_ok,
                "detail": {"required": expect_preview_in, "missing": missing, "preview": preview_words(preview)},
            }
        )
        ok = ok and p_ok

    if expect_preview_en_any:
        en_words = set(preview_words_for_lang(preview, "en"))
        found = set(expect_preview_en_any) & en_words
        e_ok = len(found) >= 1
        checks.append(
            {
                "name": "preview_en_any",
                "pass": e_ok,
                "detail": {"any_of": expect_preview_en_any, "found": sorted(found)},
            }
        )
        ok = ok and e_ok

    if expect_preview_ru_any:
        ru_words = set(preview_words_for_lang(preview, "ru"))
        found = set(expect_preview_ru_any) & ru_words
        r_ok = len(found) >= 1
        checks.append(
            {
                "name": "preview_ru_any",
                "pass": r_ok,
                "detail": {"any_of": expect_preview_ru_any, "found": sorted(found)},
            }
        )
        ok = ok and r_ok

    return ok
