"""Anaphora — deictic class from bundle + ring referent (Plan C E5–E8)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from casa.domain.dialogue_bind.blocks import block_dict, score_text
from casa.domain.dialogue_bind.dialog_bind_policy import _slots
from casa.domain.dialogue_turn import recent_dialogue

_DEVELOPMENTAL_TURN_KINDS = frozenset({"recast", "expand", "clarify", "correction"})


def deictic_markers(bundle: dict[str, Any] | None = None) -> tuple[str, ...]:
    raw = _slots("ru.meta.dialog.anaphora", bundle).get("deictic_markers") or ""
    return tuple(p.strip().lower() for p in str(raw).split("|") if p.strip())


def query_has_deictic(query: str, bundle: dict[str, Any] | None = None) -> bool:
    ql = (query or "").strip().lower()
    if not ql:
        return False
    for marker in deictic_markers(bundle):
        if marker in ql:
            return True
    return False


def recent_ring_referent(store_dir: Path, *, limit: int = 12, exclude_text: str = "") -> tuple[str, str, int]:
    """Newest proposition/hub from ring + source snippet and ring age."""
    turns = recent_dialogue(store_dir, limit=limit)
    excluded = exclude_text.strip()
    for age, turn in enumerate(turns):
        if (
            turn.speaker != "partner"
            or turn.kind in _DEVELOPMENTAL_TURN_KINDS
            or not turn.text.strip()
        ):
            continue
        snippet = turn.text.strip()
        if excluded and snippet == excluded:
            continue
        safe = re.sub(r"[^\w\u0400-\u04FF]+", "_", snippet[:40]).strip("_").lower()
        ref = f"ru.prop.partner.turn.{safe[:24] or 'recent'}"
        return ref, snippet[:120], age
    for age, turn in enumerate(turns):
        if turn.kind in _DEVELOPMENTAL_TURN_KINDS:
            continue
        if excluded and turn.text.strip() == excluded:
            continue
        prov = turn.provenance if isinstance(turn.provenance, dict) else {}
        for cid in prov.get("prop_ids") or []:
            ref = str(cid)
            if ref.startswith("ru.prop."):
                return ref, turn.text[:120], age
        for hub in prov.get("dialog_hubs") or []:
            ref = str(hub)
            if ref.startswith(("ru.prop.", "ru.dialog.")):
                return ref, turn.text[:120], age
        focus = prov.get("thread_focus")
        if isinstance(focus, dict):
            ref = str(focus.get("referent_prop") or "")
            if ref:
                return ref, turn.text[:120], age
    return "", "", 0


def anaphora_referent_blocks(
    store_dir: Path | None,
    query: str,
    bundle: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if store_dir is None or not query_has_deictic(query, bundle):
        return []
    referent, snippet, age = recent_ring_referent(store_dir.resolve(), exclude_text=query)
    if not referent:
        return []
    overlap = score_text(query, snippet, base=0) if snippet else 0
    score = 28 + min(20, overlap)
    if age:
        score = max(8, score - age * 4)
    return [
        block_dict(
            "dialog.context.referent",
            f"Референт нити: {referent}.",
            source="dialogue",
            score=score,
            section="dialogue_referent",
            slots={
                "referent_prop": referent,
                "referent_snippet": snippet[:80],
                "referent_age": str(age),
                "deictic": "1",
            },
        )
    ]


def thread_focus_from_blocks(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    focus_slots: dict[str, str] = {}
    referent_prop = ""
    for row in blocks:
        cid = str(row.get("concept_id") or "")
        slots = row.get("slots") if isinstance(row.get("slots"), dict) else {}
        if cid == "dialog.context.focus_recent":
            focus_slots = {str(k): str(v) for k, v in slots.items()}
        if cid == "dialog.context.referent":
            referent_prop = str(slots.get("referent_prop") or "")
    if not focus_slots and not referent_prop:
        return None
    out: dict[str, Any] = {}
    if focus_slots.get("thread_terms"):
        out["terms"] = [t for t in focus_slots["thread_terms"].split("|") if t]
    if focus_slots.get("thread_age"):
        out["age"] = int(focus_slots["thread_age"])
    if referent_prop or focus_slots.get("referent_prop"):
        out["referent_prop"] = referent_prop or focus_slots.get("referent_prop")
    return out or None
