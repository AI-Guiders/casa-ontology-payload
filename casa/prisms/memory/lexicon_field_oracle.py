#!/usr/bin/env python3
"""Lexicon usage axes on L3 field — predict without lexicon_axes.jsonl / bundle oracle."""

from __future__ import annotations

import json
from typing import Any

from casa.prisms.memory.f0_field_reading import pack_field_payload, unpack_field_payload
from casa.prisms.memory.ortho_field import imprint_edge, l3_process_edges
from casa.prisms.memory.vocab import norm_word

_AXIS_REL = "usage_axis"
_L2_CID_PREFIX = "lang.word."


def _axis_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k != "lemma"}


def materialize_lexicon_axis_edges(axes: dict[str, dict[str, Any]]) -> list[tuple[str, str, str]]:
    """Ingest-only: lemma axis rows → L3 E: edges."""
    edges: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for raw, row in (axes or {}).items():
        w = norm_word(str(raw or row.get("lemma") or ""))
        if not w:
            continue
        cid = f"{_L2_CID_PREFIX}{w}"
        dst = pack_field_payload(_axis_payload({**row, "lemma": w}))
        key = (cid, _AXIS_REL, dst)
        if key in seen:
            continue
        seen.add(key)
        edges.append(key)
    return edges


def lexicon_oracle_from_l3(state: dict) -> dict[str, dict[str, Any]]:
    """Rebuild lemma → axis row from L3 usage_axis edges."""
    out: dict[str, dict[str, Any]] = {}
    for src, rel, dst in l3_process_edges(state):
        if rel != _AXIS_REL or not src.startswith(_L2_CID_PREFIX):
            continue
        lemma = norm_word(src[len(_L2_CID_PREFIX) :])
        if not lemma:
            continue
        try:
            row = unpack_field_payload(dst)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        row["lemma"] = lemma
        out[lemma] = row
    return out


def sync_lexicon_axes_to_field(
    state: dict,
    axes: dict[str, dict[str, Any]],
    *,
    copies: int = 3,
) -> int:
    """Imprint missing usage_axis edges on L3 (ingest / boot migration)."""
    existing = lexicon_oracle_from_l3(state)
    added = 0
    for src, rel, dst in materialize_lexicon_axis_edges(axes):
        lemma = norm_word(src[len(_L2_CID_PREFIX) :])
        if lemma in existing:
            continue
        imprint_edge(state, src, rel, dst, copies=copies)
        existing[lemma] = {"lemma": lemma}
        added += 1
    if added:
        state["field_version"] = int(state.get("field_version") or 0) + 1
    return added


def lexicon_oracle_for_predict(state: dict) -> dict[str, dict[str, Any]]:
    """Field-first oracle; sidecar dict in state is legacy fallback only."""
    field = lexicon_oracle_from_l3(state)
    if field:
        return field
    cached = state.get("lexicon_axes")
    return cached if isinstance(cached, dict) else {}
