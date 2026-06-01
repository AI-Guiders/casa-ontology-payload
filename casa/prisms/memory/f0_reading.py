#!/usr/bin/env python3
"""F0 cue analysis + reading-frame matching (glyph sense = symbol × context)."""

from __future__ import annotations

import re
from typing import Any

# Operand: quoted string, pipe run, identifier, number
_OPERAND = r'(?:"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'|\|+|[\w\u0400-\u04ff]+|\d+(?:\.\d+)?)'
_INFIX_RE = re.compile(rf"({_OPERAND})\s*([+|=\-&])\s*({_OPERAND})")
_PIPE_ONLY = re.compile(r"^[\| ]+$")

# Legacy string tags → structured when (bundle may use either)
_LEGACY_WHEN: dict[str, dict[str, Any]] = {
    "pipes_only": {"shape": "glyph_run", "glyph_class": "pipe"},
    "binary_infix": {"shape": "infix", "op": "|", "operand": "identifier"},
    "string_concat": {"shape": "infix", "op": "+", "operand": "string_literal"},
    "arithmetic": {"shape": "default"},
}


def classify_operand(text: str) -> str:
    t = text.strip()
    if not t:
        return "empty"
    if t[0] in "\"'":
        return "string_literal"
    if _PIPE_ONLY.match(t.replace(" ", "")) and "|" in t:
        return "pipe_run"
    if re.fullmatch(r"\d+(?:\.\d+)?", t):
        return "number"
    if re.fullmatch(r"[\w\u0400-\u04ff]+", t):
        return "identifier"
    return "other"


def _filter_spurious_infix(infix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop pipe-bitwise false positives inside stick equations (||| parsed as | | |)."""
    has_arith = any(
        ix.get("op") in "+-=" and "pipe_run" in (ix.get("left_kind"), ix.get("right_kind"))
        for ix in infix
    )
    out: list[dict[str, Any]] = []
    for ix in infix:
        op = str(ix.get("op") or "")
        left = str(ix.get("left") or "")
        right = str(ix.get("right") or "")
        if op == "|" and left == "|" and right == "|":
            continue
        if has_arith and op == "|" and ix.get("left_kind") == "pipe_run" and ix.get("right_kind") == "pipe_run":
            continue
        out.append(ix)
    return out


def analyze_cue(cue: str) -> dict[str, Any]:
    """Surface syntax of cue — operand kinds, infix ops, glyph runs (not semantics)."""
    cue = cue.strip()
    has: set[str] = set(cue)
    infix: list[dict[str, Any]] = []
    for m in _INFIX_RE.finditer(cue):
        left, op, right = m.group(1), m.group(2), m.group(3)
        infix.append(
            {
                "op": op,
                "left": left,
                "right": right,
                "left_kind": classify_operand(left),
                "right_kind": classify_operand(right),
            }
        )
    infix = _filter_spurious_infix(infix)

    glyph_run: dict[str, Any] | None = None
    compact = cue.replace(" ", "")
    if _PIPE_ONLY.match(cue) and "|" in compact:
        glyph_run = {"glyph_class": "pipe", "text": compact}

    singleton = cue if len(cue) == 1 else None
    number_literal: str | None = None
    if re.fullmatch(r"\d+", compact):
        number_literal = compact
    return {
        "cue": cue,
        "has": has,
        "infix": infix,
        "glyph_run": glyph_run,
        "singleton": singleton,
        "number_literal": number_literal,
    }


def _normalize_when(when: Any) -> dict[str, Any]:
    if isinstance(when, dict):
        return dict(when)
    if isinstance(when, str):
        return dict(_LEGACY_WHEN.get(when, {"shape": when}))
    return {}


def _operand_matches(kind: str, rule: str) -> bool:
    if rule == "identifier":
        return kind in ("identifier", "number")
    return kind == rule


def _match_when(analysis: dict[str, Any], when: dict[str, Any]) -> bool:
    shape = str(when.get("shape") or "")

    if shape == "default":
        return True

    if shape == "glyph_run":
        gr = analysis.get("glyph_run")
        if not gr:
            return False
        return str(when.get("glyph_class") or "pipe") == gr.get("glyph_class")

    if shape == "singleton":
        return analysis.get("singleton") == str(when.get("glyph") or "")

    if shape == "contains":
        return str(when.get("glyph") or "") in analysis.get("has") or set()

    if shape == "infix":
        op = str(when.get("op") or "")
        operand = when.get("operand")
        exclude = when.get("exclude_operand")
        for ix in analysis.get("infix") or []:
            if ix.get("op") != op:
                continue
            for side in ("left_kind", "right_kind"):
                kind = str(ix.get(side) or "")
                if operand and not _operand_matches(kind, str(operand)):
                    continue
                if exclude and _operand_matches(kind, str(exclude)):
                    continue
                return True
        return False

    return False


def _when_rules_for_context(bundle: dict, context_id: str) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for ctx in bundle.get("reading_contexts") or []:
        if str(ctx.get("id") or "") != context_id:
            continue
        rules.append(_normalize_when(ctx.get("when")))
    return rules


def _active_when_rules(bundle: dict, context_id: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
    return [w for w in _when_rules_for_context(bundle, context_id) if _match_when(analysis, w)]


def _glyph_relevant(analysis: dict[str, Any], glyph: str, when: dict[str, Any]) -> bool:
    shape = str(when.get("shape") or "")
    if shape == "glyph_run":
        return glyph in str((analysis.get("glyph_run") or {}).get("text") or "")
    if shape == "infix":
        return glyph == str(when.get("op") or "")
    if shape == "singleton":
        return analysis.get("singleton") == glyph
    if shape in ("contains", "default"):
        return glyph in analysis.get("has") or set()
    return glyph in analysis.get("has") or set()


def _sense_applies(analysis: dict[str, Any], glyph: str, when_rules: list[dict[str, Any]]) -> bool:
    return any(_glyph_relevant(analysis, glyph, w) for w in when_rules if _match_when(analysis, w))


def _infix_matches_context_when(ix: dict[str, Any], when: dict[str, Any]) -> bool:
    if str(when.get("shape") or "") != "infix":
        return False
    if str(when.get("op") or "") != str(ix.get("op") or ""):
        return False
    operand = when.get("operand")
    exclude = when.get("exclude_operand")
    for side in ("left_kind", "right_kind"):
        kind = str(ix.get(side) or "")
        if operand and not _operand_matches(kind, str(operand)):
            continue
        if exclude and _operand_matches(kind, str(exclude)):
            continue
        return True
    return False


def _contexts_for_infix(ix: dict[str, Any], bundle: dict) -> list[str]:
    out: list[str] = []
    for ctx in bundle.get("reading_contexts") or []:
        cid = str(ctx.get("id") or "")
        if not cid:
            continue
        when = _normalize_when(ctx.get("when"))
        if _infix_matches_context_when(ix, when):
            out.append(cid)
    return out


def infix_reading_contexts(ix: dict[str, Any], bundle: dict) -> list[str]:
    """Bundle-matched frames first, then surface fallbacks (pipe / number → arithmetic)."""
    ctxs = _contexts_for_infix(ix, bundle)
    if ctxs:
        return ctxs
    kinds = (ix.get("left_kind"), ix.get("right_kind"))
    fb: list[str] = []
    if "pipe_run" in kinds:
        fb.append("math.ctx.arithmetic")
    if "number" in kinds:
        fb.append("math.ctx.arithmetic")
    return fb


def field_bound_infix_operators(
    decoded: dict,
    op: str,
    *,
    grapheme_for_glyph: Any,
) -> list[tuple[str, str]]:
    """math.op.* bound on field for infix glyph in any reading context (Extract / sleep)."""
    grapheme = grapheme_for_glyph(op) if grapheme_for_glyph else None
    sym = grapheme if grapheme and str(grapheme).startswith(("grapheme.", "punct.", "vk.")) else op
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for edge in decoded.get("edges") or []:
        es = str(edge)
        if "|denotes|" not in es:
            continue
        src, _, dst = es.partition("|denotes|")
        if not dst.startswith("math.op."):
            continue
        if "@" in src:
            sym_part, ctx = src.rsplit("@", 1)
        else:
            sym_part, ctx = src, "math.ctx.arithmetic"
        if sym_part not in (sym, op):
            continue
        key = (dst, ctx)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _glyph_lookup_keys(glyph: str, *, grapheme_for_glyph: Any) -> list[str]:
    g = glyph.strip()
    keys = [g]
    if len(g) == 1:
        grapheme = grapheme_for_glyph(g) if grapheme_for_glyph else None
        if grapheme and grapheme not in keys:
            keys.append(grapheme)
    return keys


def score_field_glyph_numerals(
    cue: str,
    decoded: dict,
    contexts: dict[str, float],
    *,
    grapheme_for_glyph: Any,
) -> dict[str, int]:
    """Boost math.num.* from sleep-minted E:glyph@ctx|denotes (teacher mapping episodes)."""
    analysis = analyze_cue(cue)
    if analysis.get("infix"):
        return {}
    raw = str(analysis.get("cue") or cue).strip()
    if "=" in raw:
        raw = raw.split("=", 1)[0].strip()
    glyph = raw.replace(" ", "")
    if not glyph:
        return {}
    scores: dict[str, int] = {}
    keys = _glyph_lookup_keys(glyph, grapheme_for_glyph=grapheme_for_glyph)
    for edge in decoded.get("edges") or []:
        es = str(edge)
        if "|denotes|" not in es:
            continue
        src, _, dst = es.partition("|denotes|")
        if not dst.startswith("math.num."):
            continue
        if "@" in src:
            sym_part, ctx = src.rsplit("@", 1)
        else:
            sym_part, ctx = src, "math.ctx.arithmetic"
        if sym_part not in keys:
            continue
        weight = max(float(contexts.get(ctx, 0)), 10.0)
        scores[dst] = scores.get(dst, 0) + int(weight * 1.4)
    return scores


def _sense_binds_op(
    op: str,
    context_id: str,
    bundle: dict,
    decoded: dict,
    *,
    concept_in_context: Any,
    grapheme_for_glyph: Any,
) -> bool:
    for sense in bundle.get("symbol_senses") or []:
        if str(sense.get("glyph") or "") != op:
            continue
        ctx = str(sense.get("context") or sense.get("context_id") or "")
        if ctx != context_id:
            continue
        if str(sense.get("concept_id") or "").startswith("math."):
            return True
    grapheme = grapheme_for_glyph(op) if grapheme_for_glyph else None
    sym = grapheme if grapheme and str(grapheme).startswith(("grapheme.", "punct.", "vk.")) else op
    return bool(concept_in_context(decoded, sym, context_id))


def unbound_operators(
    cue: str,
    bundle: dict,
    decoded: dict,
    *,
    concept_in_context: Any,
    grapheme_for_glyph: Any,
) -> list[dict[str, Any]]:
    """Infix operators in an active reading frame with no field/bundle denotes binding."""
    analysis = analyze_cue(cue)
    bundle = bundle or {}
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for ix in analysis.get("infix") or []:
        op = str(ix.get("op") or "")
        if op not in "+-=&":
            continue
        if op == "|":
            continue
        contexts = infix_reading_contexts(ix, bundle)
        if not contexts and op in "+-=&":
            contexts = ["math.ctx.arithmetic"]
        field_bound = {ctx for _, ctx in field_bound_infix_operators(decoded, op, grapheme_for_glyph=grapheme_for_glyph)}
        for ctx in contexts:
            key = (op, ctx)
            if key in seen:
                continue
            seen.add(key)
            if ctx in field_bound:
                continue
            if _sense_binds_op(op, ctx, bundle, decoded, concept_in_context=concept_in_context, grapheme_for_glyph=grapheme_for_glyph):
                continue
            grapheme = grapheme_for_glyph(op) if grapheme_for_glyph else None
            out.append(
                {
                    "op": op,
                    "context": ctx,
                    "grapheme": grapheme or op,
                    "left_kind": ix.get("left_kind"),
                    "right_kind": ix.get("right_kind"),
                }
            )
    return out


def score_field_infix_operators(
    cue: str,
    bundle: dict,
    decoded: dict,
    contexts: dict[str, float],
    *,
    concept_in_context: Any,
    grapheme_for_glyph: Any,
) -> dict[str, int]:
    """Boost math.op.* from E:denotes on field for infix operator glyphs in cue."""
    scores: dict[str, int] = {}
    for ix in analyze_cue(cue).get("infix") or []:
        op = str(ix.get("op") or "")
        if len(op) != 1 or op == "|":
            continue
        field_hits = field_bound_infix_operators(decoded, op, grapheme_for_glyph=grapheme_for_glyph)
        if field_hits:
            for concept_id, ctx in field_hits:
                weight = max(float(contexts.get(ctx, 0)), 10.0)
                scores[concept_id] = scores.get(concept_id, 0) + int(weight * 1.5)
            continue
        ctxs = infix_reading_contexts(ix, bundle)
        for ctx in ctxs:
            weight = max(float(contexts.get(ctx, 0)), 10.0)
            grapheme = grapheme_for_glyph(op) if grapheme_for_glyph else None
            sym = grapheme if grapheme and str(grapheme).startswith(("grapheme.", "punct.", "vk.")) else op
            bound = concept_in_context(decoded, sym, ctx)
            if bound:
                scores[str(bound)] = scores.get(str(bound), 0) + int(weight * 1.5)
    return scores


def detect_reading_contexts(
    cue: str,
    *,
    bundle: dict | None = None,
    unbound: list[dict[str, Any]] | None = None,
) -> dict[str, float]:
    """Score reading frames from bundle rules (specific beats default)."""
    analysis = analyze_cue(cue)
    unbound_ops = {str(u.get("op") or "") for u in (unbound or [])}
    has_infix = bool(analysis.get("infix"))
    scores: dict[str, float] = {}
    for ctx in bundle.get("reading_contexts") or [] if bundle else []:
        cid = str(ctx.get("id") or "")
        if not cid:
            continue
        when = _normalize_when(ctx.get("when"))
        if str(when.get("shape") or "") == "contains" and has_infix:
            glyph = str(when.get("glyph") or "")
            if glyph == "=" and any(str(ix.get("op") or "") in "+-" for ix in analysis.get("infix") or []):
                continue
            if glyph in "+-=" and any(str(ix.get("op") or "") == glyph for ix in analysis.get("infix") or []):
                continue
        if str(when.get("shape") or "") == "contains" and has_infix and unbound_ops:
            continue
        if not _match_when(analysis, when):
            continue
        weight = float(ctx.get("weight") or 10)
        scores[cid] = max(scores.get(cid, 0), weight)

    if analysis.get("number_literal"):
        scores["math.ctx.arithmetic"] = max(scores.get("math.ctx.arithmetic", 0), 11.0)

    if not scores:
        scores["math.ctx.arithmetic"] = 1.0
    return scores


def _score_glyph_runs(cue: str, senses: list[dict], context_id: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    by_glyph = {
        str(s["glyph"]): str(s["concept_id"])
        for s in senses
        if str(s.get("context") or s.get("context_id") or "") == context_id
    }
    if not by_glyph:
        return scores
    rest = cue.replace(" ", "")
    for glyph in sorted(by_glyph.keys(), key=len, reverse=True):
        while glyph in rest:
            cid = by_glyph[glyph]
            scores[cid] = scores.get(cid, 0) + 4
            rest = rest.replace(glyph, "", 1)
    return scores


def score_contextual_senses(
    bundle: dict,
    decoded: dict,
    cue: str,
    contexts: dict[str, float],
    *,
    concept_in_context: Any,
    grapheme_for_glyph: Any,
    unbound: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    """Map active frames + symbol_senses → concept scores (field-backed)."""
    analysis = analyze_cue(cue)
    scores: dict[str, int] = {}
    senses = bundle.get("symbol_senses") or []
    unbound_ops = {str(u.get("op") or "") for u in (unbound or [])}
    has_infix = bool(analysis.get("infix"))
    has_arith_infix = any(str(ix.get("op") or "") in "+-" for ix in analysis.get("infix") or [])

    for sense in senses:
        glyph = str(sense.get("glyph") or "")
        context = str(sense.get("context") or sense.get("context_id") or "")
        concept = str(sense.get("concept_id") or "")
        ctx_weight = contexts.get(context, 0)
        if ctx_weight <= 0 or not (glyph and concept):
            continue

        sense_when = _normalize_when(sense.get("when"))
        if sense_when:
            rules = [sense_when] if _match_when(analysis, sense_when) else []
        else:
            rules = _active_when_rules(bundle, context, analysis)
        if not rules or not _sense_applies(analysis, glyph, rules):
            continue
        if unbound_ops and any(str(w.get("shape") or "") == "contains" for w in rules):
            continue
        if has_arith_infix and glyph == "=" and any(str(w.get("shape") or "") == "contains" for w in rules):
            continue
        if glyph in unbound_ops:
            continue

        run_rule = next((w for w in rules if str(w.get("shape") or "") == "glyph_run"), None)
        if run_rule:
            for cid, pts in _score_glyph_runs(cue, senses, context).items():
                if cid == concept:
                    scores[cid] = scores.get(cid, 0) + int(pts * ctx_weight / 10)
            continue

        grapheme = str(sense.get("grapheme") or "") or (grapheme_for_glyph(glyph) or "")
        sym = grapheme if grapheme.startswith(("grapheme.", "punct.", "vk.")) else glyph
        field = concept_in_context(decoded, sym, context)
        if field:
            scores[field] = scores.get(field, 0) + int(ctx_weight * 1.2)

    return scores
