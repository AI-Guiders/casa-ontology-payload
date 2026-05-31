"""Deterministic assert-gate for the correction replay buffer (CASA-ADR-0009)."""

from __future__ import annotations

import casa.prisms.hippo.replay_buffer as rb


def _surface(ep_id: str, *, archived: int = 0, replayed=None, replays: int = 0, **over) -> dict:
    rec = {
        "episode_id": ep_id,
        "kind": "surface",
        "cue": "согласно",
        "correct": "приказу",
        "attempt": "приказа",
        "lattice_id": "L2_word",
        "concept_id": "lang.word.приказ",
        "correction_kind": "ortho_surface",
        "scene": "канцелярия",
        "first_archived_tick": archived,
        "last_replayed_tick": replayed,
        "replays": replays,
    }
    rec.update(over)
    return rec


def test_eligible_accepts_surface_and_rule():
    assert rb.eligible_for_replay(_surface("ep-1"))
    rule = {"episode_id": "r-1", "kind": "rule", "correct": "корова", "rule_id": "R:script.no_mixed_alphabet"}
    assert rb.eligible_for_replay(rule)


def test_eligible_rejects_pending_ask_hint_and_empty():
    assert not rb.eligible_for_replay(_surface("ep-p", pending=True))
    assert not rb.eligible_for_replay(_surface("ep-l", correction_kind="lexical_ask"))
    assert not rb.eligible_for_replay({"episode_id": "q", "kind": "question", "correct": "x"})
    assert not rb.eligible_for_replay({"episode_id": "h", "kind": "hint", "correct": "x"})
    assert not rb.eligible_for_replay(_surface("ep-e", correct="   "))
    assert not rb.eligible_for_replay({"episode_id": "r0", "kind": "rule", "correct": "x", "rule_id": ""})


def test_archive_is_idempotent_and_filters():
    buf: list[dict] = []
    merged = [
        {"episode_id": "ep-1", "kind": "surface", "cue": "согласно", "correct": "приказу",
         "lattice_id": "L2_word", "concept_id": "lang.word.приказ", "correction_kind": "ortho_surface", "scene": "s"},
        {"episode_id": "ep-1", "kind": "surface", "cue": "согласно", "correct": "приказу"},  # dup id
        {"episode_id": "ep-2", "kind": "question", "cue": "кор", "correct": "корова"},  # filtered
    ]
    rb.archive_records(buf, merged, now_tick=10)
    rb.archive_records(buf, merged, now_tick=11)
    assert [r["episode_id"] for r in buf] == ["ep-1"]


def test_prioritize_most_forgotten_first():
    buf = [
        _surface("fresh", archived=100, replayed=100),  # staleness 0 at now=100
        _surface("stale", archived=10, replayed=None),  # staleness 90
        _surface("mid", archived=50, replayed=80),       # staleness 20
    ]
    order = [r["episode_id"] for r in rb.prioritize(buf, now_tick=100)]
    assert order == ["stale", "mid", "fresh"]


def test_sample_topk_no_mutation():
    buf = [_surface("a", archived=0), _surface("b", archived=5), _surface("c", archived=9)]
    snapshot = [dict(r) for r in buf]
    batch = rb.sample(buf, 2, now_tick=100)
    assert len(batch) == 2
    assert buf == snapshot  # sampling must not mutate the buffer


def test_mark_replayed_updates_priority():
    buf = [_surface("a", archived=0), _surface("b", archived=1)]
    first = [r["episode_id"] for r in rb.sample(buf, 1, now_tick=100)]
    assert first == ["a"]
    rb.mark_replayed(buf, ["a"], now_tick=100)
    rec_a = next(r for r in buf if r["episode_id"] == "a")
    assert rec_a["last_replayed_tick"] == 100 and rec_a["replays"] == 1
    second = [r["episode_id"] for r in rb.sample(buf, 1, now_tick=101)]
    assert second == ["b"]  # 'a' just rehearsed -> 'b' is now more forgotten


def test_value_weight_reorders_high_value_first():
    buf = [
        _surface("stale_lowval", archived=0, value=0.0),    # staleness 100, value 0
        _surface("fresh_highval", archived=90, value=50.0),  # staleness 10, value 50
    ]
    # pure recency -> stale wins
    assert [r["episode_id"] for r in rb.sample(buf, 1, now_tick=100)] == ["stale_lowval"]
    # value-weighted -> 10 + 1.0*50 = 60 beats 100? no; use weight 5 -> 10+250 > 100
    order = [r["episode_id"] for r in rb.sample(buf, 1, now_tick=100, value_weight=5.0)]
    assert order == ["fresh_highval"]


def test_value_present_but_zero_weight_is_pure_recency():
    buf = [_surface("a", archived=0, value=99.0), _surface("b", archived=5, value=0.0)]
    # value ignored at weight 0 -> oldest (a) first
    assert [r["episode_id"] for r in rb.sample(buf, 2, now_tick=100)] == ["a", "b"]


def test_tag_value_sets_record():
    buf = [_surface("a"), _surface("b")]
    rb.tag_value(buf, "b", 7.5)
    assert next(r for r in buf if r["episode_id"] == "b")["value"] == 7.5


def test_to_replay_episode_kwargs_shapes():
    surf = rb.to_replay_episode_kwargs(_surface("ep-1"))
    assert surf["kind"] == "surface" and surf["correct"] == "приказу" and surf["lattice_id"] == "L2_word"
    rule = rb.to_replay_episode_kwargs(
        {"episode_id": "r", "kind": "rule", "cue": "кoro", "correct": "корова",
         "rule_id": "R:script.no_mixed_alphabet", "rule_hint": "один алфавит"}
    )
    assert rule["kind"] == "rule" and rule["rule_id"] == "R:script.no_mixed_alphabet"
