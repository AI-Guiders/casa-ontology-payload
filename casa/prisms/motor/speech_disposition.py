#!/usr/bin/env python3
"""When to phonate — subject disposition, not operator flags (ADR-0082)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from casa.domain.subject_agency import SubjectAction, SubjectDisposition
from casa.domain.subject_mode import is_subject_mode
from casa.prisms.control.sn_cen_runtime import TaskEmit


@dataclass(frozen=True, slots=True)
class MotorPhonationDisposition:
    should_phonate: bool
    intent: str | None
    reason: str
    reply_text: str | None = None


def _parse_disposition(raw: dict[str, Any] | None) -> SubjectDisposition | None:
    if not raw or not raw.get("action"):
        return None
    try:
        action = SubjectAction(str(raw["action"]))
    except ValueError:
        return None
    return SubjectDisposition(
        action=action,
        reason=str(raw.get("reason") or ""),
        competing_source=str(raw.get("competing_source") or ""),
    )


def _outbound_text(dialogue_rep: dict[str, Any]) -> str | None:
    outbound = dialogue_rep.get("outbound")
    if not isinstance(outbound, list):
        return None
    for row in outbound:
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or "").strip()
        if text:
            return text
    return None


def _listen_percept_active(state: dict) -> bool:
    block = state.get("_perceptual_turn")
    if not isinstance(block, dict):
        return False
    if block.get("audio_active") or block.get("coactive"):
        return True
    tokens = block.get("tokens") or []
    return any(
        str(tok).startswith(("percept.listen.", "percept.av.", "percept.self.speech"))
        for tok in tokens
    )


def _self_drive_wants_vocal(self_drive_rep: dict[str, Any] | None) -> bool:
    if not self_drive_rep:
        return False
    promote = self_drive_rep.get("skill_promote")
    if isinstance(promote, dict) and promote.get("promoted"):
        return True
    know = self_drive_rep.get("knowledge_seek")
    if isinstance(know, dict) and know.get("sought"):
        cap = str(know.get("capability") or know.get("tract") or "")
        if cap.startswith(("motor", "speech", "listen", "A:")):
            return True
    return False


def resolve_motor_phonation_disposition(
    store_dir: Path,
    state: dict,
    *,
    dialogue_rep: dict[str, Any],
    task: TaskEmit | None,
    mem_prep: dict[str, Any],
    self_drive_rep: dict[str, Any] | None = None,
    force: bool = False,
) -> MotorPhonationDisposition:
    """Phonation follows the same agency line as partner compose — silence is ok."""
    if force:
        return MotorPhonationDisposition(True, "babble", "lab_force")

    if not is_subject_mode(state, store_dir):
        return MotorPhonationDisposition(False, None, "not_subject_mode")

    try:
        from casa.prisms.metabolic import metabolic_should_sleep

        if metabolic_should_sleep(state):
            return MotorPhonationDisposition(False, None, "metabolic_sleep")
    except ImportError:
        pass

    arbiter = mem_prep.get("goal_arbiter") if isinstance(mem_prep.get("goal_arbiter"), dict) else {}
    disp = _parse_disposition(arbiter.get("subject_disposition"))
    if disp is not None and disp.action == SubjectAction.REFUSE:
        return MotorPhonationDisposition(False, None, "subject_refused")

    reply_text = str(dialogue_rep.get("reply_text") or "").strip() or None
    if reply_text and not dialogue_rep.get("soft_miss"):
        return MotorPhonationDisposition(True, "parallel_compose", "symbolic_compose", reply_text)

    initiate_text = _outbound_text(dialogue_rep)
    if initiate_text and dialogue_rep.get("initiated"):
        return MotorPhonationDisposition(True, "parallel_compose", "subject_initiated", initiate_text)

    task_action = str(task.action or "") if task else ""
    if task_action in {"speak", "articulate", "phonate"}:
        return MotorPhonationDisposition(True, "echo_field", f"cen_action:{task_action}")

    task_intent = str(task.intent or "") if task else ""
    if task_intent in {"speak", "articulate", "phonate", "vocalize"}:
        return MotorPhonationDisposition(True, "echo_field", f"cen_intent:{task_intent}")

    if disp is not None and disp.action == SubjectAction.DEFER:
        return MotorPhonationDisposition(False, None, f"subject_deferred:{disp.reason}")

    if _self_drive_wants_vocal(self_drive_rep):
        return MotorPhonationDisposition(True, "babble", "self_drive")

    if _listen_percept_active(state) and not dialogue_rep.get("partner"):
        return MotorPhonationDisposition(True, "babble", "listen_motor_explore")

    return MotorPhonationDisposition(False, None, "no_phonation_agency")
