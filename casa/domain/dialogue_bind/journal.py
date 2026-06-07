"""Journal block collection and recall helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from casa.domain.dialogue_bind.blocks import (
    block_dict,
    is_journal_bootstrap_text,
    is_wake_journal_text,
    score_text,
)
from casa.domain.dialogue_bind.field import salient_recall_tokens
from casa.domain.dialogue_bind.scoring import text_passage_overlap
from casa.prisms.memory.agent_journal import search_journal_entries
from casa.prisms.memory.agent_memory_ops import agent_recall


def journal_skip_on_dialogue(row: dict[str, Any], *, intent: str) -> bool:
    if intent != "social":
        return False
    kind = str(row.get("kind") or "")
    tags = [str(t) for t in (row.get("tags") or [])]
    if kind == "observation" and any(t.startswith("cue:") or t == "surprise" for t in tags):
        return True
    if kind == "hypothesis":
        return True
    return False


def journal_confirmed_blocks(store_dir: Path, query: str, *, intent: str) -> list[dict[str, Any]]:
    """Field-mastery-first: confirmed hypotheses beat transport-only KB."""
    blocks: list[dict[str, Any]] = []
    seen: set[str] = set()
    ql = query.lower()
    for row in search_journal_entries(store_dir, domain="self", limit=80):
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        if str(meta.get("status") or "") != "confirmed":
            continue
        eid = str(row.get("id") or "")
        text = str(row.get("text") or "").strip()
        if not text or eid in seen:
            continue
        cues = [str(c) for c in (meta.get("test_cues") or [])]
        concepts = [str(c) for c in (row.get("concepts") or [])]
        matched = any(cue.lower() in ql or ql in cue.lower() for cue in cues if cue)
        if not matched and intent == "math":
            matched = any(tok in ql for tok in cues if tok and len(tok) <= len(ql) + 2)
        if not matched:
            continue
        seen.add(eid)
        cid = concepts[0] if concepts else f"agent.self.journal.{eid}"
        base = 34 if intent == "math" else 28
        blocks.append(
            block_dict(
                cid,
                text,
                source="journal",
                score=score_text(query, text, base=base),
                section="confirmed",
            )
        )
    return blocks


def journal_cap_for_intent(intent: str, *, kb_reply_present: bool) -> int:
    if intent == "social" and kb_reply_present:
        return 6
    if intent == "social":
        return 18
    if intent == "math":
        return 10
    if intent == "grammar":
        return 8
    return 14


def journal_recall_records(store_dir: Path, query: str, *, limit: int = 6) -> list[dict[str, Any]]:
    """Full-line recall first; then salient lemma / lang.word concept."""
    q = (query or "").strip()
    seen_ids: set[str] = set()
    rows: list[dict[str, Any]] = []

    def _merge(*, recall_query: str | None = None, concept: str | None = None) -> None:
        rec = agent_recall(store_dir, query=recall_query, concept=concept, limit=limit)
        for row in rec.get("records") or rec.get("entries") or []:
            eid = str(row.get("id") or "")
            if not eid or eid in seen_ids:
                continue
            seen_ids.add(eid)
            rows.append(row)

    if q:
        _merge(recall_query=q)
    if not rows:
        for tok in salient_recall_tokens(q):
            _merge(recall_query=tok)
            if rows:
                break
    m = re.search(r"слово\s+([\w\u0400-\u04FF]+)", q, flags=re.IGNORECASE)
    if m and len(rows) < limit:
        _merge(concept=f"lang.word.{m.group(1).lower()}")
    return rows[:limit]


def journal_identity_blocks(
    store_dir: Path,
    query: str,
    *,
    intent: str,
    kb_reply_present: bool,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    seen_rows: dict[str, dict[str, Any]] = {}
    for tag in ("bootstrap", "wake", "notebook:self"):
        for row in search_journal_entries(store_dir, tags=[tag], limit=6):
            eid = str(row.get("id") or "")
            if eid and eid not in seen_rows:
                seen_rows[eid] = row
    if not seen_rows:
        for row in search_journal_entries(store_dir, domain="self", limit=10):
            eid = str(row.get("id") or "")
            if eid:
                seen_rows[eid] = row
    recall_rows = journal_recall_records(store_dir, query, limit=6)
    seen: set[str] = set()
    cap = journal_cap_for_intent(intent, kb_reply_present=kb_reply_present)
    for hit in recall_rows:
        eid = str(hit.get("id") or "")
        text = str(hit.get("text") or "").strip()
        if not text or eid in seen:
            continue
        if journal_skip_on_dialogue(hit, intent=intent):
            continue
        seen.add(eid)
        base = score_text(query, text, base=10 if intent == "social" else 8)
        if intent == "explain":
            for tok in salient_recall_tokens(query):
                if tok.lower() in text.lower():
                    base = max(base, 34)
                    break
        blocks.append(
            block_dict(
                f"agent.self.journal.{eid}",
                text,
                source="journal",
                score=min(cap, base),
            )
        )
    for row in seen_rows.values():
        eid = str(row.get("id") or "")
        text = str(row.get("text") or "").strip()
        if not text or eid in seen:
            continue
        if journal_skip_on_dialogue(row, intent=intent):
            continue
        if row.get("kind") == "hypothesis" and intent == "social":
            continue
        row_tags = [str(t) for t in (row.get("tags") or [])]
        if intent == "social" and "bootstrap" in row_tags and kb_reply_present:
            continue
        if intent == "social" and is_journal_bootstrap_text(text) and kb_reply_present:
            continue
        seen.add(eid)
        base = min(cap, 12 if "bootstrap" in row_tags else 10)
        blocks.append(
            block_dict(
                f"agent.self.journal.{eid}",
                text,
                source="journal",
                score=score_text(query, text, base=base),
            )
        )
    return blocks
