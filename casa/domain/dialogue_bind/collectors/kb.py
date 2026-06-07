"""KB block collection from semantic read."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.blocks import block_dict
from casa.domain.dialogue_bind.scoring import kb_hit_allowed


def collect_kb_blocks(
    query_read: Any,
    intent: str,
    pt: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    blocks: list[dict[str, Any]] = []
    sources: list[str] = []
    seen_kb: set[str] = set()

    for claim, score in query_read.kb_hits:
        cid = str(claim.get("concept_id") or "")
        text = str(claim.get("text") or "").strip()
        if not cid or not text or cid in seen_kb:
            continue
        if not kb_hit_allowed(cid, intent, pt):
            continue
        seen_kb.add(cid)
        claim_slots = claim.get("slots")
        blocks.append(
            block_dict(
                cid,
                text,
                source="kb",
                score=score,
                section=str(claim.get("_bundle_id") or claim.get("section") or "kb"),
                slots=claim_slots if isinstance(claim_slots, dict) else None,
            )
        )
    if query_read.kb_hits:
        sources.append("kb")
    elif query_read.concept_hints and intent == "math":
        for hint in query_read.concept_hints[:4]:
            blocks.append(
                block_dict(hint, f"Surface hint → {hint}.", source="field", score=14)
            )
        sources.append("field")

    return blocks, sources
