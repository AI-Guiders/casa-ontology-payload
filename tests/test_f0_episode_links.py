"""Sleep Extract — episode links + emergent pattern hubs on schema-math."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.f0_pattern_extract import is_emergent_pattern_id
from casa.prisms.memory.f0_stack import decode_f0_lattice, mint_episode_links
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


def test_sleep_mints_emergent_count_pattern() -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    for cue, cid in (("2", "math.num.two"), ("4", "math.num.four"), ("6", "math.num.six")):
        append_episode(
            state,
            cue=cue,
            surface_attempt="?",
            correct=cue,
            lattice_id="schema-math",
            concept_id=cid,
            scene="count_row:lab",
            form_extract_allowed=True,
        )
    sleep = run_sleep(state, bundle)
    dec = decode_f0_lattice(memory_lattices(state)["schema-math"])
    ids = {c["concept_id"] for c in dec.get("concepts") or []}
    pattern_ids = [c for c in ids if is_emergent_pattern_id(c)]
    assert len(pattern_ids) == 1


def test_mint_episode_links_idempotent() -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    lats = memory_lattices(state)
    links = [{"src": "math.num.five", "relation": "names", "dst": "lang.word.five"}]
    first = mint_episode_links(lats, lattice_id="schema-math", links=links)
    second = mint_episode_links(lats, lattice_id="schema-math", links=links)
    assert len(first) == 1
    assert len(second) == 1
