#!/usr/bin/env python3
"""Working-memory block realizer (ADR-0055)."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.tick.discourse.model import ClauseSketch, DiscourseContext, DiscourseSketch
from casa.prisms.tick.discourse.render import clause_from_slot_phrase, query_tokens, render_discourse

_PROP_QUERY_ANCHOR: dict[str, str] = {
    "rain": "дожд",
    "cancel": "отмен",
    "weekend_goal": "выходн",
}

_ANCHOR_LEMMA: dict[str, str] = {
    "дожд": "дождь",
    "отмен": "отмена",
    "квантов": "квантовый",
    "физик": "физика",
    "выходн": "выходные",
}


def wm_prism_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [b for b in blocks if b.get("source") == "wm_prism" and isinstance(b.get("slots"), dict)]


def _anchor_hits(concept_id: str, query_lower: str) -> int:
    tail = str(concept_id or "").rsplit(".", 1)[-1]
    anchor = _PROP_QUERY_ANCHOR.get(tail)
    if anchor and anchor in query_lower:
        return 4
    if tail and len(tail) > 2 and tail.lower() in query_lower:
        return 3
    return 0


def wm_concept_surface(concept_id: str, query: str, blocks: list[dict[str, Any]]) -> str:
    cid = str(concept_id or "")
    tail = cid.rsplit(".", 1)[-1]
    ql = query.lower()
    if cid.startswith("lang.word."):
        return tail
    anchor = _PROP_QUERY_ANCHOR.get(tail)
    if anchor and anchor in ql:
        for word in re.findall(r"[\w\u0400-\u04FF]+", query, flags=re.UNICODE):
            wl = word.lower()
            if anchor in wl:
                return _ANCHOR_LEMMA.get(anchor, wl)
        return _ANCHOR_LEMMA.get(anchor, tail)
    word_cid = f"lang.word.{tail}"
    for block in blocks:
        if str(block.get("concept_id") or "") == word_cid:
            return tail
    return tail.replace("_", " ")


def wm_edge_query_score(block: dict[str, Any], query: str, blocks: list[dict[str, Any]]) -> int:
    slots = block.get("slots") or {}
    fc = str(slots.get("from") or "")
    tc = str(slots.get("to") or "")
    if not fc or not tc:
        return 0
    ql = query.lower()
    a = wm_concept_surface(fc, query, blocks)
    b = wm_concept_surface(tc, query, blocks)
    hit = _anchor_hits(fc, ql) + _anchor_hits(tc, ql)
    qt = query_tokens(query)
    for surface in (a, b):
        sl = surface.lower()
        if sl in ql or any(sl.startswith(t[:4]) or t.startswith(sl[:4]) for t in qt if len(t) > 3):
            hit += 3
    return hit * 12 + int(block.get("score") or 0) + int(float(slots.get("sigma") or 0) * 10)


def wm_elaboration_allowed(
    block: dict[str, Any],
    ctx: DiscourseContext,
    *,
    allow_tail: bool,
) -> bool:
    if not allow_tail or ctx.partner_is_brief():
        return False
    bind = int(block.get("score") or 0)
    slots = block.get("slots") or {}
    sigma = float(slots.get("sigma") or 0)
    match = wm_edge_query_score(block, ctx.query, ctx.blocks)
    if ctx.query_intent in ("explain", "discuss", "journal") and bind >= 18 and match >= 12:
        return True
    if sigma >= 0.5 and str(slots.get("tier") or "") in {"episode", "hippo"}:
        return True
    return bind >= 28 and match >= 18


def _wm_primary_phrase(a: str, b: str, query: str, *, recall_tone: bool) -> str:
    ql = query.lower()
    if "связ" in ql or "между" in ql:
        return f"Связь, которую держу: {a} и {b} — в нашем разговоре они шли вместе."
    if recall_tone:
        return f"Как мы говорили: {a} связан с {b} — это держу на поле."
    return f"На поле связаны {a} и {b}."


def _wm_elaboration_phrase(a: str, b: str, block: dict[str, Any]) -> str:
    slots = block.get("slots") or {}
    tier = str(slots.get("tier") or "scratch")
    sigma = float(slots.get("sigma") or 0)
    if tier == "episode":
        return f"Эта пара уже пережила эпизод — держу её с силой около {sigma:.0%}."
    return f"Между {a} и {b} связь на поле не случайная — она повторялась в ходе разговора."


def wm_clauses_from_block(
    block: dict[str, Any],
    *,
    query: str,
    blocks: list[dict[str, Any]],
    query_intent: str = "general",
    allow_tail: bool = True,
) -> list[ClauseSketch]:
    ctx = DiscourseContext.bind(query, blocks, query_intent=query_intent)
    return WmBlockRealizer().realize(block, ctx, allow_tail=allow_tail)


def wm_link_discourse(query: str, blocks: list[dict[str, Any]]) -> str | None:
    wm = wm_prism_blocks(blocks)
    if not wm:
        return None
    top = max(wm, key=lambda b: wm_edge_query_score(b, query, blocks))
    clauses = wm_clauses_from_block(top, query=query, blocks=blocks, query_intent="general", allow_tail=False)
    if not clauses:
        return None
    return render_discourse(DiscourseSketch(clauses, paragraph_after=set()))


class WmBlockRealizer:
    """Realize WM prism edge blocks into one or two clauses."""

    def matches(self, block: dict[str, Any]) -> bool:
        return block.get("source") == "wm_prism" and isinstance(block.get("slots"), dict)

    def realize(
        self,
        block: dict[str, Any],
        ctx: DiscourseContext,
        *,
        allow_tail: bool | None = None,
    ) -> list[ClauseSketch]:
        if allow_tail is None:
            allow_tail = not ctx.partner_is_brief()
        match = wm_edge_query_score(block, ctx.query, ctx.blocks)
        bind = int(block.get("score") or 0)
        if match < 12 and bind < 12:
            return []

        slots = block.get("slots") or {}
        a = wm_concept_surface(str(slots.get("from") or ""), ctx.query, ctx.blocks)
        b = wm_concept_surface(str(slots.get("to") or ""), ctx.query, ctx.blocks)
        if not a or not b:
            return []

        recall_tone = match >= 24 or float(slots.get("sigma") or 0) >= 0.52
        primary = _wm_primary_phrase(a, b, ctx.query, recall_tone=recall_tone)
        out: list[ClauseSketch] = []
        head = clause_from_slot_phrase(primary)
        if head:
            out.append(head)
        if wm_elaboration_allowed(block, ctx, allow_tail=allow_tail):
            tail = clause_from_slot_phrase(_wm_elaboration_phrase(a, b, block), linker="При этом")
            if tail:
                out.append(tail)
        return out
