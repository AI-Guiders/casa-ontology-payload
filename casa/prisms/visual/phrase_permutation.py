"""Phrase permutation equivalence (ADR-0033 — order ignored)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def check_permutation_equiv(
    entry: dict[str, Any],
    compose_for_surface: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    """All entry.surfaces[] must yield phrase_know with the same event_id."""
    surfaces = [str(s).strip() for s in (entry.get("surfaces") or []) if str(s).strip()]
    event_id = str(entry.get("event_id") or "")
    if not surfaces:
        return {
            "event_id": event_id,
            "ok": False,
            "verdict": "no_surfaces",
            "surfaces": [],
        }

    rows: list[dict[str, Any]] = []
    ok = True
    for surface in surfaces:
        out = compose_for_surface(surface)
        phrase_ok = bool(out.get("phrase_know"))
        if not phrase_ok:
            ok = False
        if str(out.get("event_id") or "") != event_id:
            ok = False
        rows.append(
            {
                "surface": surface,
                "phrase_know": phrase_ok,
                "verdict": out.get("verdict"),
                "event_id": out.get("event_id"),
            }
        )

    return {
        "event_id": event_id,
        "ok": ok,
        "verdict": "permutation_know" if ok else "permutation_fail",
        "surfaces": rows,
        "permutation_know": ok,
    }
