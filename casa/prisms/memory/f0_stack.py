#!/usr/bin/env python3
"""F0 math lattice stack — encode/decode M: tokens on field."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
from pathlib import Path
from typing import Any

from casa.prisms.shared.codec_grid import Grid
from casa.prisms.memory.stack import _place_token
from casa.prisms.memory.vk_grapheme import grapheme_concept_for_char
from casa.prisms.memory.f0_reading import (
    analyze_cue,
    detect_reading_contexts,
    score_contextual_senses,
    score_field_glyph_numerals,
    score_field_infix_operators,
    unbound_operators,
)

_SYMBOL_PREFIXES = ("grapheme.", "punct.", "vk.")
_CTX_SEP = "@"


def load_f0_stack(path: Path | None = None) -> dict:
    p = path or Path("design/f0-math-lattice-stack.json")
    return json.loads(p.read_text(encoding="utf-8"))


def lattice_meta_f0(stack: dict, lattice_id: str) -> dict:
    for lat in stack.get("lattices") or []:
        if lat.get("id") == lattice_id:
            return lat
    raise KeyError(lattice_id)


def contextual_symbol_key(symbol: str, context_id: str) -> str:
    return f"{symbol}{_CTX_SEP}{context_id}"


def _grapheme_for_glyph(glyph: str) -> str | None:
    if len(glyph) != 1:
        return None
    try:
        gc, _ = grapheme_concept_for_char(glyph)
        return gc
    except ValueError:
        return None


def augment_bundle_symbol_links(bundle: dict) -> dict:
    """Expand symbol_senses + keyboard_symbols into contextual graph edges."""
    out = json.loads(json.dumps(bundle))
    graph = out.setdefault("graph", {})
    edges: list[dict[str, str]] = list(graph.get("edges") or [])
    seen = {(e.get("src"), e.get("relation"), e.get("dst")) for e in edges}
    symbols: set[str] = set(out.get("symbol_concepts") or [])

    for ctx in out.get("reading_contexts") or []:
        cid = str(ctx.get("id") or "")
        if cid.startswith("math.ctx."):
            key = (cid, "kind", "reading_context")
            if key not in seen:
                edges.append({"src": cid, "relation": "kind", "dst": "reading_context"})
                seen.add(key)

    for sense in out.get("symbol_senses") or []:
        glyph = str(sense.get("glyph") or "")
        context = str(sense.get("context") or sense.get("context_id") or "")
        concept = str(sense.get("concept_id") or "")
        if not (glyph and context and concept):
            continue
        grapheme = str(sense.get("grapheme") or "") or _grapheme_for_glyph(glyph) or glyph
        if grapheme.startswith(_SYMBOL_PREFIXES):
            symbols.add(grapheme)
        sym_key = contextual_symbol_key(grapheme if grapheme.startswith(_SYMBOL_PREFIXES) else glyph, context)
        for src, rel, dst in (
            (grapheme if grapheme.startswith(_SYMBOL_PREFIXES) else glyph, "in_context", context),
            (sym_key, "denotes", concept),
        ):
            key = (src, rel, dst)
            if key not in seen:
                edges.append({"src": src, "relation": rel, "dst": dst})
                seen.add(key)

    for item in out.get("keyboard_symbols") or []:
        glyph = str(item.get("char") or "")
        gc = str(item.get("grapheme") or "") or (_grapheme_for_glyph(glyph) or "")
        concept = str(item.get("math_op") or item.get("concept_id") or "")
        context = str(item.get("context") or item.get("context_id") or "math.ctx.arithmetic")
        if not (gc and concept.startswith("math.")):
            continue
        symbols.add(gc)
        sym_key = contextual_symbol_key(gc, context)
        for src, rel, dst in ((gc, "in_context", context), (sym_key, "denotes", concept)):
            key = (src, rel, dst)
            if key not in seen:
                edges.append({"src": src, "relation": rel, "dst": dst})
                seen.add(key)

    for item in out.get("math_glyphs") or []:
        glyph = str(item.get("glyph") or "")
        context = str(item.get("context") or item.get("context_id") or "")
        concept = str(item.get("concept_id") or "")
        if not (glyph and context and concept.startswith("math.")):
            continue
        grapheme = str(item.get("grapheme") or "") or (_grapheme_for_glyph(glyph) if len(glyph) == 1 else "")
        sym = grapheme if grapheme.startswith(_SYMBOL_PREFIXES) else glyph
        if sym.startswith(_SYMBOL_PREFIXES):
            symbols.add(sym)
        sym_key = contextual_symbol_key(sym, context)
        for src, rel, dst in ((sym, "in_context", context), (sym_key, "denotes", concept)):
            key = (src, rel, dst)
            if key not in seen:
                edges.append({"src": src, "relation": rel, "dst": dst})
                seen.add(key)

    from casa.prisms.memory.f0_field_reading import materialize_reading_edges

    edges.extend(materialize_reading_edges(out))

    if symbols:
        out["symbol_concepts"] = sorted(symbols)
    graph["edges"] = edges
    return out


def _symbol_concepts_on_field(bundle: dict) -> set[str]:
    ids: set[str] = set(bundle.get("symbol_concepts") or [])
    for e in (bundle.get("graph") or {}).get("edges") or []:
        for side in ("src", "dst"):
            cid = str(e.get(side) or "")
            if cid.startswith(_SYMBOL_PREFIXES) or cid.startswith("math.ctx."):
                ids.add(cid.split(_CTX_SEP, 1)[0] if _CTX_SEP in cid else cid)
    return ids


def concept_in_context(decoded: dict, symbol_key: str, context_id: str) -> str | None:
    """Follow E:symbol@ctx|denotes|math.* on field."""
    prefix = f"{contextual_symbol_key(symbol_key, context_id)}|denotes|"
    for edge in decoded.get("edges") or []:
        if str(edge).startswith(prefix):
            dst = str(edge)[len(prefix) :]
            if dst.startswith("math."):
                return dst
    return None


def math_op_for_grapheme(decoded: dict, grapheme_id: str, *, context_id: str = "math.ctx.arithmetic") -> str | None:
    return concept_in_context(decoded, grapheme_id, context_id)


def encode_f0_lattice(
    bundle: dict,
    *,
    lattice_id: str = "schema-math",
    stack: dict | None = None,
    width: int = 32,
    height: int = 32,
    copies: int = 5,
) -> dict[str, Any]:
    """Place M: / C: / E: tokens for math bundle on one F lattice."""
    bundle = augment_bundle_symbol_links(bundle)
    stack = stack or load_f0_stack()
    meta = lattice_meta_f0(stack, lattice_id)
    size = meta.get("size") or {}
    w = int(size.get("width") or width)
    h = int(size.get("height") or height)
    grid = Grid.empty(w, h)

    for item in bundle.get("math_tokens") or []:
        tok = str(item.get("token") or "")
        if tok:
            grid = _place_token(grid, tok, tok, copies=int(item.get("copies") or copies))

    for c in bundle.get("claims") or []:
        cid = str(c.get("concept_id") or "")
        if cid.startswith("math."):
            grid = _place_token(grid, f"C:{cid}", f"C:{cid}", copies=copies)

    for cid in sorted(_symbol_concepts_on_field(bundle)):
        grid = _place_token(grid, f"C:{cid}", f"C:{cid}", copies=max(2, copies // 2))

    for e in (bundle.get("graph") or {}).get("edges") or []:
        src, rel, dst = e.get("src"), e.get("relation"), e.get("dst")
        if not (src and rel and dst):
            continue
        tok = f"E:{src}|{rel}|{dst}"
        grid = _place_token(grid, tok, tok, copies=max(2, copies // 2), radius=4)

    return {
        "f_level": int(meta.get("f_level") or 0),
        "width": w,
        "height": h,
        "cells": grid.cells,
        "subsystem_id": "first_signal_math",
        "token_prefix": meta.get("token_prefix") or ["M:"],
    }


def decode_f0_lattice(lattice: dict, *, min_votes: int = 1) -> dict[str, Any]:
    vote: dict[str, int] = {}
    for cell in lattice.get("cells") or []:
        for t in cell:
            vote[t] = vote.get(t, 0) + 1

    concepts: list[dict[str, Any]] = []
    math_tokens: list[dict[str, Any]] = []
    for t, v in vote.items():
        if v < min_votes:
            continue
        if t.startswith("C:"):
            concepts.append({"concept_id": t[2:], "votes": v})
        elif t.startswith("M:"):
            math_tokens.append({"token": t, "votes": v})

    concepts.sort(key=lambda c: (-int(c["votes"]), c["concept_id"]))
    math_tokens.sort(key=lambda m: (-int(m["votes"]), m["token"]))
    edges = sorted(t[2:] for t, v in vote.items() if t.startswith("E:") and v >= min_votes)

    return {
        "min_votes": min_votes,
        "concept_ids": [c["concept_id"] for c in concepts],
        "concepts": concepts,
        "math_tokens": [m["token"] for m in math_tokens],
        "math_token_votes": math_tokens,
        "edges": edges,
        "seen_tokens": len(vote),
    }


def f0_digest(decoded: dict, *, prefix: str = "math.") -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for c in decoded.get("concepts") or []:
        cid = str(c.get("concept_id") or "")
        if cid.startswith(prefix):
            out.append((cid, int(c.get("votes") or 0)))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


_MATH_OP_GLYPH: dict[str, str] = {
    "math.op.add": "+",
    "math.op.sub": "-",
    "math.op.mul": "*",
    "math.op.eq": "=",
    "math.op.concat": "+",
    "math.op.or": "|",
}


def analyze_f0_cue_ranking(
    decoded: dict,
    cue: str,
    *,
    reading_model: dict | None = None,
    bundle: dict | None = None,
) -> dict[str, Any]:
    """Rank math.* from field; reading frames from materialized edges (bundle ingest-only fallback)."""
    from casa.prisms.memory.f0_field_reading import reading_model_for_predict

    model = reading_model or reading_model_for_predict(decoded, bundle)
    cue = cue.strip()
    unbound = unbound_operators(
        cue,
        model,
        decoded,
        concept_in_context=concept_in_context,
        grapheme_for_glyph=_grapheme_for_glyph,
    )
    contexts = detect_reading_contexts(cue, reading_model=model, unbound=unbound)
    cl = cue.lower()
    scores: dict[str, int] = {}

    scores.update(
        score_contextual_senses(
            model,
            decoded,
            cue,
            contexts,
            concept_in_context=concept_in_context,
            grapheme_for_glyph=_grapheme_for_glyph,
            unbound=unbound,
        )
    )
    scores.update(
        score_field_infix_operators(
            cue,
            model,
            decoded,
            contexts,
            concept_in_context=concept_in_context,
            grapheme_for_glyph=_grapheme_for_glyph,
        )
    )
    scores.update(
        score_field_glyph_numerals(
            cue,
            decoded,
            contexts,
            grapheme_for_glyph=_grapheme_for_glyph,
        )
    )

    if len(cue) == 1:
        try:
            gc, _ = grapheme_concept_for_char(cue)
            ctx = max(contexts, key=contexts.get)
            op = concept_in_context(decoded, gc, ctx)
            if op:
                scores[op] = scores.get(op, 0) + 12
        except ValueError:
            pass

    for cid, words in (model.get("math_keywords") or {}).items():
        for w in words:
            ws = str(w).lower()
            if ws in cl or (len(ws) == 1 and ws in cue):
                scores[str(cid)] = scores.get(str(cid), 0) + 3

    base = {cid: v for cid, v in f0_digest(decoded)}
    _digest_skip = ("math.ctx.", "math.entity.", "math.category.", "math.dim.")
    for cid, v in base.items():
        if cid.startswith(_digest_skip):
            continue
        scores[cid] = scores.get(cid, 0) + min(v, 5)

    from casa.prisms.memory.f0_cardinal_abstract import score_abstract_mul_cue
    from casa.prisms.memory.f0_equiv_extract import score_equiv_cue
    from casa.prisms.memory.f0_pattern_extract import score_emerged_patterns_from_cue

    scores.update(score_emerged_patterns_from_cue(cue, decoded))
    scores.update(score_abstract_mul_cue(cue, decoded))
    scores.update(score_equiv_cue(cue, decoded, bundle=None))

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    return {
        "ranked": ranked,
        "unbound_operators": unbound,
        "contexts": contexts,
        "coverage_gaps": [f"unbound:{u['op']}@{u['context']}" for u in unbound],
    }


def rank_cue_on_f0(
    decoded: dict,
    cue: str,
    *,
    reading_model: dict | None = None,
    bundle: dict | None = None,
) -> list[tuple[str, int]]:
    """Rank math.* — reading frames from field (cartridge optional fallback)."""
    return analyze_f0_cue_ranking(decoded, cue, reading_model=reading_model, bundle=bundle)["ranked"]


def strengthen_denotes_edge(
    lattices: dict[str, dict],
    lattice_id: str,
    symbol_key: str,
    context_id: str,
    concept_id: str,
    *,
    copies: int = 4,
) -> bool:
    """Mint or reinforce E:symbol@ctx|denotes|concept on F0 lattice (Extract after teacher)."""
    if lattice_id not in lattices or not concept_id.startswith("math."):
        return False
    lat = lattices[lattice_id]
    g = Grid(
        width=int(lat["width"]),
        height=int(lat["height"]),
        cells=[list(x) for x in lat["cells"]],
    )
    sym_key = contextual_symbol_key(symbol_key, context_id)
    for src, rel, dst in (
        (symbol_key, "in_context", context_id),
        (sym_key, "denotes", concept_id),
    ):
        tok = f"E:{src}|{rel}|{dst}"
        g = _place_token(g, tok, tok, copies=copies, radius=4)
    c_tok = f"C:{concept_id}"
    g = _place_token(g, c_tok, c_tok, copies=max(2, copies // 2), radius=3)
    lat["cells"] = g.cells
    return True


def graph_edge_token(src: str, relation: str, dst: str) -> str:
    return f"E:{str(src or '').strip()}|{str(relation or '').strip()}|{str(dst or '').strip()}"


def count_edge_copies(lat: dict[str, Any], src: str, relation: str, dst: str) -> int:
    tok = graph_edge_token(src, relation, dst)
    return sum(cell.count(tok) for cell in lat.get("cells") or [] if isinstance(cell, list))


def weaken_graph_edge(
    lattices: dict[str, dict],
    lattice_id: str,
    src: str,
    relation: str,
    dst: str,
    *,
    copies: int | None = None,
) -> int:
    """Remove edge token copies from lattice. copies=None → remove all."""
    src, relation, dst = str(src or "").strip(), str(relation or "").strip(), str(dst or "").strip()
    if not (src and relation and dst):
        return 0
    lat = lattices.get(lattice_id)
    if not lat:
        return 0
    tok = graph_edge_token(src, relation, dst)
    removed = 0
    budget = copies
    for cell in lat.get("cells") or []:
        if not isinstance(cell, list):
            continue
        while tok in cell and (budget is None or removed < budget):
            cell.remove(tok)
            removed += 1
    return removed


def strengthen_graph_edge(
    lattices: dict[str, dict],
    lattice_id: str,
    src: str,
    relation: str,
    dst: str,
    *,
    copies: int = 4,
) -> bool:
    """Mint or reinforce E:src|relation|dst (+ C: for math.* / lang.* endpoints)."""
    src, relation, dst = str(src or "").strip(), str(relation or "").strip(), str(dst or "").strip()
    if not (src and relation and dst):
        return False
    if lattice_id not in lattices:
        return False
    lat = lattices[lattice_id]
    g = Grid(
        width=int(lat["width"]),
        height=int(lat["height"]),
        cells=[list(x) for x in lat["cells"]],
    )
    tok = f"E:{src}|{relation}|{dst}"
    g = _place_token(g, tok, tok, copies=copies, radius=4)
    for cid in (src, dst):
        if cid.startswith(("math.", "lang.")):
            g = _place_token(g, f"C:{cid}", f"C:{cid}", copies=max(2, copies // 2), radius=3)
    lat["cells"] = g.cells
    return True


def mint_episode_links(
    lattices: dict[str, dict],
    *,
    lattice_id: str,
    links: list[dict[str, Any]],
    copies: int = 4,
) -> list[dict[str, str]]:
    """Sleep Extract: teacher/agent derived edges (names, prepares, example, …).

    Batched: copies the grid ONCE and places every edge on it, instead of calling
    strengthen_graph_edge per link (which deep-copies the whole grid each time —
    O(links x grid) = quadratic when minting a large glossary). Equivalent result.
    """
    if lattice_id not in lattices:
        return []
    lat = lattices[lattice_id]
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=[list(x) for x in lat["cells"]])
    minted: list[dict[str, str]] = []
    for raw in links or []:
        src = str(raw.get("src") or "")
        rel = str(raw.get("relation") or raw.get("rel") or "")
        dst = str(raw.get("dst") or "")
        if not (src and rel and dst):
            continue
        tok = f"E:{src}|{rel}|{dst}"
        _place_token(g, tok, tok, copies=copies, radius=4)
        for cid in (src, dst):
            if cid.startswith(("math.", "lang.")):
                _place_token(g, f"C:{cid}", f"C:{cid}", copies=max(2, copies // 2), radius=3)
        minted.append({"src": src, "relation": rel, "dst": dst, "edge": tok})
    lat["cells"] = g.cells
    return minted


def mint_operator_denotes_from_episode(
    lattices: dict[str, dict],
    *,
    lattice_id: str,
    cue: str,
    concept_id: str,
    bundle: dict | None = None,
    copies: int = 4,
) -> dict[str, Any] | None:
    """Sleep Extract: teacher math.op.* → contextual denotes for the operator glyph."""
    cid = str(concept_id or "")
    if not cid.startswith("math.op."):
        return None
    if lattice_id not in lattices:
        return None
    decoded = decode_f0_lattice(lattices[lattice_id], min_votes=1)
    from casa.prisms.memory.f0_field_reading import reading_model_for_predict

    model = reading_model_for_predict(decoded, bundle)
    glyph = _MATH_OP_GLYPH.get(cid)
    if not glyph:
        return None
    unbound = unbound_operators(
        cue,
        model,
        decoded,
        concept_in_context=concept_in_context,
        grapheme_for_glyph=_grapheme_for_glyph,
    )
    target = next((u for u in unbound if u.get("op") == glyph), None)
    if target is None:
        analysis = analyze_cue(cue)
        if glyph not in {str(ix.get("op") or "") for ix in analysis.get("infix") or []}:
            return None
        context = "math.ctx.arithmetic"
        grapheme = _grapheme_for_glyph(glyph) or glyph
    else:
        context = str(target.get("context") or "math.ctx.arithmetic")
        grapheme = str(target.get("grapheme") or _grapheme_for_glyph(glyph) or glyph)
    sym = grapheme if grapheme.startswith(_SYMBOL_PREFIXES) else grapheme
    if concept_in_context(decoded, sym, context) == cid:
        return {"skipped": True, "concept_id": cid, "glyph": glyph, "context": context}
    ok = strengthen_denotes_edge(lattices, lattice_id, sym, context, cid, copies=copies)
    if not ok:
        return None
    return {
        "concept_id": cid,
        "glyph": glyph,
        "grapheme": sym,
        "context": context,
        "edge": f"E:{contextual_symbol_key(sym, context)}|denotes|{cid}",
    }


def numeral_glyph_from_episode_cue(cue: str) -> str | None:
    """Left-hand glyph for mapping episodes (I = 1, 4, IV = 4) — not infix equations."""
    if analyze_cue(cue).get("infix"):
        return None
    raw = cue.strip()
    if not raw:
        return None
    if "=" in raw:
        raw = raw.split("=", 1)[0].strip()
    token = raw.split()[0] if raw.split() else raw
    return token.strip() or None


def mint_numeral_denotes_from_episode(
    lattices: dict[str, dict],
    *,
    lattice_id: str,
    cue: str,
    concept_id: str,
    copies: int = 4,
    context_id: str = "math.ctx.arithmetic",
) -> dict[str, Any] | None:
    """Sleep Extract: teacher math.num.* → E:glyph@ctx|denotes (digit glyph 0–9 or numeral/roman form)."""
    cid = str(concept_id or "")
    if not cid.startswith("math.num."):
        return None
    if lattice_id not in lattices:
        return None
    glyph = numeral_glyph_from_episode_cue(cue)
    if not glyph:
        return None
    decoded = decode_f0_lattice(lattices[lattice_id], min_votes=1)
    if len(glyph) == 1 and glyph.isdigit():
        grapheme = _grapheme_for_glyph(glyph) or glyph
        sym = grapheme if grapheme.startswith(_SYMBOL_PREFIXES) else grapheme
    elif glyph.isdigit():
        sym = glyph
    else:
        sym = glyph.upper()
    if concept_in_context(decoded, sym, context_id) == cid:
        return {"skipped": True, "concept_id": cid, "glyph": glyph, "context": context_id}
    ok = strengthen_denotes_edge(lattices, lattice_id, sym, context_id, cid, copies=copies)
    if not ok:
        return None
    return {
        "concept_id": cid,
        "glyph": glyph,
        "grapheme": sym,
        "context": context_id,
        "edge": f"E:{contextual_symbol_key(sym, context_id)}|denotes|{cid}",
    }


def glyph_to_concept(bundle: dict) -> dict[str, str]:
    """Legacy flat map — cardinal pipe runs only."""
    out: dict[str, str] = {}
    for s in bundle.get("symbol_senses") or []:
        if str(s.get("context") or s.get("context_id")) != "math.ctx.cardinal":
            continue
        glyph = str(s.get("glyph") or "")
        cid = str(s.get("concept_id") or "")
        if glyph and cid:
            out[glyph] = cid
    for g in bundle.get("math_glyphs") or []:
        glyph = str(g.get("glyph") or "")
        cid = str(g.get("concept_id") or "")
        if glyph and cid and glyph not in out:
            out[glyph] = cid
    return out
