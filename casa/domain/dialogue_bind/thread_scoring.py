"""Dialogue thread activation on bind — prior subject hubs, field overlap only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.domain.dialogue_bind.partner_scoring import partner_field_overlap


def dialogue_thread_hub_ids(store_dir: Path, *, limit: int = 8) -> list[str]:
    """ru.dialog hubs from recent subject turns (provenance), newest first."""
    from casa.domain.dialogue_turn import recent_dialogue

    hubs: list[str] = []
    seen: set[str] = set()
    for turn in reversed(recent_dialogue(store_dir, limit=limit)):
        if turn.speaker != "subject" or turn.kind not in ("reply", "initiate", "retro"):
            continue
        prov = turn.provenance if isinstance(turn.provenance, dict) else {}
        for key in ("dialog_hubs", "concept_hints"):
            for raw in prov.get(key) or []:
                hub = str(raw)
                if not hub.startswith("ru.dialog.") or hub in seen:
                    continue
                seen.add(hub)
                hubs.append(hub)
        if len(hubs) >= 10:
            break
    return hubs


def apply_dialogue_thread_deltas(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    store_dir: Path | None,
    intent: str,
) -> None:
    """Elevate thread-open dialog hubs when partner turn overlaps their field body."""
    if intent != "social" or store_dir is None:
        return
    from casa.prisms.memory.concept_layer import discourse_concept_id

    hubs = dialogue_thread_hub_ids(store_dir.resolve())
    if not hubs:
        return
    hub_set = set(hubs)
    for block in blocks:
        disc = discourse_concept_id(block)
        if disc not in hub_set and not any(disc.startswith(f"{h}.") for h in hub_set):
            continue
        ov = partner_field_overlap(query, block)
        if ov <= 0:
            continue
        block["score"] = int(block.get("score") or 0) + min(22, ov * 2)
