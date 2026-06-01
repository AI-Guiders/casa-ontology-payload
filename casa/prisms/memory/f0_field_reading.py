#!/usr/bin/env python3
"""Reading frames / keywords / senses materialized on F0 field — predict without cartridge."""

from __future__ import annotations

import base64
import json
from typing import Any

_FRAME_REL = "frame"
_KEYWORD_REL = "keyword"
_META_REL = "reading_model"


def pack_field_payload(obj: dict[str, Any]) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def unpack_field_payload(token: str) -> dict[str, Any]:
    pad = "=" * (-len(token) % 4)
    raw = base64.urlsafe_b64decode(token + pad)
    out = json.loads(raw.decode("utf-8"))
    return out if isinstance(out, dict) else {}


def materialize_reading_edges(bundle: dict) -> list[dict[str, str]]:
    """Turn cartridge reading_contexts, math_keywords, math_glyphs into graph edges (ingest-only)."""
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(src: str, rel: str, dst: str) -> None:
        key = (src, rel, dst)
        if key in seen:
            return
        seen.add(key)
        edges.append({"src": src, "relation": rel, "dst": dst})

    for ctx in bundle.get("reading_contexts") or []:
        cid = str(ctx.get("id") or "")
        if not cid:
            continue
        when = ctx.get("when")
        if isinstance(when, str):
            when = {"shape": when}
        payload = {"when": when or {}, "weight": float(ctx.get("weight") or 10)}
        add(cid, _FRAME_REL, pack_field_payload(payload))

    for cid, words in (bundle.get("math_keywords") or {}).items():
        concept = str(cid or "")
        if not concept.startswith("math."):
            continue
        for w in words or []:
            word = str(w or "").strip().lower()
            if word:
                add(concept, _KEYWORD_REL, word)

    for sense in bundle.get("symbol_senses") or []:
        when = sense.get("when")
        if not when:
            continue
        glyph = str(sense.get("glyph") or "")
        context = str(sense.get("context") or sense.get("context_id") or "")
        concept = str(sense.get("concept_id") or "")
        if glyph and context and concept:
            add(f"{context}@{glyph}", "sense_when", pack_field_payload({"when": when, "concept_id": concept}))

    return edges


def _glyph_from_symbol(sym: str) -> str:
    if sym.startswith("grapheme.latn."):
        tail = sym.rsplit(".", 1)[-1]
        if len(tail) == 1:
            return tail
    if sym.startswith("grapheme.cyrl."):
        tail = sym.rsplit(".", 1)[-1]
        if len(tail) == 1:
            return tail
    return sym


def reading_model_from_decoded(decoded: dict) -> dict[str, Any]:
    """Rebuild reading_contexts / symbol_senses / math_keywords from field edges only."""
    reading_contexts: list[dict[str, Any]] = []
    math_keywords: dict[str, list[str]] = {}
    symbol_senses: list[dict[str, Any]] = []
    sense_when: dict[tuple[str, str], dict[str, Any]] = {}

    for edge in decoded.get("edges") or []:
        es = str(edge)

        if "|denotes|" in es:
            src, _, dst = es.partition("|denotes|")
            if not dst.startswith("math."):
                continue
            if "@" in src:
                sym, ctx = src.rsplit("@", 1)
            else:
                sym, ctx = src, "math.ctx.arithmetic"
            glyph = _glyph_from_symbol(sym)
            sense: dict[str, Any] = {
                "glyph": glyph,
                "context": ctx,
                "concept_id": dst,
            }
            if sym.startswith("grapheme."):
                sense["grapheme"] = sym
            override = sense_when.get((ctx, glyph))
            if override:
                sense["when"] = override.get("when")
            symbol_senses.append(sense)
            continue

        parts = es.split("|")
        if len(parts) < 3:
            continue
        src, rel = parts[0], parts[1]
        dst = "|".join(parts[2:])

        if rel == _FRAME_REL:
            payload = unpack_field_payload(dst)
            when = payload.get("when") or {}
            reading_contexts.append(
                {
                    "id": src,
                    "when": when,
                    "weight": float(payload.get("weight") or 10),
                }
            )
            continue

        if rel == _KEYWORD_REL and src.startswith("math."):
            math_keywords.setdefault(src, []).append(dst)
            continue

        if rel == "sense_when" and "@" in src:
            ctx, glyph = src.split("@", 1)
            payload = unpack_field_payload(dst)
            sense_when[(ctx, glyph)] = payload
            continue

        continue

    return {
        "reading_contexts": reading_contexts,
        "symbol_senses": symbol_senses,
        "math_keywords": math_keywords,
    }


def reading_model_for_predict(decoded: dict, bundle: dict | None = None) -> dict[str, Any]:
    """Field-first; optional bundle fallback for legacy tests without materialized frames."""
    model = reading_model_from_decoded(decoded)
    if model.get("reading_contexts") or not bundle:
        return model
    return {
        "reading_contexts": list(bundle.get("reading_contexts") or []),
        "symbol_senses": list(bundle.get("symbol_senses") or []),
        "math_keywords": dict(bundle.get("math_keywords") or {}),
    }
