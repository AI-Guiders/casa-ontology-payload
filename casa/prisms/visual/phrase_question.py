"""Question-frame checks for phrase events (ADR-0033 §6)."""

from __future__ import annotations

import unicodedata
from typing import Any


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def check_question_frames(
    slots: dict[str, dict[str, Any]],
    frames: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify anchor+question → expected surface fills expected role slot."""
    if not frames:
        return {"ok": True, "checked": 0, "details": []}

    details: list[dict[str, Any]] = []
    ok = True
    for row in frames:
        qid = str(row.get("question_id") or "")
        exp_role = str(row.get("expected_role") or "")
        exp_surface = _nfc(str(row.get("expected_surface") or "")).lower()
        anchor = _nfc(str(row.get("anchor_surface") or "")).lower()

        slot = slots.get(exp_role) or {}
        got_surface = _nfc(str(slot.get("surface") or "")).lower()
        row_ok = bool(exp_role and exp_surface and got_surface == exp_surface)
        if not row_ok:
            ok = False
        details.append(
            {
                "question_id": qid,
                "anchor_surface": anchor,
                "expected_role": exp_role,
                "expected_surface": exp_surface,
                "got_surface": got_surface,
                "ok": row_ok,
            }
        )
    return {"ok": ok, "checked": len(frames), "details": details}


def compose_question_verdict(
    slots: dict[str, dict[str, Any]],
    entry: dict[str, Any],
) -> dict[str, Any]:
    """Phrase-level question-frame gate (requires slots already bound)."""
    frames = list(entry.get("question_frames") or [])
    check = check_question_frames(slots, frames)
    verdict = "question_know" if check["ok"] and frames else "question_skip"
    if frames and not check["ok"]:
        verdict = "question_fail"
    return {
        "event_id": str(entry.get("event_id") or ""),
        "verdict": verdict,
        "question_frames": check,
        "question_know": verdict == "question_know",
    }
