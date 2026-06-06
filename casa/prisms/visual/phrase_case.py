"""Case bindings via question-frames + role slots (ADR-0033 §6; not table-quiz primary)."""

from __future__ import annotations

import unicodedata
from typing import Any


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def check_case_frames(
    slots: dict[str, dict[str, Any]],
    case_frames: list[dict[str, Any]],
    *,
    question_frames: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Each case_frame role must be filled; optional cross-check with question_frames."""
    if not case_frames:
        return {"ok": True, "checked": 0, "details": []}

    q_by_role: dict[str, dict[str, Any]] = {}
    if question_frames:
        for q in question_frames:
            role = str(q.get("expected_role") or "")
            if role:
                q_by_role[role] = q

    details: list[dict[str, Any]] = []
    ok = True
    for row in case_frames:
        role = str(row.get("role") or "")
        case_id = str(row.get("case_id") or "")
        qid = str(row.get("question_id") or "")
        slot = slots.get(role) or {}
        got_surface = _nfc(str(slot.get("surface") or "")).lower()
        row_ok = bool(role and case_id and got_surface)
        if question_frames and qid:
            q = q_by_role.get(role) or {}
            exp_qid = str(q.get("question_id") or "")
            exp_surface = _nfc(str(q.get("expected_surface") or "")).lower()
            if exp_qid and exp_qid != qid:
                row_ok = False
            if exp_surface and got_surface != exp_surface:
                row_ok = False
        if not row_ok:
            ok = False
        details.append(
            {
                "role": role,
                "case_id": case_id,
                "question_id": qid,
                "got_surface": got_surface,
                "ok": row_ok,
            }
        )
    return {"ok": ok, "checked": len(case_frames), "details": details}


def compose_case_verdict(
    slots: dict[str, dict[str, Any]],
    entry: dict[str, Any],
) -> dict[str, Any]:
    frames = list(entry.get("case_frames") or [])
    check = check_case_frames(
        slots,
        frames,
        question_frames=list(entry.get("question_frames") or []),
    )
    verdict = "case_know" if check["ok"] and frames else "case_skip"
    if frames and not check["ok"]:
        verdict = "case_fail"
    return {
        "event_id": str(entry.get("event_id") or ""),
        "verdict": verdict,
        "case_frames": check,
        "case_know": verdict == "case_know",
    }
