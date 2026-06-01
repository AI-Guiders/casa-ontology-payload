"""F0 reading frames — generalized from bundle rules, not per-example regex."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.f0_field_reading import reading_model_from_decoded
from casa.prisms.memory.f0_reading import analyze_cue, detect_reading_contexts
from casa.prisms.memory.f0_stack import (
    augment_bundle_symbol_links,
    concept_in_context,
    contextual_symbol_key,
    decode_f0_lattice,
    encode_f0_lattice,
    math_op_for_grapheme,
    rank_cue_on_f0,
)

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


def _bundle() -> dict:
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


def test_augment_contextual_denotes_edges() -> None:
    b = augment_bundle_symbol_links(_bundle())
    edges = {(e["src"], e["relation"], e["dst"]) for e in b["graph"]["edges"]}
    key = contextual_symbol_key("grapheme.latn.+", "math.ctx.arithmetic")
    assert (key, "denotes", "math.op.add") in edges
    key_or = contextual_symbol_key("grapheme.latn.|", "math.ctx.bitwise")
    assert (key_or, "denotes", "math.op.or") in edges


def test_pipe_runs_cardinal_only() -> None:
    b = _bundle()
    lat = encode_f0_lattice(b)
    dec = decode_f0_lattice(lat)
    ranked = rank_cue_on_f0(dec, "||")
    assert ranked[0][0] == "math.num.two"
    ctx = detect_reading_contexts("||", reading_model=reading_model_from_decoded(dec))
    assert ctx.get("math.ctx.cardinal", 0) > ctx.get("math.ctx.bitwise", 0)


def test_infix_pipe_between_identifiers_is_bitwise() -> None:
    b = _bundle()
    lat = encode_f0_lattice(b)
    dec = decode_f0_lattice(lat)
    for cue in ("x|y", "a | b", "1|2"):
        assert concept_in_context(dec, "grapheme.latn.|", "math.ctx.bitwise") == "math.op.or"
        assert rank_cue_on_f0(dec, cue)[0][0] == "math.op.or"


def test_quoted_infix_plus_is_concat() -> None:
    b = _bundle()
    lat = encode_f0_lattice(b)
    dec = decode_f0_lattice(lat)
    for cue in ('"a"+"b"', '"hello" + "world"', "'x'+'y'"):
        ctx = detect_reading_contexts(cue, reading_model=reading_model_from_decoded(dec))
        assert ctx.get("math.ctx.string", 0) > ctx.get("math.ctx.arithmetic", 0)
        assert rank_cue_on_f0(dec, cue)[0][0] == "math.op.concat"


def test_numeric_infix_plus_is_add_without_code_change() -> None:
    b = _bundle()
    lat = encode_f0_lattice(b)
    dec = decode_f0_lattice(lat)
    ranked = rank_cue_on_f0(dec, "1+2")
    assert ranked[0][0] == "math.op.add"
    assert analyze_cue("1+2")["infix"][0]["left_kind"] == "number"


def test_single_char_plus_arithmetic() -> None:
    b = _bundle()
    lat = encode_f0_lattice(b)
    dec = decode_f0_lattice(lat)
    assert math_op_for_grapheme(dec, "grapheme.latn.+") == "math.op.add"
    assert rank_cue_on_f0(dec, "+")[0][0] == "math.op.add"


def test_stick_add_not_bitwise() -> None:
    b = _bundle()
    lat = encode_f0_lattice(b)
    dec = decode_f0_lattice(lat)
    assert rank_cue_on_f0(dec, "| + |")[0][0] == "math.op.add"
