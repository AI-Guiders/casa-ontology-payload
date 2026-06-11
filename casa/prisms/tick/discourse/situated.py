"""Situated social compose — partner/self thread in efferent, not hub slot rotation."""

from __future__ import annotations

import re
from typing import Any

from casa.domain.dialogue_bind.blocks import score_text
from casa.domain.dialogue_bind.partner_scoring import (
    continuer_active,
    partner_continuer_query,
    partner_quote_from_block,
    subject_quote_from_block,
    thread_continuer_turn,
)
from casa.prisms.tick.discourse.model import ClauseSketch, DiscourseContext
from casa.prisms.tick.discourse.policy import BlockDiscoursePolicy
from casa.prisms.tick.discourse.realizers.blocks import DialogBlockRealizer
from casa.prisms.tick.discourse.render import clause_from_pieces


def _split_spans(text: str) -> list[str]:
    parts = re.split(r"[,;—–-]|(?:\s+но\s+)", text, flags=re.IGNORECASE)
    out = [text.strip()] if text.strip() else []
    for p in parts:
        s = p.strip()
        if len(s) >= 6:
            out.append(s)
    return out


def acknowledgment_span(query: str, quote: str, *, self_recent: str | None) -> str | None:
    """Partner line span to echo — field overlap, prefer partner's new words vs prior subject."""
    q = (query or "").strip()
    if not q or not quote.strip():
        return None
    if score_text(q, quote, base=0) < 8:
        return None
    spans = _split_spans(quote)
    ranked: list[tuple[int, str]] = []
    for span in spans:
        ov = score_text(q, span, base=0)
        if ov < 4:
            continue
        novelty = 0 if not self_recent else max(0, 14 - score_text(self_recent, span, base=0))
        length_pen = max(0, len(span) - 42)
        rank = ov * 5 + novelty * 4 - length_pen
        ranked.append((rank, span.rstrip(".!?,")))
    if not ranked:
        return None
    ranked.sort(key=lambda row: -row[0])
    best = ranked[0][1][:72]
    m = re.search(r"\bно\b(.+)$", quote, flags=re.IGNORECASE)
    if m:
        tail = m.group(1).strip().rstrip(".!?,")
        if len(tail) >= 10 and score_text(q, tail, base=0) >= 4:
            if not self_recent or score_text(self_recent, tail, base=0) < 8:
                return tail[:72]
    if score_text(q, best, base=0) >= 14 and len(best) >= max(12, int(len(q) * 0.55)):
        return None
    return best


def _thread_gist(text: str) -> str:
    """Prior subject line essence — first sentence only, not hub tail replay."""
    t = text.strip().rstrip(".!?,")
    if "—" in t:
        t = t.split("—", 1)[-1].strip()
    elif t.lower().startswith("да "):
        t = t[2:].strip()
    if "." in t:
        t = t.split(".", 1)[0].strip()
    return t[:80]


def _continuer_head(self_quote: str) -> ClauseSketch | None:
    gist = _thread_gist(self_quote)
    if len(gist) < 6:
        return None
    return clause_from_pieces([f"Про это — {gist}"])


def _tail_from_bind(
    ctx: DiscourseContext,
    composer: Any,
    *,
    dialog: DialogBlockRealizer,
    policy: BlockDiscoursePolicy,
) -> ClauseSketch | None:
    from casa.prisms.memory.concept_layer import discourse_concept_id

    budget = ctx.budget
    for block in ctx.blocks:
        score = int(block.get("score") or 0)
        if score < budget.score_floor:
            break
        cid = discourse_concept_id(block)
        if not cid.startswith("ru.dialog."):
            continue
        extra = dialog.realize(block, ctx)
        if extra:
            return extra[0]
    return None


def compose_situated_thread(
    ctx: DiscourseContext,
    composer: Any,
    *,
    dialog: DialogBlockRealizer,
    policy: BlockDiscoursePolicy,
) -> str | None:
    """Open thread: partner/self bind → speech; hub slots only as tail."""
    if not (
        any(str(b.get("concept_id") or "") == "subject.dialog.partner_recent" for b in ctx.blocks)
        and (
            any(str(b.get("concept_id") or "") == "subject.dialog.self_recent" for b in ctx.blocks)
            or continuer_active(ctx.blocks)
        )
    ):
        return None

    partner_quote = ""
    self_quote = ""
    for block in ctx.blocks:
        cid = str(block.get("concept_id") or "")
        if cid == "subject.dialog.partner_recent":
            partner_quote = partner_quote_from_block(block)
        elif cid == "subject.dialog.self_recent":
            self_quote = subject_quote_from_block(block)

    clauses: list[ClauseSketch] = []
    scores: list[int] = []
    thread_continuer = thread_continuer_turn(ctx.blocks, ctx.query)
    if thread_continuer and self_quote:
        head = _continuer_head(self_quote)
        if head:
            clauses.append(head)
            scores.append(50)
    elif partner_quote:
        span = acknowledgment_span(ctx.query, partner_quote, self_recent=self_quote or None)
        if span:
            head = clause_from_pieces(["да", "—", span])
            if head:
                clauses.append(head)
                scores.append(46)

    if not clauses:
        return None

    pq = partner_quote.lower()
    add_tail = not thread_continuer and "не знаю" not in pq
    tail = (
        _tail_from_bind(ctx, composer, dialog=dialog, policy=policy)
        if add_tail
        else None
    )
    if tail:
        key = " ".join(tail.pieces).lower()
        head_key = " ".join(clauses[0].pieces).lower()
        if key not in head_key:
            clauses.append(tail)
            scores.append(36)

    return composer._render_discourse(clauses, scores)
