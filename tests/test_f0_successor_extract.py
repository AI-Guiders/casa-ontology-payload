"""Emergent successor chain from ordered numeral episodes."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.f0_stack import decode_f0_lattice
from casa.prisms.memory.f0_successor_extract import extract_emergent_successors
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


def test_successor_not_in_bundle_minted_from_digits() -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle, copies=2)
    for d, cid in (
        ("0", "math.num.zero"),
        ("1", "math.num.one"),
        ("2", "math.num.two"),
        ("3", "math.num.three"),
    ):
        append_episode(
            state,
            cue=d,
            surface_attempt="?",
            correct=d,
            lattice_id="schema-math",
            concept_id=cid,
            scene="arabic_digit_glyph",
        )
    sleep = run_sleep(state, bundle)
    assert any(x.get("kind") == "emergent_successor" for x in sleep.get("items") or [])
    dec = decode_f0_lattice(memory_lattices(state)["schema-math"])
    edges = set(dec.get("edges") or [])
    assert "math.num.one|successor|math.num.two" in edges
    prov = (state.get("consolidation") or {}).get("emergent_provenance") or {}
    assert prov.get("successor:cluster")
