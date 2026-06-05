#!/usr/bin/env python3
"""Subject agency — environment goals are proposals, not commands (agent-first-learn)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from casa.domain.self_model import tract_confidence
from casa.prisms.control.fpn_state import WorkingMemory

EXPLICIT_PROPOSAL_PRIORITY = 75
EXPLICIT_ACCEPTED_PRIORITY = 88
EXPLICIT_DEFERRED_PRIORITY = 55

LOW_TRACT_CONFIDENCE = 0.35


class SubjectAction(str, Enum):
    ACCEPT = "accept"
    DEFER = "defer"
    REFUSE = "refuse"


@dataclass(frozen=True, slots=True)
class SubjectDisposition:
    action: SubjectAction
    reason: str
    competing_source: str = ""


def evaluate_external_proposal(
    state: dict,
    wm: WorkingMemory,
    *,
    load_rep: dict[str, Any],
) -> SubjectDisposition:
    """Inbox / explicit WM goals are proposals — subject may defer or refuse."""
    subject_flags = state.get("subject")
    if not isinstance(subject_flags, dict):
        subject_flags = {}

    if subject_flags.get("force_accept_external"):
        return SubjectDisposition(SubjectAction.ACCEPT, "force_accept")

    if subject_flags.get("refuse_external"):
        return SubjectDisposition(SubjectAction.REFUSE, "explicit_refusal")

    weak = state.get("last_weakest_link")
    if isinstance(weak, dict) and weak.get("concept_id"):
        return SubjectDisposition(
            SubjectAction.DEFER,
            "own_practice_first",
            competing_source="deliberate_practice",
        )

    capability = str(wm.step_capability or "").strip()
    if capability and tract_confidence(state, capability) < LOW_TRACT_CONFIDENCE:
        return SubjectDisposition(
            SubjectAction.DEFER,
            f"tract_not_ready:{capability}",
            competing_source="self_model",
        )

    if load_rep.get("overloaded"):
        return SubjectDisposition(
            SubjectAction.DEFER,
            "cognitive_overload",
            competing_source="load_governor",
        )

    return SubjectDisposition(SubjectAction.ACCEPT, "accepted_proposal")


def disposition_to_priority(disp: SubjectDisposition) -> int | None:
    if disp.action == SubjectAction.REFUSE:
        return None
    if disp.action == SubjectAction.DEFER:
        return EXPLICIT_DEFERRED_PRIORITY
    return EXPLICIT_ACCEPTED_PRIORITY


def record_disposition(state: dict, disp: SubjectDisposition | None) -> dict[str, Any] | None:
    if disp is None:
        return None
    payload = {
        "action": disp.action.value,
        "reason": disp.reason,
        "competing_source": disp.competing_source,
    }
    subject = state.setdefault("subject", {})
    if isinstance(subject, dict):
        subject["last_disposition"] = payload
    return payload
