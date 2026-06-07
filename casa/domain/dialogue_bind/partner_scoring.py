"""Partner-turn surface helpers for bind reweight (speech situation, not lexicon lists)."""

from __future__ import annotations

import re
from typing import Any

from casa.domain.dialogue_bind.blocks import score_text


def kb_reply_present(kb_hits: list[tuple[dict[str, Any], int]]) -> bool:
    return any(str(c.get("concept_id") or "").startswith("ru.dialog.") for c, _ in kb_hits)


def partner_quote_from_block(block: dict[str, Any]) -> str:
    text = str(block.get("text") or "")
    match = re.search(r"«([^»]+)»", text)
    return match.group(1).strip() if match else ""


def dialog_block_body(block: dict[str, Any]) -> str:
    slots = block.get("slots") if isinstance(block.get("slots"), dict) else {}
    body = " ".join(str(v) for v in slots.values())
    return f"{block.get('text') or ''} {body}".strip()


def dialog_query_position_boost(
    query: str,
    block: dict[str, Any],
    *,
    concept_hints: list[str] | None,
) -> int:
    """Earlier partner surface → stronger bind (discourse order emerges from field, not compose)."""
    ql = (query or "").lower()
    cid = str(block.get("concept_id") or "")
    slots = block.get("slots") if isinstance(block.get("slots"), dict) else {}
    anchors: list[int] = []

    for key in ("stimulus", "word", "surface"):
        surface = str(slots.get(key) or "").lower()
        if len(surface) >= 2 and surface in ql:
            anchors.append(ql.find(surface))

    for hint in concept_hints or []:
        if hint.startswith("ru.dialog.") and (cid == hint or cid.startswith(f"{hint}.")):
            for surface in ("как дела", "как ты", "как тебе здесь", "как тебе тут"):
                if surface in ql:
                    anchors.append(ql.find(surface))
        if hint == "ru.dialog.affect" and cid.startswith("ru.dialog.affect"):
            for surface in ("как дела", "как ты"):
                if surface in ql:
                    anchors.append(ql.find(surface))
        if hint.startswith("lang.word.") and cid.startswith("ru.dialog.greeting"):
            lemma = hint.rsplit(".", 1)[-1].lower()
            if lemma and lemma in ql:
                anchors.append(ql.find(lemma))

    if not anchors:
        return 0
    pos = min(anchors)
    span = max(len(ql), 8)
    return max(0, (span - pos) * 3)


def partner_self_label(quote: str) -> str:
    """Self-label in partner turn — later «Я X» after preamble (discourse structure)."""
    matches = list(re.finditer(r"[яЯ]\s+([А-ЯЁ][а-яё]{1,24})\b", quote))
    return matches[-1].group(1) if matches else ""


def partner_dialog_bind_overlap(quote: str, blocks: list[dict[str, Any]]) -> int:
    """Overlap partner quote with activated ru.dialog bind — situational, not lexicon lists."""
    best = 0
    for block in blocks:
        cid = str(block.get("concept_id") or "")
        if not cid.startswith("ru.dialog."):
            continue
        slots = block.get("slots") if isinstance(block.get("slots"), dict) else {}
        body = " ".join(str(v) for v in slots.values())
        text = f"{block.get('text') or ''} {body}"
        best = max(best, score_text(quote, text, base=0))
    return best


def partner_speech_turn(
    quote: str,
    *,
    intent: str,
    concept_hints: list[str] | None,
    blocks: list[dict[str, Any]],
) -> bool:
    """Partner turn is intro/teaching when tract + bind support it."""
    if intent != "social" or not quote.strip():
        return False
    if partner_self_label(quote):
        return True
    if partner_dialog_bind_overlap(quote, blocks) >= 8:
        return True
    hints = set(concept_hints or [])
    return bool(hints & {"ru.dialog.capabilities", "ru.dialog.thanks", "ru.dialog.affect"})


def social_dialog_slot_allowed(cid: str, *, concept_hints: list[str] | None) -> bool:
    """Dialog slot enters compose only when semantic_read routed the speech situation."""
    hints = set(concept_hints or [])
    if cid.startswith("ru.dialog.how_are_you"):
        return False
    if cid.startswith("ru.dialog.self"):
        return any(h.startswith("ru.dialog.self") for h in hints)
    return True
