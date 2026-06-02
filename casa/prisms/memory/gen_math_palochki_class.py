#!/usr/bin/env python3
"""Generate math-palochki class bundle + lesson manifest for agent ingest."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

BASE_BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
CLASS_DIR = REPO_ROOT / "lessons/math-palochki"


def _extend_bundle(base: dict) -> dict:
    b = deepcopy(base)
    b["bundle_id"] = "kb-math-palochki-v1"
    b["title"] = "Class math-palochki — sticks, operands, + − × ÷"
    b["doc"] = "lessons/math-palochki/README.md"
    b["schema_version"] = max(int(base.get("schema_version") or 1), 5)

    extra_tokens = [
        {"token": "M:op:sub", "copies": 5},
        {"token": "M:op:mul", "copies": 5},
        {"token": "M:op:div", "copies": 5},
    ]
    seen = {t["token"] for t in b.get("math_tokens") or []}
    for item in extra_tokens:
        if item["token"] not in seen:
            b.setdefault("math_tokens", []).append(item)

    role_claims = [
        ("math.role.addend", "Operand role: addend (слагаемое)."),
        ("math.role.sum", "Operand role: sum (сумма)."),
        ("math.role.minuend", "Operand role: minuend (уменьшаемое)."),
        ("math.role.subtrahend", "Operand role: subtrahend (вычитаемое)."),
        ("math.role.difference", "Operand role: difference (разность)."),
        ("math.role.factor", "Operand role: factor (множитель)."),
        ("math.role.product", "Operand role: product (произведение)."),
        ("math.role.dividend", "Operand role: dividend (делимое)."),
        ("math.role.divisor", "Operand role: divisor (делитель)."),
        ("math.role.quotient", "Operand role: quotient (частное)."),
        ("math.role.heap", "Counting role: heap / pile (кучка)."),
        ("math.op.sub", "Subtraction operator schema (glyph −)."),
        ("math.op.div", "Division operator schema (glyph /)."),
    ]
    existing = {c["concept_id"] for c in b.get("claims") or []}
    for cid, text in role_claims:
        if cid not in existing:
            b.setdefault("claims", []).append({"concept_id": cid, "text": text})

    ru_words = [
        ("lang.word.слагаемое", "math.role.addend"),
        ("lang.word.сумма", "math.role.sum"),
        ("lang.word.уменьшаемое", "math.role.minuend"),
        ("lang.word.вычитаемое", "math.role.subtrahend"),
        ("lang.word.разность", "math.role.difference"),
        ("lang.word.множитель", "math.role.factor"),
        ("lang.word.произведение", "math.role.product"),
        ("lang.word.делимое", "math.role.dividend"),
        ("lang.word.делитель", "math.role.divisor"),
        ("lang.word.частное", "math.role.quotient"),
        ("lang.word.кучка", "math.role.heap"),
        ("lang.word.палочка", "math.entity.stick"),
    ]
    for word, role in ru_words:
        cid = word
        if cid not in existing:
            b.setdefault("claims", []).append({"concept_id": cid, "text": f"RU word → {role}"})
            existing.add(cid)

    edges = list((b.get("graph") or {}).get("edges") or [])
    edge_keys = {(e["src"], e["relation"], e["dst"]) for e in edges}
    for item in extra_tokens:
        tok = item["token"]
        op = tok.replace("M:op:", "math.op.")
        key = (tok, "schema_of", op)
        if key not in edge_keys:
            edges.append({"src": tok, "relation": "schema_of", "dst": op})
            edge_keys.add(key)
    for word, role in ru_words:
        key = (role, "denotes", word)
        if key not in edge_keys:
            edges.append({"src": role, "relation": "denotes", "dst": word})
            edge_keys.add(key)
    b.setdefault("graph", {})["edges"] = edges

    senses = list(b.get("symbol_senses") or [])
    sense_keys = {(s.get("glyph"), s.get("context"), s.get("concept_id")) for s in senses}
    for glyph, grapheme, ctx, concept in (
        ("-", "grapheme.latn.-", "math.ctx.arithmetic", "math.op.sub"),
        ("/", "grapheme.latn./", "math.ctx.arithmetic", "math.op.div"),
        ("×", "grapheme.latn.×", "math.ctx.arithmetic", "math.op.mul"),
        ("*", "grapheme.latn.*", "math.ctx.arithmetic", "math.op.mul"),
    ):
        key = (glyph, ctx, concept)
        if key not in sense_keys:
            senses.append(
                {
                    "glyph": glyph,
                    "grapheme": grapheme,
                    "context": ctx,
                    "concept_id": concept,
                }
            )
            sense_keys.add(key)
    b["symbol_senses"] = senses

    glyphs = list(b.get("math_glyphs") or [])
    glyph_keys = {(g.get("glyph"), g.get("concept_id")) for g in glyphs}
    for glyph, concept in (
        ("-", "math.op.sub"),
        ("/", "math.op.div"),
        ("×", "math.op.mul"),
    ):
        if (glyph, concept) not in glyph_keys:
            glyphs.append({"glyph": glyph, "concept_id": concept, "context": "math.ctx.arithmetic"})
    b["math_glyphs"] = glyphs

    kw = dict(b.get("math_keywords") or {})
    kw.update(
        {
            "math.op.sub": ["sub", "вычесть", "отрезать", "minus", "−"],
            "math.op.div": ["div", "делить", "разделить", "÷", "/"],
            "math.op.mul": ["mul", "умнож", "×", "times"],
            "math.role.dividend": ["делимое"],
            "math.role.divisor": ["делитель"],
            "math.role.quotient": ["частное"],
            "math.role.addend": ["слагаемое"],
            "math.role.sum": ["сумма"],
        }
    )
    b["math_keywords"] = kw

    contexts = list(b.get("reading_contexts") or [])
    contexts.extend(
        [
            {
                "id": "math.ctx.arithmetic",
                "when": {"shape": "infix", "op": "-", "operand": "pipe_run"},
                "weight": 10,
                "text": "Stick subtraction ||| - ||.",
            },
            {
                "id": "math.ctx.arithmetic",
                "when": {"shape": "infix", "op": "/", "operand": "pipe_run"},
                "weight": 10,
                "text": "Stick division |||| / 2.",
            },
            {
                "id": "math.ctx.arithmetic",
                "when": {"shape": "singleton", "glyph": "-"},
                "weight": 10,
            },
            {
                "id": "math.ctx.arithmetic",
                "when": {"shape": "singleton", "glyph": "/"},
                "weight": 10,
            },
        ]
    )
    b["reading_contexts"] = contexts
    b.setdefault("symbol_concepts", [])
    for g in ("grapheme.latn.-", "grapheme.latn./", "grapheme.latn.×", "grapheme.latn.*"):
        if g not in b["symbol_concepts"]:
            b["symbol_concepts"].append(g)
    _add_counting_zero_and_digits(b)
    _add_paren_groups(b)
    _add_paren_precedence(b)
    _add_fraction_heaps(b)
    _add_arithmetic_properties(b)
    return b


def _add_arithmetic_properties(b: dict) -> None:
    """Property schemas — agent extracts from co-presented lesson scenes (sleep), not runtime oracle."""
    claims = list(b.get("claims") or [])
    existing = {c["concept_id"] for c in claims}
    prop_claims = [
        ("math.prop.commutative_add", "Addition: reordering addends yields the same heap."),
        ("math.prop.commutative_mul", "Multiplication: reordering factors yields the same product."),
        ("math.prop.associative_add", "Addition: grouping of addends does not change the sum."),
        ("math.prop.associative_mul", "Multiplication: grouping of factors does not change the product."),
        ("math.prop.distributive_mul_over_add", "Multiplication distributes over addition on heaps."),
        ("math.prop.identity_add_zero", "Adding zero leaves the heap unchanged."),
        ("math.prop.identity_mul_one", "Multiplying by one leaves the heap unchanged."),
        ("math.prop.division_inverse_mul", "Division and multiplication are inverse questions on same heaps."),
    ]
    for cid, text in prop_claims:
        if cid not in existing:
            claims.append({"concept_id": cid, "text": text})
            existing.add(cid)
    b["claims"] = claims

    edges = list((b.get("graph") or {}).get("edges") or [])
    edge_keys = {(e["src"], e["relation"], e["dst"]) for e in edges}
    applies = [
        ("math.prop.commutative_add", "math.op.add"),
        ("math.prop.commutative_mul", "math.op.mul"),
        ("math.prop.associative_add", "math.op.add"),
        ("math.prop.associative_mul", "math.op.mul"),
        ("math.prop.distributive_mul_over_add", "math.op.mul"),
        ("math.prop.identity_add_zero", "math.op.add"),
        ("math.prop.identity_mul_one", "math.op.mul"),
        ("math.prop.division_inverse_mul", "math.op.div"),
        ("math.prop.division_inverse_mul", "math.op.mul"),
    ]
    for src, dst in applies:
        key = (src, "applies_to", dst)
        if key not in edge_keys:
            edges.append({"src": src, "relation": "applies_to", "dst": dst})
            edge_keys.add(key)
    b.setdefault("graph", {})["edges"] = edges

    kw = dict(b.get("math_keywords") or {})
    kw.update(
        {
            "math.prop.commutative_add": ["коммутатив", "перестановка", "от перестановки"],
            "math.prop.commutative_mul": ["коммутатив", "перестановка множителей"],
            "math.prop.identity_add_zero": ["ноль", "нейтральный", "+0", "пустая группа"],
            "math.prop.identity_mul_one": ["единица", "×1", "один раз"],
            "math.prop.division_inverse_mul": ["обратное", "деление и умножение"],
        }
    )
    b["math_keywords"] = kw


def _add_paren_groups(b: dict) -> None:
    """Parenthesized stick heaps: () = 0, (|) = 1, (IIIII) = 5, math.ctx.group."""
    claims = list(b.get("claims") or [])
    existing = {c["concept_id"] for c in claims}
    for cid, text in (
        ("math.entity.group", "Grouping delimiter: parentheses around a heap (кучка в скобках)."),
        ("math.ctx.group", "Reading: (|) (||) () as grouped stick cardinality."),
    ):
        if cid not in existing:
            claims.append({"concept_id": cid, "text": text})
            existing.add(cid)
    b["claims"] = claims

    senses = list(b.get("symbol_senses") or [])
    sense_keys = {(s.get("glyph"), s.get("context"), s.get("concept_id")) for s in senses}
    ctx = "math.ctx.group"
    for glyph, concept in (
        ("()", "math.num.zero"),
        ("(|)", "math.num.one"),
        ("(||)", "math.num.two"),
        ("(|||)", "math.num.three"),
        ("(||||)", "math.num.four"),
        ("(I)", "math.num.one"),
        ("(II)", "math.num.two"),
        ("(III)", "math.num.three"),
        ("(IIII)", "math.num.four"),
        ("(IIIII)", "math.num.five"),
    ):
        key = (glyph, ctx, concept)
        if key in sense_keys:
            continue
        row: dict[str, Any] = {"glyph": glyph, "context": ctx, "concept_id": concept}
        if glyph in ("()", "(|)", "(||)", "(|||)", "(||||)"):
            row["when"] = {"shape": "group", "inner": "empty" if glyph == "()" else "pipe_run"}
        else:
            row["when"] = {"shape": "group", "inner": "i_run"}
        senses.append(row)
        sense_keys.add(key)
    b["symbol_senses"] = senses

    glyphs = list(b.get("math_glyphs") or [])
    glyph_keys = {(g.get("glyph"), g.get("concept_id")) for g in glyphs}
    for glyph, concept in (
        ("()", "math.num.zero"),
        ("(|)", "math.num.one"),
        ("(||)", "math.num.two"),
        ("(III)", "math.num.three"),
        ("(IIIII)", "math.num.five"),
    ):
        if (glyph, concept) not in glyph_keys:
            glyphs.append({"glyph": glyph, "concept_id": concept, "context": ctx})
    b["math_glyphs"] = glyphs

    kw = dict(b.get("math_keywords") or {})
    kw.setdefault("math.entity.group", [])
    for word in ("группа", "скобки", "кучка в скобках", "пустая группа"):
        if word not in kw["math.entity.group"]:
            kw["math.entity.group"].append(word)
    kw.setdefault("math.num.zero", [])
    for word in ("()", "пустая группа", "пустые скобки"):
        if word not in kw["math.num.zero"]:
            kw["math.num.zero"].append(word)
    b["math_keywords"] = kw

    contexts = list(b.get("reading_contexts") or [])
    contexts.extend(
        [
            {
                "id": "math.ctx.group",
                "when": {"shape": "group"},
                "weight": 12,
                "text": "Parenthesized stick heap: (|) (||) ().",
            },
            {
                "id": "math.ctx.group",
                "when": {"shape": "group", "inner": "empty"},
                "weight": 14,
                "text": "Empty group () counts as zero.",
            },
            {
                "id": "math.ctx.arithmetic",
                "when": {"shape": "infix", "op": "+", "operand": "pipe_group"},
                "weight": 11,
                "text": "Add grouped heaps: (||) + (||).",
            },
            {
                "id": "math.ctx.arithmetic",
                "when": {"shape": "infix", "op": "-", "operand": "pipe_group"},
                "weight": 11,
                "text": "Subtract grouped heaps: (|||) - (||).",
            },
        ]
    )
    b["reading_contexts"] = contexts

    sym = list(b.setdefault("symbol_concepts", []))
    for g in ("grapheme.latn.(", "grapheme.latn.)", "grapheme.latn.I"):
        if g not in sym:
            sym.append(g)
    b["symbol_concepts"] = sym


def _add_paren_precedence(b: dict) -> None:
    """Parentheses as precedence control in arithmetic expressions.

    Separate from `math.ctx.group` where `()` is an empty heap (zero).
    Here parentheses mean "compute inside first", e.g. (4 - 7) + 5.
    """
    claims = list(b.get("claims") or [])
    existing = {c["concept_id"] for c in claims}
    for cid, text in (
        ("math.entity.parens", "Parentheses as delimiters in expressions (скобки)."),
        ("math.ctx.precedence", "Reading: parentheses set priority of operations."),
    ):
        if cid not in existing:
            claims.append({"concept_id": cid, "text": text})
            existing.add(cid)
    b["claims"] = claims

    kw = dict(b.get("math_keywords") or {})
    kw.setdefault("math.entity.parens", [])
    for w in ("скобки", "(", ")", "приоритет", "сначала в скобках"):
        if w not in kw["math.entity.parens"]:
            kw["math.entity.parens"].append(w)
    b["math_keywords"] = kw

    contexts = list(b.get("reading_contexts") or [])
    contexts.extend(
        [
            {
                "id": "math.ctx.precedence",
                "when": {"shape": "singleton", "glyph": "("},
                "weight": 6,
                "text": "Parentheses can change priority of operations.",
            },
            {
                "id": "math.ctx.precedence",
                "when": {"shape": "text", "contains": "(4 - 7) + 5"},
                "weight": 9,
                "text": "Parentheses change priority: (4 - 7) + 5.",
            },
        ]
    )
    b["reading_contexts"] = contexts


# Дробь на кучках: числитель = сколько кучек взяли, знаменатель = на сколько кучек делили.
FRAC_HALF_VIS = "(||) ||"
FRAC_TWO_THIRDS_VIS = "(||) [(||)(||)]"
FRAC_THREE_FOURTHS_VIS = "()[()()()]"
# Полная отрисовка 3/4: та же схема, что ()[()()()] — снаружи 1/4 (не взяли), в […] три доли.
FRAC_THREE_FOURTHS_FULL = "(||) [(||)(||)(||)]"


def _add_fraction_heaps(b: dict) -> None:
    """Fraction as heap-parts: 1/2 = (||) ||, 2/3 = (||) [(||)(||)], 3/4 = ()[()()()]."""
    claims = list(b.get("claims") or [])
    existing = {c["concept_id"] for c in claims}
    frac_claims = [
        ("math.concept.fraction", "Fraction: N heaps taken out of K equal heaps (дробь на кучках)."),
        ("math.role.numerator", "Numerator: how many heaps were taken (числитель)."),
        ("math.role.denominator", "Denominator: into how many heaps the whole was split (знаменатель)."),
        ("math.entity.heap_bracket", "Square brackets group several equal heaps: [(||)(||)]."),
        (
            "math.entity.heap_slot",
            "One heap-share in fraction notation: () marks a heap even without sticks drawn inside "
            "(not lesson-11 zero — sticks omitted for brevity).",
        ),
        ("math.ctx.fraction_heap", "Reading: fraction as highlighted heap parts."),
        ("math.frac.one_half", "One half: 1 heap of 2 — (||) ||."),
        ("math.frac.two_thirds", "Two thirds: 2 heaps of 3 — (||) [(||)(||)]."),
        (
            "math.frac.three_fourths",
            "Three fourths: 3 heaps of 4 — ()[()()()] (lazy) or (||) [(||)(||)(||)] (full sticks).",
        ),
    ]
    for cid, text in frac_claims:
        if cid not in existing:
            claims.append({"concept_id": cid, "text": text})
            existing.add(cid)

    ru_frac = [
        ("lang.word.дробь", "math.concept.fraction"),
        ("lang.word.числитель", "math.role.numerator"),
        ("lang.word.знаменатель", "math.role.denominator"),
        ("lang.word.половина", "math.frac.one_half"),
    ]
    for word, role in ru_frac:
        cid = word
        if cid not in existing:
            claims.append({"concept_id": cid, "text": f"RU word → {role}"})
            existing.add(cid)
    b["claims"] = claims

    edges = list((b.get("graph") or {}).get("edges") or [])
    edge_keys = {(e["src"], e["relation"], e["dst"]) for e in edges}
    for role, word in ru_frac:
        key = (role, "denotes", word)
        if key not in edge_keys:
            edges.append({"src": role, "relation": "denotes", "dst": word})
            edge_keys.add(key)
    for frac in ("math.frac.one_half", "math.frac.two_thirds", "math.frac.three_fourths"):
        key = ("math.concept.fraction", "example_of", frac)
        if key not in edge_keys:
            edges.append({"src": frac, "relation": "instance_of", "dst": "math.concept.fraction"})
            edge_keys.add(key)
        key2 = ("math.role.heap", "part_of", frac)
        if key2 not in edge_keys:
            edges.append({"src": "math.role.heap", "relation": "models", "dst": frac})
            edge_keys.add(key2)
    b.setdefault("graph", {})["edges"] = edges

    ctx = "math.ctx.fraction_heap"
    senses = list(b.get("symbol_senses") or [])
    sense_keys = {(s.get("glyph"), s.get("context"), s.get("concept_id")) for s in senses}
    for glyph, concept in (
        ("1/2", "math.frac.one_half"),
        ("2/3", "math.frac.two_thirds"),
        ("3/4", "math.frac.three_fourths"),
        (FRAC_HALF_VIS, "math.frac.one_half"),
        (FRAC_TWO_THIRDS_VIS, "math.frac.two_thirds"),
        (FRAC_THREE_FOURTHS_VIS, "math.frac.three_fourths"),
        (FRAC_THREE_FOURTHS_FULL, "math.frac.three_fourths"),
    ):
        key = (glyph, ctx, concept)
        if key in sense_keys:
            continue
        row: dict[str, Any] = {
            "glyph": glyph,
            "context": ctx,
            "concept_id": concept,
            "when": {"shape": "fraction_heap"},
        }
        senses.append(row)
        sense_keys.add(key)
    b["symbol_senses"] = senses

    glyphs = list(b.get("math_glyphs") or [])
    glyph_keys = {(g.get("glyph"), g.get("concept_id")) for g in glyphs}
    for glyph, concept in (
        ("1/2", "math.frac.one_half"),
        ("2/3", "math.frac.two_thirds"),
        ("3/4", "math.frac.three_fourths"),
    ):
        if (glyph, concept) not in glyph_keys:
            glyphs.append({"glyph": glyph, "concept_id": concept, "context": ctx})
    b["math_glyphs"] = glyphs

    kw = dict(b.get("math_keywords") or {})
    kw.update(
        {
            "math.concept.fraction": ["дробь", "доля", "часть", "fraction"],
            "math.role.numerator": ["числитель", "взяли", "сколько кучек взяли"],
            "math.role.denominator": ["знаменатель", "на сколько кучек", "разделили"],
            "math.frac.one_half": ["1/2", "половина", FRAC_HALF_VIS],
            "math.frac.two_thirds": ["2/3", "две трети", FRAC_TWO_THIRDS_VIS],
            "math.frac.three_fourths": [
                "3/4",
                "три четверти",
                FRAC_THREE_FOURTHS_VIS,
                FRAC_THREE_FOURTHS_FULL,
            ],
            "math.entity.heap_slot": ["кучка-доля", "слот кучки", "без палочек внутри"],
            "math.entity.heap_bracket": ["скобки кучек", "[", "]"],
        }
    )
    b["math_keywords"] = kw

    contexts = list(b.get("reading_contexts") or [])
    contexts.extend(
        [
            {
                "id": ctx,
                "when": {"shape": "fraction_heap"},
                "weight": 14,
                "text": "Fraction on heaps: numerator heaps taken, denominator total heaps.",
            },
            {
                "id": ctx,
                "when": {"shape": "fraction_heap", "glyph": FRAC_HALF_VIS},
                "weight": 16,
                "text": "Half: one heap of two — (||) ||.",
            },
            {
                "id": ctx,
                "when": {"shape": "fraction_heap", "glyph": FRAC_TWO_THIRDS_VIS},
                "weight": 16,
                "text": "Two thirds: (||) plus bracket of two heaps.",
            },
            {
                "id": ctx,
                "when": {"shape": "fraction_heap", "glyph": FRAC_THREE_FOURTHS_VIS},
                "weight": 16,
                "text": "Three fourths (lazy): () marks heap-shares without drawing sticks inside.",
            },
            {
                "id": ctx,
                "when": {"shape": "fraction_heap", "glyph": FRAC_THREE_FOURTHS_FULL},
                "weight": 15,
                "text": "Three fourths (full): (||) is the one heap left, bracket holds the three taken.",
            },
        ]
    )
    b["reading_contexts"] = contexts

    sym = list(b.setdefault("symbol_concepts", []))
    for g in ("grapheme.latn.[", "grapheme.latn.]", "grapheme.latn./"):
        if g not in sym:
            sym.append(g)
    b["symbol_concepts"] = sym


def _add_counting_zero_and_digits(b: dict) -> None:
    """Zero, sticks 1–4, digit glyphs ↔ math.num.* (lesson-00)."""
    senses = list(b.get("symbol_senses") or [])
    sense_keys = {(s.get("glyph"), s.get("context"), s.get("concept_id")) for s in senses}
    for glyph, concept in (
        ("||||", "math.num.four"),
        ("0", "math.num.zero"),
        ("1", "math.num.one"),
        ("2", "math.num.two"),
        ("3", "math.num.three"),
        ("4", "math.num.four"),
    ):
        ctx = "math.ctx.cardinal"
        key = (glyph, ctx, concept)
        if key in sense_keys:
            continue
        row: dict[str, Any] = {"glyph": glyph, "context": ctx, "concept_id": concept}
        if len(glyph) == 1 and glyph.isdigit():
            row["grapheme"] = f"grapheme.latn.{glyph}"
        senses.append(row)
        sense_keys.add(key)
    b["symbol_senses"] = senses

    glyphs = list(b.get("math_glyphs") or [])
    glyph_keys = {(g.get("glyph"), g.get("concept_id")) for g in glyphs}
    if ("||||", "math.num.four") not in glyph_keys:
        glyphs.append({"glyph": "||||", "concept_id": "math.num.four", "context": "math.ctx.cardinal"})
    b["math_glyphs"] = glyphs

    kw = dict(b.get("math_keywords") or {})
    kw.setdefault("math.num.zero", [])
    kw.setdefault("math.num.four", [])
    for word in ("zero", "ноль", "пусто", "нет", "ноль палочек", "0 палочек"):
        if word not in kw["math.num.zero"]:
            kw["math.num.zero"].append(word)
    for word in ("four", "четыре", "четыре палочки"):
        if word not in kw["math.num.four"]:
            kw["math.num.four"].append(word)
    for cid, extra in (
        ("math.num.one", ("одна палочка",)),
        ("math.num.two", ("две палочки",)),
        ("math.num.three", ("три палочки",)),
    ):
        kw.setdefault(cid, [])
        for word in extra:
            if word not in kw[cid]:
                kw[cid].append(word)
    b["math_keywords"] = kw

    contexts = list(b.get("reading_contexts") or [])
    ctx_ids = {str(c.get("id")) for c in contexts}
    if "math.ctx.cardinal" in ctx_ids:
        contexts.append(
            {
                "id": "math.ctx.cardinal",
                "when": {"shape": "singleton", "glyph": "0"},
                "weight": 10,
                "text": "Digit zero in stick counting.",
            }
        )
    b["reading_contexts"] = contexts

    sym = list(b.setdefault("symbol_concepts", []))
    for d in "01234":
        g = f"grapheme.latn.{d}"
        if g not in sym:
            sym.append(g)
    b["symbol_concepts"] = sym


def _ep(
    cue: str,
    correct: str,
    concept_id: str,
    scene: str,
    *,
    structure_tag: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "cue": cue,
        "correct": correct,
        "concept_id": concept_id,
        "scene": scene,
        "lattice_id": "schema-math",
        "episode_source": "lesson",
    }
    if structure_tag:
        row["structure_tag"] = structure_tag
    return row


def _scene(cue: str, scene: str, concept_id: str) -> dict[str, Any]:
    """Teacher presentation — visible structure in cue; no numeric oracle in correct."""
    return {
        "cue": cue,
        "correct": "",
        "surface_attempt": "",
        "concept_id": concept_id,
        "scene": scene,
        "lattice_id": "schema-math",
        "episode_source": "lesson",
        "presentation": True,
    }


def _vocab(cue: str, concept_id: str, scene: str) -> dict[str, Any]:
    """Role / property word — identity mapping, not arithmetic oracle."""
    return _ep(cue, cue, concept_id, scene)


def build_manifest() -> dict[str, Any]:
    lessons: list[dict[str, Any]] = [
        {
            "id": "lesson-00-zero-and-digits",
            "title": "Ноль и цифры ↔ палочки",
            "episodes": [
                _ep("0", "0", "math.num.zero", "lesson00_zero"),
                _ep("ноль", "0", "math.num.zero", "lesson00_zero_word"),
                _ep("пусто", "0", "math.num.zero", "lesson00_empty"),
                _ep("ноль палочек", "0", "math.num.zero", "lesson00_zero_phrase"),
                _ep("1", "1", "math.num.one", "lesson00_digit"),
                _ep("2", "2", "math.num.two", "lesson00_digit"),
                _ep("3", "3", "math.num.three", "lesson00_digit"),
                _ep("4", "4", "math.num.four", "lesson00_digit"),
                _ep("1 = |", "|", "math.num.one", "lesson00_digit_stick"),
                _ep("2 = ||", "||", "math.num.two", "lesson00_digit_stick"),
                _ep("3 = |||", "|||", "math.num.three", "lesson00_digit_stick"),
                _ep("4 = ||||", "||||", "math.num.four", "lesson00_digit_stick"),
                _ep("одна палочка", "|", "math.num.one", "lesson00_phrase"),
                _ep("две палочки", "||", "math.num.two", "lesson00_phrase"),
                _ep("три палочки", "|||", "math.num.three", "lesson00_phrase"),
                _ep("четыре палочки", "||||", "math.num.four", "lesson00_phrase"),
            ],
        },
        {
            "id": "lesson-01-sticks-and-heaps",
            "title": "Палочка и кучки",
            "episodes": [
                _ep("|", "1", "math.num.one", "lesson01_count"),
                _ep("||", "2", "math.num.two", "lesson01_count"),
                _ep("|||", "3", "math.num.three", "lesson01_count"),
                _ep("||||", "4", "math.num.four", "lesson01_count"),
                _ep("палочка", "палочка", "math.entity.stick", "lesson01_vocab"),
                _ep("кучка", "кучка", "math.role.heap", "lesson01_vocab"),
            ],
        },
        {
            "id": "lesson-02-equal-heaps",
            "title": "Поровну",
            "episodes": [
                _ep("|||||| поровну 3", "|| || ||", "math.num.two", "lesson02_equal"),
                _ep("|||| поровну 2", "|| ||", "math.num.two", "lesson02_equal"),
                _ep("сколько в каждой || || ||", "2", "math.num.two", "lesson02_each"),
            ],
        },
        {
            "id": "lesson-03-addition",
            "title": "Сложение",
            "episodes": [
                _ep("| + | = ||", "||", "math.op.add", "lesson03_sticks_add"),
                _ep("|| + || = ||||", "||||", "math.op.add", "lesson03_sticks_add"),
                _ep("2 + 3 = 5", "5", "math.op.add", "lesson03_numeric_add"),
                _ep("слагаемое", "слагаемое", "math.role.addend", "lesson03_vocab"),
                _ep("сумма", "сумма", "math.role.sum", "lesson03_vocab"),
            ],
        },
        {
            "id": "lesson-04-subtraction",
            "title": "Вычитание",
            "episodes": [
                _ep("||| - || = |", "|", "math.op.sub", "lesson04_sticks_sub"),
                _ep("|||| - | = |||", "|||", "math.op.sub", "lesson04_sticks_sub"),
                _ep("5 - 2 = 3", "3", "math.op.sub", "lesson04_numeric_sub"),
                _ep("уменьшаемое", "уменьшаемое", "math.role.minuend", "lesson04_vocab"),
                _ep("вычитаемое", "вычитаемое", "math.role.subtrahend", "lesson04_vocab"),
                _ep("разность", "разность", "math.role.difference", "lesson04_vocab"),
            ],
        },
        {
            "id": "lesson-05-groups-of-n",
            "title": "Группы по N",
            "episodes": [
                _ep("|| || ||", "6", "math.num.six", "lesson05_groups"),
                _ep("3 раза по 2", "6", "math.num.six", "lesson05_skip"),
                _ep("||| + ||| + |||", "9", "math.op.add", "lesson05_repeat_add"),
            ],
        },
        {
            "id": "lesson-06-multiplication",
            "title": "Умножение",
            "episodes": [
                _ep("3 × 2 = 6", "6", "math.op.mul", "lesson06_mul"),
                _ep("2 * 3 = 6", "6", "math.op.mul", "lesson06_mul"),
                _ep("|| || || = 3 × 2", "6", "math.op.mul", "lesson06_sticks_mul"),
                _ep("множитель", "множитель", "math.role.factor", "lesson06_vocab"),
                _ep("произведение", "произведение", "math.role.product", "lesson06_vocab"),
            ],
        },
        {
            "id": "lesson-07-division-groups-of",
            "title": "Деление: по N в кучке",
            "episodes": [
                _ep("|||| / 2", "2", "math.op.div", "lesson07_div_quotitive"),
                _ep("|||| / 2 = 2", "2", "math.op.div", "lesson07_div_quotitive"),
                _ep("|||| / 2 → (||)(||)", "2", "math.role.quotient", "lesson07_heap_count"),
                _ep("делимое", "делимое", "math.role.dividend", "lesson07_vocab"),
                _ep("делитель", "делитель", "math.role.divisor", "lesson07_vocab"),
                _ep("частное", "частное", "math.role.quotient", "lesson07_vocab"),
            ],
        },
        {
            "id": "lesson-08-division-into-heaps",
            "title": "Деление: на K кучек",
            "episodes": [
                _ep("|||| на 2 кучки", "2", "math.role.quotient", "lesson08_div_partition"),
                _ep("|||| / 2 кучки", "||", "math.num.two", "lesson08_each_heap"),
                _ep("6 / 3 = 2", "2", "math.op.div", "lesson08_numeric_div"),
            ],
        },
        {
            "id": "lesson-09-which-question",
            "title": "Какой вопрос?",
            "episodes": [
                _ep("|| + || = ?", "math.op.add", "math.op.add", "lesson09_drill"),
                _ep("||| - || = ?", "math.op.sub", "math.op.sub", "lesson09_drill"),
                _ep("|||| / 2 = ?", "math.op.div", "math.op.div", "lesson09_drill"),
                _ep("3 × 2 = ?", "math.op.mul", "math.op.mul", "lesson09_drill"),
            ],
        },
        {
            "id": "lesson-10-operand-vocabulary",
            "title": "Словарь операндов",
            "episodes": [
                _ep("слагаемое + слагаемое = сумма", "сумма", "math.role.sum", "lesson10_recap"),
                _ep("уменьшаемое − вычитаемое = разность", "разность", "math.role.difference", "lesson10_recap"),
                _ep("делимое ÷ делитель = частное", "частное", "math.role.quotient", "lesson10_recap"),
                _ep("множитель × множитель = произведение", "произведение", "math.role.product", "lesson10_recap"),
            ],
        },
        {
            "id": "lesson-11-paren-groups",
            "title": "Группы в скобках",
            "episodes": [
                _ep("()", "0", "math.num.zero", "lesson11_empty_group"),
                _ep("пустая группа", "0", "math.num.zero", "lesson11_empty_word"),
                _ep("(|)", "1", "math.num.one", "lesson11_pipe_group"),
                _ep("(||)", "2", "math.num.two", "lesson11_pipe_group"),
                _ep("(|||)", "3", "math.num.three", "lesson11_pipe_group"),
                _ep("(||||)", "4", "math.num.four", "lesson11_pipe_group"),
                _ep("(I)", "1", "math.num.one", "lesson11_i_group"),
                _ep("(II)", "2", "math.num.two", "lesson11_i_group"),
                _ep("(III)", "3", "math.num.three", "lesson11_i_group"),
                _ep("(IIII)", "4", "math.num.four", "lesson11_i_group"),
                _ep("(IIIII)", "5", "math.num.five", "lesson11_i_group"),
                _ep("() = 0", "0", "math.num.zero", "lesson11_eq"),
                _ep("(|) = 1", "1", "math.num.one", "lesson11_eq"),
                _ep("(||) = 2", "2", "math.num.two", "lesson11_eq"),
                _ep("(|||) = 3", "3", "math.num.three", "lesson11_eq"),
                _ep("(IIIII) = ?", "5", "math.num.five", "lesson11_drill"),
                _ep("группа", "группа", "math.entity.group", "lesson11_vocab"),
            ],
        },
        {
            "id": "lesson-12-compute-drill",
            "title": "Вычисления: примеры",
            "episodes": [
                _ep("| + | = ||", "||", "math.op.add", "lesson12_sticks_add"),
                _ep("|| + | = |||", "|||", "math.op.add", "lesson12_sticks_add"),
                _ep("(||) + (||) = ||||", "||||", "math.op.add", "lesson12_group_add"),
                _ep("(|||) + (|) = ||||", "||||", "math.op.add", "lesson12_group_add"),
                _ep("1 + 2 = 3", "3", "math.op.add", "lesson12_numeric_add"),
                _ep("2 + 3 = 5", "5", "math.op.add", "lesson12_numeric_add"),
                _ep("||| - || = |", "|", "math.op.sub", "lesson12_sticks_sub"),
                _ep("(|||) - (||) = (|)", "(|)", "math.op.sub", "lesson12_group_sub"),
                _ep("5 - 2 = 3", "3", "math.op.sub", "lesson12_numeric_sub"),
                _ep("|||| - || = ||", "||", "math.op.sub", "lesson12_sticks_sub"),
                _ep("3 × 2 = 6", "6", "math.op.mul", "lesson12_mul"),
                _ep("|| || || = 6", "6", "math.op.mul", "lesson12_sticks_mul"),
                _ep("|||| / 2 = 2", "2", "math.op.div", "lesson12_div"),
                _ep("(||||) / (||) = (||)", "(||)", "math.op.div", "lesson12_group_div"),
                _ep("| + | = ?", "||", "math.op.add", "lesson12_drill"),
                _ep("(||) + (||) = ?", "||||", "math.op.add", "lesson12_drill"),
                _ep("4 - 1 = ?", "3", "math.op.sub", "lesson12_drill"),
            ],
        },
        {
            "id": "lesson-13-kolb-count-rows",
            "title": "Kolb: ряд счёта (teacher demo)",
            "episodes": [
                _scene("0", "count_row:by_one", "math.num.zero"),
                _scene("1", "count_row:by_one", "math.num.one"),
                _scene("2", "count_row:by_one", "math.num.two"),
                _scene("3", "count_row:by_one", "math.num.three"),
                _scene("4", "count_row:by_one", "math.num.four"),
                _scene("5", "count_row:by_one", "math.num.five"),
            ],
        },
        {
            "id": "lesson-14-commutative",
            "title": "Свойства: перестановка (+ и ×)",
            "episodes": [
                _scene("| + || = |||", "prop:comm_add", "math.prop.commutative_add"),
                _scene("|| + | = |||", "prop:comm_add", "math.prop.commutative_add"),
                _scene("(||) + (|||) = (|||||)", "prop:comm_add", "math.prop.commutative_add"),
                _scene("(|||) + (||) = (|||||)", "prop:comm_add", "math.prop.commutative_add"),
                _scene("2 + 3", "prop:comm_add", "math.op.add"),
                _scene("3 + 2", "prop:comm_add", "math.op.add"),
                _scene("|| || ||", "prop:comm_mul", "math.op.mul"),
                _scene("|| || || = 3 × 2", "prop:comm_mul", "math.prop.commutative_mul"),
                _scene("3 × 2", "prop:comm_mul", "math.op.mul"),
                _scene("2 × 3", "prop:comm_mul", "math.op.mul"),
                _vocab("перестановка слагаемых", "math.prop.commutative_add", "lesson14_vocab"),
                _vocab("перестановка множителей", "math.prop.commutative_mul", "lesson14_vocab"),
            ],
        },
        {
            "id": "lesson-15-associative-distributive",
            "title": "Свойства: группировка и распределение",
            "episodes": [
                _scene("(| + ||) + ||| = |||||", "prop:assoc_add", "math.prop.associative_add"),
                _scene("| + (|| + |||) = |||||", "prop:assoc_add", "math.prop.associative_add"),
                _scene("(||) + (|| + |||) = (|||||)", "prop:assoc_add", "math.prop.associative_add"),
                _scene("2 × (3 × 2)", "prop:assoc_mul", "math.prop.associative_mul"),
                _scene("(2 × 3) × 2", "prop:assoc_mul", "math.prop.associative_mul"),
                _scene("2 × (|| + ||)", "prop:distributive", "math.prop.distributive_mul_over_add"),
                _scene("2 × || + 2 × ||", "prop:distributive", "math.prop.distributive_mul_over_add"),
                _vocab("группировка слагаемых", "math.prop.associative_add", "lesson15_vocab"),
                _vocab("распределительное", "math.prop.distributive_mul_over_add", "lesson15_vocab"),
            ],
        },
        {
            "id": "lesson-16-identities-division",
            "title": "Свойства: ноль, единица, ÷ ↔ ×",
            "episodes": [
                _scene("||| + () = |||", "prop:identity_add_zero", "math.prop.identity_add_zero"),
                _scene("|||| + () = ||||", "prop:identity_add_zero", "math.prop.identity_add_zero"),
                _scene("5 + 0", "prop:identity_add_zero", "math.prop.identity_add_zero"),
                _scene("| × 1 = |", "prop:identity_mul_one", "math.prop.identity_mul_one"),
                _scene("|||| × 1 = ||||", "prop:identity_mul_one", "math.prop.identity_mul_one"),
                _scene("3 × 1", "prop:identity_mul_one", "math.prop.identity_mul_one"),
                _scene("|||| / 2 → (||)(||)", "prop:div_inverse_mul", "math.prop.division_inverse_mul"),
                _scene("2 × 2 = ||||", "prop:div_inverse_mul", "math.prop.division_inverse_mul"),
                _scene("6 / 3", "prop:div_inverse_mul", "math.op.div"),
                _scene("2 × 3", "prop:div_inverse_mul", "math.op.mul"),
                _vocab("нейтральный элемент сложения", "math.prop.identity_add_zero", "lesson16_vocab"),
                _vocab("нейтральный элемент умножения", "math.prop.identity_mul_one", "lesson16_vocab"),
            ],
        },
        {
            "id": "lesson-17-roles-and-four-ops",
            "title": "Роли операндов + четыре действия (сцены)",
            "episodes": [
                _scene("слагаемое + слагаемое → сумма", "lesson17_roles_add", "math.role.sum"),
                _scene("уменьшаемое − вычитаемое → разность", "lesson17_roles_sub", "math.role.difference"),
                _scene("множитель × множитель → произведение", "lesson17_roles_mul", "math.role.product"),
                _scene("делимое ÷ делитель → частное", "lesson17_roles_div", "math.role.quotient"),
                _vocab("слагаемое", "math.role.addend", "lesson17_vocab"),
                _vocab("уменьшаемое", "math.role.minuend", "lesson17_vocab"),
                _vocab("множитель", "math.role.factor", "lesson17_vocab"),
                _vocab("делимое", "math.role.dividend", "lesson17_vocab"),
                _scene("| + | = ||", "lesson17_op_add", "math.op.add"),
                _scene("||| - || = |", "lesson17_op_sub", "math.op.sub"),
                _scene("|| || ||", "lesson17_op_mul", "math.op.mul"),
                _scene("|||| / 2 → (||)(||)", "lesson17_op_div", "math.op.div"),
                _scene("2 + 3", "lesson17_expr", "math.op.add"),
                _scene("5 - 2", "lesson17_expr", "math.op.sub"),
                _scene("3 × 2", "lesson17_expr", "math.op.mul"),
                _scene("6 / 3", "lesson17_expr", "math.op.div"),
            ],
        },
        {
            "id": "lesson-19-place-value-tens-ones",
            "title": "Числа: десятки и единицы (10–99)",
            "episodes": [
                _scene("25 = 2 × 10 + 5 × 1", "lesson19_place_value", "math.num.25"),
                _scene("34 = 3 × 10 + 4 × 1", "lesson19_place_value", "math.num.34"),
                _scene("40 = 4 × 10 + 0 × 1", "lesson19_place_value", "math.num.40"),
                _scene("99 = 9 × 10 + 9 × 1", "lesson19_place_value", "math.num.99"),
                _scene("2 × 10 + 5 × 1 = 25", "lesson19_place_value", "math.num.25"),
                _scene("3 × 10 + 4 × 1 = 34", "lesson19_place_value", "math.num.34"),
                _vocab("десяток", "math.num.ten", "lesson19_vocab"),
                _vocab("единица", "math.num.one", "lesson19_vocab"),
            ],
        },
        {
            "id": "lesson-18-fraction-heaps",
            "title": "Дроби: доля кучек",
            "episodes": [
                _ep("дробь", "дробь", "math.concept.fraction", "lesson18_vocab"),
                _ep("числитель", "числитель", "math.role.numerator", "lesson18_vocab"),
                _ep("знаменатель", "знаменатель", "math.role.denominator", "lesson18_vocab"),
                _scene(
                    "числитель / знаменатель = дробь",
                    "lesson18_frac_roles",
                    "math.concept.fraction",
                ),
                _ep(
                    "числитель / знаменатель = дробь",
                    "дробь",
                    "math.concept.fraction",
                    "lesson18_frac_roles",
                ),
                _ep(
                    "числитель / знаменатель",
                    "дробь",
                    "math.concept.fraction",
                    "lesson18_frac_roles",
                ),
                _scene(
                    "числитель — сколько кучек взяли, знаменатель — на сколько кучек разделили",
                    "lesson18_rule",
                    "math.concept.fraction",
                ),
                _scene(
                    f"1/2 = {FRAC_HALF_VIS}",
                    "lesson18_half",
                    "math.frac.one_half",
                ),
                _ep(
                    f"1/2 = {FRAC_HALF_VIS}",
                    FRAC_HALF_VIS,
                    "math.frac.one_half",
                    "lesson18_half",
                ),
                _ep("1/2", "1/2", "math.frac.one_half", "lesson18_half_glyph"),
                _ep("половина", "1/2", "math.frac.one_half", "lesson18_half_word"),
                _ep(
                    "1 из 2 кучек",
                    "1/2",
                    "math.frac.one_half",
                    "lesson18_half_phrase",
                ),
                _scene(
                    f"2/3 = {FRAC_TWO_THIRDS_VIS}",
                    "lesson18_two_thirds",
                    "math.frac.two_thirds",
                ),
                _ep(
                    f"2/3 = {FRAC_TWO_THIRDS_VIS}",
                    FRAC_TWO_THIRDS_VIS,
                    "math.frac.two_thirds",
                    "lesson18_two_thirds",
                ),
                _ep("2/3", "2/3", "math.frac.two_thirds", "lesson18_two_thirds_glyph"),
                _ep(
                    "2 из 3 кучек",
                    "2/3",
                    "math.frac.two_thirds",
                    "lesson18_two_thirds_phrase",
                ),
                _scene(
                    "() в дроби — одна кучка-доля; палочки внутри можно не рисовать (это не ноль из lesson 11)",
                    "lesson18_heap_slot",
                    "math.entity.heap_slot",
                ),
                _scene(
                    f"3/4 = {FRAC_THREE_FOURTHS_VIS}",
                    "lesson18_three_fourths",
                    "math.frac.three_fourths",
                ),
                _ep(
                    f"3/4 = {FRAC_THREE_FOURTHS_VIS}",
                    FRAC_THREE_FOURTHS_VIS,
                    "math.frac.three_fourths",
                    "lesson18_three_fourths",
                ),
                _scene(
                    f"3/4 = {FRAC_THREE_FOURTHS_FULL}",
                    "lesson18_three_fourths_full",
                    "math.frac.three_fourths",
                ),
                _ep(
                    f"3/4 = {FRAC_THREE_FOURTHS_FULL}",
                    FRAC_THREE_FOURTHS_FULL,
                    "math.frac.three_fourths",
                    "lesson18_three_fourths_full",
                ),
                _ep("3/4", "3/4", "math.frac.three_fourths", "lesson18_three_fourths_glyph"),
                _ep(
                    "3 из 4 кучек",
                    "3/4",
                    "math.frac.three_fourths",
                    "lesson18_three_fourths_phrase",
                ),
                _ep(
                    "|||| на 2 кучки → 1/2",
                    "1/2",
                    "math.frac.one_half",
                    "lesson18_link_div",
                ),
                _ep(
                    "|||| на 4 кучки, взяли 3 → 3/4",
                    "3/4",
                    "math.frac.three_fourths",
                    "lesson18_link_div",
                ),
            ],
        },
    ]
    return {
        "schema_version": 1,
        "class_id": "math-palochki",
        "target_agent": "von-neumann",
        "bundle": "kb-math-palochki-v1.bundle.json",
        "probe": [
            {"cue": "0", "expect": "math.num.zero"},
            {"cue": "()", "expect": "math.num.zero"},
            {"cue": "||||", "expect": "math.num.four"},
            {"cue": "(||)", "expect": "math.num.two"},
            {"cue": "(IIIII)", "expect": "math.num.five"},
            {"cue": "1", "expect": "math.num.one"},
            {"cue": "ноль палочек", "expect": "math.num.zero"},
            {"cue": "одна палочка", "expect": "math.num.one"},
            {"cue": "| + |", "expect": "math.op.add"},
            {"cue": "(||) + (||)", "expect": "math.op.add"},
            {"cue": "||| - ||", "expect": "math.op.sub"},
            {"cue": "(|||) - (||)", "expect": "math.op.sub"},
            {"cue": "|||| / 2", "expect": "math.op.div"},
            {"cue": "3 × 2", "expect": "math.op.mul"},
            {"cue": "||", "expect": "math.num.two"},
            {"cue": "1/2", "expect": "math.frac.one_half"},
            {"cue": FRAC_HALF_VIS, "expect": "math.frac.one_half"},
            {"cue": "2/3", "expect": "math.frac.two_thirds"},
            {"cue": "3/4", "expect": "math.frac.three_fourths"},
            {"cue": "числитель / знаменатель", "expect": "math.concept.fraction"},
            {"cue": "числитель / знаменатель = дробь", "expect": "math.concept.fraction"},
        ],
        "mastery_probe": [
            {"cue": "| + | = ?", "expect": "math.num.two", "tier": "compute", "op": "add"},
            {"cue": "(||) + (||) = ?", "expect": "math.num.four", "tier": "compute", "op": "add"},
            {"cue": "2 + 3 = ?", "expect": "math.num.five", "tier": "compute", "op": "add"},
            {"cue": "||| - || = ?", "expect": "math.num.one", "tier": "compute", "op": "sub"},
            {"cue": "(|||) - (||) = ?", "expect": "math.num.one", "tier": "compute", "op": "sub"},
            {"cue": "5 - 2 = ?", "expect": "math.num.three", "tier": "compute", "op": "sub"},
            {"cue": "3 × 2 = ?", "expect": "math.num.six", "tier": "compute", "op": "mul"},
            {"cue": "|| || || = ?", "expect": "math.num.six", "tier": "compute", "op": "mul"},
            {"cue": "|||| / 2 = ?", "expect": "math.num.two", "tier": "compute", "op": "div"},
            {"cue": "6 / 3 = ?", "expect": "math.num.two", "tier": "compute", "op": "div"},
            {"cue": "слагаемое", "expect": "math.role.addend", "tier": "role"},
            {"cue": "делимое", "expect": "math.role.dividend", "tier": "role"},
            {"cue": "произведение", "expect": "math.role.product", "tier": "role"},
            {"cue": "разность", "expect": "math.role.difference", "tier": "role"},
            {"cue": "2 + 3", "expect": "math.prop.commutative_add", "tier": "property"},
            {"cue": "3 + 2", "expect": "math.prop.commutative_add", "tier": "property"},
            {"cue": "||| + () = |||", "expect": "math.prop.identity_add_zero", "tier": "property"},
            {"cue": "3 × 1", "expect": "math.prop.identity_mul_one", "tier": "property"},
            {"cue": "6 / 3", "expect": "math.prop.division_inverse_mul", "tier": "property"},
            {"cue": "1/2", "expect": "math.frac.one_half", "tier": "fraction"},
            {"cue": FRAC_HALF_VIS, "expect": "math.frac.one_half", "tier": "fraction"},
            {"cue": FRAC_TWO_THIRDS_VIS, "expect": "math.frac.two_thirds", "tier": "fraction"},
            {"cue": FRAC_THREE_FOURTHS_VIS, "expect": "math.frac.three_fourths", "tier": "fraction"},
            {"cue": "числитель", "expect": "math.role.numerator", "tier": "fraction"},
            {"cue": "знаменатель", "expect": "math.role.denominator", "tier": "fraction"},
            {"cue": "числитель / знаменатель", "expect": "math.concept.fraction", "tier": "fraction"},
            {"cue": "числитель / знаменатель = дробь", "expect": "math.concept.fraction", "tier": "fraction"},
        ],
        "mastery_threshold": {
            "compute": 0.85,
            "role": 0.9,
            "property": 0.75,
            "fraction": 0.75,
        },
        "lessons": lessons,
    }


def write_class(out_dir: Path | None = None) -> dict[str, Any]:
    out = (out_dir or CLASS_DIR).resolve()
    out.mkdir(parents=True, exist_ok=True)
    base = json.loads(BASE_BUNDLE.read_text(encoding="utf-8"))
    bundle = _extend_bundle(base)
    manifest = build_manifest()
    bundle_path = out / "kb-math-palochki-v1.bundle.json"
    manifest_path = out / "class.manifest.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "class_dir": str(out),
        "bundle": str(bundle_path),
        "manifest": str(manifest_path),
        "lesson_count": len(manifest["lessons"]),
        "episode_count": sum(len(l["episodes"]) for l in manifest["lessons"]),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Generate math-palochki class artifacts")
    p.add_argument("--out-dir", type=Path, default=CLASS_DIR)
    args = p.parse_args()
    rep = write_class(args.out_dir)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
