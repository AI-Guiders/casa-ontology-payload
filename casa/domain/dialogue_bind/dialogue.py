"""Dialogue continuity blocks and stance inference."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from casa.domain.dialogue_bind.blocks import block_dict, score_text
from casa.domain.dialogue_turn import recent_dialogue
from casa.prisms.control.sn_cen_runtime import TaskEmit

_DEVELOPMENTAL_TURN_KINDS = frozenset({"recast", "expand", "clarify", "correction"})


def _surface_partner_turn(turn: Any) -> bool:
    return turn.speaker == "partner" and turn.kind not in _DEVELOPMENTAL_TURN_KINDS


def dialogue_continuity_blocks(store_dir: Path | None, query: str) -> list[dict[str, Any]]:
    if store_dir is None:
        return []
    blocks: list[dict[str, Any]] = []
    turns = recent_dialogue(store_dir, limit=10)
    focus_terms: list[str] = []
    focus_intents: list[str] = []
    latest_partner: str | None = None
    latest_subject: str | None = None
    for turn in turns:
        if _surface_partner_turn(turn):
            latest_partner = turn.text
        elif turn.speaker == "subject" and turn.kind in ("reply", "initiate"):
            latest_subject = turn.text
        prov = turn.provenance if isinstance(turn.provenance, dict) else {}
        if prov.get("query_intent"):
            intent = str(prov["query_intent"])
            if intent not in focus_intents:
                focus_intents.append(intent)
        for cid in prov.get("prop_ids") or []:
            s = str(cid)
            if s and s not in focus_terms:
                focus_terms.append(s)
        for cid in prov.get("dialog_hubs") or []:
            s = str(cid)
            if s and s not in focus_terms:
                focus_terms.append(s)
        for act in prov.get("partner_speech_acts") or []:
            s = f"ru.speech_act.partner.{act}"
            if s not in focus_terms:
                focus_terms.append(s)
        for skill in re.findall(r"skill\.[\w.\-]+", turn.text):
            if skill not in focus_terms:
                focus_terms.append(skill)
    if latest_partner:
        ql = query.strip().lower()
        pq = latest_partner.strip().lower()
        base = 4 if pq == ql else score_text(query, latest_partner, base=12)
        blocks.append(
            block_dict(
                "subject.dialog.partner_recent",
                f"Партнёр недавно: «{latest_partner[:120]}».",
                source="dialogue",
                score=base,
            )
        )
    if latest_subject:
        blocks.append(
            block_dict(
                "subject.dialog.self_recent",
                f"Я недавно: «{latest_subject[:100]}».",
                source="dialogue",
                score=24,
            )
        )
    thread_age = 0 if latest_partner else min(len(turns), 4)
    thread_overlap = 0
    referent_prop = ""
    if latest_partner:
        thread_overlap = max(thread_overlap, score_text(query, latest_partner, base=0))
    if latest_subject:
        thread_overlap = max(thread_overlap, score_text(query, latest_subject, base=0))
    from casa.domain.dialogue_bind.anaphora import query_has_deictic, recent_ring_referent

    if store_dir is not None and query_has_deictic(query):
        referent_prop, _, ring_age = recent_ring_referent(store_dir, exclude_text=query)
        if ring_age:
            thread_age = ring_age
    if focus_terms:
        parts = ["Текущий фокус диалога: " + ", ".join(focus_terms[:5])]
        if focus_intents:
            parts.append("последние намерения: " + ", ".join(focus_intents[:3]))
        base_score = 12
        if thread_overlap >= 8:
            base_score += min(24, thread_overlap)
        elif thread_age > 0:
            base_score = max(4, base_score - thread_age * 3)
        blocks.append(
            block_dict(
                "dialog.context.focus_recent",
                "; ".join(parts) + ".",
                source="dialogue",
                score=base_score,
                section="dialogue_focus",
                slots={
                    "thread_terms": "|".join(focus_terms[:5]),
                    "thread_age": str(thread_age),
                    "thread_overlap": str(thread_overlap),
                    "thread_intents": "|".join(focus_intents[:3]),
                    **({"referent_prop": referent_prop} if referent_prop else {}),
                },
            )
        )
    return blocks


def infer_stance(blocks: list[dict[str, Any]], *, task: TaskEmit | None, intent: str) -> str:
    if not blocks:
        return "unknown"
    top = max(int(b.get("score") or 0) for b in blocks)
    has_kb = any(str(b.get("source")) == "kb" for b in blocks)
    has_journal = any(str(b.get("source")) == "journal" for b in blocks)
    has_cen = bool(task and task.answer_blocks)
    if intent == "math" and has_kb and top >= 18:
        return "confident"
    if intent == "social" and has_kb and top >= 20:
        return "confident"
    if intent == "grammar" and has_kb and top >= 18:
        return "confident"
    if intent == "explain" and has_kb and top >= 16:
        return "confident"
    if intent in ("discuss", "rewrite", "journal") and top >= 18:
        return "confident"
    if top >= 16 and (has_journal or has_cen or has_kb):
        return "confident"
    if top >= 8 or has_journal or has_kb:
        return "partial"
    return "unknown"
