"""Passage block collection from gather."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.blocks import block_dict
from casa.prisms.tick.passage import (
    passage_salient_lemmas,
    passage_sentence_bind_rows,
    passage_tokens,
    split_passage_query,
)
from casa.prisms.tick.semantic_read import has_passage_context


def collect_passage_blocks(
    q: str,
    *,
    intent: str,
    compose_mode: str | None,
    merged_bundle: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str], set[str]]:
    """Collect passage-related blocks; returns blocks, source tags, passage token set."""
    blocks: list[dict[str, Any]] = []
    sources: list[str] = []
    pt: set[str] = set()

    passage, _ = split_passage_query(q)

    if compose_mode == "journal" and not has_passage_context(q):
        seen_cue: set[str] = set()
        for idx, sent, sent_score in passage_sentence_bind_rows(q, q):
            cid = f"passage.sent.{idx}"
            if cid in seen_cue:
                continue
            seen_cue.add(cid)
            blocks.append(
                block_dict(
                    cid,
                    sent,
                    source="passage",
                    score=sent_score,
                    section="passage_sent",
                )
            )
        for lemma in passage_salient_lemmas(q, q):
            surf = f"passage.surface.{lemma}"
            if surf in seen_cue:
                continue
            seen_cue.add(surf)
            blocks.append(
                block_dict(
                    surf,
                    f"«{lemma}»",
                    source="passage",
                    score=20,
                    section="passage_lattice",
                )
            )
        if seen_cue:
            pt = passage_tokens(q)
            sources.append("passage")

    if has_passage_context(q) and merged_bundle and intent in ("discuss", "rewrite", "journal"):
        pt = passage_tokens(passage)
        by_cid = {
            str(c.get("concept_id") or ""): c
            for c in (merged_bundle.get("claims") or [])
            if c.get("concept_id")
        }
        seen_passage: set[str] = set()
        for cid, claim in by_cid.items():
            if cid.startswith("ru.meta.discourse."):
                text = str(claim.get("text") or "").strip()
                if text and cid not in seen_passage:
                    seen_passage.add(cid)
                    blocks.append(
                        block_dict(
                            cid,
                            text,
                            source="kb",
                            score=32,
                            section="discourse",
                            slots=claim.get("slots") if isinstance(claim.get("slots"), dict) else None,
                        )
                    )
            if not cid.startswith("lang.word."):
                continue
            lemma = cid.rsplit(".", 1)[-1].lower()
            if not lemma or lemma not in pt or cid in seen_passage:
                continue
            seen_passage.add(cid)
            text = str(claim.get("text") or "").strip()
            if text:
                blocks.append(
                    block_dict(
                        cid,
                        text,
                        source="kb",
                        score=30,
                        section="passage",
                        slots=claim.get("slots") if isinstance(claim.get("slots"), dict) else None,
                    )
                )
        _, passage_question = split_passage_query(q)
        for idx, sent, sent_score in passage_sentence_bind_rows(passage, passage_question):
            sent_cid = f"passage.sent.{idx}"
            if sent_cid in seen_passage:
                continue
            seen_passage.add(sent_cid)
            blocks.append(
                block_dict(
                    sent_cid,
                    sent,
                    source="passage",
                    score=sent_score,
                    section="passage_sent",
                )
            )
        for lemma in passage_salient_lemmas(passage, passage_question):
            surf_cid = f"passage.surface.{lemma}"
            if surf_cid in seen_passage:
                continue
            seen_passage.add(surf_cid)
            blocks.append(
                block_dict(
                    surf_cid,
                    f"«{lemma}»",
                    source="passage",
                    score=22,
                    section="passage_lattice",
                )
            )
        if pt or seen_passage:
            sources.append("passage")

    return blocks, sources, pt
