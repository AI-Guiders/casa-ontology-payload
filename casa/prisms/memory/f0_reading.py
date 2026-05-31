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

    glyph_run: dict[str, Any] | None = None
    compact = cue.replace(" ", "")
    if _PIPE_ONLY.match(cue) and "|" in compact:
        glyph_run = {"glyph_class": "pipe", "text": compact}

    singleton = cue if len(cue) == 1 else None
    return {
        "cue": cue,
        "has": has,
        "infix": infix,
        "glyph_run": glyph_run,
        "singleton": singleton,
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


def detect_reading_contexts(cue: str, *, bundle: dict | None = None) -> dict[str, float]:
    """Score reading frames from bundle rules (specific beats default)."""
    analysis = analyze_cue(cue)
    scores: dict[str, float] = {}
    for ctx in bundle.get("reading_contexts") or [] if bundle else []:
        cid = str(ctx.get("id") or "")
        if not cid:
            continue
        when = _normalize_when(ctx.get("when"))
        if not _match_when(analysis, when):
            continue
        weight = float(ctx.get("weight") or 10)
        scores[cid] = max(scores.get(cid, 0), weight)

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
) -> dict[str, int]:
    """Map active frames + symbol_senses → concept scores (field-backed)."""
    analysis = analyze_cue(cue)
    scores: dict[str, int] = {}
    senses = bundle.get("symbol_senses") or []

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
