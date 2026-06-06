"""Circumstantial slots P2 (ADR-0033 §6.1) — time, manner, …"""

from __future__ import annotations

import unicodedata
from typing import Any


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def check_circumstantials(
    slots: dict[str, dict[str, Any]],
    specs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify circumstantial.* roles filled with expected surfaces."""
    if not specs:
        return {"ok": True, "checked": 0, "details": []}

    details: list[dict[str, Any]] = []
    ok = True
    for row in specs:
        kind = str(row.get("kind") or "")
        role = str(row.get("role") or f"circumstantial.{kind}")
        exp_surface = _nfc(str(row.get("surface") or "")).lower()
        slot = slots.get(role) or {}
        got = _nfc(str(slot.get("surface") or "")).lower()
        row_ok = bool(exp_surface and got == exp_surface)
        if not row_ok:
            ok = False
        details.append(
            {
                "kind": kind,
                "role": role,
                "expected_surface": exp_surface,
                "got_surface": got,
                "question_id": row.get("question_id"),
                "ok": row_ok,
            }
        )
    return {"ok": ok, "checked": len(specs), "details": details}
