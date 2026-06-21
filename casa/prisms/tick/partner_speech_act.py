#!/usr/bin/env python3
"""Partner speech act from bundle claims — read/bind feature, not efferent text."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from casa.prisms.tick.tract.claims import slot_cue_hit

_SPEECH_PREFIX = "ru.speech_act.partner."
_DESIGN_REL = Path("design") / "kb-partner-speech-acts.v1.json"

# Earlier in list = wins tie-break (specific before broad).
_ACT_PRIORITY = (
    "thanks",
    "farewell",
    "greeting",
    "intro_self",
    "ask_thought",
    "how_are_you",
    "mirror_ack",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _design_speech_claims() -> tuple[dict[str, Any], ...]:
    path = _repo_root() / _DESIGN_REL
    if not path.is_file():
        return ()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    out: list[dict[str, Any]] = []
    for row in raw.get("claims") or []:
        if isinstance(row, dict) and str(row.get("concept_id") or "").startswith(_SPEECH_PREFIX):
            out.append(row)
    return tuple(out)


def partner_speech_act_claims(bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {
        str(c.get("concept_id") or ""): c for c in _design_speech_claims() if c.get("concept_id")
    }
    if bundle:
        for row in bundle.get("claims") or []:
            if not isinstance(row, dict):
                continue
            cid = str(row.get("concept_id") or "")
            if cid.startswith(_SPEECH_PREFIX):
                by_id[cid] = row
    return list(by_id.values())


def _block_concept_id(b: Any) -> str:
    """Read concept_id from a block that may be a dict or an AnswerBlock-like object."""
    if isinstance(b, dict):
        return str(b.get("concept_id") or "")
    return str(getattr(b, "concept_id", "") or "")


def resolve_partner_speech_act_claim(
    query: str,
    bundle: dict[str, Any] | None = None,
    *,
    blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Best partner speech-act claim for this turn as bind evidence."""
    ql = (query or "").strip().lower()
    if not ql:
        return None
    ranked: list[tuple[int, int, str, dict[str, Any]]] = []
    for claim in partner_speech_act_claims(bundle):
        slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
        cue = slot_cue_hit(ql, slots)
        if cue <= 0:
            continue
        act = str(slots.get("speech_act") or "").strip()
        if not act:
            continue
        pri = _ACT_PRIORITY.index(act) if act in _ACT_PRIORITY else 99
        ranked.append((cue, -pri, act, claim))
    if not ranked:
        from casa.domain.dialogue_bind.partner_scoring import partner_self_label

        if partner_self_label(query):
            for claim in partner_speech_act_claims(bundle):
                slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
                if str(slots.get("speech_act") or "") == "intro_self":
                    out = dict(claim)
                    out["slots"] = {**slots, "speech_act": "intro_self", "cue_score": 2}
                    return out
        if blocks and any(_block_concept_id(b) == "subject.dialog.self_recent" for b in blocks):
            for claim in partner_speech_act_claims(bundle):
                slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
                if str(slots.get("speech_act") or "") == "thread_turn":
                    out = dict(claim)
                    out["slots"] = {**slots, "speech_act": "thread_turn", "cue_score": 1}
                    return out
        return None
    ranked.sort(key=lambda row: (-row[0], row[1]))
    cue, _, act, claim = ranked[0]
    out = dict(claim)
    slots = dict(out.get("slots") or {})
    slots["speech_act"] = act
    slots["cue_score"] = cue
    out["slots"] = slots
    return out


def resolve_partner_speech_act(
    query: str,
    bundle: dict[str, Any] | None = None,
    *,
    blocks: list[dict[str, Any]] | None = None,
) -> str | None:
    """Speech-act label for diagnostics and planning; never authorizes phrase templates."""
    claim = resolve_partner_speech_act_claim(query, bundle, blocks=blocks)
    if not claim:
        return None
    slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
    return str(slots.get("speech_act") or "").strip() or None
