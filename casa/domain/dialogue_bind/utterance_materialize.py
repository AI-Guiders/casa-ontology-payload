"""Materialize ru.dialog hub slots into competing utterance blocks at bind — not compose."""

from __future__ import annotations

import re
from typing import Any

from casa.domain.dialogue_bind.partner_scoring import (
    narrative_recently_spoken,
    partner_field_overlap,
    thread_continuer_turn,
)
from casa.prisms.tick.discourse.slots import BlockSlots


def _hub_id(block: dict[str, Any]) -> str:
    from casa.prisms.memory.concept_layer import discourse_concept_id

    return discourse_concept_id(block)


def _content_tokens(text: str) -> set[str]:
    return {
        w
        for w in re.findall(r"[\w\u0400-\u04FF]+", str(text or "").lower(), flags=re.UNICODE)
        if len(w) > 3
    }


def _shared_novel(query: str, body: str) -> tuple[int, int]:
    """(shared, novel) content-concept counts, stem-aware so совпадать~совпадает."""
    def stem(w: str) -> str:
        return w[:6] if len(w) > 6 else w

    qs = {stem(w) for w in _content_tokens(query)}
    bs = {stem(w) for w in _content_tokens(body)}
    return len(bs & qs), len(bs - qs)


def _parrot_penalty(query: str, body: str) -> int:
    """Variant repeats the partner's line — field overlap WITHOUT novel efferent.

    Three echo signals: (1) the variant repeats TWO+ of the partner's content
    concepts (stem-aware, so "не знаю"+"совпада…" is caught even across inflection);
    (2) it opens with the partner's words AND adds little new content; (3) heavy
    literal field overlap. A variant that echoes ONE concept but adds real new content
    is genuine mirroring, not parroting ("я тоже не знаю" -> "не знаю, совпадает ли
    мой опыт"), and is not penalised.
    """
    from casa.domain.dialogue_bind.blocks import score_text

    ql = (query or "").lower()
    bl = (body or "").lower()
    shared, novel = _shared_novel(query, body)
    if shared >= 2:
        return 80
    words = re.findall(r"[\w\u0400-\u04FF]+", bl, flags=re.UNICODE)
    for n in range(min(6, len(words)), 0, -1):
        prefix = " ".join(words[:n]).lower()
        if novel < 2 and len(prefix) >= 5 and prefix in ql:
            return 88
    stub: dict[str, Any] = {"text": body, "slots": {"phrase": body}}
    if score_text(query, body, base=0) >= 16 or partner_field_overlap(query, stub) >= 14:
        return 80
    return 0


def _variant_score(
    hub_score: int,
    *,
    query: str,
    body: str,
    slot_index: int,
    min_index: int,
    blocks: list[dict[str, Any]],
    continuer: bool,
) -> int:
    stub: dict[str, Any] = {"text": body, "slots": {"phrase": body}}
    score = hub_score + min(24, partner_field_overlap(query, stub))
    if narrative_recently_spoken(body, blocks):
        return 0
    score = max(0, score - _parrot_penalty(query, body))
    if continuer and slot_index == min_index and partner_field_overlap(query, stub) < 8:
        score = max(0, score - 72)
    return score


def materialize_dialog_utterances(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    intent: str,
) -> None:
    """Split multi-slot dialog hubs into ranked utterance atoms; compose only renders winners."""
    if intent != "social":
        return

    continuer = thread_continuer_turn(blocks, query)
    out: list[dict[str, Any]] = []

    for block in blocks:
        hub = _hub_id(block)
        if not hub.startswith("ru.dialog."):
            out.append(block)
            continue

        slots = BlockSlots.read(block)
        indices = BlockSlots.clause_indices(slots)
        if not indices:
            out.append(block)
            continue

        hub_score = int(block.get("score") or 0)
        min_index = min(indices)
        variants: list[dict[str, Any]] = []

        staged: list[tuple[int, str, str, str, int, int]] = []
        hub_parrot = False
        for i in indices:
            body = str(slots.get(f"clause_{i}") or slots.get(f"sentence_{i}") or "").strip()
            if not body:
                continue
            slot_key = f"clause_{i}" if f"clause_{i}" in slots else f"sentence_{i}"
            parrot = _parrot_penalty(query, body)
            if parrot >= 80:
                hub_parrot = True
            score = _variant_score(
                hub_score,
                query=query,
                body=body,
                slot_index=i,
                min_index=min_index,
                blocks=blocks,
                continuer=continuer,
            )
            if score <= 0:
                continue
            staged.append((score, body, slot_key, hub, parrot, i))

        if hub_parrot:
            adjusted: list[tuple[int, str, str, str, int, int]] = []
            for score, body, slot_key, hub, parrot, slot_index in staged:
                if parrot >= 80:
                    adjusted.append((score, body, slot_key, hub, parrot, slot_index))
                    continue
                nudge = 8 * max(0, slot_index - min_index)
                if slot_index == min_index:
                    nudge -= 56
                adjusted.append((score + nudge, body, slot_key, hub, parrot, slot_index))
            staged = adjusted

        for score, body, slot_key, hub, _, _ in staged:
            row = dict(block)
            row["concept_id"] = f"{hub}@{slot_key}"
            row["bind_hub"] = hub
            row["surface_concept_id"] = hub
            row["text"] = body
            row["slots"] = {"phrase": body, "slot_key": slot_key}
            row["score"] = score
            variants.append(row)

        if variants:
            out.extend(variants)
        elif hub_score > 0:
            out.append(block)

    blocks[:] = out
