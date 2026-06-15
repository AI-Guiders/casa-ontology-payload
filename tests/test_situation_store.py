"""Persisted situation memory: fingerprints live on the field and survive a new session.

Persist situations as edges on the lattice; reconstruct the memory in a fresh state that
carries only the lattice cells (as field_state would); recall still works; forget removes.
"""

from __future__ import annotations

import copy
import json

from casa.curriculum.concept_net import teach_concept_net
from casa.curriculum.parse import parse_graph
from casa.curriculum.situation_memory import recall_containing, recall_similar, seen
from casa.curriculum.situation_store import forget_situation, load_memory, persist_situation
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
NET = REPO_ROOT / "lab/curriculum/concept-net-base-v1.json"
LAT = "schema-math"
SITUATIONS = ["яблоко на столе у окна", "собака ест мясо", "книга на столе"]


def _fresh() -> dict:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    teach_concept_net(state, LAT, json.loads(NET.read_text(encoding="utf-8")), bundle=bundle)
    return state


def test_persisted_memory_survives_a_new_session() -> None:
    s1 = _fresh()
    for t in SITUATIONS:
        assert persist_situation(s1, LAT, parse_graph(s1, LAT, t), label=t) is not None
    # new "session": a fresh state carrying only the lattice cells (as field_state does)
    s2 = _fresh()
    memory_lattices(s2)[LAT]["cells"] = copy.deepcopy(memory_lattices(s1)[LAT]["cells"])
    mem = load_memory(s2, LAT)
    labels = {r["label"] for r in mem["situations"]}
    assert SITUATIONS[0] in labels and SITUATIONS[1] in labels and SITUATIONS[2] in labels
    # recall works on the reconstructed memory
    assert seen(mem, parse_graph(s2, LAT, "собака ест мясо")) is not None
    assert any(r["label"] == "книга на столе" for r in recall_containing(mem, parse_graph(s2, LAT, "книга на столе")))
    ranked = recall_similar(mem, parse_graph(s2, LAT, "apple on the table"), top=2)
    assert ranked[0][0]["label"] == "яблоко на столе у окна"


def test_non_situation_is_not_persisted() -> None:
    s = _fresh()
    # «кот ест рыбу» — fish-the-animal is not edible -> no valid edge -> not a situation
    assert persist_situation(s, LAT, parse_graph(s, LAT, "кот ест рыбу"), label="x") is None
    assert load_memory(s, LAT)["situations"] == []


def test_forget_removes_from_field() -> None:
    s = _fresh()
    fid = persist_situation(s, LAT, parse_graph(s, LAT, "книга на столе"), label="книга на столе")
    assert len(load_memory(s, LAT)["situations"]) == 1
    forget_situation(s, LAT, fid)
    assert load_memory(s, LAT)["situations"] == []
