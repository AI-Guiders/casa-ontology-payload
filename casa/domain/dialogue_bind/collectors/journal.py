"""Journal block collection in gather."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.domain.dialogue_bind.blocks import (
    block_dict,
    is_journal_bootstrap_text,
    is_wake_journal_text,
    score_text,
)
from casa.domain.dialogue_bind.dialogue import dialogue_continuity_blocks
from casa.domain.dialogue_bind.journal import journal_confirmed_blocks, journal_identity_blocks
from casa.domain.dialogue_bind.scoring import kb_reply_present, text_passage_overlap
from casa.prisms.memory.agent_journal import search_journal_entries


def collect_journal_blocks(
    store_dir: Path,
    q: str,
    *,
    intent: str,
    pt: set[str],
    kb_hits: list[tuple[dict[str, Any], int]],
) -> tuple[list[dict[str, Any]], list[str]]:
    blocks: list[dict[str, Any]] = []
    sources: list[str] = []

    if intent in ("journal", "recall"):
        confirmed = journal_confirmed_blocks(store_dir, q, intent=intent)
        blocks.extend(confirmed)
        if confirmed:
            sources.append("journal")
        for row in search_journal_entries(store_dir, domain="self", limit=24):
            text = str(row.get("text") or "").strip()
            eid = str(row.get("id") or "")
            if not text or not eid:
                continue
            if is_journal_bootstrap_text(text) or is_wake_journal_text(text):
                continue
            if not text_passage_overlap(text, pt) and score_text(q, text, base=0) < 6:
                continue
            blocks.append(
                block_dict(
                    f"agent.self.journal.{eid}",
                    text,
                    source="journal",
                    score=14,
                    section="journal_echo",
                )
            )
        blocks.extend(dialogue_continuity_blocks(store_dir, q))
        if any(b.get("source") == "dialogue" for b in blocks):
            sources.append("dialogue")
        if any(b.get("section") == "journal_echo" for b in blocks):
            sources.append("journal")
    elif intent != "discuss":
        confirmed = journal_confirmed_blocks(store_dir, q, intent=intent)
        blocks.extend(confirmed)
        if confirmed:
            sources.append("journal")
        jblocks = journal_identity_blocks(
            store_dir,
            q,
            intent=intent,
            kb_reply_present=kb_reply_present(kb_hits),
        )
        blocks.extend(jblocks)
        if jblocks:
            sources.append("journal")
        blocks.extend(dialogue_continuity_blocks(store_dir, q))
        if any(b.get("source") == "dialogue" for b in blocks):
            sources.append("dialogue")
    elif pt:
        for row in search_journal_entries(store_dir, domain="self", limit=40):
            text = str(row.get("text") or "").strip()
            eid = str(row.get("id") or "")
            if not text or not eid or not text_passage_overlap(text, pt):
                continue
            blocks.append(
                block_dict(
                    f"agent.self.journal.{eid}",
                    text,
                    source="journal",
                    score=12,
                    section="passage_echo",
                )
            )
        if any(b.get("section") == "passage_echo" for b in blocks):
            sources.append("journal")

    return blocks, sources
