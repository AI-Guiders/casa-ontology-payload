#!/usr/bin/env python3
"""Retention@N under listen interference — replay vs ablation (CASA-ADR-0009, UC v0.3).

Scenario (in-memory, deterministic):
  teach correction → sleep → listen flood → N empty/replay sleeps → measure target copies.

Pass criterion for the bench gate: replay branch retains at least as many target copies
as ablation and strictly wins on the bundled synthetic scenario.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.memory_prisms import (
    append_episode,
    ensure_prisms,
    memory_lattices,
    run_sleep,
    _strengthen_concept,
)
from casa.prisms.shared.lattice_names_v1 import LEXICON_RU

# canonical id: append_episode/run_sleep canonicalize the legacy "L2_word" alias to
# lexicon-ru, so the lattice must be keyed canonically or the retain lookup misses
LATTICE_ID = LEXICON_RU
TARGET_CONCEPT = "lang.word.приказ"
MIN_RETAIN_COPIES = 2
STRENGTH = 4


def _concept_token(concept_id: str) -> str:
    return concept_id if str(concept_id).startswith("C:") else f"C:{concept_id}"


def count_concept_copies(lattice: dict, concept_id: str) -> int:
    tok = _concept_token(concept_id)
    return sum(1 for cell in lattice.get("cells") or [] for t in cell if str(t) == tok)


def mini_state() -> dict:
    n = 16 * 16
    lat = {"width": 16, "height": 16, "cells": [[] for _ in range(n)], "concept_prefix": "lang.word."}
    return ensure_prisms(
        {
            "field_version": 1,
            "sss": {"lattices": {LATTICE_ID: lat}, "active_lattice": LATTICE_ID},
            "consolidation": {},
        }
    )


def teach_correction(state: dict) -> None:
    append_episode(
        state,
        cue="согласно",
        surface_attempt="приказа",
        correct="приказу",
        lattice_id=LATTICE_ID,
        concept_id=TARGET_CONCEPT,
        correction_kind="ortho_surface",
        scene="канцелярия",
    )


def listen_flood(state: dict, *, words: int, copies: int) -> None:
    lattices = memory_lattices(state)
    for i in range(words):
        _strengthen_concept(lattices, LATTICE_ID, f"lang.word.noise{i:02d}", copies=copies)


def run_scenario(
    *,
    replay_k: int,
    interference_words: int = 28,
    interference_copies: int = 8,
    rehearsal_sleeps: int = 2,
    strength: int = STRENGTH,
) -> dict[str, Any]:
    state = mini_state()
    bundle: dict = {"claims": [], "graph": {"edges": []}}

    teach_correction(state)
    run_sleep(state, bundle, replay_k=0, strength=strength)
    lat = memory_lattices(state)[LATTICE_ID]
    immediate = count_concept_copies(lat, TARGET_CONCEPT)

    listen_flood(state, words=interference_words, copies=interference_copies)
    lat = memory_lattices(state)[LATTICE_ID]
    after_flood = count_concept_copies(lat, TARGET_CONCEPT)

    for _ in range(rehearsal_sleeps):
        run_sleep(state, bundle, replay_k=replay_k, strength=strength)

    lat = memory_lattices(state)[LATTICE_ID]
    final = count_concept_copies(lat, TARGET_CONCEPT)

    return {
        "replay_k": replay_k,
        "immediate_copies": immediate,
        "after_flood_copies": after_flood,
        "final_copies": final,
        "immediate_pass": immediate >= MIN_RETAIN_COPIES,
        "retained": final >= MIN_RETAIN_COPIES,
        "interference_words": interference_words,
        "rehearsal_sleeps": rehearsal_sleeps,
    }


def compare(*, interference_words: int = 28, rehearsal_sleeps: int = 2) -> dict[str, Any]:
    ablation = run_scenario(replay_k=0, interference_words=interference_words, rehearsal_sleeps=rehearsal_sleeps)
    replay = run_scenario(replay_k=1, interference_words=interference_words, rehearsal_sleeps=rehearsal_sleeps)
    gap_ablation = int(ablation["immediate_pass"]) - int(ablation["retained"])
    gap_replay = int(replay["immediate_pass"]) - int(replay["retained"])
    improved = replay["final_copies"] > ablation["final_copies"] or (
        replay["retained"] and not ablation["retained"]
    )
    return {
        "schema_version": 1,
        "bench": "retention",
        "min_retain_copies": MIN_RETAIN_COPIES,
        "ablation": ablation,
        "replay": replay,
        "forgetting_gap_ablation": gap_ablation,
        "forgetting_gap_replay": gap_replay,
        "replay_reduces_gap": gap_replay <= gap_ablation,
        "improved": improved,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="retention@N bench — replay vs ablation (ADR-0009)")
    p.add_argument("--interference-words", type=int, default=28)
    p.add_argument("--rehearsal-sleeps", type=int, default=2)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    report = compare(interference_words=args.interference_words, rehearsal_sleeps=args.rehearsal_sleeps)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    return 0 if report["improved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
