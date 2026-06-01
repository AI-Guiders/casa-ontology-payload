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
    return b


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
            "title": "Kolb: ряд счёта → emergent pattern",
            "episodes": [
                _ep("0", "0", "math.num.zero", "count_row:by_one"),
                _ep("1", "1", "math.num.one", "count_row:by_one"),
                _ep("2", "2", "math.num.two", "count_row:by_one"),
                _ep("3", "3", "math.num.three", "count_row:by_one"),
                _ep("4", "4", "math.num.four", "count_row:by_one"),
                _ep("5", "5", "math.num.five", "count_row:by_one"),
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
        ],
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
