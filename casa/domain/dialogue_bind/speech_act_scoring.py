"""Speech-act bind deltas — social zone bias on read, not efferent templates."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.partner_scoring import partner_quote_from_block
from casa.prisms.memory.concept_layer import discourse_concept_id

# prefix → score delta when partner speech act is active (bind only)
_ACT_BIAS: dict[str, tuple[tuple[str, int], ...]] = {
    "how_are_you": (
        ("ru.dialog.how_are_you", 42),
        ("ru.dialog.self", 22),
        ("ru.dialog.honest.", 12),
        ("ru.dialog.affect", -52),
        ("ru.dialog.capabilities", -28),
        ("ru.dialog.thanks", -18),
    ),
    "greeting": (
        ("ru.dialog.greeting", 22),
        ("ru.dialog.affect", 10),
        ("ru.dialog.capabilities", -14),
    ),
    "thanks": (
        ("ru.dialog.thanks", 30),
        ("ru.dialog.farewell", -12),
        ("ru.dialog.affect", -14),
        ("ru.dialog.capabilities", -20),
    ),
    "farewell": (
        ("ru.dialog.farewell", 28),
        ("ru.dialog.thanks", 8),
        ("ru.dialog.affect", -10),
    ),
    "ask_thought": (
        ("subject.dialog.self_recent", 18),
        ("dialog.context.focus_recent", 14),
        ("ru.dialog.self", 16),
        ("ru.dialog.honest.", 10),
        ("ru.dialog.greeting", -24),
        ("ru.dialog.capabilities", -20),
        ("ru.dialog.affect", -8),
    ),
    "mirror_ack": (
        ("subject.dialog.partner_recent", 10),
        ("subject.dialog.self_recent", 8),
        ("ru.dialog.self", 12),
        ("ru.dialog.capabilities", -28),
        ("ru.dialog.greeting", -20),
    ),
    "thread_turn": (
        ("subject.dialog.self_recent", 12),
        ("subject.dialog.partner_recent", 10),
        ("dialog.context.focus_recent", 10),
    ),
}


def _active_speech_acts(blocks: list[dict[str, Any]]) -> list[str]:
    ranked: list[tuple[int, str]] = []
    for row in blocks:
        cid = str(row.get("concept_id") or "")
        if not cid.startswith("ru.speech_act.partner."):
            continue
        slots = row.get("slots") if isinstance(row.get("slots"), dict) else {}
        act = str(slots.get("speech_act") or cid.rsplit(".", 1)[-1]).strip()
        if not act:
            continue
        ranked.append((int(row.get("score") or 0), act))
    if not ranked:
        return []
    ranked.sort(key=lambda item: -item[0])
    return [ranked[0][1]]


def apply_speech_act_bind_deltas(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    intent: str,
) -> None:
    """Elevate dialog families that fit partner speech act — field routing, not phrase pick."""
    if intent != "social":
        return
    acts = _active_speech_acts(blocks)
    if not acts:
        return
    act = acts[0]
    rules = _ACT_BIAS.get(act)
    if not rules:
        return

    partner_quote = ""
    for row in blocks:
        if str(row.get("concept_id") or "") == "subject.dialog.partner_recent":
            partner_quote = partner_quote_from_block(row)
            break

    for row in blocks:
        cid = str(row.get("concept_id") or "")
        disc = discourse_concept_id(row)
        delta = 0
        for prefix, nudge in rules:
            if cid.startswith(prefix) or disc.startswith(prefix):
                delta += nudge
        if act == "mirror_ack" and partner_quote and "не знаю" in partner_quote.lower():
            if disc.startswith("ru.dialog.affect") or cid.startswith("ru.dialog.affect"):
                delta -= 18
        if act == "thanks" and disc.startswith("ru.dialog.affect"):
            delta -= 10
        if delta:
            row["score"] = int(row.get("score") or 0) + delta
