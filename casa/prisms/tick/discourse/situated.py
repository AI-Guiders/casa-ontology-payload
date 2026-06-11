"""Situated social compose — continuer head only; no partner-line echo in efferent."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.partner_scoring import (
    subject_quote_from_block,
    thread_continuer_turn,
)
from casa.prisms.tick.discourse.model import ClauseSketch, DiscourseContext
from casa.prisms.tick.discourse.policy import BlockDiscoursePolicy
from casa.prisms.tick.discourse.realizers.blocks import DialogBlockRealizer
from casa.prisms.tick.discourse.render import clause_from_pieces


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


def compose_situated_thread(
    ctx: DiscourseContext,
    composer: Any,
    *,
    dialog: DialogBlockRealizer,
    policy: BlockDiscoursePolicy,
) -> str | None:
    """Only thread_turn continuer — phatic acts compose from bind winners, no «Да —» echo."""
    _ = dialog, policy
    from casa.domain.dialogue_bind.speech_act_scoring import active_speech_act_slots

    act = str(active_speech_act_slots(ctx.blocks).get("speech_act") or "")
    if act and act != "thread_turn":
        return None
    if not thread_continuer_turn(ctx.blocks, ctx.query):
        return None

    self_quote = ""
    for block in ctx.blocks:
        if str(block.get("concept_id") or "") == "subject.dialog.self_recent":
            self_quote = subject_quote_from_block(block)
            break
    if not self_quote:
        return None

    head = _continuer_head(self_quote)
    if not head:
        return None
    return composer._render_discourse([head], [50])
