"""Dialogue continuity blocks and stance inference."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from casa.domain.dialogue_bind.blocks import block_dict, score_text
from casa.domain.dialogue_turn import recent_dialogue
from casa.prisms.control.sn_cen_runtime import TaskEmit


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
        if turn.speaker == "partner":
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
        blocks.append(
            block_dict(
                "subject.dialog.partner_recent",
                f"Партнёр недавно: «{latest_partner[:120]}».",
                source="dialogue",
                score=score_text(query, latest_partner, base=12),
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
    ql = query.lower()
    if focus_terms and any(m in ql for m in ("что с", "с ним", "с этим", "про это", "контекст", "продолж")):
        parts = ["Текущий фокус диалога: " + ", ".join(focus_terms[:5])]
        if focus_intents:
            parts.append("последние намерения: " + ", ".join(focus_intents[:3]))
        blocks.append(
            block_dict(
                "dialog.context.focus_recent",
                "; ".join(parts) + ".",
                source="dialogue",
                score=20,
                section="dialogue_focus",
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
