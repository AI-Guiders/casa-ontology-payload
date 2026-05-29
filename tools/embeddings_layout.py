#!/usr/bin/env python3
"""Embeddings-on-layout v0 stub: salience boost from section hubs (no trainable vectors yet)."""

from __future__ import annotations

import hashlib


def _section_token(doc_path: str, section: str) -> str:
    return f"S:{doc_path}|{section}"


def _hash_embed(concept_id: str, dim: int = 8) -> list[float]:
    h = hashlib.blake2b(concept_id.encode("utf-8"), digest_size=dim).digest()
    return [b / 255.0 for b in h]


def salience_from_layout(
    *,
    concept_ids: list[str],
    present_tokens: list[str] | None,
    bundle: dict,
    base_salience: dict[str, float],
) -> dict[str, float]:
    """
    Boost concepts whose section hub token S:doc|section is present in decoded grid.
    Optional continuous prior from hash embedding (frozen, not learned).
    """
    present = set(present_tokens or [])
    claims_by_cid: dict[str, dict] = {}
    for c in bundle.get("claims") or []:
        cid = c.get("concept_id")
        if cid and cid not in claims_by_cid:
            claims_by_cid[str(cid)] = c

    out = dict(base_salience)
    for cid in concept_ids:
        claim = claims_by_cid.get(cid)
        boost = 0.0
        if claim:
            dp = str(claim.get("doc_path") or "")
            sec = str(claim.get("section") or "")
            if dp and sec and _section_token(dp, sec) in present:
                boost += 0.25
        emb = sum(_hash_embed(cid)) / 8.0
        out[cid] = out.get(cid, 0.5) * (1.0 + boost) + 0.05 * emb
    return out
