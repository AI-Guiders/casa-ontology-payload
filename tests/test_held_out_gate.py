"""Held-out gate — anti-tautology core (partition, ablation, negative control)."""

from __future__ import annotations

from casa.eval.held_out_gate import (
    ablate_injection_vectors,
    candidate_id_for,
    negative_control_relabel,
    partition_probe_bank,
)


def _num_cases(n: int) -> list[dict]:
    return [
        {"lattice": "schema-math", "cue": str(i), "concept_id": f"math.num.n{i}", "target": str(i)}
        for i in range(n)
    ]


def test_candidate_id_is_order_independent_and_stable() -> None:
    a = candidate_id_for([{"concept_id": "x", "text": "1"}, {"concept_id": "y"}])
    b = candidate_id_for([{"concept_id": "y"}, {"concept_id": "x", "text": "1"}])
    assert a == b
    assert a.startswith("cand-")
    # a different claim body yields a different id
    c = candidate_id_for([{"concept_id": "x", "text": "2"}, {"concept_id": "y"}])
    assert c != a


def test_partition_is_deterministic_disjoint_and_subtracts_held_out() -> None:
    cases = _num_cases(10)
    train, held = partition_probe_bank(cases, held_out_ratio=0.3, seed=0)
    train2, held2 = partition_probe_bank(cases, held_out_ratio=0.3, seed=0)
    # deterministic
    assert [c["cue"] for c in held] == [c["cue"] for c in held2]
    assert [c["cue"] for c in train] == [c["cue"] for c in train2]
    # sized
    assert len(held) == 3 and len(train) == 7
    # disjoint by (lattice, cue): no held-out cue leaks into train
    held_keys = {(c["lattice"], c["cue"]) for c in held}
    assert all((c["lattice"], c["cue"]) not in held_keys for c in train)


def test_partition_changes_with_seed() -> None:
    cases = _num_cases(10)
    _, held_a = partition_probe_bank(cases, held_out_ratio=0.3, seed=0)
    _, held_b = partition_probe_bank(cases, held_out_ratio=0.3, seed=7)
    assert [c["cue"] for c in held_a] != [c["cue"] for c in held_b]


def test_partition_empty_bank() -> None:
    assert partition_probe_bank([], held_out_ratio=0.3, seed=0) == ([], [])


def test_ablation_zeroes_injection_and_deep_copies() -> None:
    state = {"claims_nav": [1, 2, 3], "hot": {"a": 1}, "hot_context": ["x"], "keep": 5}
    ablated = ablate_injection_vectors(state)
    assert ablated["claims_nav"] == []
    assert ablated["hot"] == {}
    assert ablated["hot_context"] == []
    assert ablated["keep"] == 5
    assert ablated["_ablation"] == "injection_off"
    # original untouched (deep copy)
    assert state["claims_nav"] == [1, 2, 3]
    assert state["hot"] == {"a": 1}


def test_negative_control_relabels_to_deterministic_sibling() -> None:
    cases = [
        {"lattice": "L", "cue": "2", "concept_id": "math.num.two", "target": "2"},
        {"lattice": "L", "cue": "4", "concept_id": "math.num.four", "target": "4"},
    ]
    relabeled = negative_control_relabel(cases)
    # each case keeps its cue but gets a WRONG sibling concept_id, target cleared
    by_cue = {c["cue"]: c for c in relabeled}
    assert by_cue["2"]["concept_id"] == "math.num.four"
    assert by_cue["4"]["concept_id"] == "math.num.two"
    assert all(c["target"] == "" for c in relabeled)
    # deterministic
    assert negative_control_relabel(cases) == relabeled


def test_negative_control_drops_cases_without_siblings() -> None:
    # a lone concept in its prefix family has no sibling to relabel to
    cases = [{"lattice": "L", "cue": "x", "concept_id": "solo.only.one", "target": "x"}]
    assert negative_control_relabel(cases) == []
