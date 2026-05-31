"""Unit tests for f0_reading frame matching."""

from __future__ import annotations

from casa.prisms.memory.f0_reading import analyze_cue, detect_reading_contexts


def test_analyze_classifies_operands() -> None:
    a = analyze_cue('"a"+"b"')
    assert a["infix"][0]["left_kind"] == "string_literal"
    assert a["infix"][0]["op"] == "+"

    b = analyze_cue("x|y")
    assert b["infix"][0]["op"] == "|"
    assert b["infix"][0]["left_kind"] == "identifier"

    c = analyze_cue("||")
    assert c["glyph_run"]["glyph_class"] == "pipe"


def test_frame_rules_are_data_driven() -> None:
    bundle = {
        "reading_contexts": [
            {"id": "math.ctx.custom", "when": {"shape": "infix", "op": "&", "operand": "identifier"}, "weight": 9},
        ]
    }
    assert detect_reading_contexts("a&b", bundle=bundle)["math.ctx.custom"] == 9
