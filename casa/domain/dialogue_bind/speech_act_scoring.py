"""Speech-act bind deltas from bundle claim slots — no act→hub Python tuples."""

from __future__ import annotations

from typing import Any

from casa.prisms.memory.concept_layer import discourse_concept_id


def _split_pipe(raw: str) -> list[str]:
    return [p.strip() for p in str(raw or "").split("|") if p.strip()]


def _parse_weighted_prefixes(raw: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for part in _split_pipe(raw):
        if ":" in part:
            prefix, weight = part.rsplit(":", 1)
            try:
                out.append((prefix.strip(), int(weight.strip())))
            except ValueError:
                continue
        else:
            out.append((part, 12))
    return out


def _active_speech_act_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[tuple[int, dict[str, Any]]] = []
    for row in blocks:
        cid = str(row.get("concept_id") or "")
        if not cid.startswith("ru.speech_act.partner."):
            continue
        ranked.append((int(row.get("score") or 0), row))
    ranked.sort(key=lambda item: -item[0])
    return [row for _, row in ranked]


def _active_speech_acts(blocks: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for row in _active_speech_act_blocks(blocks):
        slots = row.get("slots") if isinstance(row.get("slots"), dict) else {}
        act = str(slots.get("speech_act") or "").strip()
        if act:
            out.append(act)
            break
    return out


def active_speech_act_slots(blocks: list[dict[str, Any]]) -> dict[str, str]:
    rows = _active_speech_act_blocks(blocks)
    if not rows:
        return {}
    slots = rows[0].get("slots")
    if not isinstance(slots, dict):
        return {}
    return {str(k): str(v) for k, v in slots.items() if v is not None}


def compose_single_hub_from_bind(blocks: list[dict[str, Any]]) -> bool:
    """Speech-act classes are bind-nudge only — never efferent hub-count policy."""
    _ = blocks
    return False


def apply_speech_act_bind_deltas(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    intent: str,
) -> None:
    """Apply bind_boost / bind_demote from active speech-act claim slots on the field."""
    _ = query
    if intent != "social":
        return
    slots = active_speech_act_slots(blocks)
    if not slots:
        return

    boosts = _parse_weighted_prefixes(slots.get("bind_boost") or "")
    demotes = _parse_weighted_prefixes(slots.get("bind_demote") or "")
    if not boosts and not demotes:
        return

    from casa.prisms.tick.discourse.meta_glue_guard import dialogue_thread_carries

    if dialogue_thread_carries(blocks):
        boosts = [(p, max(4, n // 3)) for p, n in boosts]
        for prefix, _ in boosts:
            if prefix.startswith("ru.dialog."):
                demotes.append((prefix, 18))

    for row in blocks:
        cid = str(row.get("concept_id") or "")
        disc = discourse_concept_id(row)
        delta = 0
        for prefix, nudge in boosts:
            if cid.startswith(prefix) or disc.startswith(prefix):
                delta += nudge
        for prefix, nudge in demotes:
            if cid.startswith(prefix) or disc.startswith(prefix):
                delta -= nudge
        if delta:
            row["score"] = int(row.get("score") or 0) + delta
