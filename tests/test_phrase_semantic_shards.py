#!/usr/bin/env python3
"""Token-range phrase shard id slugs (L3 semantic naming)."""

from __future__ import annotations

from casa.prisms.memory.phrase_shard import (
    attach_token_range_shard_ids,
    build_semantic_l3_rename_map,
    phrase_token_kind_hint,
    phrase_token_range_lattice_id,
    phrase_token_range_slug,
    phrase_token_slug_part,
)

_LO = "E:lang.word.а-ля|usage_axis|eyJh"
_HI = "E:lang.word.андрейкин|usage_axis|eyJh"


def test_phrase_token_slug_part():
    assert phrase_token_slug_part(_LO) == "lang.word.а-ля"
    assert len(phrase_token_slug_part("E:lang.word." + "н" * 40)) <= 20


def test_phrase_token_range_slug():
    slug = phrase_token_range_slug(_LO, _HI)
    assert "lang.word" in slug
    assert phrase_token_range_slug(_LO, _LO) == phrase_token_slug_part(_LO)


def test_phrase_token_range_lattice_id():
    lid = phrase_token_range_lattice_id(_LO, _HI)
    assert lid.startswith("phrases-")
    assert "07" not in lid


def test_phrase_token_kind_hint():
    assert phrase_token_kind_hint(_LO) == "word entity"
    assert phrase_token_kind_hint("M:qty:3") == "meta"


def test_attach_token_range_shard_ids():
    ranges = [
        {"shard": 7, "token_lo": _LO, "token_hi": _HI, "label": "x", "token_count": 781},
    ]
    out = attach_token_range_shard_ids(ranges)
    assert out[0]["shard_id"].startswith("phrases-")
    assert out[0].get("token_hint") == "word entity"


def test_build_l3_rename_map():
    cfg = {
        "token_ranges": [
            {"shard": 7, "token_lo": _LO, "token_hi": _HI},
        ]
    }
    m = build_semantic_l3_rename_map(cfg)
    new_id = m["L3_phrase_07"]
    assert m["phrases-07"] == new_id
    assert new_id.startswith("phrases-")
    assert "07" not in new_id.split("-", 1)[1][:4] or "lang.word" in new_id
