"""Partner-turn surface helpers for bind reweight (field overlap, not lexicon oracles)."""

from __future__ import annotations

import re
from typing import Any

from casa.domain.dialogue_bind.blocks import score_text

_FIELD_OVERLAP_MIN = 8
_BIND_ROUTE_MIN = 48


def kb_reply_present(kb_hits: list[tuple[dict[str, Any], int]]) -> bool:
    return any(str(c.get("concept_id") or "").startswith("ru.dialog.") for c, _ in kb_hits)


def partner_quote_from_block(block: dict[str, Any]) -> str:
    text = str(block.get("text") or "")
    match = re.search(r"«([^»]+)»", text)
    return match.group(1).strip() if match else ""


def subject_quote_from_block(block: dict[str, Any]) -> str:
    """Recent subject line from dialogue continuity block («…»)."""
    return partner_quote_from_block(block)


def thread_continuation_active(
    blocks: list[dict[str, Any]],
    query: str,
) -> bool:
    """Open social thread: partner turn follows a prior subject reply."""
    if not any(str(b.get("concept_id") or "") == "subject.dialog.self_recent" for b in blocks):
        return False
    if partner_self_label(query):
        return False
    ql = (query or "").strip().lower()
    if not ql:
        return False
    for block in blocks:
        if str(block.get("concept_id") or "") != "subject.dialog.partner_recent":
            continue
        quote = partner_quote_from_block(block)
        if not quote:
            continue
        if quote.strip().lower() == ql or score_text(query, quote, base=0) >= 12:
            return True
    return False


def continuer_active(blocks: list[dict[str, Any]]) -> bool:
    """Bind carries continuer situation (dialog.context.focus_recent from dialogue ring)."""
    return any(str(b.get("concept_id") or "") == "dialog.context.focus_recent" for b in blocks)


def thread_continuer_turn(blocks: list[dict[str, Any]], query: str) -> bool:
    """Open thread when ring carries focus_recent — no substring cue markers."""
    _ = query
    return continuer_active(blocks)


def hub_open_in_focus(blocks: list[dict[str, Any]], hub: str) -> bool:
    for block in blocks:
        if str(block.get("concept_id") or "") != "dialog.context.focus_recent":
            continue
        return hub in str(block.get("text") or "")
    return False


def narrative_recently_spoken(clause_text: str, blocks: list[dict[str, Any]]) -> bool:
    """Anti-replay: gated narrative already appeared in recent subject outbound."""
    key = re.sub(r"\s+", " ", str(clause_text or "").strip().lower())
    if len(key) < 12:
        return False
    prefix = key[:48]
    for block in blocks:
        if str(block.get("concept_id") or "") != "subject.dialog.self_recent":
            continue
        spoken = subject_quote_from_block(block).lower()
        if not spoken:
            continue
        if prefix in spoken or key in spoken:
            return True
    return False


def dialog_block_body(block: dict[str, Any]) -> str:
    slots = block.get("slots") if isinstance(block.get("slots"), dict) else {}
    body = " ".join(str(v) for v in slots.values())
    return f"{block.get('text') or ''} {body}".strip()


def partner_field_overlap(query: str, block: dict[str, Any]) -> int:
    """Partner turn ↔ ru.dialog block body on field — curriculum/KB text, not cue lists."""
    return score_text(query, dialog_block_body(block))


def _hint_routes_dialog(concept_hints: list[str] | None, cid: str, prefix: str) -> bool:
    if not cid.startswith(prefix):
        return False
    return any(h.startswith(prefix) for h in (concept_hints or []))


def field_routed_dialog_slot(
    cid: str,
    *,
    hint_prefix: str,
    concept_hints: list[str] | None,
    query: str,
    block: dict[str, Any] | None,
) -> bool:
    """Gated ru.dialog.* enters compose when semantic_read or bind elevated it on field."""
    if _hint_routes_dialog(concept_hints, cid, hint_prefix):
        return True
    if block is not None and partner_field_overlap(query, block) >= _FIELD_OVERLAP_MIN:
        return True
    return int((block or {}).get("score") or 0) >= _BIND_ROUTE_MIN


def dialog_query_position_boost(
    query: str,
    block: dict[str, Any],
    *,
    concept_hints: list[str] | None,
) -> int:
    """Earlier partner surface → stronger bind (stimulus/surface slots + routed hints)."""
    ql = (query or "").lower()
    cid = str(block.get("concept_id") or "")
    slots = block.get("slots") if isinstance(block.get("slots"), dict) else {}
    anchors: list[int] = []

    for key in ("stimulus", "word", "surface"):
        surface = str(slots.get(key) or "").lower()
        if len(surface) >= 2 and surface in ql:
            anchors.append(ql.find(surface))

    for hint in concept_hints or []:
        if not hint.startswith(("ru.dialog.", "lang.word.")):
            continue
        if cid == hint or cid.startswith(f"{hint}.") or hint.startswith("lang.word."):
            for key in ("stimulus", "word", "surface"):
                surface = str(slots.get(key) or "").lower()
                if len(surface) >= 2 and surface in ql:
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
    if partner_dialog_bind_overlap(quote, blocks) >= _FIELD_OVERLAP_MIN:
        return True
    hints = set(concept_hints or [])
    if hints & {"ru.dialog.capabilities", "ru.dialog.thanks"}:
        if thread_continuation_active(blocks, quote):
            return False
        return True
    return False


def social_dialog_slot_allowed(
    cid: str,
    *,
    concept_hints: list[str] | None,
    query: str = "",
    block: dict[str, Any] | None = None,
    bundle: dict[str, Any] | None = None,
) -> bool:
    """Gated hubs need hint / overlap / bind floor — open hubs always allowed."""
    from casa.domain.dialogue_bind.dialog_bind_policy import (
        gated_dialog_prefixes,
        hub_family_prefix,
        open_dialog_prefixes,
    )

    if not cid.startswith("ru.dialog."):
        return True
    if any(cid.startswith(p) for p in open_dialog_prefixes(bundle)):
        return True
    if not any(cid.startswith(p) for p in gated_dialog_prefixes(bundle)):
        return True
    prefix = hub_family_prefix(cid)
    return field_routed_dialog_slot(
        cid,
        hint_prefix=prefix,
        concept_hints=concept_hints,
        query=query,
        block=block,
    )


def max_field_overlap_for_prefix(
    query: str, blocks: list[dict[str, Any]], prefix: str
) -> int:
    """Peak partner↔field overlap for a ru.dialog family (reweight demotion)."""
    from casa.prisms.memory.concept_layer import discourse_concept_id

    best = 0
    for row in blocks:
        disc = discourse_concept_id(row)
        if disc.startswith(prefix):
            best = max(best, partner_field_overlap(query, row))
    return best
